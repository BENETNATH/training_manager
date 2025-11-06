from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.team import bp
from app.models import User, Team, Competency, Skill, SkillPracticeEvent, UserContinuousTraining, UserContinuousTrainingStatus, ContinuousTrainingEvent, ContinuousTrainingType, ExternalTrainingSkillClaim, ExternalTrainingStatus, ExternalTraining
from app.decorators import permission_required
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from app import db # Import db

@bp.route('/competencies')
@login_required
@permission_required('view_team_competencies')
def team_competencies():
    # A team lead can now lead multiple teams
    led_teams = current_user.teams_as_lead # Get all teams the user leads

    if not led_teams:
        flash('You are not currently leading any teams.', 'warning')
        return redirect(url_for('dashboard.user_profile', username=current_user.full_name))

    all_skills = Skill.query.order_by(Skill.name).all()
    
    # Dictionary to hold competency matrix for each led team
    teams_competency_data = {}

    for team in led_teams:
        team_members = team.members # Get members for the current team (no .all() needed)
        skill_competency_matrix = {skill.id: {'skill': skill, 'member_competencies': {}} for skill in all_skills}
        member_training_summaries = {}
        skills_with_competent_members_ids = set() # Initialize set for skills with competent members

        for member in team_members:
            db.session.refresh(member) # Refresh the user object to get latest data

            member_training_summaries[member.id] = {
                'user': member,
                'continuous_training_summary': {
                    'total_hours_6_years': member.total_continuous_training_hours_6_years,
                            'live_hours_6_years': member.live_continuous_training_hours_6_years,
                            'online_hours_6_years': member.online_continuous_training_hours_6_years,
                            'required_hours': member.required_continuous_training_hours,
                            'is_compliant': member.is_continuous_training_compliant,
                            'required_live_training_hours': member.required_live_training_hours,
                            'is_live_training_compliant': member.is_live_training_compliant,
                            'is_at_risk_next_year': member.is_at_risk_next_year,
                        }
                    }
    
            for skill in all_skills:
                competency = Competency.query.filter_by(user_id=member.id, skill_id=skill.id).first()
                
                # Check for approved external training claims for this user and skill
                external_training_claim = ExternalTrainingSkillClaim.query.join(ExternalTraining).filter(
                    ExternalTrainingSkillClaim.skill_id == skill.id,
                    ExternalTraining.user_id == member.id,
                    ExternalTraining.status == ExternalTrainingStatus.APPROVED
                ).first()

                latest_practice_date = None
                if competency:
                    latest_practice_date = competency.latest_practice_date
                elif external_training_claim:
                    latest_practice_date = external_training_claim.practice_date
                
                # If either a competency or an approved external training claim exists, consider the member competent
                if competency or external_training_claim:
                    skills_with_competent_members_ids.add(skill.id) # Add skill ID if competency or approved external training exists
                
                needs_recycling = False
                recycling_due_date = None
                # Calculate recycling dates if a latest_practice_date is available and skill has a validity period
                if latest_practice_date and skill.validity_period_months:
                    recycling_due_date = latest_practice_date + timedelta(days=skill.validity_period_months * 30)
                    needs_recycling = datetime.now(timezone.utc) > recycling_due_date

                skill_competency_matrix[skill.id]['member_competencies'][member.id] = {
                    'competency': competency,
                    'latest_practice_date': latest_practice_date,
                    'recycling_due_date': recycling_due_date,
                    'needs_recycling': needs_recycling
                }
        teams_competency_data[team.id] = {
            'team': team,
            'members': team_members,
            'all_skills': all_skills,
            'skill_competency_matrix': skill_competency_matrix,
            'member_training_summaries': member_training_summaries,
            'skills_with_competent_members_ids': list(skills_with_competent_members_ids) # Convert set to list
        }    
    return render_template('team/team_competencies.html', title='Team Competencies',
                           teams_competency_data=teams_competency_data, all_skills=all_skills)
