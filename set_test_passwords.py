from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Set temporary passwords for both users
    user1 = User.query.filter_by(email='testuser1@example.com').first()
    user2 = User.query.filter_by(email='testuser2@example.com').first()
    
    user1.password_hash = generate_password_hash('test1234')
    user2.password_hash = generate_password_hash('test1234')
    
    db.session.commit()
    
    print(f"Set temporary passwords for:")
    print(f"- Test User 1 (email: testuser1@example.com, password: test1234)")
    print(f"- Test User 2 (email: testuser2@example.com, password: test1234)")
