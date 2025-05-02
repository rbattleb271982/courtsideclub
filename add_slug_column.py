
import os
import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def add_slug_column():
    """Add the slug column to the tournaments table if it doesn't exist"""
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tournaments' AND column_name = 'slug';
        """)
        
        if cursor.fetchone() is None:
            logger.info("Adding 'slug' column to tournaments table")
            
            # Add the column
            cursor.execute("""
                ALTER TABLE tournaments 
                ADD COLUMN slug VARCHAR(100) UNIQUE;
            """)
            
            # Update existing records to have a slug based on their ID
            cursor.execute("""
                UPDATE tournaments
                SET slug = id;
            """)
            
            # Make the column non-nullable after populating it
            cursor.execute("""
                ALTER TABLE tournaments
                ALTER COLUMN slug SET NOT NULL;
            """)
            
            logger.info("Successfully added 'slug' column and updated existing records")
        else:
            logger.info("Column 'slug' already exists in tournaments table")
            
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error adding 'slug' column: {e}")
        return False

if __name__ == "__main__":
    success = add_slug_column()
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)
