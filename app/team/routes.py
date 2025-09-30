from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.team import bp
from app.models import User, Team, Competency, Skill, SkillPracticeEvent
from app.decorators import team_lead_required
from datetime import datetime, timedelta

@bp.route('/competencies')
@login_required
@team_lead_required
def team_competencies():
    # A team lead can now lead multiple teams
    led_teams = current_user.teams_as_lead # Get all teams the user leads

    if not led_teams:
        flash('You are not currently leading any teams.', 'warning')
        return redirect(url_for('main.dashboard'))

    all_skills = Skill.query.order_by(Skill.name).all()
    
    # Dictionary to hold competency matrix for each led team
    teams_competency_data = {}

    for team in led_teams:
        team_members = team.members # Get members for the current team (no .all() needed)
        competency_matrix = {}

        for member in team_members:
            competency_matrix[member.id] = {
                'user': member,
                'skills': {}
            }
            for skill in all_skills:
                competency = Competency.query.filter_by(user_id=member.id, skill_id=skill.id).first()
                
                latest_practice_date = None
                if competency:
                    latest_practice_date = competency.evaluation_date
                    practice_events = SkillPracticeEvent.query.join(SkillPracticeEvent.skills).filter(
                        SkillPracticeEvent.user_id == member.id,
                        Skill.id == skill.id
                    ).order_by(SkillPracticeEvent.practice_date.desc()).first()

                    if practice_events and practice_events.practice_date > latest_practice_date:
                        latest_practice_date = practice_events.practice_date
                
                needs_recycling = False
                recycling_due_date = None
                if competency and competency.skill.validity_period_months and latest_practice_date:
                    recycling_due_date = latest_practice_date + timedelta(days=competency.skill.validity_period_months * 30)
                    needs_recycling = datetime.utcnow() > recycling_due_date

                competency_matrix[member.id]['skills'][skill.id] = {
                    'competency': competency,
                    'latest_practice_date': latest_practice_date,
                    'recycling_due_date': recycling_due_date,
                    'needs_recycling': needs_recycling
                }
        teams_competency_data[team.id] = {
            'team': team,
            'members': team_members,
            'competency_matrix': competency_matrix
        }
    
    return render_template('team/team_competencies.html', title='Team Competencies',
                           teams_competency_data=teams_competency_data, all_skills=all_skills)
