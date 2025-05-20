"""
Create 50 test users with realistic variation for CourtSide Club
- Some have complete profiles, some partial
- Each user attending 3-6 different tournaments
- Random session selections
- Variation in open_to_meet, wants_to_meet
- 40% have ordered lanyards
"""
import random
import string
from datetime import datetime, timedelta
from app import app, db
from models import User, Tournament, UserTournament, UserPastTournament
from werkzeug.security import generate_password_hash

# Configuration
NUM_USERS = 50
MIN_TOURNAMENTS = 3
MAX_TOURNAMENTS = 6
MIN_SESSIONS = 1
MAX_SESSIONS = 3
LANYARD_PERCENTAGE = 40
COMPLETE_PROFILE_PERCENTAGE = 50

# Sample data for generating realistic users
first_names = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James", 
    "Isabella", "Logan", "Charlotte", "Benjamin", "Amelia", "Mason", "Mia", 
    "Ethan", "Harper", "Alexander", "Evelyn", "Jacob", "Abigail", "Michael", 
    "Emily", "Elijah", "Elizabeth", "Daniel", "Sofia", "Matthew", "Avery", 
    "Aiden", "Ella", "Henry", "Scarlett", "Joseph", "Grace", "Jackson", 
    "Chloe", "Samuel", "Victoria", "David", "Riley", "Carter", "Aria", 
    "Wyatt", "Lily", "John", "Aubrey", "Owen", "Zoey", "Luke", "Penelope"
]

last_names = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", 
    "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", 
    "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson", 
    "Clark", "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", 
    "Hernandez", "King", "Wright", "Lopez", "Hill", "Scott", "Green", 
    "Adams", "Baker", "Gonzalez", "Nelson", "Carter", "Mitchell", "Perez", 
    "Roberts", "Turner", "Phillips", "Campbell", "Parker", "Evans", "Edwards", 
    "Collins", "Stewart", "Sanchez", "Morris", "Rogers", "Reed", "Cook", 
    "Morgan", "Bell", "Murphy", "Bailey", "Rivera", "Cooper", "Richardson", 
    "Cox", "Howard", "Ward", "Torres", "Peterson", "Gray", "Ramirez", "James",
    "Watson", "Brooks", "Kelly", "Sanders", "Price", "Bennett", "Wood", "Barnes",
    "Ross", "Henderson", "Coleman", "Jenkins", "Perry", "Powell", "Long"
]

locations = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", 
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", 
    "Dallas, TX", "San Jose, CA", "Austin, TX", "Jacksonville, FL", 
    "Fort Worth, TX", "Columbus, OH", "San Francisco, CA", "Charlotte, NC", 
    "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Washington, DC",
    "London, UK", "Paris, France", "Rome, Italy", "Madrid, Spain",
    "Toronto, Canada", "Melbourne, Australia", "Tokyo, Japan", "Berlin, Germany",
    "Montreal, Canada", "Amsterdam, Netherlands", "Sydney, Australia"
]

def get_random_email(first_name, last_name):
    """Generate a random email address based on name"""
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com"]
    random_num = random.randint(1, 99)
    email_style = random.choice([
        f"{first_name.lower()}.{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{first_name.lower()}{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{first_name.lower()[0]}{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{last_name.lower()}.{first_name.lower()}{random_num}@{random.choice(domains)}"
    ])
    return email_style

def generate_password():
    """Generate a random password"""
    length = random.randint(8, 12)
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(length))

def get_available_tournaments():
    """Get all available tournaments"""
    return Tournament.query.all()

def get_random_sessions(tournament, num_sessions):
    """Get random sessions for a tournament"""
    all_sessions = tournament.sessions
    if not all_sessions or len(all_sessions) == 0:
        # If no sessions defined, create some generic ones for testing
        days = (tournament.end_date - tournament.start_date).days + 1
        all_sessions = []
        for day_offset in range(days):
            date = tournament.start_date + timedelta(days=day_offset)
            date_str = date.strftime("%Y-%m-%d")
            all_sessions.extend([
                {"date": date_str, "label": "Morning"},
                {"date": date_str, "label": "Afternoon"},
                {"date": date_str, "label": "Evening"}
            ])
    
    # Select random sessions
    if len(all_sessions) <= num_sessions:
        selected_sessions = all_sessions
    else:
        selected_sessions = random.sample(all_sessions, num_sessions)
    
    # Format as session_label (comma-separated string of date:label pairs)
    session_labels = []
    for session in selected_sessions:
        if isinstance(session, dict) and 'date' in session and 'label' in session:
            session_labels.append(f"{session['date']}:{session['label']}")
        elif isinstance(session, str):
            # Handle case where sessions are already strings
            session_labels.append(session)
    
    return ",".join(session_labels)

def create_user_with_tournaments():
    """Create a user with random tournaments"""
    # Generate user details
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    email = get_random_email(first_name, last_name)
    name = f"{first_name} {last_name}"
    password = generate_password()
    
    # Determine if user has complete profile
    has_complete_profile = random.randint(1, 100) <= COMPLETE_PROFILE_PERCENTAGE
    location = random.choice(locations) if has_complete_profile else None
    
    # Determine if lanyard ordered
    lanyard_ordered = random.randint(1, 100) <= LANYARD_PERCENTAGE
    
    # Create the user
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        name=name,
        password_hash=generate_password_hash(password),
        location=location,
        lanyard_ordered=lanyard_ordered,
        notifications=random.choice([True, False]),
        welcome_seen=True,
        is_admin=False,
        date_created=datetime.utcnow()
    )
    
    db.session.add(user)
    db.session.flush()  # To get the user ID
    
    # Get all tournaments and select random ones to attend
    all_tournaments = get_available_tournaments()
    num_tournaments = random.randint(MIN_TOURNAMENTS, MAX_TOURNAMENTS)
    selected_tournaments = random.sample(all_tournaments, min(num_tournaments, len(all_tournaments)))
    
    # Create tournament registrations
    for tournament in selected_tournaments:
        # Choose number of sessions
        num_sessions = random.randint(MIN_SESSIONS, MAX_SESSIONS)
        session_label = get_random_sessions(tournament, num_sessions)
        
        # Randomize other fields
        attending = random.choice([True, False])
        attendance_type = random.choice(['attending', 'maybe'])
        open_to_meet = random.choice([True, False])
        wants_to_meet = random.choice([True, False])
        
        user_tournament = UserTournament(
            user_id=user.id,
            tournament_id=tournament.id,
            session_label=session_label,
            attending=attending,
            attendance_type=attendance_type,
            open_to_meet=open_to_meet,
            wants_to_meet=wants_to_meet,
            created_at=datetime.utcnow()
        )
        
        db.session.add(user_tournament)
    
    # Add past tournaments for users with complete profiles
    if has_complete_profile and len(all_tournaments) > num_tournaments:
        # Get tournaments not selected for current attendance
        remaining_tournaments = [t for t in all_tournaments if t not in selected_tournaments]
        num_past_tournaments = random.randint(1, min(3, len(remaining_tournaments)))
        past_selected = random.sample(remaining_tournaments, num_past_tournaments)
        
        for tournament in past_selected:
            past_tournament = UserPastTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                created_at=datetime.utcnow()
            )
            db.session.add(past_tournament)
    
    return user, email, password

def create_test_users():
    """Create the specified number of test users"""
    print(f"Creating {NUM_USERS} test users...")
    
    users_created = []
    admin_credentials = None
    
    with app.app_context():
        for i in range(NUM_USERS):
            user, email, password = create_user_with_tournaments()
            
            # Make the first user an admin for testing
            if i == 0:
                user.is_admin = True
                admin_credentials = (email, password)
            
            users_created.append((email, password))
            print(f"Created user {i+1}/{NUM_USERS}: {email}")
        
        # Commit all changes to the database
        db.session.commit()
        
        # Print out admin credentials
        if admin_credentials:
            print(f"\nADMIN CREDENTIALS:")
            print(f"Email: {admin_credentials[0]}")
            print(f"Password: {admin_credentials[1]}")
        
        # Print statistics
        print(f"\nCreated {len(users_created)} test users")
        print(f"Users with complete profiles: ~{NUM_USERS * COMPLETE_PROFILE_PERCENTAGE // 100}")
        print(f"Users with lanyards ordered: ~{NUM_USERS * LANYARD_PERCENTAGE // 100}")
        
        return users_created

if __name__ == "__main__":
    create_test_users()