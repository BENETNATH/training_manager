from flask import Flask, request, g, current_app
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel, lazy_gettext as _l
import os
import importlib.resources
from flask_mail import Mail
from dotenv import load_dotenv # Import load_dotenv

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')
babel = Babel()
mail = Mail()

from app.api import api # Import the api object from app.api
from app.models import User # Import User model

def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

def create_app(config_class=Config):
    load_dotenv() # Load environment variables
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    mail.init_app(app)

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

    from app.profile import bp as profile_bp
    app.register_blueprint(profile_bp, url_prefix='/profile')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.team import bp as team_bp
    app.register_blueprint(team_bp, url_prefix='/team')

    from app.training import bp as training_bp
    app.register_blueprint(training_bp, url_prefix='/training')

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    with app.app_context():
        db.create_all() # Ensure tables are created

        # Check if an admin user exists, if not, create one
    with app.app_context(): # Push application context here
        # Check for and create admin user if none exists
        if not User.check_for_admin_user():
            User.create_admin_user(app.config['ADMIN_EMAIL'], app.config['ADMIN_PASSWORD'])

    return app
