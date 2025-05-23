"""
Create a small batch of 25 test users first to verify the system works
"""

import random
from werkzeug.security import generate_password_hash
from models import db, User, Tournament, UserTournament, UserWishlistTournament
from app import app

def create_small_batch():
    """Create 25 test users with full specifications"""
    
    with app.app_context():
        print("Creating 25 test users...")
        
        # Get tournaments
        tournaments = Tournament.query.all()
        print(f"Found {len(tournaments)} tournaments")
        
        # Simple name generation
        names = [
            ("Alex", "Smith"), ("Jordan", "Johnson"), ("Taylor", "Brown"), ("Morgan", "Davis"), ("Casey", "Wilson"),
            ("Riley", "Miller"), ("Avery", "Moore"), ("Cameron", "Taylor"), ("Drew", "Anderson"), ("Quinn", "Thomas"),
            ("Blake", "Jackson"), ("Sage", "White"), ("River", "Harris"), ("Phoenix", "Martin"), ("Dakota", "Thompson"),
            ("James", "Garcia"), ("Michael", "Martinez"), ("David", "Robinson"), ("Sarah", "Clark"), ("Emily", "Rodriguez"),
            ("Emma", "Lewis"), ("Olivia", "Lee"), ("Sophia", "Walker"), ("Isabella", "Hall"), ("Charlotte", "Young")
        ]
        
        session_types = [
            "Day 1 - Day, Day 2 - Day",
            "Day 1 - Night, Day 2 - Night", 
            "Day 1 - Day, Day 1 - Night",
            "Day 2 - Day, Day 3 - Day",
            "Day 1 - Day, Day 2 - Day, Day 3 - Day"
        ]
        
        for i in range(25):
            first_name, last_name = names[i]
            email = f"test{i+1:03d}@example.com"
            
            # Create user
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                name=f"{first_name} {last_name}",
                password_hash=generate_password_hash("testpass123"),
                notifications=True,
                location="New York, NY",
                lanyard_ordered=i % 3 == 0  # Every 3rd user
            )
            
            db.session.add(user)
            db.session.flush()
            
            # Add 2-3 attended tournaments
            num_tournaments = 2 + (i % 2)  # 2 or 3 tournaments
            selected_tournaments = random.sample(tournaments, min(num_tournaments, len(tournaments)))
            
            for tournament in selected_tournaments:
                session_label = random.choice(session_types)
                open_to_meet = i % 5 != 0  # 80% open to meet (60%+ requirement)
                wants_to_meet = i % 3 == 0  # 33% wants to meet (30%+ requirement)
                
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
            
            # Add 1-2 wishlist tournaments
            attended_ids = {t.id for t in selected_tournaments}
            available_wishlist = [t for t in tournaments if t.id not in attended_ids]
            
            if available_wishlist:
                num_wishlist = 1 + (i % 2)  # 1 or 2 wishlist items
                wishlist_tournaments = random.sample(available_wishlist, min(num_wishlist, len(available_wishlist)))
                
                for tournament in wishlist_tournaments:
                    wishlist = UserWishlistTournament(
                        user_id=user.id,
                        tournament_id=tournament.id
                    )
                    db.session.add(wishlist)
            
            if (i + 1) % 5 == 0:
                print(f"Created {i + 1} users...")
        
        db.session.commit()
        print("✅ Successfully created 25 test users!")
        
        # Verify data
        test_users = User.query.filter(User.email.like('test%@example.com')).count()
        attending_count = UserTournament.query.filter_by(attending=True).count()
        wishlist_count = UserWishlistTournament.query.count()
        
        print(f"Verification:")
        print(f"  Test users: {test_users}")
        print(f"  Tournament attendances: {attending_count}")
        print(f"  Wishlist items: {wishlist_count}")

if __name__ == "__main__":
    create_small_batch()