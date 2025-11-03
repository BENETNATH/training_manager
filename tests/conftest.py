import sys
import os
import pytest
from faker import Faker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import init_roles_and_permissions, User
from config import Config

import logging

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False # Disable CSRF for easier testing

@pytest.fixture(scope='session')
def app():
    app = create_app(TestConfig)
    with app.app_context():
        # Configure logging for tests
        logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
        app.logger.handlers = [] # Clear existing handlers
        app.logger.addHandler(logging.StreamHandler(sys.stderr))
        app.logger.setLevel(logging.ERROR)

        db.create_all()
        init_roles_and_permissions()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    with app.test_client() as client:
        with app.app_context():
            yield client
            db.session.remove()
            db.drop_all()
            db.create_all()

@pytest.fixture(scope='function')
def admin_user(app):
    with app.app_context():
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(full_name='Admin User', email='admin@example.com', is_admin=True, is_approved=True)
            admin.set_password('admin_password')
            db.session.add(admin)
            db.session.commit()
        return admin

@pytest.fixture(scope='function')
def user_factory(app, db):
    def _user_factory(**kwargs):
        with app.app_context():
            fake = Faker()
            user = User(
                full_name=kwargs.get('full_name', fake.name()),
                email=kwargs.get('email', fake.email()),
                password_hash=kwargs.get('password_hash', None),
                is_admin=kwargs.get('is_admin', False),
                is_approved=kwargs.get('is_approved', True),
                study_level=kwargs.get('study_level', None)
            )
            if 'password' in kwargs:
                user.set_password(kwargs['password'])
            else:
                user.set_password('password') # Default password
            db.session.add(user)
            db.session.commit()
            return user
    return _user_factory

@pytest.fixture(scope='function')
def runner(app):
    return app.test_cli_runner()
