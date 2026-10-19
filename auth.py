import re
import logging
from urllib.parse import urlparse, urljoin
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User, LoginAttempt

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()
logger = logging.getLogger('daily_code_exam.security')

COMMON_PASSWORDS = {
    'password', 'password123', 'admin12345', '1234567890', 'qwertyuiop',
    'letmein1234', 'welcome123', 'iloveyou123', 'secret1234', 'monkey1234',
    'football12', 'testing123', 'passcode123', 'dragon1234', 'master1234'
}


def is_safe_url(target):
    """Prevents Open Redirect attacks by validating the redirect target host."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def validate_password_strength(password: str):
    """
    Validates that password:
    - Has at least 10 characters
    - Contains at least 1 uppercase letter
    - Contains at least 1 lowercase letter
    - Contains at least 1 digit
    - Contains at least 1 special character
    - Is not in the common passwords blacklist
    """
    if len(password) < 10:
        return False, "Password must be at least 10 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_=+/\\~`]', password):
        return False, "Password must contain at least one special symbol."
    
    clean_pw = password.lower().strip()
    for common in COMMON_PASSWORDS:
        if common in clean_pw:
            return False, "Password is too common or easily guessable."
            
    return True, ""


def admin_required(f):
    """Decorator to protect administrative routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.path))
        if not current_user.is_admin:
            logger.warning(f"Unauthorized admin access attempt by user {current_user.username} from IP {request.remote_addr}")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('exam.exam_page'))

    errors = {}
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Username validation: 3-20 chars alphanumeric and underscore
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            errors['username'] = "Username must be 3-20 characters and contain only letters, numbers, and underscores."
        elif User.query.filter_by(username=username).first():
            errors['username'] = "Username is already taken."

        # Email validation
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            errors['email'] = "Please provide a valid email address."
        elif User.query.filter_by(email=email).first():
            errors['email'] = "An account with this email already exists."

        # Password matching
        if password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."
        else:
            is_valid, msg = validate_password_strength(password)
            if not is_valid:
                errors['password'] = msg

        if not errors:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(
                username=username,
                email=email,
                password_hash=hashed_pw
            )
            db.session.add(new_user)
            db.session.commit()

            logger.info(f"New user registered: {username} from IP {request.remote_addr}")
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('auth.login'))

    return render_template('register.html', errors=errors)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('exam.exam_page'))

    error_msg = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        client_ip = request.remote_addr or '0.0.0.0'

        # Account lockout check: 5 failed attempts in 15 mins locks account
        locked, reason = LoginAttempt.is_locked_out(username, client_ip, max_attempts=5, window_minutes=15)
        if locked:
            logger.warning(f"LOCKED OUT login attempt for '{username}' from IP {client_ip} (trigger: {reason})")
            # Strictly show generic error without leaking lockout status or user existence
            flash("Invalid credentials.", "danger")
            return render_template('login.html', error_msg="Invalid credentials.")

        # Check credentials
        user = User.query.filter(
            (User.username == username) | (User.email == username.lower())
        ).first()

        valid_credentials = False
        if user and bcrypt.check_password_hash(user.password_hash, password):
            valid_credentials = True

        if not valid_credentials:
            # Record failed attempt
            LoginAttempt.record(username=username, ip_address=client_ip, successful=False)
            logger.warning(f"Failed login attempt for user '{username}' from IP {client_ip}")
            # Generic response never reveals which field was wrong
            flash("Invalid credentials.", "danger")
            return render_template('login.html', error_msg="Invalid credentials.")

        # Successful Login
        LoginAttempt.record(username=user.username, ip_address=client_ip, successful=True)

        # Enforce single active session: regenerate session token
        token = user.generate_session_token()
        db.session.commit()

        # Session regeneration to prevent session fixation attacks
        session.clear()
        session['session_token'] = token
        session.permanent = True

        login_user(user, remember=False)
        logger.info(f"Successful login for '{user.username}' from IP {client_ip}")
        flash(f"Welcome back, {user.username}!", "success")

        # Open-redirect safe redirection
        next_page = request.args.get('next')
        if next_page and is_safe_url(next_page):
            return redirect(next_page)
        return redirect(url_for('exam.exam_page'))

    return render_template('login.html', error_msg=error_msg)


@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    # Clear session token in database to prevent reuse
    current_user.session_token = None
    db.session.commit()

    logout_user()
    session.clear()
    logger.info(f"User {username} logged out from IP {request.remote_addr}")
    flash("You have been logged out securely.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    errors = {}
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not bcrypt.check_password_hash(current_user.password_hash, current_password):
            errors['current_password'] = "Incorrect current password."

        if new_password != confirm_password:
            errors['confirm_password'] = "New passwords do not match."
        else:
            is_valid, msg = validate_password_strength(new_password)
            if not is_valid:
                errors['new_password'] = msg

        if not errors:
            current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            # Invalidate older sessions
            current_user.generate_session_token()
            session['session_token'] = current_user.session_token
            db.session.commit()

            logger.info(f"Password changed for user {current_user.username}")
            flash("Your password has been updated successfully.", "success")
            return redirect(url_for('dashboard.view_dashboard'))

    return render_template('change_password.html', errors=errors)
