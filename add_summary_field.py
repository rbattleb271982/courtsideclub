"""
Database Migration to add summary field to Tournament model

This script adds the 'summary' column to the tournaments table,
allowing AI-generated editorial summaries for each tournament.
"""

import os
from sqlalchemy import create_engine, text

def add_summary_field():
    """Add the summary column to the tournaments table if it doesn't exist"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as connection:
            # Check if summary column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tournaments' 
                AND column_name = 'summary'
            """))
            
            if result.fetchone():
                print("Summary column already exists in tournaments table")
                return
            
            # Add the summary column
            connection.execute(text("""
                ALTER TABLE tournaments 
                ADD COLUMN summary TEXT
            """))
            
            connection.commit()
            print("Successfully added summary column to tournaments table")
            
    except Exception as e:
        print(f"Error adding summary column: {e}")

if __name__ == "__main__":
    add_summary_field()