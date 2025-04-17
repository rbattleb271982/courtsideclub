import os
import secrets
import string
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

# Initialize blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tournaments.index'))
    
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next', '')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('tournaments.index'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html', google_enabled=False)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tournaments.index'))
    
    if request.method == 'POST':
        try:
            email = request.form['email'].lower()
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            
            # Log for debugging
            logging.info(f"Registration attempt with email: {email}")
            logging.info(f"First name: {first_name}, Last name: {last_name}")
            
            # Generate a secure random password for the user
            # Complex password with letters, numbers, and symbols
            alphabet = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'
            password = ''.join(secrets.choice(alphabet) for _ in range(12))
            
            # Form validation
            try:
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    flash('Email already registered.', 'danger')
                    return render_template('register.html')
            except Exception as e:
                logging.error(f"Error checking existing user: {str(e)}")
                flash('An error occurred while checking user information.', 'danger')
                return render_template('register.html')
            
            # Create and store user
            try:
                new_user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password_hash=generate_password_hash(password)
                )
                
                db.session.add(new_user)
                db.session.commit()
                
                # Log the user in
                login_user(new_user)
                
                # Display the generated password to the user (only once)
                flash(f'Registration successful! Your generated password is: {password}', 'success')
                flash('Please save this password now. It will not be shown again.', 'warning')
                
                # Store the password in the session temporarily to show on the next page
                session['temp_password'] = password
                
                return redirect(url_for('user.profile'))
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error creating new user: {str(e)}")
                flash('An error occurred during registration. Please try again.', 'danger')
                return render_template('register.html')
                
        except Exception as e:
            logging.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


