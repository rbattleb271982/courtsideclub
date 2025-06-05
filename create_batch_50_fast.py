"""
Create 50 test users efficiently with minimal complexity
"""
import random
from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash

def create_50_users_fast():
    with app.app_context():
        tournaments = Tournament.query.all()
        tournament_ids = [t.id for t in tournaments[:10]]  # Use first 10 tournaments for speed
        
        created = 0
        
        try:
            for i in range(50):
                user_num = random.randint(10000, 99999)
                
                user = User(
                    email=f"user{user_num}@test.com",
                    password_hash=generate_password_hash("TestPass123"),
                    first_name=f"First{user_num}",
                    last_name=f"Last{user_num}",
                    name=f"First{user_num} Last{user_num}",
                    notifications=True,
                    welcome_seen=True,
                    test_user=True
                )
                
                db.session.add(user)
                db.session.flush()
                
                # Add 3 tournaments per user
                selected_tournaments = random.sample(tournament_ids, 3)
                has_lanyard = False
                
                for tournament_id in selected_tournaments:
                    attending = random.choice([True, False])
                    session_label = None
                    
                    if attending:
                        session_label = random.choice(["Day Session", "Night Session", "Day Session,Night Session"])
                        has_lanyard = True
                    
                    user_tournament = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament_id,
                        attending=attending,
                        open_to_meet=random.choice([True, False]),
                        wants_to_meet=attending and random.choice([True, False]),
                        session_label=session_label
                    )
                    
                    db.session.add(user_tournament)
                
                # Add shipping if has lanyard
                if has_lanyard:
                    user.lanyard_ordered = True
                    
                    address = ShippingAddress(
                        user_id=user.id,
                        name=f"First{user_num} Last{user_num}",
                        address1=f"{random.randint(100, 999)} Main St",
                        city="Test City",
                        state="NY",
                        zip_code=f"{random.randint(10000, 99999)}",
                        country="USA"
                    )
                    
                    db.session.add(address)
                
                created += 1
            
            db.session.commit()
            print(f"Successfully created {created} users")
            return True
            
        except Exception as e:
            print(f"Error: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = create_50_users_fast()
    if success:
        with app.app_context():
            total = User.query.filter_by(test_user=True).count()
            print(f"Total test users: {total}")
    else:
        print("Failed to create users")