from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectMultipleField, TextAreaField, StringField, DateTimeLocalField, SelectField, BooleanField, FieldList, FormField
from wtforms.validators import DataRequired, Optional, Length
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from app.models import Skill, User, Species, ExternalTrainingSkillClaim # Added ExternalTrainingSkillClaim

def get_skills():
    return Skill.query.order_by(Skill.name).all()

def get_species():
    return Species.query.order_by(Species.name).all()

def get_users():
    return User.query.order_by(User.full_name).all()

class TrainingRequestForm(FlaskForm):
    species = QuerySelectField('Species', query_factory=get_species, get_label='name', validators=[DataRequired()])
    skills_requested = QuerySelectMultipleField('Skills Requested', query_factory=get_skills, get_label='name', validators=[DataRequired()])
    submit = SubmitField('Submit Training Request')

class ExternalTrainingSkillClaimForm(FlaskForm):
    skill = QuerySelectField('Skill', query_factory=get_skills, get_label='name', validators=[DataRequired()])
    level = SelectField('Competency Level', choices=[('Novice', 'Novice'), ('Intermediate', 'Intermediate'), ('Expert', 'Expert')], validators=[DataRequired()])
    species_claimed = QuerySelectMultipleField('Species Claimed', query_factory=get_species, get_label='name', validators=[DataRequired()])
    wants_to_be_tutor = BooleanField('Want to be tutor ?')
    practice_date = DateTimeLocalField('Date of Latest Practice', format='%Y-%m-%dT%H:%M', validators=[Optional()])

class ExternalTrainingForm(FlaskForm):
    external_trainer_name = StringField('External Trainer Name', validators=[DataRequired()])
    date = DateTimeLocalField('Date of Training', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    skill_claims = FieldList(FormField(ExternalTrainingSkillClaimForm), min_entries=1, label='Skills Claimed')
    attachment = FileField('Certificate/Document Attachment', validators=[FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'PDF, DOCX, Images only!')])
    submit = SubmitField('Submit External Training')



class ProposeSkillForm(FlaskForm):
    name = StringField('Nom de la Compétence', validators=[DataRequired(), Length(min=2, max=128)])
    description = TextAreaField('Description (optionnel)', validators=[Optional()], render_kw={"rows": 3})
    submit = SubmitField('Proposer la Compétence')
