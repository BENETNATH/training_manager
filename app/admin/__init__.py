"""Admin blueprint for managing administrative functionalities."""
from flask import Blueprint

bp = Blueprint('admin', __name__)

from app.admin import routes
