import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base configuration loaded from environment variables."""
    # Core Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-insecure-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', '0') in ('1', 'true', 'True')
    ENV = os.environ.get('FLASK_ENV', 'production')

    # Database: fix Render/Heroku postgres:// schema if necessary
    db_url = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(basedir, 'daily_code_exam.db')}"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    } if not db_url.startswith("sqlite") else {}

    # Strict Session Security
    SESSION_COOKIE_HTTPONLY = True
    # In production or if explicitly configured, enforce Secure cookie
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1')
    SESSION_COOKIE_SAMESITE = 'Strict'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_REFRESH_EACH_REQUEST = True

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200  # 2 hours, matches session

    # Code Executor Settings
    EXECUTOR = os.environ.get('EXECUTOR', 'piston').lower()
    EXECUTOR_URL = os.environ.get('EXECUTOR_URL', 'https://emkc.org/api/v2/piston/execute')
    EXECUTOR_API_KEY = os.environ.get('EXECUTOR_API_KEY', '')
    EXECUTOR_TIMEOUT = int(os.environ.get('EXECUTOR_TIMEOUT', '10'))

    # Groq AI Settings
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

    # Uploads Config
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB maximum file upload
    ALLOWED_EXTENSIONS = {'.py', '.txt', '.pdf', '.docx'}

    # Security & Time Window
    BYPASS_TIME_WINDOW = os.environ.get('BYPASS_TIME_WINDOW', 'false').lower() in ('true', '1')
    MAX_CODE_SIZE_BYTES = 10 * 1024  # 10 KB limit
    ALLOWED_LANGUAGES = {'python', 'javascript', 'cpp', 'java'}

    # Security Logging
    LOG_FILE = os.path.join(basedir, 'security.log')

    # Content Security Policy for Talisman
    CSP = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            "'unsafe-eval'",
            "https://cdnjs.cloudflare.com",
            "https://cdn.jsdelivr.net",
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            "https://cdnjs.cloudflare.com",
            "https://cdn.jsdelivr.net",
            "https://fonts.googleapis.com",
        ],
        'font-src': [
            "'self'",
            "data:",
            "https://cdnjs.cloudflare.com",
            "https://cdn.jsdelivr.net",
            "https://fonts.gstatic.com",
        ],
        'img-src': [
            "'self'",
            "data:",
            "https:",
        ],
        'worker-src': [
            "'self'",
            "blob:",
            "https://cdnjs.cloudflare.com",
            "https://cdn.jsdelivr.net",
        ],
        'connect-src': [
            "'self'",
            "https://cdnjs.cloudflare.com",
            "https://cdn.jsdelivr.net",
            "https://emkc.org",
        ],
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}
