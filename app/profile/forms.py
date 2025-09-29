from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectMultipleField, TextAreaField, StringField, DateTimeLocalField
from wtforms.validators import DataRequired, Optional, Length
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from app.models import Skill, User, Species

def get_skills():
    return Skill.query.order_by(Skill.name).all()

def get_species():
    return Species.query.order_by(Species.name).all()

def get_users():
    return User.query.order_by(User.full_name).all()

class TrainingRequestForm(FlaskForm):
    skills_requested = QuerySelectMultipleField('Skills Requested', query_factory=get_skills,
                                                get_label='name', validators=[DataRequired()])
    species_requested = QuerySelectMultipleField('Species Requested', query_factory=get_species,
                                                 get_label='name', validators=[Optional()])
    justification = TextAreaField('Justification', render_kw={"rows": 5})
    submit = SubmitField('Submit Training Request')

class ExternalTrainingForm(FlaskForm):
    external_trainer_name = StringField('External Trainer Name', validators=[DataRequired()])
    date = DateTimeLocalField('Date of Training', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    skills_claimed = QuerySelectMultipleField('Skills Claimed', query_factory=get_skills,
                                              get_label='name', validators=[DataRequired()])
    attachment = FileField('Certificate/Document Attachment', validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'PDF, DOCX, Images only!')])
    submit = SubmitField('Submit External Training')

class SkillPracticeEventForm(FlaskForm):
    skills = QuerySelectMultipleField('Compétences Pratiquées', query_factory=get_skills,
                             get_label='name', validators=[DataRequired()])
    practice_date = DateTimeLocalField('Date de Pratique', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()], render_kw={"rows": 3})
    submit = SubmitField('Déclarer Pratique')

class ProposeSkillForm(FlaskForm):
    name = StringField('Nom de la Compétence', validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField('Description (optionnel)', validators=[Optional()], render_kw={"rows": 3})
    submit = SubmitField('Proposer la Compétence')
