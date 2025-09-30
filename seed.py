import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import (
    User, Team, Species, Skill, TrainingPath, TrainingSession, Competency,
    SkillPracticeEvent, TrainingRequest, ExternalTraining,
    Complexity, TrainingRequestStatus, ExternalTrainingStatus
)
from werkzeug.security import generate_password_hash
from faker import Faker
import random
from datetime import datetime, timedelta

load_dotenv()
fake = Faker()

app = create_app()

def create_admin_user():
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')

    if not admin_email or not admin_password:
        print("ADMIN_EMAIL or ADMIN_PASSWORD not set in .env. Skipping admin user creation.")
        return None
    else:
        admin_user = User.query.filter_by(email=admin_email).first()
        if admin_user is None:
            admin_user = User(full_name="Admin User", email=admin_email, is_admin=True, is_team_lead=True)
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{admin_email}' created.")
            return admin_user
        else:
            print(f"Admin user '{admin_email}' already exists.")
            return admin_user

def create_teams(count=5):
    teams = []
    for _ in range(count):
        team_name = fake.unique.company() + " Team"
        team = Team.query.filter_by(name=team_name).first()
        if team is None:
            team = Team(name=team_name)
            db.session.add(team)
            teams.append(team)
    db.session.commit()
    print(f"Created {len(teams)} teams.")
    return Team.query.all()

def create_users(teams, count=20):
    users = []
    for _ in range(count):
        full_name = fake.name()
        email = fake.unique.email()
        password = "password" # Default password for generated users
        team_id = random.choice(teams).id if teams else None
        is_admin = fake.boolean(chance_of_getting_true=10) # 10% chance of being admin
        is_team_lead = fake.boolean(chance_of_getting_true=20) # 20% chance of being team lead

        user = User(full_name=full_name, email=email, is_admin=is_admin, is_team_lead=is_team_lead, team_id=team_id)
        user.set_password(password)
        db.session.add(user)
        users.append(user)
    db.session.commit()
    print(f"Created {len(users)} users.")
    return User.query.all()

def create_species(count=5):
    species_list = []
    for _ in range(count):
        species_name = fake.unique.word().capitalize() + " Species"
        species = Species.query.filter_by(name=species_name).first()
        if species is None:
            species = Species(name=species_name)
            db.session.add(species)
            species_list.append(species)
    db.session.commit()
    print(f"Created {len(species_list)} species.")
    return Species.query.all()

def create_skills(species_list, count=30):
    skills = []
    for _ in range(count):
        skill_name = fake.unique.catch_phrase()
        description = fake.paragraph()
        validity_period_months = random.randint(6, 24)
        complexity = random.choice(list(Complexity))
        reference_urls_text = ", ".join([fake.url() for _ in range(random.randint(0, 2))])
        training_videos_urls_text = ", ".join([fake.url() for _ in range(random.randint(0, 2))])
        potential_external_tutors_text = fake.name() if fake.boolean(chance_of_getting_true=30) else ""

        skill = Skill(
            name=skill_name,
            description=description,
            validity_period_months=validity_period_months,
            complexity=complexity,
            reference_urls_text=reference_urls_text,
            training_videos_urls_text=training_videos_urls_text,
            potential_external_tutors_text=potential_external_tutors_text
        )
        if species_list and fake.boolean(chance_of_getting_true=70):
            skill.species.append(random.choice(species_list))
        db.session.add(skill)
        skills.append(skill)
    db.session.commit()
    print(f"Created {len(skills)} skills.")
    return Skill.query.all()

def create_training_paths(skills, count=10):
    training_paths = []
    for _ in range(count):
        path_name = fake.unique.bs() + " Training Path"
        description = fake.paragraph()
        
        training_path = TrainingPath(name=path_name, description=description)
        
        if skills:
            num_skills = random.randint(1, min(5, len(skills)))
            training_path.skills.extend(random.sample(skills, num_skills))
        
        db.session.add(training_path)
        training_paths.append(training_path)
    db.session.commit()
    print(f"Created {len(training_paths)} training paths.")
    return TrainingPath.query.all()

def create_training_sessions(users, skills, count=15):
    training_sessions = []
    tutors = [u for u in users if u.tutored_skills] # Users who can tutor
    
    for _ in range(count):
        title = fake.sentence(nb_words=6)
        location = fake.address()
        start_time = fake.date_time_between(start_date='-1y', end_date='now')
        end_time = start_time + timedelta(hours=random.randint(1, 4))
        animal_count = random.randint(1, 10) if fake.boolean(chance_of_getting_true=50) else None
        ethical_authorization_id = fake.bothify(text='????-########') if fake.boolean(chance_of_getting_true=30) else None

        tutor = random.choice(tutors) if tutors else None
        
        training_session = TrainingSession(
            title=title,
            location=location,
            start_time=start_time,
            end_time=end_time,
            tutor=tutor,
            animal_count=animal_count,
            ethical_authorization_id=ethical_authorization_id
        )
        
        if skills:
            num_skills = random.randint(1, min(3, len(skills)))
            training_session.skills_covered.extend(random.sample(skills, num_skills))
            
        db.session.add(training_session)
        training_sessions.append(training_session)
    db.session.commit()
    print(f"Created {len(training_sessions)} training sessions.")
    return TrainingSession.query.all()

def create_competencies(users, skills, training_sessions, count=50):
    competencies = []
    for _ in range(count):
        user = random.choice(users)
        skill = random.choice(skills)
        
        # Ensure unique competency for user-skill pair
        existing_competency = Competency.query.filter_by(user=user, skill=skill).first()
        if existing_competency:
            continue

        level = random.choice(['Novice', 'Intermediate', 'Expert'])
        evaluation_date = fake.date_time_between(start_date='-2y', end_date='now')
        evaluator = random.choice(users) if fake.boolean(chance_of_getting_true=70) else None
        session = random.choice(training_sessions) if training_sessions and fake.boolean(chance_of_getting_true=50) else None

        competency = Competency(
            user=user,
            skill=skill,
            level=level,
            evaluation_date=evaluation_date,
            evaluator=evaluator,
            training_session=session
        )
        db.session.add(competency)
        competencies.append(competency)
    db.session.commit()
    print(f"Created {len(competencies)} competencies.")
    return Competency.query.all()

def create_skill_practice_events(users, skills, count=40):
    practice_events = []
    for _ in range(count):
        user = random.choice(users)
        skill = random.choice(skills)
        practice_date = fake.date_time_between(start_date='-1y', end_date='now')
        notes = fake.sentence() if fake.boolean(chance_of_getting_true=50) else None

        event = SkillPracticeEvent(
            user=user,
            skill=skill,
            practice_date=practice_date,
            notes=notes
        )
        db.session.add(event)
        practice_events.append(event)
    db.session.commit()
    print(f"Created {len(practice_events)} skill practice events.")
    return practice_events

def create_training_requests(users, skills, count=20):
    training_requests = []
    for _ in range(count):
        requester = random.choice(users)
        request_date = fake.date_time_between(start_date='-6m', end_date='now')
        status = random.choice(list(TrainingRequestStatus))

        request = TrainingRequest(
            requester=requester,
            request_date=request_date,
            status=status
        )
        
        if skills:
            num_skills = random.randint(1, min(3, len(skills)))
            request.skills_requested.extend(random.sample(skills, num_skills))
            
        db.session.add(request)
        training_requests.append(request)
    db.session.commit()
    print(f"Created {len(training_requests)} training requests.")
    return training_requests

def create_external_trainings(users, skills, count=10):
    external_trainings = []
    for _ in range(count):
        user = random.choice(users)
        external_trainer_name = fake.company()
        date = fake.date_time_between(start_date='-1y', end_date='now')
        status = random.choice(list(ExternalTrainingStatus))
        validator = random.choice(users) if fake.boolean(chance_of_getting_true=50) else None

        external_training = ExternalTraining(
            user=user,
            external_trainer_name=external_trainer_name,
            date=date,
            status=status,
            validator=validator
        )
        
        if skills:
            num_skills = random.randint(1, min(3, len(skills)))
            external_training.skills_claimed.extend(random.sample(skills, num_skills))
            
        db.session.add(external_training)
        external_trainings.append(external_training)
    db.session.commit()
    print(f"Created {len(external_trainings)} external trainings.")
    return external_trainings


with app.app_context():
    db.create_all() # Ensure tables exist

    print("Seeding database...")

    admin_user = create_admin_user()
    
    teams = create_teams()
    users = create_users(teams)
    
    # Refresh objects from DB to ensure all relationships are correctly loaded after initial commit
    teams = Team.query.all()
    users = User.query.all()

    # Assign team leads by setting lead_id directly
    for team in teams:
        potential_leads = [u for u in users if u.is_team_lead and u.team_id == team.id]
        if potential_leads:
            team.lead_id = random.choice(potential_leads).id
            db.session.add(team)
    db.session.commit()
    print("Assigned team leads.")

    species_list = create_species()
    skills = create_skills(species_list)

    # Assign some skills to tutors
    for user in users:
        if user.is_team_lead and skills and fake.boolean(chance_of_getting_true=50):
            num_tutored_skills = random.randint(1, min(3, len(skills)))
            user.tutored_skills.extend(random.sample(skills, num_tutored_skills))
            db.session.add(user)
    db.session.commit()
    print("Assigned tutored skills to some team leads.")

    training_paths = create_training_paths(skills)

    # Assign some training paths to users
    for user in users:
        if training_paths and fake.boolean(chance_of_getting_true=40):
            num_assigned_paths = random.randint(1, min(2, len(training_paths)))
            user.assigned_training_paths.extend(random.sample(training_paths, num_assigned_paths))
            db.session.add(user)
    db.session.commit()
    print("Assigned training paths to some users.")

    training_sessions = create_training_sessions(users, skills)

    # Assign attendees to training sessions
    for session in training_sessions:
        if users and fake.boolean(chance_of_getting_true=70):
            num_attendees = random.randint(1, min(5, len(users)))
            session.attendees.extend(random.sample(users, num_attendees))
            db.session.add(session)
    db.session.commit()
    print("Assigned attendees to training sessions.")

    competencies = create_competencies(users, skills, training_sessions)
    skill_practice_events = create_skill_practice_events(users, skills)
    training_requests = create_training_requests(users, skills)
    external_trainings = create_external_trainings(users, skills)

    print("Database seeding complete!")
