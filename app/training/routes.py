import os
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db, mail
from app.training import bp
from app.training.forms import TrainingSessionForm
from app.models import TrainingRequest, TrainingRequestStatus, TrainingSession, Competency, ContinuousTrainingEvent, ContinuousTrainingEventStatus
from app.decorators import permission_required
from flask_mail import Message
from ics import Calendar, Event
from datetime import datetime, timedelta, timezone

@bp.route('/requests')
@login_required
@permission_required('training_request_manage') # Or a custom decorator for tutors/admins
def list_training_requests():
    training_requests = TrainingRequest.query.filter_by(status=TrainingRequestStatus.PENDING).all()
    return render_template('training/list_training_requests.html', title='Training Requests', requests=training_requests)

def _populate_form_from_training_request(form, training_request):
    """Helper function to pre-populate TrainingSessionForm from a TrainingRequest."""
    form.skills_covered.data = training_request.skills_requested
    # You might want to pre-populate attendees based on the request, or leave it for manual selection
    # form.attendees.data = [training_request.requester]
    # Add other fields if they exist in TrainingRequest and should pre-fill TrainingSessionForm
    # For example:
    # if training_request.training_path:
    #     form.training_path.data = training_request.training_path
    # if training_request.description:
    #     form.description.data = training_request.description
    # if training_request.requester:
    #     form.attendees.data = [training_request.requester]
    return form

def _populate_form_from_training_request(form, training_request):
    """Helper function to pre-populate TrainingSessionForm from a TrainingRequest."""
    form.skills_covered.data = training_request.skills_requested
    # You might want to pre-populate attendees based on the request, or leave it for manual selection
    # form.attendees.data = [training_request.requester]
    # Add other fields if they exist in TrainingRequest and should pre-fill TrainingSessionForm
    # For example:
    # if training_request.training_path:
    #     form.training_path.data = training_request.training_path
    # if training_request.description:
    #     form.description.data = training_request.description
    # if training_request.requester:
    #     form.attendees.data = [training_request.requester]
    return form

def _create_session_object_from_form(form):
    """Helper to create and populate a TrainingSession object from form data."""
    session = TrainingSession(
        title=form.title.data,
        location=form.location.data,
        start_time=form.start_time.data,
        end_time=form.end_time.data,
        tutor=form.tutor.data,
        ethical_authorization_id=form.ethical_authorization_id.data,
        animal_count=form.animal_count.data
    )
    session.attendees = form.attendees.data
    session.skills_covered = form.skills_covered.data
    return session

def _handle_session_attachment(form, session):
    """Helper to manage file uploads for a TrainingSession."""
    if form.attachment.data:
        content_type = "training_session"
        current_utc = datetime.now(timezone.utc)
        year = current_utc.year
        month = current_utc.month
        # Assuming the creator of the session is the current_user
        user_id = current_user.id
        session_title_slug = secure_filename(session.title.lower().replace(' ', '_'))[:50] # Slugify title, limit length
        timestamp = int(current_utc.timestamp())
        original_filename = secure_filename(form.attachment.data.filename)
        file_extension = os.path.splitext(original_filename)[1]

        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', content_type, str(year), str(month), str(user_id))
        os.makedirs(upload_folder, exist_ok=True)

        new_filename = f"{user_id}_{content_type}_{session_title_slug}_{timestamp}{file_extension}"
        file_path = os.path.join(upload_folder, new_filename)
        form.attachment.data.save(file_path)
        session.attachment_path = os.path.join('uploads', content_type, str(year), str(month), str(user_id), new_filename)

def _create_session_competencies(session):
    """Helper to create competency records for attendees of a TrainingSession."""
    for attendee in session.attendees:
        for skill in session.skills_covered:
            existing_competency = Competency.query.filter_by(user_id=attendee.id, skill_id=skill.id).first()
            if not existing_competency:
                competency = Competency(
                    user=attendee,
                    skill=skill,
                    level='Novice',
                    evaluation_date=session.end_time,
                    evaluator=session.tutor,
                    training_session=session
                )
                db.session.add(competency)

def _send_session_reminders(session):
    """Helper to send email reminders and ICS files for a TrainingSession."""
    c = Calendar()
    e = Event()
    e.name = session.title
    e.begin = session.start_time
    e.end = session.end_time
    e.location = session.location
    e.description = f"Training Session for {', '.join([s.name for s in session.skills_covered])}"
    c.add_event(e)

    ics_filename = secure_filename(f"{session.title}_{session.start_time.strftime('%Y%m%d%H%M')}.ics")
    ics_path = os.path.join(current_app.root_path, 'static', 'ics', ics_filename)
    os.makedirs(os.path.dirname(ics_path), exist_ok=True)
    with open(ics_path, 'w') as f:
        f.writelines(c)

    for attendee in session.attendees:
        msg = Message(f"Training Session Reminder: {session.title}",
                      sender=current_app.config['ADMINS'][0],
                      recipients=[attendee.email])
        msg.body = render_template('email/training_session_reminder.txt', user=attendee, session=session)
        msg.html = render_template('email/training_session_reminder.html', user=attendee, session=session)
        with current_app.open_resource(ics_path) as fp:
            msg.attach(ics_filename, "text/calendar", fp.read())
        mail.send(msg)
    flash('Email reminders sent!', 'info')

@bp.route('/requests/<int:request_id>/create_session', methods=['GET', 'POST'])
@login_required
@permission_required('training_session_manage') # Or a custom decorator for tutors/admins
def create_training_session_from_request(request_id):
    training_request = TrainingRequest.query.get_or_404(request_id)
    form = TrainingSessionForm()

    if form.validate_on_submit():
        session = _create_session_object_from_form(form)
        _handle_session_attachment(form, session)

        db.session.add(session)

        # Update training request status
        training_request.status = TrainingRequestStatus.APPROVED
        db.session.add(training_request)
        db.session.commit() # Commit here to get session.id for competencies

        _create_session_competencies(session)
        db.session.commit() # Commit competencies

        if form.send_email_reminders.data:
            _send_session_reminders(session)

        flash('Training session created successfully!', 'success')
        return redirect(url_for('training.list_training_requests'))
    
    elif request.method == 'GET':
        # Pre-populate form with data from training request
        form.skills_covered.data = training_request.skills_requested
        # You might want to pre-populate attendees based on the request, or leave it for manual selection
        # form.attendees.data = [training_request.requester]

    return render_template('training/training_session_form.html', title='Create Training Session', form=form, training_request=training_request, action_url=url_for('training.create_training_session_from_request', request_id=training_request.id))
@bp.route('/create_session_from_requests', methods=['GET', 'POST'])
@login_required
@permission_required('training_session_manage')
def create_session_from_requests():
    form = TrainingSessionForm()
    training_requests = [] # Initialize an empty list

    if request.method == 'POST':
        # Check if this is the initial POST from list_training_requests.html
        # or a subsequent POST from the training_session_form.html
        if 'request_ids' in request.form and 'skill_grouping' in request.form:
            # This is the initial POST from list_training_requests.html
            request_ids = request.form.getlist('request_ids')
            skill_grouping = request.form.get('skill_grouping') # 'all' or 'common'

            if not request_ids:
                flash('No training requests selected.', 'warning')
                return redirect(url_for('admin.list_training_requests'))

            training_requests = TrainingRequest.query.filter(TrainingRequest.id.in_(request_ids)).options(
                db.joinedload(TrainingRequest.requester),
                db.joinedload(TrainingRequest.skills_requested)
            ).all()

            if not training_requests:
                flash('No valid training requests found for the selected IDs.', 'danger')
                return redirect(url_for('admin.list_training_requests'))

            all_skills = set()
            common_skills = None
            all_attendees = set()

            for req in training_requests:
                all_attendees.add(req.requester)
                current_request_skills = set(req.skills_requested)
                all_skills.update(current_request_skills)

                if common_skills is None:
                    common_skills = current_request_skills
                else:
                    common_skills.intersection_update(current_request_skills)

            skills_to_prefill = []
            if skill_grouping == 'all':
                skills_to_prefill = list(all_skills)
            elif skill_grouping == 'common':
                skills_to_prefill = list(common_skills)
            
            skills_to_prefill.sort(key=lambda s: s.name)

            form.attendees.data = list(all_attendees)
            form.skills_covered.data = skills_to_prefill
            
            if skills_to_prefill:
                skill_names = [s.name for s in skills_to_prefill]
                form.title.data = f"Formation: {', '.join(skill_names[:3])}{'...' if len(skill_names) > 3 else ''}"
            else:
                form.title.data = "Nouvelle Session de Formation"
            
            # Pass the original request IDs to the form for later submission
            original_request_ids = [req.id for req in training_requests]

        elif form.validate_on_submit():
            # This block handles the submission of the TrainingSessionForm
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
                content_type = "training_session"
                current_utc = datetime.now(timezone.utc)
                year = current_utc.year
                month = current_utc.month
                user_id = current_user.id # Assuming the creator of the session is the current_user
                session_title_slug = secure_filename(session.title.lower().replace(' ', '_'))[:50] # Slugify title, limit length
                timestamp = int(current_utc.timestamp())
                original_filename = secure_filename(form.attachment.data.filename)
                file_extension = os.path.splitext(original_filename)[1]

                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', content_type, str(year), str(month), str(user_id))
                os.makedirs(upload_folder, exist_ok=True)

                new_filename = f"{user_id}_{content_type}_{session_title_slug}_{timestamp}{file_extension}"
                file_path = os.path.join(upload_folder, new_filename)
                form.attachment.data.save(file_path)
                session.attachment_path = os.path.join('uploads', content_type, str(year), str(month), str(user_id), new_filename)

            session.attendees = form.attendees.data
            session.skills_covered = form.skills_covered.data
            
            db.session.add(session)

            original_request_ids = request.form.getlist('original_request_ids')
            if original_request_ids:
                requests_to_update = TrainingRequest.query.filter(TrainingRequest.id.in_(original_request_ids)).all()
                for req in requests_to_update:
                    req.status = TrainingRequestStatus.APPROVED
                    db.session.add(req)

            db.session.commit()

            for attendee in session.attendees:
                for skill in session.skills_covered:
                    existing_competency = Competency.query.filter_by(user_id=attendee.id, skill_id=skill.id).first()
                    if not existing_competency:
                        competency = Competency(
                            user=attendee,
                            skill=skill,
                            level='Novice',
                            evaluation_date=session.end_time,
                            evaluator=session.tutor,
                            training_session=session
                        )
                        db.session.add(competency)
            db.session.commit()

            if form.send_email_reminders.data:
                c = Calendar()
                e = Event()
                e.name = session.title
                e.begin = session.start_time
                e.end = session.end_time
                e.location = session.location
                e.description = f"Training Session for {', '.join([s.name for s in session.skills_covered])}"
                c.add_event(e)

                ics_filename = secure_filename(f"{session.title}_{session.start_time.strftime('%Y%m%d%H%M')}.ics")
                ics_path = os.path.join(current_app.root_path, 'static', 'ics', ics_filename)
                os.makedirs(os.path.dirname(ics_path), exist_ok=True)
                with open(ics_path, 'w') as f:
                    f.writelines(c)
                
                for attendee in session.attendees:
                    msg = Message(f"Training Session Reminder: {session.title}",
                                  sender=current_app.config['ADMINS'][0],
                                  recipients=[attendee.email])
                    msg.body = render_template('email/training_session_reminder.txt', user=attendee, session=session)
                    msg.html = render_template('email/training_session_reminder.html', user=attendee, session=session)
                    with current_app.open_resource(ics_path) as fp:
                        msg.attach(ics_filename, "text/calendar", fp.read())
                    mail.send(msg)
                flash('Email reminders sent!', 'info')

            flash('Training session created successfully!', 'success')
            return redirect(url_for('training.list_training_requests'))
        else:
            # If form validation fails on submission, re-render with errors
            # Need to re-populate training_requests if available from hidden field
            original_request_ids = request.form.getlist('original_request_ids')
            if original_request_ids:
                training_requests = TrainingRequest.query.filter(TrainingRequest.id.in_(original_request_ids)).options(
                    db.joinedload(TrainingRequest.requester),
                    db.joinedload(TrainingRequest.skills_requested)
                ).all()
            flash('Please correct the errors in the form.', 'danger')

    # For GET requests or initial rendering of the form (e.g., if validation fails on submission)
    # If training_requests is empty, it means it's a GET request or initial load without pre-filled data
    # In this case, original_request_ids might still be present from a failed form submission
    if not training_requests and 'original_request_ids' in request.form:
        original_request_ids = request.form.getlist('original_request_ids')
        if original_request_ids:
            training_requests = TrainingRequest.query.filter(TrainingRequest.id.in_(original_request_ids)).options(
                db.joinedload(TrainingRequest.requester),
                db.joinedload(TrainingRequest.skills_requested)
            ).all()

    return render_template('training/training_session_form.html', 
                           title='Create Grouped Training Session', 
                           form=form, 
                           training_requests=training_requests, # Pass all selected requests
                           original_request_ids=[req.id for req in training_requests], # Pass IDs for form submission
                           action_url=url_for('training.create_session_from_requests'))

# Placeholder for actual email templates
# I will create these later if needed, for now, they are just referenced.

# Placeholder for actual email templates
# I will create these later if needed, for now, they are just referenced.

# Placeholder for actual email templates
# I will create these later if needed, for now, they are just referenced.

@bp.route('/event/<int:event_id>/details')
@login_required
def show_continuous_training_event_details(event_id):
    """
    Provides the details for a continuous training event,
    intended to be loaded into a modal.
    """
    event = ContinuousTrainingEvent.query.get_or_404(event_id)
    # Any user can view the details of an approved event
    return render_template('training/_event_details.html', event=event, ContinuousTrainingEventStatus=ContinuousTrainingEventStatus)
