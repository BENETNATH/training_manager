from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from app.models import User, Skill, TrainingRequest, tutor_skill_association, Species # Added tutor_skill_association, Species
from sqlalchemy import or_ # Added this import
from flask_babel import lazy_gettext as _

def get_users():
    return User.query.order_by(User.full_name).all()

def get_skills():
    return Skill.query.order_by(Skill.name).all()

def get_species():
    return Species.query.order_by(Species.name).all()

class TrainingSessionForm(FlaskForm):
    title = StringField('Session Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    start_time = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    main_species = QuerySelectField('Main Species', query_factory=get_species, get_label='name', allow_blank=True, blank_text='-- Select Main Species --', validators=[Optional()]) # Added this field
    ethical_authorization_id = StringField('Ethical Authorization ID', validators=[Optional()])
    animal_count = IntegerField('Animal Count', validators=[Optional(), NumberRange(min=0)])
    attachment = FileField('Attachment (e.g., Attendance Sheet)', validators=[FileAllowed(['pdf', 'doc', 'docx', 'xlsx', 'csv'], 'PDF, DOCX, XLSX, CSV only!')])
    attendees = QuerySelectMultipleField('Attendees', query_factory=get_users, get_label='full_name', validators=[DataRequired()])
    skills_covered = QuerySelectMultipleField('Skills Covered', query_factory=get_skills, get_label='name', validators=[Optional()])
    send_email_reminders = BooleanField('Send Email Reminders to Attendees')
    submit = SubmitField('Create Training Session')

    def validate_end_time(self, field):
        if field.data <= self.start_time.data:
            raise ValidationError(_('End time must be after start time.'))
