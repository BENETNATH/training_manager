from flask import Blueprint, session, current_app # Import session, current_app
from flask_restx import Api
from flask_login import current_user, login_user
from app import login as login_manager # Import the login_manager instance
from app.models import User # Import the User model

bp = Blueprint('api', __name__)
api = Api(bp,
          title='Training Manager API',
          version='1.0',
          description='A RESTful API for the Training Manager application',
          csrf_protect=False)



from app.api import routes
