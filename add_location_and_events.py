"""
Database Migration to add location field to users table and create events table

This script adds the 'location' column to the users table and creates the
events table for tracking user actions.
"""
import os
import logging
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, inspect
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run():
    """Add location column to users table and create events table if they don't exist"""
    # Connect to the database
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logging.error("DATABASE_URL environment variable not set.")
        return
    
    engine = create_engine(db_url)
    metadata = MetaData()
    inspector = inspect(engine)
    
    # Check if location column exists in users table
    location_exists = False
    for column in inspector.get_columns('users'):
        if column['name'] == 'location':
            location_exists = True
            break
    
    # Check if events table exists
    events_table_exists = 'events' in inspector.get_table_names()
    
    if location_exists and events_table_exists:
        logging.info("Location column and events table already exist. No changes needed.")
        return
    
    connection = engine.connect()
    transaction = connection.begin()
    
    try:
        if not location_exists:
            logging.info("Adding location column to users table...")
            connection.execute(sa.text('ALTER TABLE users ADD COLUMN location VARCHAR(100)'))
        
        if not events_table_exists:
            logging.info("Creating events table...")
            connection.execute(sa.text('''
            CREATE TABLE events (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_data TEXT DEFAULT '{}'
            )
            '''))
        
        transaction.commit()
        logging.info("Migration completed successfully.")
    except Exception as e:
        transaction.rollback()
        logging.error(f"Migration failed: {str(e)}")
    finally:
        connection.close()

if __name__ == "__main__":
    run()