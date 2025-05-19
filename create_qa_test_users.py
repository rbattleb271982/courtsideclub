"""
Create QA test users for comprehensive testing.
"""
import logging
from app import app, db
from models import User, UserPastTournament, Tournament
from werkzeug.security import generate_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_users():
    """Create test users for QA testing"""
    # Test user template
    test_users = [
        {"email": "qa_test1@example.com", "first_name": "QA", "last_name": "User 1", "password": "test1234"},
        {"email": "qa_test2@example.com", "first_name": "QA", "last_name": "User 2", "password": "test1234"},
        {"email": "qa_test3@example.com", "first_name": "QA", "last_name": "User 3", "password": "test1234"},
        {"email": "qa_test4@example.com", "first_name": "QA", "last_name": "User 4", "password": "test1234"},
        {"email": "qa_test5@example.com", "first_name": "QA", "last_name": "User 5", "password": "test1234"},
        {"email": "qa_test6@example.com", "first_name": "QA", "last_name": "User 6", "password": "test1234"},
    ]
    
    created_count = 0
    already_exists_count = 0
    
    for user_data in test_users:
        email = user_data["email"]
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            logger.info(f"User {email} already exists, skipping creation")
            already_exists_count += 1
            continue
        
        # Create new user
        new_user = User(
            email=email,
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            name=f"{user_data['first_name']} {user_data['last_name']}",
            password_hash=generate_password_hash(user_data["password"])
        )
        
        # Set welcome seen to avoid welcome message
        new_user.welcome_seen = True
        
        db.session.add(new_user)
        db.session.commit()
        logger.info(f"Created test user: {email}")
        created_count += 1
    
    return created_count, already_exists_count

def add_past_tournaments_to_users():
    """
    Add past tournaments to all test users.
    Each user will get 3-6 random past tournaments.
    """
    import random
    
    # Get all test users
    test_users = User.query.filter(User.email.like('%test%@example.com')).all()
    
    # Get all tournaments for past selection
    tournaments = Tournament.query.all()
    
    # Add past tournaments to each user
    for user in test_users:
        logger.info(f"Adding past tournaments for user: {user.email}")
        
        # Randomly select 3-6 tournaments for this user
        num_past_tournaments = random.randint(3, 6)
        selected_tournaments = random.sample(list(tournaments), num_past_tournaments)
        
        # Add each tournament to the user's past tournaments
        for tournament in selected_tournaments:
            # Check if this past tournament is already added
            existing = UserPastTournament.query.filter_by(
                user_id=user.id, 
                tournament_id=tournament.id
            ).first()
            
            if not existing:
                past_tournament = UserPastTournament(
                    user_id=user.id,
                    tournament_id=tournament.id
                )
                db.session.add(past_tournament)
                logger.info(f"Added past tournament {tournament.name} for user {user.email}")
        
    db.session.commit()
    logger.info("Completed adding past tournaments to test users")

if __name__ == "__main__":
    with app.app_context():
        created, existing = create_test_users()
        logger.info(f"Created {created} new test users, {existing} already existed")
        
        add_past_tournaments_to_users()
        logger.info("Process completed successfully")