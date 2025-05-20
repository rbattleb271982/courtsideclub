"""
Create a smaller set of test users with diverse permutations.
This version is simplified to run more reliably.
"""
import random
import string
from datetime import datetime, timedelta
from app import app, db
from models import User, Tournament, UserTournament, UserPastTournament, ShippingAddress
from werkzeug.security import generate_password_hash

# Configuration - smaller number for initial testing
NUM_USERS = 25
TEST_PASSWORD = "testuser123"  # Common password for all test users

# Sample data for generating realistic users
first_names = ["Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James", 
               "Isabella", "Logan", "Charlotte", "Benjamin", "Amelia", "Mason", "Mia",
               "Ethan", "Harper", "Alexander", "Evelyn", "Jacob", "Abigail", "Michael"]

last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", 
              "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White",
              "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson"]

locations = ["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", 
             "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", 
             "Dallas, TX", "San Jose, CA", "Austin, TX", "Jacksonville, FL"]

def get_random_email(first_name, last_name):
    """Generate a random email address based on name"""
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]
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
    
    # Handle lanyard variations
    if user_type == "urgent_lanyard":
        user.lanyard_ordered = True
        user.lanyard_sent = False
    elif user_type == "lanyard_sent":
        user.lanyard_ordered = True
        user.lanyard_sent = True
        user.lanyard_sent_date = datetime.utcnow() - timedelta(days=random.randint(1, 10))
    elif user_type == "lanyard_ordered":
        user.lanyard_ordered = True
        user.lanyard_sent = False
    else:
        # Random lanyard status for other users
        user.lanyard_ordered = random.random() > 0.6
        user.lanyard_sent = user.lanyard_ordered and random.random() > 0.5
        if user.lanyard_sent:
            user.lanyard_sent_date = datetime.utcnow() - timedelta(days=random.randint(1, 20))
    
    db.session.add(user)
    db.session.flush()  # Get the user ID
    
    # Add tournament attendance based on user type
    if user_type == "urgent_lanyard" and upcoming_tournaments:
        # Add at least one upcoming tournament (within 9 days)
        for tournament in upcoming_tournaments[:1]:  # Just add the first one
            session_label = f"Day 1 - Day, Day 2 - Night"
            
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
    
    # Add other tournaments
    if user_type != "no_tournaments":
        # Add 1-3 random future tournaments
        available_tournaments = future_tournaments
        num_tournaments = random.randint(1, min(3, len(available_tournaments)))
        selected_tournaments = random.sample(available_tournaments, num_tournaments)
        
        for tournament in selected_tournaments:
            # Generate random session labels
            day_count = (tournament.end_date - tournament.start_date).days + 1
            sessions = []
            for i in range(min(day_count, 3)):
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
    if user_type in ["past_tournaments", "many_past_tournaments"] and past_tournaments:
        num_past = 2 if user_type == "past_tournaments" else 5
        count = min(num_past, len(past_tournaments))
        selected = random.sample(past_tournaments, count)
        
        for tournament in selected:
            past = UserPastTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(past)
    
    # Create shipping address for users with lanyards
    if user.lanyard_ordered:
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

def create_test_set():
    """Create a smaller test set with focused variations"""
    print(f"Creating {NUM_USERS} test users...")
    
    users_created = []
    admin_user = None
    
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
            # Critical test cases
            "urgent_lanyard",
            "urgent_lanyard",
            "urgent_lanyard",
            "lanyard_sent",
            "lanyard_ordered",
            "past_tournaments",
            "many_past_tournaments",
            "no_tournaments",
            # Fill in with more variation
            "regular",
            "regular",
            "regular",
            "regular"
        ]
        
        # Create users based on types
        for i in range(NUM_USERS):
            user_type = user_types[i % len(user_types)]
            print(f"Creating user {i+1}/{NUM_USERS} of type: {user_type}")
            
            try:
                user = create_user_with_variations(
                    user_type,
                    upcoming_tournaments,
                    future_tournaments,
                    past_tournaments
                )
                
                # Make first user admin
                if i == 0:
                    user.is_admin = True
                    admin_user = user
                
                users_created.append((user.email, TEST_PASSWORD))
                
            except Exception as e:
                print(f"Error creating user {i+1}: {str(e)}")
                db.session.rollback()
                continue
        
        # Commit changes
        try:
            db.session.commit()
            print(f"Successfully created {len(users_created)} test users")
            
            # Print admin credentials
            if admin_user:
                print("\nADMIN CREDENTIALS:")
                print(f"Email: {admin_user.email}")
                print(f"Password: {TEST_PASSWORD}")
            
            # Print stats
            print("\nTest User Statistics:")
            print(f"Total users: {User.query.count()}")
            print(f"Users with lanyards ordered: {User.query.filter_by(lanyard_ordered=True).count()}")
            print(f"Users with lanyards sent: {User.query.filter_by(lanyard_sent=True).count()}")
            print(f"Total tournament registrations: {UserTournament.query.count()}")
            print(f"Total past tournament entries: {UserPastTournament.query.count()}")
            
            # Print users with unsent lanyards attending upcoming tournaments
            if upcoming_tournaments:
                urgent_count = 0
                for tournament in upcoming_tournaments:
                    for reg in UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).all():
                        user = User.query.get(reg.user_id)
                        if user and user.lanyard_ordered and not user.lanyard_sent:
                            urgent_count += 1
                
                print(f"Users qualifying for urgent lanyard alert: {urgent_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {str(e)}")
            return []
        
        return users_created

if __name__ == "__main__":
    create_test_set()