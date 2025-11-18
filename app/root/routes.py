from flask import redirect, url_for, session, request
from flask_login import current_user, login_required
from app.root import bp

@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.index'))
        else:
            return redirect(url_for('dashboard.dashboard_home'))
    return redirect(url_for('auth.login'))

@bp.route('/personal_dashboard') # New route
@login_required # Ensure only logged-in users can access this
def personal_dashboard_redirect():
    return redirect(url_for('dashboard.dashboard_home'))

@bp.route('/language/<language>')
def language_switch(language):
    session['language'] = language
    return redirect(request.referrer)
