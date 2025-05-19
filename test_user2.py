from app import app, db
from models import User, Tournament, UserTournament, UserPastTournament
from flask_login import login_user

with app.app_context():
    # Log in as User 2
    user2 = User.query.filter_by(email='testuser2@example.com').first()
    print(f"Logged in as {user2.name} (ID: {user2.id})")
    
    # Check what would be displayed for Roland Garros
    # First, get tournament data
    tournament = Tournament.query.filter_by(id='roland_garros').first()
    
    # Get attendance stats
    attending_count = UserTournament.query.filter(
        UserTournament.tournament_id == 'roland_garros',
        UserTournament.attending == True
    ).count()
    
    meeting_count = UserTournament.query.filter(
        UserTournament.tournament_id == 'roland_garros',
        UserTournament.attending == True,
        UserTournament.wants_to_meet == True
    ).count()
    
    print(f"\nRoland Garros attendance stats (visible to User 2):")
    print(f"- Attending users: {attending_count}")
    print(f"- Open to meeting: {meeting_count}")
    
    # Get past tournaments data (as would be seen by User 2)
    print("\nShared past tournaments that would be visible:")
    
    # Get all users attending
    attending_users = UserTournament.query.filter(
        UserTournament.tournament_id == 'roland_garros',
        UserTournament.attending == True
    ).all()
    
    attending_user_ids = [ut.user_id for ut in attending_users]
    
    # Get past tournaments of attending users
    past_tournaments = db.session.query(
        Tournament.name, db.func.count(UserPastTournament.user_id).label('count')
    ).join(
        UserPastTournament, Tournament.id == UserPastTournament.tournament_id
    ).filter(
        UserPastTournament.user_id.in_(attending_user_ids),
        Tournament.id != 'roland_garros'  # Exclude current tournament
    ).group_by(
        Tournament.name
    ).order_by(
        db.desc('count')
    ).all()
    
    for name, count in past_tournaments:
        print(f"- {name}: {count} {'people have' if count > 1 else 'person has'} been to this tournament")
