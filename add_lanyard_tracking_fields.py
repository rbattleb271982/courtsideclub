"""
Database Migration to add lanyard tracking fields to User model

This script adds the 'lanyard_sent' and 'lanyard_sent_date' columns to the users table,
enabling admin tracking of lanyard fulfillment status.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, Column, Boolean, DateTime, text

def add_lanyard_tracking_fields():
    """Add the lanyard_sent and lanyard_sent_date columns to the users table if they don't exist"""
    
    # Use the DATABASE_URL from environment variables
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set.")
        sys.exit(1)
        
    # Create engine and connect
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Check if lanyard_sent column exists
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'lanyard_sent'"))
        lanyard_sent_exists = bool(result.fetchone())
        
        # Check if lanyard_sent_date column exists
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'lanyard_sent_date'"))
        lanyard_sent_date_exists = bool(result.fetchone())
        
        # Add lanyard_sent column if it doesn't exist
        if not lanyard_sent_exists:
            print("Adding lanyard_sent column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN lanyard_sent BOOLEAN DEFAULT FALSE"))
            print("lanyard_sent column added successfully.")
        else:
            print("lanyard_sent column already exists in users table.")
            
        # Add lanyard_sent_date column if it doesn't exist
        if not lanyard_sent_date_exists:
            print("Adding lanyard_sent_date column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN lanyard_sent_date TIMESTAMP"))
            print("lanyard_sent_date column added successfully.")
        else:
            print("lanyard_sent_date column already exists in users table.")
        
        print("Migration completed successfully.")
        
if __name__ == "__main__":
    add_lanyard_tracking_fields()