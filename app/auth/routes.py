from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.email import send_email, send_password_reset_email
from flask import current_app
from app.models import User
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.user_profile'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.user_profile'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.user_profile'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(full_name=form.full_name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user! Your account is awaiting administrator approval.')

        # Send email to user about pending approval
        send_email('[Training Manager] Your Account is Awaiting Approval',
                   sender=current_app.config['MAIL_USERNAME'],
                   recipients=[user.email],
                   text_body=render_template('email/registration_pending.txt', user=user),
                   html_body=render_template('email/registration_pending.html', user=user))

        # Notify admins
        admins = User.query.filter_by(is_admin=True).all()
        for admin in admins:
            send_email('[Training Manager] New User Registration Awaiting Approval',
                       sender=current_app.config['MAIL_USERNAME'],
                       recipients=[admin.email],
                       text_body=render_template('email/admin_new_registration.txt', user=user),
                       html_body=render_template('email/admin_new_registration.html', user=user))

        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    
    if current_user.is_authenticated and current_user.is_approved:
        # Log: Already authenticated user trying to access login page
        current_app.logger.info(f"User {current_user.email} (ID: {current_user.id}) attempted to access login page while already authenticated.")
        if current_user.is_admin:
            return redirect(url_for('admin.index'))
        else:
            return redirect(url_for('dashboard.user_profile', username=current_user.full_name))
    form = LoginForm()
    if request.method == 'POST':
        # First, check if the user exists to prioritize the "invalid credentials" message
        # if the user is not registered.
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))

        # If user exists, then proceed with form validation, including CSRF.
        if form.validate_on_submit():
            if not user.check_password(form.password.data):
                flash('Invalid username or password', 'danger')
                return redirect(url_for('auth.login'))
            if not user.is_approved:
                flash('Your account is awaiting administrator approval.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                if current_user.is_admin:
                    next_page = url_for('admin.index')
                else:
                    next_page = url_for('dashboard.user_profile', username=current_user.full_name)
            return redirect(next_page)
        else:
            # If form validation fails (e.g., CSRF, or other field errors)
            if 'csrf_token' in form.errors:
                flash('CSRF token missing or incorrect. Please try again.', 'danger')
            else:
                # Other form validation errors (e.g., empty fields) - these should be rare if user exists
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{form[field].label.text}: {error}', 'danger')
    
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    # Log: Successful logout attempt
    current_app.logger.info(f"User {current_user.email} (ID: {current_user.id}) successfully logged out.")
    if current_user.is_admin:
        redirect_url = url_for('admin.index')
    else:
        redirect_url = url_for('auth.login')
    logout_user()
    return redirect(redirect_url)

@bp.route('/sso_login')
def sso_login():
    token = request.args.get('token')
    if not token:
        flash('Invalid SSO request', 'danger')
        return redirect(url_for('auth.login'))

    serializer = URLSafeTimedSerializer(current_app.config.get('SSO_SECRET_KEY'))
    try:
        data = serializer.loads(token, max_age=30)
        email = data.get('email')
        if not email:
            flash('Invalid SSO token', 'danger')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(email=email).first()
        if not user or not user.is_approved:
            flash('User not found or not approved', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        if user.is_admin:
            return redirect(url_for('admin.index'))
        else:
            return redirect(url_for('dashboard.user_profile', username=user.full_name))

    except (BadSignature, SignatureExpired):
        flash('Invalid or expired SSO token', 'danger')
        return redirect(url_for('auth.login'))
