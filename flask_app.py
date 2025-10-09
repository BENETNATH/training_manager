import os
from app import create_app, db
from app.models import User, Team, Species, Skill, TrainingPath, TrainingSession, Competency, SkillPracticeEvent, TrainingRequest, ExternalTraining, Complexity, TrainingRequestStatus, ExternalTrainingStatus, init_roles_and_permissions

app = create_app()

with app.app_context():
    init_roles_and_permissions()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Team': Team, 'Species': Species, 'Skill': Skill,
            'TrainingPath': TrainingPath, 'TrainingSession': TrainingSession,
            'Competency': Competency, 'SkillPracticeEvent': SkillPracticeEvent,
            'TrainingRequest': TrainingRequest, 'ExternalTraining': ExternalTraining,
            'Complexity': Complexity, 'TrainingRequestStatus': TrainingRequestStatus,
            'ExternalTrainingStatus': ExternalTrainingStatus}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)