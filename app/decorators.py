from functools import wraps
from flask_login import current_user
from flask import abort
from app.models import TrainingSession

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def tutor_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = kwargs.get('session_id')
        if not session_id:
            # This decorator is intended for routes with a session_id
            abort(500)
        
        session = TrainingSession.query.get_or_404(session_id)
        
        if not current_user.is_admin and current_user.id != session.tutor_id:
            abort(403)  # Forbidden
            
        return f(*args, **kwargs)
    return decorated_function

def team_lead_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the user is authenticated and leads at least one team
        if not current_user.is_authenticated or not current_user.teams_as_lead:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
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
