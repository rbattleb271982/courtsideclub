"""
Create QA test users for comprehensive testing.
"""
import random
import string
from datetime import datetime, timedelta
from app import app, db
from models import User, Tournament, UserTournament, UserPastTournament, ShippingAddress
from werkzeug.security import generate_password_hash

# Configuration
QA_USER_COUNT = 50
TEST_PASSWORD = "testuser123"  # Common password for all test users

# Create known test users with predictable accounts
qa_users = [
    {
        "email": "qa_admin@test.com",
        "first_name": "QA",
        "last_name": "Admin",
        "is_admin": True,
        "lanyard_ordered": True,
        "lanyard_sent": True
    },
    {
        "email": "qa_urgent@test.com",
        "first_name": "QA",
        "last_name": "Urgent",
        "is_admin": False,
        "lanyard_ordered": True,
        "lanyard_sent": False,
        "attending_upcoming": True
    },
    {
        "email": "qa_many@test.com",
        "first_name": "QA",
        "last_name": "Many",
        "is_admin": False,
        "lanyard_ordered": True,
        "lanyard_sent": False,
        "many_tournaments": True
    },
    {
        "email": "qa_none@test.com",
        "first_name": "QA",
        "last_name": "None",
        "is_admin": False,
        "lanyard_ordered": False,
        "lanyard_sent": False,
        "no_tournaments": True
    },
    {
        "email": "qa_past@test.com",
        "first_name": "QA",
        "last_name": "Past",
        "is_admin": False,
        "lanyard_ordered": True,
        "lanyard_sent": True,
        "many_past": True
    }
]

# Sample data for generating random users
first_names = ["Robert", "Julia", "Samuel", "Sarah", "Daniel", "Michelle", "Patrick", "Catherine", 
               "George", "Laura", "Jeffrey", "Nicole", "Brian", "Rebecca", "Kenneth", "Angela",
               "Timothy", "Melissa", "Gregory", "Heather", "Jason", "Amy", "Jose", "Christina",
               "Edward", "Tiffany", "Ronald", "Brittany", "Anthony", "Jennifer"]

last_names = ["Long", "Sullivan", "Reed", "Hughes", "Butler", "Foster", "Simmons", "Russell", 
              "Bryant", "Griffin", "Diaz", "Hayes", "Myers", "Ford", "Hamilton", "Graham",
              "Sullivan", "Wallace", "Woods", "Cole", "West", "Jordan", "Owens", "Reynolds",
              "Fisher", "Ellis", "Harrison", "Gibson", "McDonald", "Cruz"]

locations = ["Seattle, WA", "Denver, CO", "Minneapolis, MN", "Austin, TX", 
             "Raleigh, NC", "Orlando, FL", "San Francisco, CA", "Chicago, IL", 
             "New York, NY", "Phoenix, AZ", "Montreal, Canada", "Vancouver, Canada"]

def create_test_users():
    """Create test users for QA testing"""
    print(f"Creating {len(qa_users)} known QA test users and {QA_USER_COUNT} random test users...")
    
    created_users = []
    
    with app.app_context():
        # Get tournament data
        future_tournaments = Tournament.query.filter(
            Tournament.start_date >= datetime.utcnow().date()
        ).order_by(Tournament.start_date).all()
        
        upcoming_tournaments = Tournament.query.filter(
            Tournament.start_date >= datetime.utcnow().date(),
            Tournament.start_date <= datetime.utcnow().date() + timedelta(days=9)
        ).order_by(Tournament.start_date).all()
        
        past_tournaments = Tournament.query.filter(
            Tournament.end_date < datetime.utcnow().date()
        ).all()
        
        if not future_tournaments:
            print("No tournaments found. Please import tournaments first.")
            return
        
        print(f"Found {len(future_tournaments)} future tournaments")
        print(f"Found {len(upcoming_tournaments)} upcoming tournaments (next 9 days)")
        print(f"Found {len(past_tournaments)} past tournaments")
        
        # Create the known QA test users
        for qa_user in qa_users:
            print(f"Creating QA test user: {qa_user['email']}")
            
            # Create the user
            user = User(
                email=qa_user['email'],
                first_name=qa_user['first_name'],
                last_name=qa_user['last_name'],
                name=f"{qa_user['first_name']} {qa_user['last_name']}",
                password_hash=generate_password_hash(TEST_PASSWORD),
                location=random.choice(locations),
                lanyard_ordered=qa_user.get('lanyard_ordered', False),
                lanyard_sent=qa_user.get('lanyard_sent', False),
                is_admin=qa_user.get('is_admin', False),
                welcome_seen=True,
                notifications=True,
                date_created=datetime.utcnow() - timedelta(days=random.randint(10, 30))
            )
            
            if user.lanyard_sent:
                user.lanyard_sent_date = datetime.utcnow() - timedelta(days=random.randint(1, 10))
            
            db.session.add(user)
            db.session.flush()  # Get the user ID
            
            # Add shipping address if lanyard ordered
            if user.lanyard_ordered:
                address = ShippingAddress(
                    user_id=user.id,
                    name=user.get_full_name(),
                    address1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Park', 'Oak'])} St",
                    address2=random.choice(["", f"Apt {random.randint(1, 999)}"]),
                    city=user.location.split(",")[0] if user.location else "New York",
                    state=user.location.split(",")[1].strip() if user.location and "," in user.location else "NY",
                    zip_code=f"{random.randint(10000, 99999)}",
                    country="USA",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 10))
                )
                db.session.add(address)
            
            # Add tournament registrations based on user type
            if qa_user.get('attending_upcoming') and upcoming_tournaments:
                # Add all upcoming tournaments
                for tournament in upcoming_tournaments:
                    ut = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        session_label="Day 1 - Day, Day 1 - Night, Day 2 - Day, Day 2 - Night",
                        attending=True,
                        attendance_type='attending',
                        open_to_meet=True,
                        wants_to_meet=True,
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 5))
                    )
                    db.session.add(ut)
            
            elif qa_user.get('many_tournaments') and future_tournaments:
                # Add 5+ tournaments
                num_to_add = min(6, len(future_tournaments))
                for tournament in future_tournaments[:num_to_add]:
                    ut = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        session_label="Day 1 - Day, Day 3 - Night",
                        attending=True,
                        attendance_type='attending',
                        open_to_meet=random.choice([True, False]),
                        wants_to_meet=random.choice([True, False]),
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 15))
                    )
                    db.session.add(ut)
            
            elif not qa_user.get('no_tournaments') and future_tournaments:
                # Add 1-3 random tournaments
                num_to_add = min(random.randint(1, 3), len(future_tournaments))
                selected = random.sample(future_tournaments, num_to_add)
                
                for tournament in selected:
                    ut = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        session_label="Day 1 - Day, Day 2 - Night",
                        attending=True,
                        attendance_type=random.choice(['attending', 'maybe']),
                        open_to_meet=random.choice([True, False]),
                        wants_to_meet=random.choice([True, False]),
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20))
                    )
                    db.session.add(ut)
            
            # Add past tournaments if specified
            if qa_user.get('many_past') and past_tournaments:
                num_past = min(8, len(past_tournaments))
                for tournament in past_tournaments[:num_past]:
                    past = UserPastTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                    )
                    db.session.add(past)
            
            created_users.append((qa_user['email'], TEST_PASSWORD))
        
        # Create random test users
        for i in range(QA_USER_COUNT):
            # Generate random user data
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email = f"qa_random{i+1}@letcourtside.test"
            
            # Create basic user
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                name=f"{first_name} {last_name}",
                password_hash=generate_password_hash(TEST_PASSWORD),
                location=random.choice(locations) if random.random() > 0.3 else None,
                lanyard_ordered=random.random() > 0.5,
                lanyard_sent=False,  # Most haven't been sent to create more urgent cases
                welcome_seen=True,
                is_admin=False,
                notifications=random.choice([True, False]),
                date_created=datetime.utcnow() - timedelta(days=random.randint(1, 60))
            )
            
            if random.random() < 0.2:  # 20% have been sent
                user.lanyard_sent = True
                user.lanyard_sent_date = datetime.utcnow() - timedelta(days=random.randint(1, 10))
            
            db.session.add(user)
            db.session.flush()
            
            # Add shipping address if lanyard ordered
            if user.lanyard_ordered:
                address = ShippingAddress(
                    user_id=user.id,
                    name=user.get_full_name(),
                    address1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Park', 'Oak'])} St",
                    address2=random.choice(["", f"Apt {random.randint(1, 999)}"]),
                    city=user.location.split(",")[0] if user.location else "New York",
                    state=user.location.split(",")[1].strip() if user.location and "," in user.location else "NY",
                    zip_code=f"{random.randint(10000, 99999)}",
                    country="USA",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 10))
                )
                db.session.add(address)
            
            # Add random tournaments (75% have tournaments)
            if random.random() < 0.75 and future_tournaments:
                num_tournaments = random.randint(1, min(4, len(future_tournaments)))
                selected = random.sample(future_tournaments, num_tournaments)
                
                for tournament in selected:
                    # Create random session labels
                    days = (tournament.end_date - tournament.start_date).days + 1
                    sessions = []
                    for d in range(min(days, 3)):
                        if random.random() < 0.7:  # 70% include Day sessions
                            sessions.append(f"Day {d+1} - Day")
                        if random.random() < 0.5:  # 50% include Night sessions
                            sessions.append(f"Day {d+1} - Night")
                    
                    session_label = ", ".join(sessions)
                    
                    ut = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        session_label=session_label,
                        attending=True if session_label else random.choice([True, False]),
                        attendance_type=random.choice(['attending', 'maybe']),
                        open_to_meet=random.choice([True, False]),
                        wants_to_meet=random.choice([True, False]),
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20))
                    )
                    db.session.add(ut)
            
            # Add past tournaments (60% have past tournaments)
            if random.random() < 0.6 and past_tournaments:
                num_past = random.randint(1, min(5, len(past_tournaments)))
                selected = random.sample(past_tournaments, num_past)
                
                for tournament in selected:
                    past = UserPastTournament(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 45))
                    )
                    db.session.add(past)
            
            created_users.append((email, TEST_PASSWORD))
            
            if (i+1) % 10 == 0:
                print(f"Created {i+1}/{QA_USER_COUNT} random test users")
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"Successfully created {len(created_users)} test users")
            
            # Print stats
            print("\nTest User Statistics:")
            print(f"Total users: {User.query.count()}")
            print(f"Users with lanyards ordered: {User.query.filter_by(lanyard_ordered=True).count()}")
            print(f"Users with lanyards sent: {User.query.filter_by(lanyard_sent=True).count()}")
            print(f"Total tournament registrations: {UserTournament.query.count()}")
            print(f"Total past tournament entries: {UserPastTournament.query.count()}")
            
            # Print known user credentials
            print("\nQA Test User Credentials (all use password: testuser123):")
            for user in qa_users:
                print(f"- {user['email']} ({user['first_name']} {user['last_name']})")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {str(e)}")
        
        return created_users

def add_past_tournaments_to_users():
    """
    Add past tournaments to all test users.
    Each user will get 3-6 random past tournaments.
    """
    with app.app_context():
        past_tournaments = Tournament.query.filter(
            Tournament.end_date < datetime.utcnow().date()
        ).all()
        
        if not past_tournaments:
            print("No past tournaments found.")
            return
        
        # Get all users
        users = User.query.all()
        
        for user in users:
            # Skip users who already have past tournaments
            existing_count = UserPastTournament.query.filter_by(user_id=user.id).count()
            if existing_count > 0:
                continue
            
            # Add 3-6 random past tournaments
            num_past = random.randint(3, min(6, len(past_tournaments)))
            selected = random.sample(past_tournaments, num_past)
            
            for tournament in selected:
                past = UserPastTournament(
                    user_id=user.id,
                    tournament_id=tournament.id,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60))
                )
                db.session.add(past)
        
        # Commit changes
        try:
            db.session.commit()
            total_past = UserPastTournament.query.count()
            print(f"Successfully added past tournaments. Total past tournament entries: {total_past}")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding past tournaments: {str(e)}")

if __name__ == "__main__":
    create_test_users()
    # Uncomment to add past tournaments to existing users
    # add_past_tournaments_to_users()