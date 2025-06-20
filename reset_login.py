#!/usr/bin/env python3
"""
Quick script to reset login credentials for Let'CourtSide
This will help you get back into your account if you're locked out
"""

import os
from werkzeug.security import generate_password_hash
from app import app, db
from models import User

def reset_user_login():
    with app.app_context():
        print("=== Let'CourtSide Login Reset ===")
        
        # Show existing users
        users = User.query.all()
        print(f"\nFound {len(users)} users in the database:")
        for i, user in enumerate(users, 1):
            print(f"{i}. {user.email} - {user.first_name or 'No name'} {user.last_name or ''}")
        
        if not users:
            print("No users found! Let's create a new admin account.")
            email = input("Enter your email: ").strip()
            password = input("Enter a new password: ").strip()
            
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                first_name="Admin",
                last_name="User"
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ Created new account for {email}")
            return
        
        # Reset existing user password
        choice = input(f"\nWhich user would you like to reset? (1-{len(users)}): ").strip()
        
        try:
            user_index = int(choice) - 1
            if 0 <= user_index < len(users):
                user = users[user_index]
                new_password = input(f"Enter new password for {user.email}: ").strip()
                
                if new_password:
                    user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    print(f"✅ Password reset for {user.email}")
                    print(f"You can now login with:")
                    print(f"Email: {user.email}")
                    print(f"Password: {new_password}")
                else:
                    print("❌ Password cannot be empty")
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Please enter a valid number")

if __name__ == "__main__":
    reset_user_login()