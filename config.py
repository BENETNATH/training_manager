import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for Flask application. Set it in .env file.")
    
    # Ensure the SQLite database path is absolute
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('sqlite:///'):
        db_path = db_url.split('sqlite:///')[1]
        if not os.path.isabs(db_path):
            # Build absolute path from project root
            db_path = os.path.join(basedir, db_path)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
    elif db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        # Default to an absolute path if DATABASE_URL is not set
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 16 * 1000 * 1000  # 16 MB upload limit

    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost' # Default to localhost
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or None # Keep None if not set
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or None # Keep None if not set
    
    # ADMINS should be a list of email addresses
    ADMINS = [email.strip() for email in os.environ.get('ADMIN_EMAILS', '').split(',') if email.strip()]

    LANGUAGES = ['en', 'fr']

    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

    # Session Cookie Settings for Security
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    if SESSION_COOKIE_SAMESITE.lower() == 'none':
        SESSION_COOKIE_SAMESITE = None

    # Logging Level
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO' # Default to INFO
