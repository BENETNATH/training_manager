from flask import redirect, url_for
from flask_login import current_user
from app.root import bp

@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.index'))
        else:
            return redirect(url_for('profile.user_profile', username=current_user.full_name))
    return redirect(url_for('auth.login'))
