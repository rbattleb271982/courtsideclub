from app import app, db
from models import User, UserTournament, UserPastTournament, Tournament

with app.app_context():
    # Verify User 1
    user1 = User.query.filter_by(email='testuser1@example.com').first()
    print(f"Test User 1 (ID: {user1.id}, Name: {user1.name})")
    
    # Check tournament attendance
    user1_tournaments = UserTournament.query.filter_by(user_id=user1.id).all()
    print("\nAttending tournaments:")
    for ut in user1_tournaments:
        tournament = Tournament.query.get(ut.tournament_id)
        print(f"- {tournament.name} (Attending: {ut.attending}, Open to meet: {ut.wants_to_meet})")
        print(f"  Sessions: {ut.session_label}")
    
    # Check past tournaments
    user1_past = UserPastTournament.query.filter_by(user_id=user1.id).all()
    print("\nPast tournaments:")
    for pt in user1_past:
        tournament = Tournament.query.get(pt.tournament_id)
        print(f"- {tournament.name}")
        
    # Verify User 2
    user2 = User.query.filter_by(email='testuser2@example.com').first()
    print(f"\nTest User 2 (ID: {user2.id}, Name: {user2.name})")
    
    # Check stats for Roland Garros
    roland_garros = Tournament.query.filter_by(id='roland_garros').first()
    attending_count = UserTournament.query.filter_by(tournament_id='roland_garros', attending=True).count()
    meeting_count = UserTournament.query.filter_by(tournament_id='roland_garros', attending=True, wants_to_meet=True).count()
    
    print(f"\nRoland Garros stats:")
    print(f"- Total attending: {attending_count}")
    print(f"- Open to meeting: {meeting_count}")
