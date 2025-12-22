import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for Flask application. Set it in .env file.")
    
    # Database Configuration
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite').lower()
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'training_manager')
    DB_USER = os.environ.get('DB_USER', 'appuser')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')

    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    elif DB_TYPE == 'mysql':
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    elif DB_TYPE == 'postgresql':
        SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # Default to SQLite
        db_path = os.path.join(basedir, 'instance', 'app.db')
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path

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
    LOG_LEVEL = os.environ.get('APP_LOG_LEVEL') or os.environ.get('LOG_LEVEL') or 'INFO' # Default to INFO

    # Service API Key for inter-app communication
    SERVICE_API_KEY = os.environ.get('SERVICE_API_KEY')

    # SSO Secret Key for seamless login
    SSO_SECRET_KEY = os.environ.get('SSO_SECRET_KEY')
