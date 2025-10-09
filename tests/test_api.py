import pytest
from app import db
from app.models import User, Team, Species, Skill, TrainingPath, TrainingSession, Competency, SkillPracticeEvent, TrainingRequest, ExternalTraining, ExternalTrainingSkillClaim, Complexity, TrainingRequestStatus, ExternalTrainingStatus, Role
from datetime import datetime, timedelta
import json
from flask import url_for

def create_api_user():
    # Ensure the Admin role exists
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        admin_role = Role(name='Admin')
        db.session.add(admin_role)
        db.session.commit()

    user = User(full_name='API Test User', email='api_test@example.com', is_admin=True)
    user.set_password('api_password')
    user.generate_api_key()
    user.roles.append(admin_role)
    db.session.add(user)
    db.session.commit()
    return user


def test_api_key_authentication(client):
    user = create_api_user()
    # Test with valid API key
    headers = {'X-API-Key': user.api_key}
    response = client.get('/api/users/', headers=headers)
    assert response.status_code == 200

    # Test with invalid API key
    headers = {'X-API-Key': 'invalid_key'}
    response = client.get('/api/users/', headers=headers)
    assert response.status_code == 401

    # Test with missing API key
    response = client.get('/api/users/')
    assert response.status_code == 401

def test_api_get_users(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    response = client.get('/api/users/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1 # Only the api_user exists initially
    assert data[0]['email'] == user.email

def test_api_create_user(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    user_data = {
        'full_name': 'New API User',
        'email': 'new_api_user@example.com',
        'password': 'new_password',
        'is_admin': False
    }
    response = client.post('/api/users/', headers=headers, json=user_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['email'] == 'new_api_user@example.com'
    assert User.query.filter_by(email='new_api_user@example.com').first() is not None

def test_api_update_user(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    updated_data = {
        'full_name': 'Updated API User',
        'email': 'api_test_updated@example.com',
        'is_admin': True
    }
    response = client.put(f'/api/users/{user.id}', headers=headers, json=updated_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['full_name'] == 'Updated API User'
    assert data['email'] == 'api_test_updated@example.com'
    assert data['is_admin'] is True

def test_api_delete_user(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    user_to_delete = User(full_name='Delete User', email='delete@example.com')
    user_to_delete.set_password('deletepass')
    db.session.add(user_to_delete)
    db.session.commit()

    response = client.delete(f'/api/users/{user_to_delete.id}', headers=headers)
    assert response.status_code == 204
    assert User.query.get(user_to_delete.id) is None

# Add tests for other API endpoints (Teams, Species, Skills, etc.)
def test_api_get_teams(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    team = Team(name='Test Team')
    db.session.add(team)
    db.session.commit()
    response = client.get('/api/teams/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Team'

def test_api_create_team(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    team_data = {'name': 'New API Team'}
    response = client.post('/api/teams/', headers=headers, json=team_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Team'

def test_api_get_species(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    species = Species(name='Test Species')
    db.session.add(species)
    db.session.commit()
    response = client.get('/api/species/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Species'

def test_api_create_species(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    species_data = {'name': 'New API Species'}
    response = client.post('/api/species/', headers=headers, json=species_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Species'

def test_api_get_skills(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='Test Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    response = client.get('/api/skills/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Skill'

def test_api_create_skill(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill_data = {'name': 'New API Skill', 'complexity': 'SIMPLE'}
    response = client.post('/api/skills/', headers=headers, json=skill_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Skill'

def test_api_get_training_paths(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    species = Species(name='Test Species for Path')
    db.session.add(species)
    db.session.commit()
    path = TrainingPath(name='Test Path', species_id=species.id)
    db.session.add(path)
    db.session.commit()
    response = client.get('/api/training_paths/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['name'] == 'Test Path'

def test_api_create_training_path(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    path_data = {'name': 'New API Path'}
    response = client.post('/api/training_paths/', headers=headers, json=path_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'New API Path'

def test_api_get_training_sessions(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    session = TrainingSession(title='Test Session', start_time=datetime.utcnow(), end_time=datetime.utcnow() + timedelta(hours=1))
    db.session.add(session)
    db.session.commit()
    response = client.get('/api/training_sessions/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['title'] == 'Test Session'

def test_api_create_training_session(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    session_data = {
        'title': 'New API Session',
        'start_time': datetime.utcnow().isoformat(),
        'end_time': (datetime.utcnow() + timedelta(hours=1)).isoformat()
    }
    response = client.post('/api/training_sessions/', headers=headers, json=session_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'New API Session'

def test_api_get_competencies(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='Competency Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    competency = Competency(user=user, skill=skill, level='Novice')
    db.session.add(competency)
    db.session.commit()
    response = client.get('/api/competencies/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['user_id'] == user.id

def test_api_create_competency(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='New Competency Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    competency_data = {
        'user_id': user.id,
        'skill_id': skill.id,
        'level': 'Expert'
    }
    response = client.post('/api/competencies/', headers=headers, json=competency_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['level'] == 'Expert'

def test_api_get_skill_practice_events(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='Practice Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    event = SkillPracticeEvent(user=user, notes='notes')
    event.skills.append(skill)
    db.session.add(event)
    db.session.commit()
    response = client.get('/api/skill_practice_events/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['user_id'] == user.id

def test_api_create_skill_practice_event(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='New Practice Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    event_data = {
        'user_id': user.id,
        'skill_ids': [skill.id],
        'practice_date': datetime.utcnow().isoformat(),
        'notes': 'Practiced well'
    }
    response = client.post('/api/skill_practice_events/', headers=headers, json=event_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['notes'] == 'Practiced well'

def test_api_get_training_requests(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='Request Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    request_obj = TrainingRequest(requester=user, status=TrainingRequestStatus.PENDING)
    request_obj.skills_requested.append(skill)
    db.session.add(request_obj)
    db.session.commit()
    response = client.get('/api/training_requests/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['requester_id'] == user.id

def test_api_create_training_request(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='Another Request Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    request_data = {
        'requester_id': user.id,
        'skill_ids': [skill.id],
        'status': 'PENDING'
    }
    response = client.post('/api/training_requests/', headers=headers, json=request_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'TrainingRequestStatus.PENDING'

def test_api_get_external_trainings(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='External Training Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    external_training = ExternalTraining(user=user, external_trainer_name='Trainer A', date=datetime.utcnow(), status=ExternalTrainingStatus.PENDING)
    claim = ExternalTrainingSkillClaim(skill=skill, level='Novice')
    external_training.skill_claims.append(claim)
    db.session.add(external_training)
    db.session.commit()
    response = client.get('/api/external_trainings/', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    assert data[0]['user_id'] == user.id

def test_api_create_external_training(client):
    user = create_api_user()
    headers = {'X-API-Key': user.api_key}
    skill = Skill(name='Yet Another External Skill', complexity=Complexity.SIMPLE)
    db.session.add(skill)
    db.session.commit()
    external_training_data = {
        'user_id': user.id,
        'external_trainer_name': 'Trainer B',
        'date': datetime.utcnow().isoformat(),
        'status': 'PENDING',
        'skill_claims': [{'skill_id': skill.id, 'level': 'Expert'}]
    }
    response = client.post('/api/external_trainings/', headers=headers, json=external_training_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['external_trainer_name'] == 'Trainer B'

def test_submit_training_request_new(client):
    user = create_api_user()
    # Log in the user
    client.post('/auth/login', data={'email': user.email, 'password': 'api_password'}, follow_redirects=True)

    skill = Skill(name='New Skill for Request', complexity=Complexity.SIMPLE)
    species = Species(name='New Species for Request')
    db.session.add_all([skill, species])
    db.session.commit()

    data = {
        'species': species.id,
        'skills_requested': [skill.id],
        'submit': True
    }
    response = client.post('/profile/request-training', data=data, follow_redirects=True)
    assert response.status_code == 200 # After redirect
    # Check for a success message in the response data
    assert b'Request for &#39;New Skill for Request&#39; on &#39;New Species for Request&#39; created.' in response.data
    
    request = TrainingRequest.query.filter_by(requester_id=user.id).first()
    assert request is not None
    assert skill in request.skills_requested
    assert species in request.species_requested

def test_submit_training_request_duplicate(client):
    user = create_api_user()
    client.post('/auth/login', data={'email': user.email, 'password': 'api_password'}, follow_redirects=True)

    skill = Skill(name='Duplicate Skill Request', complexity=Complexity.SIMPLE)
    species = Species(name='Duplicate Species Request')
    db.session.add_all([skill, species])
    db.session.commit()

    # First request
    request1 = TrainingRequest(requester=user, status=TrainingRequestStatus.PENDING)
    request1.skills_requested.append(skill)
    request1.species_requested.append(species)
    db.session.add(request1)
    db.session.commit()

    data = {
        'species': species.id,
        'skills_requested': [skill.id],
        'submit': True
    }
    response = client.post('/profile/request-training', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert f"Request for &#39;{skill.name}&#39; on &#39;{species.name}&#39; already exists and is pending.".encode('utf-8') in response.data

    # Check that a new request was not created
    requests = TrainingRequest.query.filter_by(requester_id=user.id).all()
    assert len(requests) == 1

def test_submit_training_request_update_species(client):
    user = create_api_user()
    client.post('/auth/login', data={'email': user.email, 'password': 'api_password'}, follow_redirects=True)

    skill = Skill(name='Update Species Skill', complexity=Complexity.SIMPLE)
    species1 = Species(name='Update Species 1')
    species2 = Species(name='Update Species 2')
    db.session.add_all([skill, species1, species2])
    db.session.commit()

    # First request
    request1 = TrainingRequest(requester=user, status=TrainingRequestStatus.PENDING)
    request1.skills_requested.append(skill)
    request1.species_requested.append(species1)
    db.session.add(request1)
    db.session.commit()

    data = {
        'species': species2.id,
        'skills_requested': [skill.id],
        'submit': True
    }
    response = client.post('/profile/request-training', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert f"Request for &#39;{skill.name}&#39; on &#39;{species2.name}&#39; created.".encode('utf-8') in response.data

    # Check that a new request was created, as the logic creates a new one per species
    requests = TrainingRequest.query.filter_by(requester_id=user.id).all()
    assert len(requests) == 2
    assert species2 in requests[1].species_requested