from app import app, db
from models import User
from werkzeug.security import generate_password_hash
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_create_user():
    """Test user creation directly against the database"""
    with app.app_context():
        try:
            # Create a test user
            email = "test_user@example.com"
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                logger.info(f"Test user already exists with ID: {existing_user.id}")
                logger.info(f"Fields: first_name={existing_user.first_name}, last_name={existing_user.last_name}")
                logger.info(f"Password hash exists: {bool(existing_user.password_hash)}")
                
                # Check the past_tournaments field
                logger.info(f"Past tournaments: {existing_user.past_tournaments}")
                
                # Try to update an existing field
                existing_user.first_name = "UpdatedFirstName"
                db.session.commit()
                logger.info("Successfully updated existing user")
                
                return
                
            # Create new user
            new_user = User(
                email=email,
                first_name="Test",
                last_name="User",
                name="Test User",
                password_hash=generate_password_hash("password123", method='pbkdf2:sha256')
            )
            
            # Set some test data for past_tournaments
            new_user.past_tournaments = ["aus_open", "indian_wells"]
            
            # Add to database
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"Created test user with ID: {new_user.id}")
            logger.info(f"Past tournaments: {new_user.past_tournaments}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating test user: {str(e)}", exc_info=True)

if __name__ == "__main__":
    test_create_user()