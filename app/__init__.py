from flask import Flask, request, g, current_app, session, redirect, url_for
from flask_login import current_user
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel, lazy_gettext as _l
import os
import importlib.resources
from flask_mail import Mail
from flask_bootstrap import Bootstrap # Import Flask-Bootstrap
from dotenv import load_dotenv # Import load_dotenv

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')

@login.unauthorized_handler
def unauthorized():
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Unauthorized: Please log in.'}), 401
    return redirect(url_for('auth.login'))
babel = Babel()
mail = Mail()
bootstrap = Bootstrap() # Initialize Flask-Bootstrap

from app.api import api # Import the api object from app.api
from app.models import User # Import User model

import logging
from logging.handlers import RotatingFileHandler
import os

# ... (rest of the imports and initializations)

def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

def create_app(config_class=Config):
    load_dotenv() # Load environment variables
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.logger.setLevel(logging.DEBUG) # Set logging level to DEBUG

    # Configure file logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/training_manager.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)
    
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    mail.init_app(app)
    bootstrap.init_app(app) # Initialize Flask-Bootstrap with the app

    from app.models import Skill # Import Skill model here

    @app.template_filter('get_skill_name')
    def get_skill_name_filter(skill_id):
        try:
            skill = Skill.query.get(int(skill_id))
            return skill.name if skill else 'Unknown Skill'
        except (ValueError, TypeError):
            # Handle cases where skill_id might not be a valid integer
            return 'Unknown Skill'

    # The api object is already initialized with the blueprint in app.api.__init__.py
    # No need to call api.init_app(app) here, as it's handled by the blueprint registration

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.root import bp as root_bp
    from app.root import routes # Import routes to register them with the blueprint
    app.register_blueprint(root_bp)



    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.team import bp as team_bp
    app.register_blueprint(team_bp, url_prefix='/team')

    from app.training import bp as training_bp
    app.register_blueprint(training_bp, url_prefix='/training')

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    csrf.exempt(api_bp)

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.has_table("user"):
            db.create_all()
            print("Database tables created.")
            # Initialize roles and permissions
            from app.models import init_roles_and_permissions
            init_roles_and_permissions()
            print("Roles and permissions initialized.")

        if User.query.first() is None:
            admin_email = os.environ.get('ADMIN_EMAIL')
            admin_password = os.environ.get('ADMIN_PASSWORD')
            if admin_email and admin_password:
                User.create_admin_user(admin_email, admin_password)
                print("Admin user created.")
            else:
                print("Admin user not created. ADMIN_EMAIL and ADMIN_PASSWORD not set.")

    return app
