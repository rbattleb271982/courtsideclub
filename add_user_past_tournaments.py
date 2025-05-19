"""
Database Migration to add UserPastTournament table

This script adds the UserPastTournament table to the database, 
allowing users to save tournaments they've previously attended.
"""

from models import db, UserPastTournament
from app import app
import logging

def add_user_past_tournaments_table():
    """
    Create the user_past_tournament table if it doesn't exist.
    This is a proper model-based approach for handling past tournaments.
    """
    try:
        with app.app_context():
            # Create the table
            db.create_all()
            logging.info("UserPastTournament table created successfully")
            print("UserPastTournament table created successfully")
    except Exception as e:
        logging.error(f"Error creating UserPastTournament table: {str(e)}")
        print(f"Error creating UserPastTournament table: {str(e)}")

if __name__ == "__main__":
    add_user_past_tournaments_table()