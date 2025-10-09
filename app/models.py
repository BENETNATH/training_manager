from datetime import datetime, timedelta
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import enum
import secrets
import os

# Many-to-Many relationship tables
role_permission_association = db.Table('role_permission_association',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)

user_role_association = db.Table('user_role_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

tutor_skill_association = db.Table('tutor_skill_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

training_path_assigned_users = db.Table('training_path_assigned_users',
    db.Column('training_path_id', db.Integer, db.ForeignKey('training_path.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

training_session_tutors = db.Table('training_session_tutors',
    db.Column('training_session_id', db.Integer, db.ForeignKey('training_session.id'), primary_key=True),
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
    practice_date = db.Column(db.DateTime, nullable=True)

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



class TrainingPathSkill(db.Model):
    __tablename__ = 'training_path_skill'
    training_path_id = db.Column(db.Integer, db.ForeignKey('training_path.id'), primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), primary_key=True)
    order = db.Column(db.Integer, nullable=False)

    training_path = db.relationship('TrainingPath', back_populates='skills_association')
    skill = db.relationship('Skill')

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
    is_approved = db.Column(db.Boolean, default=False) # New field for admin approval
    study_level = db.Column(db.String(64), nullable=True)
    api_key = db.Column(db.String(64), unique=True, nullable=True) # New API Key field
    new_email = db.Column(db.String(120), index=True, unique=True, nullable=True) # For email change confirmation
    email_confirmation_token = db.Column(db.String(128), unique=True, nullable=True) # Token for email change confirmation

    teams = db.relationship('Team', secondary=user_team_membership, back_populates='members')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.api_key is None:
            self.generate_api_key()

    teams_as_lead = db.relationship('Team', secondary=user_team_leadership, back_populates='team_leads')
    roles = db.relationship('Role', secondary=user_role_association, back_populates='users', lazy='dynamic')
    competencies = db.relationship('Competency', back_populates='user', lazy='selectin', foreign_keys='[Competency.user_id]')
    evaluated_competencies = db.relationship('Competency', back_populates='evaluator', lazy='dynamic', foreign_keys='Competency.evaluator_id')
    training_requests = db.relationship('TrainingRequest', back_populates='requester', lazy='dynamic')
    external_trainings = db.relationship('ExternalTraining', back_populates='user', lazy='dynamic', foreign_keys='ExternalTraining.user_id')
    validated_external_trainings = db.relationship('ExternalTraining', back_populates='validator', lazy='dynamic', foreign_keys='ExternalTraining.validator_id')
    skill_practice_events = db.relationship('SkillPracticeEvent', back_populates='user', lazy='dynamic')
    assigned_training_paths = db.relationship('TrainingPath', secondary=training_path_assigned_users, back_populates='assigned_users')
    tutored_skills = db.relationship('Skill', secondary=tutor_skill_association, back_populates='tutors')
    attended_training_sessions = db.relationship('TrainingSession', secondary=training_session_attendees, back_populates='attendees')
    tutored_training_sessions = db.relationship('TrainingSession', secondary=training_session_tutors, back_populates='tutors')
    
    # New relationships for regulatory and continuous training
    initial_regulatory_training = db.relationship('InitialRegulatoryTraining', back_populates='user', uselist=False, cascade="all, delete-orphan")
    created_continuous_training_events = db.relationship('ContinuousTrainingEvent', foreign_keys='ContinuousTrainingEvent.creator_id', back_populates='creator', lazy='dynamic')
    validated_continuous_training_events = db.relationship('ContinuousTrainingEvent', foreign_keys='ContinuousTrainingEvent.validator_id', back_populates='validator', lazy='dynamic')
    continuous_trainings_attended = db.relationship('UserContinuousTraining', foreign_keys='UserContinuousTraining.user_id', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    validated_user_continuous_trainings = db.relationship('UserContinuousTraining', foreign_keys='UserContinuousTraining.validated_by_id', back_populates='validated_by', lazy='dynamic')

    # Constants for continuous training
    CONTINUOUS_TRAINING_DAYS_REQUIRED = 3
    CONTINUOUS_TRAINING_YEARS_WINDOW = 6
    HOURS_PER_DAY = 7.15
    MIN_LIVE_TRAINING_RATIO = 0.70 # 70%

    def get_continuous_training_hours(self, start_date, end_date, training_type=None):
        query = self.continuous_trainings_attended.join(ContinuousTrainingEvent).filter(
            UserContinuousTraining.status == UserContinuousTrainingStatus.APPROVED,
            ContinuousTrainingEvent.event_date >= start_date,
            ContinuousTrainingEvent.event_date < end_date
        )
        if training_type:
            query = query.filter(ContinuousTrainingEvent.training_type == training_type)
        
        total_hours = query.with_entities(db.func.sum(UserContinuousTraining.validated_hours)).scalar()
        return total_hours if total_hours is not None else 0.0

    @property
    def total_continuous_training_hours_6_years(self):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=self.CONTINUOUS_TRAINING_YEARS_WINDOW * 365.25) # Account for leap years
        return self.get_continuous_training_hours(start_date, end_date)

    @property
    def live_continuous_training_hours_6_years(self):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=self.CONTINUOUS_TRAINING_YEARS_WINDOW * 365.25)
        return self.get_continuous_training_hours(start_date, end_date, training_type=ContinuousTrainingType.PRESENTIAL)

    @property
    def online_continuous_training_hours_6_years(self):
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=self.CONTINUOUS_TRAINING_YEARS_WINDOW * 365.25)
        return self.get_continuous_training_hours(start_date, end_date, training_type=ContinuousTrainingType.ONLINE)

    @property
    def required_continuous_training_hours(self):
        return self.CONTINUOUS_TRAINING_DAYS_REQUIRED * self.HOURS_PER_DAY

    @property
    def is_continuous_training_compliant(self):
        return self.total_continuous_training_hours_6_years >= self.required_continuous_training_hours

    @property
    def live_training_ratio(self):
        total_hours = self.total_continuous_training_hours_6_years
        if total_hours == 0:
            return 0.0
        return self.live_continuous_training_hours_6_years / total_hours

    @property
    def is_live_training_ratio_compliant(self):
        if self.total_continuous_training_hours_6_years == 0: # If no training, ratio is not applicable
            return True
        return self.live_training_ratio >= self.MIN_LIVE_TRAINING_RATIO

    def get_continuous_training_hours_for_year(self, year):
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
        return self.get_continuous_training_hours(start_date, end_date)

    @property
    def continuous_training_summary_by_year(self):
        summary = {}
        current_year = datetime.utcnow().year
        for year in range(current_year - self.CONTINUOUS_TRAINING_YEARS_WINDOW + 1, current_year + 1):
            summary[year] = self.get_continuous_training_hours_for_year(year)
        return summary

    @property
    def is_at_risk_next_year(self):
        # Check if user has less than 2.5 days (17.875 hours) over the last 5 years
        # This is a simplified check, a more robust one would project forward
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=5 * 365.25)
        hours_last_5_years = self.get_continuous_training_hours(start_date, end_date)
        return hours_last_5_years < (2.5 * self.HOURS_PER_DAY)

    def has_role(self, role_name):
        return self.roles.filter_by(name=role_name).first() is not None

    def can(self, permission_name):
        if self.is_admin: # Admins have all permissions
            return True
        for role in self.roles:
            if role.permissions.filter_by(name=permission_name).first() is not None:
                return True
        return False

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self):
        new_key = secrets.token_hex(32)
        self.api_key = new_key
        return new_key

    def generate_email_confirmation_token(self):
        self.email_confirmation_token = secrets.token_urlsafe(32)
        return self.email_confirmation_token

    def verify_email_confirmation_token(self, token):
        return self.email_confirmation_token == token

    @classmethod
    def check_for_admin_user(cls):
        return cls.query.filter_by(is_admin=True).first()

    @classmethod
    def create_admin_user(cls, email, password, full_name="Admin User"):
        admin_user = cls(full_name=full_name, email=email, is_admin=True, is_approved=True) # Admin users are approved by default
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.flush() # Flush to get admin_user.id
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            admin_user.roles.append(admin_role)
        db.session.commit()
        return admin_user

    def __repr__(self):
        return f'<User {self.full_name}>'

def init_roles_and_permissions():
    # Define core permissions
    permissions_data = [
        {'name': 'admin_access', 'description': 'Access to the admin dashboard and all admin functionalities.'},
        {'name': 'user_manage', 'description': 'Create, edit, and delete users.'},
        {'name': 'role_manage', 'description': 'Create, edit, and delete roles and assign permissions to them.'},
        {'name': 'permission_manage', 'description': 'View and manage permissions.'},
        {'name': 'team_manage', 'description': 'Create, edit, and delete teams.'},
        {'name': 'skill_manage', 'description': 'Create, edit, and delete skills.'},
        {'name': 'species_manage', 'description': 'Create, edit, and delete species.'},
        {'name': 'training_path_manage', 'description': 'Create, edit, and delete training paths.'},
        {'name': 'training_session_manage', 'description': 'Create, edit, and delete training sessions.'},
        {'name': 'training_request_manage', 'description': 'View and manage training requests.'},
        {'name': 'external_training_validate', 'description': 'Validate external trainings.'},
        {'name': 'training_session_validate', 'description': 'Validate competencies for training sessions.'},
        {'name': 'view_reports', 'description': 'View various application reports.'},
        {'name': 'self_edit_profile', 'description': 'Edit own user profile.'},
        {'name': 'self_view_profile', 'description': 'View own user profile.'},
        {'name': 'self_declare_skill_practice', 'description': 'Declare own skill practice events.'},
        {'name': 'self_submit_training_request', 'description': 'Submit own training requests.'},
        {'name': 'self_submit_external_training', 'description': 'Submit own external training records.'},
        {'name': 'view_team_competencies', 'description': 'View competencies of team members.'},
        {'name': 'tutor_for_skill', 'description': 'Can be assigned as a tutor for skills.'},
        {'name': 'tutor_for_session', 'description': 'Can be assigned as a tutor for training sessions.'},
        {'name': 'competency_manage', 'description': 'Manage competencies.'},
        {'name': 'skill_practice_manage', 'description': 'Manage skill practice events.'},
        {'name': 'view_any_certificate', 'description': 'View any user\'s certificate.'},
        {'name': 'view_any_booklet', 'description': 'View any user\'s booklet.'},
        {'name': 'continuous_training_manage', 'description': 'Create, edit, and delete continuous training events.'},
        {'name': 'continuous_training_validate', 'description': 'Validate user attendance for continuous training events.'},
        {'name': 'initial_regulatory_training_manage', 'description': 'Manage initial regulatory training records for users.'},
        {'name': 'self_submit_continuous_training_attendance', 'description': 'Submit own continuous training attendance records.'},
        {'name': 'self_request_continuous_training_event', 'description': 'Request the creation of a new continuous training event.'}, # NEW PERMISSION
    ]

    for p_data in permissions_data:
        permission = Permission.query.filter_by(name=p_data['name']).first()
        if not permission:
            permission = Permission(name=p_data['name'], description=p_data['description'])
            db.session.add(permission)
    db.session.commit()

    # Define roles and assign permissions
    roles_data = {
        'Admin': [
            'admin_access', 'user_manage', 'role_manage', 'permission_manage', 'team_manage', 
            'skill_manage', 'species_manage', 'training_path_manage', 'training_session_manage', 
            'training_request_manage', 'external_training_validate', 'training_session_validate',
            'view_reports', 'self_edit_profile', 'self_declare_skill_practice', 
            'self_submit_training_request', 'self_submit_external_training', 'view_team_competencies',
            'tutor_for_skill', 'tutor_for_session', 'continuous_training_manage', 'continuous_training_validate',
            'initial_regulatory_training_manage', 'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event' # Add to Admin
        ],
        'Team Leader': [
            'self_edit_profile', 'self_declare_skill_practice', 'self_submit_training_request',
            'self_submit_external_training', 'view_team_competencies', 'training_request_manage',
            'tutor_for_skill', 'tutor_for_session', 'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event' # Add to Team Leader
        ],
        'Tutor': [
            'self_edit_profile', 'self_declare_skill_practice', 'self_submit_training_request',
            'self_submit_external_training', 'training_session_validate', 'tutor_for_skill', 'tutor_for_session',
            'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event' # Add to Tutor
        ],
        'Validator': [
            'self_edit_profile', 'continuous_training_validate', 'external_training_validate', 'training_session_validate',
            'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event' # Add to Validator
        ],
        'User': [
            'self_edit_profile', 'self_declare_skill_practice', 'self_submit_training_request',
            'self_submit_external_training', 'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event' # Add to User
        ]
    }

    for r_name, p_names in roles_data.items():
        role = Role.query.filter_by(name=r_name).first()
        if not role:
            role = Role(name=r_name, description=f'{r_name} role')
            db.session.add(role)
            db.session.flush() # Assign an ID to the new role
        
        # Clear existing permissions and re-add to ensure consistency
        role.permissions = []
        for p_name in p_names:
            permission = Permission.query.filter_by(name=p_name).first()
            if permission and permission not in role.permissions:
                role.permissions.append(permission)
    db.session.commit()



class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)

    def __repr__(self):
        return f'<Permission {self.name}>'

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)

    permissions = db.relationship('Permission', secondary=role_permission_association, backref='roles', lazy='dynamic')
    users = db.relationship('User', secondary=user_role_association, back_populates='roles', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'


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
    species_id = db.Column(db.Integer, db.ForeignKey('species.id'), nullable=False) # New: Single species for the training path

    species = db.relationship('Species', backref='training_paths') # New relationship

    skills_association = db.relationship('TrainingPathSkill', back_populates='training_path', cascade="all, delete-orphan", order_by='TrainingPathSkill.order')

    @property
    def skills(self):
        return [assoc.skill for assoc in self.skills_association]

    assigned_users = db.relationship('User', secondary=training_path_assigned_users, back_populates='assigned_training_paths')

    def __repr__(self):
        return f'<TrainingPath {self.name}>'


# ... (other code) ...

class TrainingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(128))
    start_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    main_species_id = db.Column(db.Integer, db.ForeignKey('species.id'))
    ethical_authorization_id = db.Column(db.String(64))
    animal_count = db.Column(db.Integer)
    attachment_path = db.Column(db.String(256)) # Path to uploaded attendance sheet or other document
    status = db.Column(db.String(64), default='Pending') # New status field

    main_species = db.relationship('Species', backref='training_sessions')
    attendees = db.relationship('User', secondary=training_session_attendees, back_populates='attended_training_sessions')
    skills_covered = db.relationship('Skill', secondary=training_session_skills_covered, back_populates='training_sessions_covered')
    competencies = db.relationship('Competency', back_populates='training_session', lazy='dynamic')
    tutors = db.relationship('User', secondary=training_session_tutors, back_populates='tutored_training_sessions')

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
    external_evaluator_name = db.Column(db.String(128), nullable=True) # New field for external evaluator name
    training_session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'))
    external_training_id = db.Column(db.Integer, db.ForeignKey('external_training.id', name='fk_competency_external_training_id'), nullable=True) # New field
    certificate_path = db.Column(db.String(256)) # Path to generated certificate

    user = db.relationship('User', back_populates='competencies', foreign_keys='Competency.user_id')
    skill = db.relationship('Skill', back_populates='competencies')
    evaluator = db.relationship('User', back_populates='evaluated_competencies', foreign_keys='Competency.evaluator_id')
    training_session = db.relationship('TrainingSession', back_populates='competencies')
    external_training = db.relationship('ExternalTraining', backref='competencies') # New relationship
    species = db.relationship('Species', secondary=competency_species_association, backref='competencies')

    @property
    def latest_practice_date(self):
        # Find the most recent practice event for this skill and user
        practice_event = SkillPracticeEvent.query.filter(
            SkillPracticeEvent.user_id == self.user_id,
            SkillPracticeEvent.skills.any(id=self.skill_id)
        ).order_by(SkillPracticeEvent.practice_date.desc()).first()

        # Compare with evaluation_date
        if practice_event and practice_event.practice_date > self.evaluation_date:
            return practice_event.practice_date
        return self.evaluation_date

    @property
    def recycling_due_date(self):
        if self.skill.validity_period_months:
            # Using 30.44 days as average for a month
            return self.latest_practice_date + timedelta(days=self.skill.validity_period_months * 30.44)
        return None

    @property
    def needs_recycling(self):
        if self.recycling_due_date:
            return datetime.utcnow() > self.recycling_due_date
        return False

    @property
    def warning_date(self):
        if self.recycling_due_date and self.skill.validity_period_months:
            # Warning period is typically 1/4 of the validity period
            return self.recycling_due_date - timedelta(days=self.skill.validity_period_months * 30.44 / 4)
        return None

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
    notes = db.Column(db.Text, nullable=True)

    requester = db.relationship('User', back_populates='training_requests')
    skills_requested = db.relationship('Skill', secondary=training_request_skills_requested, back_populates='training_requests_for_skill')
    species_requested = db.relationship('Species', secondary=training_request_species_requested, back_populates='training_requests_for_species')

    @property
    def associated_species(self):
        # If species were explicitly requested, prioritize them.
        if self.species_requested:
            return self.species_requested
        
        # Fallback for older requests: infer from skills.
        species_set = set()
        for skill in self.skills_requested:
            species_set.update(skill.species)
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

class TrainingSessionTutorSkill(db.Model):
    training_session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'), primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), primary_key=True)

    training_session = db.relationship('TrainingSession', backref=db.backref('tutor_skill_mappings', cascade="all, delete-orphan"))
    tutor = db.relationship('User', backref='training_session_skill_mappings')
    skill = db.relationship('Skill', backref='training_session_tutor_mappings')

    def __repr__(self):
        return f'<TrainingSessionTutorSkill Session:{self.training_session_id} Tutor:{self.tutor_id} Skill:{self.skill_id}>'

# New Models for Regulatory and Continuous Training

class InitialRegulatoryTrainingLevel(enum.Enum):
    NIVEAU_1_CONCEPTEUR = 'Niveau 1: Concepteur'
    NIVEAU_2_EXPERIMENTATEUR = 'Niveau 2: Experimentateur'
    NIVEAU_3_SOIGNEUR = 'Niveau 3: Soigneur'

class InitialRegulatoryTraining(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    level = db.Column(db.Enum(InitialRegulatoryTrainingLevel), nullable=False)
    training_date = db.Column(db.DateTime, nullable=False)
    attachment_path = db.Column(db.String(256), nullable=True) # Path to certificate/document

    user = db.relationship('User', back_populates='initial_regulatory_training')

    def __repr__(self):
        return f'<InitialRegulatoryTraining {self.user.full_name} - {self.level.value}>'

class ContinuousTrainingType(enum.Enum):
    ONLINE = 'Online'
    PRESENTIAL = 'Presential'

class ContinuousTrainingEventStatus(enum.Enum):
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'

class ContinuousTrainingEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    training_type = db.Column(db.Enum(ContinuousTrainingType), nullable=False)
    location = db.Column(db.String(128), nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Float, nullable=False) # Duration in hours
    attachment_path = db.Column(db.String(256), nullable=True) # Program attachment
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum(ContinuousTrainingEventStatus), default=ContinuousTrainingEventStatus.PENDING, nullable=False)
    validator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Validator of the event itself

    creator = db.relationship('User', foreign_keys=[creator_id], back_populates='created_continuous_training_events')
    validator = db.relationship('User', foreign_keys=[validator_id], back_populates='validated_continuous_training_events')
    user_attendances = db.relationship('UserContinuousTraining', back_populates='event', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ContinuousTrainingEvent {self.title} on {self.event_date.strftime("%Y-%m-%d")}>'

class UserContinuousTrainingStatus(enum.Enum):
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'

class UserContinuousTraining(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('continuous_training_event.id'), nullable=False)
    attendance_attachment_path = db.Column(db.String(256), nullable=True) # User's certificate of presence
    status = db.Column(db.Enum(UserContinuousTrainingStatus), default=UserContinuousTrainingStatus.PENDING, nullable=False)
    validated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    validation_date = db.Column(db.DateTime, nullable=True)
    validated_hours = db.Column(db.Float, nullable=True) # Actual hours validated for the user

    user = db.relationship('User', foreign_keys=[user_id], back_populates='continuous_trainings_attended')
    event = db.relationship('ContinuousTrainingEvent', back_populates='user_attendances')
    validated_by = db.relationship('User', foreign_keys=[validated_by_id], back_populates='validated_user_continuous_trainings')

    def __repr__(self):
        return f'<UserContinuousTraining {self.user.full_name} - {self.event.title} - {self.status.value}>'
