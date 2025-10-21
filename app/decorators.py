"""
This module contains custom decorators for handling permissions and authentication.
"""
from functools import wraps
from flask import abort, current_app, url_for, jsonify, request, redirect, flash, g
from flask_login import current_user
from app.models import TrainingSession, User


def permission_required(permission_name):
    """
    Decorator to check if a user has a specific permission.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_to_check = g.current_user if hasattr(g, 'current_user') else current_user
            if not user_to_check.can(permission_name):
                # Log: Authorization failure
                current_app.logger.warning(
                    f"Authorization failure: User {user_to_check.email} (ID: {user_to_check.id}) "
                    f"attempted to access {request.endpoint} without "
                    f"'{permission_name}' permission."
                )
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator to check if a user has admin access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can('admin_access'):
            if current_user.is_authenticated:
                flash('You do not have permission to access the admin dashboard.', 'danger')
                return redirect(url_for('dashboard.user_profile', username=current_user.full_name))
            # This case should ideally be handled by @login_required, but as a fallback
            abort(403) # Or redirect to login
        return f(*args, **kwargs)
    return decorated_function


def tutor_or_admin_required(f):
    """
    Decorator to check if a user is a tutor for a session or has admin rights.
    """
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
    """
    Decorator to check if a user has permission to view team competencies.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the user has the 'view_team_competencies' permission
        if not current_user.can('view_team_competencies'):
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function


def token_required(f):
    """
    Decorator to check for a valid API token in the request headers.
    """
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
