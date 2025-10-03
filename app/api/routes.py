from flask import jsonify, request
from flask_restx import Resource, fields
from app.api import api
from app import db
from app.models import User, Team, Species, Skill, TrainingPath, TrainingSession, Competency, SkillPracticeEvent, TrainingRequest, ExternalTraining, Complexity, TrainingRequestStatus, ExternalTrainingStatus, TrainingSessionTutorSkill
from werkzeug.security import generate_password_hash
from functools import wraps # Import wraps
import secrets # Import secrets
from datetime import datetime, timedelta # Import datetime

# API Models for marshalling

# Define skill_model first as it's a dependency for user_model
skill_model = api.model('Skill', {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(required=True, description='Skill name'),
    'description': fields.String(description='Skill description'),
    'validity_period_months': fields.Integer(description='Validity period in months'),
    'complexity': fields.String(enum=[c.value for c in Complexity], description='Complexity level'),
    'reference_urls_text': fields.String(description='Comma-separated reference URLs'),
    'protocol_attachment_path': fields.String(description='Path to protocol attachment'),
    'training_videos_urls_text': fields.String(description='Comma-separated training video URLs'),
    'potential_external_tutors_text': fields.String(description='Comma-separated potential external tutors'),
    'species_ids': fields.List(fields.Integer, description='List of associated species IDs', attribute=lambda x: [s.id for s in x.species]),
    'tutor_ids': fields.List(fields.Integer, description='List of associated tutor IDs', attribute=lambda x: [t.id for t in x.tutors]),
})

user_model = api.model('User', {
    'id': fields.Integer(readOnly=True),
    'full_name': fields.String(required=True, description='User full name'),
    'email': fields.String(required=True, description='User email address'),
    'is_admin': fields.Boolean(description='Is user an administrator'),
    'api_key': fields.String(description='User API Key', readOnly=True), # Expose API key
    'team_id': fields.Integer(description='ID of the team the user belongs to'), # This might need adjustment if a user can belong to multiple teams
    'is_team_lead': fields.Boolean(description='Is user a team lead', attribute=lambda x: len(x.teams_as_lead) > 0, readOnly=True),
    'team_name': fields.String(attribute=lambda x: x.teams[0].name if x.teams else None, description='Name of the team the user belongs to', readOnly=True),
    'tutored_skills': fields.List(fields.Nested(skill_model), attribute='tutored_skills', description='Skills the user can tutor', skip_none=True),
})

team_model = api.model('Team', {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(required=True, description='Team name'),
    'lead_id': fields.Integer(description='ID of the team lead user'),
    'lead_name': fields.String(attribute='lead.full_name', description='Name of the team lead', readOnly=True),
})

species_model = api.model('Species', {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(required=True, description='Species name'),
})


training_path_model = api.model('TrainingPath', {
    'id': fields.Integer(readOnly=True),
    'name': fields.String(required=True, description='Training path name'),
    'description': fields.String(description='Training path description'),
    'skill_ids': fields.List(fields.Integer, description='List of skill IDs in this path', attribute=lambda x: [s.id for s in x.skills]),
    'assigned_user_ids': fields.List(fields.Integer, description='List of user IDs assigned to this path', attribute=lambda x: [u.id for u in x.assigned_users]),
})

training_session_model = api.model('TrainingSession', {
    'id': fields.Integer(readOnly=True),
    'title': fields.String(required=True, description='Session title'),
    'location': fields.String(description='Session location'),
    'start_time': fields.DateTime(dt_format='iso8601', description='Session start time (ISO 8601)'),
    'end_time': fields.DateTime(dt_format='iso8601', description='Session end time (ISO 8601)'),
    'tutor_id': fields.Integer(description='ID of the tutor'),
    'ethical_authorization_id': fields.String(description='Ethical authorization ID'),
    'animal_count': fields.Integer(description='Number of animals involved'),
    'attachment_path': fields.String(description='Path to session attachment'),
    'attendee_ids': fields.List(fields.Integer, description='List of attendee user IDs', attribute=lambda x: [u.id for u in x.attendees]),
    'skills_covered_ids': fields.List(fields.Integer, description='List of skills covered IDs', attribute=lambda x: [s.id for s in x.skills_covered]),
})

competency_model = api.model('Competency', {
    'id': fields.Integer(readOnly=True),
    'user_id': fields.Integer(required=True, description='ID of the user'),
    'skill_id': fields.Integer(required=True, description='ID of the skill'),
    'level': fields.String(description='Competency level'),
    'evaluation_date': fields.DateTime(dt_format='iso8601', description='Evaluation date (ISO 8601)'),
    'evaluator_id': fields.Integer(description='ID of the evaluator'),
    'training_session_id': fields.Integer(description='ID of the training session'),
    'certificate_path': fields.String(description='Path to certificate'),
})

skill_practice_event_model = api.model('SkillPracticeEvent', {
    'id': fields.Integer(readOnly=True),
    'user_id': fields.Integer(required=True, description='ID of the user'),
    'skill_id': fields.Integer(required=True, description='ID of the skill'),
    'practice_date': fields.DateTime(dt_format='iso8601', description='Practice date (ISO 8601)'),
    'notes': fields.String(description='Notes about the practice'),
})

training_request_model = api.model('TrainingRequest', {
    'id': fields.Integer(readOnly=True),
    'requester_id': fields.Integer(required=True, description='ID of the requester'),
    'request_date': fields.DateTime(dt_format='iso8601', description='Request date (ISO 8601)'),
    'status': fields.String(enum=[s.value for s in TrainingRequestStatus], description='Request status'),
    'skills_requested_ids': fields.List(fields.Integer, description='List of requested skill IDs', attribute=lambda x: [s.id for s in x.skills_requested]),
})

external_training_model = api.model('ExternalTraining', {
    'id': fields.Integer(readOnly=True),
    'user_id': fields.Integer(required=True, description='ID of the user'),
    'external_trainer_name': fields.String(description='Name of the external trainer'),
    'date': fields.DateTime(dt_format='iso8601', description='Date of external training (ISO 8601)'),
    'attachment_path': fields.String(description='Path to attachment'),
    'status': fields.String(enum=[s.value for s in ExternalTrainingStatus], description='Status of external training'),
    'validator_id': fields.Integer(description='ID of the validator'),
    'skills_claimed_ids': fields.List(fields.Integer, description='List of claimed skill IDs', attribute=lambda x: [s.id for s in x.skills_claimed]),
})

skill_ids_payload = api.model('SkillIdsPayload', {
    'skill_ids': fields.List(fields.Integer, required=True, description='List of skill IDs')
})


tutor_validity_payload = api.model('TutorValidityPayload', {
    'skill_id': fields.Integer(required=True, description='Skill ID'),
    'training_date': fields.String(required=True, description='Date of the training')
})


# API Key Authentication
def token_required(f):
    @api.doc(security='apikey')
    @wraps(f)
    def decorated(*args, **kwargs):
        # Temporarily bypass API key check for debugging
        print("[DEBUG] API Key check bypassed for debugging.")
        return f(*args, **kwargs)
        # Original API key check logic (commented out):
        # api_key = request.headers.get('X-API-Key')
        # if not api_key:
        #     api.abort(401, "API Key is missing")
        
        # users_with_keys = User.query.filter(User.api_key.isnot(None)).all()
        # found_user = None
        # for user in users_with_keys:
        #     if secrets.compare_digest(user.api_key, api_key):
        #         found_user = user
        #         break

        # if not found_user:
        #     api.abort(401, "Invalid API Key")
        
        # return f(*args, **kwargs)
    return decorated

# Namespaces
ns_users = api.namespace('users', description='User operations')
ns_teams = api.namespace('teams', description='Team operations')
ns_species = api.namespace('species', description='Species operations')
ns_skills = api.namespace('skills', description='Skill operations')
ns_tutors = api.namespace('tutors', description='Tutor operations')
ns_training_paths = api.namespace('training_paths', description='Training Path operations')
ns_training_sessions = api.namespace('training_sessions', description='Training Session operations')
ns_competencies = api.namespace('competencies', description='Competency operations')
ns_skill_practice_events = api.namespace('skill_practice_events', description='Skill Practice Event operations')
ns_training_requests = api.namespace('training_requests', description='Training Request operations')
ns_external_trainings = api.namespace('external_trainings', description='External Training operations')

@api.route('/test')
class TestResource(Resource):
    def get(self):
        print("[DEBUG] Test endpoint reached!")
        return {'message': 'Test endpoint reached successfully!'}, 200


# User Endpoints
@ns_users.route('/')
class UserList(Resource):
    @api.marshal_list_with(user_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all users"""
        return User.query.all()

    @api.expect(user_model)
    @api.marshal_with(user_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new user"""
        data = api.payload
        user = User(full_name=data['full_name'], email=data['email'],
                    is_admin=data.get('is_admin', False),
                    is_team_lead=data.get('is_team_lead', False))
        if 'password' in data: # Password should be hashed before saving
            user.set_password(data['password'])
        if 'team_id' in data:
            user.team = Team.query.get(data['team_id'])
        db.session.add(user)
        db.session.commit()
        return user, 201

@ns_users.route('/<int:id>')
@api.response(404, 'User not found')
@api.param('id', 'The user identifier')
class UserResource(Resource):
    @api.marshal_with(user_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a user by ID"""
        return User.query.get_or_404(id)

    @api.expect(user_model)
    @api.marshal_with(user_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a user by ID"""
        user = User.query.get_or_404(id)
        data = api.payload
        user.full_name = data['full_name']
        user.email = data['email']
        user.is_admin = data.get('is_admin', user.is_admin)
        user.is_team_lead = data.get('is_team_lead', user.is_team_lead)
        if 'password' in data:
            user.set_password(data['password'])
        if 'team_id' in data:
            user.team = Team.query.get(data['team_id'])
        
        # Generate API key if it's missing
        if user.api_key is None:
            user.generate_api_key()

        db.session.commit()
        return user

    @api.response(204, 'User deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a user by ID"""
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        return '', 204

# Team Endpoints
@ns_teams.route('/')
class TeamList(Resource):
    @api.marshal_list_with(team_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all teams"""
        return Team.query.all()

    @api.expect(team_model)
    @api.marshal_with(team_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new team"""
        data = api.payload
        team = Team(name=data['name'])
        if 'lead_id' in data:
            team.lead = User.query.get(data['lead_id'])
        db.session.add(team)
        db.session.commit()
        return team, 201

@ns_teams.route('/<int:id>')
@api.response(404, 'Team not found')
@api.param('id', 'The team identifier')
class TeamResource(Resource):
    @api.marshal_with(team_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a team by ID"""
        return Team.query.get_or_404(id)

    @api.expect(team_model)
    @api.marshal_with(team_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a team by ID"""
        team = Team.query.get_or_404(id)
        data = api.payload
        team.name = data['name']
        if 'lead_id' in data:
            team.lead = User.query.get(data['lead_id'])
        db.session.commit()
        return team

    @api.response(204, 'Team deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a team by ID"""
        team = Team.query.get_or_404(id)
        db.session.delete(team)
        db.session.commit()
        return '', 204

# Species Endpoints
@ns_species.route('/')
class SpeciesList(Resource):
    @api.marshal_list_with(species_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all species"""
        return Species.query.all()

    @api.expect(species_model)
    @api.marshal_with(species_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new species"""
        data = api.payload
        species = Species(name=data['name'])
        db.session.add(species)
        db.session.commit()
        return species, 201

@ns_species.route('/<int:id>/skills')
@api.response(404, 'Species not found')
@api.param('id', 'The species identifier')
class SpeciesSkills(Resource):
    @api.marshal_list_with(skill_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve skills for a species by ID"""
        species = Species.query.get_or_404(id)
        return species.skills

@ns_species.route('/<int:id>')
@api.response(404, 'Species not found')
@api.param('id', 'The species identifier')
class SpeciesResource(Resource):
    @api.marshal_with(species_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a species by ID"""
        return Species.query.get_or_404(id)

    @api.expect(species_model)
    @api.marshal_with(species_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a species by ID"""
        species = Species.query.get_or_404(id)
        data = api.payload
        species.name = data['name']
        db.session.commit()
        return species

    @api.response(204, 'Species deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a species by ID"""
        species = Species.query.get_or_404(id)
        db.session.delete(species)
        db.session.commit()
        return '', 204

# Training Path Endpoints
@ns_training_paths.route('/')
class TrainingPathList(Resource):
    @api.marshal_list_with(training_path_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all training paths"""
        return TrainingPath.query.all()

    @api.expect(training_path_model)
    @api.marshal_with(training_path_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new training path"""
        data = api.payload
        training_path = TrainingPath(name=data['name'], description=data.get('description'))
        
        if 'skill_ids' in data:
            training_path.skills = Skill.query.filter(Skill.id.in_(data['skill_ids'])).all()
        if 'assigned_user_ids' in data:
            training_path.assigned_users = User.query.filter(User.id.in_(data['assigned_user_ids'])).all()

        db.session.add(training_path)
        db.session.commit()
        return training_path, 201

@ns_training_paths.route('/<int:id>')
@api.response(404, 'Training Path not found')
@api.param('id', 'The training path identifier')
class TrainingPathResource(Resource):
    @api.marshal_with(training_path_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a training path by ID"""
        return TrainingPath.query.get_or_404(id)

    @api.expect(training_path_model)
    @api.marshal_with(training_path_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a training path by ID"""
        training_path = TrainingPath.query.get_or_404(id)
        data = api.payload
        training_path.name = data['name']
        training_path.description = data.get('description', training_path.description)

        if 'skill_ids' in data:
            training_path.skills = Skill.query.filter(Skill.id.in_(data['skill_ids'])).all()
        if 'assigned_user_ids' in data:
            training_path.assigned_users = User.query.filter(User.id.in_(data['assigned_user_ids'])).all()

        db.session.commit()
        return training_path

    @api.response(204, 'Training Path deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a training path by ID"""
        training_path = TrainingPath.query.get_or_404(id)
        db.session.delete(training_path)
        db.session.commit()
        return '', 204

# Training Session Endpoints
@ns_training_sessions.route('/<int:id>/tutor_skill_mappings')
@api.response(404, 'Training Session not found')
@api.param('id', 'The training session identifier')
class TrainingSessionTutorSkillMapping(Resource):
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve tutor skill mappings for a training session by ID"""
        session = TrainingSession.query.get_or_404(id)
        mappings = TrainingSessionTutorSkill.query.filter_by(training_session_id=session.id).all()
        return [{'tutor_id': m.tutor_id, 'skill_id': m.skill_id} for m in mappings]

@ns_training_sessions.route('/')
class TrainingSessionList(Resource):
    @api.marshal_list_with(training_session_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all training sessions"""
        return TrainingSession.query.all()

    @api.expect(training_session_model)
    @api.marshal_with(training_session_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new training session"""
        data = api.payload
        session = TrainingSession(
            title=data['title'],
            location=data.get('location'),
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            ethical_authorization_id=data.get('ethical_authorization_id'),
            animal_count=data.get('animal_count'),
            attachment_path=data.get('attachment_path')
        )
        if 'tutor_id' in data:
            session.tutor = User.query.get(data['tutor_id'])
        if 'attendee_ids' in data:
            session.attendees = User.query.filter(User.id.in_(data['attendee_ids'])).all()
        if 'skills_covered_ids' in data:
            session.skills_covered = Skill.query.filter(Skill.id.in_(data['skills_covered_ids'])).all()
        
        db.session.add(session)
        db.session.commit()
        return session, 201

@ns_training_sessions.route('/<int:id>')
@api.response(404, 'Training Session not found')
@api.param('id', 'The training session identifier')
class TrainingSessionResource(Resource):
    @api.marshal_with(training_session_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a training session by ID"""
        return TrainingSession.query.get_or_404(id)

    @api.expect(training_session_model)
    @api.marshal_with(training_session_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a training session by ID"""
        session = TrainingSession.query.get_or_404(id)
        data = api.payload
        session.title = data['title']
        session.location = data.get('location', session.location)
        session.start_time = datetime.fromisoformat(data['start_time'])
        session.end_time = datetime.fromisoformat(data['end_time'])
        session.ethical_authorization_id = data.get('ethical_authorization_id', session.ethical_authorization_id)
        session.animal_count = data.get('animal_count', session.animal_count)
        session.attachment_path = data.get('attachment_path', session.attachment_path)

        if 'tutor_id' in data:
            session.tutor = User.query.get(data['tutor_id'])
        if 'attendee_ids' in data:
            session.attendees = User.query.filter(User.id.in_(data['attendee_ids'])).all()
        if 'skills_covered_ids' in data:
            session.skills_covered = Skill.query.filter(Skill.id.in_(data['skills_covered_ids'])).all()

        db.session.commit()
        return session

    @api.response(204, 'Training Session deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a training session by ID"""
        session = TrainingSession.query.get_or_404(id)
        db.session.delete(session)
        db.session.commit()
        return '', 204

# Competency Endpoints
@ns_competencies.route('/')
class CompetencyList(Resource):
    @api.marshal_list_with(competency_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all competencies"""
        return Competency.query.all()

    @api.expect(competency_model)
    @api.marshal_with(competency_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new competency"""
        data = api.payload
        competency = Competency(
            user_id=data['user_id'],
            skill_id=data['skill_id'],
            level=data.get('level'),
            evaluation_date=datetime.fromisoformat(data['evaluation_date']) if 'evaluation_date' in data else datetime.utcnow(),
            certificate_path=data.get('certificate_path')
        )
        if 'evaluator_id' in data:
            competency.evaluator = User.query.get(data['evaluator_id'])
        if 'training_session_id' in data:
            competency.training_session = TrainingSession.query.get(data['training_session_id'])
        
        db.session.add(competency)
        db.session.commit()
        return competency, 201

@ns_competencies.route('/<int:id>')
@api.response(404, 'Competency not found')
@api.param('id', 'The competency identifier')
class CompetencyResource(Resource):
    @api.marshal_with(competency_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a competency by ID"""
        return Competency.query.get_or_404(id)

    @api.expect(competency_model)
    @api.marshal_with(competency_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a competency by ID"""
        competency = Competency.query.get_or_404(id)
        data = api.payload
        competency.user_id = data['user_id']
        competency.skill_id = data['skill_id']
        competency.level = data.get('level', competency.level)
        competency.evaluation_date = datetime.fromisoformat(data['evaluation_date']) if 'evaluation_date' in data else competency.evaluation_date
        competency.certificate_path = data.get('certificate_path', competency.certificate_path)

        if 'evaluator_id' in data:
            competency.evaluator = User.query.get(data['evaluator_id'])
        if 'training_session_id' in data:
            competency.training_session = TrainingSession.query.get(data['training_session_id'])

        db.session.commit()
        return competency

    @api.response(204, 'Competency deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a competency by ID"""
        competency = Competency.query.get_or_404(id)
        db.session.delete(competency)
        db.session.commit()
        return '', 204

# Skill Practice Event Endpoints
@ns_skill_practice_events.route('/')
class SkillPracticeEventList(Resource):
    @api.marshal_list_with(skill_practice_event_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all skill practice events"""
        return SkillPracticeEvent.query.all()

    @api.expect(skill_practice_event_model)
    @api.marshal_with(skill_practice_event_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new skill practice event"""
        data = api.payload
        event = SkillPracticeEvent(
            user_id=data['user_id'],
            skill_id=data['skill_id'],
            practice_date=datetime.fromisoformat(data['practice_date']) if 'practice_date' in data else datetime.utcnow(),
            notes=data.get('notes')
        )
        db.session.add(event)
        db.session.commit()
        return event, 201

@ns_skill_practice_events.route('/<int:id>')
@api.response(404, 'Skill Practice Event not found')
@api.param('id', 'The skill practice event identifier')
class SkillPracticeEventResource(Resource):
    @api.marshal_with(skill_practice_event_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a skill practice event by ID"""
        return SkillPracticeEvent.query.get_or_404(id)

    @api.expect(skill_practice_event_model)
    @api.marshal_with(skill_practice_event_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a skill practice event by ID"""
        event = SkillPracticeEvent.query.get_or_404(id)
        data = api.payload
        event.user_id = data['user_id']
        event.skill_id = data['skill_id']
        event.practice_date = datetime.fromisoformat(data['practice_date']) if 'practice_date' in data else event.practice_date
        event.notes = data.get('notes', event.notes)
        db.session.commit()
        return event

    @api.response(204, 'Skill Practice Event deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a skill practice event by ID"""
        event = SkillPracticeEvent.query.get_or_404(id)
        db.session.delete(event)
        db.session.commit()
        return '', 204

# Training Request Endpoints
@ns_training_requests.route('/')
class TrainingRequestList(Resource):
    @api.marshal_list_with(training_request_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all training requests"""
        return TrainingRequest.query.all()

    @api.expect(training_request_model)
    @api.marshal_with(training_request_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new training request"""
        data = api.payload
        training_request = TrainingRequest(
            requester_id=data['requester_id'],
            request_date=datetime.fromisoformat(data['request_date']) if 'request_date' in data else datetime.utcnow(),
            status=TrainingRequestStatus[data['status'].upper()] if 'status' in data else TrainingRequestStatus.PENDING
        )
        if 'skills_requested_ids' in data:
            training_request.skills_requested = Skill.query.filter(Skill.id.in_(data['skills_requested_ids'])).all()
        
        db.session.add(training_request)
        db.session.commit()
        return training_request, 201

@ns_training_requests.route('/<int:id>')
@api.response(404, 'Training Request not found')
@api.param('id', 'The training request identifier')
class TrainingRequestResource(Resource):
    @api.marshal_with(training_request_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a training request by ID"""
        return TrainingRequest.query.get_or_404(id)

    @api.expect(training_request_model)
    @api.marshal_with(training_request_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a training request by ID"""
        training_request = TrainingRequest.query.get_or_404(id)
        data = api.payload
        training_request.requester_id = data['requester_id']
        training_request.request_date = datetime.fromisoformat(data['request_date']) if 'request_date' in data else training_request.request_date
        training_request.status = TrainingRequestStatus[data['status'].upper()] if 'status' in data else training_request.status

        if 'skills_requested_ids' in data:
            training_request.skills_requested = Skill.query.filter(Skill.id.in_(data['skills_requested_ids'])).all()

        db.session.commit()
        return training_request

    @api.response(204, 'Training Request deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a training request by ID"""
        training_request = TrainingRequest.query.get_or_404(id)
        db.session.delete(training_request)
        db.session.commit()
        return '', 204

# External Training Endpoints
@ns_external_trainings.route('/')
class ExternalTrainingList(Resource):
    @api.marshal_list_with(external_training_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all external trainings"""
        return ExternalTraining.query.all()

    @api.expect(external_training_model)
    @api.marshal_with(external_training_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new external training"""
        data = api.payload
        external_training = ExternalTraining(
            user_id=data['user_id'],
            external_trainer_name=data.get('external_trainer_name'),
            date=datetime.fromisoformat(data['date']) if 'date' in data else datetime.utcnow(),
            attachment_path=data.get('attachment_path'),
            status=ExternalTrainingStatus[data['status'].upper()] if 'status' in data else ExternalTrainingStatus.PENDING
        )
        if 'validator_id' in data:
            external_training.validator = User.query.get(data['validator_id'])
        if 'skills_claimed_ids' in data:
            external_training.skills_claimed = Skill.query.filter(Skill.id.in_(data['skills_claimed_ids'])).all()
        
        db.session.add(external_training)
        db.session.commit()
        return external_training, 201

@ns_external_trainings.route('/<int:id>')
@api.response(404, 'External Training not found')
@api.param('id', 'The external training identifier')
class ExternalTrainingResource(Resource):
    @api.marshal_with(external_training_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve an external training by ID"""
        return ExternalTraining.query.get_or_404(id)

    @api.expect(external_training_model)
    @api.marshal_with(external_training_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update an external training by ID"""
        external_training = ExternalTraining.query.get_or_404(id)
        data = api.payload
        external_training.user_id = data['user_id']
        external_training.external_trainer_name = data.get('external_trainer_name', external_training.external_trainer_name)
        external_training.date = datetime.fromisoformat(data['date']) if 'date' in data else external_training.date
        external_training.attachment_path = data.get('attachment_path', external_training.attachment_path)
        external_training.status = ExternalTrainingStatus[data['status'].upper()] if 'status' in data else external_training.status

        if 'validator_id' in data:
            external_training.validator = User.query.get(data['validator_id'])
        if 'skills_claimed_ids' in data:
            external_training.skills_claimed = Skill.query.filter(Skill.id.in_(data['skills_claimed_ids'])).all()

        db.session.commit()
        return external_training

    @api.response(204, 'External Training deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete an external training by ID"""
        external_training = ExternalTraining.query.get_or_404(id)
        db.session.delete(external_training)
        db.session.commit()
        return '', 204

# Skill Endpoints
@ns_skills.route('/')
class SkillListResource(Resource):
    @api.marshal_list_with(skill_model)
    @api.doc(security='apikey')
    @token_required
    def get(self):
        """List all skills"""
        return Skill.query.all()

    @api.expect(skill_model)
    @api.marshal_with(skill_model, code=201)
    @api.doc(security='apikey')
    @token_required
    def post(self):
        """Create a new skill"""
        data = api.payload
        skill = Skill(name=data['name'], description=data.get('description'),
                      validity_period_months=data.get('validity_period_months'),
                      complexity=Complexity[data['complexity'].upper()],
                      reference_urls_text=data.get('reference_urls_text'),
                      protocol_attachment_path=data.get('protocol_attachment_path'),
                      training_videos_urls_text=data.get('training_videos_urls_text'),
                      potential_external_tutors_text=data.get('potential_external_tutors_text'))
        
        if 'species_ids' in data:
            skill.species = Species.query.filter(Species.id.in_(data['species_ids'])).all()
        if 'tutor_ids' in data:
            skill.tutors = User.query.filter(User.id.in_(data['tutor_ids'])).all()

        db.session.add(skill)
        db.session.commit()
        return skill, 201

@ns_skills.route('/species')
class SkillSpecies(Resource):
    @api.doc(description='Get species for a list of skills.')
    @api.expect(skill_ids_payload)
    @token_required
    def post(self):
        """Get species for a list of skills"""
        data = api.payload
        skill_ids = data['skill_ids']

        if not skill_ids:
            return jsonify({'species': []})

        # Find all skills first
        skills = Skill.query.filter(Skill.id.in_(skill_ids)).all()
        if not skills or len(skills) != len(skill_ids):
            return jsonify({'species': []})

        # Get all species for the first skill
        common_species = set(skills[0].species)

        # Intersect with species of other skills
        for skill in skills[1:]:
            common_species.intersection_update(skill.species)

        # Prepare response with species details
        species_data = []
        for species in common_species:
            species_data.append({
                'id': species.id,
                'name': species.name,
            })

        return jsonify({'species': species_data})

@ns_skills.route('/tutors')
class SkillTutors(Resource):
    @api.doc(description='Get tutors for a list of skills.')
    @api.expect(skill_ids_payload)
    @token_required
    def post(self):
        """Get tutors for a list of skills"""
        data = api.payload
        skill_ids = data['skill_ids']

        if not skill_ids:
            return jsonify({'tutors': []})

        # Find all skills first
        skills = Skill.query.filter(Skill.id.in_(skill_ids)).all()
        if not skills or len(skills) != len(skill_ids):
            return jsonify({'tutors': []})

        # Get all tutors that can teach at least one of the selected skills
        tutors = set()
        for skill in skills:
            tutors.update(skill.tutors)

        # Prepare response with tutor details
        tutors_data = []
        for tutor in tutors:
            tutors_data.append({
                'id': tutor.id,
                'full_name': tutor.full_name,
                'email': tutor.email,
            })

        return jsonify({'tutors': tutors_data})

@ns_skills.route('/tutors_for_skills')
class SkillTutorsForSkills(Resource):
    @api.doc(description='Get tutors who can teach all specified skills.')
    @api.expect(skill_ids_payload)
    @token_required
    def post(self):
        """Get tutors for a list of skills"""
        data = api.payload
        skill_ids = data['skill_ids']

        if not skill_ids:
            return jsonify({'tutors': []})

        # Find all skills first
        skills = Skill.query.filter(Skill.id.in_(skill_ids)).all()
        if not skills or len(skills) != len(skill_ids):
            return jsonify({'tutors': []})

        # Get all potential tutors (users who can tutor at least one of the requested skills)
        # and then filter them down to those who can tutor ALL requested skills.
        potential_tutors = set()
        for skill in skills:
            potential_tutors.update(skill.tutors)

        qualified_tutors = []
        for tutor in potential_tutors:
            # Check if this tutor can teach ALL selected skills
            if all(skill in tutor.tutored_skills for skill in skills):
                qualified_tutors.append(tutor)

        # Prepare response with tutor details
        tutors_data = []
        for tutor in qualified_tutors:
            tutors_data.append({
                'id': tutor.id,
                'full_name': tutor.full_name,
                'email': tutor.email,
            })

        return jsonify({'tutors': tutors_data})

@ns_skills.route('/<int:id>')
@api.response(404, 'Skill not found')
@api.param('id', 'The skill identifier')
class SkillResource(Resource):
    @api.marshal_with(skill_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve a skill by ID"""
        return Skill.query.get_or_404(id)

    @api.expect(skill_model)
    @api.marshal_with(skill_model)
    @api.doc(security='apikey')
    @token_required
    def put(self, id):
        """Update a skill by ID"""
        skill = Skill.query.get_or_404(id)
        data = api.payload
        skill.name = data['name']
        skill.description = data.get('description', skill.description)
        skill.validity_period_months = data.get('validity_period_months', skill.validity_period_months)
        skill.complexity = Complexity[data['complexity'].upper()]
        skill.reference_urls_text = data.get('reference_urls_text', skill.reference_urls_text)
        skill.protocol_attachment_path = data.get('protocol_attachment_path', skill.protocol_attachment_path)
        skill.training_videos_urls_text = data.get('training_videos_urls_text', skill.training_videos_urls_text)
        skill.potential_external_tutors_text = data.get('potential_external_tutors_text', skill.potential_external_tutors_text)

        if 'species_ids' in data:
            skill.species = Species.query.filter(Species.id.in_(data['species_ids'])).all()
        if 'tutor_ids' in data:
            skill.tutors = User.query.filter(User.id.in_(data['tutor_ids'])).all()

        db.session.commit()
        return skill

    @api.response(204, 'Skill deleted')
    @api.doc(security='apikey')
    @token_required
    def delete(self, id):
        """Delete a skill by ID"""
        skill = Skill.query.get_or_404(id)
        db.session.delete(skill)
        db.session.commit()
        return '', 204

@ns_skills.route('/<int:id>/tutors_with_validity')
@api.response(404, 'Skill not found')
@api.param('id', 'The skill identifier')
class SkillTutorsWithValidity(Resource):
    @api.doc(security='apikey', params={'training_date': 'The training date in YYYY-MM-DD format'})
    @token_required
    def get(self, id):
        """Retrieve tutors for a skill with their validity status"""
        skill = Skill.query.get_or_404(id)
        training_date_str = request.args.get('training_date')
        if not training_date_str:
            api.abort(400, "Training date is required")
        
        try:
            training_date = datetime.strptime(training_date_str, '%Y-%m-%d')
        except ValueError:
            api.abort(400, "Invalid date format. Use YYYY-MM-DD.")

        tutors_data = []
        for tutor in skill.tutors:
            is_valid = True
            message = "Tutor is valid."

            if skill.validity_period_months:
                # Find the latest competency or practice event for this tutor and skill
                latest_competency = Competency.query.filter_by(user_id=tutor.id, skill_id=skill.id).order_by(Competency.evaluation_date.desc()).first()
                latest_practice = SkillPracticeEvent.query.join(SkillPracticeEvent.skills).filter(SkillPracticeEvent.user_id == tutor.id, Skill.id == skill.id).order_by(SkillPracticeEvent.practice_date.desc()).first()

                latest_validation_date = None
                if latest_competency:
                    latest_validation_date = latest_competency.evaluation_date
                if latest_practice and (latest_validation_date is None or latest_practice.practice_date > latest_validation_date):
                    latest_validation_date = latest_practice.practice_date

                if latest_validation_date:
                    recycling_due_date = latest_validation_date + timedelta(days=skill.validity_period_months * 30.44)
                    if training_date.date() > recycling_due_date.date():
                        is_valid = False
                        message = f"{tutor.full_name}'s competency for {skill.name} has expired."
                else:
                    # No competency or practice found, so they are not considered valid for tutoring
                    is_valid = False
                    message = f"No validation record found for {tutor.full_name} on skill {skill.name}."


            tutors_data.append({
                'id': tutor.id,
                'full_name': tutor.full_name,
                'is_valid': is_valid,
                'message': message
            })
        return jsonify(tutors_data)

@ns_tutors.route('/<int:id>/skills')
@api.response(404, 'Tutor not found')
@api.param('id', 'The tutor identifier')
class TutorSkills(Resource):
    @api.marshal_list_with(skill_model)
    @api.doc(security='apikey')
    @token_required
    def get(self, id):
        """Retrieve skills for a tutor by ID"""
        tutor = User.query.get_or_404(id)
        return tutor.tutored_skills

@ns_tutors.route('/<int:id>/check_validity')
@api.response(404, 'Tutor not found')
@api.param('id', 'The tutor identifier')
class TutorValidity(Resource):
    @api.doc(description='Check if a tutor is valid for a given skill and a training date.')
    @api.expect(tutor_validity_payload)
    @token_required
    def post(self, id):
        """Check tutor validity"""
        data = api.payload
        skill_id = data['skill_id']
        training_date = datetime.strptime(data['training_date'], '%Y-%m-%d')

        tutor = User.query.get_or_404(id)

        skill = Skill.query.get_or_404(skill_id)

        if tutor not in skill.tutors:
            return jsonify({'is_valid': False, 'message': f'{tutor.full_name} is not a tutor for {skill.name}.'})

        # Check recycling period
        competency = Competency.query.filter_by(user_id=id, skill_id=skill.id).order_by(Competency.evaluation_date.desc()).first()
        if competency and competency.evaluation_date:
            recycling_due_date = competency.evaluation_date + timedelta(days=skill.validity_period_months * 30.44)
            if training_date > recycling_due_date:
                return jsonify({'is_valid': False, 'message': f'{tutor.full_name}\'s competency for {skill.name} has expired.'})

        return jsonify({'is_valid': True, 'message': 'Tutor is valid.'})

        return jsonify({'is_valid': True, 'message': 'Tutor is valid.'})

# Register namespaces
api.add_namespace(ns_users)
api.add_namespace(ns_tutors)
api.add_namespace(ns_teams)
api.add_namespace(ns_species)
api.add_namespace(ns_skills)
api.add_namespace(ns_training_paths)
api.add_namespace(ns_training_sessions)
api.add_namespace(ns_competencies)
api.add_namespace(ns_skill_practice_events)
api.add_namespace(ns_training_requests)
api.add_namespace(ns_external_trainings)
