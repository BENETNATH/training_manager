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
