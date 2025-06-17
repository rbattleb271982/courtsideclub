import os
import secrets
import string
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
# Rate limiting will be implemented at the application level

from models import db, User
from services.sendgrid_service import send_email
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Initialize blueprint
auth_bp = Blueprint('auth', __name__)

# Rate limiter will be initialized separately to avoid circular imports

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
                
                # Debug logging before login_user
                logging.info(f"About to call login_user for user {user.id}")
                
                # Make session permanent for proper persistence
                session.permanent = True
                
                login_result = login_user(user, remember=remember)
                logging.info(f"login_user result: {login_result}")
                
                # Commit any pending database changes
                db.session.commit()
                
                # Check if user is actually logged in
                logging.info(f"current_user.is_authenticated after login: {current_user.is_authenticated}")
                logging.info(f"Session contents: {dict(session)}")

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

                # Set session flag for welcome message
                session['show_welcome'] = True
                session.modified = True
                session.permanent = True
                
                # Pass user ID to login-success to re-establish session if cookies are blocked
                return redirect(url_for('auth.login_success', user_id=user.id))

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

                # Send welcome email
                from services.email import send_welcome_email
                send_welcome_email(new_user.id)

                # Show welcome message
                flash("Welcome to CourtSide Club! 🎾 You can now choose which tournaments you're attending and let other fans know you're open to meeting. Head to the Tournaments page to get started.", "success")
                
                # Set session flags
                session['show_welcome'] = True
                session.modified = True
                session.permanent = True

                # Use same iframe-compatible flow as login
                return redirect(url_for('auth.login_success', user_id=new_user.id))
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
    log_event(user_id, 'user_logout', data={
        'ip': request.remote_addr,
        'user_agent': str(request.user_agent) if request.user_agent else None
    })
    
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for('main.public_home'))

@auth_bp.route('/reset_password/request', methods=['GET', 'POST'])
def reset_password_request():
    """
    Secure password reset request route with rate limiting.
    Generates secure token and sends branded reset email.
    """
    if current_user.is_authenticated:
        return redirect(url_for('user.my_tournaments'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('reset_password_request.html')

        # Look up the user by email
        user = User.query.filter_by(email=email).first()

        if user:
            try:
                # Generate secure token using itsdangerous
                serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
                token = serializer.dumps(user.email, salt='password-reset-salt')
                
                # Generate reset URL
                reset_url = url_for('auth.reset_password_confirm', token=token, _external=True)
                
                # Send password reset email
                from services.email import send_password_reset_email
                send_password_reset_email(user.email, user.first_name or 'Tennis Fan', reset_url)
                
                logging.info(f"Password reset email sent to: {email}")
                
            except Exception as e:
                logging.error(f"Error sending password reset email: {str(e)}")
                # Still show success message for security
        else:
            # Log attempt but don't reveal email doesn't exist
            logging.info(f"Password reset requested for non-existent email: {email}")

        # Always show same message regardless of email existence (security best practice)
        flash('If your email is registered, you will receive a password reset link shortly.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('reset_password_request.html')

@auth_bp.route('/reset_password/confirm/<token>', methods=['GET', 'POST'])
def reset_password_confirm(token):
    """
    Secure password reset confirmation route with token validation.
    Validates token expiration and updates user password.
    """
    if current_user.is_authenticated:
        return redirect(url_for('user.my_tournaments'))

    # Validate token and extract email
    try:
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiry
    except SignatureExpired:
        flash('Your password reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.reset_password_request'))
    except BadSignature:
        flash('Invalid password reset link. Please request a new one.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    # Find the user
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid password reset link. Please request a new one.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate inputs
        if not password or not confirm_password:
            flash('Please fill in all fields.', 'danger')
            return render_template('reset_password.html', token=token)

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return render_template('reset_password.html', token=token)

        # Validate password requirements
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('reset_password.html', token=token)

        try:
            # Update the user's password
            user.password_hash = generate_password_hash(password)
            db.session.commit()

            # Log the password reset event
            from services.event_logger import log_event
            try:
                log_event(user.id, 'password_reset', data={
                    'ip': request.remote_addr,
                    'user_agent': str(request.user_agent) if request.user_agent else None
                })
            except Exception as log_e:
                logging.warning(f"Failed to log password reset event: {str(log_e)}")

            logging.info(f"Password successfully reset for user: {email}")
            flash('Your password has been updated successfully. You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            logging.error(f"Error updating password for {email}: {str(e)}")
            db.session.rollback()
            flash('An error occurred while updating your password. Please try again.', 'danger')
            return render_template('reset_password.html', token=token)

    # GET request - show the reset form
    return render_template('reset_password.html', token=token)

@auth_bp.route('/login-success')
def login_success():
    """Re-establish session if cookies were blocked, then redirect to my-tournaments"""
    user_id = request.args.get('user_id')
    
    # If already authenticated, proceed to redirect
    if current_user.is_authenticated:
        return render_template("auth/login_success.html")
    
    # If not authenticated but have user_id, re-establish session
    if user_id:
        try:
            user = User.query.get(int(user_id))
            if user:
                # Re-establish the session
                login_user(user)
                session['show_welcome'] = True
                session.modified = True
                session.permanent = True
                
                logging.info(f"Re-established session for user {user.email} via login-success")
                return render_template("auth/login_success.html")
        except (ValueError, TypeError):
            pass
    
    # If no valid session can be established, redirect to login
    return redirect(url_for('auth.login'))

