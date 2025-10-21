"""Admin forms for managing users, teams, species, skills, training paths, roles, permissions, and continuous training events."""

# Standard library imports

# Third-party imports
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField, SelectField,
    TextAreaField, IntegerField, HiddenField, DateTimeLocalField, FloatField
)
from wtforms.validators import DataRequired, ValidationError, Email, Length, Optional, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms import FieldList, FormField

# First-party imports
from app import db
from app.models import (
    User, Team, Species, Skill, Complexity, TrainingPath, Role, Permission,
    ContinuousTrainingType, InitialRegulatoryTrainingLevel, UserContinuousTrainingStatus
)

def get_teams():
    """Returns a list of all teams, ordered by name."""
    return Team.query.order_by(Team.name).all()

def get_users():
    """Returns a list of all users, ordered by full name."""
    return User.query.order_by(User.full_name).all()

def get_species():
    """Returns a list of all species, ordered by name."""
    return Species.query.order_by(Species.name).all()

def get_skills():
    """Returns a list of all skills, ordered by name."""
    return Skill.query.order_by(Skill.name).all()

def get_roles():
    """Returns a list of all roles, ordered by name."""
    return Role.query.order_by(Role.name).all()

def get_permissions():
    """Returns a list of all permissions, ordered by name."""
    return Permission.query.order_by(Permission.name).all()

def get_training_paths_with_species():
    """Returns a list of all training paths with their associated species, ordered by name."""
    return TrainingPath.query.options(db.joinedload(TrainingPath.species)).order_by(TrainingPath.name).all()

def get_training_path_label(training_path):
    """Returns a formatted label for a training path, including its associated species."""
    return f"{training_path.name} ({training_path.species.name})"

class UserForm(FlaskForm):
    """Form for creating and editing users."""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    is_admin = BooleanField('Is Admin')
    study_level = SelectField('Study Level',
                              choices=[('pre-BAC', 'pre-BAC')] +
                                      [(str(i), str(i)) for i in range(9)] +
                                      [('8+', '8+')],
                              validators=[Optional()])
    teams = QuerySelectMultipleField('Teams', query_factory=get_teams, get_label='name')
    teams_as_lead = QuerySelectMultipleField('Led Teams', query_factory=get_teams, get_label='name')
    assigned_training_paths = QuerySelectMultipleField('Assign Training Paths', query_factory=get_training_paths_with_species, get_label=get_training_path_label)
    roles = QuerySelectMultipleField('Roles', query_factory=get_roles, get_label='name')
    submit = SubmitField('Save User')

    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        """Validates that the email address is not already registered."""
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please use a different email address.')

class TeamForm(FlaskForm):
    """Form for creating and editing teams."""
    name = StringField('Team Name', validators=[DataRequired(), Length(min=2, max=64)])
    members = QuerySelectMultipleField('Members', query_factory=get_users, get_label='full_name')
    team_leads = QuerySelectMultipleField('Team Leads', query_factory=get_users, get_label='full_name')
    submit = SubmitField('Save Team')

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        """Validates that the team name is not already in use."""
        if name.data != self.original_name:
            team = Team.query.filter_by(name=self.name.data).first()
            if team:
                raise ValidationError('That team name is already in use. Please choose a different name.')

class SpeciesForm(FlaskForm):
    """Form for creating and editing species."""
    name = StringField('Species Name', validators=[DataRequired(), Length(min=2, max=64)])
    submit = SubmitField('Save Species')

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        """Validates that the species name is not already in use."""
        if name.data != self.original_name:
            species = Species.query.filter_by(name=self.name.data).first()
            if species:
                raise ValidationError('That species name is already in use. Please choose a different name.')

class SkillForm(FlaskForm):
    """Form for creating and editing skills."""
    name = StringField('Skill Name', validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField('Description', validators=[Optional()])
    validity_period_months = IntegerField('Validity Period (Months)', validators=[Optional(), NumberRange(min=1)])
    complexity = SelectField('Complexity', choices=[(c.name, c.value) for c in Complexity], validators=[DataRequired()])
    reference_urls_text = TextAreaField('Reference URLs (comma-separated)', validators=[Optional()])
    protocol_attachment = FileField('Protocol Attachment',
                                    validators=[FileAllowed(['pdf', 'doc', 'docx'],
                                                            'PDF, DOC, DOCX only!')])
    training_videos_urls_text = TextAreaField('Training Videos URLs (comma-separated)',
                                              validators=[Optional()])
    potential_external_tutors_text = TextAreaField('Potential External Tutors (comma-separated)',
                                                   validators=[Optional()])
    species = QuerySelectMultipleField('Associated Species', query_factory=get_species,
                                       get_label='name')
    submit = SubmitField('Save Skill')

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        """Validates that the skill name is not already in use."""
        if name.data != self.original_name:
            skill = Skill.query.filter_by(name=self.name.data).first()
            if skill:
                raise ValidationError('That skill name is already in use. Please choose a different name.')

class TrainingPathForm(FlaskForm):
    """Form for creating and editing training paths."""
    name = StringField('Training Path Name', validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField('Description', validators=[Optional()])
    species = QuerySelectField('Associated Species', query_factory=get_species,
                               get_label='name', validators=[DataRequired()])
    skills_json = HiddenField('Skills JSON', validators=[DataRequired()])
    submit = SubmitField('Save Training Path')

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        """Validates that the training path name is not already in use."""
        if name.data != self.original_name:
            path = TrainingPath.query.filter_by(name=self.name.data).first()
            if path:
                raise ValidationError('That training path name is already in use. Please choose a different name.')

class ImportForm(FlaskForm):
    """Form for importing data from Excel files."""
    import_file = FileField('Select File',
                            validators=[DataRequired(), FileAllowed(['xlsx'], 'XLSX files only!')])
    update_existing = BooleanField('Update existing records if names/emails match?',
                                   default=False)
    submit = SubmitField('Import')

class AddUserToTeamForm(FlaskForm):
    """Form for adding users to a team."""
    users = QuerySelectMultipleField('Select Users', query_factory=get_users,
                                     get_label='full_name', allow_blank=False,
                                     validators=[DataRequired()])
    submit = SubmitField('Add Users to Team')

class CompetencyValidationForm(FlaskForm):
    """Subform for validating a single competency."""
    skill_id = HiddenField()
    skill_name_display = HiddenField() # Added for displaying skill name in template
    acquired = BooleanField('Acquired')
    level = SelectField('Level',
                        choices=[('Novice', 'Novice'), ('Intermediate', 'Intermediate'),
                                 ('Expert', 'Expert')],
                        validators=[Optional()])

class AttendeeValidationForm(FlaskForm):
    """Subform for validating competencies for a single attendee."""
    user_label = HiddenField()
    full_name_display = HiddenField() # Added for displaying full name in template
    competencies = FieldList(FormField(CompetencyValidationForm))

class TrainingValidationForm(FlaskForm):
    """Form for validating competencies after a training session."""
    attendees = FieldList(FormField(AttendeeValidationForm))
    submit = SubmitField('Validate Competencies')

class RoleForm(FlaskForm):
    """Form for creating and editing roles."""
    name = StringField('Role Name', validators=[DataRequired(), Length(min=2, max=64)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Role')

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        """Validates that the role name is not already taken."""
        if name.data != self.original_name:
            role = Role.query.filter_by(name=self.name.data).first()
            if role:
                raise ValidationError('That role name is already taken. Please choose a different one.')

class PermissionForm(FlaskForm):
    """Form for creating and editing permissions."""
    name = StringField('Permission Name', validators=[DataRequired(), Length(min=2, max=64)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Permission')

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        """Validates that the permission name is not already taken."""
        if name.data != self.original_name:
            permission = Permission.query.filter_by(name=self.name.data).first()
            if permission:
                raise ValidationError('That permission name is already taken. Please choose a different one.')

class AdminInitialRegulatoryTrainingForm(FlaskForm):
    """Form for administering initial regulatory training records."""
    user = QuerySelectField('Utilisateur', query_factory=get_users,
                            get_label='full_name', validators=[DataRequired()])
    level = SelectField('Niveau de Formation Réglementaire Initiale',
                        choices=[(level.name, level.value) for level in InitialRegulatoryTrainingLevel],
                        validators=[DataRequired()])
    training_date = DateTimeLocalField('Date de la Formation', format='%Y-%m-%dT%H:%M',
                                       validators=[DataRequired()])
    attachment = FileField('Attestation de Formation (PDF, DOCX, Images)',
                           validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
                                                   'PDF, DOCX, Images only!')])
    submit = SubmitField('Enregistrer la Formation Initiale')

class ContinuousTrainingEventForm(FlaskForm):
    """Form for creating and editing continuous training events."""
    title = StringField("Titre de l'événement",
                        validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField('Description', validators=[Optional()])
    training_type = SelectField('Type de Formation',
                                choices=[(t.name, t.value) for t in ContinuousTrainingType],
                                validators=[DataRequired()])
    location = StringField("Lieu (si présentiel)", validators=[Optional(), Length(max=128)])
    event_date = DateTimeLocalField("Date et Heure de l'événement",
                                    format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    duration_hours = FloatField('Durée (heures)', validators=[DataRequired(), NumberRange(min=0)])
    attachment = FileField('Programme/Document (PDF, DOCX, Images)',
                           validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'],
                                                   'PDF, DOCX, Images only!'), Optional()])
    submit = SubmitField("Enregistrer l'événement")

class ValidateUserContinuousTrainingEntryForm(FlaskForm):
    """Subform for validating a single user's continuous training entry."""
    user_ct_id = HiddenField()
    user_full_name = StringField('Utilisateur', render_kw={'readonly': True})
    event_title = StringField('Événement', render_kw={'readonly': True})
    event_date = StringField("Date de l'événement", render_kw={'readonly': True})
    attendance_attachment_path = HiddenField()
    validated_hours = FloatField('Heures Validées',
                                 validators=[DataRequired(), NumberRange(min=0)])
    status = SelectField('Statut',
                         choices=[(s.name, s.value) for s in UserContinuousTrainingStatus],
                         validators=[DataRequired()])
    submit = SubmitField('Valider')

class BatchValidateUserContinuousTrainingForm(FlaskForm):
    """Form for batch validating continuous training entries."""
    entries = FieldList(FormField(ValidateUserContinuousTrainingEntryForm))
    submit_batch = SubmitField('Valider la Sélection')