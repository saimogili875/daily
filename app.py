import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_bcrypt import Bcrypt
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

from config import Config, config_by_name
from models import db, User, IST
from seed import seed_database
from auth import auth_bp
from exam import exam_bp, trigger_groq_question_generation
from dashboard import dashboard_bp

# Initialize extensions
login_manager = LoginManager()
csrf = CSRFProtect()
bcrypt = Bcrypt()

def get_limiter_key():
    """Returns user ID if authenticated, else client IP address."""
    if current_user and current_user.is_authenticated:
        return f"user:{current_user.id}"
    return get_remote_address()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day"],
    storage_uri="memory://"
)


def create_app(config_name=None):
    app = Flask(__name__)

    # Load configuration
    env_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config_by_name.get(env_name, Config))

    # Configure Security Logging
    setup_security_logging(app)

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"

    # Security Headers via Talisman
    # Monaco editor requires worker blob and script eval in web workers
    is_prod = not app.config.get('DEBUG', False)
    Talisman(
        app,
        content_security_policy=app.config.get('CSP'),
        content_security_policy_nonce_in=[],
        force_https=is_prod and app.config.get('SESSION_COOKIE_SECURE', False),
        strict_transport_security=is_prod,
        session_cookie_secure=app.config.get('SESSION_COOKIE_SECURE', False),
        session_cookie_http_only=True,
        frame_options='DENY',
        referrer_policy='strict-origin-when-cross-origin'
    )

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(dashboard_bp)

    # Apply strict endpoint-specific rate limiting
    # Register: 3/hour per IP
    limiter.limit("3 per hour", key_func=get_remote_address)(app.view_functions['auth.register'])
    # Login: 5/minute per IP
    limiter.limit("5 per minute", key_func=get_remote_address)(app.view_functions['auth.login'])
    # Run: 10/min per user
    limiter.limit("10 per minute", key_func=get_limiter_key)(app.view_functions['exam.run_code'])
    # Submit: 5/min per user
    limiter.limit("5 per minute", key_func=get_limiter_key)(app.view_functions['exam.submit_exam'])

    # Single Active Session Check & Session Verification
    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        if user:
            # Verify user's session token matches session cookie
            token_in_session = session.get('session_token')
            if token_in_session and user.session_token and user.session_token != token_in_session:
                # Concurrent login detected; invalidate older session
                return None
        return user

    @app.before_request
    def check_concurrent_session():
        if current_user.is_authenticated:
            session_token = session.get('session_token')
            if current_user.session_token and session_token != current_user.session_token:
                app.logger.warning(f"Concurrent session detected for user {current_user.username}; terminating old session.")
                logout_user()
                session.clear()
                flash("Your session was terminated because a new login occurred on another browser or device.", "warning")
                return redirect(url_for('auth.login'))

    # Custom Error Handlers (Leak no stack traces)
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json:
            return jsonify({'error': 'Forbidden. Access denied or action blocked.'}), 403
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json:
            return jsonify({'error': 'Resource not found.'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f"Rate limit exceeded: {request.remote_addr} on {request.path}")
        if request.is_json:
            return jsonify({'error': f'Rate limit exceeded. Please wait before retrying: {e.description}'}), 429
        return render_template('429.html', description=e.description), 429

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}", exc_info=True)
        if request.is_json:
            return jsonify({'error': 'An internal server error occurred.'}), 500
        return render_template('500.html'), 500

    # CLI Seed Command
    @app.cli.command('seed')
    def seed_cmd():
        """Flask CLI command to seed 30 questions and initial admin."""
        seed_database(app)

    # Initialize Database and Seed if empty
    with app.app_context():
        db.create_all()
        # Seed automatically if no questions present
        from models import Question
        if Question.query.count() == 0:
            seed_database(app)

    # APScheduler for Daily 8:55 PM IST Question Generation
    start_scheduler(app)

    return app


def setup_security_logging(app):
    """Sets up dedicated rotating log file for security events."""
    log_file = app.config.get('LOG_FILE', 'security.log')
    handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [PID:%(process)d] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    # Configure security and groq loggers
    for log_name in ['daily_code_exam.security', 'daily_code_exam.groq', 'werkzeug']:
        l = logging.getLogger(log_name)
        l.addHandler(handler)
        l.setLevel(logging.INFO)

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def start_scheduler(app):
    """Initializes APScheduler background job for daily question generation at 8:55 PM IST."""
    # Prevent running twice in debug reloader
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.config.get('DEBUG', False):
        try:
            scheduler = BackgroundScheduler(timezone=IST)
            
            def scheduled_task():
                with app.app_context():
                    app.logger.info("Running daily 8:55 PM IST Groq Question Generation...")
                    success, msg = trigger_groq_question_generation()
                    app.logger.info(f"Daily question generation result: {msg}")

            # Run every day at 20:55 (8:55 PM IST)
            scheduler.add_job(
                scheduled_task,
                'cron',
                hour=20,
                minute=55,
                timezone=IST,
                id='daily_groq_generation',
                replace_existing=True
            )
            scheduler.start()
            app.logger.info("APScheduler initialized: Daily Groq question job scheduled at 20:55 IST.")
        except Exception as e:
            app.logger.warning(f"Could not start background scheduler: {e}")


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
