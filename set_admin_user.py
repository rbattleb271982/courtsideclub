"""Script to add is_admin column and set admin user"""
import logging
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create minimal Flask app for the script
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def add_admin_column_and_set_admin(email):
    """Add is_admin column if needed and set specified user as admin"""
    try:
        with app.app_context():
            connection = db.engine.connect()

            # Check if column exists
            inspect_query = """
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_admin';
            """
            result = connection.execute(db.text(inspect_query))
            column_exists = result.scalar() is not None

            if not column_exists:
                # Add the column
                add_column_query = "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;"
                connection.execute(db.text(add_column_query))
                logger.info("Added is_admin column")

            # Set admin user
            update_query = "UPDATE users SET is_admin = TRUE WHERE email = :email;"
            connection.execute(db.text(update_query), {"email": email})
            connection.commit()
            logger.info(f"Set {email} as admin")
            return True

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_admin_user.py email@example.com")
        sys.exit(1)
    email = sys.argv[1]
    success = add_admin_column_and_set_admin(email)
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)