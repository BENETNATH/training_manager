from flask import Blueprint

bp = Blueprint('training', __name__)

from app.training import routes
