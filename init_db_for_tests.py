
import os
from app import create_app, db
from app.models import User, init_roles_and_permissions

app = create_app()
with app.app_context():
    init_roles_and_permissions()
    if not User.query.filter_by(email='admin@example.com').first():
        User.create_admin_user('admin@example.com', 'password')
    db.session.commit()
