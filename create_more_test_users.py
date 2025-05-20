"""
Create 25 more test users with additional variations.
This script creates more diverse test users to further populate the system.
"""
import random
import string
from datetime import datetime, timedelta
from app import app, db
from models import User, Tournament, UserTournament, UserPastTournament, ShippingAddress
from werkzeug.security import generate_password_hash

# Configuration
NUM_USERS = 25
TEST_PASSWORD = "testuser123"  # Common password for all test users

# Sample data for generating realistic users
first_names = ["Tyler", "Madison", "Brandon", "Zoe", "Caleb", "Leah", "Isaac", "Allison", 
               "Zachary", "Natalie", "Justin", "Lauren", "Kevin", "Rachel", "Nicholas", "Morgan",
               "Eric", "Brooke", "Jonathan", "Samantha", "Adam", "Alexis", "Aaron", "Katherine",
               "Kyle", "Kaitlyn", "Thomas", "Jessica", "Austin", "Stephanie"]

last_names = ["Cook", "Morgan", "Bell", "Murphy", "Bailey", "Rivera", "Cooper", "Richardson", 
              "Cox", "Howard", "Ward", "Torres", "Peterson", "Gray", "Ramirez", "James",
              "Watson", "Brooks", "Kelly", "Sanders", "Price", "Bennett", "Wood", "Barnes",
              "Ross", "Henderson", "Coleman", "Jenkins", "Perry", "Powell"]

locations = ["Miami, FL", "Boston, MA", "Portland, OR", "Nashville, TN", 
             "Las Vegas, NV", "Atlanta, GA", "Pittsburgh, PA", "Cleveland, OH", 
             "Cincinnati, OH", "Detroit, MI", "St. Louis, MO", "Tampa, FL",
             "London, UK", "Paris, France", "Madrid, Spain", "Rome, Italy"]

def get_random_email(first_name, last_name):
    """Generate a random email address based on name"""
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "protonmail.com"]
    random_num = random.randint(1, 999)
    email_style = random.choice([
        f"{first_name.lower()}.{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{first_name.lower()}{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{first_name.lower()[0]}{last_name.lower()}{random_num}@{random.choice(domains)}"
    ])
    return email_style

def get_future_tournaments():
    """Get tournaments that start today or in the future"""
    today = datetime.utcnow().date()
    return Tournament.query.filter(Tournament.start_date >= today).order_by(Tournament.start_date).all()

def get_tournaments_within_days(days=9):
    """Get tournaments happening within the specified number of days"""
    today = datetime.utcnow().date()
    cutoff_date = today + timedelta(days=days)
    return Tournament.query.filter(
        Tournament.start_date >= today,
        Tournament.start_date <= cutoff_date
    ).order_by(Tournament.start_date).all()

def get_past_tournaments():
    """Get tournaments that have already ended"""
    today = datetime.utcnow().date()
    return Tournament.query.filter(Tournament.end_date < today).all()

def create_user_with_variations(user_type, upcoming_tournaments, future_tournaments, past_tournaments):
    """Create a user with specific variations based on type"""
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    email = get_random_email(first_name, last_name)
    
    # Create basic user
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        name=f"{first_name} {last_name}",
        password_hash=generate_password_hash(TEST_PASSWORD),
        location=random.choice(locations) if random.random() > 0.3 else None,
        welcome_seen=True,
        is_admin=False,
        date_created=datetime.utcnow() - timedelta(days=random.randint(10, 60))
    )
    
    # Handle different types of users with various permutations
    if user_type == "multiple_upcoming":
        # Users with multiple upcoming tournaments
        user.lanyard_ordered = True
        user.lanyard_sent = False
    elif user_type == "lanyard_ordered_multiple_addresses":
        # Users who ordered lanyard and have entered address multiple times (edit history)
        user.lanyard_ordered = True
        user.lanyard_sent = False 
    elif user_type == "many_tournaments":
        # Users attending many tournaments (4+)
        user.lanyard_ordered = random.choice([True, False])
        user.lanyard_sent = user.lanyard_ordered and random.choice([True, False])
    elif user_type == "day_sessions_only":
        # Users who only attend day sessions
        user.lanyard_ordered = random.choice([True, False]) 
        user.lanyard_sent = user.lanyard_ordered and random.choice([True, False])
    elif user_type == "night_sessions_only":
        # Users who only attend night sessions
        user.lanyard_ordered = random.choice([True, False])
        user.lanyard_sent = user.lanyard_ordered and random.choice([True, False])
    elif user_type == "mixed_sessions":
        # Users with mix of day/night sessions
        user.lanyard_ordered = random.choice([True, False])
        user.lanyard_sent = user.lanyard_ordered and random.choice([True, False])
    else:
        # Random settings for other users
        user.lanyard_ordered = random.random() > 0.5
        user.lanyard_sent = user.lanyard_ordered and random.random() > 0.5
    
    if user.lanyard_sent:
        user.lanyard_sent_date = datetime.utcnow() - timedelta(days=random.randint(1, 20))
    
    db.session.add(user)
    db.session.flush()  # Get the user ID
    
    # Create tournament registrations based on user type
    if user_type == "multiple_upcoming" and upcoming_tournaments:
        # Add all upcoming tournaments
        for tournament in upcoming_tournaments:
            # Generate longer session labels
            session_label = "Day 1 - Day, Day 1 - Night, Day 2 - Day"
            
            ut = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                session_label=session_label,
                attending=True,
                attendance_type='attending',
                open_to_meet=True,
                wants_to_meet=True,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 5))
            )
            db.session.add(ut)
    
    elif user_type == "many_tournaments" and future_tournaments:
        # Add 4-6 tournaments for users who attend many
        num_to_add = min(random.randint(4, 6), len(future_tournaments))
        selected = random.sample(future_tournaments, num_to_add)
        
        for tournament in selected:
            # Random session labels
            day_count = (tournament.end_date - tournament.start_date).days + 1
            sessions = []
            for i in range(min(day_count, random.randint(2, 5))):
                day_num = i + 1
                sessions.append(f"Day {day_num} - {'Day' if random.random() > 0.5 else 'Night'}")
            
            session_label = ", ".join(sessions)
            
            ut = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                session_label=session_label,
                attending=True,
                attendance_type=random.choice(['attending', 'maybe']),
                open_to_meet=random.choice([True, False]),
                wants_to_meet=random.choice([True, False]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(ut)
    
    elif user_type == "day_sessions_only" and future_tournaments:
        # Add 1-3 tournaments with day sessions only
        num_to_add = min(random.randint(1, 3), len(future_tournaments))
        selected = random.sample(future_tournaments, num_to_add)
        
        for tournament in selected:
            # Day sessions only
            day_count = (tournament.end_date - tournament.start_date).days + 1
            sessions = []
            for i in range(min(day_count, random.randint(1, 3))):
                day_num = i + 1
                sessions.append(f"Day {day_num} - Day")
            
            session_label = ", ".join(sessions)
            
            ut = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                session_label=session_label,
                attending=True,
                attendance_type=random.choice(['attending', 'maybe']),
                open_to_meet=random.choice([True, False]),
                wants_to_meet=random.choice([True, False]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(ut)
    
    elif user_type == "night_sessions_only" and future_tournaments:
        # Add 1-3 tournaments with night sessions only
        num_to_add = min(random.randint(1, 3), len(future_tournaments))
        selected = random.sample(future_tournaments, num_to_add)
        
        for tournament in selected:
            # Night sessions only
            day_count = (tournament.end_date - tournament.start_date).days + 1
            sessions = []
            for i in range(min(day_count, random.randint(1, 3))):
                day_num = i + 1
                sessions.append(f"Day {day_num} - Night")
            
            session_label = ", ".join(sessions)
            
            ut = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                session_label=session_label,
                attending=True,
                attendance_type=random.choice(['attending', 'maybe']),
                open_to_meet=random.choice([True, False]),
                wants_to_meet=random.choice([True, False]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(ut)
    
    elif user_type == "mixed_sessions" and future_tournaments:
        # Add 1-3 tournaments with mix of day and night sessions
        num_to_add = min(random.randint(1, 3), len(future_tournaments))
        selected = random.sample(future_tournaments, num_to_add)
        
        for tournament in selected:
            # Mix of day and night sessions
            day_count = (tournament.end_date - tournament.start_date).days + 1
            sessions = []
            for i in range(min(day_count, random.randint(2, 4))):
                day_num = i + 1
                # Add both day and night for some days
                if random.random() > 0.5:
                    sessions.append(f"Day {day_num} - Day")
                    sessions.append(f"Day {day_num} - Night")
                else:
                    sessions.append(f"Day {day_num} - {'Day' if random.random() > 0.5 else 'Night'}")
            
            session_label = ", ".join(sessions)
            
            ut = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                session_label=session_label,
                attending=True,
                attendance_type=random.choice(['attending', 'maybe']),
                open_to_meet=random.choice([True, False]),
                wants_to_meet=random.choice([True, False]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(ut)
    
    else:
        # Add 1-2 random tournaments for other user types
        if future_tournaments:
            num_to_add = min(random.randint(1, 2), len(future_tournaments))
            selected = random.sample(future_tournaments, num_to_add)
            
            for tournament in selected:
                # Simple session selection
                day_count = (tournament.end_date - tournament.start_date).days + 1
                sessions = []
                for i in range(min(day_count, 2)):
                    day_num = i + 1
                    sessions.append(f"Day {day_num} - {'Day' if random.random() > 0.5 else 'Night'}")
                
                session_label = ", ".join(sessions)
                
                ut = UserTournament(
                    user_id=user.id,
                    tournament_id=tournament.id,
                    session_label=session_label,
                    attending=True,
                    attendance_type=random.choice(['attending', 'maybe']),
                    open_to_meet=random.choice([True, False]),
                    wants_to_meet=random.choice([True, False]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                db.session.add(ut)
    
    # Add past tournaments for some users
    if random.random() > 0.5 and past_tournaments:
        num_past = random.randint(1, min(4, len(past_tournaments)))
        selected = random.sample(past_tournaments, num_past)
        
        for tournament in selected:
            past = UserPastTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(past)
    
    # Create shipping address for users with lanyards
    if user.lanyard_ordered:
        # For users with multiple address edits, create a slightly different address
        if user_type == "lanyard_ordered_multiple_addresses":
            # Create two addresses (the system will use the most recent one)
            address1 = ShippingAddress(
                user_id=user.id,
                name=user.get_full_name(),
                address1=f"{random.randint(100, 999)} Old Address St",
                address2=random.choice(["", f"Apt {random.randint(1, 99)}"]),
                city="Old City",
                state="OL",
                zip_code=f"{random.randint(10000, 99999)}",
                country="USA",
                created_at=datetime.utcnow() - timedelta(days=random.randint(10, 20))
            )
            db.session.add(address1)
            
            # Create newer address after a delay
            address2 = ShippingAddress(
                user_id=user.id,
                name=user.get_full_name(),
                address1=f"{random.randint(100, 999)} {random.choice(['New', 'Main', 'Park'])} St",
                address2=random.choice(["", f"Apt {random.randint(1, 99)}"]),
                city=user.location.split(",")[0] if user.location and "," in user.location else "New City",
                state=user.location.split(",")[1].strip() if user.location and "," in user.location else "NC",
                zip_code=f"{random.randint(10000, 99999)}",
                country="USA",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 5))
            )
            db.session.add(address2)
        else:
            # Create a single address for other users
            address = ShippingAddress(
                user_id=user.id,
                name=user.get_full_name(),
                address1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Cedar'])} St",
                address2=random.choice(["", f"Apt {random.randint(1, 999)}"]),
                city=user.location.split(",")[0] if user.location and "," in user.location else "New York",
                state=user.location.split(",")[1].strip() if user.location and "," in user.location else "NY",
                zip_code=f"{random.randint(10000, 99999)}",
                country="USA",
                created_at=datetime.utcnow()
            )
            db.session.add(address)
    
    return user

def create_more_test_users():
    """Create an additional set of users with more variations"""
    print(f"Creating {NUM_USERS} more test users...")
    
    users_created = []
    
    with app.app_context():
        # Get tournament data
        future_tournaments = get_future_tournaments()
        upcoming_tournaments = get_tournaments_within_days(9)
        past_tournaments = get_past_tournaments()
        
        if not future_tournaments:
            print("No future tournaments found. Please import tournaments first.")
            return []
        
        print(f"Found {len(future_tournaments)} future tournaments")
        print(f"Found {len(upcoming_tournaments)} upcoming tournaments (next 9 days)")
        print(f"Found {len(past_tournaments)} past tournaments")
        
        # Define user types to create
        user_types = [
            "multiple_upcoming",
            "lanyard_ordered_multiple_addresses",
            "many_tournaments",
            "day_sessions_only",
            "night_sessions_only",
            "mixed_sessions",
            "regular"
        ]
        
        # Create users based on types
        for i in range(NUM_USERS):
            # Cycle through user types, but make sure we have a good distribution
            if i < len(user_types):
                user_type = user_types[i]
            else:
                user_type = random.choice(user_types)
                
            print(f"Creating user {i+1}/{NUM_USERS} of type: {user_type}")
            
            try:
                user = create_user_with_variations(
                    user_type,
                    upcoming_tournaments,
                    future_tournaments,
                    past_tournaments
                )
                
                users_created.append((user.email, TEST_PASSWORD))
                
            except Exception as e:
                print(f"Error creating user {i+1}: {str(e)}")
                db.session.rollback()
                continue
        
        # Commit changes
        try:
            db.session.commit()
            print(f"Successfully created {len(users_created)} additional test users")
            
            # Print stats
            print("\nUpdated Test User Statistics:")
            print(f"Total users: {User.query.count()}")
            print(f"Users with lanyards ordered: {User.query.filter_by(lanyard_ordered=True).count()}")
            print(f"Users with lanyards sent: {User.query.filter_by(lanyard_sent=True).count()}")
            print(f"Total tournament registrations: {UserTournament.query.count()}")
            print(f"Total past tournament entries: {UserPastTournament.query.count()}")
            print(f"Total shipping addresses: {ShippingAddress.query.count()}")
            
            # Print users with unsent lanyards attending upcoming tournaments
            if upcoming_tournaments:
                urgent_count = 0
                for tournament in upcoming_tournaments:
                    for reg in UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).all():
                        user = User.query.filter_by(id=reg.user_id).first()
                        if user and user.lanyard_ordered and not user.lanyard_sent:
                            urgent_count += 1
                
                print(f"Users qualifying for urgent lanyard alert: {urgent_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {str(e)}")
            return []
        
        return users_created

if __name__ == "__main__":
    create_more_test_users()