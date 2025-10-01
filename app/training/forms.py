from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from app.models import User, Skill, TrainingRequest, tutor_skill_association # Added tutor_skill_association
from sqlalchemy import or_ # Added this import

def get_users():
    return User.query.order_by(User.full_name).all()

class TrainingSessionForm(FlaskForm):
    title = StringField('Session Title', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    start_time = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    ethical_authorization_id = StringField('Ethical Authorization ID', validators=[Optional()])
    animal_count = IntegerField('Animal Count', validators=[Optional(), NumberRange(min=0)])
    attachment = FileField('Attachment (e.g., Attendance Sheet)', validators=[FileAllowed(['pdf', 'doc', 'docx', 'xlsx', 'csv'], 'PDF, DOCX, XLSX, CSV only!')])
    attendees = QuerySelectMultipleField('Attendees', query_factory=get_users, get_label='full_name', validators=[DataRequired()])
    send_email_reminders = BooleanField('Send Email Reminders to Attendees')
    submit = SubmitField('Create Training Session')

    def validate_end_time(self, field):
        if field.data <= self.start_time.data:
            raise ValidationError('L\'heure de fin doit être postérieure à l\'heure de début.')
