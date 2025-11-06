import os
import io
import json
from flask import render_template, flash, redirect, url_for, current_app, request, send_file, abort, jsonify
from flask_login import login_required, current_user, logout_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, extract, case
import traceback # Import traceback
from fpdf import FPDF
from fpdf.html import HTMLMixin
from fpdf.fonts import FontFace
import zipfile
from app import db
from app.decorators import permission_required
from app.email import send_email
from app.dashboard import bp
from app.models import (
    User, TrainingRequest, TrainingRequestStatus, ExternalTraining, ExternalTrainingStatus,
    UserContinuousTraining, UserContinuousTrainingStatus, ContinuousTrainingEvent,
    ContinuousTrainingEventStatus, Skill, ContinuousTrainingType, Competency, Role, Permission,
    InitialRegulatoryTraining, InitialRegulatoryTrainingLevel, SkillPracticeEvent, Species,
    UserDismissedNotification, tutor_skill_association, TrainingSession, ExternalTrainingSkillClaim,
    training_session_attendees
)
from app.profile.forms import (
    RequestContinuousTrainingEventForm, SubmitContinuousTrainingAttendanceForm, EditProfileForm,
    SingleInitialRegulatoryTrainingForm, InitialRegulatoryTrainingsForm, ProposeSkillForm, ExternalTrainingForm, ExternalTrainingSkillClaimForm, TrainingRequestForm
)
from collections import defaultdict
from datetime import datetime, timezone

class PDF(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4', user_name=''):
        super().__init__(orientation, unit, format)
        self.user_name = user_name

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        generation_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        footer_text = f'Livret de Compétences de {self.user_name} - {generation_date}'
        self.cell(0, 10, footer_text, 0, 0, 'L')
        self.cell(0, 10, f'{self.page_no()}/{{nb}}', 0, 0, 'R')

def _generate_booklet_pdf(user):
    # --- Data Fetching ---
    competencies = user.competencies
    initial_trainings = user.initial_regulatory_trainings
    continuous_trainings = user.continuous_trainings_attended.join(ContinuousTrainingEvent).filter(
        UserContinuousTraining.status == UserContinuousTrainingStatus.APPROVED
    ).order_by(ContinuousTrainingEvent.event_date.desc()).all()

    # --- PDF Generation ---
    pdf = PDF(user_name=user.full_name)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    
    # --- Header ---
    pdf.cell(0, 10, 'LIVRET DE COMPETENCES', 0, 1, 'C')
    pdf.ln(10)

    # --- User Info ---
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Informations utilisateur', 0, 1, 'L')
    pdf.set_font('Helvetica', '', 10)
    
    # Basic user info table
    with pdf.table(col_widths=(40, 150)) as table:
        row = table.row()
        row.cell("Nom Prénom")
        row.cell(user.full_name)
    pdf.ln(10)

    # --- Formation Initiale : Diplômes ---
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Formation Initiale : Diplômes', 0, 1, 'L')
    pdf.set_font('Helvetica', '', 12)
    with pdf.table(col_widths=(40, 40, 30, 30, 30, 20)) as table:
        headings = table.row()
        for heading in ("Diplôme", "Etablissement", "Pays", "Date de réussite", "Niveau d'étude", "Remarques"):
            headings.cell(heading)
        
        row = table.row()
        row.cell(user.study_level or "N/A")
        row.cell("N/A")
        row.cell("N/A")
        row.cell("N/A")
        row.cell("N/A")
        row.cell("")

    pdf.ln(10)

    # --- Formation spécifique à l'expérimentation animale ---
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, "Formation spécifique à l'expérimentation animale", 0, 1, 'L')
    pdf.set_font('Helvetica', '', 12)
    with pdf.table(col_widths=(35, 40, 20, 25, 30, 20, 20, 15)) as table:
        headings = table.row()
        for heading in ("Niveau", "Module", "Espece", "N° Agrément", "Etablissement", "Formateur", "Date", "jours"):
            headings.cell(heading)
        
        for training in initial_trainings:
            row = table.row()
            row.cell(training.level.value if training.level else "N/A")
            row.cell(training.training_type)
            row.cell("N/A")
            row.cell("N/A")
            row.cell("N/A")
            row.cell("N/A")
            row.cell(training.training_date.strftime("%d/%m/%Y") if training.training_date else "N/A")
            row.cell("N/A")
    pdf.ln(10)

    # --- Formation Continue ---
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Formation Continue', 0, 1, 'L')
    pdf.set_font('Helvetica', '', 12)
    with pdf.table(col_widths=(50, 40, 30, 30, 20, 20)) as table:
        headings = table.row()
        for heading in ("Nom de la formation", "Thematique", "Type", "Lieu", "Date", "Durée (j)"):
            headings.cell(heading)
        for ct in continuous_trainings:
            row = table.row()
            row.cell(ct.event.title)
            row.cell("N/A")
            row.cell(ct.event.training_type.value)
            row.cell(ct.event.location or "N/A")
            row.cell(ct.event.event_date.strftime("%d/%m/%Y"))
            row.cell(str(round(ct.validated_hours / 7, 2)) if ct.validated_hours else "N/A") # Assuming 7h/day
    pdf.ln(10)

    # --- Compétences techniques ---
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Compétences techniques', 0, 1, 'L')
    pdf.set_font('Helvetica', '', 12)
    with pdf.table(col_widths=(40, 50, 20, 25, 25, 30, 20)) as table:
        headings = table.row()
        for heading in ("Type de compétence", "Compétence", "Etat", "Date", "Espèces", "Type de formation", "Tuteur"):
            headings.cell(heading)

        for comp in competencies:
            row = table.row()
            row.cell("N/A")
            row.cell(comp.skill.name)
            row.cell(comp.level or "N/A")
            row.cell(comp.evaluation_date.strftime("%d/%m/%Y"))
            row.cell(", ".join([s.name for s in comp.species]) if comp.species else "N/A")
            row.cell("N/A")
            row.cell(comp.evaluator.full_name if comp.evaluator else (comp.external_evaluator_name or "N/A"))

    pdf_output = pdf.output()
    pdf_buffer = io.BytesIO(pdf_output)
    pdf_buffer.seek(0)
    return pdf_buffer

def get_notification_summary_for_user(user):
    notifications = []
    total_count = 0

    # Get dismissed notifications for the current user
    dismissed_notifications = {d.notification_type for d in user.dismissed_notifications}

    # Admin-focused notifications
    if user.can('user_manage') and 'user_approvals' not in dismissed_notifications:
        pending_user_approvals_count = User.query.filter_by(is_approved=False).count()
        if pending_user_approvals_count > 0:
            notifications.append({
                'type': 'user_approvals',
                'title': 'New User Approvals',
                'count': pending_user_approvals_count,
                'url': url_for('admin.pending_users')
            })
            total_count += pending_user_approvals_count

    if user.can('training_request_manage') and 'training_requests' not in dismissed_notifications:
        pending_requests_count = TrainingRequest.query.filter_by(status=TrainingRequestStatus.PENDING).count()
        if pending_requests_count > 0:
            notifications.append({
                'type': 'training_requests',
                'title': 'Pending Training Requests',
                'count': pending_requests_count,
                'url': url_for('admin.list_training_requests')
            })
            total_count += pending_requests_count

    if user.can('external_training_validate') and 'external_trainings' not in dismissed_notifications:
        pending_external_trainings_count = ExternalTraining.query.filter_by(status=ExternalTrainingStatus.PENDING).count()
        if pending_external_trainings_count > 0:
            notifications.append({
                'type': 'external_trainings',
                'title': 'Pending External Training Validations',
                'count': pending_external_trainings_count,
                'url': url_for('admin.validate_external_trainings')
            })
            total_count += pending_external_trainings_count

    if user.can('continuous_training_validate') and 'continuous_training_validations' not in dismissed_notifications:
        pending_continuous_training_validations_count = UserContinuousTraining.query.filter_by(status=UserContinuousTrainingStatus.PENDING).count()
        if pending_continuous_training_validations_count > 0:
            notifications.append({
                'type': 'continuous_training_validations',
                'title': 'Pending Continuous Training Validations',
                'count': pending_continuous_training_validations_count,
                'url': url_for('admin.validate_continuous_trainings')
            })
            total_count += pending_continuous_training_validations_count

    if user.can('continuous_training_manage') and 'continuous_event_requests' not in dismissed_notifications:
        pending_continuous_event_requests_count = ContinuousTrainingEvent.query.filter_by(status=ContinuousTrainingEventStatus.PENDING).count()
        if pending_continuous_event_requests_count > 0:
            notifications.append({
                'type': 'continuous_event_requests',
                'title': 'Pending Continuous Event Requests',
                'count': pending_continuous_event_requests_count,
                'url': url_for('admin.manage_continuous_training_events', status='PENDING')
            })
            total_count += pending_continuous_event_requests_count

    if user.can('skill_manage') and 'proposed_skills' not in dismissed_notifications:
        proposed_skills_count = TrainingRequest.query.filter_by(status=TrainingRequestStatus.PROPOSED_SKILL).count()
        if proposed_skills_count > 0:
            notifications.append({
                'type': 'proposed_skills',
                'title': 'Proposed Skills',
                'count': proposed_skills_count,
                'url': url_for('admin.proposed_skills')
            })
            total_count += proposed_skills_count

    if user.can('skill_manage') and 'skills_without_tutors' not in dismissed_notifications:
        skills_without_tutors_count = Skill.query.filter(~Skill.tutors.any()).count()
        if skills_without_tutors_count > 0:
            notifications.append({
                'type': 'skills_without_tutors',
                'title': 'Skills Without Tutors',
                'count': skills_without_tutors_count,
                'url': url_for('admin.tutor_less_skills_report')
            })
            total_count += skills_without_tutors_count

    if user.can('training_session_manage') and 'sessions_to_finalize' not in dismissed_notifications:
        sessions_to_be_finalized_count = TrainingSession.query.filter(
            TrainingSession.start_time < datetime.now(timezone.utc),
            TrainingSession.status != 'Realized'
        ).count()
        if sessions_to_be_finalized_count > 0:
            notifications.append({
                'type': 'sessions_to_finalize',
                'title': 'Sessions to Finalize',
                'count': sessions_to_be_finalized_count,
                'url': url_for('admin.manage_training_sessions', filter='to_be_finalized')
            })
            total_count += sessions_to_be_finalized_count

    # User-focused notifications
    if user.is_authenticated:
        # Skills needing recycling
        if 'skills_needing_recycling' not in dismissed_notifications:
            skills_needing_recycling_count = 0
            for comp in user.competencies:
                if comp.needs_recycling:
                    skills_needing_recycling_count += 1

            if skills_needing_recycling_count > 0:
                url = url_for('dashboard.dashboard_home')
                if user.can('view_reports'):
                    url = url_for('admin.recycling_report')
                
                notifications.append({
                    'type': 'skills_needing_recycling',
                    'title': 'Skills Needing Recycling',
                    'count': skills_needing_recycling_count,
                    'url': url
                })
                total_count += skills_needing_recycling_count

        # Upcoming training sessions
        if 'upcoming_sessions' not in dismissed_notifications:
            now = datetime.now(timezone.utc)
            upcoming_training_sessions_count = TrainingSession.query.join(TrainingSession.attendees).filter(User.id == user.id, TrainingSession.start_time > now).count()
            if upcoming_training_sessions_count > 0:
                notifications.append({
                    'type': 'upcoming_sessions',
                    'title': 'Upcoming Training Sessions',
                    'count': upcoming_training_sessions_count,
                    'url': url_for('dashboard.dashboard_home') # Or a dedicated page for upcoming sessions
                })
                total_count += upcoming_training_sessions_count

        # Pending training requests by user
        if 'user_pending_training_requests' not in dismissed_notifications:
            user_pending_training_requests_count = TrainingRequest.query.filter_by(requester_id=user.id, status=TrainingRequestStatus.PENDING).count()
            if user_pending_training_requests_count > 0:
                notifications.append({
                    'type': 'user_pending_training_requests',
                    'title': 'Your Pending Training Requests',
                    'count': user_pending_training_requests_count,
                    'url': url_for('dashboard.dashboard_home') # Or a dedicated page for user's requests
                })
                total_count += user_pending_training_requests_count

        # Pending external trainings by user
        if 'user_pending_external_trainings' not in dismissed_notifications:
            user_pending_external_trainings_count = user.external_trainings.filter_by(status=ExternalTrainingStatus.PENDING).count()
            if user_pending_external_trainings_count > 0:
                notifications.append({
                    'type': 'user_pending_external_trainings',
                    'title': 'Your Pending External Trainings',
                    'count': user_pending_external_trainings_count,
                    'url': url_for('dashboard.dashboard_home') # Or a dedicated page for user's external trainings
                })
                total_count += user_pending_external_trainings_count

    return {'total_count': total_count, 'notifications': notifications}

@bp.route('/user_profile/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(full_name=username).first_or_404()
    if user == current_user:
        return redirect(url_for('dashboard.dashboard_home'))
    # For now, if it's not the current user, we'll just redirect to dashboard_home
    # A more complete solution would involve a dedicated view_user_profile.html template
    # and appropriate permissions to view other users' profiles.
    flash(f"Viewing profile for {user.full_name} is not yet fully implemented.", 'info')
    return redirect(url_for('dashboard.dashboard_home'))


@bp.route('/')
@login_required
def dashboard_home():
    user = current_user
    db.session.refresh(user) # Refresh the user object to get latest data

    # START: New logic for training chart (from dashboard.user_profile)
    current_year = datetime.now(timezone.utc).year
    years_labels = [str(y) for y in range(current_year - 5, current_year + 1)]
    six_years_ago = datetime(current_year - 5, 1, 1)

    chart_data_agg = {
        'validated_online': defaultdict(float),
        'validated_presential': defaultdict(float),
        'pending_online': defaultdict(float),
        'pending_presential': defaultdict(float),
    }

    all_continuous_trainings_for_chart = UserContinuousTraining.query.join(
        ContinuousTrainingEvent
    ).filter(
        UserContinuousTraining.user_id == user.id,
        ContinuousTrainingEvent.event_date >= six_years_ago
    ).options(
        db.joinedload(UserContinuousTraining.event)
    ).all()

    for uct in all_continuous_trainings_for_chart:
        year = uct.event.event_date.year
        if uct.status == UserContinuousTrainingStatus.APPROVED:
            hours = uct.validated_hours or 0.0
            if uct.event.training_type == ContinuousTrainingType.ONLINE:
                chart_data_agg['validated_online'][year] += hours
            else: # PRESENTIAL
                chart_data_agg['validated_presential'][year] += hours
        elif uct.status == UserContinuousTrainingStatus.PENDING:
            hours = uct.event.duration_hours or 0.0
            if uct.event.training_type == ContinuousTrainingType.ONLINE:
                chart_data_agg['pending_online'][year] += hours
            else: # PRESENTIAL
                chart_data_agg['pending_presential'][year] += hours

    training_chart_data = {
        'labels': years_labels,
        'datasets': [
            {
                'label': 'Validated (Presential)',
                'data': [chart_data_agg['validated_presential'][int(y)] for y in years_labels],
                'backgroundColor': 'rgba(40, 167, 69, 0.7)', # Green
            },
            {
                'label': 'Validated (Online)',
                'data': [chart_data_agg['validated_online'][int(y)] for y in years_labels],
                'backgroundColor': 'rgba(0, 123, 255, 0.7)', # Blue
            },
            {
                'label': 'Pending (Presential)',
                'data': [chart_data_agg['pending_presential'][int(y)] for y in years_labels],
                'backgroundColor': 'rgba(255, 193, 7, 0.7)', # Yellow
            },
            {
                'label': 'Pending (Online)',
                'data': [chart_data_agg['pending_online'][int(y)] for y in years_labels],
                'backgroundColor': 'rgba(253, 126, 20, 0.7)', # Orange
            }
        ]
    }
    # END: New logic for training chart

    # Get all competencies for the user (from dashboard.user_profile)
    competencies = user.competencies

    # Get all training paths assigned to the user (from dashboard.user_profile)
    assigned_paths = user.assigned_training_paths

    # Get all skills from the assigned training paths (from dashboard.user_profile)
    required_skills = {skill_assoc.skill for path in assigned_paths for skill_assoc in path.skills_association}

    # Get all skills the user is competent in (from dashboard.user_profile)
    competent_skills = {comp.skill for comp in competencies}

    # Determine the skills the user still needs to acquire (from dashboard.user_profile)
    required_skills_todo = list(required_skills - competent_skills)

    # Get pending training requests for the user (from dashboard.user_profile)
    pending_training_requests_by_user = TrainingRequest.query.filter_by(requester_id=user.id, status=TrainingRequestStatus.PENDING).all()
    pending_external_trainings_by_user = current_user.external_trainings.filter_by(status=ExternalTrainingStatus.PENDING).all()

    # Get upcoming and completed training sessions for the user (from dashboard.user_profile)
    now = datetime.now(timezone.utc)
    upcoming_training_sessions_by_user = [sess for sess in user.attended_training_sessions if sess.start_time > now]
    completed_training_sessions_by_user = [sess for sess in user.attended_training_sessions if sess.start_time <= now]

    # Get initial regulatory training
    initial_regulatory_trainings = user.initial_regulatory_trainings

    # Get continuous training data (from dashboard.user_profile)
    continuous_trainings_attended = user.continuous_trainings_attended.join(ContinuousTrainingEvent).filter(UserContinuousTraining.status == UserContinuousTrainingStatus.APPROVED).order_by(ContinuousTrainingEvent.event_date.desc()).all()
    total_continuous_training_hours_6_years = user.total_continuous_training_hours_6_years
    live_continuous_training_hours_6_years = user.live_continuous_training_hours_6_years
    online_continuous_training_hours_6_years = user.online_continuous_training_hours_6_years
    required_continuous_training_hours = user.required_continuous_training_hours
    is_continuous_training_compliant = user.is_continuous_training_compliant
    is_live_training_compliant = user.is_live_training_compliant
    required_live_training_hours = user.required_live_training_hours
    is_at_risk_next_year = user.is_at_risk_next_year
    continuous_training_summary_by_year = user.continuous_training_summary_by_year

    # Existing dashboard counts (ensure they are still correct or remove if redundant)
    user_pending_training_requests_count = len(pending_training_requests_by_user)
    user_pending_external_trainings_count = current_user.external_trainings.filter_by(status=ExternalTrainingStatus.PENDING).count()
    user_next_session = TrainingSession.query \
        .join(training_session_attendees) \
        .filter(training_session_attendees.c.user_id == current_user.id) \
        .filter(TrainingSession.start_time > datetime.now(timezone.utc)) \
        .order_by(TrainingSession.start_time.asc()) \
        .first()
    user_skills_needing_recycling_count = Competency.query \
        .join(Skill) \
        .filter(\
            Competency.user_id == current_user.id,\
            Skill.validity_period_months.isnot(None),\
            func.DATETIME(func.JULIANDAY(Competency.evaluation_date) + (Skill.validity_period_months * 30.44)) < datetime.now(timezone.utc)\
        ).count()

    # Get notification summary for dashboard tabs
    notification_summary = get_notification_summary_for_user(current_user)

    return render_template('dashboard/dashboard.html',
                           user=user,
                           competencies=competencies,
                           required_skills_todo=required_skills_todo,
                           pending_training_requests_by_user=pending_training_requests_by_user,
                           pending_external_trainings_by_user=pending_external_trainings_by_user,
                           upcoming_training_sessions_by_user=upcoming_training_sessions_by_user,
                           completed_training_sessions_by_user=completed_training_sessions_by_user,
                           initial_regulatory_trainings=initial_regulatory_trainings,
                           continuous_trainings_attended=continuous_trainings_attended,
                           total_continuous_training_hours_6_years=total_continuous_training_hours_6_years,
                           live_continuous_training_hours_6_years=live_continuous_training_hours_6_years,
                           online_continuous_training_hours_6_years=online_continuous_training_hours_6_years,
                           required_continuous_training_hours=required_continuous_training_hours,
                           is_continuous_training_compliant=is_continuous_training_compliant,
                           is_live_training_compliant=is_live_training_compliant,
                           required_live_training_hours=required_live_training_hours,
                           is_at_risk_next_year=is_at_risk_next_year,
                           continuous_training_summary_by_year=continuous_training_summary_by_year,
                           training_chart_data=training_chart_data,
                           all_continuous_trainings=all_continuous_trainings_for_chart,
                           UserContinuousTrainingStatus=UserContinuousTrainingStatus,
                           ContinuousTrainingType=ContinuousTrainingType,
                           TrainingRequestStatus=TrainingRequestStatus,
                           notification_summary=notification_summary, # Pass notification summary to template
                           now=now
                           )


@bp.route('/request_continuous_training_event', methods=['GET', 'POST'])
@login_required
@permission_required('self_request_continuous_training_event') # A new permission might be needed
def request_continuous_training_event():
    form = RequestContinuousTrainingEventForm()
    if form.validate_on_submit():
        attachment_path = None
        if form.attachment.data:
            current_utc = datetime.now(timezone.utc)
            year = current_utc.year
            month = current_utc.month
            user_id = current_user.id
            event_title_slug = secure_filename(form.title.data.lower().replace(' ', '_'))[:50] # Slugify title, limit length
            timestamp = int(current_utc.timestamp())
            original_filename = secure_filename(form.attachment.data.filename)
            file_extension = os.path.splitext(original_filename)[1]
            content_type = "continuous_training_events"

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', content_type, str(year), str(month), str(user_id))
            os.makedirs(upload_folder, exist_ok=True)

            new_filename = f"{user_id}_{content_type}_{event_title_slug}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_folder, new_filename)
            form.attachment.data.save(file_path)
            attachment_path = os.path.join('uploads', content_type, str(year), str(month), str(user_id), new_filename)

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

        # Send email to continuous training managers
        ct_managers = User.query.join(User.roles).join(Role.permissions).filter(
            Permission.name == 'continuous_training_manage'
        ).all()

        if ct_managers:
            recipients = [manager.email for manager in ct_managers if manager.email]
            if recipients:
                send_email(
                    '[Training Manager] New Continuous Training Event Request for Review',
                    sender=current_app.config['MAIL_USERNAME'],
                    recipients=recipients,
                    text_body=render_template(
                        'email/continuous_training_event_requested_notification.txt',
                        user=current_user,
                        event_title=new_event.title,
                        event_description=new_event.description,
                        event_date=new_event.event_date.strftime('%Y-%m-%d')
                    ),
                    html_body=render_template(
                        'email/continuous_training_event_requested_notification.html',
                        user=current_user,
                        event_title=new_event.title,
                        event_description=new_event.description,
                        event_date=new_event.event_date.strftime('%Y-%m-%d')
                    )
                )
                current_app.logger.info(f"Email sent to CT managers for new event request by {current_user.full_name}")

        flash("Votre demande d'événement de formation continue a été soumise pour validation !", 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': "Votre demande d'événement de formation continue a été soumise pour validation !", 'redirect_url': url_for('dashboard.dashboard_home')})
        return redirect(url_for('dashboard.dashboard_home'))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/request_continuous_training_event.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400

    # For GET requests or non-AJAX POST with validation errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/request_continuous_training_event.html', form=form)
    return render_template('profile/request_continuous_training_event.html', title='Demander un Événement de Formation Continue', form=form)


@bp.route('/submit_continuous_training_attendance', methods=['GET', 'POST'])
@login_required
@permission_required('self_submit_continuous_training_attendance') # Use the new specific permission
def submit_continuous_training_attendance():
    form = SubmitContinuousTrainingAttendanceForm()

    # Populate choices for the event field for server-side validation
    approved_events = ContinuousTrainingEvent.query.filter_by(status=ContinuousTrainingEventStatus.APPROVED).order_by(ContinuousTrainingEvent.event_date.desc()).all()
    form.event.choices = [(str(event.id), f"{event.title} ({event.event_date.strftime('%Y-%m-%d')}) - {event.location or 'N/A'}") for event in approved_events]

    if form.validate_on_submit():
        # Check for duplicate submission
        existing_attendance = UserContinuousTraining.query.filter_by(
            user_id=current_user.id,
            event_id=form.event.data
        ).first()

        if existing_attendance:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'You have already submitted an attendance for this event.'}), 400
            else:
                flash('You have already submitted an attendance for this event.', 'warning')
                return redirect(url_for('dashboard.dashboard_home'))

        attendance_attachment_path = None
        if form.attendance_attachment.data:
            current_utc = datetime.now(timezone.utc)
            year = current_utc.year
            month = current_utc.month
            user_id = current_user.id
            event_id = form.event.data # The event ID is available here
            timestamp = int(current_utc.timestamp())
            original_filename = secure_filename(form.attendance_attachment.data.filename)
            file_extension = os.path.splitext(original_filename)[1]
            content_type = "continuous_training_attendance"
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', content_type, str(year), str(month), str(user_id))
            os.makedirs(upload_folder, exist_ok=True)

            new_filename = f"{user_id}_{content_type}_event{event_id}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_folder, new_filename)
            form.attendance_attachment.data.save(file_path)
            attendance_attachment_path = os.path.join('uploads', content_type, str(year), str(month), str(user_id), new_filename)

        # Fetch the ContinuousTrainingEvent object using the ID from form.event.data
        selected_event = ContinuousTrainingEvent.query.get(form.event.data)
        if not selected_event:
            flash("L'événement de formation continue sélectionné est introuvable.", 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "L'événement de formation continue sélectionné est introuvable."}), 400
            return redirect(url_for('dashboard.dashboard_home'))

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
            return jsonify({'success': True, 'message': 'Votre participation à la formation continue a été soumise pour validation !', 'redirect_url': url_for('dashboard.dashboard_home')})
        return redirect(url_for('dashboard.dashboard_home'))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_submit_continuous_training_attendance_form.html', form=form)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400

    # For GET requests or non-AJAX POST with validation errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_submit_continuous_training_attendance_form.html', form=form)
    return render_template('profile/submit_continuous_training_attendance.html', title='Soumettre une Participation à une Formation Continue', form=form)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
@permission_required('self_edit_profile')
def edit_profile():
    form = EditProfileForm(original_email=current_user.email)
    initial_trainings_form = InitialRegulatoryTrainingsForm()

    if form.validate_on_submit() and initial_trainings_form.validate_on_submit():
        # Handle password change
        if form.password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Incorrect current password.', 'danger')
                return redirect(url_for('dashboard.edit_profile'))
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
            return redirect(url_for('dashboard.dashboard_home'))

        current_user.full_name = form.full_name.data
        current_user.study_level = form.study_level.data
        db.session.commit()
        flash('Your changes have been saved.', 'success')

        # Handle initial regulatory trainings
        # Get existing trainings to compare with submitted data
        existing_trainings = {t.id: t for t in current_user.initial_regulatory_trainings}
        submitted_training_ids = set()

        for entry_form in initial_trainings_form.initial_trainings.entries:
            if entry_form.training_type.data and entry_form.level.data and entry_form.training_date.data:
                # Find if an existing training matches the submitted data
                matched_training = None
                for et in existing_trainings.values():
                    if et.training_type == entry_form.training_type.data and \
                       et.level.name == entry_form.level.data and \
                       et.training_date == entry_form.training_date.data:
                        matched_training = et
                        break

                attachment_path = None
                if entry_form.attachment.data:
                    current_utc = datetime.now(timezone.utc)
                    year = current_utc.year
                    month = current_utc.month
                    user_id = current_user.id
                    training_type_slug = secure_filename(entry_form.training_type.data.lower().replace(' ', '_'))[:50]
                    timestamp = int(current_utc.timestamp())
                    original_filename = secure_filename(entry_form.attachment.data.filename)
                    file_extension = os.path.splitext(original_filename)[1]
                    content_type = "initial_regulatory_training"
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', content_type, str(year), str(month), str(user_id))
                    os.makedirs(upload_folder, exist_ok=True)

                    new_filename = f"{user_id}_{content_type}_{training_type_slug}_{timestamp}{file_extension}"
                    file_path = os.path.join(upload_folder, new_filename)
                    entry_form.attachment.data.save(file_path)
                    attachment_path = os.path.join('uploads', content_type, str(year), str(month), str(user_id), new_filename)

                    # Delete old attachment if it exists and is being replaced
                    if matched_training and matched_training.attachment_path and matched_training.attachment_path != attachment_path:
                        old_path = os.path.join(current_app.root_path, 'static', matched_training.attachment_path)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                else:
                    # If no new attachment, keep existing one if updating
                    if matched_training and matched_training.attachment_path:
                        attachment_path = matched_training.attachment_path

                if matched_training:
                    matched_training.training_type = entry_form.training_type.data
                    matched_training.level = InitialRegulatoryTrainingLevel[entry_form.level.data]
                    matched_training.training_date = entry_form.training_date.data
                    matched_training.attachment_path = attachment_path
                    submitted_training_ids.add(matched_training.id)
                else:
                    new_training = InitialRegulatoryTraining(
                        user=current_user,
                        training_type=entry_form.training_type.data,
                        level=InitialRegulatoryTrainingLevel[entry_form.level.data],
                        training_date=entry_form.training_date.data,
                        attachment_path=attachment_path
                    )
                    db.session.add(new_training)
                    db.session.flush() # Assign an ID to the new training
                    submitted_training_ids.add(new_training.id)

        # Delete trainings that were not in the submitted form data
        for training_id, training_obj in existing_trainings.items():
            if training_id not in submitted_training_ids:
                # Delete associated attachment if it exists
                if training_obj.attachment_path:
                    old_path = os.path.join(current_app.root_path, 'static', training_obj.attachment_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                db.session.delete(training_obj)

        db.session.commit()
        flash('Vos formations réglementaires initiales ont été enregistrées/mises à jour avec succès !', 'success')
        
        return redirect(url_for('dashboard.dashboard_home'))

    elif request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.study_level.data = current_user.study_level

        # Populate initial_trainings_form with existing data by appending a dictionary
        for training in current_user.initial_regulatory_trainings:
            # THIS BLOCK IS NOW CORRECTLY INDENTED
            initial_trainings_form.initial_trainings.append_entry({
                'training_type': training.training_type,
                'level': training.level.name,
                'training_date': training.training_date
            })

    return render_template('profile/edit_dashboard.html', title='Edit Profile', form=form, initial_trainings_form=initial_trainings_form, api_key=current_user.api_key, InitialRegulatoryTrainingLevel=InitialRegulatoryTrainingLevel)
        

@bp.route('/regenerate_api_key', methods=['POST'])
@login_required
def regenerate_api_key():
    new_key = current_user.generate_api_key()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Nouvelle clé API générée avec succès !', 'api_key': new_key})


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


@bp.route('/request-training', methods=['GET', 'POST'])
@login_required
@permission_required('self_submit_training_request')
def submit_training_request():
    form = TrainingRequestForm()
    skill_id = request.args.get('skill_id')
    species_id = request.args.get('species_id')

    if request.method == 'GET' and skill_id and species_id:
        skill = Skill.query.get(skill_id)
        species = Species.query.get(species_id)
        if skill and species:
            form.skills_requested.data = [skill]
            form.species.data = species

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
        selected_species = form.species.data # This is now a single Species object
        
        if not selected_species:
            flash('Please select a species for the training request.', 'danger')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Please select a species for the training request.'}), 400
            return redirect(url_for('dashboard.dashboard_home'))

        successful_requests_messages = []
        existing_requests_messages = []
        errors_occurred = False

        for skill in selected_skills:
            # Check for existing pending request for the single selected species
            existing_req = TrainingRequest.query.filter(
                TrainingRequest.requester == current_user,
                TrainingRequest.status == TrainingRequestStatus.PENDING,
                TrainingRequest.skills_requested.any(Skill.id == skill.id),
                TrainingRequest.species_requested.any(Species.id == selected_species.id)
            ).first()

            if existing_req:
                existing_requests_messages.append(f"Request for '{skill.name}' on '{selected_species.name}' already exists and is pending.")
                continue # Skip creating this request

            # Create new TrainingRequest
            req = TrainingRequest(
                requester=current_user,
                status=TrainingRequestStatus.PENDING,
                justification=form.justification.data
            )
            db.session.add(req)
            
            req.skills_requested.append(skill)
            req.species_requested.append(selected_species) # Append the single selected species

            successful_requests_messages.append(f"Request for '{skill.name}' on '{selected_species.name}' created.")
            current_app.logger.info(f"Created new TrainingRequest: {req} for skill: {skill.name} and species: {selected_species.name}")

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
                if existing_requests_messages:
                    return jsonify({'success': True, 'message': existing_requests_messages[0], 'redirect_url': url_for('dashboard.dashboard_home')})
                elif successful_requests_messages:
                    return jsonify({'success': True, 'message': successful_requests_messages[0], 'redirect_url': url_for('dashboard.dashboard_home')})
                else:
                    return jsonify({'success': True, 'message': 'Request processed.', 'redirect_url': url_for('dashboard.dashboard_home')})
            
            return redirect(url_for('dashboard.dashboard_home'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing training request: {e}", exc_info=True) # Log full traceback
            traceback.print_exc() # Print traceback directly to stderr
            flash('An unexpected error occurred during submission.', 'danger')
            errors_occurred = True # Mark that an error occurred

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                import traceback
                return jsonify({'success': False, 'message': 'An unexpected error occurred during submission.', 'traceback': traceback.format_exc()}), 500
            return redirect(url_for('dashboard.dashboard_home'))
    elif request.method == 'POST': # Validation failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_training_request_form.html', form=form, api_key=current_user.api_key)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'})

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_training_request_form.html', form=form, api_key=current_user.api_key)

    return render_template('profile/_training_request_form.html', title='Submit Training Request', form=form)


@bp.route('/propose-skill', methods=['GET', 'POST'])
@login_required
def propose_skill():
    form = ProposeSkillForm()
    if form.validate_on_submit():
        # Create a TrainingRequest with a special status for proposed skills
        req = TrainingRequest(
            requester=current_user,
            status=TrainingRequestStatus.PROPOSED_SKILL,
            justification=f"Proposed Skill: {form.name.data} - Description: {form.description.data}")
        db.session.add(req)
        db.session.commit()

        # Send email to skill managers
        skill_managers = User.query.join(User.roles).join(Role.permissions).filter(
            Permission.name == 'skill_manage'
        ).all()
        
        if skill_managers:
            recipients = [manager.email for manager in skill_managers if manager.email]
            if recipients:
                send_email(
                    '[Training Manager] New Skill Proposal for Review',
                    sender=current_app.config['MAIL_USERNAME'],
                    recipients=recipients,
                    text_body=render_template(
                        'email/skill_proposed_notification.txt',
                        user=current_user,
                        skill_name=form.name.data,
                        skill_description=form.description.data
                    ),
                    html_body=render_template(
                        'email/skill_proposed_notification.html',
                        user=current_user,
                        skill_name=form.name.data,
                        skill_description=form.description.data
                    )
                )
                current_app.logger.info(f"Email sent to skill managers for new skill proposal by {current_user.full_name}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Votre proposition de compétence a été soumise aux administrateurs.', 'redirect_url': url_for('dashboard.dashboard_home')})
        flash('Votre proposition de compétence a été soumise aux administrateurs.', 'success')
        return redirect(url_for('dashboard.dashboard_home'))
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
            duration_hours=form.duration_hours.data,
            status=ExternalTrainingStatus.PENDING
        )
        if form.attachment.data:
            content_type = "external_training"
            current_utc = datetime.now(timezone.utc)
            year = current_utc.year
            month = current_utc.month
            user_id = current_user.id
            external_trainer_slug = secure_filename(form.external_trainer_name.data.lower().replace(' ', '_'))[:50] # Slugify trainer name, limit length
            timestamp = int(current_utc.timestamp())
            original_filename = secure_filename(form.attachment.data.filename)
            file_extension = os.path.splitext(original_filename)[1]

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', content_type, str(year), str(month), str(user_id))
            os.makedirs(upload_folder, exist_ok=True)

            new_filename = f"{user_id}_{content_type}_{external_trainer_slug}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_folder, new_filename)
            form.attachment.data.save(file_path)
            ext_training.attachment_path = os.path.join('uploads', content_type, str(year), str(month), str(user_id), new_filename)
        
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
            return jsonify({'success': True, 'message': 'Votre formation externe a été soumise pour validation.', 'redirect_url': url_for('dashboard.dashboard_home')})
        flash('External training submitted for validation!', 'success')
        return redirect(url_for('dashboard.dashboard_home'))
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
                    
                    existing_event = SkillPracticeEvent.query.filter(
                        SkillPracticeEvent.user_id == current_user.id,
                        SkillPracticeEvent.practice_date == practice_date
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
            return jsonify({'success': True, 'message': 'Pratiques et niveaux mis à jour avec succès !', 'redirect_url': url_for('dashboard.dashboard_home')})
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
            'is_tutor': current_user in comp.skill.tutors, # NEW: Add tutor status
            'needs_recycling': comp.needs_recycling
        })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_declare_skill_practice_form.html', competencies=competencies_data)

    return render_template('profile/declare_skill_practice.html', title='Declare Skill Practice', competencies=competencies_data)



@bp.route('/api/all_skills')
@login_required
def get_all_skills():
    skills = Skill.query.order_by(Skill.name).all()
    skills_data = [{'id': skill.id, 'name': skill.name} for skill in skills]
    return jsonify(skills_data)

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

def _generate_certificate_pdf_buffer(competency_id):
    comp = Competency.query.get_or_404(competency_id)

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

    pdf_output = pdf.output()
    pdf_buffer = io.BytesIO(pdf_output)
    pdf_buffer.seek(0)
    return pdf_buffer


@bp.route('/competency/<int:competency_id>/certificate.pdf')
@login_required
def generate_certificate(competency_id):
    comp = Competency.query.get_or_404(competency_id)
    if comp.user_id != current_user.id and not current_user.can('view_any_certificate'):
        abort(403)

    pdf_buffer = _generate_certificate_pdf_buffer(competency_id)
    
    return send_file(pdf_buffer, as_attachment=True,
                     download_name=f"certificate_{comp.user.full_name.replace(' ', '_')}_{comp.skill.name.replace(' ', '_')}.pdf",
                     mimetype='application/pdf')


@bp.route('/<int:user_id>/booklet.zip')
@login_required
def generate_user_booklet_zip(user_id):
    if user_id != current_user.id and not current_user.can('view_any_booklet'):
        abort(403)
    user = User.query.get_or_404(user_id)
    
    # --- Data Fetching ---
    competencies = user.competencies
    initial_trainings = user.initial_regulatory_trainings
    continuous_trainings = user.continuous_trainings_attended.join(ContinuousTrainingEvent).filter(
        UserContinuousTraining.status == UserContinuousTrainingStatus.APPROVED
    ).order_by(ContinuousTrainingEvent.event_date.desc()).all()
    external_trainings = user.external_trainings.filter_by(status=ExternalTrainingStatus.APPROVED).all()

    # --- PDF Generation (captured in BytesIO) ---
    pdf_buffer = _generate_booklet_pdf(user)

    # --- ZIP File Creation ---
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add the generated PDF booklet
        zf.writestr(f"booklet_{user.full_name.replace(' ', '_')}.pdf", pdf_buffer.read())

        # Add Initial Regulatory Training attachments
        for training in initial_trainings:
            if training.attachment_path:
                attachment_full_path = os.path.join(current_app.root_path, 'static', training.attachment_path)
                if os.path.exists(attachment_full_path):
                    zf.write(attachment_full_path, f"Initial_Training/{training.training_type}_{os.path.basename(training.attachment_path)}")

        # Add Continuous Training attachments
        for ct in continuous_trainings:
            if ct.attendance_attachment_path:
                attachment_full_path = os.path.join(current_app.root_path, 'static', ct.attendance_attachment_path)
                if os.path.exists(attachment_full_path):
                    zf.write(attachment_full_path, f"Continuous_Training/{os.path.basename(ct.attendance_attachment_path)}")
            if ct.event.attachment_path: # Event-level attachment
                attachment_full_path = os.path.join(current_app.root_path, 'static', ct.event.attachment_path)
                if os.path.exists(attachment_full_path):
                    zf.write(attachment_full_path, f"Continuous_Training/Event_Attachments/{os.path.basename(ct.event.attachment_path)}")

        # Add External Training attachments
        for ext_training in external_trainings:
            if ext_training.attachment_path:
                attachment_full_path = os.path.join(current_app.root_path, 'static', ext_training.attachment_path)
                if os.path.exists(attachment_full_path):
                    zf.write(attachment_full_path, f"External_Training/{os.path.basename(ext_training.attachment_path)}")

        # Add Competency Certificates (if any)
        for comp in competencies:
            try:
                certificate_pdf_buffer = _generate_certificate_pdf_buffer(comp.id)
                if certificate_pdf_buffer:
                    zf.writestr(f"Skills_Certificates/certificate_{comp.user.full_name.replace(' ', '_')}_{comp.skill.name.replace(' ', '_')}.pdf", certificate_pdf_buffer.read())
            except Exception as e:
                current_app.logger.error(f"Error generating certificate for competency {comp.id}: {e}")


    zip_buffer.seek(0)
    generation_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return send_file(zip_buffer, as_attachment=True,
                     download_name=f"booklet_{user.full_name.replace(' ', '_')}_{generation_date_str}.zip",
                     mimetype='application/zip')


@bp.route('/training_requests/delete/<int:request_id>', methods=['POST'])
@login_required
def delete_training_request(request_id):
    training_request = TrainingRequest.query.get_or_404(request_id)
    if training_request.requester != current_user and not current_user.can('training_request_manage'):
        abort(403)
    db.session.delete(training_request)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Training request deleted successfully!'})


@bp.route('/edit_training_request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@permission_required('self_submit_training_request') # User needs permission to submit/edit requests
def edit_training_request(request_id):
    training_request = TrainingRequest.query.get_or_404(request_id)

    # Ensure current user is the requester or has admin privileges
    if training_request.requester != current_user and not current_user.can('admin_access'):
        abort(403)

    form = TrainingRequestForm(obj=training_request)

    # Populate skills_requested and species_requested for GET request
    if request.method == 'GET':
        # For QuerySelectMultipleField, data needs to be a list of model objects
        form.skills_requested.data = training_request.skills_requested
        # For QuerySelectField, data needs to be a single model object
        form.species.data = training_request.species_requested[0] if training_request.species_requested else None
        # Set query_factory for skills_requested based on the pre-selected species
        initial_species_id = form.species.data.id if form.species.data else None
        form.skills_requested.query_factory = lambda: Skill.query.join(Skill.species).filter(Species.id == initial_species_id).order_by(Skill.name).all() if initial_species_id else Skill.query.filter(False).all()
    elif request.method == 'POST':
        # For POST, populate query_factory based on submitted species_id
        species_id = request.form.get('species')
        form.skills_requested.query_factory = lambda: Skill.query.join(Skill.species).filter(Species.id == species_id).order_by(Skill.name).all() if species_id else Skill.query.filter(False).all()


    if form.validate_on_submit():
        # Update the training_request object
        form.populate_obj(training_request)

        # Handle many-to-many relationships for skills_requested and species_requested
        training_request.skills_requested.clear()
        for skill in form.skills_requested.data:
            training_request.skills_requested.append(skill)

        training_request.species_requested.clear()
        if form.species.data:
            training_request.species_requested.append(form.species.data)

        db.session.commit()
        flash('Demande de formation mise à jour avec succès !', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Demande de formation mise à jour avec succès !', 'redirect_url': url_for('dashboard.dashboard_home')})
        return redirect(url_for('dashboard.dashboard_home'))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render_template('profile/_training_request_form.html', form=form, api_key=current_user.api_key)
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profile/_training_request_form.html', form=form, api_key=current_user.api_key)

    return render_template('profile/_training_request_form.html', title='Modifier Demande de Formation', form=form)


@bp.route('/external_training/delete/<int:training_id>', methods=['POST'])
@login_required
def delete_external_training(training_id):
    external_training = ExternalTraining.query.get_or_404(training_id)
    if external_training.user_id != current_user.id and not current_user.can('external_training_validate'):
        abort(403)

    # Delete associated attachment if it exists
    if external_training.attachment_path:
        file_path = os.path.join(current_app.root_path, 'static', external_training.attachment_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(external_training)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Formation externe supprimée avec succès !'})


@bp.route('/edit_external_training/<int:training_id>', methods=['GET', 'POST'])
@login_required
@permission_required('self_submit_external_training')
def edit_external_training(training_id):
    external_training = ExternalTraining.query.options(
        db.joinedload(ExternalTraining.skill_claims).joinedload(ExternalTrainingSkillClaim.skill),
        db.joinedload(ExternalTraining.skill_claims).joinedload(ExternalTrainingSkillClaim.species_claimed)
    ).get_or_404(training_id)

    if external_training.user_id != current_user.id and not current_user.can('external_training_validate'):
        abort(403)

    form = ExternalTrainingForm(obj=external_training)

    if request.method == 'GET':
        # Pre-populate skill claims for GET request
        # This part is tricky with FieldList and FormField.
        # The obj=external_training should handle basic fields.
        # For skill_claims, we need to ensure the form's FieldList is populated correctly.
        # If the form was already submitted with errors, it will have data.
        # Otherwise, we populate from the external_training object.
        if not form.skill_claims.entries: # Only populate if not already populated (e.g., from a failed POST)
            while len(form.skill_claims.entries) > 0:
                form.skill_claims.pop_entry()
            for claim in external_training.skill_claims:
                claim_form = ExternalTrainingSkillClaimForm(
                    skill=claim.skill,
                    level=claim.level,
                    species_claimed=claim.species_claimed,
                    wants_to_be_tutor=claim.wants_to_be_tutor,
                    practice_date=claim.practice_date
                )
                form.skill_claims.append_entry(claim_form)

    if form.validate_on_submit():
        # Update basic fields
        form.populate_obj(external_training)

        # Handle attachment update
        if form.attachment.data:
            # Delete old attachment if it exists
            if external_training.attachment_path:
                old_path = os.path.join(current_app.root_path, 'static', external_training.attachment_path)
                if os.path.exists(old_path):
                    os.remove(old_path)

            content_type = "external_training"
            current_utc = datetime.now(timezone.utc)
            year = current_utc.year
            month = current_utc.month
            user_id = current_user.id
            external_trainer_slug = secure_filename(form.external_trainer_name.data.lower().replace(' ', '_'))[:50]
            timestamp = int(current_utc.timestamp())
            original_filename = secure_filename(form.attachment.data.filename)
            file_extension = os.path.splitext(original_filename)[1]

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', content_type, str(year), str(month), str(user_id))
            os.makedirs(upload_folder, exist_ok=True)

            new_filename = f"{user_id}_{content_type}_{external_trainer_slug}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_folder, new_filename)
            form.attachment.data.save(file_path)
            external_training.attachment_path = os.path.join('uploads', content_type, str(year), str(month), str(user_id), new_filename)

        # Handle skill claims: remove old ones, add new ones
        for claim in external_training.skill_claims:
            db.session.delete(claim)
        external_training.skill_claims.clear()
        db.session.flush() # Ensure old claims are deleted before adding new ones

        for skill_claim_data in form.skill_claims.data:
            skill_claim = ExternalTrainingSkillClaim(
                skill=skill_claim_data['skill'],
                level=skill_claim_data['level'],
                species_claimed=skill_claim_data['species_claimed'],
                wants_to_be_tutor=skill_claim_data['wants_to_be_tutor'],
                practice_date=skill_claim_data['practice_date']
            )
            external_training.skill_claims.append(skill_claim)

        db.session.commit()
        flash('Formation externe mise à jour avec succès !', 'success')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Formation externe mise à jour avec succès !', 'redirect_url': url_for('dashboard.dashboard_home')})
        return redirect(url_for('dashboard.dashboard_home'))
    elif request.method == 'POST': # Validation failed for POST request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Need to pass all_skills_json and all_species_json for Select2 re-initialization
            all_skills = [{'id': skill.id, 'name': skill.name} for skill in Skill.query.order_by(Skill.name).all()]
            all_species = [{'id': species.id, 'name': species.name} for species in Species.query.order_by(Species.name).all()]
            form_html = render_template('profile/_external_training_form.html', form=form, all_skills_json=json.dumps(all_skills), all_species_json=json.dumps(all_species))
            return jsonify({'success': False, 'form_html': form_html, 'message': 'Veuillez corriger les erreurs du formulaire.'}), 400

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        all_skills = [{'id': skill.id, 'name': skill.name} for skill in Skill.query.order_by(Skill.name).all()]
        all_species = [{'id': species.id, 'name': species.name} for species in Species.query.order_by(Species.name).all()]
        return render_template('profile/_external_training_form.html', form=form, all_skills_json=json.dumps(all_skills), all_species_json=json.dumps(all_species))

    all_skills = [{'id': skill.id, 'name': skill.name} for skill in Skill.query.order_by(Skill.name).all()]
    all_species = [{'id': species.id, 'name': species.name} for species in Species.query.order_by(Species.name).all()]
    return render_template('profile/submit_external_training.html', title='Modifier Formation Externe', form=form, all_skills_json=json.dumps(all_skills), all_species_json=json.dumps(all_species))


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


@bp.route('/dismissed_notifications')
@login_required
def dismissed_notifications():
    dismissed_notifications = UserDismissedNotification.query.filter_by(user_id=current_user.id).order_by(UserDismissedNotification.dismissed_at.desc()).all()
    return render_template('dashboard/dismissed_notifications.html',
                           title='Dismissed Notifications',
                           dismissed_notifications=dismissed_notifications)

@bp.route('/skills')
@login_required
def skills_list():
    form = ProposeSkillForm()
    skills_query = db.session.query(
        Skill,
        func.count(func.distinct(Competency.user_id)).label('user_count'),
        func.count(func.distinct(tutor_skill_association.c.user_id)).label('tutor_count')
    ).outerjoin(Competency, Skill.id == Competency.skill_id)      .outerjoin(tutor_skill_association, Skill.id == tutor_skill_association.c.skill_id)      .options(db.joinedload(Skill.species))      .group_by(Skill.id)

    skill_name = request.args.get('skill_name', '')
    if skill_name:
        skills_query = skills_query.filter(Skill.name.ilike(f'%{skill_name}%'))

    skills_data = skills_query.order_by(Skill.name).all()

    return render_template('profile/skills_list.html',
                           title='Available Skills',
                           skills_data=skills_data,
                           skill_name=skill_name,
                           form=form)

