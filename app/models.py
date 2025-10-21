"""
This module defines the database models for the training management application,
including users, roles, permissions, skills, training sessions, and various
training-related entities. It also includes utility functions for role and
permission initialization.
"""
import enum
import secrets
from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login

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
external_training_skill_claim_species_association = db.Table(
    'external_training_skill_claim_species_association',
    db.Column('external_training_skill_claim_external_training_id', db.Integer,
              db.ForeignKey('external_training_skill_claim.external_training_id'),
              primary_key=True),
    db.Column('external_training_skill_claim_skill_id', db.Integer,
              db.ForeignKey('external_training_skill_claim.skill_id'),
              primary_key=True),
    db.Column('species_id', db.Integer, db.ForeignKey('species.id'), primary_key=True)
)

class ExternalTrainingSkillClaim(db.Model):
    """
    Represents a claim for a skill obtained through external training.
    """
    external_training_id = db.Column(db.Integer, db.ForeignKey('external_training.id'),
                                     primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), primary_key=True)
    level = db.Column(db.String(64), nullable=False, default='Novice')
    wants_to_be_tutor = db.Column(db.Boolean, default=False)
    practice_date = db.Column(db.DateTime(timezone=True), nullable=True)

    external_training = db.relationship('ExternalTraining', back_populates='skill_claims')
    skill = db.relationship('Skill', back_populates='external_training_claims')
    species_claimed = db.relationship(
        'Species',
        secondary=external_training_skill_claim_species_association,
        primaryjoin=lambda: db.and_(
            external_training_skill_claim_species_association.c.\
                external_training_skill_claim_external_training_id == \
                ExternalTrainingSkillClaim.external_training_id,
            external_training_skill_claim_species_association.c.\
                external_training_skill_claim_skill_id == ExternalTrainingSkillClaim.skill_id
        ),
        secondaryjoin=lambda: external_training_skill_claim_species_association.c.species_id == \
            Species.id,
        backref='external_training_skill_claims'
    )

skill_species_association = db.Table('skill_species_association',
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True),
    db.Column('species_id', db.Integer, db.ForeignKey('species.id'), primary_key=True)
)

skill_practice_event_skills = db.Table('skill_practice_event_skills',
    db.Column('skill_practice_event_id', db.Integer,
              db.ForeignKey('skill_practice_event.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)


class TrainingPathSkill(db.Model):
    """
    Represents a skill within a training path, including its order.
    """
    __tablename__ = 'training_path_skill'
    training_path_id = db.Column(db.Integer, db.ForeignKey('training_path.id'),
                                 primary_key=True)
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
    """
    Enum for skill complexity levels.
    """
    SIMPLE = 'Simple'
    MODERATE = 'Modéré'
    COMPLEX = 'Complexe'

class TrainingRequestStatus(enum.Enum):
    """
    Enum for the status of a training request.
    """
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'
    PROPOSED_SKILL = 'Proposed Skill'

class ExternalTrainingStatus(enum.Enum):
    """
    Enum for the status of an external training.
    """
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'


class User(UserMixin, db.Model):
    """
    Represents a user in the system.
    """
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), index=True, unique=False, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    study_level = db.Column(db.String(64), nullable=True)
    api_key = db.Column(db.String(64), unique=True, nullable=True)
    new_email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    email_confirmation_token = db.Column(db.String(128), unique=True, nullable=True)

    teams = db.relationship('Team', secondary=user_team_membership, back_populates='members')

    def __init__(self, **kwargs):
        """
        Initializes a new User instance and generates an API key if not provided.
        """
        super().__init__(**kwargs)
        if self.api_key is None:
            self.generate_api_key()

    teams_as_lead = db.relationship('Team', secondary=user_team_leadership,
                                    back_populates='team_leads')
    roles = db.relationship('Role', secondary=user_role_association,
                            back_populates='users', lazy='dynamic')
    competencies = db.relationship('Competency', back_populates='user', lazy='selectin',
                                   foreign_keys=lambda: [Competency.user_id])
    evaluated_competencies = db.relationship('Competency', back_populates='evaluator',
                                             lazy='dynamic',
                                             foreign_keys=lambda: [Competency.evaluator_id])
    training_requests = db.relationship('TrainingRequest', back_populates='requester',
                                        lazy='dynamic')
    external_trainings = db.relationship('ExternalTraining', back_populates='user',
                                         lazy='dynamic',
                                         foreign_keys='ExternalTraining.user_id')
    validated_external_trainings = db.relationship('ExternalTraining', back_populates='validator',
                                                   lazy='dynamic',
                                                   foreign_keys='ExternalTraining.validator_id')
    skill_practice_events = db.relationship('SkillPracticeEvent', back_populates='user',
                                           lazy='dynamic')
    assigned_training_paths = db.relationship('TrainingPath',
                                              secondary=training_path_assigned_users,
                                              back_populates='assigned_users')
    tutored_skills = db.relationship('Skill', secondary=tutor_skill_association,
                                      back_populates='tutors')
    attended_training_sessions = db.relationship('TrainingSession',
                                                  secondary=training_session_attendees,
                                                  back_populates='attendees')
    tutored_training_sessions = db.relationship('TrainingSession',
                                                 secondary=training_session_tutors,
                                                 back_populates='tutors')

    # New relationships for regulatory and continuous training
    initial_regulatory_training = db.relationship('InitialRegulatoryTraining',
                                                  back_populates='user', uselist=False,
                                                  cascade="all, delete-orphan")
    created_continuous_training_events = db.relationship('ContinuousTrainingEvent',
                                                         foreign_keys=lambda: [ContinuousTrainingEvent.creator_id],
                                                         back_populates='creator', lazy='dynamic')
    validated_continuous_training_events = db.relationship('ContinuousTrainingEvent',
                                                           foreign_keys=lambda: [ContinuousTrainingEvent.validator_id],
                                                           back_populates='validator',
                                                           lazy='dynamic')
    continuous_trainings_attended = db.relationship('UserContinuousTraining',
                                                    foreign_keys=lambda: [UserContinuousTraining.user_id],
                                                    back_populates='user', lazy='dynamic',
                                                    cascade="all, delete-orphan")
    validated_user_continuous_trainings = db.relationship('UserContinuousTraining',
                                                           foreign_keys=lambda: [UserContinuousTraining.validated_by_id],
                                                           back_populates='validated_by',
                                                           lazy='dynamic')

    # Constants for continuous training
    CONTINUOUS_TRAINING_DAYS_REQUIRED = 3
    CONTINUOUS_TRAINING_YEARS_WINDOW = 6
    HOURS_PER_DAY = 7.15
    MIN_LIVE_TRAINING_RATIO = 0.70 # 70%

    def get_continuous_training_hours(self, start_date, end_date, training_type=None):
        """
        Calculates the total continuous training hours for a user within a given period.
        """
        query = self.continuous_trainings_attended.join(ContinuousTrainingEvent).filter(
            UserContinuousTraining.status == UserContinuousTrainingStatus.APPROVED,
            ContinuousTrainingEvent.event_date >= start_date,
            ContinuousTrainingEvent.event_date < end_date
        )
        if training_type:
            query = query.filter(ContinuousTrainingEvent.training_type == training_type)

        total_hours = query.with_entities(
            db.func.sum(UserContinuousTraining.validated_hours.cast(db.Float))).scalar()
        return total_hours if total_hours is not None else 0.0

    @property
    def total_continuous_training_hours_6_years(self):
        """
        Returns the total continuous training hours over the last 6 years.
        """
        end_date = datetime.now(timezone.utc)
        # Account for leap years
        start_date = end_date - timedelta(days=self.CONTINUOUS_TRAINING_YEARS_WINDOW * 365.25)
        return self.get_continuous_training_hours(start_date, end_date)

    @property
    def live_continuous_training_hours_6_years(self):
        """
        Returns the live continuous training hours over the last 6 years.
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.CONTINUOUS_TRAINING_YEARS_WINDOW * 365.25)
        return self.get_continuous_training_hours(start_date, end_date,
                                                  training_type=ContinuousTrainingType.PRESENTIAL)

    @property
    def online_continuous_training_hours_6_years(self):
        """
        Returns the online continuous training hours over the last 6 years.
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.CONTINUOUS_TRAINING_YEARS_WINDOW * 365.25)
        return self.get_continuous_training_hours(start_date, end_date,
                                                  training_type=ContinuousTrainingType.ONLINE)

    @property
    def required_continuous_training_hours(self):
        """
        Returns the total required continuous training hours.
        """
        return self.CONTINUOUS_TRAINING_DAYS_REQUIRED * self.HOURS_PER_DAY

    @property
    def is_continuous_training_compliant(self):
        """
        Checks if the user is compliant with continuous training requirements.
        """
        return self.total_continuous_training_hours_6_years >= \
            self.required_continuous_training_hours

    @property
    def live_training_ratio(self):
        """
        Calculates the ratio of live training hours to total continuous training hours.
        """
        total_hours = self.total_continuous_training_hours_6_years
        if total_hours == 0:
            return 0.0
        return self.live_continuous_training_hours_6_years / total_hours

    @property
    def is_live_training_ratio_compliant(self):
        """
        Checks if the user is compliant with the live training ratio requirement.
        """
        # If no training, ratio is not applicable
        if self.total_continuous_training_hours_6_years == 0:
            return True
        return self.live_training_ratio >= self.MIN_LIVE_TRAINING_RATIO

    def get_continuous_training_hours_for_year(self, year):
        """
        Returns continuous training hours for a specific year.
        """
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
        return self.get_continuous_training_hours(start_date, end_date)

    @property
    def continuous_training_summary_by_year(self):
        """
        Returns a summary of continuous training hours by year.
        """
        summary = {}
        current_year = datetime.now(timezone.utc).year
        for year in range(current_year - self.CONTINUOUS_TRAINING_YEARS_WINDOW + 1,
                         current_year + 1):
            summary[year] = self.get_continuous_training_hours_for_year(year)
        return summary

    @property
    def is_at_risk_next_year(self):
        """
        Checks if the user is at risk of non-compliance for continuous training next year.
        """
        # Check if user has less than 2.5 days (17.875 hours) over the last 5 years
        # This is a simplified check, a more robust one would project forward
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=5 * 365.25)
        hours_last_5_years = self.get_continuous_training_hours(start_date, end_date)
        return hours_last_5_years < (2.5 * self.HOURS_PER_DAY)

    def has_role(self, role_name):
        """
        Checks if the user has a specific role.
        """
        return self.roles.filter_by(name=role_name).first() is not None

    def can(self, permission_name):
        """
        Checks if the user has a specific permission.
        """
        if self.is_admin: # Admins have all permissions
            return True
        for role in self.roles:
            if role.permissions.filter_by(name=permission_name).first() is not None:
                return True
        return False

    def set_password(self, password):
        """
        Sets the user's password by hashing it.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Checks if the provided password matches the user's hashed password.
        """
        return check_password_hash(self.password_hash, password)

    def generate_api_key(self):
        """
        Generates a new API key for the user.
        """
        new_key = secrets.token_hex(32)
        self.api_key = new_key
        return new_key

    def generate_email_confirmation_token(self):
        """
        Generates a token for email change confirmation.
        """
        self.email_confirmation_token = secrets.token_urlsafe(32)
        return self.email_confirmation_token

    def verify_email_confirmation_token(self, token):
        """
        Verifies the email confirmation token.
        """
        return self.email_confirmation_token == token

    @classmethod
    def check_for_admin_user(cls):
        """
        Checks if an admin user exists in the database.
        """
        return cls.query.filter_by(is_admin=True).first()

    @classmethod
    def create_admin_user(cls, email, password, full_name="Admin User"):
        """
        Creates a new admin user.
        """
        # Admin users are approved by default
        admin_user = cls(full_name=full_name, email=email, is_admin=True, is_approved=True)
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.flush() # Flush to get admin_user.id
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            admin_user.roles.append(admin_role)
        db.session.commit()
        return admin_user

    def __repr__(self):
        """
        Returns a string representation of the User object.
        """
        return f'<User {self.full_name}>'

def init_roles_and_permissions():
    """
    Initializes default roles and permissions in the database.
    """
    # Define core permissions with categories
    permissions_data = [
        {'name': 'admin_access',
         'description': 'Access to the admin dashboard and all admin functionalities.',
         'category': 'Admin Management'},
        {'name': 'user_manage', 'description': 'Create, edit, and delete users.',
         'category': 'Admin Management'},
        {'name': 'role_manage',
         'description': 'Create, edit, and delete roles and assign permissions to them.',
         'category': 'Admin Management'},
        {'name': 'permission_manage', 'description': 'View and manage permissions.',
         'category': 'Admin Management'},

        {'name': 'team_manage', 'description': 'Create, edit, and delete teams.',
         'category': 'Team Management'},
        {'name': 'view_team_competencies', 'description': 'View competencies of team members.',
         'category': 'Team Management'},

        {'name': 'skill_manage', 'description': 'Create, edit, and delete skills.',
         'category': 'Skill Management'},
        {'name': 'species_manage', 'description': 'Create, edit, and delete species.',
         'category': 'Skill Management'},
        {'name': 'tutor_for_skill', 'description': 'Can be assigned as a tutor for skills.',
         'category': 'Skill Management'},
        {'name': 'competency_manage', 'description': 'Manage competencies.',
         'category': 'Skill Management'},
        {'name': 'skill_practice_manage', 'description': 'Manage skill practice events.',
         'category': 'Skill Management'},

        {'name': 'training_path_manage', 'description': 'Create, edit, and delete training paths.',
         'category': 'Training Management'},
        {'name': 'training_session_manage',
         'description': 'Create, edit, and delete training sessions.',
         'category': 'Training Management'},
        {'name': 'training_request_manage', 'description': 'View and manage training requests.',
         'category': 'Training Management'},
        {'name': 'external_training_validate', 'description': 'Validate external trainings.',
         'category': 'Training Management'},
        {'name': 'training_session_validate',
         'description': 'Validate competencies for training sessions.',
         'category': 'Training Management'},
        {'name': 'continuous_training_manage',
         'description': 'Create, edit, and delete continuous training events.',
         'category': 'Training Management'},
        {'name': 'continuous_training_validate',
         'description': 'Validate user attendance for continuous training events.',
         'category': 'Training Management'},
        {'name': 'initial_regulatory_training_manage',
         'description': 'Manage initial regulatory training records for users.',
         'category': 'Training Management'},

        {'name': 'self_edit_profile', 'description': 'Edit own user dashboard.',
         'category': 'User Self-Service'},
        {'name': 'self_view_profile', 'description': 'View own user dashboard.',
         'category': 'User Self-Service'},
        {'name': 'self_declare_skill_practice', 'description': 'Declare own skill practice events.',
         'category': 'User Self-Service'},
        {'name': 'self_submit_training_request', 'description': 'Submit own training requests.',
         'category': 'User Self-Service'},
        {'name': 'self_submit_external_training', 'description': 'Submit own external training records.',
         'category': 'User Self-Service'},
        {'name': 'self_submit_continuous_training_attendance',
         'description': 'Submit own continuous training attendance records.',
         'category': 'User Self-Service'},
        {'name': 'self_request_continuous_training_event',
         'description': 'Request the creation of a new continuous training event.',
         'category': 'User Self-Service'},

        {'name': 'view_reports', 'description': 'View various application reports.',
         'category': 'Reporting'},
        {'name': 'view_any_certificate', 'description': "View any user's certificate.",
         'category': 'Reporting'},
        {'name': 'view_any_booklet', 'description': "View any user's booklet.",
         'category': 'Reporting'},
    ]

    for p_data in permissions_data:
        permission = Permission.query.filter_by(name=p_data['name']).first()
        if not permission:
            permission = Permission(name=p_data['name'], description=p_data['description'],
                                    category=p_data['category'])
            db.session.add(permission)
        else:
            # Update existing permission's description and category if they changed
            if permission.description != p_data['description']:
                permission.description = p_data['description']
            if permission.category != p_data['category']:
                permission.category = p_data['category']
            db.session.add(permission) # Re-add to ensure update is tracked
    db.session.commit()

    # Define roles and assign permissions
    roles_data = {
        'Admin': [p_data['name'] for p_data in permissions_data], # Assign all permissions to Admin
        'Team Leader': [
            'self_edit_profile', 'self_declare_skill_practice', 'self_submit_training_request',
            'self_submit_external_training', 'view_team_competencies', 'training_request_manage',
            'tutor_for_skill', 'tutor_for_session', 'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event'
        ],
        'Tutor': [
            'self_edit_profile', 'self_declare_skill_practice', 'self_submit_training_request',
            'self_submit_external_training', 'training_session_validate', 'tutor_for_skill',
            'tutor_for_session', 'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event'
        ],
        'Validator': [
            'self_edit_profile', 'continuous_training_validate', 'external_training_validate',
            'training_session_validate', 'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event'
        ],
        'User': [
            'self_edit_profile', 'self_declare_skill_practice', 'self_submit_training_request',
            'self_submit_external_training', 'self_submit_continuous_training_attendance',
            'self_request_continuous_training_event'
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
    """
    Represents a permission that can be assigned to roles.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(64), nullable=True)

    def __repr__(self):
        """
        Returns a string representation of the Permission object.
        """
        return f'<Permission {self.name}>'

class Role(db.Model):
    """
    Represents a user role with associated permissions.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)

    permissions = db.relationship('Permission', secondary=role_permission_association,
                                backref='roles', lazy='dynamic')
    users = db.relationship('User', secondary=user_role_association,
                            back_populates='roles', lazy='dynamic')

    def __repr__(self):
        """
        Returns a string representation of the Role object.
        """
        return f'<Role {self.name}>'


@login.user_loader
def load_user(id_val):
    """
    Loads a user from the database given their ID.
    """
    return User.query.get(int(id_val))

class Team(db.Model):
    """
    Represents a team of users.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    members = db.relationship('User', secondary=user_team_membership, back_populates='teams')
    team_leads = db.relationship('User', secondary=user_team_leadership,
                                 back_populates='teams_as_lead')

    def __repr__(self):
        """
        Returns a string representation of the Team object.
        """
        return f'<Team {self.name}>'

class Species(db.Model):
    """
    Represents a species associated with skills and training.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    skills = db.relationship('Skill', secondary=skill_species_association,
                            back_populates='species')
    training_requests_for_species = db.relationship('TrainingRequest',
                                                    secondary=training_request_species_requested,
                                                    back_populates='species_requested')

    def __repr__(self):
        """
        Returns a string representation of the Species object.
        """
        return f'<Species {self.name}>'

class Skill(db.Model):
    """
    Represents a skill that users can acquire.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, unique=True, nullable=False)
    description = db.Column(db.Text)
    validity_period_months = db.Column(db.Integer, default=12)
    complexity = db.Column(db.Enum(Complexity), default=Complexity.SIMPLE, nullable=False)
    # Stores multiple URLs as text, e.g., comma-separated or JSON string
    reference_urls_text = db.Column(db.Text)
    protocol_attachment_path = db.Column(db.String(256)) # Path to uploaded protocol document
    training_videos_urls_text = db.Column(db.Text) # Stores multiple URLs as text
    potential_external_tutors_text = db.Column(db.Text) # Stores names/contact info as text

    species = db.relationship('Species', secondary=skill_species_association,
                            back_populates='skills')
    tutors = db.relationship('User', secondary=tutor_skill_association,
                            back_populates='tutored_skills')
    competencies = db.relationship('Competency', back_populates='skill', lazy='dynamic')
    training_sessions_covered = db.relationship('TrainingSession',
                                                secondary=training_session_skills_covered,
                                                back_populates='skills_covered')
    training_requests_for_skill = db.relationship('TrainingRequest',
                                                  secondary=training_request_skills_requested,
                                                  back_populates='skills_requested')
    external_training_claims = db.relationship('ExternalTrainingSkillClaim',
                                                back_populates='skill', lazy='dynamic')
    skill_practice_events = db.relationship('SkillPracticeEvent',
                                            secondary=skill_practice_event_skills,
                                            back_populates='skills')

    def __repr__(self):
        """
        Returns a string representation of the Skill object.
        """
        return f'<Skill {self.name}>'

class TrainingPath(db.Model):
    """
    Represents a sequence of skills for user training.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id'), nullable=False)

    species = db.relationship('Species', backref='training_paths') # New relationship

    skills_association = db.relationship('TrainingPathSkill', back_populates='training_path',
                                        cascade="all, delete-orphan",
                                        order_by='TrainingPathSkill.order')

    @property
    def skills(self):
        """
        Returns the list of skills in this training path, in order.
        """
        return [assoc.skill for assoc in self.skills_association]

    assigned_users = db.relationship('User', secondary=training_path_assigned_users,
                                    back_populates='assigned_training_paths')

    def __repr__(self):
        """
        Returns a string representation of the TrainingPath object.
        """
        return f'<TrainingPath {self.name}>'


class TrainingSession(db.Model):
    """
    Represents a scheduled training session.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(128))
    start_time = db.Column(db.DateTime(timezone=True), index=True,
                           default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime(timezone=True), index=True,
                         default=lambda: datetime.now(timezone.utc))
    main_species_id = db.Column(db.Integer, db.ForeignKey('species.id'))
    ethical_authorization_id = db.Column(db.String(64))
    animal_count = db.Column(db.Integer)
    attachment_path = db.Column(db.String(256)) # Path to uploaded attendance sheet or other document
    status = db.Column(db.String(64), default='Pending') # New status field

    main_species = db.relationship('Species', backref='training_sessions')
    attendees = db.relationship('User', secondary=training_session_attendees,
                                back_populates='attended_training_sessions')
    skills_covered = db.relationship('Skill', secondary=training_session_skills_covered,
                                     back_populates='training_sessions_covered')
    competencies = db.relationship('Competency', back_populates='training_session',
                                  lazy='dynamic')
    tutors = db.relationship('User', secondary=training_session_tutors,
                            back_populates='tutored_training_sessions')

    @property
    def associated_species(self):
        """
        Returns a list of unique species associated with the skills covered in this session.
        """
        species_set = set()
        for skill in self.skills_covered:
            species_set.update(skill.species)
        return list(species_set)

    def __repr__(self):
        """
        Returns a string representation of the TrainingSession object.
        """
        return f'<TrainingSession {self.title}>'

competency_species_association = db.Table('competency_species_association',
    db.Column('competency_id', db.Integer, db.ForeignKey('competency.id'), primary_key=True),
    db.Column('species_id', db.Integer, db.ForeignKey('species.id'), primary_key=True)
)

class Competency(db.Model):
    """
    Represents a user's competency in a specific skill.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    level = db.Column(db.String(64)) # e.g., 'Novice', 'Intermediate', 'Expert'
    evaluation_date = db.Column(db.DateTime(timezone=True), index=True,
                               default=lambda: datetime.now(timezone.utc))
    evaluator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    external_evaluator_name = db.Column(db.String(128), nullable=True)
    training_session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'))
    external_training_id = db.Column(db.Integer,
                                     db.ForeignKey('external_training.id',
                                                   name='fk_competency_external_training_id'),
                                     nullable=True)
    certificate_path = db.Column(db.String(256)) # Path to generated certificate

    user = db.relationship('User', back_populates='competencies',
                            foreign_keys=lambda: [Competency.user_id])
    skill = db.relationship('Skill', back_populates='competencies')
    evaluator = db.relationship('User', back_populates='evaluated_competencies',
                                foreign_keys=lambda: [Competency.evaluator_id])
    training_session = db.relationship('TrainingSession', back_populates='competencies')
    external_training = db.relationship('ExternalTraining', backref='competencies')
    species = db.relationship('Species', secondary=competency_species_association,
                            backref='competencies')

    @property
    def latest_practice_date(self):
        """
        Returns the latest practice date for this competency (either evaluation or practice event).
        """
        # Find the most recent practice event for this skill and user
        practice_event = SkillPracticeEvent.query.filter(
            SkillPracticeEvent.user_id == self.user_id,
            SkillPracticeEvent.skills.any(id=self.skill_id)
        ).order_by(SkillPracticeEvent.practice_date.desc()).first()

        evaluation_date = self.evaluation_date
        if evaluation_date.tzinfo is None:
            evaluation_date = evaluation_date.replace(tzinfo=timezone.utc)

        if practice_event and practice_event.practice_date:
            practice_date = practice_event.practice_date
            if practice_date.tzinfo is None:
                practice_date = practice_date.replace(tzinfo=timezone.utc)

            if practice_date > evaluation_date:
                return practice_date

        return evaluation_date

    @property
    def recycling_due_date(self):
        """
        Calculates the recycling due date for the competency.
        """
        if self.skill.validity_period_months:
            # Using 30.44 days as average for a month
            return self.latest_practice_date + \
                timedelta(days=self.skill.validity_period_months * 30.44)
        return None

    @property
    def needs_recycling(self):
        """
        Checks if the competency needs recycling.
        """
        if self.recycling_due_date:
            return datetime.now(timezone.utc) > self.recycling_due_date
        return False

    @property
    def warning_date(self):
        """
        Calculates the warning date before recycling is due.
        """
        if self.recycling_due_date and self.skill.validity_period_months:
            # Warning period is typically 1/4 of the validity period
            return self.recycling_due_date - \
                timedelta(days=self.skill.validity_period_months * 30.44 / 4)
        return None

    def __repr__(self):
        """
        Returns a string representation of the Competency object.
        """
        return f'<Competency {self.user.full_name} - {self.skill.name}>'

class SkillPracticeEvent(db.Model):
    """
    Records an instance of a user practicing a skill.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    practice_date = db.Column(db.DateTime(timezone=True), index=True,
                              default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.Text)

    user = db.relationship('User', back_populates='skill_practice_events')
    skills = db.relationship('Skill', secondary=skill_practice_event_skills,
                            back_populates='skill_practice_events')

    def __repr__(self):
        """
        Returns a string representation of the SkillPracticeEvent object.
        """
        skill_names = ', '.join([s.name for s in self.skills]) if self.skills else 'No Skills'
        return f'<SkillPracticeEvent {self.user.full_name} - {skill_names} on ' \
               f'{self.practice_date.strftime("%Y-%m-%d")}>'

class TrainingRequest(db.Model):
    """
    Represents a user's request for training.
    """
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_date = db.Column(db.DateTime(timezone=True), index=True,
                            default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.Enum(TrainingRequestStatus),
                        default=TrainingRequestStatus.PENDING, nullable=False)
    justification = db.Column(db.Text, nullable=True)
    preferred_date = db.Column(db.DateTime(timezone=True), nullable=True)

    requester = db.relationship('User', back_populates='training_requests')
    skills_requested = db.relationship('Skill', secondary=training_request_skills_requested,
                                        back_populates='training_requests_for_skill')
    species_requested = db.relationship('Species', secondary=training_request_species_requested,
                                        back_populates='training_requests_for_species')

    @property
    def associated_species(self):
        """
        Returns a list of species associated with this training request.
        """
        # If species were explicitly requested, prioritize them.
        if self.species_requested:
            return self.species_requested

        # Fallback for older requests: infer from skills.
        species_set = set()
        for skill in self.skills_requested:
            species_set.update(skill.species)
        return list(species_set)

    def __repr__(self):
        """
        Returns a string representation of the TrainingRequest object.
        """
        return f'<TrainingRequest {self.id} by {self.requester.full_name}>'

class ExternalTraining(db.Model):
    """
    Records external training completed by a user.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    external_trainer_name = db.Column(db.String(128))
    date = db.Column(db.DateTime(timezone=True), index=True,
                     default=lambda: datetime.now(timezone.utc))
    attachment_path = db.Column(db.String(256)) # Path to external certificate/document
    status = db.Column(db.Enum(ExternalTrainingStatus),
                        default=ExternalTrainingStatus.PENDING, nullable=False)
    validator_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship('User', back_populates='external_trainings',
                            foreign_keys=lambda: [ExternalTraining.user_id])
    validator = db.relationship('User', back_populates='validated_external_trainings',
                                foreign_keys=lambda: [ExternalTraining.validator_id])
    skill_claims = db.relationship('ExternalTrainingSkillClaim',
                                    back_populates='external_training', lazy='select',
                                    cascade="all, delete-orphan")

    def __repr__(self):
        """
        Returns a string representation of the ExternalTraining object.
        """
        return f'<ExternalTraining {self.id} by {self.user.full_name}>'

class TrainingSessionTutorSkill(db.Model):
    """
    Associates a tutor with a specific skill within a training session.
    """
    training_session_id = db.Column(db.Integer, db.ForeignKey('training_session.id'),
                                     primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), primary_key=True)

    training_session = db.relationship('TrainingSession',
                                        backref=db.backref('tutor_skill_mappings',
                                                           cascade="all, delete-orphan"))
    tutor = db.relationship('User', backref='training_session_skill_mappings')
    skill = db.relationship('Skill', backref='training_session_tutor_mappings')

    def __repr__(self):
        """
        Returns a string representation of the TrainingSessionTutorSkill object.
        """
        return f'<TrainingSessionTutorSkill Session:{self.training_session_id} ' \
               f'Tutor:{self.tutor_id} Skill:{self.skill_id}>'

# New Models for Regulatory and Continuous Training

class InitialRegulatoryTrainingLevel(enum.Enum):
    """
    Enum for levels of initial regulatory training.
    """
    NIVEAU_1_CONCEPTEUR = 'Niveau 1: Concepteur'
    NIVEAU_2_EXPERIMENTATEUR = 'Niveau 2: Experimentateur'
    NIVEAU_3_SOIGNEUR = 'Niveau 3: Soigneur'

class InitialRegulatoryTraining(db.Model):
    """
    Records a user's initial regulatory training.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    level = db.Column(db.Enum(InitialRegulatoryTrainingLevel), nullable=False)
    training_date = db.Column(db.DateTime(timezone=True), nullable=False)
    attachment_path = db.Column(db.String(256), nullable=True)

    user = db.relationship('User', back_populates='initial_regulatory_training')

    def __repr__(self):
        """
        Returns a string representation of the InitialRegulatoryTraining object.
        """
        return f'<InitialRegulatoryTraining {self.user.full_name} - {self.level.value}>'

class ContinuousTrainingType(enum.Enum):
    """
    Enum for types of continuous training (Online or Presential).
    """
    ONLINE = 'Online'
    PRESENTIAL = 'Presential'

class ContinuousTrainingEventStatus(enum.Enum):
    """
    Enum for the status of a continuous training event.
    """
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'

class ContinuousTrainingEvent(db.Model):
    """
    Represents a continuous training event.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    training_type = db.Column(db.Enum(ContinuousTrainingType), nullable=False)
    location = db.Column(db.String(128), nullable=True)
    event_date = db.Column(db.DateTime(timezone=True), nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    attachment_path = db.Column(db.String(256), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum(ContinuousTrainingEventStatus),
                        default=ContinuousTrainingEventStatus.PENDING, nullable=False)
    validator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    creator = db.relationship('User', foreign_keys=[creator_id],
                            back_populates='created_continuous_training_events')
    validator = db.relationship('User', foreign_keys=[validator_id],
                                back_populates='validated_continuous_training_events')
    user_attendances = db.relationship('UserContinuousTraining', back_populates='event',
                                        lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        """
        Returns a string representation of the ContinuousTrainingEvent object.
        """
        return f'<ContinuousTrainingEvent {self.title} on ' \
               f'{self.event_date.strftime("%Y-%m-%d")}>'

class UserContinuousTrainingStatus(enum.Enum):
    """
    Enum for the status of a user's attendance at a continuous training event.
    """
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'

class UserContinuousTraining(db.Model):
    """
    Records a user's attendance and validation for a continuous training event.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('continuous_training_event.id'),
                         nullable=False)
    attendance_attachment_path = db.Column(db.String(256), nullable=True)
    status = db.Column(db.Enum(UserContinuousTrainingStatus),
                        default=UserContinuousTrainingStatus.PENDING, nullable=False)
    validated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    validation_date = db.Column(db.DateTime(timezone=True), nullable=True)
    validated_hours = db.Column(db.Float, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id],
                            back_populates='continuous_trainings_attended')
    event = db.relationship('ContinuousTrainingEvent', back_populates='user_attendances')
    validated_by = db.relationship('User', foreign_keys=[validated_by_id],
                                    back_populates='validated_user_continuous_trainings')

    def __repr__(self):
        """
        Returns a string representation of the UserContinuousTraining object.
        """
        return f'<UserContinuousTraining {self.user.full_name} - {self.event.title} - ' \
               f'{self.status.value}>'

class UserDismissedNotification(db.Model):
    """
    Records notifications dismissed by a user.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(128), nullable=False)
    notification_url = db.Column(db.String(512), nullable=True)
    dismissed_at = db.Column(db.DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('dismissed_notifications', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'notification_type',
                                         name='_user_notification_uc'),)

    def __repr__(self):
        """
        Returns a string representation of the UserDismissedNotification object.
        """
        return f'<UserDismissedNotification User:{self.user_id} Type:{self.notification_type}>'
