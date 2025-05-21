"""
Database Migration to add commentary field to Tournament model

This script adds the 'commentary' column to the tournaments table,
allowing admins to add editorial snippets for each event.
"""

import logging
from app import db
from sqlalchemy import Column, Text

def add_commentary_field():
    """Add the commentary column to the tournaments table if it doesn't exist"""
    try:
        # Check if the column already exists
        from models import Tournament
        tournament = Tournament.query.first()
        
        # If this doesn't raise an error, the column exists
        try:
            _ = tournament.commentary
            logging.info("Commentary column already exists in tournaments table")
            return False
        except (AttributeError, Exception):
            # Column doesn't exist, so add it
            pass
        
        # Add the column
        db.engine.execute('ALTER TABLE tournaments ADD COLUMN commentary TEXT')
        
        logging.info("Successfully added commentary column to tournaments table")
        return True
    except Exception as e:
        logging.error(f"Error adding commentary column: {str(e)}")
        return False

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the migration
    from app import create_app
    app = create_app()
    
    with app.app_context():
        add_commentary_field()
