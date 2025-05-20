import os
import secrets
import string
import logging
try:
    from flask import Blueprint, render_template, request, redirect, url_for, flash, session
    from flask_login import login_user, logout_user, login_required, current_user
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError:
    pass  # Imports will be available at runtime

from models import db, User
from services.sendgrid_service import send_email
from itsdangerous import URLSafeTimedSerializer

# Initialize blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('user.my_tournaments'))

    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']

        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check if user exists and has a password hash
        if user and user.password_hash:
            # Debug logging
            logging.info(f"Login attempt for user: {email}")
            logging.info(f"Password hash in DB: {user.password_hash[:20]}...")

            # Try to verify the password
            is_valid = check_password_hash(user.password_hash, password)
            logging.info(f"Password check result: {is_valid}")

            if is_valid:
                # Check if the remember checkbox was selected
                remember = 'remember' in request.form
                login_user(user, remember=remember)

                # Log the successful login event
                from services.event_logger import log_event
                event_data = {
                    'method': 'password',
                    'email': email,
                    'ip': request.remote_addr,
                    'user_agent': str(request.user_agent) if request.user_agent else None
                }
                log_event(user.id, 'user_login', event_data)

                # Show welcome message if user hasn't seen it before
                if not user.welcome_seen:
                    flash("Welcome to CourtSide Club! 🎾 You can now choose which tournaments you're attending and let other fans know you're open to meeting. Head to the Tournaments page to get started.", "success")
                    user.welcome_seen = True
                    db.session.commit()

                # Always redirect to my_tournaments after login
                return redirect(url_for('user.my_tournaments'))

        # If we get here, authentication failed
        flash('Invalid email or password', 'danger')

    return render_template('login.html', google_enabled=False)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('user.my_tournaments'))

    if request.method == 'POST':
        try:
            email = request.form['email'].lower()
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            # Log for debugging
            logging.info(f"Registration attempt with email: {email}")
            logging.info(f"First name: {first_name}, Last name: {last_name}")

            # Validate that passwords match
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('register.html')

            # Validate password requirements (should also be checked by frontend)
            if len(password) < 8:
                flash('Password must be at least 8 characters long.', 'danger')
                return render_template('register.html')

            # Form validation
            try:
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    flash('Email already registered.', 'danger')
                    return render_template('register.html')
            except Exception as e:
                logging.error(f"Error checking existing user: {str(e)}", exc_info=True)
                flash('An error occurred while checking user information.', 'danger')
                return render_template('register.html')

            # Create and store user
            try:
                new_user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    name=f"{first_name} {last_name}",  # Also set the name field for compatibility
                    password_hash=generate_password_hash(password),
                    lanyard_ordered=False,
                    notifications=True,
                    welcome_seen=True  # Set to True since we'll show the welcome message directly
                )

                db.session.add(new_user)
                db.session.commit()

                # Log the user in
                login_user(new_user)

                # Log the signup event
                from services.event_logger import log_event
                event_data = {
                    'method': 'signup',
                    'email': email,
                    'ip': request.remote_addr,
                    'user_agent': str(request.user_agent) if request.user_agent else None
                }
                log_event(new_user.id, 'user_signup', event_data)

                # Show welcome message
                flash("Welcome to CourtSide Club! 🎾 You can now choose which tournaments you're attending and let other fans know you're open to meeting. Head to the Tournaments page to get started.", "success")

                return redirect(url_for('user.my_tournaments'))
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error creating new user: {str(e)}", exc_info=True)
                flash('An error occurred during registration. Please try again.', 'danger')
                return render_template('register.html')

        except Exception as e:
            logging.error(f"Registration error: {str(e)}", exc_info=True)
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('register.html')

    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    
    # Log the logout event
    from services.event_logger import log_event
    log_event('user_logout', data={
        'user_id': user_id,
        'ip': request.remote_addr,
        'user_agent': str(request.user_agent) if request.user_agent else None
    })
    
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('user.my_tournaments'))

    if request.method == 'POST':
        email = request.form.get('email', '').lower()

        # Look up the user by email
        user = User.query.filter_by(email=email).first()

        if user:
            try:
                # Generate a secure token
                reset_token = secrets.token_urlsafe(32)

                # In a real app, we would send an email with a reset link
                # For this app, we'll show a link directly in the UI

                flash('Password reset instructions have been sent to your email. Please check your inbox.', 'info')

                # Instead of actually sending an email, we'll just redirect to a page where they can set a new password
                # In a real application, this would be sent via email with a secure token

                # For this demo, we'll directly go to the reset page
                return render_template('reset_password.html', email=email, token=reset_token)

            except Exception as e:
                logging.error(f"Error initiating password reset: {str(e)}")
                flash('An error occurred while processing your request. Please try again.', 'danger')
        else:
            # We don't want to reveal that the email doesn't exist
            flash('If your email is registered, you will receive password reset instructions. Please check your email.', 'info')

            # But we log it for debugging
            logging.info(f"Password reset requested for non-existent email: {email}")

    return render_template('reset_password_request.html')

@auth_bp.route('/reset_password/confirm', methods=['POST'])
def reset_password_confirm():
    email = request.form.get('email')
    token = request.form.get('token')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Validate inputs
    if not all([email, token, password, confirm_password]):
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    # Check if passwords match
    if password != confirm_password:
        flash('Passwords do not match. Please try again.', 'danger')
        return render_template('reset_password.html', email=email, token=token)

    # Validate password requirements
    if len(password) < 8:
        flash('Password must be at least 8 characters long.', 'danger')
        return render_template('reset_password.html', email=email, token=token)

    # Find the user
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    try:
        # Update the user's password
        user.password_hash = generate_password_hash(password)
        db.session.commit()

        # Show success message
        flash('Your password has been updated successfully. You can now log in with your new password.', 'success')

        # Redirect to login page
        return redirect(url_for('auth.login'))

    except Exception as e:
        logging.error(f"Error updating password: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating your password. Please try again.', 'danger')
        return render_template('reset_password.html', email=email, token=token)