import pytest
from app import db
from app.models import User, Team, Skill, Species, Complexity
from datetime import datetime, timedelta

def test_user_password(app):
    with app.app_context():
        u = User(full_name='John Doe', email='john@example.com')
        u.set_password('cat')
        assert not u.check_password('dog')
        assert u.check_password('cat')

def test_user_team_relationship(app):
    with app.app_context():
        t = Team(name='Development')
        u = User(full_name='Jane Doe', email='jane@example.com', team=t)
        u.set_password('testpassword') # Set a password for the user
        db.session.add(t)
        db.session.add(u)
        db.session.commit()
        assert u.team.name == 'Development'
        assert t.members.count() == 1
        assert t.members.first().full_name == 'Jane Doe'

def test_user_api_key_generation(app):
    with app.app_context():
        u = User(full_name='API User', email='api@example.com')
        u.set_password('apipassword')
        db.session.add(u)
        db.session.commit()
        assert u.api_key is None # Should be None initially

        u.generate_api_key()
        assert u.api_key is not None
        assert len(u.api_key) == 64 # 32 bytes * 2 (hex)

def test_skill_creation(app):
    with app.app_context():
        s = Skill(name='Python Programming', description='Basic Python skills',
                  validity_period_months=24, complexity=Complexity.COMPLEX)
        db.session.add(s)
        db.session.commit()
        assert s.name == 'Python Programming'
        assert s.complexity == Complexity.COMPLEX

def test_skill_species_relationship(app):
    with app.app_context():
        s1 = Species(name='Canine')
        s2 = Species(name='Feline')
        db.session.add_all([s1, s2])
        db.session.commit()

        skill = Skill(name='Animal Handling', complexity=Complexity.SIMPLE)
        skill.species.append(s1)
        skill.species.append(s2)
        db.session.add(skill)
        db.session.commit()

        assert len(skill.species) == 2
        assert s1 in skill.species
        assert s2 in skill.species
        assert skill in s1.skills
        assert skill in s2.skills
