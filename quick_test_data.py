"""
Quick Test Data Creation Script

Creates a basic set of tournament interactions for testing the system.
"""
import random
from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress

# Define the main tournaments we want to test
POPULAR_TOURNAMENT_IDS = [
    'aus_open', 'roland_garros', 'wimbledon', 'us_open',  # Grand Slams
    'indian_wells', 'miami_open', 'madrid_open', 'rome_masters',  # Masters 1000
    'queens_club', 'berlin_open'  # 500 Series
]

# Track attendance
attending_count = 0
maybe_count = 0
lanyard_count = 0

def create_sample_data():
    """Create quick test data for each user"""
    # Get all test users
    users = User.query.filter(User.email.like('%test%@example.com')).all()
    if not users:
        print("No test users found. Please run create_qa_test_users.py first.")
        return
    
    # Get tournaments
    tournaments = Tournament.query.filter(Tournament.id.in_(POPULAR_TOURNAMENT_IDS)).all()
    if not tournaments:
        print("No tournaments found with selected IDs.")
        return
    
    print(f"Found {len(users)} test users and {len(tournaments)} target tournaments")
    
    # Process each user
    for user in users:
        print(f"Creating data for {user.email}")
        
        # Clear existing data
        UserTournament.query.filter_by(user_id=user.id).delete()
        user.lanyard_ordered = False
        
        # Each user gets 5 random tournaments
        user_tournaments = random.sample(tournaments, min(5, len(tournaments)))
        
        # Create attendance records
        for idx, tournament in enumerate(user_tournaments):
            # First 3 are "attending", rest are "maybe"
            is_attending = idx < 3
            attendance_type = "attending" if is_attending else "maybe"
            
            global attending_count, maybe_count
            if is_attending:
                attending_count += 1
            else:
                maybe_count += 1
            
            # Create record
            record = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                attendance_type=attendance_type,
                attending=is_attending,
                wants_to_meet=True
            )
            db.session.add(record)
            
            # Add sessions for attending users
            if is_attending:
                # Create 2-4 session labels
                sessions = []
                for day in range(1, 5):
                    if random.random() < 0.5:
                        sessions.append(f"Day {day} - Day")
                    if random.random() < 0.5:
                        sessions.append(f"Day {day} - Night")
                
                # Ensure at least one session
                if not sessions:
                    sessions = ["Day 1 - Day"]
                
                record.session_label = ", ".join(sessions)
        
        # 80% of users with "attending" records get lanyard
        attending_records = UserTournament.query.filter_by(
            user_id=user.id, attending=True
        ).count()
        
        if attending_records > 0 and random.random() < 0.8:
            user.lanyard_ordered = True
            
            # Add shipping address if needed
            if not ShippingAddress.query.filter_by(user_id=user.id).first():
                address = ShippingAddress(
                    user_id=user.id,
                    name=user.get_full_name(),
                    address1="123 Main St",
                    city="New York",
                    state="NY",
                    zip_code="10001",
                    country="United States"
                )
                db.session.add(address)
                
            global lanyard_count
            lanyard_count += 1
    
    # Commit all changes
    db.session.commit()
    
    print(f"Created test data:")
    print(f"- Attending records: {attending_count}")
    print(f"- Maybe attending records: {maybe_count}")
    print(f"- Lanyard orders: {lanyard_count}")

if __name__ == "__main__":
    with app.app_context():
        create_sample_data()