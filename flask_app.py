import os
from app import create_app, db
from app.models import User, Team, Species, Skill, TrainingPath, TrainingSession, Competency, SkillPracticeEvent, TrainingRequest, ExternalTraining, Complexity, TrainingRequestStatus, ExternalTrainingStatus

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Team': Team, 'Species': Species, 'Skill': Skill,
            'TrainingPath': TrainingPath, 'TrainingSession': TrainingSession,
            'Competency': Competency, 'SkillPracticeEvent': SkillPracticeEvent,
            'TrainingRequest': TrainingRequest, 'ExternalTraining': ExternalTraining,
            'Complexity': Complexity, 'TrainingRequestStatus': TrainingRequestStatus,
            'ExternalTrainingStatus': ExternalTrainingStatus}

if __name__ == '__main__':
    with app.app_context():
        # Create database tables and admin user if they don't exist
        db.create_all()
        if not User.check_for_admin_user():
            User.create_admin_user(app.config['ADMIN_EMAIL'], app.config['ADMIN_PASSWORD'])
            print("Admin user created.")
        print("Database is ready.")

    app.run(host='0.0.0.0', port=5000)