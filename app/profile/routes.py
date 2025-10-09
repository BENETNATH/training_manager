import os
import io
from flask import render_template, flash, redirect, url_for, current_app, request, send_file, abort, jsonify
from flask_login import login_required, current_user, logout_user
from werkzeug.utils import secure_filename
from sqlalchemy import func
import json
from fpdf import FPDF
from fpdf.html import HTMLMixin
from fpdf.fonts import FontFace
from app import db
from app.profile import bp
from app.profile.forms import EditProfileForm, TrainingRequestForm, ExternalTrainingForm, ProposeSkillForm, InitialRegulatoryTrainingForm, SubmitContinuousTrainingAttendanceForm, RequestContinuousTrainingEventForm
from app.models import User, Skill, Competency, TrainingRequest, ExternalTraining, SkillPracticeEvent, Species, TrainingRequestStatus, ExternalTrainingStatus, ExternalTrainingSkillClaim, TrainingSession, tutor_skill_association, InitialRegulatoryTraining, ContinuousTrainingEvent, UserContinuousTraining, UserContinuousTrainingStatus, InitialRegulatoryTrainingLevel, ContinuousTrainingEventStatus, ContinuousTrainingType
from app.decorators import permission_required

# ... existing code ...

@bp.route('/request_continuous_training_event', methods=['GET', 'POST'])
@login_required
@permission_required('self_request_continuous_training_event') # A new permission might be needed
def request_continuous_training_event():
    form = RequestContinuousTrainingEventForm()
    if form.validate_on_submit():
        attachment_path = None
        if form.attachment.data:
            filename = secure_filename(f"{current_user.id}_continuous_training_event_request_{datetime.utcnow().timestamp()}_{form.attachment.data.filename}")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'continuous_training_events_requests')
            os.makedirs(upload_path, exist_ok=True)
            form.attachment.data.save(os.path.join(upload_path, filename))
            attachment_path = f"uploads/continuous_training_events_requests/{filename}"

        new_event = ContinuousTrainingEvent(
            title=form.title.data,
            location=form.location.data,
            training_type=ContinuousTrainingType[form.training_type.data],
            event_date=form.event_date.data,
            attachment_path=attachment_path,
            description=form.notes.data, # Map notes to description
            creator_id=current_user.id,
            status=ContinuousTrainingEventStatus.PENDING,
            duration_hours=0.0 # Set to 0.0 initially, to be updated by validator
        )
        db.session.add(new_event)
        db.session.commit()

        flash('Votre demande d\'événement de formation continue a été soumise pour validation !', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Votre demande d\'événement de formation continue a été soumise pour validation !', 'redirect_url': url_for('profile.user_profile', username=current_user.full_name)})
        return redirect(url_for('profile.user_profile', username=current_user.full_name))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/request_continuous_training_event.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400

    # For GET requests or non-AJAX POST with validation errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/request_continuous_training_event.html', form=form)
    return render_template('profile/request_continuous_training_event.html', title='Demander un Événement de Formation Continue', form=form)
from app.email import send_email # Import send_email
from flask import current_app # Import current_app
from datetime import datetime, timedelta

class PDFWithFooter(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4', user_name="", generation_date=""):
        super().__init__(orientation, unit, format)
        self.user_name = user_name
        self.generation_date = generation_date

    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        footer_text = f'Booklet for {self.user_name} | Generated on {self.generation_date}'
        self.cell(0, 10, footer_text, 0, 0, 'L')
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'R')



@bp.route('/submit_initial_regulatory_training', methods=['GET', 'POST'])
@login_required
@permission_required('self_edit_profile') # Users can manage their own initial training
def submit_initial_regulatory_training():
    form = InitialRegulatoryTrainingForm()
    if form.validate_on_submit():
        if current_user.initial_regulatory_training:
            flash('Vous avez déjà enregistré une formation réglementaire initiale. Veuillez l\'éditer si nécessaire.', 'warning')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Vous avez déjà enregistré une formation réglementaire initiale.'}), 409 # Conflict
            return redirect(url_for('profile.edit_initial_regulatory_training'))

        attachment_path = None
        if form.attachment.data:
            filename = secure_filename(f"{current_user.id}_initial_reg_training_{datetime.utcnow().timestamp()}_{form.attachment.data.filename}")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'initial_regulatory_training')
            os.makedirs(upload_path, exist_ok=True)
            form.attachment.data.save(os.path.join(upload_path, filename))
            attachment_path = f"uploads/initial_regulatory_training/{filename}"

        initial_training = InitialRegulatoryTraining(
            user=current_user,
            level=InitialRegulatoryTrainingLevel[form.level.data],
            training_date=form.training_date.data,
            attachment_path=attachment_path
        )
        db.session.add(initial_training)
        db.session.commit()
        flash('Formation réglementaire initiale enregistrée avec succès !', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Formation réglementaire initiale enregistrée avec succès !', 'redirect_url': url_for('profile.user_profile', username=current_user.full_name)})
        return redirect(url_for('profile.user_profile', username=current_user.full_name))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Re-render the form with errors and return as JSON
            form_html = render_template('profile/submit_initial_regulatory_training.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400
    
    # For GET requests or non-AJAX POST with validation errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/submit_initial_regulatory_training.html', form=form)
    return render_template('profile/submit_initial_regulatory_training.html', title='Enregistrer Formation Initiale', form=form)

@bp.route('/edit_initial_regulatory_training', methods=['GET', 'POST'])
@login_required
@permission_required('self_edit_profile')
def edit_initial_regulatory_training():
    initial_training = current_user.initial_regulatory_training
    if not initial_training:
        flash('Aucune formation réglementaire initiale enregistrée. Veuillez en ajouter une.', 'info')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Aucune formation réglementaire initiale enregistrée.'}), 404
        return redirect(url_for('profile.submit_initial_regulatory_training'))

    form = InitialRegulatoryTrainingForm(obj=initial_training)
    if form.validate_on_submit():
        initial_training.level = InitialRegulatoryTrainingLevel[form.level.data]
        initial_training.training_date = form.training_date.data

        if form.attachment.data:
            # Delete old attachment if exists
            if initial_training.attachment_path:
                old_path = os.path.join(current_app.root_path, 'static', initial_training.attachment_path)
                if os.path.exists(old_path):
                    os.remove(old_path)

            filename = secure_filename(f"{current_user.id}_initial_reg_training_{datetime.utcnow().timestamp()}_{form.attachment.data.filename}")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'initial_regulatory_training')
            os.makedirs(upload_path, exist_ok=True)
            form.attachment.data.save(os.path.join(upload_path, filename))
            initial_training.attachment_path = f"uploads/initial_regulatory_training/{filename}"
        
        db.session.commit()
        flash('Formation réglementaire initiale mise à jour avec succès !', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Formation réglementaire initiale mise à jour avec succès !', 'redirect_url': url_for('profile.user_profile', username=current_user.full_name)})
        return redirect(url_for('profile.user_profile', username=current_user.full_name))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/submit_initial_regulatory_training.html', form=form, initial_training=initial_training)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400
    elif request.method == 'GET':
        form.level.data = initial_training.level.name
        form.training_date.data = initial_training.training_date

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/submit_initial_regulatory_training.html', form=form, initial_training=initial_training)
    return render_template('profile/submit_initial_regulatory_training.html', title='Éditer Formation Initiale', form=form, initial_training=initial_training)

@bp.route('/submit_continuous_training_attendance', methods=['GET', 'POST'])
@login_required
@permission_required('self_submit_continuous_training_attendance') # Use the new specific permission
def submit_continuous_training_attendance():
    form = SubmitContinuousTrainingAttendanceForm()

    # Populate choices for the event field for server-side validation
    approved_events = ContinuousTrainingEvent.query.filter_by(status=ContinuousTrainingEventStatus.APPROVED).order_by(ContinuousTrainingEvent.event_date.desc()).all()
    form.event.choices = [(str(event.id), f"{event.title} ({event.event_date.strftime('%Y-%m-%d')}) - {event.location or 'N/A'}") for event in approved_events]

    if form.validate_on_submit():
        attendance_attachment_path = None
        if form.attendance_attachment.data:
            filename = secure_filename(f"{current_user.id}_continuous_training_attendance_{datetime.utcnow().timestamp()}_{form.attendance_attachment.data.filename}")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'continuous_training_attendance')
            os.makedirs(upload_path, exist_ok=True)
            form.attendance_attachment.data.save(os.path.join(upload_path, filename))
            attendance_attachment_path = f"uploads/continuous_training_attendance/{filename}"

        # Fetch the ContinuousTrainingEvent object using the ID from form.event.data
        selected_event = ContinuousTrainingEvent.query.get(form.event.data)
        if not selected_event:
            flash('L\'événement de formation continue sélectionné est introuvable.', 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'L\'événement de formation continue sélectionné est introuvable.'}), 400
            return redirect(url_for('profile.user_profile', username=current_user.full_name))

        user_ct = UserContinuousTraining(
            user=current_user,
            event=selected_event,  # Pass the ContinuousTrainingEvent object
            attendance_attachment_path=attendance_attachment_path,
            status=UserContinuousTrainingStatus.PENDING
        )
        db.session.add(user_ct)
        db.session.commit()
        flash('Votre participation à la formation continue a été soumise pour validation !', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Votre participation à la formation continue a été soumise pour validation !', 'redirect_url': url_for('profile.user_profile', username=current_user.full_name)})
        return redirect(url_for('profile.user_profile', username=current_user.full_name))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/submit_continuous_training_attendance.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400

    # For GET requests or non-AJAX POST with validation errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/submit_continuous_training_attendance.html', form=form, ContinuousTrainingType=ContinuousTrainingType)
    return render_template('profile/submit_continuous_training_attendance.html', title='Soumettre une Participation à une Formation Continue', form=form, ContinuousTrainingType=ContinuousTrainingType)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
@permission_required('self_edit_profile')
def edit_profile():
    form = EditProfileForm(original_email=current_user.email)
    if form.validate_on_submit():
        # Handle password change
        if form.password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Incorrect current password.', 'danger')
                return redirect(url_for('profile.edit_profile'))
            current_user.set_password(form.password.data)
            flash('Your password has been changed.', 'success')

        # Handle email change
        if form.new_email.data and form.new_email.data != current_user.email:
            current_user.new_email = form.new_email.data
            token = current_user.generate_email_confirmation_token()
            db.session.commit()
            send_email('[Training Manager] Confirm Your Email Change',
                       sender=current_app.config['MAIL_USERNAME'],
                       recipients=[current_user.new_email],
                       text_body=render_template('email/email_change_confirmation.txt', user=current_user, token=token),
                       html_body=render_template('email/email_change_confirmation.html', user=current_user, token=token))
            flash('A confirmation email has been sent to your new email address. Please check your inbox to complete the change.', 'info')
            return redirect(url_for('profile.user_profile', username=current_user.full_name))

        current_user.full_name = form.full_name.data
        current_user.study_level = form.study_level.data
        db.session.commit()
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('profile.user_profile', username=current_user.full_name))
    elif request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.study_level.data = current_user.study_level
    return render_template('profile/edit_profile.html', title='Edit Profile', form=form)

@bp.route('/confirm_email/<token>')
def confirm_email(token):
    user = User.query.filter_by(email_confirmation_token=token).first()
    if user and user.verify_email_confirmation_token(token):
        user.email = user.new_email
        user.new_email = None
        user.email_confirmation_token = None
        db.session.commit()
        flash('Your email address has been updated!', 'success')
        # Log out the user as their email (which is used for login) has changed
        logout_user()
        return redirect(url_for('auth.login'))
    else:
        flash('The email confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('root.index'))

@bp.route('/user/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(full_name=username).first_or_404()
    db.session.refresh(user) # Refresh the user object to get latest data
    if user.id != current_user.id and not current_user.can('user_manage'):
        abort(403)
    
    # Get all competencies for the user
    competencies = user.competencies

    # Get all training paths assigned to the user
    assigned_paths = user.assigned_training_paths

    # Get all skills from the assigned training paths
    required_skills = {skill_assoc.skill for path in assigned_paths for skill_assoc in path.skills_association}

    # Get all skills the user is competent in
    competent_skills = {comp.skill for comp in competencies}

    # Determine the skills the user still needs to acquire
    required_skills_todo = list(required_skills - competent_skills)

    # Get pending training requests for the user
    pending_training_requests_by_user = TrainingRequest.query.filter_by(requester_id=user.id, status=TrainingRequestStatus.PENDING).all()

    # Get upcoming and completed training sessions for the user
    now = datetime.utcnow()
    upcoming_training_sessions_by_user = [sess for sess in user.attended_training_sessions if sess.start_time > now]
    completed_training_sessions_by_user = [sess for sess in user.attended_training_sessions if sess.start_time <= now]

    # Get initial regulatory training
    initial_regulatory_training = user.initial_regulatory_training

    # Get continuous training data
    continuous_trainings_attended = user.continuous_trainings_attended.join(ContinuousTrainingEvent).filter(UserContinuousTraining.status == UserContinuousTrainingStatus.APPROVED).order_by(ContinuousTrainingEvent.event_date.desc()).all()
    total_continuous_training_hours_6_years = user.total_continuous_training_hours_6_years
    live_continuous_training_hours_6_years = user.live_continuous_training_hours_6_years
    online_continuous_training_hours_6_years = user.online_continuous_training_hours_6_years
    required_continuous_training_hours = user.required_continuous_training_hours
    is_continuous_training_compliant = user.is_continuous_training_compliant
    live_training_ratio = user.live_training_ratio
    is_live_training_ratio_compliant = user.is_live_training_ratio_compliant
    is_at_risk_next_year = user.is_at_risk_next_year
    continuous_training_summary_by_year = user.continuous_training_summary_by_year

    return render_template('profile/user_profile.html', 
                           user=user, 
                           competencies=competencies,
                           required_skills_todo=required_skills_todo,
                           pending_training_requests_by_user=pending_training_requests_by_user,
                           upcoming_training_sessions_by_user=upcoming_training_sessions_by_user,
                           completed_training_sessions_by_user=completed_training_sessions_by_user,
                           initial_regulatory_training=initial_regulatory_training,
                           continuous_trainings_attended=continuous_trainings_attended,
                           total_continuous_training_hours_6_years=total_continuous_training_hours_6_years,
                           live_continuous_training_hours_6_years=live_continuous_training_hours_6_years,
                           online_continuous_training_hours_6_years=online_continuous_training_hours_6_years,
                           required_continuous_training_hours=required_continuous_training_hours,
                           is_continuous_training_compliant=is_continuous_training_compliant,
                           live_training_ratio=live_training_ratio,
                           is_live_training_ratio_compliant=is_live_training_ratio_compliant,
                           is_at_risk_next_year=is_at_risk_next_year,
                           continuous_training_summary_by_year=continuous_training_summary_by_year,
                           datetime=datetime,
                           timedelta=timedelta)

@bp.route('/request-training', methods=['GET', 'POST'])
@login_required
@permission_required('self_submit_training_request')
def submit_training_request():
    form = TrainingRequestForm()

    def get_skills_for_species(species_id):
        if species_id:
            return Skill.query.join(Skill.species).filter(Species.id == species_id).order_by(Skill.name).all()
        return Skill.query.filter(False).all() # Return an empty query if no species selected

    if request.method == 'POST':
        species_id = request.form.get('species')
        form.skills_requested.query_factory = lambda: get_skills_for_species(species_id)
    else:
        # For GET requests or initial form rendering, if a species is pre-selected
        initial_species_id = form.species.data.id if form.species.data else None
        form.skills_requested.query_factory = lambda: get_skills_for_species(initial_species_id)

    if form.validate_on_submit():
        selected_skills = form.skills_requested.data
        selected_species_list = form.species.data # Now a list of species
        
        if not selected_species_list:
            flash('Please select at least one species for the training request.', 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Please select at least one species for the training request.'}), 400
            return redirect(url_for('profile.user_profile'))

        successful_requests_messages = []
        existing_requests_messages = []
        errors_occurred = False

        for skill in selected_skills:
            for species in selected_species_list:
                # Check for existing pending request
                existing_req = TrainingRequest.query.filter_by(
                    requester=current_user,
                    status=TrainingRequestStatus.PENDING
                ).join(TrainingRequest.skills_requested).filter(Skill.id == skill.id).join(TrainingRequest.species_requested).filter(Species.id == species.id).first()

                if existing_req:
                    existing_requests_messages.append(f"Request for '{skill.name}' on '{species.name}' already exists and is pending.")
                    continue # Skip creating this request

                # Create new TrainingRequest
                req = TrainingRequest(requester=current_user, status=TrainingRequestStatus.PENDING)
                db.session.add(req)
                
                req.skills_requested.append(skill)
                req.species_requested.append(species) # Each request is for a single species

                successful_requests_messages.append(f"Request for '{skill.name}' on '{species.name}' created.")
                current_app.logger.info(f"Created new TrainingRequest: {req} for skill: {skill.name} and species: {species.name}")

        try:
            db.session.commit()
            
            # Flash messages for successful and existing requests
            for msg in successful_requests_messages:
                flash(msg, 'success')
            for msg in existing_requests_messages:
                flash(msg, 'info') # Use info for existing requests

            if errors_occurred: # This flag is currently not set, but kept for future potential errors
                flash('Some errors occurred during submission.', 'danger')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Combine messages for AJAX response
                all_messages = successful_requests_messages + existing_requests_messages
                if errors_occurred:
                    all_messages.append('Some errors occurred during submission.')
                return jsonify({'success': not errors_occurred, 'message': '; '.join(all_messages), 'redirect_url': url_for('profile.user_profile')})
            
            return redirect(url_for('profile.user_profile'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing training request: {e}")
            flash('An unexpected error occurred during submission.', 'danger')
            errors_occurred = True # Mark that an error occurred

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'An unexpected error occurred during submission.'}), 500
            return redirect(url_for('profile.user_profile'))
    elif request.method == 'POST': # Validation failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_training_request_form.html', form=form, api_key=current_user.api_key)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'})

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_training_request_form.html', form=form, api_key=current_user.api_key)

    return render_template('profile/submit_training_request.html', title='Submit Training Request', form=form)

@bp.route('/propose-skill', methods=['GET', 'POST'])
@login_required
def propose_skill():
    form = ProposeSkillForm()
    if form.validate_on_submit():
        # Create a TrainingRequest with a special status for proposed skills
        req = TrainingRequest(
            requester=current_user,
            status=TrainingRequestStatus.PROPOSED_SKILL,
            notes=f"Proposed Skill: {form.name.data} - Description: {form.description.data}"
        )
        db.session.add(req)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Votre proposition de compétence a été soumise aux administrateurs.', 'redirect_url': url_for('profile.user_profile')})
        flash('Votre proposition de compétence a été soumise aux administrateurs.', 'success')
        return redirect(url_for('profile.user_profile'))
    elif request.method == 'POST': # Validation failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_propose_skill_form.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'})

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_propose_skill_form.html', form=form)

    return render_template('profile/propose_skill.html', title='Proposer une Compétence', form=form)

@bp.route('/submit-external-training', methods=['GET', 'POST'])
@login_required
@permission_required('self_submit_external_training')
def submit_external_training():
    form = ExternalTrainingForm()
    if form.validate_on_submit():
        ext_training = ExternalTraining(
            user=current_user,
            external_trainer_name=form.external_trainer_name.data,
            date=form.date.data,
            status=ExternalTrainingStatus.PENDING
        )
        if form.attachment.data:
            filename = secure_filename(f"{current_user.id}_{datetime.utcnow().timestamp()}_{form.attachment.data.filename}")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'external')
            os.makedirs(upload_path, exist_ok=True)
            form.attachment.data.save(os.path.join(upload_path, filename))
            ext_training.attachment_path = f"uploads/external/{filename}"
        
        db.session.add(ext_training)

        for skill_claim_data in form.skill_claims.data:
            skill_claim = ExternalTrainingSkillClaim(
                skill=skill_claim_data['skill'],
                level=skill_claim_data['level'],
                species_claimed=skill_claim_data['species_claimed'],
                wants_to_be_tutor=skill_claim_data['wants_to_be_tutor'],
                practice_date=skill_claim_data['practice_date']
            )
            ext_training.skill_claims.append(skill_claim)

        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Votre formation externe a été soumise pour validation.', 'redirect_url': url_for('profile.user_profile')})
        flash('External training submitted for validation!', 'success')
        return redirect(url_for('profile.user_profile'))
    elif request.method == 'POST': # Validation failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_external_training_form.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'})

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        all_skills = [{'id': skill.id, 'name': skill.name} for skill in Skill.query.order_by(Skill.name).all()]
        all_species = [{'id': species.id, 'name': species.name} for species in Species.query.order_by(Species.name).all()]
        return render_template('profile/_external_training_form.html', form=form, all_skills_json=json.dumps(all_skills), all_species_json=json.dumps(all_species))

    all_skills = [{'id': skill.id, 'name': skill.name} for skill in Skill.query.order_by(Skill.name).all()]
    all_species = [{'id': species.id, 'name': species.name} for species in Species.query.order_by(Species.name).all()]
    return render_template('profile/submit_external_training.html', title='Submit External Training', form=form, all_skills_json=json.dumps(all_skills), all_species_json=json.dumps(all_species))

@bp.route('/declare-practice', methods=['GET', 'POST'])
@login_required
@permission_required('self_declare_skill_practice')
def declare_skill_practice():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400

        try:
            for item in data:
                competency_id = item.get('competency_id')
                practice_date_str = item.get('practice_date')
                new_level = item.get('level')
                wants_to_be_tutor = item.get('wants_to_be_tutor', False) # Get the new flag

                competency = Competency.query.get(competency_id)
                if not competency or competency.user_id != current_user.id:
                    return jsonify({'success': False, 'message': f'Competency {competency_id} not found or not owned by user.'}), 403

                # Update competency level if provided and different
                if new_level and new_level != competency.level:
                    competency.level = new_level

                # Create SkillPracticeEvent if practice_date is provided
                if practice_date_str:
                    practice_date = datetime.fromisoformat(practice_date_str.replace('Z', '+00:00')) # Handle 'Z' for UTC
                    
                    existing_event = SkillPracticeEvent.query.filter_by(
                        user_id=current_user.id,
                        practice_date=practice_date
                    ).filter(SkillPracticeEvent.skills.any(id=competency.skill_id)).first()

                    if not existing_event:
                        event = SkillPracticeEvent(
                            user=current_user,
                            practice_date=practice_date,
                            notes=f"Practice declared via batch update for skill: {competency.skill.name}"
                        )
                        event.skills.append(competency.skill)
                        db.session.add(event)
                    else:
                        pass # Optionally update notes or just skip if event exists
                
                # Add user as tutor if wants_to_be_tutor is true
                if wants_to_be_tutor:
                    if current_user not in competency.skill.tutors:
                        competency.skill.tutors.append(current_user)
                else: # wants_to_be_tutor is false, so remove if they are a tutor
                    if current_user in competency.skill.tutors:
                        competency.skill.tutors.remove(current_user)

            db.session.commit()
            return jsonify({'success': True, 'message': 'Pratiques et niveaux mis à jour avec succès !', 'redirect_url': url_for('profile.user_profile')})
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating practices: {e}")
            return jsonify({'success': False, 'message': f'Erreur lors de la mise à jour des pratiques: {str(e)}'}), 500

    # GET Request handling
    user_competencies = current_user.competencies
    competencies_data = []
    for comp in user_competencies:
        # Ensure latest_practice_date is calculated as in user_profile
        practice_event = SkillPracticeEvent.query.filter(
            SkillPracticeEvent.user_id == current_user.id,
            SkillPracticeEvent.skills.any(id=comp.skill_id)
        ).order_by(SkillPracticeEvent.practice_date.desc()).first()
        
        comp_latest_practice_date = comp.evaluation_date 
        if practice_event and practice_event.practice_date > comp_latest_practice_date:
            comp_latest_practice_date = practice_event.practice_date
        elif comp.latest_practice_date: # If already calculated in user_profile context
             comp_latest_practice_date = comp.latest_practice_date

        competencies_data.append({
            'competency_id': comp.id,
            'skill_name': comp.skill.name,
            'skill_id': comp.skill.id,
            'species': [{'id': s.id, 'name': s.name} for s in comp.species],
            'current_level': comp.level,
            'latest_practice_date': comp_latest_practice_date.isoformat() if comp_latest_practice_date else None,
            'is_tutor': current_user in comp.skill.tutors # NEW: Add tutor status
        })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_declare_skill_practice_form.html', competencies=competencies_data)

    return render_template('profile/declare_skill_practice.html', title='Declare Skill Practice', competencies=competencies_data)

@bp.route('/generate-api-key', methods=['POST'])
@login_required
def generate_api_key():
    new_key = current_user.generate_api_key()
    db.session.commit() # Commit the new API key to the database
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Nouvelle clé API générée avec succès !', 'api_key': new_key})
    flash(f"Your new API Key has been generated. Please store it securely, it will not be shown again: {new_key}", 'success')
    return redirect(url_for('profile.user_profile'))

@bp.route('/api/continuous_training_events/search')
@login_required
def search_continuous_training_events():
    query = request.args.get('q', '').strip()
    event_type = request.args.get('type', '').strip()
    event_date_str = request.args.get('date', '').strip()

    events_query = ContinuousTrainingEvent.query.filter_by(status=ContinuousTrainingEventStatus.APPROVED)

    if query:
        events_query = events_query.filter(
            (ContinuousTrainingEvent.title.ilike(f'%{query}%')) |
            (ContinuousTrainingEvent.location.ilike(f'%{query}%'))
        )
    
    if event_type:
        try:
            valid_type = ContinuousTrainingType[event_type.upper()]
            events_query = events_query.filter_by(training_type=valid_type)
        except KeyError:
            pass

    if event_date_str:
        try:
            search_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            events_query = events_query.filter(
                db.func.date(ContinuousTrainingEvent.event_date) == search_date
            )
        except ValueError:
            pass

    events = events_query.order_by(ContinuousTrainingEvent.event_date.desc()).limit(20).all()

    results = []
    for event in events:
        results.append({
            'id': event.id,
            'text': f"{event.title} ({event.event_date.strftime('%Y-%m-%d')}) - {event.location or 'N/A'}"
        })
    return jsonify({'results': results})

@bp.route('/competency/<int:competency_id>/certificate.pdf')
@login_required
def generate_certificate(competency_id):
    comp = Competency.query.get_or_404(competency_id)
    if comp.user_id != current_user.id and not current_user.can('view_any_certificate'):
        abort(403)

    pdf = FPDF(orientation='L', unit='mm', format='A4') # Landscape A4
    pdf.add_page()
    pdf.set_auto_page_break(auto=False, margin=0)

    # Colors
    blue = (0, 123, 255)
    dark_gray = (52, 58, 64)
    green = (40, 167, 69)
    yellow = (255, 193, 7)
    light_gray = (108, 117, 125)

    # Border
    pdf.set_draw_color(*blue)
    pdf.set_line_width(3)
    pdf.rect(5, 5, 287, 200) # A4 landscape is 297x210 mm, inner border

    # Certificate Header
    pdf.set_font('Times', 'B', 36)
    pdf.set_text_color(*blue)
    pdf.ln(20) # Move down
    pdf.cell(0, 15, 'CERTIFICATE OF COMPETENCY', 0, 1, 'C')

    # Subheader
    pdf.set_font('Times', '', 20)
    pdf.set_text_color(*dark_gray)
    pdf.ln(10)
    pdf.cell(0, 10, 'This certifies that', 0, 1, 'C')

    # Recipient Name
    pdf.set_font('Times', 'B', 30)
    pdf.set_text_color(*green)
    pdf.ln(5)
    pdf.cell(0, 15, comp.user.full_name, 0, 1, 'C')

    # Skill Introduction
    pdf.set_font('Times', '', 18)
    pdf.set_text_color(*dark_gray)
    pdf.ln(10)
    pdf.multi_cell(0, 10, 'has successfully demonstrated competency in the skill of', 0, 'C')

    # Skill Name
    pdf.set_font('Times', 'B', 26)
    pdf.set_text_color(*yellow)
    pdf.ln(5)
    pdf.cell(0, 15, comp.skill.name, 0, 1, 'C')

    # Species (if any)
    if comp.species:
        species_names = ", ".join([s.name for s in comp.species])
        pdf.set_font('Times', '', 14)
        pdf.set_text_color(*light_gray)
        pdf.ln(5)
        pdf.multi_cell(0, 8, f'Associated Species: {species_names}', 0, 'C')

    # Competency Level
    pdf.set_font('Times', '', 18)
    pdf.set_text_color(*dark_gray)
    pdf.ln(5)
    pdf.multi_cell(0, 10, f'at a {comp.level} level.', 0, 'C')

    # Awarded Date and Evaluator
    pdf.set_font('Times', '', 14)
    pdf.set_text_color(*light_gray)
    pdf.ln(5)
    pdf.cell(0, 8, f'Awarded on: {comp.evaluation_date.strftime("%B %d, %Y")}', 0, 1, 'C')
    evaluator_name = "N/A"
    if comp.external_evaluator_name:
        evaluator_name = comp.external_evaluator_name
    elif comp.evaluator:
        evaluator_name = comp.evaluator.full_name
    pdf.cell(0, 8, f'Evaluated by: {evaluator_name}', 0, 1, 'C')

    pdf_output = pdf.output(dest='S')
    
    return send_file(io.BytesIO(pdf_output), as_attachment=True,
                     download_name=f"certificate_{comp.user.full_name.replace(' ', '_')}_{comp.skill.name.replace(' ', '_')}.pdf",
                     mimetype='application/pdf')


@bp.route('/<int:user_id>/booklet.pdf')
@login_required
def generate_user_booklet_pdf(user_id):
    if user_id != current_user.id and not current_user.can('view_any_booklet'):
        abort(403)
    user = User.query.get_or_404(user_id)
    
    competencies = user.competencies

    # 2. INSTANTIATE YOUR NEW CUSTOM CLASS
    generation_date_str = datetime.utcnow().strftime("%Y-%m-%d")
    pdf = PDFWithFooter(
        orientation='L', 
        unit='mm', 
        format='A4',
        user_name=user.full_name,
        generation_date=generation_date_str
    )
    
    # 3. ENABLE TOTAL PAGE COUNT ALIAS
    pdf.alias_nb_pages()
    
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Colors
    blue = (0, 123, 255)
    dark_gray = (52, 58, 64)
    green = (40, 167, 69)
    red = (220, 53, 69)
    orange = (253, 126, 20)

    # Title Page
    pdf.set_font('Times', 'B', 24)
    pdf.set_text_color(*blue)
    pdf.cell(0, 20, 'Competency Booklet', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Times', '', 18)
    pdf.set_text_color(*dark_gray)
    pdf.cell(0, 10, f'for {user.full_name}', 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font('Times', '', 12)
    pdf.cell(0, 10, f'Generated on: {generation_date_str}', 0, 1, 'C')
    
    pdf.set_font('Times', 'B', 16)
    pdf.set_text_color(*dark_gray)
    pdf.cell(0, 10, 'Overview of Competencies', 0, 1, 'L')
    pdf.ln(5)

    if not competencies:
        pdf.set_font('Times', '', 12)
        pdf.cell(0, 10, 'No competencies recorded.', 0, 1, 'L')
    else:
        # Prepare table data
        headings = ("Skill", "Level", "Evaluated", "Evaluator", "Last Practice", "Recycling Due", "Status", "Species")
        
        data = []
        for comp in competencies:
            recycling_due = "N/A"
            status_text = "Unlimited"
            
            if comp.skill.validity_period_months:
                recycling_due = comp.recycling_due_date.strftime("%Y-%m-%d")
                if comp.needs_recycling:
                    status_text = "Expired"
                elif comp.warning_date and datetime.utcnow() > comp.warning_date:
                    status_text = "Recycling Soon"
                else:
                    status_text = "Valid"
            
            data.append((
                comp.skill.name,
                comp.level or "N/A",
                comp.evaluation_date.strftime("%Y-%m-%d"),
                comp.external_evaluator_name if comp.external_evaluator_name else (comp.evaluator.full_name if comp.evaluator else "N/A"),
                comp.latest_practice_date.strftime("%Y-%m-%d") if comp.latest_practice_date else "N/A",
                recycling_due,
                status_text,
                ", ".join([s.name for s in comp.species]) if comp.species else "N/A"
            ))

        # Create the table using the pdf.table() API
        pdf.set_font("Times", size=8)
        pdf.set_draw_color(0, 0, 0)
        
        with pdf.table(
            col_widths=(60, 25, 25, 40, 25, 25, 25, 42),
            text_align=("LEFT", "CENTER", "CENTER", "LEFT", "CENTER", "CENTER", "CENTER", "LEFT"),
            headings_style=FontFace(emphasis="B", color=dark_gray, fill_color=(200, 220, 255))
        ) as table:
            # Render header row
            header_row = table.row()
            for heading in headings:
                header_row.cell(heading)
            
            # Render data rows
            for data_row in data:
                row = table.row()
                for i, datum in enumerate(data_row):
                    if i == 6: # Special handling for the Status cell
                        if datum == "Valid":
                            pdf.set_text_color(*green)
                        elif datum == "Recycling Soon":
                            pdf.set_text_color(*orange)
                        elif datum == "Expired":
                            pdf.set_text_color(*red)
                        
                        row.cell(datum)
                        pdf.set_text_color(*dark_gray) # Reset color
                    else:
                        row.cell(datum)

    pdf_output = pdf.output()
    
    return send_file(io.BytesIO(pdf_output), as_attachment=True,
                     download_name=f"booklet_{user.full_name.replace(' ', '_')}.pdf",
                     mimetype='application/pdf')

@bp.route('/training_requests/delete/<int:request_id>', methods=['POST'])
@login_required
def delete_training_request(request_id):
    training_request = TrainingRequest.query.get_or_404(request_id)
    if training_request.requester != current_user and not current_user.can('training_request_manage'):
        abort(403)
    db.session.delete(training_request)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Training request deleted successfully!'})
@bp.route('/external_training/<int:training_id>')
@login_required
def show_external_training(training_id):
    external_training = ExternalTraining.query.options(
        db.joinedload(ExternalTraining.user),
        db.joinedload(ExternalTraining.validator),
        db.joinedload(ExternalTraining.skill_claims).joinedload(ExternalTrainingSkillClaim.skill),
        db.joinedload(ExternalTraining.skill_claims).joinedload(ExternalTrainingSkillClaim.species_claimed)
    ).get_or_404(training_id)

    # Ensure the current user is either the owner of the external training or an admin
    if external_training.user_id != current_user.id and not current_user.can('external_training_validate'):
        abort(403)

    return render_template('profile/view_external_training.html',
                           title='External Training Details',
                           external_training=external_training)

@bp.route('/skills')
@login_required
def skills_list():
    form = ProposeSkillForm()
    skills_query = db.session.query(
        Skill,
        func.count(func.distinct(Competency.user_id)).label('user_count'),
        func.count(func.distinct(tutor_skill_association.c.user_id)).label('tutor_count')
    ).outerjoin(Competency, Skill.id == Competency.skill_id) \
     .outerjoin(tutor_skill_association, Skill.id == tutor_skill_association.c.skill_id) \
     .options(db.joinedload(Skill.species)) \
     .group_by(Skill.id)

    skill_name = request.args.get('skill_name', '')
    if skill_name:
        skills_query = skills_query.filter(Skill.name.ilike(f'%{skill_name}%'))

    skills_data = skills_query.order_by(Skill.name).all()

    return render_template('profile/skills_list.html',
                           title='Available Skills',
                           skills_data=skills_data,
                           skill_name=skill_name,
                           form=form)