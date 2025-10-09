from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.email import send_email
from flask import current_app
from app.models import User

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile.user_profile'))
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
        if current_user.is_admin:
            return redirect(url_for('admin.index'))
        else:
            return redirect(url_for('profile.user_profile', username=current_user.full_name))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        if not user.is_approved:
            flash('Your account is awaiting administrator approval.')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            if current_user.is_admin:
                next_page = url_for('admin.index')
            else:
                next_page = url_for('profile.user_profile', username=current_user.full_name)
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    if current_user.is_admin:
        redirect_url = url_for('admin.index')
    else:
        redirect_url = url_for('profile.user_profile')
    logout_user()
    return redirect(redirect_url)
