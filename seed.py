import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import (
    User, Team, Species, Skill, TrainingPath, TrainingSession, Competency, SkillPracticeEvent,
    TrainingRequest, ExternalTraining, Role, Permission, InitialRegulatoryTrainingLevel,
    InitialRegulatoryTraining, ContinuousTrainingType, ContinuousTrainingEvent,
    ContinuousTrainingEventStatus, UserContinuousTrainingStatus, UserContinuousTraining,
    Complexity, TrainingRequestStatus, ExternalTrainingStatus, init_roles_and_permissions
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
            admin_user = User.create_admin_user(email=admin_email, password=admin_password)
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
    study_levels = ['pre-BAC'] + [str(i) for i in range(9)] + ['8+']
    for _ in range(count):
        full_name = fake.name()
        email = fake.unique.email()
        password = "password" # Default password for generated users
        is_admin = fake.boolean(chance_of_getting_true=10) # 10% chance of being admin
        study_level = random.choice(study_levels)

        user = User(full_name=full_name, email=email, is_admin=is_admin, study_level=study_level)
        user.set_password(password)
        db.session.add(user)
        users.append(user)
    db.session.commit()

    # Assign users to teams and potentially as team leads after they are committed
    for user in users:
        if teams and fake.boolean(chance_of_getting_true=70): # 70% chance to be in a team
            chosen_team = random.choice(teams)
            user.teams.append(chosen_team)
            if fake.boolean(chance_of_getting_true=20): # 20% chance of being team lead for that team
                user.teams_as_lead.append(chosen_team)
        db.session.add(user)
    db.session.commit()
    print(f"Created {len(users)} users and assigned them to teams.")
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

def create_training_paths(skills, species_list, count=10):
    training_paths = []
    for _ in range(count):
        path_name = fake.unique.bs() + " Training Path"
        description = fake.paragraph()
        
        if not species_list:
            print("Warning: No species available to assign to TrainingPath. Skipping creation.")
            continue

        chosen_species = random.choice(species_list)
        training_path = TrainingPath(name=path_name, description=description, species_id=chosen_species.id)
        
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
            animal_count=animal_count,
            ethical_authorization_id=ethical_authorization_id
        )
        
        if tutor:
            training_session.tutors.append(tutor)
        
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
            practice_date=practice_date,
            notes=notes
        )
        event.skills.append(skill)
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
        db.session.add(external_training) # Add external_training to session immediately
        db.session.flush() # Flush to assign an ID to external_training
        
        if skills:
            num_skills = random.randint(1, min(3, len(skills)))
            # For each skill, create an ExternalTrainingSkillClaim object
            for skill_obj in random.sample(skills, num_skills):
                skill_claim = ExternalTrainingSkillClaim(
                    level=random.choice(['Novice', 'Intermediate', 'Expert']),
                    wants_to_be_tutor=fake.boolean(chance_of_getting_true=30),
                    practice_date=fake.date_time_between(start_date=date, end_date='now') if fake.boolean(chance_of_getting_true=50) else None
                )
                skill_claim.skill = skill_obj # Assign skill object to the relationship
                skill_claim.external_training = external_training # Explicitly link to parent external_training
                db.session.add(skill_claim) # Add skill_claim to session
                # Assign species associated with the skill to the skill claim
                if skill_obj.species:
                    skill_claim.species_claimed.extend(skill_obj.species)
                # No need to append to external_training.skill_claims here, as it's handled by the relationship backref
            
        external_trainings.append(external_training)
    db.session.commit()
    print(f"Created {len(external_trainings)} external trainings.")
    return external_trainings

def create_initial_regulatory_trainings(users):
    initial_trainings = []
    for user in users:
        if fake.boolean(chance_of_getting_true=50): # 50% of users have initial training
            level = random.choice(list(InitialRegulatoryTrainingLevel))
            training_date = fake.date_time_between(start_date='-5y', end_date='-1y')
            initial_training = InitialRegulatoryTraining(
                user=user,
                level=level,
                training_date=training_date,
                attachment_path=None # For simplicity, no attachments in seed
            )
            db.session.add(initial_training)
            initial_trainings.append(initial_training)
    db.session.commit()
    print(f"Created {len(initial_trainings)} initial regulatory trainings.")
    return initial_trainings

def create_continuous_training_events(users, count=20):
    events = []
    for _ in range(count):
        title = fake.sentence(nb_words=5)
        description = fake.paragraph()
        training_type = random.choice(list(ContinuousTrainingType))
        location = fake.city() if training_type == ContinuousTrainingType.PRESENTIAL else None
        event_date = fake.date_time_between(start_date='-3y', end_date='+1y')
        duration_hours = random.randint(1, 8)
        creator = random.choice(users)

        event = ContinuousTrainingEvent(
            title=title,
            description=description,
            training_type=training_type,
            location=location,
            event_date=event_date,
            duration_hours=duration_hours,
            attachment_path=None, # For simplicity, no attachments in seed
            creator=creator,
            status=ContinuousTrainingEventStatus.APPROVED # Seeded events are approved by default
        )
        db.session.add(event)
        events.append(event)
    db.session.commit()
    print(f"Created {len(events)} continuous training events.")
    return events

def create_user_continuous_trainings(users, continuous_training_events, count_per_user=3):
    user_cts = []
    for user in users:
        if continuous_training_events:
            num_trainings = random.randint(0, count_per_user)
            chosen_events = random.sample(continuous_training_events, min(num_trainings, len(continuous_training_events)))
            for event in chosen_events:
                status = random.choice(list(UserContinuousTrainingStatus))
                validated_by = random.choice(users) if status == UserContinuousTrainingStatus.APPROVED else None
                validated_hours = event.duration_hours if status == UserContinuousTrainingStatus.APPROVED else None
                validation_date = fake.date_time_between(start_date=event.event_date, end_date='now') if status == UserContinuousTrainingStatus.APPROVED else None

                user_ct = UserContinuousTraining(
                    user=user,
                    event=event,
                    attendance_attachment_path=None, # For simplicity, no attachments in seed
                    status=status,
                    validated_by=validated_by,
                    validated_hours=validated_hours,
                    validation_date=validation_date
                )
                db.session.add(user_ct)
                user_cts.append(user_ct)
    db.session.commit()
    print(f"Created {len(user_cts)} user continuous trainings.")
    return user_cts


with app.app_context():
    db.create_all() # Ensure tables exist
    init_roles_and_permissions()

    print("Seeding database...")

    admin_user = create_admin_user()
    
    teams = create_teams()
    users = create_users(teams)
    
    # Refresh objects from DB to ensure all relationships are correctly loaded after initial commit
    teams = Team.query.all()
    users = User.query.all()

    # Assign team leads by setting lead_id directly
    for team in teams:
        # Find users who are leads for this specific team
        potential_leads = [u for u in users if team in u.teams_as_lead]
        if potential_leads:
            # This part needs to be re-evaluated. The Team model does not have a lead_id attribute.
            # Team leads are associated via the many-to-many relationship team_leads.
            # The current logic here is trying to set a single lead_id on the team, which is incorrect.
            # If the goal is to ensure each team has at least one lead, this logic needs to be different.
            # For now, I will comment out this section as it's trying to set a non-existent attribute.
            pass # No direct lead_id on Team model

    species_list = create_species()
    skills = create_skills(species_list)

    # Assign some skills to tutors
    for user in users:
        if user.teams_as_lead and skills and fake.boolean(chance_of_getting_true=50):
            # Get skills not already tutored by the user
            available_skills = [skill for skill in skills if skill not in user.tutored_skills]
            if available_skills:
                num_tutored_skills = random.randint(1, min(3, len(available_skills)))
                user.tutored_skills.extend(random.sample(available_skills, num_tutored_skills))
                db.session.add(user)
    db.session.commit()
    print("Assigned tutored skills to some team leads.")

    training_paths = create_training_paths(skills, species_list)

    # Assign some training paths to users
    for user in users:
        if training_paths and fake.boolean(chance_of_getting_true=40):
            # Get paths not already assigned to the user
            available_paths = [path for path in training_paths if path not in user.assigned_training_paths]
            if available_paths:
                num_assigned_paths = random.randint(1, min(2, len(available_paths)))
                user.assigned_training_paths.extend(random.sample(available_paths, num_assigned_paths))
                db.session.add(user)
    db.session.commit()
    print("Assigned training paths to some users.")

    training_sessions = create_training_sessions(users, skills)

    # Assign attendees to training sessions
    for session in training_sessions:
        if users and fake.boolean(chance_of_getting_true=70):
            # Get users not already assigned to the session
            available_users = [user for user in users if user not in session.attendees]
            if available_users:
                num_attendees = random.randint(1, min(5, len(available_users)))
                session.attendees.extend(random.sample(available_users, num_attendees))
                db.session.add(session)
    db.session.commit()
    print("Assigned attendees to training sessions.")

    competencies = create_competencies(users, skills, training_sessions)
    skill_practice_events = create_skill_practice_events(users, skills)
    training_requests = create_training_requests(users, skills)
    external_trainings = create_external_trainings(users, skills)

    initial_regulatory_trainings = create_initial_regulatory_trainings(users)
    continuous_training_events = create_continuous_training_events(users)
    user_continuous_trainings = create_user_continuous_trainings(users, continuous_training_events)

    print("Database seeding complete!")
