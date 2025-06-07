"""
Create 500 QA test users efficiently with correct model fields
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash
import random
import json

def create_users_batch(batch_size=50):
    """Create a batch of users efficiently"""
    
    with app.app_context():
        # Get all tournaments
        tournaments = Tournament.query.all()
        if not tournaments:
            print("No tournaments found!")
            return 0
        
        # Find next available user number
        existing_count = User.query.filter(User.email.like('testuser%@example.com')).count()
        start_num = existing_count + 1
        
        users_created = 0
        
        for i in range(start_num, start_num + batch_size):
            email = f"testuser{i}@example.com"
            
            # Skip if exists
            if User.query.filter_by(email=email).first():
                continue
            
            # Create user
            user = User(
                email=email,
                first_name="Test",
                last_name=str(i),
                name=f"Test {i}",
                password_hash=generate_password_hash('testpass123'),
                test_user=True,
                location=random.choice(["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ"])
            )
            
            # 10% chance of lanyard order
            if random.random() < 0.1:
                user.lanyard_ordered = True
            
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Create shipping address if needed
            if user.lanyard_ordered:
                shipping_address = ShippingAddress(
                    user_id=user.id,
                    name=f"Test {i}",
                    address1="123 Test St",
                    city="Testville",
                    state="CA",
                    zip_code="90000",
                    country="US"
                )
                db.session.add(shipping_address)
            
            # Add 5-10 tournaments
            num_tournaments = random.randint(5, 10)
            selected_tournaments = random.sample(tournaments, min(num_tournaments, len(tournaments)))
            
            for tournament in selected_tournaments:
                # Get sessions
                sessions = tournament.sessions or []
                if isinstance(sessions, str):
                    try:
                        sessions = json.loads(sessions)
                    except:
                        sessions = []
                
                # Select 3+ sessions
                if sessions:
                    num_sessions = random.randint(3, min(8, len(sessions)))
                    selected_sessions = random.sample(sessions, min(num_sessions, len(sessions)))
                else:
                    selected_sessions = []
                
                user_tournament = UserTournament(
                    user_id=user.id,
                    tournament_id=tournament.id,
                    attending=True,
                    session_label=",".join(selected_sessions),
                    open_to_meet=random.random() < 0.5,
                    wants_to_meet=random.random() < 0.4
                )
                db.session.add(user_tournament)
            
            users_created += 1
        
        db.session.commit()
        return users_created

if __name__ == "__main__":
    total_created = 0
    target = 500
    
    # Create in batches
    while total_created < target:
        remaining = target - total_created
        batch_size = min(50, remaining)
        
        print(f"Creating batch of {batch_size} users...")
        
        try:
            created = create_users_batch(batch_size)
            total_created += created
            print(f"Created {created} users. Total: {total_created}")
            
            if created == 0:
                print("No more users to create")
                break
                
        except Exception as e:
            print(f"Error: {e}")
            break
    
    print(f"Final total: {total_created} users created")