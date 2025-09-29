from flask import Blueprint
from flask_restx import Api

bp = Blueprint('api', __name__)
api = Api(bp,
          title='Training Manager API',
          version='1.0',
          description='A RESTful API for the Training Manager application')

from app.api import routes
