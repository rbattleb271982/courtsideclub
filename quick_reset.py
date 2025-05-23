#!/usr/bin/env python3
"""
Quick password reset for richardtest@gmail.com
"""

from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def quick_reset():
    with app.app_context():
        # Reset richardtest@gmail.com with password 'password123'
        user = User.query.filter_by(email='richardtest@gmail.com').first()
        
        if user:
            user.password_hash = generate_password_hash('password123')
            db.session.commit()
            print("✅ Password reset successful!")
            print("Email: richardtest@gmail.com")
            print("Password: password123")
        else:
            print("❌ User not found")

if __name__ == "__main__":
    quick_reset()