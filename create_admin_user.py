"""
Script to create a new admin user with specified credentials
"""
import logging
import os
import sys
from app import app, db
from models import User
from werkzeug.security import generate_password_hash
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user(email, password, first_name=None, last_name=None):
    """Create a new admin user with the specified credentials"""
    try:
        with app.app_context():
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            
            if existing_user:
                # Update existing user to admin
                existing_user.is_admin = True
                existing_user.password_hash = generate_password_hash(password)
                if first_name:
                    existing_user.first_name = first_name
                if last_name:
                    existing_user.last_name = last_name
                
                db.session.commit()
                logger.info(f"Updated existing user {email} to admin with new password")
            else:
                # Create new admin user
                new_user = User(
                    email=email,
                    password_hash=generate_password_hash(password),
                    first_name=first_name,
                    last_name=last_name,
                    is_admin=True,
                    notifications=True,
                    welcome_seen=True
                )
                
                db.session.add(new_user)
                db.session.commit()
                logger.info(f"Created new admin user: {email}")
            
            return True

    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin_user.py <email> <password> [first_name] [last_name]")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    first_name = sys.argv[3] if len(sys.argv) > 3 else None
    last_name = sys.argv[4] if len(sys.argv) > 4 else None
    
    success = create_admin_user(email, password, first_name, last_name)
    
    if success:
        print(f"Admin user {email} created/updated successfully")
    else:
        print("Failed to create admin user")
        sys.exit(1)