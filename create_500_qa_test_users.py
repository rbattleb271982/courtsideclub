"""
Create 500 QA test users with randomized tournament participation

Each user will have:
- Email: testuser1@example.com through testuser500@example.com
- Password: hashed version of 'testpass123'
- Name: Test 1 through Test 500
- 5-10 random tournaments with attending=True
- 3+ random sessions per tournament
- Random open_to_meet (~50%) and wants_to_meet (~40%)
- ~10% will have lanyard orders with shipping addresses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash
import random
import json

def get_all_tournaments():
    """Get all tournaments from the database"""
    with app.app_context():
        tournaments = Tournament.query.all()
        return tournaments

def get_random_sessions(tournament, num_sessions):
    """Get random sessions from a tournament"""
    if not tournament.sessions:
        return []
    
    # Parse sessions if it's a JSON string
    sessions = tournament.sessions
    if isinstance(sessions, str):
        try:
            sessions = json.loads(sessions)
        except json.JSONDecodeError:
            return []
    
    if not sessions or len(sessions) < num_sessions:
        return sessions
    
    return random.sample(sessions, num_sessions)

def create_shipping_address(user):
    """Create a shipping address for a user"""
    addresses = [
        {"street": "123 Test St", "city": "Testville", "state": "CA", "zip": "90000"},
        {"street": "456 Mock Ave", "city": "Demotown", "state": "NY", "zip": "10001"},
        {"street": "789 Sample Blvd", "city": "Placeholder", "state": "FL", "zip": "33101"},
        {"street": "321 Trial Way", "city": "Benchmark", "state": "TX", "zip": "75001"},
        {"street": "654 Dummy Dr", "city": "Prototype", "state": "WA", "zip": "98001"}
    ]
    
    addr_data = random.choice(addresses)
    
    shipping_address = ShippingAddress(
        user_id=user.id,
        first_name=user.first_name or "Test",
        last_name=user.last_name or "User",
        address_line_1=addr_data["street"],
        city=addr_data["city"],
        state=addr_data["state"],
        postal_code=addr_data["zip"],
        country="US",
        phone="555-0123"
    )
    
    db.session.add(shipping_address)
    return shipping_address

def create_500_qa_test_users():
    """Create 500 QA test users with tournament participation"""
    
    with app.app_context():
        print("Starting creation of 500 QA test users...")
        
        # Get all tournaments
        tournaments = get_all_tournaments()
        if not tournaments:
            print("ERROR: No tournaments found in database!")
            return
        
        print(f"Found {len(tournaments)} tournaments in database")
        
        # Check current user count
        current_users = User.query.filter(User.email.like('testuser%@example.com')).count()
        print(f"Current test users in database: {current_users}")
        
        users_created = 0
        
        try:
            for i in range(1, 501):  # testuser1 through testuser500
                email = f"testuser{i}@example.com"
                
                # Check if user already exists
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    print(f"User {email} already exists, skipping...")
                    continue
                
                # Create user
                user = User(
                    email=email,
                    first_name="Test",
                    last_name=str(i),
                    name=f"Test {i}",
                    password_hash=generate_password_hash('testpass123'),
                    test_user=True,
                    location=random.choice(["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA"])
                )
                
                # 10% chance of lanyard order
                if random.random() < 0.1:
                    user.lanyard_ordered = True
                
                db.session.add(user)
                db.session.flush()  # Get the user ID
                
                # Create shipping address if lanyard ordered
                if user.lanyard_ordered:
                    create_shipping_address(user)
                
                # Select 5-10 random tournaments
                num_tournaments = random.randint(5, 10)
                selected_tournaments = random.sample(tournaments, min(num_tournaments, len(tournaments)))
                
                for tournament in selected_tournaments:
                    # Get 3+ random sessions
                    num_sessions = random.randint(3, min(8, len(tournament.sessions) if tournament.sessions else 3))
                    selected_sessions = get_random_sessions(tournament, num_sessions)
                    
                    # Create UserTournament entry
                    user_tournament = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        attending=True,
                        session_label=",".join(selected_sessions) if selected_sessions else "",
                        open_to_meet=random.random() < 0.5,  # 50% chance
                        wants_to_meet=random.random() < 0.4   # 40% chance
                    )
                    
                    db.session.add(user_tournament)
                
                users_created += 1
                
                # Commit in batches of 25 to avoid timeouts
                if users_created % 25 == 0:
                    db.session.commit()
                    print(f"Created {users_created} users so far...")
            
            # Final commit
            db.session.commit()
            print(f"Successfully created {users_created} QA test users!")
            
            # Verify results
            total_test_users = User.query.filter(User.email.like('testuser%@example.com')).count()
            total_registrations = UserTournament.query.join(User).filter(User.email.like('testuser%@example.com')).count()
            total_lanyards = User.query.filter(User.email.like('testuser%@example.com'), User.lanyard_ordered == True).count()
            total_addresses = ShippingAddress.query.join(User).filter(User.email.like('testuser%@example.com')).count()
            
            print(f"\nFinal Results:")
            print(f"Total test users: {total_test_users}")
            print(f"Total tournament registrations: {total_registrations}")
            print(f"Users with lanyard orders: {total_lanyards}")
            print(f"Shipping addresses created: {total_addresses}")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: {e}")
            raise

if __name__ == "__main__":
    create_500_qa_test_users()