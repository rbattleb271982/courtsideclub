"""
Database Migration to add tournament info fields

This script adds the additional fields to the tournaments table:
- about (text description)
- draw_url (link to tournament draw)
- schedule_url (link to tournament schedule)
"""
import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create a minimal Flask app for migration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def add_tournament_fields():
    """Add the about, draw_url, and schedule_url fields to the tournaments table if they don't exist"""
    try:
        with app.app_context():
            # Connect to the database
            connection = db.engine.connect()
            
            # Check if columns already exist
            inspect_query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='tournaments' AND column_name='about';
            """
            result = connection.execute(db.text(inspect_query))
            column_exists = result.scalar() is not None
            
            if not column_exists:
                # Add the columns
                logging.info("Adding tournament info columns...")
                add_columns_query = """
                ALTER TABLE tournaments 
                ADD COLUMN about TEXT,
                ADD COLUMN draw_url VARCHAR(255),
                ADD COLUMN schedule_url VARCHAR(255);
                """
                connection.execute(db.text(add_columns_query))
                connection.commit()
                logging.info("Added tournament info columns successfully!")
            else:
                logging.info("Tournament info columns already exist.")
                
            connection.close()
            return True
    except Exception as e:
        logging.error(f"Error adding tournament info columns: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    add_tournament_fields()