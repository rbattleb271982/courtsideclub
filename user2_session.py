from app import app, db
from models import User
from flask import Flask, request, redirect, url_for, session
from flask_login import login_user

# Test function to log in User 2 and create a session cookie
with app.app_context():
    # Get User 2
    user2 = User.query.filter_by(email='testuser2@example.com').first()
    
    # Log them in programmatically
    app.config['SESSION_TYPE'] = 'filesystem'
    login_user(user2)
    
    # Generate session cookie value for testing
    print("Created session for Test User 2")
    print("Session ID:", session.sid if hasattr(session, 'sid') else "Unable to extract session ID")
    print("To test, visit: http://localhost:5000/tournaments/roland_garros")
