from app import app, db
from models import User, UserTournament, UserPastTournament, Tournament
from flask_login import login_user

with app.app_context():
    # Get Test User 1
    user1 = User.query.filter_by(email='testuser1@example.com').first()
    
    if not user1:
        print("Test User 1 not found")
        exit(1)
    
    # Mark them as attending Roland Garros with sessions
    tournament = Tournament.query.filter_by(id='roland_garros').first()
    
    if not tournament:
        print("Roland Garros tournament not found")
        exit(1)
    
    # Create UserTournament record for Roland Garros
    user_tournament = UserTournament(
        user_id=user1.id,
        tournament_id=tournament.id,
        attending=True,
        attendance_type='attending',
        wants_to_meet=True,
        session_label='Day 1 - Day, Day 2 - Day'
    )
    db.session.add(user_tournament)
    
    # Add past tournaments
    past_tournaments = ['madrid_open', 'indian_wells', 'doha']
    for tournament_id in past_tournaments:
        past_tournament = UserPastTournament(
            user_id=user1.id,
            tournament_id=tournament_id
        )
        db.session.add(past_tournament)
    
    db.session.commit()
    
    print(f"Set up Test User 1 (ID: {user1.id}):")
    print(f"- Attending: Roland Garros")
    print(f"- Past tournaments: Madrid Open, Indian Wells, Doha")
