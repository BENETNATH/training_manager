import os
import io
from flask import render_template, flash, redirect, url_for, current_app, request, send_file, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import re
from fpdf import FPDF
from fpdf.html import HTMLMixin
from fpdf.enums import TableBordersLayout
from fpdf.fonts import FontFace
from datetime import datetime, timedelta
import json

from app import db, mail
from app.profile import bp
from app.models import User, Competency, Skill, SkillPracticeEvent, TrainingRequest, TrainingRequestStatus, ExternalTraining, ExternalTrainingStatus, TrainingSession, ExternalTrainingSkillClaim, Species # Added ExternalTrainingSkillClaim and Species
from app.profile.forms import TrainingRequestForm, ExternalTrainingForm, ProposeSkillForm

class MyFPDF(FPDF, HTMLMixin):
    pass

class PDFWithFooter(FPDF):
    def __init__(self, *args, user_name, generation_date, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_name = user_name
        self.generation_date = generation_date

    def footer(self):
        # Go to 1.5 cm from bottom
        self.set_y(-15)
        # Select Times italic 8
        self.set_font("Times", "I", 8)
        # Set text color to gray
        self.set_text_color(128)
        # Create the footer text
        footer_text = f"{self.user_name} - Booklet extract date : {self.generation_date} - Page {self.page_no()}/{{nb}}"
        # Print centered page number
        self.cell(0, 10, footer_text, 0, 0, "C")


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
    
    user_competencies = user.competencies
    acquired_skills = {comp.skill for comp in user_competencies}
    required_skills_todo = list(all_required_skills - acquired_skills)
    
    # --- Logique de Recyclage et Dernière Pratique ---
    # The properties on the Competency model now handle these calculations.
    # We just need to ensure they are accessed to trigger the logic if needed.
    for comp in user_competencies:
        # Accessing the properties will trigger their calculation
        _ = comp.latest_practice_date
        _ = comp.recycling_due_date
        _ = comp.needs_recycling
        _ = comp.warning_date

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
        req = TrainingRequest(requester=current_user, status=TrainingRequestStatus.PENDING)
        
        # Fetch Skill objects based on the submitted IDs
        selected_skills = form.skills_requested.data
        req.skills_requested = selected_skills
        
        req.species_requested = [form.species.data]
        db.session.add(req)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Votre demande de formation a été soumise avec succès !', 'redirect_url': url_for('profile.user_profile')})
        flash('Your training request has been submitted!', 'success')
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
                if wants_to_be_tutor and current_user not in competency.skill.tutors:
                    competency.skill.tutors.append(current_user)

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
                comp.evaluator.full_name if comp.evaluator else "N/A",
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

@bp.route('/external_training/<int:training_id>')
@login_required
def view_external_training(training_id):
    external_training = ExternalTraining.query.options(
        db.joinedload(ExternalTraining.user),
        db.joinedload(ExternalTraining.validator),
        db.joinedload(ExternalTraining.skill_claims).joinedload(ExternalTrainingSkillClaim.skill),
        db.joinedload(ExternalTraining.skill_claims).joinedload(ExternalTrainingSkillClaim.species_claimed)
    ).get_or_404(training_id)

    # Ensure the current user is either the owner of the external training or an admin
    if external_training.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    return render_template('profile/view_external_training.html',
                           title='External Training Details',
                           external_training=external_training)

