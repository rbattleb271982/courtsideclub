from app import app, db
from models import User, UserTournament, UserPastTournament, Tournament
from werkzeug.security import generate_password_hash

with app.app_context():
    # Check if users exist already
    user1 = User.query.filter_by(email='testuser1@example.com').first()
    user2 = User.query.filter_by(email='testuser2@example.com').first()
    
    # If not, create them
    if not user1:
        user1 = User(
            email='testuser1@example.com',
            name='Test User 1',
            first_name='Test',
            last_name='User 1',
            password_hash=generate_password_hash('test1234')
        )
        db.session.add(user1)
        print("Created Test User 1")
    else:
        print("Test User 1 already exists")
        
    if not user2:
        user2 = User(
            email='testuser2@example.com',
            name='Test User 2',
            first_name='Test',
            last_name='User 2',
            password_hash=generate_password_hash('test1234')
        )
        db.session.add(user2)
        print("Created Test User 2")
    else:
        print("Test User 2 already exists")
    
    db.session.commit()
    
    # Set up User 1 attendance and past tournaments
    # First, clean any existing data
    UserTournament.query.filter_by(user_id=user1.id).delete()
    UserPastTournament.query.filter_by(user_id=user1.id).delete()
    
    # Set up Roland Garros attendance 
    user_tournament = UserTournament(
        user_id=user1.id,
        tournament_id='roland_garros',
        attending=True,
        attendance_type='attending',
        wants_to_meet=True,
        session_label='Day 1 - Day, Day 2 - Day'
    )
    db.session.add(user_tournament)
    
    # Add past tournaments for User 1
    past_tournaments = ['madrid_open', 'indian_wells', 'doha']
    for tournament_id in past_tournaments:
        past_tournament = UserPastTournament(
            user_id=user1.id,
            tournament_id=tournament_id
        )
        db.session.add(past_tournament)
    
    db.session.commit()
    print(f"\nSetup complete:")
    print(f"- User 1 (ID: {user1.id}) is attending Roland Garros")
    print(f"- User 1 has past tournaments: Madrid Open, Indian Wells, Doha")
    print(f"- User 2 (ID: {user2.id}) is not attending any tournaments")
    
    print("\nTesting URLs:")
    print("1. Log in as Test User 1:")
    print("   - Email: testuser1@example.com")
    print("   - Password: test1234")
    print("   - Visit: http://localhost:5000/tournaments/roland_garros")
    print("\n2. Log in as Test User 2:")
    print("   - Email: testuser2@example.com")
    print("   - Password: test1234")
    print("   - Visit: http://localhost:5000/tournaments/roland_garros")
