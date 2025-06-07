"""
Create remaining QA test users to reach 500 total
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash
import random
import json

def create_small_batch(batch_size=25):
    """Create a small batch of users"""
    
    with app.app_context():
        tournaments = Tournament.query.all()
        existing_count = User.query.filter(User.email.like('testuser%@example.com')).count()
        start_num = existing_count + 1
        
        users_created = 0
        
        for i in range(start_num, start_num + batch_size):
            if i > 500:  # Don't exceed testuser500
                break
                
            email = f"testuser{i}@example.com"
            
            if User.query.filter_by(email=email).first():
                continue
            
            user = User(
                email=email,
                first_name="Test",
                last_name=str(i),
                name=f"Test {i}",
                password_hash=generate_password_hash('testpass123'),
                test_user=True,
                location=random.choice(["New York, NY", "Los Angeles, CA", "Chicago, IL"])
            )
            
            if random.random() < 0.1:
                user.lanyard_ordered = True
            
            db.session.add(user)
            db.session.flush()
            
            if user.lanyard_ordered:
                address = ShippingAddress(
                    user_id=user.id,
                    name=f"Test {i}",
                    address1="123 Test St",
                    city="Testville",
                    state="CA",
                    zip_code="90000",
                    country="US"
                )
                db.session.add(address)
            
            # Add tournaments
            num_tournaments = random.randint(5, 8)
            selected_tournaments = random.sample(tournaments, min(num_tournaments, len(tournaments)))
            
            for tournament in selected_tournaments:
                sessions = tournament.sessions or []
                if isinstance(sessions, str):
                    try:
                        sessions = json.loads(sessions)
                    except:
                        sessions = []
                
                if sessions:
                    num_sessions = random.randint(3, min(6, len(sessions)))
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
    # Create in small batches of 25
    total_created = 0
    
    for batch in range(15):  # 15 batches of 25 = 375 more users
        try:
            created = create_small_batch(25)
            total_created += created
            print(f"Batch {batch + 1}: Created {created} users. Total new: {total_created}")
            
            if created == 0:
                break
                
        except Exception as e:
            print(f"Error in batch {batch + 1}: {e}")
            break
    
    print(f"Created {total_created} additional users")