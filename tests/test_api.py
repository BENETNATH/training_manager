import pytest
from app import db
from app.models import User, Team, Species, Skill, TrainingPath, TrainingSession, Competency, SkillPracticeEvent, TrainingRequest, ExternalTraining, Complexity, TrainingRequestStatus, ExternalTrainingStatus
from datetime import datetime, timedelta
import json

@pytest.fixture
def api_user(app):
    with app.app_context():
        user = User(full_name='API Test User', email='api_test@example.com', is_admin=True)
        user.set_password('api_password')
        user.generate_api_key()
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def auth_headers(api_user):
    return {'X-API-Key': api_user.api_key}

def test_api_key_authentication(client, api_user):
    # Test with valid API key
    headers = {'X-API-Key': api_user.api_key}
    response = client.get('/api/users/', headers=headers)
    assert response.status_code == 200

    # Test with invalid API key
    headers = {'X-API-Key': 'invalid_key'}
    response = client.get('/api/users/', headers=headers)
    assert response.status_code == 401

    # Test with missing API key
    response = client.get('/api/users/')
    assert response.status_code == 401

def test_api_get_users(client, auth_headers, api_user):
    response = client.get('/api/users/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1 # Only the api_user exists initially
    assert data[0]['email'] == api_user.email

def test_api_create_user(client, auth_headers):
    user_data = {
        'full_name': 'New API User',
        'email': 'new_api_user@example.com',
        'password': 'new_password',
        'is_admin': False,
        'is_team_lead': False
    }
    response = client.post('/api/users/', headers=auth_headers, json=user_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['email'] == 'new_api_user@example.com'
    assert User.query.filter_by(email='new_api_user@example.com').first() is not None

def test_api_get_user_by_id(client, auth_headers, api_user):
    response = client.get(f'/api/users/{api_user.id}', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['email'] == api_user.email

def test_api_update_user(client, auth_headers, api_user):
    updated_data = {
        'full_name': 'Updated API User',
        'email': 'api_test_updated@example.com',
        'is_admin': True
    }
    response = client.put(f'/api/users/{api_user.id}', headers=auth_headers, json=updated_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['full_name'] == 'Updated API User'
    assert data['email'] == 'api_test_updated@example.com'
    assert data['is_admin'] is True

def test_api_delete_user(client, auth_headers, api_user):
    user_to_delete = User(full_name='Delete User', email='delete@example.com')
    user_to_delete.set_password('deletepass')
    db.session.add(user_to_delete)
    db.session.commit()

    response = client.delete(f'/api/users/{user_to_delete.id}', headers=auth_headers)
    assert response.status_code == 204
    assert User.query.get(user_to_delete.id) is None

# Add tests for other API endpoints (Teams, Species, Skills, etc.)
def test_api_get_teams(client, auth_headers):
    team = Team(name='Test Team')
    db.session.add(team)
    db.session.commit()
    response = client.get('/api/teams/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Team'

def test_api_create_team(client, auth_headers):
    team_data = {'name': 'New API Team'}
    response = client.post('/api/teams/', headers=auth_headers, json=team_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Team'

def test_api_get_species(client, auth_headers):
    species = Species(name='Test Species')
    db.session.add(species)
    db.session.commit()
    response = client.get('/api/species/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Species'

def test_api_create_species(client, auth_headers):
    species_data = {'name': 'New API Species'}
    response = client.post('/api/species/', headers=auth_headers, json=species_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Species'

def test_api_get_skills(client, auth_headers):
    skill = Skill(name='Test Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    response = client.get('/api/skills/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Skill'

def test_api_create_skill(client, auth_headers):
    skill_data = {'name': 'New API Skill', 'complexity': 'SIMPLE'}
    response = client.post('/api/skills/', headers=auth_headers, json=skill_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Skill'

def test_api_get_training_paths(client, auth_headers):
    path = TrainingPath(name='Test Path')
    db.session.add(path)
    db.session.commit()
    response = client.get('/api/training_paths/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Path'

def test_api_create_training_path(client, auth_headers):
    path_data = {'name': 'New API Path'}
    response = client.post('/api/training_paths/', headers=auth_headers, json=path_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Path'

def test_api_get_training_sessions(client, auth_headers):
    session = TrainingSession(title='Test Session', start_time=datetime.utcnow(), end_time=datetime.utcnow() + timedelta(hours=1))
    db.session.add(session)
    db.session.commit()
    response = client.get('/api/training_sessions/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['title'] == 'Test Session'

def test_api_create_training_session(client, auth_headers):
    session_data = {
        'title': 'New API Session',
        'start_time': datetime.utcnow().isoformat(),
        'end_time': (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    response = client.post('/api/training_sessions/', headers=auth_headers, json=session_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'New API Session'

def test_api_get_competencies(client, auth_headers, api_user):
    skill = Skill(name='Competency Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    competency = Competency(user=api_user, skill=skill, level='Novice')
    db.session.add(competency)
    db.session.commit()
    response = client.get('/api/competencies/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['user_id'] == api_user.id

def test_api_create_competency(client, auth_headers, api_user):
    skill = Skill(name='New Competency Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    competency_data = {
        'user_id': api_user.id,
        'skill_id': skill.id,
        'level': 'Expert'
    }
    response = client.post('/api/competencies/', headers=auth_headers, json=competency_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['level'] == 'Expert'

def test_api_get_skill_practice_events(client, auth_headers, api_user):
    skill = Skill(name='Practice Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    event = SkillPracticeEvent(user=api_user, skill=skill, practice_date=datetime.utcnow())
    db.session.add(event)
    db.session.commit()
    response = client.get('/api/skill_practice_events/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['user_id'] == api_user.id

def test_api_create_skill_practice_event(client, auth_headers, api_user):
    skill = Skill(name='New Practice Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    event_data = {
        'user_id': api_user.id,
        'skill_id': skill.id,
        'practice_date': datetime.utcnow().isoformat(),
        'notes': 'Practiced well'
    }
    response = client.post('/api/skill_practice_events/', headers=auth_headers, json=event_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['notes'] == 'Practiced well'

def test_api_get_training_requests(client, auth_headers, api_user):
    skill = Skill(name='Request Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    request_obj = TrainingRequest(requester=api_user, status=TrainingRequestStatus.PENDING)
    request_obj.skills_requested.append(skill)
    db.session.add(request_obj)
    db.session.commit()
    response = client.get('/api/training_requests/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['requester_id'] == api_user.id

def test_api_create_training_request(client, auth_headers, api_user):
    skill = Skill(name='Another Request Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    request_data = {
        'requester_id': api_user.id,
        'skills_requested_ids': [skill.id],
        'status': 'PENDING'
    }
    response = client.post('/api/training_requests/', headers=auth_headers, json=request_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'Pending'

def test_api_get_external_trainings(client, auth_headers, api_user):
    skill = Skill(name='External Training Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    external_training = ExternalTraining(user=api_user, external_trainer_name='Trainer A', date=datetime.utcnow(), status=ExternalTrainingStatus.PENDING)
    external_training.skills_claimed.append(skill)
    db.session.add(external_training)
    db.session.commit()
    response = client.get('/api/external_trainings/', headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['user_id'] == api_user.id

def test_api_create_external_training(client, auth_headers, api_user):
    skill = Skill(name='Yet Another External Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    external_training_data = {
        'user_id': api_user.id,
        'external_trainer_name': 'Trainer B',
        'date': datetime.utcnow().isoformat(),
        'status': 'PENDING',
        'skills_claimed_ids': [skill.id]
    }
    response = client.post('/api/external_trainings/', headers=auth_headers, json=external_training_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['external_trainer_name'] == 'Trainer B'
