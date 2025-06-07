"""
Create 500 QA test users in efficient batches
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash
import random
import json

def create_batch_users(start_num, end_num):
    """Create users from start_num to end_num"""
    
    with app.app_context():
        # Get all tournaments once
        tournaments = Tournament.query.all()
        if not tournaments:
            print("ERROR: No tournaments found!")
            return 0
        
        users_created = 0
        
        for i in range(start_num, end_num + 1):
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
            db.session.flush()
            
            # Create shipping address if needed
            if user.lanyard_ordered:
                shipping_address = ShippingAddress(
                    user_id=user.id,
                    first_name="Test",
                    last_name=str(i),
                    address_line_1="123 Test St",
                    city="Testville",
                    state="CA",
                    postal_code="90000",
                    country="US",
                    phone="555-0123"
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
                num_sessions = random.randint(3, min(8, len(sessions)) if sessions else 3)
                selected_sessions = random.sample(sessions, min(num_sessions, len(sessions))) if sessions else []
                
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
    # Create in batches of 50
    total_created = 0
    
    for batch_start in range(1, 501, 50):
        batch_end = min(batch_start + 49, 500)
        print(f"Creating users {batch_start} to {batch_end}...")
        
        try:
            created = create_batch_users(batch_start, batch_end)
            total_created += created
            print(f"Created {created} users in this batch. Total: {total_created}")
            
        except Exception as e:
            print(f"Error in batch {batch_start}-{batch_end}: {e}")
            continue
    
    print(f"Final total created: {total_created}")