"""
Database Migration to add 'welcome_seen' column to users table

This script adds the 'welcome_seen' column to the users table,
ensuring users only see the welcome message once.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def add_welcome_seen_column():
    """Add the welcome_seen column to the users table if it doesn't exist"""
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'welcome_seen';
        """)
        
        if cursor.fetchone() is None:
            logger.info("Adding 'welcome_seen' column to users table")
            
            # Add the column
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN welcome_seen BOOLEAN DEFAULT FALSE;
            """)
            
            logger.info("Successfully added 'welcome_seen' column")
        else:
            logger.info("Column 'welcome_seen' already exists in users table")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error adding 'welcome_seen' column: {e}")
        return False
        
    return True

if __name__ == "__main__":
    logger.info("Starting migration to add 'welcome_seen' column to users table")
    success = add_welcome_seen_column()
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)