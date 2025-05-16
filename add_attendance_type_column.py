"""
Database Migration to add 'attendance_type' column to user_tournament table

This script adds the 'attendance_type' column to the user_tournament table,
ensuring we can properly track whether a user selected 'attending' or 'maybe'.
"""

import sys
import os

from app import app, db

def add_attendance_type_column():
    """Add the attendance_type column to the user_tournament table if it doesn't exist"""
    # Check if the column already exists
    try:
        # Try to execute a query that references the column
        db.session.execute("SELECT attendance_type FROM user_tournament LIMIT 1")
        print("Column 'attendance_type' already exists in user_tournament table.")
        return False
    except Exception as e:
        # Column doesn't exist or other error
        if "column user_tournament.attendance_type does not exist" in str(e):
            # Add the column
            db.session.execute("ALTER TABLE user_tournament ADD COLUMN attendance_type VARCHAR(20) DEFAULT 'attending'")
            db.session.commit()
            print("Added 'attendance_type' column to user_tournament table.")
            
            # Initialize existing records based on their session_label value
            print("Initializing attendance_type values for existing records...")
            db.session.execute("""
                UPDATE user_tournament 
                SET attendance_type = 'maybe' 
                WHERE attending = TRUE AND (session_label IS NULL OR session_label = '')
            """)
            db.session.execute("""
                UPDATE user_tournament 
                SET attendance_type = 'attending' 
                WHERE attending = TRUE AND session_label IS NOT NULL AND session_label != ''
            """)
            db.session.commit()
            print("Successfully initialized attendance_type values.")
            return True
        else:
            # Some other error occurred
            print(f"Error checking for column: {e}")
            return False

if __name__ == "__main__":
    with app.app_context():
        add_attendance_type_column()