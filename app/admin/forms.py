from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, ValidationError, Email, Length, Optional
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from flask_wtf.file import FileField, FileAllowed
from app.models import User, Team, Species, Skill, Complexity, TrainingPath
from wtforms import FieldList, FormField
from app import db

def get_teams():
    return Team.query.order_by(Team.name).all()

def get_users():
    return User.query.order_by(User.full_name).all()

def get_species():
    return Species.query.order_by(Species.name).all()

def get_training_paths_with_species():
    return TrainingPath.query.options(db.joinedload(TrainingPath.species)).order_by(TrainingPath.name).all()

def get_training_path_label(training_path):
    return f"{training_path.name} ({training_path.species.name})"

class UserForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    is_admin = BooleanField('Is Admin')
    teams = QuerySelectMultipleField('Teams', query_factory=get_teams, get_label='name')
    teams_as_lead = QuerySelectMultipleField('Led Teams', query_factory=get_teams, get_label='name')
    assigned_training_paths = QuerySelectMultipleField('Assign Training Paths', query_factory=get_training_paths_with_species, get_label=get_training_path_label)
    submit = SubmitField('Save User')

    def __init__(self, original_email=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please use a different email address.')

class TeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired(), Length(min=2, max=64)])
    members = QuerySelectMultipleField('Members', query_factory=get_users, get_label='full_name')
    team_leads = QuerySelectMultipleField('Team Leads', query_factory=get_users, get_label='full_name')
    submit = SubmitField('Save Team')

    def __init__(self, original_name=None, *args, **kwargs):
        super(TeamForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            team = Team.query.filter_by(name=self.name.data).first()
            if team:
                raise ValidationError('That team name is already in use. Please choose a different name.')

class SpeciesForm(FlaskForm):
    name = StringField('Species Name', validators=[DataRequired(), Length(min=2, max=64)])
    submit = SubmitField('Save Species')

    def __init__(self, original_name=None, *args, **kwargs):
        super(SpeciesForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            species = Species.query.filter_by(name=self.name.data).first()
            if species:
                raise ValidationError('That species name is already in use. Please choose a different name.')

class SkillForm(FlaskForm):
    name = StringField('Skill Name', validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField('Description', validators=[Optional()])
    validity_period_months = IntegerField('Validity Period (Months)', validators=[Optional()])
    complexity = SelectField('Complexity', choices=[(c.name, c.value) for c in Complexity], validators=[DataRequired()])
    reference_urls_text = TextAreaField('Reference URLs (comma-separated)', validators=[Optional()])
    protocol_attachment = FileField('Protocol Attachment', validators=[FileAllowed(['pdf', 'doc', 'docx'], 'PDF, DOC, DOCX only!')])
    training_videos_urls_text = TextAreaField('Training Videos URLs (comma-separated)', validators=[Optional()])
    potential_external_tutors_text = TextAreaField('Potential External Tutors (comma-separated)', validators=[Optional()])
    species = QuerySelectMultipleField('Associated Species', query_factory=get_species, get_label='name')

    submit = SubmitField('Save Skill')

    def __init__(self, original_name=None, *args, **kwargs):
        super(SkillForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            skill = Skill.query.filter_by(name=self.name.data).first()
            if skill:
                raise ValidationError('That skill name is already in use. Please choose a different name.')

class TrainingPathForm(FlaskForm):
    name = StringField('Training Path Name', validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField('Description', validators=[Optional()])
    species = QuerySelectField('Associated Species', query_factory=get_species, get_label='name', validators=[DataRequired()])
    skills_json = HiddenField('Skills JSON', validators=[DataRequired()])
    submit = SubmitField('Save Training Path')

    def __init__(self, original_name=None, *args, **kwargs):
        super(TrainingPathForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            path = TrainingPath.query.filter_by(name=self.name.data).first()
            if path:
                raise ValidationError('That training path name is already in use. Please choose a different name.')

class ImportForm(FlaskForm):
    import_file = FileField('Select File', validators=[DataRequired(), FileAllowed(['xlsx'], 'XLSX files only!')])
    update_existing = BooleanField('Update existing skills if names match?', default=False)
    submit = SubmitField('Import')

class AddUserToTeamForm(FlaskForm):
    users = QuerySelectMultipleField('Select Users', query_factory=get_users, get_label='full_name')
    submit = SubmitField('Add Users to Team')

class CompetencyValidationForm(FlaskForm):
    skill_id = HiddenField()
    skill_name_display = HiddenField() # Added for displaying skill name in template
    acquired = BooleanField('Acquired')
    level = SelectField('Level', choices=[('Novice', 'Novice'), ('Intermediate', 'Intermediate'), ('Expert', 'Expert')], validators=[Optional()])

class AttendeeValidationForm(FlaskForm):
    user_label = HiddenField()
    full_name_display = HiddenField() # Added for displaying full name in template
    competencies = FieldList(FormField(CompetencyValidationForm))

class TrainingValidationForm(FlaskForm):
    attendees = FieldList(FormField(AttendeeValidationForm))
    submit = SubmitField('Validate Competencies')
