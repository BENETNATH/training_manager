from functools import wraps
from flask_login import current_user, login_required
from flask import abort, current_app, url_for, jsonify, request, redirect, flash
from app.models import TrainingSession, User

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission_name):
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can('admin_access'):
            if current_user.is_authenticated:
                flash('You do not have permission to access the admin dashboard.', 'danger')
                return redirect(url_for('profile.user_profile', username=current_user.full_name))
            else:
                # This case should ideally be handled by @login_required, but as a fallback
                abort(403) # Or redirect to login
        return f(*args, **kwargs)
    return decorator

def tutor_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = kwargs.get('session_id')
        if not session_id:
            # This decorator is intended for routes with a session_id
            abort(500)
        
        session = TrainingSession.query.get_or_404(session_id)
        
        # Check if user has permission to validate training sessions OR is a tutor for this session
        if not current_user.can('training_session_validate') and current_user not in session.tutors:
            abort(403)  # Forbidden
            
        return f(*args, **kwargs)
    return decorated_function

def team_lead_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the user has the 'view_team_competencies' permission
        if not current_user.can('view_team_competencies'):
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'X-API-Key' in request.headers:
            token = request.headers['X-API-Key']

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        user = User.query.filter_by(api_key=token).first()

        if not user:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(*args, **kwargs)

    return decorated
