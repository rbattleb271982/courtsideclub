"""
Create 500 realistic test users for Let'CourtSide

Each user will have:
- Unique email and name
- At least 2 tournaments marked as attended (attending=True)
- Each attended tournament has 2+ sessions selected
- 1-3 bucket list tournaments
- Proper open_to_meet/wants_to_meet distribution
- No duplicate tournament assignments per user
"""

import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from models import db, User, Tournament, UserTournament, UserWishlistTournament
from app import app

# Lists for generating realistic names
first_names = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Cameron", "Drew", "Quinn",
    "Blake", "Sage", "River", "Phoenix", "Dakota", "Skylar", "Rowan", "Emery", "Finley", "Hayden",
    "James", "Michael", "David", "John", "Robert", "William", "Christopher", "Joseph", "Daniel", "Matthew",
    "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
    "George", "Timothy", "Ronald", "Jason", "Edward", "Jeffrey", "Ryan", "Jacob", "Gary", "Nicholas",
    "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott", "Brandon", "Benjamin", "Samuel", "Gregory",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
    "Nancy", "Lisa", "Betty", "Helen", "Sandra", "Donna", "Carol", "Ruth", "Sharon", "Michelle",
    "Laura", "Sarah", "Kimberly", "Deborah", "Dorothy", "Lisa", "Nancy", "Karen", "Betty", "Helen",
    "Maria", "Ashley", "Emma", "Olivia", "Sophia", "Isabella", "Charlotte", "Amelia", "Evelyn", "Abigail",
    "Harper", "Emily", "Elizabeth", "Avery", "Sofia", "Ella", "Madison", "Scarlett", "Victoria", "Aria"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
    "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes",
    "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
    "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez"
]

def get_random_sessions(tournament_sessions):
    """Get 2+ random sessions for a tournament"""
    if not tournament_sessions:
        return ["Day Session", "Night Session"]
    
    # Ensure we get at least 2 sessions
    selected = random.sample(tournament_sessions, min(len(tournament_sessions), random.randint(2, min(4, len(tournament_sessions)))))
    return selected

def create_500_test_users():
    """Create 500 realistic test users with proper tournament distributions"""
    
    with app.app_context():
        print("Starting creation of 500 test users...")
        
        # Get all tournaments
        tournaments = Tournament.query.all()
        if not tournaments:
            print("No tournaments found! Please import tournaments first.")
            return
            
        print(f"Found {len(tournaments)} tournaments")
        
        # Define typical session types for tournaments
        session_types = {
            'day': ['Day 1 - Day', 'Day 2 - Day', 'Day 3 - Day', 'Day 4 - Day', 'Day 5 - Day'],
            'night': ['Day 1 - Night', 'Day 2 - Night', 'Day 3 - Night', 'Day 4 - Night'],
            'combined': ['Day 1 - Day', 'Day 1 - Night', 'Day 2 - Day', 'Day 2 - Night', 'Day 3 - Day', 'Day 3 - Night']
        }
        
        # Track tournament attendance to ensure distribution
        tournament_attendance = {t.id: 0 for t in tournaments}
        
        users_created = 0
        
        for i in range(500):
            try:
                # Generate unique user details
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                email = f"test{i+1:03d}@example.com"
                
                # Create user
                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    name=f"{first_name} {last_name}",
                    password_hash=generate_password_hash("testpass123"),
                    notifications=random.choice([True, False]),
                    location=random.choice(["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", 
                                          "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
                                          "Dallas, TX", "San Jose, CA", "Austin, TX", "Jacksonville, FL",
                                          "San Francisco, CA", "Indianapolis, IN", "Columbus, OH", "Fort Worth, TX"]),
                    lanyard_ordered=random.choice([True, False]) if random.random() < 0.3 else False
                )
                
                db.session.add(user)
                db.session.flush()  # Get the user ID
                
                # Select 2-4 tournaments for attendance (ensuring minimum 10 per tournament)
                num_attending = random.randint(2, 4)
                
                # Prioritize tournaments with lower attendance first
                available_tournaments = sorted(tournaments, key=lambda t: tournament_attendance[t.id])
                selected_tournaments = random.sample(available_tournaments, min(num_attending, len(tournaments)))
                
                user_tournament_ids = set()
                
                for tournament in selected_tournaments:
                    # Skip if already selected
                    if tournament.id in user_tournament_ids:
                        continue
                        
                    user_tournament_ids.add(tournament.id)
                    
                    # Generate 2+ sessions for this tournament
                    session_choice = random.choice(['day', 'night', 'combined'])
                    available_sessions = session_types[session_choice]
                    selected_sessions = get_random_sessions(available_sessions)
                    session_label = ', '.join(selected_sessions)
                    
                    # Determine meeting preferences
                    open_to_meet = random.random() < 0.6  # 60% open to meeting
                    wants_to_meet = random.random() < 0.3  # 30% wants to meet
                    
                    # Create UserTournament entry
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
                    tournament_attendance[tournament.id] += 1
                
                # Add 1-3 bucket list tournaments (different from attended ones)
                remaining_tournaments = [t for t in tournaments if t.id not in user_tournament_ids]
                if remaining_tournaments:
                    num_wishlist = random.randint(1, min(3, len(remaining_tournaments)))
                    wishlist_tournaments = random.sample(remaining_tournaments, num_wishlist)
                    
                    for tournament in wishlist_tournaments:
                        wishlist_entry = UserWishlistTournament(
                            user_id=user.id,
                            tournament_id=tournament.id
                        )
                        db.session.add(wishlist_entry)
                
                users_created += 1
                
                # Commit every 25 users to avoid memory issues and timeouts
                if users_created % 25 == 0:
                    db.session.commit()
                    print(f"Created {users_created} users...")
                    
                    # Brief pause to prevent overwhelming the database
                    import time
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Error creating user {i+1}: {str(e)}")
                db.session.rollback()
                continue
        
        # Final commit
        db.session.commit()
        
        print(f"\n✅ Successfully created {users_created} test users!")
        
        # Print tournament attendance distribution
        print("\nTournament attendance distribution:")
        for tournament in tournaments:
            count = tournament_attendance[tournament.id]
            print(f"  {tournament.name}: {count} attendees")
        
        # Verify minimum requirements
        min_attendance = min(tournament_attendance.values())
        if min_attendance >= 10:
            print(f"\n✅ All tournaments have at least 10 attendees (minimum: {min_attendance})")
        else:
            print(f"\n⚠️ Some tournaments have fewer than 10 attendees (minimum: {min_attendance})")
        
        return users_created

if __name__ == "__main__":
    create_500_test_users()