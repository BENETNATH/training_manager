import os
import io
from flask import render_template, flash, redirect, url_for, current_app, request, send_file, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from weasyprint import HTML
from datetime import datetime, timedelta

from app import db, mail
from app.profile import bp
from app.models import User, Competency, Skill, SkillPracticeEvent, TrainingRequest, TrainingRequestStatus, ExternalTraining, ExternalTrainingStatus, TrainingSession
from app.profile.forms import TrainingRequestForm, ExternalTrainingForm, SkillPracticeEventForm, ProposeSkillForm

@bp.route('/<int:user_id>')
@bp.route('/')
@login_required
def user_profile(user_id=None):
    if user_id:
        if not current_user.is_admin:
            abort(403) # Only admins can view other users' profiles
        user = User.query.get_or_404(user_id)
    else:
        user = current_user

    # --- Logique du Parcours de Formation ---
    all_required_skills = set()
    for path in user.assigned_training_paths:
        for skill in path.skills:
            all_required_skills.add(skill)
    
    user_competencies = user.competencies.all()
    acquired_skills = {comp.skill for comp in user_competencies}
    required_skills_todo = list(all_required_skills - acquired_skills)
    
    # --- Logique de Recyclage et Dernière Pratique ---
    for comp in user_competencies:
        practice_event = SkillPracticeEvent.query.filter_by(
            user_id=user.id
        ).join(SkillPracticeEvent.skills).filter_by(
            id=comp.skill_id
        ).order_by(SkillPracticeEvent.practice_date.desc()).first()
        
        comp.latest_practice_date = comp.evaluation_date
        if practice_event and practice_event.practice_date > comp.evaluation_date:
            comp.latest_practice_date = practice_event.practice_date
        
        if comp.skill.validity_period_months:
            recycling_due_date = comp.latest_practice_date + timedelta(days=comp.skill.validity_period_months * 30.44)
            comp.needs_recycling = datetime.utcnow() > recycling_due_date
            comp.recycling_due_date = recycling_due_date
            comp.warning_date = recycling_due_date - timedelta(days=comp.skill.validity_period_months * 30.44 / 4)
        else:
            comp.needs_recycling = False
            comp.recycling_due_date = None
            comp.warning_date = None

    # --- Demandes de formation en cours ---
    pending_training_requests_by_user = TrainingRequest.query.filter(
        TrainingRequest.requester == user,
        TrainingRequest.status.in_([TrainingRequestStatus.PENDING, TrainingRequestStatus.PROPOSED_SKILL])
    ).order_by(TrainingRequest.request_date.desc()).all()

    # --- Sessions de formation passées et à venir ---
    now = datetime.utcnow()
    upcoming_training_sessions_by_user = TrainingSession.query.join(TrainingSession.attendees).filter(
        User.id == user.id,
        TrainingSession.start_time > now
    ).order_by(TrainingSession.start_time.asc()).all()
    completed_training_sessions_by_user = TrainingSession.query.join(TrainingSession.attendees).filter(
        User.id == user.id,
        TrainingSession.end_time <= now
    ).order_by(TrainingSession.end_time.desc()).all()

    return render_template('profile/user_profile.html', 
                           title=f"{user.full_name}'s Profile", 
                           user=user,
                           competencies=user_competencies,
                           required_skills_todo=required_skills_todo,
                           pending_training_requests_by_user=pending_training_requests_by_user,
                           upcoming_training_sessions_by_user=upcoming_training_sessions_by_user,
                           completed_training_sessions_by_user=completed_training_sessions_by_user,
                           datetime=datetime,
                           TrainingRequestStatus=TrainingRequestStatus)

@bp.route('/request-training', methods=['GET', 'POST'])
@login_required
def submit_training_request():
    form = TrainingRequestForm()
    if form.validate_on_submit():
        req = TrainingRequest(requester=current_user, status=TrainingRequestStatus.PENDING)
        req.skills_requested = form.skills_requested.data
        req.species_requested = form.species_requested.data
        db.session.add(req)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Votre demande de formation a été soumise avec succès !', 'redirect_url': url_for('profile.user_profile')})
        flash('Your training request has been submitted!', 'success')
        return redirect(url_for('profile.user_profile'))
    elif request.method == 'POST': # Validation failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_training_request_form.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'})

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_training_request_form.html', form=form)

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

    return render_template('profile/propose_skill_form.html', title='Proposer une Compétence', form=form)

@bp.route('/submit-external-training', methods=['GET', 'POST'])
@login_required
def submit_external_training():
    form = ExternalTrainingForm()
    if form.validate_on_submit():
        ext_training = ExternalTraining(
            user=current_user,
            external_trainer_name=form.external_trainer_name.data,
            date=form.date.data,
            status=ExternalTrainingStatus.PENDING,
            skills_claimed=form.skills_claimed.data
        )
        if form.attachment.data:
            filename = secure_filename(f"{current_user.id}_{datetime.utcnow().timestamp()}_{form.attachment.data.filename}")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'external')
            os.makedirs(upload_path, exist_ok=True)
            form.attachment.data.save(os.path.join(upload_path, filename))
            ext_training.attachment_path = f"uploads/external/{filename}"
        
        db.session.add(ext_training)
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
        return render_template('profile/_external_training_form.html', form=form)

    return render_template('profile/submit_external_training.html', title='Submit External Training', form=form)

@bp.route('/declare-practice', methods=['GET', 'POST'])
@login_required
def declare_skill_practice():
    form = SkillPracticeEventForm()
    if form.validate_on_submit():
        event = SkillPracticeEvent(
            user=current_user,
            practice_date=form.practice_date.data,
            notes=form.notes.data
        )
        event.skills = form.skills.data # Assign multiple skills
        db.session.add(event)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            skill_names = ', '.join([s.name for s in form.skills.data])
            return jsonify({'success': True, 'message': f'Pratique pour les compétences "{skill_names}" déclarée avec succès !', 'redirect_url': url_for('profile.user_profile')})
        flash(f'Practice for skills "{form.skills.data}" has been declared.', 'success')
        return redirect(url_for('profile.user_profile'))
    elif request.method == 'POST': # Validation failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_declare_skill_practice_form.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'})

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_declare_skill_practice_form.html', form=form)

    return render_template('profile/declare_skill_practice.html', title='Declare Skill Practice', form=form)

@bp.route('/generate-api-key', methods=['POST'])
@login_required
def generate_api_key():
    new_key = current_user.generate_api_key()
    db.session.commit() # Commit the new API key to the database
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Nouvelle clé API générée avec succès !', 'api_key': new_key})
    flash(f"Your new API Key has been generated. Please store it securely, it will not be shown again: {new_key}", 'success')
    return redirect(url_for('profile.user_profile'))

@bp.route('/competency/<int:competency_id>/certificate.pdf')
@login_required
def generate_certificate(competency_id):
    comp = Competency.query.get_or_404(competency_id)
    if comp.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    html = render_template('certificates/certificate.html', competency=comp)
    pdf = HTML(string=html, base_url=request.url_root).write_pdf()
    
    return send_file(io.BytesIO(pdf), as_attachment=True,
                     download_name=f"certificate_{comp.user.full_name.replace(' ', '_')}_{comp.skill.name.replace(' ', '_')}.pdf",
                     mimetype='application/pdf')

@bp.route('/<int:user_id>/booklet.pdf')
@login_required
def generate_user_booklet_pdf(user_id):
    if user_id != current_user.id and not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    
    # Réutiliser la même logique de calcul que pour le profil
    competencies = user.competencies.all()
    for comp in competencies:
        practice_event = SkillPracticeEvent.query.filter_by(
            user_id=user.id
        ).join(SkillPracticeEvent.skills).filter_by(
            id=comp.skill_id
        ).order_by(SkillPracticeEvent.practice_date.desc()).first()
        comp.latest_practice_date = comp.evaluation_date
        if practice_event and practice_event.practice_date > comp.evaluation_date:
            comp.latest_practice_date = practice_event.practice_date
        if comp.skill.validity_period_months:
            recycling_due_date = comp.latest_practice_date + timedelta(days=comp.skill.validity_period_months * 30.44)
            comp.needs_recycling = datetime.utcnow() > recycling_due_date
            comp.recycling_due_date = recycling_due_date
        else:
            comp.needs_recycling = False
            comp.recycling_due_date = None

    html = render_template('certificates/booklet.html', user=user, competencies=competencies, current_date=datetime.utcnow())
    pdf = HTML(string=html, base_url=request.url_root).write_pdf()

    return send_file(io.BytesIO(pdf), as_attachment=True,
                     download_name=f"booklet_{user.full_name.replace(' ', '_')}.pdf",
                     mimetype='application/pdf')
