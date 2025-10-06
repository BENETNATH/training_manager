import pytest
from app import db
from app.models import User, Team, Species, Skill, TrainingPath, TrainingSession, Competency, SkillPracticeEvent, TrainingRequest, ExternalTraining, Complexity, TrainingRequestStatus, ExternalTrainingStatus
from datetime import datetime, timedelta

def test_user_creation(app):
    with app.app_context():
        u = User(full_name='John Doe', email='john@example.com')
        u.set_password('password')
        db.session.add(u)
        db.session.commit()
        assert u.id is not None
        assert u.check_password('password')
        assert not u.check_password('wrongpassword')

def test_user_team_relationship(app):
    with app.app_context():
        t = Team(name='Development')
        u = User(full_name='Jane Doe', email='jane@example.com')
        u.set_password('password')
        u.teams.append(t)
        db.session.add(t)
        db.session.add(u)
        db.session.commit()
        assert u.teams[0].name == 'Development'

def test_user_api_key_generation(app):
    with app.app_context():
        u = User(full_name='API User', email='api@example.com')
        u.set_password('apipassword')
        db.session.add(u)
        db.session.commit()
        assert u.api_key is not None
        old_key = u.api_key
        u.generate_api_key()
        db.session.commit()
        assert u.api_key != old_key

def test_skill_complexity_enum(app):
    with app.app_context():
        s = Skill(name='Complex Skill', complexity=Complexity.COMPLEX)
        db.session.add(s)
        db.session.commit()
        retrieved_skill = Skill.query.filter_by(name='Complex Skill').first()
        assert retrieved_skill.complexity == Complexity.COMPLEX

def test_training_request_status_enum(app):
    with app.app_context():
        u = User(full_name='Request User', email='request@example.com')
        u.set_password('password')
        tr = TrainingRequest(requester=u, status=TrainingRequestStatus.APPROVED)
        db.session.add(u)
        db.session.add(tr)
        db.session.commit()
        retrieved_tr = TrainingRequest.query.first()
        assert retrieved_tr.status == TrainingRequestStatus.APPROVED