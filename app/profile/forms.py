from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectMultipleField, TextAreaField, StringField, DateTimeLocalField, SelectField, BooleanField, FieldList, FormField, PasswordField, FloatField # Added PasswordField, StringField, SelectField, SubmitField, FloatField
from wtforms.validators import DataRequired, Optional, Length, EqualTo, Email, ValidationError # Added EqualTo, Email, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from app.models import Skill, User, Species, ExternalTrainingSkillClaim, InitialRegulatoryTrainingLevel, ContinuousTrainingEvent, ContinuousTrainingType # Added new models and enums, including ContinuousTrainingType
from flask_babel import lazy_gettext as _

# ... existing form definitions ...

class RequestContinuousTrainingEventForm(FlaskForm):
    title = StringField(_('Event Title'), validators=[DataRequired(), Length(min=2, max=255)])
    location = StringField(_('Location'), validators=[Optional(), Length(max=255)])
    training_type = SelectField(_('Training Type'), choices=[(tag.name, tag.value) for tag in ContinuousTrainingType], validators=[DataRequired()])
    event_date = DateTimeLocalField(_('Event Date'), format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    attachment = FileField(_('Program (PDF, DOCX, Images)'), validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'PDF, DOCX, Images only!'), Optional()])
    notes = TextAreaField(_('Additional Notes'), validators=[Optional()], render_kw={"rows": 3})
    submit = SubmitField(_('Submit Event Request'))

def get_skills():
    return Skill.query.order_by(Skill.name).all()

def get_species():
    return Species.query.order_by(Species.name).all()

def get_users():
    return User.query.order_by(User.full_name).all()

def get_continuous_training_events():
    return ContinuousTrainingEvent.query.order_by(ContinuousTrainingEvent.event_date.desc()).all()

class TrainingRequestForm(FlaskForm):
    species = QuerySelectField('Species', 
                               query_factory=get_species, 
                               get_label='name', 
                               allow_blank=True, 
                               blank_text='-- Select a Species --', 
                               validators=[DataRequired()])
    skills_requested = QuerySelectMultipleField('Skills Requested', query_factory=get_skills, get_label='name', validators=[DataRequired()])
    justification = TextAreaField('Justification', validators=[DataRequired(), Length(min=10, max=500)], render_kw={"rows": 3})
    preferred_date = DateTimeLocalField('Preferred Date (Optional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    submit = SubmitField('Submit Training Request')

class SingleInitialRegulatoryTrainingForm(FlaskForm):
    training_type = StringField(_('Initial Training Type'), validators=[DataRequired(), Length(min=2, max=128)])
    level = SelectField(_('Initial Regulatory Training Level'), choices=[(level.name, level.value) for level in InitialRegulatoryTrainingLevel], validators=[DataRequired()])
    training_date = DateTimeLocalField(_('Training Date'), format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    attachment = FileField(_('Training Certificate (PDF, DOCX, Images)'), validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'PDF, DOCX, Images only!'), DataRequired()])
    submit = SubmitField(_('Submit'))

class InitialRegulatoryTrainingsForm(FlaskForm):
    initial_trainings = FieldList(FormField(SingleInitialRegulatoryTrainingForm), min_entries=0, label='Initial Regulatory Trainings')
    submit = SubmitField('Save Initial Trainings')

class SubmitContinuousTrainingAttendanceForm(FlaskForm):
    event = SelectField(_('Continuous Training Event'), validators=[DataRequired()])
    attendance_attachment = FileField(_('Attendance Certificate (PDF, DOCX, Images)'), validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'PDF, DOCX, Images only!')])
    submit = SubmitField(_('Declare my Presence'))

class ExternalTrainingSkillClaimForm(FlaskForm):
    skill = QuerySelectField('Skill', query_factory=get_skills, get_label='name', validators=[DataRequired()])
    level = SelectField('Competency Level', choices=[('Novice', 'Novice'), ('Intermediate', 'Intermediate'), ('Expert', 'Expert')], validators=[DataRequired()])
    species_claimed = QuerySelectMultipleField('Species Claimed', query_factory=get_species, get_label='name', validators=[DataRequired()])
    wants_to_be_tutor = BooleanField('Want to be tutor ?')
    practice_date = DateTimeLocalField('Date of Latest Practice', format='%Y-%m-%dT%H:%M', validators=[Optional()])

class ExternalTrainingForm(FlaskForm):
    external_trainer_name = StringField('External Trainer Name', validators=[DataRequired()])
    date = DateTimeLocalField('Date of Training', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    duration_hours = FloatField('Duration (hours)', validators=[DataRequired()])
    skill_claims = FieldList(FormField(ExternalTrainingSkillClaimForm), min_entries=1, label='Skills Claimed')
    attachment = FileField('Certificate/Document Attachment', validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'PDF, DOCX, Images only!')])
    submit = SubmitField('Submit External Training')

    def validate_skill_claims(self, field):
        seen_skills = set()
        for skill_claim_form in field.entries:
            if skill_claim_form.form.skill.data:
                skill_id = skill_claim_form.form.skill.data.id
                if skill_id in seen_skills:
                    raise ValidationError('Duplicate skill claims are not allowed.')
                seen_skills.add(skill_id)

class EditProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    study_level = SelectField('Study Level', choices=[('pre-BAC', 'pre-BAC')] + [(str(i), str(i)) for i in range(9)] + [('8+', '8+')], validators=[Optional()])
    
    # For email change
    new_email = StringField('New Email', validators=[Optional(), Email()])

    # For password change
    current_password = PasswordField('Current Password', validators=[Optional()])
    password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    password2 = PasswordField(
        'Repeat New Password', validators=[Optional(), EqualTo('password', message='Passwords must match.')])

    initial_regulatory_trainings = FieldList(FormField(SingleInitialRegulatoryTrainingForm), min_entries=0, label='Initial Regulatory Trainings')

    submit = SubmitField('Save Changes')

    def __init__(self, original_email=None, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_new_email(self, new_email):
        if new_email.data and new_email.data != self.original_email:
            user = User.query.filter_by(email=new_email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please use a different email address.')

    def validate_current_password(self, current_password):
        # Only validate current password if a new password is provided
        if self.password.data and not current_password.data:
            raise ValidationError('Please enter your current password to change it.')
        # If current password is provided, but no new password, it's also an error
        if current_password.data and not self.password.data:
            raise ValidationError('Please enter a new password if you provide your current password.')

class ProposeSkillForm(FlaskForm):
    name = StringField(_('Skill Name'), validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField(_('Description (optional)'), validators=[Optional()], render_kw={"rows": 3})
    submit = SubmitField(_('Propose Skill'))