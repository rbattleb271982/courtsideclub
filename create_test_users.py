from app import app, db
from models import User
from werkzeug.security import generate_password_hash

# Create test users
with app.app_context():
    # User 1
    u1 = User(
        email='testuser1@example.com',
        name='Test User 1',
        first_name='Test',
        last_name='User 1',
        password_hash=generate_password_hash('password123')
    )
    db.session.add(u1)
    
    # User 2
    u2 = User(
        email='testuser2@example.com',
        name='Test User 2',
        first_name='Test',
        last_name='User 2',
        password_hash=generate_password_hash('password123')
    )
    db.session.add(u2)
    
    # Commit to database
    db.session.commit()
    
    print(f'Created test users with IDs: {u1.id}, {u2.id}')
