"""
Create a debug user with known credentials for testing
"""
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_debug_user():
    """Create a debug user with known credentials"""
    with app.app_context():
        # Check if debug user already exists
        existing_user = User.query.filter_by(email='debug@test.com').first()
        if existing_user:
            print(f"Debug user already exists: debug@test.com")
            return
        
        # Create debug user
        debug_user = User(
            name='Debug User',
            email='debug@test.com',
            password_hash=generate_password_hash('password123'),
            first_name='Debug',
            last_name='User',
            location='Test City, USA',
            notifications=True,
            welcome_seen=True
        )
        
        db.session.add(debug_user)
        db.session.commit()
        
        print(f"Created debug user:")
        print(f"Email: debug@test.com")
        print(f"Password: password123")

if __name__ == '__main__':
    create_debug_user()