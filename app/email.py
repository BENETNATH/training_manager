"""
This module provides functions for sending emails asynchronously.
"""
import threading
from flask import current_app, render_template
from flask_mail import Message
from app import mail


def send_async_email(app, msg):
    """
    Sends an email asynchronously within the Flask application context.
    """
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    """
    Composes and sends an email using Flask-Mail.
    """
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # This is a common and accepted pattern in Flask to get the actual app object.
    threading.Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()  # pylint: disable=W0212

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Training Manager] Reset Your Password',
               sender=current_app.config['MAIL_USERNAME'],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))
