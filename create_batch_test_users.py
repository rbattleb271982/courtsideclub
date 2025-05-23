"""
Create test users in batches to avoid timeouts
Run this multiple times to reach 500 users total
"""

import random
import sys
from werkzeug.security import generate_password_hash
from models import db, User, Tournament, UserTournament, UserWishlistTournament
from app import app

# Name lists for realistic user generation
first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Cameron", "Drew", "Quinn", "Blake", "James", "Michael", "David", "John", "Robert", "William", "Christopher", "Joseph", "Daniel", "Matthew", "Anthony", "Mark", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Emma", "Olivia", "Sophia", "Isabella", "Charlotte", "Amelia", "Evelyn", "Abigail"]

last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"]

def create_batch_users(batch_size=50):
    """Create a batch of test users"""
    
    with app.app_context():
        # Get current user count
        current_count = User.query.filter(User.email.like('test%@example.com')).count()
        print(f"Current test users: {current_count}")
        
        if current_count >= 750:
            print("Already have 750+ test users!")
            return current_count
        
        # Get tournaments
        tournaments = Tournament.query.all()
        if not tournaments:
            print("No tournaments found!")
            return current_count
            
        print(f"Creating batch of {batch_size} users...")
        
        session_options = [
            "Day 1 - Day, Day 2 - Day",
            "Day 1 - Night, Day 2 - Night", 
            "Day 1 - Day, Day 1 - Night",
            "Day 2 - Day, Day 3 - Day",
            "Day 1 - Day, Day 2 - Day, Day 3 - Day",
            "Day 1 - Night, Day 2 - Night, Day 3 - Night"
        ]
        
        locations = ["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Miami, FL", "Boston, MA", "Seattle, WA", "Denver, CO"]
        
        created = 0
        
        for i in range(batch_size):
            try:
                user_num = current_count + i + 1
                if user_num > 750:
                    break
                    
                # Create unique user
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                email = f"test{user_num:03d}@example.com"
                
                # Check if user already exists
                if User.query.filter_by(email=email).first():
                    continue
                
                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    name=f"{first_name} {last_name}",
                    password_hash=generate_password_hash("testpass123"),
                    notifications=random.choice([True, False]),
                    location=random.choice(locations),
                    lanyard_ordered=random.random() < 0.3
                )
                
                db.session.add(user)
                db.session.flush()
                
                # Add 2-4 attended tournaments
                num_tournaments = random.randint(2, 4)
                selected_tournaments = random.sample(tournaments, min(num_tournaments, len(tournaments)))
                
                for tournament in selected_tournaments:
                    session_label = random.choice(session_options)
                    open_to_meet = random.random() < 0.6  # 60%
                    wants_to_meet = random.random() < 0.3  # 30%
                    
                    user_tournament = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        attending=True,
                        session_label=session_label,
                        open_to_meet=open_to_meet,
                        wants_to_meet=wants_to_meet,
                        attendance_type='attending'
                    )
                    db.session.add(user_tournament)
                
                # Add 1-3 wishlist tournaments (different from attended)
                attended_ids = {t.id for t in selected_tournaments}
                available_for_wishlist = [t for t in tournaments if t.id not in attended_ids]
                
                if available_for_wishlist:
                    num_wishlist = random.randint(1, min(3, len(available_for_wishlist)))
                    wishlist_tournaments = random.sample(available_for_wishlist, num_wishlist)
                    
                    for tournament in wishlist_tournaments:
                        wishlist = UserWishlistTournament(
                            user_id=user.id,
                            tournament_id=tournament.id
                        )
                        db.session.add(wishlist)
                
                created += 1
                
            except Exception as e:
                print(f"Error creating user {user_num}: {e}")
                db.session.rollback()
                continue
        
        # Commit the batch
        db.session.commit()
        new_total = current_count + created
        print(f"✅ Created {created} users. Total test users: {new_total}")
        
        return new_total

if __name__ == "__main__":
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    total = create_batch_users(batch_size)
    
    if total < 500:
        remaining = 500 - total
        print(f"\nTo reach 500 users, run: python create_batch_test_users.py {min(remaining, 50)}")