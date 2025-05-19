from app import app, db
from models import User, Tournament, UserTournament
from flask_login import login_user
import requests

with app.app_context():
    # Sign in as User 1
    user1 = User.query.filter_by(email='testuser1@example.com').first()
    print(f"Logged in as {user1.name} (ID: {user1.id})")
    
    # Verify Roland Garros attendance
    ut = UserTournament.query.filter_by(user_id=user1.id, tournament_id='roland_garros').first()
    
    if ut:
        print(f"Attendance status for Roland Garros:")
        print(f"- Attending: {ut.attending}")
        print(f"- Open to meeting: {ut.wants_to_meet}")
        print(f"- Sessions: {ut.session_label}")
    else:
        print("Not attending Roland Garros yet")
