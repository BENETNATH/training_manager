from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from app.models import User, Skill, TrainingRequest

def get_tutors():
    # This will be dynamically updated by JS, but needs a default for initial load
    return User.query.order_by(User.full_name).all()

def get_skills():
    return Skill.query.order_by(Skill.name).all()

def get_users():
    return User.query.order_by(User.full_name).all()

class TrainingSessionForm(FlaskForm):
    title = StringField('Session Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    start_time = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    tutor = QuerySelectField('Tutor', query_factory=get_tutors, allow_blank=True, get_label='full_name', validators=[DataRequired()])
    ethical_authorization_id = StringField('Ethical Authorization ID', validators=[Optional()])
    animal_count = IntegerField('Animal Count', validators=[Optional(), NumberRange(min=0)])
    attachment = FileField('Attachment (e.g., Attendance Sheet)', validators=[FileAllowed(['pdf', 'doc', 'docx', 'xlsx', 'csv'], 'PDF, DOCX, XLSX, CSV only!')])
    attendees = QuerySelectMultipleField('Attendees', query_factory=get_users, get_label='full_name', validators=[DataRequired()])
    skills_covered = QuerySelectMultipleField('Skills Covered', query_factory=get_skills, get_label='name', validators=[DataRequired()])
    send_email_reminders = BooleanField('Send Email Reminders to Attendees')
    submit = SubmitField('Create Training Session')

    def validate_tutor(self, field):
        selected_skills = self.skills_covered.data
        selected_tutor = field.data

        if selected_skills and not selected_tutor:
            raise ValidationError('A tutor is required when skills are selected.')
        
        if selected_skills and selected_tutor:
            # Check if the selected tutor can teach ALL selected skills
            for skill in selected_skills:
                if skill not in selected_tutor.tutored_skills:
                    raise ValidationError(f'The selected tutor cannot teach skill: {skill.name}.')
