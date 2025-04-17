import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from replit import db
from models import User

# Initialize blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tournaments.index'))
    
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        
        # Check if user exists and password is correct
        if email in db and 'password' in db[email]:
            stored_password = db[email]['password']
            if check_password_hash(stored_password, password):
                user = User(
                    email,
                    db[email].get('email'),
                    db[email].get('name'),
                    db[email].get('attending', []),
                    db[email].get('raised_hand', {}),
                    db[email].get('lanyard_ordered', False),
                    db[email].get('notifications', True)
                )
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
        email = request.form['email'].lower()
        name = request.form['name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Form validation
        if email in db:
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        # Store user in database
        db[email] = {
            'email': email,
            'name': name,
            'password': generate_password_hash(password),
            'attending': [],
            'raised_hand': {},
            'lanyard_ordered': False,
            'notifications': True
        }
        
        # Log the user in
        user = User(email, email, name)
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('tournaments.index'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


