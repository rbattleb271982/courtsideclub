"""
Database Migration to add surface field to Tournament model

This script adds the 'surface' column to the tournaments table,
allowing admins to specify the court surface type for each tournament.
"""
import logging
from app import app, db
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_surface_field():
    """Add the surface column to the tournaments table if it doesn't exist"""
    try:
        with app.app_context():
            connection = db.engine.connect()
            
            # Check if column exists
            inspect_query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='tournaments' AND column_name='surface';
            """
            result = connection.execute(text(inspect_query))
            column_exists = result.scalar() is not None
            
            if not column_exists:
                # Add the column
                add_column_query = "ALTER TABLE tournaments ADD COLUMN surface VARCHAR(50);"
                connection.execute(text(add_column_query))
                connection.commit()
                logger.info("Added surface column to tournaments table")
                return True
            else:
                logger.info("Surface column already exists in tournaments table")
                return True
            
    except Exception as e:
        logger.error(f"Error adding surface column: {str(e)}")
        return False

if __name__ == "__main__":
    success = add_surface_field()
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")