import os
import io
from flask import render_template, flash, redirect, url_for, current_app, request, send_file, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import re
from fpdf import FPDF
from fpdf.html import HTMLMixin
from datetime import datetime, timedelta
import json

from app import db, mail
from app.profile import bp
from app.models import User, Competency, Skill, SkillPracticeEvent, TrainingRequest, TrainingRequestStatus, ExternalTraining, ExternalTrainingStatus, TrainingSession, ExternalTrainingSkillClaim, Species # Added ExternalTrainingSkillClaim and Species
from app.profile.forms import TrainingRequestForm, ExternalTrainingForm, SkillPracticeEventForm, ProposeSkillForm

class MyFPDF(FPDF, HTMLMixin):
    pass

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
        validity_months = comp.skill.validity_period_months if comp.skill.validity_period_months is not None else 12
        if validity_months:
            recycling_due_date = comp.latest_practice_date + timedelta(days=validity_months * 30.44)
            comp.needs_recycling = datetime.utcnow() > recycling_due_date
            comp.recycling_due_date = recycling_due_date
            comp.warning_date = recycling_due_date - timedelta(days=validity_months * 30.44 / 4)
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
            status=ExternalTrainingStatus.PENDING
        )
        if form.attachment.data:
            filename = secure_filename(f"{current_user.id}_{datetime.utcnow().timestamp()}_{form.attachment.data.filename}")
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'external')
            os.makedirs(upload_path, exist_ok=True)
            form.attachment.data.save(os.path.join(upload_path, filename))
            ext_training.attachment_path = f"uploads/external/{filename}"
        
        db.session.add(ext_training)
        # Process skill claims from the FieldList
        for skill_claim_data in form.skill_claims.data:
            skill_claim = ExternalTrainingSkillClaim(
                skill=skill_claim_data['skill'],
                level=skill_claim_data['level'],
                species_claimed=skill_claim_data['species_claimed'],
                wants_to_be_tutor=skill_claim_data['wants_to_be_tutor']
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
    pdf.cell(0, 8, f'Evaluated by: {comp.evaluator.full_name if comp.evaluator else "N/A"}', 0, 1, 'C')

    # Signature Block
    y_signature = 170 # Position signatures 170mm from the top of the page
    
    left_x_start = 45.6
    right_x_start = 171.2

    # Administrator Signature
    pdf.set_xy(left_x_start, y_signature) # Position left signature
    pdf.set_font('Times', '', 12)
    pdf.set_text_color(*dark_gray)
    pdf.cell(80, 5, '', 'B', 1, 'C') # Line
    pdf.set_xy(left_x_start, y_signature + 5) # Move Y down for text
    pdf.cell(80, 10, 'Administrator Signature', 0, 0, 'C')

    # Evaluator Signature
    pdf.set_xy(right_x_start, y_signature) # Position right signature
    pdf.cell(80, 5, '', 'B', 1, 'C') # Line
    pdf.set_xy(right_x_start, y_signature + 5) # Move Y down for text
    pdf.cell(80, 10, 'Evaluator Signature', 0, 0, 'C')

    pdf_output = pdf.output(dest='S')
    
    return send_file(io.BytesIO(pdf_output), as_attachment=True,
                     download_name=f"certificate_{comp.user.full_name.replace(' ', '_')}_{comp.skill.name.replace(' ', '_')}.pdf",
                     mimetype='application/pdf')

@bp.route('/<int:user_id>/booklet.pdf')
@login_required
def generate_user_booklet_pdf(user_id):
    if user_id != current_user.id and not current_user.is_admin:
        abort(403)
    user = User.query.get_or_404(user_id)
    
    # Re-calculate competencies data as in user_profile
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
        validity_months = comp.skill.validity_period_months if comp.skill.validity_period_months is not None else 12
        if validity_months:
            recycling_due_date = comp.latest_practice_date + timedelta(days=validity_months * 30.44)
            comp.needs_recycling = datetime.utcnow() > recycling_due_date
            comp.recycling_due_date = recycling_due_date
            comp.warning_date = recycling_due_date - timedelta(days=validity_months * 30.44 / 4)
        else:
            comp.needs_recycling = False
            comp.recycling_due_date = None
            comp.warning_date = None

    pdf = FPDF(orientation='L', unit='mm', format='A4') # Landscape A4
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Colors
    blue = (0, 123, 255)
    dark_gray = (52, 58, 64)
    green = (40, 167, 69)
    red = (220, 53, 69)
    orange = (253, 126, 20)
    light_gray = (108, 117, 125)

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
    pdf.cell(0, 10, f'Generated on: {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
    
    pdf.set_font('Times', 'B', 16)
    pdf.set_text_color(*dark_gray)
    pdf.cell(0, 10, 'Overview of Competencies', 0, 1, 'L')
    pdf.ln(5)

    if not competencies:
        pdf.set_font('Times', '', 12)
        pdf.cell(0, 10, 'No competencies recorded.', 0, 1, 'L')
    else:
        # Table Headers
        col_widths = [60, 25, 25, 40, 25, 25, 25, 42] # Total 267mm, A4 landscape usable width is 297 - 2*15 = 267mm
        headers = ["Skill", "Level", "Evaluated", "Evaluator", "Last Practice", "Recycling Due", "Status", "Species"]
        
        pdf.set_font('Times', 'B', 10)
        pdf.set_fill_color(200, 220, 255) # Light blue background for headers
        pdf.set_text_color(0, 0, 0) # Black text for headers
        
        # Draw header row
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 7, header, 1, 0, 'C', 1)
        pdf.ln()

        pdf.set_font('Times', '', 8) # Smaller font for table content
        pdf.set_text_color(*dark_gray)
        pdf.set_fill_color(240, 240, 240) # Lighter background for rows
        
        row_height = 6 # Base row height

        for comp in competencies:
            # Check if new page is needed
            if pdf.get_y() + row_height > pdf.h - pdf.b_margin:
                pdf.add_page()
                pdf.set_font('Times', 'B', 10)
                pdf.set_fill_color(200, 220, 255)
                pdf.set_text_color(0, 0, 0)
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 7, header, 1, 0, 'C', 1)
                pdf.ln()
                pdf.set_font('Times', '', 8)
                pdf.set_text_color(*dark_gray)
                pdf.set_fill_color(240, 240, 240)

            fill = False # Alternate row background
            
            # Data for the current row
            skill_name = comp.skill.name
            level = comp.level
            evaluated_date = comp.evaluation_date.strftime("%Y-%m-%d")
            evaluator = comp.evaluator.full_name if comp.evaluator else "N/A"
            last_practice = comp.latest_practice_date.strftime("%Y-%m-%d") if comp.latest_practice_date else "N/A"
            
            recycling_due = "N/A"
            status_text = "Unlimited"
            status_color = green
            if comp.skill.validity_period_months:
                recycling_due = comp.recycling_due_date.strftime("%Y-%m-%d")
                if comp.needs_recycling:
                    status_text = "Expired"
                    status_color = red
                elif comp.warning_date and datetime.utcnow() > comp.warning_date:
                    status_text = "Recycling Soon"
                    status_color = orange
                else:
                    status_text = "Valid"
                    status_color = green
            
            species_names = ", ".join([s.name for s in comp.species]) if comp.species else "N/A"

            # Store current Y position to draw multi_cell content
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            
            # Determine max height needed for this row
            max_cell_height = row_height
            
            # Skill Name (multi_cell to handle wrapping)
            pdf.set_xy(x_start + sum(col_widths[:0]), y_start)
            pdf.multi_cell(col_widths[0], row_height, skill_name, 0, 'L')
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)
            
            # Level
            pdf.set_xy(x_start + sum(col_widths[:1]), y_start)
            pdf.multi_cell(col_widths[1], row_height, level, 0, 'C')
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)

            # Evaluated Date
            pdf.set_xy(x_start + sum(col_widths[:2]), y_start)
            pdf.multi_cell(col_widths[2], row_height, evaluated_date, 0, 'C')
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)

            # Evaluator
            pdf.set_xy(x_start + sum(col_widths[:3]), y_start)
            pdf.multi_cell(col_widths[3], row_height, evaluator, 0, 'L')
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)

            # Last Practice
            pdf.set_xy(x_start + sum(col_widths[:4]), y_start)
            pdf.multi_cell(col_widths[4], row_height, last_practice, 0, 'C')
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)

            # Recycling Due
            pdf.set_xy(x_start + sum(col_widths[:5]), y_start)
            pdf.multi_cell(col_widths[5], row_height, recycling_due, 0, 'C')
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)

            # Status
            pdf.set_xy(x_start + sum(col_widths[:6]), y_start)
            pdf.set_text_color(*status_color)
            pdf.multi_cell(col_widths[6], row_height, status_text, 0, 'C')
            pdf.set_text_color(*dark_gray) # Reset color
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)

            # Species
            pdf.set_xy(x_start + sum(col_widths[:7]), y_start)
            pdf.multi_cell(col_widths[7], row_height, species_names, 0, 'L')
            max_cell_height = max(max_cell_height, pdf.get_y() - y_start)

            # Draw borders for the entire row
            pdf.set_xy(x_start, y_start)
            for w in col_widths:
                pdf.cell(w, max_cell_height, '', 1, 0, 'L', fill)
            pdf.ln(max_cell_height) # Move to next line, using max height of cells

            fill = not fill # Alternate row background

    pdf_output = pdf.output(dest='S')
    
    return send_file(io.BytesIO(pdf_output), as_attachment=True,
                     download_name=f"booklet_{user.full_name.replace(' ', '_')}.pdf",
                     mimetype='application/pdf')
