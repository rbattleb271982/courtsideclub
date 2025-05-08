"""
Script to set a user as admin

Usage:
    python set_admin_user.py email@example.com

This will set the is_admin flag to True for the specified user.
"""
import sys
import logging
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Create a minimal Flask app for the script
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def set_admin(email):
    """
    Set the is_admin flag to True for the user with the given email
    
    Args:
        email: The email address of the user to make admin
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with app.app_context():
            # Get the User model dynamically to avoid import issues
            from models import User
            
            # Find the user by email
            user = User.query.filter_by(email=email).first()
            
            if not user:
                logging.error(f"User with email {email} not found.")
                return False
                
            # Set is_admin to True
            user.is_admin = True
            db.session.commit()
            
            logging.info(f"User {email} is now an admin.")
            return True
    except Exception as e:
        logging.error(f"Error setting admin: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python set_admin_user.py email@example.com")
        sys.exit(1)
        
    email = sys.argv[1]
    success = set_admin(email)
    
    if success:
        print(f"✅ User {email} is now an admin.")
    else:
        print(f"❌ Failed to set {email} as admin. See logs for details.")
        sys.exit(1)