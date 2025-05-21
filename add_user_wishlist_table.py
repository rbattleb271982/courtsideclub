"""
Database Migration to add UserWishlistTournament table

This script adds the UserWishlistTournament table to the database, 
allowing users to create a bucket list of tournaments they'd like to attend someday.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.exc import SQLAlchemyError

# Get database URL from environment
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("Error: DATABASE_URL environment variable not set.")
    sys.exit(1)

def add_user_wishlist_table():
    """
    Create the user_wishlist_tournaments table if it doesn't exist.
    This enables users to maintain a bucket list of tournaments they'd like to attend.
    """
    try:
        # Create connection to database
        engine = create_engine(db_url)
        conn = engine.connect()
        
        # Check if the user_wishlist_tournaments table already exists
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        if 'user_wishlist_tournaments' not in metadata.tables:
            # Create the user_wishlist_tournaments table
            query = text("""
            CREATE TABLE user_wishlist_tournaments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                tournament_id VARCHAR(50) NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, tournament_id)
            );
            """)
            conn.execute(query)
            conn.commit()
            print("Created user_wishlist_tournaments table successfully.")
        else:
            print("user_wishlist_tournaments table already exists. No changes made.")

    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()
            
if __name__ == "__main__":
    add_user_wishlist_table()