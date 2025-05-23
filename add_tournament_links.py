"""
Database Migration to add external_url and bracket_url fields to Tournament model

This script adds the 'external_url' and 'bracket_url' columns to the tournaments table,
allowing admins to add official tournament websites and bracket links.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Get database URL from environment
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("Error: DATABASE_URL environment variable not set.")
    sys.exit(1)

def add_tournament_link_fields():
    """Add the external_url and bracket_url columns to the tournaments table if they don't exist"""
    try:
        # Create connection to database
        engine = create_engine(db_url)
        conn = engine.connect()
        
        # Check if external_url column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='tournaments' AND column_name='external_url'
        """))
        external_url_exists = result.fetchone() is not None
        
        # Check if bracket_url column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='tournaments' AND column_name='bracket_url'
        """))
        bracket_url_exists = result.fetchone() is not None
        
        # Add external_url column if it doesn't exist
        if not external_url_exists:
            print("Adding external_url column to tournaments table...")
            conn.execute(text("""
                ALTER TABLE tournaments
                ADD COLUMN external_url VARCHAR(255)
            """))
            print("external_url column added successfully.")
        else:
            print("external_url column already exists.")
        
        # Add bracket_url column if it doesn't exist
        if not bracket_url_exists:
            print("Adding bracket_url column to tournaments table...")
            conn.execute(text("""
                ALTER TABLE tournaments
                ADD COLUMN bracket_url VARCHAR(255)
            """))
            print("bracket_url column added successfully.")
        else:
            print("bracket_url column already exists.")
        
        conn.commit()
        conn.close()
        print("Migration completed successfully.")
        return True
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    add_tournament_link_fields()