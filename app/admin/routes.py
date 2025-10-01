import os

import io
from flask import render_template, redirect, url_for, flash, request, current_app, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.admin import bp
from app.admin.forms import UserForm, TeamForm, SpeciesForm, SkillForm, TrainingPathForm, ImportForm, AddUserToTeamForm, TrainingValidationForm, AttendeeValidationForm, CompetencyValidationForm
from app.training.forms import TrainingSessionForm # Import TrainingSessionForm
from app.models import User, Team, Species, Skill, TrainingPath, ExternalTraining, TrainingRequest, TrainingRequestStatus, ExternalTrainingStatus, Competency, TrainingSession, SkillPracticeEvent, Complexity, ExternalTrainingSkillClaim
from app.decorators import admin_required
from sqlalchemy import func, extract
import openpyxl # Import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment
from datetime import datetime, timedelta # Import datetime, timedelta

@bp.route('/')
@bp.route('/index')
@login_required
@admin_required
def index():
    # Metrics for the cards
    pending_requests_count = TrainingRequest.query.filter_by(status=TrainingRequestStatus.PENDING).count()
    pending_external_trainings_count = ExternalTraining.query.filter_by(status=ExternalTrainingStatus.PENDING).count()
    skills_without_tutors_count = Skill.query.filter(~Skill.tutors.any()).count()
    
    # Placeholder for more complex metrics
    users_needing_recycling_set = set()
    for user_obj in User.query.all(): # Renamed 'user' to 'user_obj' to avoid conflict with 'user' in edit_user
        for comp in user_obj.competencies.all():
            latest_practice_date = comp.evaluation_date
            practice_event = SkillPracticeEvent.query.filter_by(
                user_id=user_obj.id
            ).join(SkillPracticeEvent.skills).filter_by(
                id=comp.skill_id
            ).order_by(SkillPracticeEvent.practice_date.desc()).first()

            if practice_event and practice_event.practice_date > latest_practice_date:
                latest_practice_date = practice_event.practice_date
            
            if comp.skill.validity_period_months:
                # Using 30.44 days as average for a month
                recycling_due_date = latest_practice_date + timedelta(days=comp.skill.validity_period_months * 30.44)
                if datetime.utcnow() > recycling_due_date:
                    users_needing_recycling_set.add(user_obj)

    recycling_needed_count = len(users_needing_recycling_set)
    users_needing_recycling = list(users_needing_recycling_set)
    
    # Logic for sessions this month (now next session)
    now = datetime.utcnow()
    next_session = TrainingSession.query.filter(TrainingSession.start_time > now).order_by(TrainingSession.start_time.asc()).first()

    # Data for the tables
    users = User.query.options(db.joinedload(User.teams), db.joinedload(User.teams_as_lead)).order_by(User.full_name).all() # Eagerly load teams and teams_as_lead
    skills = Skill.query.options(db.joinedload(Skill.species)).order_by(Skill.name).all()
    pending_training_requests = TrainingRequest.query.options(
        db.joinedload(TrainingRequest.requester),
        db.joinedload(TrainingRequest.skills_requested),
        db.joinedload(TrainingRequest.species_requested)
    ).filter_by(status=TrainingRequestStatus.PENDING).all()
    teams = Team.query.all()

    return render_template('admin/index.html',
                           title='Admin Dashboard',
                           pending_requests_count=pending_requests_count,
                           pending_external_trainings_count=pending_external_trainings_count,
                           skills_without_tutors_count=skills_without_tutors_count,
                           recycling_needed_count=recycling_needed_count,
                           next_session=next_session,
                           users=users,
                           skills=skills,
                           pending_training_requests=pending_training_requests,
                           users_needing_recycling=users_needing_recycling,
                           teams=teams)

# User Management
@bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/manage_users.html', title='Manage Users', users=users)

@bp.route('/teams')
@login_required
@admin_required
def manage_teams():
    teams = Team.query.all()
    return render_template('admin/manage_teams.html', title='Manage Teams', teams=teams)


@bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User(full_name=form.full_name.data, email=form.email.data,
                    is_admin=form.is_admin.data)
        user.set_password(form.password.data)
        
        # Handle many-to-many relationships
        user.teams = form.teams.data
        user.teams_as_lead = form.teams_as_lead.data

        db.session.add(user)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': 'User added successfully!',
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'is_admin': user.is_admin,
                    'teams': [t.name for t in user.teams],
                    'teams_as_lead': [lt.name for lt in user.teams_as_lead]
                }
            })

        flash('User added successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_user_form_fields.html', form=form)

    return render_template('admin/user_form.html', title='Add User', form=form)

@bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(original_email=user.email)
    if form.validate_on_submit():
        user.full_name = form.full_name.data
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        user.is_admin = form.is_admin.data
        
        # Handle many-to-many relationships
        user.teams = form.teams.data
        user.teams_as_lead = form.teams_as_lead.data

        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': 'User updated successfully!',
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'is_admin': user.is_admin,
                    'teams': [t.name for t in user.teams],
                    'teams_as_lead': [lt.name for lt in user.teams_as_lead]
                }
            })

        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    elif request.method == 'GET':
        form.full_name.data = user.full_name
        form.email.data = user.email
        form.is_admin.data = user.is_admin
        
        # Pre-populate many-to-many fields
        form.teams.data = user.teams
        form.teams_as_lead.data = user.teams_as_lead
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_user_form_fields.html', form=form)
    return render_template('admin/user_form.html', title='Edit User', form=form)

@bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': # Check if the request is an AJAX request
        return jsonify({'success': True, 'message': 'User deleted successfully!'})
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.manage_users'))

# Team Management

@bp.route('/teams/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_team():
    form = TeamForm()
    if form.validate_on_submit():
        team = Team(name=form.name.data)
        db.session.add(team)
        db.session.flush() # Flush to assign an ID to the new team

        # Handle many-to-many relationships
        team.members = form.members.data
        team.team_leads = form.team_leads.data

        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'message': 'Team added successfully!',
                'team': {
                    'id': team.id,
                    'name': team.name,
                    'members': [m.full_name for m in team.members],
                    'team_leads': [l.full_name for l in team.team_leads]
                }
            })

        flash('Team added successfully!', 'success')
        return redirect(url_for('admin.manage_teams'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_team_form_fields.html', form=form)

    return render_template('admin/team_form.html', title='Add Team', form=form)

@bp.route('/teams/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_team(id):
    team = Team.query.get_or_404(id)
    form = TeamForm(original_name=team.name)
    if form.validate_on_submit():
        team.name = form.name.data
        
        # Handle many-to-many relationships
        team.members = form.members.data
        team.team_leads = form.team_leads.data

        db.session.commit()
        flash('Team updated successfully!', 'success')
        return redirect(url_for('admin.index')) # Redirect to admin dashboard
    elif request.method == 'GET':
        form.name.data = team.name
        
        # Pre-populate many-to-many fields
        form.members.data = team.members
        form.team_leads.data = team.team_leads
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_team_form_fields.html', form=form, team=team)
    return render_template('admin/team_form.html', title='Edit Team', form=form)

@bp.route('/teams/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_team(id):
    team = Team.query.get_or_404(id)
    
    db.session.delete(team)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Team deleted successfully!'})

    flash('Team deleted successfully!', 'success')
    return redirect(url_for('admin.index')) # Redirect to admin dashboard
    flash('Team deleted successfully!', 'success')
    return redirect(url_for('admin.manage_teams'))

@bp.route('/team/<int:team_id>/add_users', methods=['GET', 'POST'])
@login_required
@admin_required
def add_users_to_team(team_id):
    team = Team.query.get_or_404(team_id)
    form = AddUserToTeamForm()

    if form.validate_on_submit():
        selected_users = form.users.data
        for user in selected_users:
            if user not in team.members: # Prevent adding duplicates
                team.members.append(user)
        db.session.commit()
        flash(f'{len(selected_users)} user(s) added to team {team.name} successfully!', 'success')
        return jsonify({'success': True, 'message': f'{len(selected_users)} user(s) added to team {team.name} successfully!'})

    # For GET request or form validation failure
    # Filter users to only show those not already in this team
    # This query needs to be updated to reflect the many-to-many relationship
    form.users.query = User.query.filter(~User.teams.any(id=team.id)).order_by(User.full_name).all()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_add_users_to_team_form.html', form=form, team=team)
    
    flash('Error adding users to team.', 'danger')
    return redirect(url_for('admin.index')) # Redirect to admin dashboard on error

# Species Management
@bp.route('/species')
@login_required
@admin_required
def manage_species():
    species_list = Species.query.all()
    return render_template('admin/manage_species.html', title='Manage Species', species_list=species_list)

@bp.route('/species/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_species():
    form = SpeciesForm()
    if form.validate_on_submit():
        species = Species(name=form.name.data)
        db.session.add(species)
        db.session.commit()
        flash('Species added successfully!', 'success')
        return redirect(url_for('admin.manage_species'))
    return render_template('admin/species_form.html', title='Add Species', form=form)

@bp.route('/species/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_species(id):
    species = Species.query.get_or_404(id)
    form = SpeciesForm(original_name=species.name)
    if form.validate_on_submit():
        species.name = form.name.data
        db.session.commit()
        flash('Species updated successfully!', 'success')
        return redirect(url_for('admin.manage_species'))
    elif request.method == 'GET':
        form.name.data = species.name
    return render_template('admin/species_form.html', title='Edit Species', form=form)

@bp.route('/species/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_species(id):
    species = Species.query.get_or_404(id)
    db.session.delete(species)
    db.session.commit()
    flash('Species deleted successfully!', 'success')
    return redirect(url_for('admin.manage_species'))

# Skill Management
@bp.route('/skills')
@login_required
@admin_required
def manage_skills():
    skills = Skill.query.options(db.joinedload(Skill.species)).order_by(Skill.name).all()
    return render_template('admin/manage_skills.html', title='Manage Skills', skills=skills)

@bp.route('/skills/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_skill():
    form = SkillForm()
    if form.validate_on_submit():
        skill = Skill(name=form.name.data, description=form.description.data,
                      validity_period_months=form.validity_period_months.data,
                      complexity=form.complexity.data,
                      reference_urls_text=form.reference_urls_text.data,
                      training_videos_urls_text=form.training_videos_urls_text.data,
                      potential_external_tutors_text=form.potential_external_tutors_text.data)
        
        if form.protocol_attachment.data:
            filename = secure_filename(form.protocol_attachment.data.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'protocols')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            form.protocol_attachment.data.save(file_path)
            skill.protocol_attachment_path = os.path.join('uploads', 'protocols', filename)

        skill.species = form.species.data
        skill.tutors = form.tutors.data

        db.session.add(skill)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Skill added successfully!',
                'skill': {
                    'id': skill.id,
                    'name': skill.name,
                    'description': skill.description,
                    'tutors': [t.full_name for t in skill.tutors]
                }
            })

        flash('Skill added successfully!', 'success')
        return redirect(url_for('admin.manage_skills'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if form.errors:
            return jsonify({'success': False, 'form_html': render_template('admin/_skill_form_fields.html', form=form)})
        return render_template('admin/_skill_form_fields.html', form=form)

    return render_template('admin/skill_form.html', title='Add Skill', form=form)

@bp.route('/skills/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_skill(id):
    skill = Skill.query.get_or_404(id)
    form = SkillForm(original_name=skill.name)
    if form.validate_on_submit():
        skill.name = form.name.data
        skill.description = form.description.data
        skill.validity_period_months = form.validity_period_months.data
        skill.complexity = form.complexity.data
        skill.reference_urls_text = form.reference_urls_text.data
        skill.training_videos_urls_text = form.training_videos_urls_text.data
        skill.potential_external_tutors_text = form.potential_external_tutors_text.data

        if form.protocol_attachment.data:
            filename = secure_filename(form.protocol_attachment.data.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'protocols')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            form.protocol_attachment.data.save(file_path)
            skill.protocol_attachment_path = os.path.join('uploads', 'protocols', filename)
        
        skill.species = form.species.data
        skill.tutors = form.tutors.data
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Skill updated successfully!',
                'skill': {
                    'id': skill.id,
                    'name': skill.name,
                    'description': skill.description,
                    'tutors': [t.full_name for t in skill.tutors]
                }
            })

        flash('Skill updated successfully!', 'success')
        return redirect(url_for('admin.manage_skills'))
    
    elif request.method == 'GET':
        form.name.data = skill.name
        form.description.data = skill.description
        form.validity_period_months.data = skill.validity_period_months
        form.complexity.data = skill.complexity.name
        form.reference_urls_text.data = skill.reference_urls_text
        form.training_videos_urls_text.data = skill.training_videos_urls_text
        form.potential_external_tutors_text.data = skill.potential_external_tutors_text
        form.species.data = skill.species
        form.tutors.data = skill.tutors

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if form.errors:
            return jsonify({'success': False, 'form_html': render_template('admin/_skill_form_fields.html', form=form)})
        return render_template('admin/_skill_form_fields.html', form=form)
    
    return render_template('admin/skill_form.html', title='Edit Skill', form=form)

@bp.route('/skills/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_skill(id):
    skill = Skill.query.get_or_404(id)
    db.session.delete(skill)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Skill deleted successfully!'})
    flash('Skill deleted successfully!', 'success')
    return redirect(url_for('admin.manage_skills'))

# Training Path Management
@bp.route('/training_paths')
@login_required
@admin_required
def manage_training_paths():
    training_paths = TrainingPath.query.all()
    return render_template('admin/manage_training_paths.html', title='Manage Training Paths', training_paths=training_paths)

@bp.route('/training_paths/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_training_path():
    form = TrainingPathForm()
    if form.validate_on_submit():
        training_path = TrainingPath(name=form.name.data, description=form.description.data)
        training_path.skills = form.skills.data
        training_path.assigned_users = form.assigned_users.data
        db.session.add(training_path)
        db.session.commit()
        flash('Training Path added successfully!', 'success')
        return redirect(url_for('admin.manage_training_paths'))
    return render_template('admin/training_path_form.html', title='Add Training Path', form=form)

@bp.route('/training_paths/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_training_path(id):
    training_path = TrainingPath.query.get_or_404(id)
    form = TrainingPathForm(original_name=training_path.name)
    if form.validate_on_submit():
        training_path.name = form.name.data
        training_path.description = form.description.data
        training_path.skills = form.skills.data
        training_path.assigned_users = form.assigned_users.data
        db.session.commit()
        flash('Training Path updated successfully!', 'success')
        return redirect(url_for('admin.manage_training_paths'))
    elif request.method == 'GET':
        form.name.data = training_path.name
        form.description.data = training_path.description
        form.skills.data = training_path.skills
        form.assigned_users.data = training_path.assigned_users
    return render_template('admin/training_path_form.html', title='Edit Training Path', form=form)

@bp.route('/training_paths/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_training_path(id):
    training_path = TrainingPath.query.get_or_404(id)
    db.session.delete(training_path)
    db.session.commit()
    flash('Training Path deleted successfully!', 'success')
    return redirect(url_for('admin.manage_training_paths'))

# Import/Export Functionality (Placeholders)
@bp.route('/import_export_users', methods=['GET', 'POST'])
@login_required
@admin_required
def import_export_users():
    form = ImportForm()
    form.update_existing.label.text = "Update existing users if emails match?"
    if form.validate_on_submit():
        if form.import_file.data:
            file = form.import_file.data
            filename = secure_filename(file.filename)
            
            if filename.endswith('.xlsx'):
                workbook = openpyxl.load_workbook(file)
                sheet = workbook.active
                
                users_imported = 0
                users_updated = 0
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True)): # Skip header
                    try:
                        # Assuming Excel columns: full_name, email, password, is_admin, is_team_lead, team_name
                        full_name, email, password, is_admin_str, is_team_lead_str, team_name = row
                        
                        user = User.query.filter_by(email=email).first()
                        if user is None:
                            is_admin = str(is_admin_str).lower() == 'true'
                            is_team_lead = str(is_team_lead_str).lower() == 'true'
                            
                            user = User(full_name=full_name, email=email, is_admin=is_admin)
                            user.set_password(password)
                            
                            if team_name:
                                team = Team.query.filter_by(name=team_name).first()
                                if not team:
                                    team = Team(name=team_name)
                                    db.session.add(team)
                                
                                user.teams.append(team)
                                if is_team_lead:
                                    user.teams_as_lead.append(team)
                            
                            db.session.add(user)
                            users_imported += 1
                        elif form.update_existing.data:
                            user.full_name = full_name
                            user.is_admin = str(is_admin_str).lower() == 'true'
                            if password:
                                user.set_password(password)
                            
                            is_team_lead = str(is_team_lead_str).lower() == 'true'
                            
                            # Clear existing teams and leadership roles
                            user.teams.clear()
                            user.teams_as_lead.clear()

                            if team_name:
                                team = Team.query.filter_by(name=team_name).first()
                                if not team:
                                    team = Team(name=team_name)
                                    db.session.add(team)
                                
                                user.teams.append(team)
                                if is_team_lead:
                                    user.teams_as_lead.append(team)
                            users_updated += 1

                    except Exception as e:
                        flash(f"Error importing row {row_idx+1}: {row} - {e}", 'danger')
                        db.session.rollback()
                        continue
                db.session.commit()
                flash(f"{users_imported} users imported, {users_updated} users updated successfully from Excel!", 'success')
            else:
                flash('Unsupported file format. Please upload an XLSX file.', 'danger')
            
            return redirect(url_for('admin.index')) # Redirect to admin dashboard after import

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_import_form.html', form=form, 
                               action_url=url_for('admin.import_export_users'),
                               template_url=url_for('admin.download_user_import_template_xlsx'))

    return render_template('admin/import_export_users.html', title='Import/Export Users', form=form)





@bp.route('/export_users_xlsx')
@login_required
@admin_required
def export_users_xlsx():
    users = User.query.all()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Users"

    # Write header
    sheet.append(['full_name', 'email', 'password', 'is_admin', 'is_team_lead', 'team_name'])

    # Write data
    for user in users:
        sheet.append([user.full_name, user.email, '', user.is_admin, bool(user.teams_as_lead), user.teams[0].name if user.teams else ''])
    
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'users_export_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.xlsx')

@bp.route('/download_user_import_template_xlsx')
@login_required
@admin_required
def download_user_import_template_xlsx():
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "User Import Template"

    headers = ['full_name', 'email', 'password', 'is_admin', 'is_team_lead', 'team_name']
    sheet.append(headers)

    # Data validation for is_admin and is_team_lead columns
    dv_boolean = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=True)
    dv_boolean.add('D2:D1048576') # is_admin column
    dv_boolean.add('E2:E1048576') # is_team_lead column
    sheet.add_data_validation(dv_boolean)

    # Data validation for team_name (list of existing teams)
    team_names = [t.name for t in Team.query.all()]
    if team_names:
        dv_teams = DataValidation(type="list", formula1='"' + ','.join(team_names) + '"', allow_blank=True)
        dv_teams.add('F2:F1048576') # team_name column
        sheet.add_data_validation(dv_teams)

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='user_import_template.xlsx')

@bp.route('/import_export_skills', methods=['GET', 'POST'])
@login_required
@admin_required
def import_export_skills():
    form = ImportForm()
    if form.validate_on_submit():
        if form.import_file.data:
            file = form.import_file.data
            filename = secure_filename(file.filename)
            
            if filename.endswith('.xlsx'):
                workbook = openpyxl.load_workbook(file)
                sheet = workbook.active
                
                skills_imported = 0
                skills_updated = 0
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True)): # Skip header
                    try:
                        # Assuming Excel columns: name, description, validity_period_months, complexity, reference_urls_text, training_videos_urls_text, potential_external_tutors_text, species_names, tutor_emails
                        name, description, validity_period_months_str, complexity_str, reference_urls_text, training_videos_urls_text, potential_external_tutors_text, species_names_str, tutor_emails_str = row
                        
                        skill = Skill.query.filter_by(name=name).first()
                        
                        if skill is None:
                            validity_period_months = int(validity_period_months_str) if validity_period_months_str else None
                            complexity = Complexity(complexity_str) if complexity_str else Complexity.SIMPLE
                            
                            skill = Skill(
                                name=name,
                                description=description,
                                validity_period_months=validity_period_months,
                                complexity=complexity,
                                reference_urls_text=reference_urls_text,
                                training_videos_urls_text=training_videos_urls_text,
                                potential_external_tutors_text=potential_external_tutors_text
                            )
                            db.session.add(skill)
                            # The flush is needed to get the skill.id before adding species and tutors
                            db.session.flush()

                            if species_names_str:
                                species_names = [s.strip() for s in str(species_names_str).split(',')]
                                for species_name in species_names:
                                    species_obj = Species.query.filter_by(name=species_name).first()
                                    if species_obj:
                                        skill.species.append(species_obj)
                                    else:
                                        flash(f"Species '{species_name}' not found for skill '{name}'. It will be skipped.", 'warning')
                            
                            if tutor_emails_str:
                                tutor_emails = [e.strip() for e in str(tutor_emails_str).split(',')]
                                for tutor_email in tutor_emails:
                                    tutor_obj = User.query.filter_by(email=tutor_email).first()
                                    if tutor_obj:
                                        skill.tutors.append(tutor_obj)
                                    else:
                                        flash(f"Tutor with email '{tutor_email}' not found for skill '{name}'. It will be skipped.", 'warning')
                            skills_imported += 1
                        elif form.update_existing.data:
                            # Update existing skill
                            skill.description = description
                            skill.validity_period_months = int(validity_period_months_str) if validity_period_months_str else None
                            skill.complexity = Complexity(complexity_str) if complexity_str else Complexity.SIMPLE
                            skill.reference_urls_text = reference_urls_text
                            skill.training_videos_urls_text = training_videos_urls_text
                            skill.potential_external_tutors_text = potential_external_tutors_text

                            # Handle species (clear and re-add for updates)
                            skill.species.clear()
                            if species_names_str:
                                species_names = [s.strip() for s in str(species_names_str).split(',')]
                                for species_name in species_names:
                                    species_obj = Species.query.filter_by(name=species_name).first()
                                    if species_obj:
                                        skill.species.append(species_obj)
                                    else:
                                        flash(f"Species '{species_name}' not found for skill '{name}'. It will be skipped.", 'warning')
                            
                            # Handle tutors (clear and re-add for updates)
                            skill.tutors.clear()
                            if tutor_emails_str:
                                tutor_emails = [e.strip() for e in str(tutor_emails_str).split(',')]
                                for tutor_email in tutor_emails:
                                    tutor_obj = User.query.filter_by(email=tutor_email).first()
                                    if tutor_obj:
                                        skill.tutors.append(tutor_obj)
                                    else:
                                        flash(f"Tutor with email '{tutor_email}' not found for skill '{name}'. It will be skipped.", 'warning')
                            skills_updated += 1
                        else:
                            flash(f"Skill '{name}' already exists and 'Update existing' was not checked. Skipping.", 'info')
                            continue

                    except Exception as e:
                        flash(f"Error importing row {row_idx+1}: {row} - {e}", 'danger')
                        db.session.rollback()
                        continue
                db.session.commit()
                flash(f"{skills_imported} skills imported and {skills_updated} skills updated successfully from Excel!", 'success')
            else:
                flash('Unsupported file format. Please upload an XLSX file.', 'danger')
            
            return redirect(url_for('admin.index')) # Redirect to admin dashboard after import
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_import_form.html', form=form,
                               action_url=url_for('admin.import_export_skills'),
                               template_url=url_for('admin.download_skill_import_template'))

    return render_template('admin/import_export_skills.html', title='Import/Export Skills', form=form)
@bp.route('/download_skill_import_template')
@login_required
@admin_required
def download_skill_import_template():
    # Get data for dropdowns
    complexity_values = [c.name for c in Complexity]
    species_names = [s.name for s in Species.query.all()]
    tutor_emails = [u.email for u in User.query.all()]

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Skill Import Template"

    headers = [
        'name', 'description', 'validity_period_months', 'complexity',
        'reference_urls_text', 'training_videos_urls_text',
        'potential_external_tutors_text', 'species_names', 'tutor_emails'
    ]
    sheet.append(headers)

    # Create data validation for 'complexity'
    dv_complexity = DataValidation(type="list", formula1='"' + ','.join(complexity_values) + '"', allow_blank=True)
    dv_complexity.add('D2:D1048576') # Apply to column D (Complexity) from row 2 onwards
    sheet.add_data_validation(dv_complexity)

    # Create data validation for 'species_names' (assuming comma-separated list)
    # This is a bit trickier for multi-select, so we'll provide a hint in the comment
    # For now, just a list of existing species for single selection or as a guide
    # if species_names:
    #     dv_species = DataValidation(type="list", formula1='"' + ','.join(species_names) + '"', allow_blank=True)
    #     dv_species.add('H2:H1048576') # Apply to column H (species_names) from row 2 onwards
    #     sheet.add_data_validation(dv_species)
    
    # Create data validation for 'tutor_emails' (assuming comma-separated list)
    # if tutor_emails:
    #     dv_tutors = DataValidation(type="list", formula1='"' + ','.join(tutor_emails) + '"', allow_blank=True)
    #     dv_tutors.add('I2:I1048576') # Apply to column I (tutor_emails) from row 2 onwards
    #     sheet.add_data_validation(dv_tutors)

    # Add a comment to guide users for multi-select fields
    sheet['H1'].comment = openpyxl.comments.Comment("For multiple species, separate names with commas (e.g., 'Species A, Species B')", "Admin")
    sheet['I1'].comment = openpyxl.comments.Comment("For multiple tutors, separate emails with commas (e.g., 'tutor1@example.com, tutor2@example.com')", "Admin")


    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='skill_import_template.xlsx')



@bp.route('/export_skills_xlsx')
@login_required
@admin_required
def export_skills_xlsx():
    skills = Skill.query.all()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Skills"

    headers = [
        'name', 'description', 'validity_period_months', 'complexity',
        'reference_urls_text', 'training_videos_urls_text',
        'potential_external_tutors_text', 'species_names', 'tutor_emails'
    ]
    sheet.append(headers)

    # Get data for dropdowns (same as import template)
    complexity_values = [c.name for c in Complexity]
    species_names_list = [s.name for s in Species.query.all()]
    tutor_emails_list = [u.email for u in User.query.all()]

    # Create data validation for 'complexity'
    dv_complexity = DataValidation(type="list", formula1='"' + ','.join(complexity_values) + '"', allow_blank=True)
    dv_complexity.add('D2:D1048576') # Apply to column D (Complexity) from row 2 onwards
    sheet.add_data_validation(dv_complexity)

    # Create data validation for 'species_names'
    # if species_names_list:
    #     dv_species = DataValidation(type="list", formula1='"' + ','.join(species_names_list) + '"', allow_blank=True)
    #     dv_species.add('H2:H1048576') # Apply to column H (species_names) from row 2 onwards
    #     sheet.add_data_validation(dv_species)
    
    # Create data validation for 'tutor_emails'
    # if tutor_emails_list:
    #     dv_tutors = DataValidation(type="list", formula1='"' + ','.join(tutor_emails_list) + '"', allow_blank=True)
    #     dv_tutors.add('I2:I1048576') # Apply to column I (tutor_emails) from row 2 onwards
    #     sheet.add_data_validation(dv_tutors)

    # Add comments to guide users for multi-select fields
    sheet['H1'].comment = Comment("For multiple species, separate names with commas (e.g., 'Species A, Species B')", "Admin")
    sheet['I1'].comment = Comment("For multiple tutors, separate emails with commas (e.g., 'tutor1@example.com, tutor2@example.com')", "Admin")

    # Write data
    for skill in skills:
        species_names = ', '.join([s.name for s in skill.species])
        tutor_emails = ', '.join([t.email for t in skill.tutors])
        sheet.append([
            skill.name,
            skill.description,
            skill.validity_period_months,
            skill.complexity.value,
            skill.reference_urls_text,
            skill.training_videos_urls_text,
            skill.potential_external_tutors_text,
            species_names,
            tutor_emails
        ])
    
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'skills_export_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.xlsx')



@bp.route('/training_sessions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_training_session():
    form = TrainingSessionForm()
    if form.validate_on_submit():
        session = TrainingSession(
            title=form.title.data,
            location=form.location.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            tutor=form.tutor.data,
            ethical_authorization_id=form.ethical_authorization_id.data,
            animal_count=form.animal_count.data
        )
        if form.attachment.data:
            filename = secure_filename(form.attachment.data.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'training_sessions')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            form.attachment.data.save(file_path)
            session.attachment_path = os.path.join('uploads', 'training_sessions', filename)

        session.attendees = form.attendees.data
        session.skills_covered = form.skills_covered.data
        
        db.session.add(session)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Session de formation créée avec succès !',
                'session': {
                    'id': session.id,
                    'title': session.title,
                    'location': session.location,
                    'start_time': session.start_time.strftime('%Y-%m-%d %H:%M'),
                    'end_time': session.end_time.strftime('%Y-%m-%d %H:%M'),
                    'tutor_name': session.tutor.full_name if session.tutor else 'N/A',
                    'attendees_count': len(session.attendees),
                    'skills_covered_count': len(session.skills_covered),
                    'associated_species': [s.name for s in session.associated_species]
                }
            })

        flash('Session de formation créée avec succès !', 'success')
        return redirect(url_for('admin.manage_training_sessions'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_training_session_form_fields.html', form=form)

    return render_template('admin/training_session_form.html', title='Create Training Session', form=form)

@bp.route('/training_sessions')
@login_required
@admin_required
def manage_training_sessions():
    training_sessions = TrainingSession.query.order_by(TrainingSession.start_time.desc()).all()
    return render_template('admin/manage_training_sessions.html', title='Manage Training Sessions', training_sessions=training_sessions)

@bp.route('/training_sessions/edit/<int:session_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_training_session(session_id):
    session = TrainingSession.query.get_or_404(session_id)
    form = TrainingSessionForm(obj=session) # Pre-populate form with session data
    if form.validate_on_submit():
        session.title = form.title.data
        session.location = form.location.data
        session.start_time = form.start_time.data
        session.end_time = form.end_time.data
        session.tutor = form.tutor.data
        session.ethical_authorization_id = form.ethical_authorization_id.data
        session.animal_count = form.animal_count.data

        if form.attachment.data:
            filename = secure_filename(form.attachment.data.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'training_sessions')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            form.attachment.data.save(file_path)
            session.attachment_path = os.path.join('uploads', 'training_sessions', filename)

        session.attendees = form.attendees.data
        session.skills_covered = form.skills_covered.data
        
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Session de formation mise à jour avec succès !',
                'session': {
                    'id': session.id,
                    'title': session.title,
                    'location': session.location,
                    'start_time': session.start_time.strftime('%Y-%m-%d %H:%M'),
                    'end_time': session.end_time.strftime('%Y-%m-%d %H:%M'),
                    'tutor_name': session.tutor.full_name if session.tutor else 'N/A',
                    'attendees_count': len(session.attendees),
                    'skills_covered_count': len(session.skills_covered),
                    'associated_species': [s.name for s in session.associated_species]
                }
            })

        flash('Session de formation mise à jour avec succès !', 'success')
        return redirect(url_for('admin.manage_training_sessions'))
    
    elif request.method == 'GET':
        # Pre-populate form fields for GET request
        form.title.data = session.title
        form.location.data = session.location
        form.start_time.data = session.start_time
        form.end_time.data = session.end_time
        form.tutor.data = session.tutor
        form.ethical_authorization_id.data = session.ethical_authorization_id
        form.animal_count.data = session.animal_count
        form.attendees.data = session.attendees
        form.skills_covered.data = session.skills_covered

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/_training_session_form_fields.html', form=form)

    return render_template('admin/training_session_form.html', title='Edit Training Session', form=form)

@bp.route('/training_sessions/delete/<int:session_id>', methods=['POST'])
@login_required
@admin_required
def delete_training_session(session_id):
    session = TrainingSession.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Session de formation supprimée avec succès.'})

@bp.route('/training_sessions/<int:session_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_training_session_details(session_id):
    session = TrainingSession.query.get_or_404(session_id)
    form = TrainingValidationForm()

    if form.validate_on_submit():
        # Authorization check: Only the tutor of the session or an admin can validate
        if current_user != session.tutor and not current_user.is_admin:
            flash('You are not authorized to validate competencies for this session.', 'danger')
            return redirect(url_for('admin.view_training_session_details', session_id=session.id))

        for attendee_form_data in form.attendees.data:
            user_label = attendee_form_data.get('user_label')
            if not user_label:
                flash('Invalid attendee data: user label is missing.', 'warning')
                continue # Skip this attendee if user_label is missing or empty

            try:
                user_id = int(user_label.split('-')[0]) # Extract user_id from 'id-fullname'
            except (ValueError, IndexError):
                flash(f'Invalid user label format: {user_label}', 'warning')
                continue # Skip if user_label is not in expected format

            user = User.query.get(user_id)
            if not user:
                flash(f'User with ID {user_id} not found.', 'warning')
                continue # Skip if user does not exist

            for competency_form_data in attendee_form_data['competencies']:
                skill_id = competency_form_data['skill_id']
                acquired = competency_form_data['acquired']
                level = competency_form_data['level']

                skill = Skill.query.get(skill_id)

                if acquired:
                    # Check if competency already exists
                    competency = Competency.query.filter_by(
                        user_id=user.id,
                        skill_id=skill.id,
                        training_session_id=session.id
                    ).first()

                    if competency:
                        # Update existing competency
                        competency.level = level
                        competency.evaluation_date = datetime.utcnow()
                        competency.evaluator = current_user
                    else:
                        # Create new competency
                        competency = Competency(
                            user=user,
                            skill=skill,
                            level=level,
                            evaluation_date=datetime.utcnow(),
                            evaluator=current_user,
                            training_session=session
                        )
                        db.session.add(competency)
                else:
                    # If not acquired, and a competency exists, delete it
                    competency = Competency.query.filter_by(
                        user_id=user.id,
                        skill_id=skill.id,
                        training_session_id=session.id
                    ).first()
                    if competency:
                        db.session.delete(competency)
        
        db.session.commit()
        flash('Competencies validated successfully!', 'success')
        return redirect(url_for('admin.view_training_session_details', session_id=session.id))

    elif request.method == 'GET':
        # Populate the form for GET requests
        for attendee in session.attendees:
            attendee_form = AttendeeValidationForm()
            attendee_form.user_label = f'{attendee.id}-{attendee.full_name}' # Store user_id and full_name

            for skill in session.skills_covered:
                competency_form = CompetencyValidationForm()
                # competency_form.user_id.data = attendee.id # Removed as user_id is no longer a form field
                # competency_form.skill_id.data = skill.id # Removed as skill_id is no longer a form field
                # competency_form.skill_name_display.data = skill.name # Removed as skill_name_display is no longer a form field

                # Check if competency already exists for pre-population
                competency = Competency.query.filter_by(
                    user_id=attendee.id,
                    skill_id=skill.id,
                    training_session_id=session.id
                ).first()

                if competency:
                    competency_form.acquired = True
                    competency_form.level = competency.level
                else:
                    competency_form.acquired = False
                    competency_form.level = 'Novice' # Default level

                attendee_form.competencies.append_entry(competency_form)
            form.attendees.append_entry(attendee_form)

    return render_template('admin/view_training_session_details.html', title='Session Details', session=session, form=form)

@bp.route('/training_requests/reject/<int:request_id>', methods=['POST'])
@login_required
@admin_required
def reject_training_request(request_id):
    training_request = TrainingRequest.query.get_or_404(request_id)
    training_request.status = TrainingRequestStatus.REJECTED
    db.session.commit()
    return jsonify({'success': True, 'message': 'Demande de formation rejetée avec succès.'})

# External Training Validation
@bp.route('/validate_external_trainings')
@login_required
@admin_required
def validate_external_trainings():
    pending_external_trainings = ExternalTraining.query.filter_by(status=ExternalTrainingStatus.PENDING).all()
    return render_template('admin/validate_external_trainings.html', title='Validate External Trainings', trainings=pending_external_trainings)

@bp.route('/validate_external_trainings/approve/<int:training_id>', methods=['POST'])
@login_required
@admin_required
def approve_external_training(training_id):
    external_training = ExternalTraining.query.options(db.joinedload(ExternalTraining.skill_claims).joinedload(ExternalTrainingSkillClaim.skill)).get_or_404(training_id)
    external_training.status = ExternalTrainingStatus.APPROVED
    external_training.validator = current_user
    db.session.add(external_training)

    # Create competencies for each skill claim
    for skill_claim in external_training.skill_claims:
        competency = Competency(
            user=external_training.user,
            skill=skill_claim.skill,
            level=skill_claim.level,
            evaluation_date=external_training.date
        )
        db.session.add(competency)
        db.session.flush() # Flush to assign an ID to the new competency before modifying its relationships

        # Transfer species_claimed from ExternalTrainingSkillClaim to Competency
        competency.species = skill_claim.species_claimed

        # If user wants to be a tutor, add them to the skill's tutors
        if skill_claim.wants_to_be_tutor and external_training.user not in skill_claim.skill.tutors:
            skill_claim.skill.tutors.append(external_training.user)
    
    db.session.commit()
    flash('External training approved and competencies created!', 'success')
    return redirect(url_for('admin.validate_external_trainings'))

@bp.route('/validate_external_trainings/reject/<int:training_id>', methods=['POST'])
@login_required
@admin_required
def reject_external_training(training_id):
    external_training = ExternalTraining.query.get_or_404(training_id)
    external_training.status = ExternalTrainingStatus.REJECTED
    external_training.validator = current_user
    db.session.add(external_training)
    db.session.commit()
    flash('External training rejected.', 'info')
    return redirect(url_for('admin.validate_external_trainings'))

@bp.route('/training_requests')
@login_required
@admin_required
def list_training_requests():
    pending_training_requests = TrainingRequest.query.options(
        db.joinedload(TrainingRequest.requester),
        db.joinedload(TrainingRequest.skills_requested),
        db.joinedload(TrainingRequest.species_requested)
    ).filter_by(status=TrainingRequestStatus.PENDING).all()
    return render_template('admin/list_training_requests.html',
                           title='Pending Training Requests',
                           pending_training_requests=pending_training_requests)

# Reports (Placeholder)
@bp.route('/tutor_less_skills_report')
@login_required
@admin_required
def tutor_less_skills_report():
    # This will require a more complex query to find skills with no associated tutors
    skills_without_tutors = Skill.query.filter(~Skill.tutors.any()).all()
    return render_template('admin/tutor_less_skills_report.html', title='Skills Without Tutors Report', skills=skills_without_tutors)
