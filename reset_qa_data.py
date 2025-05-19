"""
Reset QA Data Script

This script resets our QA test data to ensure consistent testing:
1. Clears all existing UserTournament records for test users
2. Creates 5+ tournaments for each test user with a balanced mix of attendance types
3. Adds proper session selections for attending users
4. Sets up lanyard orders for eligible users
"""
import logging
import random
from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_test_users():
    """Get all test users for QA"""
    users = User.query.filter(
        (User.email.like('%test%@example.com')) | 
        (User.email == 'richardbattlebaxter@gmail.com')
    ).all()
    return users

def reset_test_data():
    """Reset all test data for QA users"""
    users = get_test_users()
    if not users:
        logger.error("No test users found. Please run create_qa_test_users.py first.")
        return
    
    for user in users:
        # Delete all existing tournament selections
        UserTournament.query.filter_by(user_id=user.id).delete()
        # Reset lanyard ordered status
        user.lanyard_ordered = False
    
    db.session.commit()
    logger.info(f"Reset data for {len(users)} test users")
    return users

def create_balanced_test_data():
    """Create balanced test data with good distribution across tournaments"""
    users = reset_test_data()
    if not users:
        return
    
    tournaments = Tournament.query.all()
    if not tournaments:
        logger.error("No tournaments found in the database.")
        return
    
    # Create a balanced distribution of users across tournaments
    # Take the top 10 tournaments and ensure they have multiple attendees
    popular_tournaments = random.sample(tournaments, min(10, len(tournaments)))
    remaining_tournaments = [t for t in tournaments if t not in popular_tournaments]
    
    # Track metrics
    total_interactions = 0
    attending_count = 0
    maybe_count = 0
    lanyard_orders = 0
    
    # For each user, create 5-8 tournament selections
    for user in users:
        logger.info(f"Creating tournament selections for {user.email}")
        user_tournaments = []
        
        # Add 2-4 popular tournaments to ensure overlap
        user_popular_count = random.randint(2, min(4, len(popular_tournaments)))
        user_tournaments.extend(random.sample(popular_tournaments, user_popular_count))
        
        # Add additional tournaments to reach 5-8 total
        target_count = random.randint(5, 8)
        if len(user_tournaments) < target_count and remaining_tournaments:
            additional_needed = target_count - len(user_tournaments)
            additional_count = min(additional_needed, len(remaining_tournaments))
            user_tournaments.extend(random.sample(remaining_tournaments, additional_count))
        
        # Create UserTournament records
        for tournament in user_tournaments:
            # 80% attending, 20% maybe
            is_attending = random.random() < 0.8
            attendance_type = "attending" if is_attending else "maybe"
            
            if is_attending:
                attending_count += 1
            else:
                maybe_count += 1
                
            # Create the tournament record
            user_tournament = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                attendance_type=attendance_type,
                attending=is_attending,
                wants_to_meet=random.random() < 0.9  # 90% want to meet
            )
            db.session.add(user_tournament)
            db.session.flush()  # Get ID without committing
            
            total_interactions += 1
            
            # Add session selections for attending users
            if is_attending:
                session_labels = []
                
                # Get session days from tournament data if available
                session_days_count = 5  # Default if no data available
                
                if tournament.sessions and len(tournament.sessions) > 0:
                    session_days_count = min(len(tournament.sessions), 14)  # Cap at 14 days
                
                # Select 1-3 random days
                num_days = random.randint(1, min(3, session_days_count))
                selected_days = random.sample(range(1, session_days_count + 1), num_days)
                
                for day in selected_days:
                    # Randomly choose session type (Day, Night, or both)
                    session_types = ["Day", "Night"]
                    selected_types = random.sample(session_types, random.randint(1, 2))
                    
                    for session_type in selected_types:
                        session_labels.append(f"Day {day} - {session_type}")
                
                # Join all session labels with commas
                if session_labels:
                    user_tournament.session_label = ", ".join(session_labels)
                    logger.info(f"Added {len(session_labels)} sessions for {user.email} at {tournament.name}")
        
        # Randomly create lanyard orders for users with sufficient attendance
        eligible_for_lanyard = UserTournament.query.filter_by(
            user_id=user.id, 
            attending=True
        ).filter(UserTournament.session_label.isnot(None)).first() is not None
        
        if eligible_for_lanyard and random.random() < 0.7:  # 70% of eligible users order lanyards
            user.lanyard_ordered = True
            
            # Create or update shipping address
            existing_address = ShippingAddress.query.filter_by(user_id=user.id).first()
            if not existing_address:
                address = ShippingAddress(
                    user_id=user.id,
                    name=user.get_full_name(),
                    address1=f"{random.randint(100, 9999)} Main St",
                    city=random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
                    state=random.choice(["NY", "CA", "IL", "TX", "AZ"]),
                    zip_code=f"{random.randint(10000, 99999)}",
                    country="United States"
                )
                db.session.add(address)
                lanyard_orders += 1
                logger.info(f"Created lanyard order for {user.email}")
    
    db.session.commit()
    
    logger.info(f"Created balanced test data:")
    logger.info(f"- Total users: {len(users)}")
    logger.info(f"- Total interactions: {total_interactions}")
    logger.info(f"- Attending records: {attending_count}")
    logger.info(f"- Maybe attending records: {maybe_count}")
    logger.info(f"- Lanyard orders: {lanyard_orders}")

if __name__ == "__main__":
    with app.app_context():
        logger.info("Starting QA test data reset and generation")
        create_balanced_test_data()
        logger.info("QA test data generation complete")