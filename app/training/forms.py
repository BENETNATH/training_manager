from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from app.models import User, Skill, TrainingRequest, tutor_skill_association # Added tutor_skill_association
from sqlalchemy import or_ # Added this import

def get_tutors():
    # Filter for users who have tutored skills
    # This implicitly means they are associated with at least one skill as a tutor
    return User.query.join(tutor_skill_association).group_by(User.id).order_by(User.full_name).all()

def get_skills():
    return Skill.query.order_by(Skill.name).all()

def get_users():
    return User.query.order_by(User.full_name).all()

class TrainingSessionForm(FlaskForm):
    title = StringField('Session Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    start_time = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    tutor = QuerySelectField('Tutor', query_factory=get_tutors, allow_blank=True, get_label='full_name', validators=[Optional()])
    ethical_authorization_id = StringField('Ethical Authorization ID', validators=[Optional()])
    animal_count = IntegerField('Animal Count', validators=[Optional(), NumberRange(min=0)])
    attachment = FileField('Attachment (e.g., Attendance Sheet)', validators=[FileAllowed(['pdf', 'doc', 'docx', 'xlsx', 'csv'], 'PDF, DOCX, XLSX, CSV only!')])
    attendees = QuerySelectMultipleField('Attendees', query_factory=get_users, get_label='full_name', validators=[DataRequired()])
    skills_covered = QuerySelectMultipleField('Skills Covered', query_factory=get_skills, get_label='name', validators=[DataRequired()])
    send_email_reminders = BooleanField('Send Email Reminders to Attendees')
    submit = SubmitField('Create Training Session')
