
"""
Database Migration to add 'attending' column to user_tournament table

This script adds the 'attending' column to the user_tournament table,
ensuring users can be marked as attending a tournament once they've saved their sessions.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def add_attending_column():
    """Add the attending column to the user_tournament table if it doesn't exist"""
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_tournament' AND column_name = 'attending';
        """)
        
        if cursor.fetchone() is None:
            logger.info("Adding 'attending' column to user_tournament table")
            
            # Add the column
            cursor.execute("""
                ALTER TABLE user_tournament 
                ADD COLUMN attending BOOLEAN DEFAULT FALSE;
            """)
            
            # Update existing records: mark as attending if they have sessions
            cursor.execute("""
                UPDATE user_tournament
                SET attending = TRUE
                WHERE sessions::text <> '[]';
            """)
            
            logger.info("Successfully added 'attending' column and updated existing records")
        else:
            logger.info("Column 'attending' already exists in user_tournament table")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error adding 'attending' column: {e}")
        return False
        
    return True

if __name__ == "__main__":
    logger.info("Starting migration to add 'attending' column to user_tournament table")
    success = add_attending_column()
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)
