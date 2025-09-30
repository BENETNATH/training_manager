from datetime import datetime
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import enum
import secrets
import os

# Many-to-Many relationship tables
tutor_skill_association = db.Table('tutor_skill_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

training_path_skills = db.Table('training_path_skills',
    db.Column('training_path_id', db.Integer, db.ForeignKey('training_path.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

training_path_assigned_users = db.Table('training_path_assigned_users',
    db.Column('training_path_id', db.Integer, db.ForeignKey('training_path.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

training_session_attendees = db.Table('training_session_attendees',
    db.Column('training_session_id', db.Integer, db.ForeignKey('training_session.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

training_session_skills_covered = db.Table('training_session_skills_covered',
    db.Column('training_session_id', db.Integer, db.ForeignKey('training_session.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

training_request_skills_requested = db.Table('training_request_skills_requested',
    db.Column('training_request_id', db.Integer, db.ForeignKey('training_request.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

training_request_species_requested = db.Table('training_request_species_requested',
    db.Column('training_request_id', db.Integer, db.ForeignKey('training_request.id'), primary_key=True),
    db.Column('species_id', db.Integer, db.ForeignKey('species.id'), primary_key=True)
)

# Many-to-Many relationship table for ExternalTrainingSkillClaim and Species
external_training_skill_claim_species_association = db.Table('external_training_skill_claim_species_association',
    db.Column('external_training_skill_claim_external_training_id', db.Integer, db.ForeignKey('external_training_skill_claim.external_training_id'), primary_key=True),
    db.Column('external_training_skill_claim_skill_id', db.Integer, db.ForeignKey('external_training_skill_claim.skill_id'), primary_key=True),
    db.Column('species_id', db.Integer, db.ForeignKey('species.id'), primary_key=True)
)

class ExternalTrainingSkillClaim(db.Model):
    external_training_id = db.Column(db.Integer, db.ForeignKey('external_training.id'), primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), primary_key=True)
    level = db.Column(db.String(64), nullable=False, default='Novice') # e.g., 'Novice', 'Intermediate', 'Expert'
    wants_to_be_tutor = db.Column(db.Boolean, default=False)

    external_training = db.relationship('ExternalTraining', back_populates='skill_claims')
    skill = db.relationship('Skill', back_populates='external_training_claims')
    species_claimed = db.relationship(
        'Species',
        secondary=external_training_skill_claim_species_association,
        primaryjoin=lambda: db.and_(
            external_training_skill_claim_species_association.c.external_training_skill_claim_external_training_id == ExternalTrainingSkillClaim.external_training_id,
            external_training_skill_claim_species_association.c.external_training_skill_claim_skill_id == ExternalTrainingSkillClaim.skill_id
        ),
        secondaryjoin=lambda: external_training_skill_claim_species_association.c.species_id == Species.id,
        backref='external_training_skill_claims'
    )

skill_species_association = db.Table('skill_species_association',
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True),
    db.Column('species_id', db.Integer, db.ForeignKey('species.id'), primary_key=True)
)

skill_practice_event_skills = db.Table('skill_practice_event_skills',
    db.Column('skill_practice_event_id', db.Integer, db.ForeignKey('skill_practice_event.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

user_team_membership = db.Table('user_team_membership',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)

user_team_leadership = db.Table('user_team_leadership',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)


class Complexity(enum.Enum):
    SIMPLE = 'Simple'
    MODERATE = 'Modéré'
    COMPLEX = 'Complexe'

class TrainingRequestStatus(enum.Enum):
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'
    PROPOSED_SKILL = 'Proposed Skill'

class ExternalTrainingStatus(enum.Enum):
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), index=True, unique=False, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    api_key = db.Column(db.String(64), unique=True, nullable=True) # New API Key field

    teams = db.relationship('Team', secondary=user_team_membership, back_populates='members')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.api_key is None:
            self.generate_api_key()
    teams_as_lead = db.relationship('Team', secondary=user_team_leadership, back_populates='team_leads')
    competencies = db.relationship('Competency', back_populates='user', lazy='dynamic', foreign_keys='Competency.user_id')
    evaluated_competencies = db.relationship('Competency', back_populates='evaluator', lazy='dynamic', foreign_keys='Competency.evaluator_id')
    training_sessions_as_tutor = db.relationship('TrainingSession', back_populates='tutor', lazy='dynamic', foreign_keys='TrainingSession.tutor_id')
    training_requests = db.relationship('TrainingRequest', back_populates='requester', lazy='dynamic')
    external_trainings = db.relationship('ExternalTraining', back_populates='user', lazy='dynamic', foreign_keys='ExternalTraining.user_id')
    validated_external_trainings = db.relationship('ExternalTraining', back_populates='validator', lazy='dynamic', foreign_keys='ExternalTraining.validator_id')
    skill_practice_events = db.relationship('SkillPracticeEvent', back_populates='user', lazy='dynamic')
    assigned_training_paths = db.relationship('TrainingPath', secondary=training_path_assigned_users, back_populates='assigned_users')
    tutored_skills = db.relationship('Skill', secondary=tutor_skill_association, back_populates='tutors')
    attended_training_sessions = db.relationship('TrainingSession', secondary=training_session_attendees, back_populates='attendees')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self):
        self.api_key = secrets.token_hex(32)

    @classmethod
    def check_for_admin_user(cls):
        return cls.query.filter_by(is_admin=True).first()

    @classmethod
    def create_admin_user(cls, email, password, full_name="Admin User"):
        admin_user = cls(full_name=full_name, email=email, is_admin=True)
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        return admin_user

    def __repr__(self):
        return f'<User {self.full_name}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    members = db.relationship('User', secondary=user_team_membership, back_populates='teams')
    team_leads = db.relationship('User', secondary=user_team_leadership, back_populates='teams_as_lead')

    def __repr__(self):
        return f'<Team {self.name}>'

class Species(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    skills = db.relationship('Skill', secondary=skill_species_association, back_populates='species')
    training_requests_for_species = db.relationship('TrainingRequest', secondary=training_request_species_requested, back_populates='species_requested')

    def __repr__(self):
        return f'<Species {self.name}>'

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, unique=True, nullable=False)
    description = db.Column(db.Text)
    validity_period_months = db.Column(db.Integer, default=12)
    complexity = db.Column(db.Enum(Complexity), default=Complexity.SIMPLE, nullable=False)
    reference_urls_text = db.Column(db.Text) # Stores multiple URLs as text, e.g., comma-separated or JSON string
    protocol_attachment_path = db.Column(db.String(256)) # Path to uploaded protocol document
    training_videos_urls_text = db.Column(db.Text) # Stores multiple URLs as text
    potential_external_tutors_text = db.Column(db.Text) # Stores names/contact info as text

    species = db.relationship('Species', secondary=skill_species_association, back_populates='skills')
    tutors = db.relationship('User', secondary=tutor_skill_association, back_populates='tutored_skills')
    training_paths = db.relationship('TrainingPath', secondary=training_path_skills, back_populates='skills')
    competencies = db.relationship('Competency', back_populates='skill', lazy='dynamic')
    training_sessions_covered = db.relationship('TrainingSession', secondary=training_session_skills_covered, back_populates='skills_covered')
    training_requests_for_skill = db.relationship('TrainingRequest', secondary=training_request_skills_requested, back_populates='skills_requested')
    external_training_claims = db.relationship('ExternalTrainingSkillClaim', back_populates='skill', lazy='dynamic')
    skill_practice_events = db.relationship('SkillPracticeEvent', secondary=skill_practice_event_skills, back_populates='skills')

    def __repr__(self):
        return f'<Skill {self.name}>'

class TrainingPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text)

    skills = db.relationship('Skill', secondary=training_path_skills, back_populates='training_paths')
    assigned_users = db.relationship('User', secondary=training_path_assigned_users, back_populates='assigned_training_paths')

    def __repr__(self):
        return f'<TrainingPath {self.name}>'

class TrainingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(128))
    start_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    tutor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ethical_authorization_id = db.Column(db.String(64))
    animal_count = db.Column(db.Integer)
    attachment_path = db.Column(db.String(256)) # Path to uploaded attendance sheet or other document

    tutor = db.relationship('User', back_populates='training_sessions_as_tutor', foreign_keys='TrainingSession.tutor_id')
    attendees = db.relationship('User', secondary=training_session_attendees, back_populates='attended_training_sessions')
    skills_covered = db.relationship('Skill', secondary=training_session_skills_covered, back_populates='training_sessions_covered')
    competencies = db.relationship('Competency', back_populates='training_session', lazy='dynamic')

    @property
    def associated_species(self):
        species_set = set()
        for skill in self.skills_covered:
            species_set.update(skill.species)
        return list(species_set)

    def __repr__(self):
        return f'<TrainingSession {self.title}>'

competency_species_association = db.Table('competency_species_association',
    db.Column('competency_id', db.Integer, db.ForeignKey('competency.id'), primary_key=True),
    db.Column('species_id', db.Integer, db.ForeignKey('species.id'), primary_key=True)
)

class Competency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    level = db.Column(db.String(64)) # e.g., 'Novice', 'Intermediate', 'Expert'
    evaluation_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    training_session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'))
    certificate_path = db.Column(db.String(256)) # Path to generated certificate

    user = db.relationship('User', back_populates='competencies', foreign_keys='Competency.user_id')
    skill = db.relationship('Skill', back_populates='competencies')
    evaluator = db.relationship('User', back_populates='evaluated_competencies', foreign_keys='Competency.evaluator_id')
    training_session = db.relationship('TrainingSession', back_populates='competencies')
    species = db.relationship('Species', secondary=competency_species_association, backref='competencies')

    def __repr__(self):
        return f'<Competency {self.user.full_name} - {self.skill.name}>'

class SkillPracticeEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    practice_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    notes = db.Column(db.Text)

    user = db.relationship('User', back_populates='skill_practice_events')
    skills = db.relationship('Skill', secondary=skill_practice_event_skills, back_populates='skill_practice_events')

    def __repr__(self):
        skill_names = ', '.join([s.name for s in self.skills]) if self.skills else 'No Skills'
        return f'<SkillPracticeEvent {self.user.full_name} - {skill_names} on {self.practice_date.strftime("%Y-%m-%d")}>'

class TrainingRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.Enum(TrainingRequestStatus), default=TrainingRequestStatus.PENDING, nullable=False)

    requester = db.relationship('User', back_populates='training_requests')
    skills_requested = db.relationship('Skill', secondary=training_request_skills_requested, back_populates='training_requests_for_skill')
    species_requested = db.relationship('Species', secondary=training_request_species_requested, back_populates='training_requests_for_species')

    @property
    def associated_species(self):
        species_set = set()
        for skill in self.skills_requested:
            species_set.update(skill.species)
        # Also include species directly requested
        species_set.update(self.species_requested)
        return list(species_set)

    def __repr__(self):
        return f'<TrainingRequest {self.id} by {self.requester.full_name}>'

class ExternalTraining(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    external_trainer_name = db.Column(db.String(128))
    date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    attachment_path = db.Column(db.String(256)) # Path to external certificate/document
    status = db.Column(db.Enum(ExternalTrainingStatus), default=ExternalTrainingStatus.PENDING, nullable=False)
    validator_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship('User', back_populates='external_trainings', foreign_keys='ExternalTraining.user_id')
    validator = db.relationship('User', back_populates='validated_external_trainings', foreign_keys='ExternalTraining.validator_id')
    skill_claims = db.relationship('ExternalTrainingSkillClaim', back_populates='external_training', lazy='select', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ExternalTraining {self.id} by {self.user.full_name}>'
