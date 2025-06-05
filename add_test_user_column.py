"""
Database Migration to add 'test_user' column to users table

This script adds the 'test_user' column to the users table,
enabling identification of test accounts for data management.
"""
import logging
from app import app, db
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_test_user_column():
    """Add the test_user column to the users table if it doesn't exist"""
    try:
        with app.app_context():
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='test_user'
            """))
            
            if result.fetchone():
                logger.info("test_user column already exists")
                return True
            
            # Add the column
            db.session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN test_user BOOLEAN DEFAULT FALSE
            """))
            
            db.session.commit()
            logger.info("Successfully added test_user column to users table")
            return True
            
    except Exception as e:
        logger.error(f"Error adding test_user column: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    success = add_test_user_column()
    if success:
        print("test_user column added successfully")
    else:
        print("Failed to add test_user column")