"""
Create 50 realistic test users for Let'CourtSide as a test batch

Each user will have:
- Realistic names and email formats
- 2-8 randomized tournaments from existing database
- Proper attendance flags and session selections
- Randomized open_to_meet/wants_to_meet flags
- Lanyard orders for users with session selections
- Associated ShippingAddress entries for lanyard orders
- test_user = True flag for identification
"""
import logging
import random
import sys
from datetime import datetime, timedelta
from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Realistic first names
FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella", "William",
    "Mia", "James", "Charlotte", "Benjamin", "Amelia", "Lucas", "Harper", "Henry", "Evelyn", "Alexander",
    "Abigail", "Michael", "Emily", "Daniel", "Elizabeth", "Matthew", "Mila", "Jackson", "Ella", "Sebastian",
    "Madison", "David", "Scarlett", "Joseph", "Victoria", "Samuel", "Aria", "John", "Grace", "Owen",
    "Chloe", "Wyatt", "Camila", "Jack", "Penelope", "Luke", "Riley", "Jayden", "Layla", "Dylan",
    "Lillian", "Grayson", "Nora", "Levi", "Zoey", "Isaac", "Mila", "Gabriel", "Aubrey", "Julian",
    "Hannah", "Mateo", "Lily", "Anthony", "Addison", "Jaxon", "Eleanor", "Lincoln", "Natalie", "Joshua",
    "Luna", "Christopher", "Savannah", "Andrew", "Brooklyn", "Theodore", "Leah", "Caleb", "Zoe", "Ryan",
    "Stella", "Asher", "Hazel", "Nathan", "Ellie", "Thomas", "Paisley", "Leo", "Audrey", "Isaiah",
    "Skylar", "Charles", "Violet", "Josiah", "Claire", "Hudson", "Bella", "Christian", "Aurora", "Hunter"
]

# Realistic last names
LAST_NAMES = [
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

# Email domains for realistic emails
EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "live.com", "msn.com", "comcast.net", "verizon.net",
    "example.com", "test.com", "demo.com", "sample.org", "mockmail.net"
]

# US states for shipping addresses
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

# Cities for shipping addresses
CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego",
    "Dallas", "San Jose", "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte", "San Francisco",
    "Indianapolis", "Seattle", "Denver", "Washington", "Boston", "El Paso", "Nashville", "Detroit",
    "Oklahoma City", "Portland", "Las Vegas", "Memphis", "Louisville", "Baltimore", "Milwaukee", "Albuquerque",
    "Tucson", "Fresno", "Mesa", "Sacramento", "Atlanta", "Kansas City", "Colorado Springs", "Miami"
]

def get_random_email(first_name, last_name):
    """Generate a random email address based on name"""
    formats = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name.lower()}{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}{last_name[0].lower()}",
        f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}",
        f"{first_name.lower()}{random.randint(1, 999)}"
    ]
    
    username = random.choice(formats)
    domain = random.choice(EMAIL_DOMAINS)
    return f"{username}@{domain}"

def generate_password():
    """Generate a random password"""
    return f"TestPass{random.randint(100, 999)}"

def get_all_tournaments():
    """Get all available tournaments"""
    return Tournament.query.all()

def get_random_sessions(tournament, num_sessions):
    """Get random sessions for a tournament"""
    if not tournament.sessions:
        return []
    
    # Handle sessions field - it can be a list or string
    if isinstance(tournament.sessions, list):
        available_sessions = tournament.sessions
    elif isinstance(tournament.sessions, str):
        available_sessions = tournament.sessions.split(',') if tournament.sessions else []
    else:
        return []
    
    # Clean up session names
    available_sessions = [s.strip() for s in available_sessions if s and s.strip()]
    
    # Select random number of sessions (at least 1 if any available)
    if available_sessions:
        num_to_select = min(num_sessions, len(available_sessions))
        return random.sample(available_sessions, num_to_select)
    
    return []

def create_shipping_address(user):
    """Create a shipping address for a user"""
    full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.name or "Test User"
    
    address = ShippingAddress(
        user_id=user.id,
        name=full_name,
        address1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm', 'Cedar', 'Park', 'First', 'Second'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr', 'Way'])}",
        address2=random.choice(["", f"Apt {random.randint(1, 999)}", f"Suite {random.randint(100, 999)}"]) if random.random() < 0.3 else "",
        city=random.choice(CITIES),
        state=random.choice(US_STATES),
        zip_code=f"{random.randint(10000, 99999)}",
        country="USA"
    )
    
    return address

def create_user_with_tournaments():
    """Create a user with random tournaments"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    email = get_random_email(first_name, last_name)
    
    # Ensure unique email
    attempt = 0
    while User.query.filter_by(email=email).first() and attempt < 10:
        email = get_random_email(first_name, last_name)
        attempt += 1
    
    # Create user
    user = User(
        email=email,
        password_hash=generate_password_hash(generate_password()),
        first_name=first_name,
        last_name=last_name,
        name=f"{first_name} {last_name}",
        notifications=random.choice([True, False]),
        welcome_seen=True,
        test_user=True
    )
    
    db.session.add(user)
    db.session.flush()  # Get user ID
    
    # Get all tournaments
    tournaments = get_all_tournaments()
    if not tournaments:
        logger.warning("No tournaments found in database")
        return user, [], None
    
    # Select 2-8 random tournaments
    num_tournaments = random.randint(2, min(8, len(tournaments)))
    selected_tournaments = random.sample(tournaments, num_tournaments)
    
    user_tournaments = []
    has_sessions = False
    
    for tournament in selected_tournaments:
        # Random attendance flags
        attending = random.choice([True, False])
        open_to_meet = random.choice([True, False])
        wants_to_meet = random.choice([True, False]) if attending else False
        
        # Get random sessions if attending
        session_selections = []
        if attending:
            num_sessions = random.randint(1, 4)  # 1-4 sessions per tournament
            session_selections = get_random_sessions(tournament, num_sessions)
            if session_selections:
                has_sessions = True
        
        # Create UserTournament record
        user_tournament = UserTournament(
            user_id=user.id,
            tournament_id=tournament.id,
            attending=attending,
            open_to_meet=open_to_meet,
            wants_to_meet=wants_to_meet,
            session_label=','.join(session_selections) if session_selections else None
        )
        
        user_tournaments.append(user_tournament)
        db.session.add(user_tournament)
    
    # Create lanyard order and shipping address if user has sessions
    shipping_address = None
    if has_sessions:
        user.lanyard_ordered = True
        shipping_address = create_shipping_address(user)
        db.session.add(shipping_address)
    
    return user, user_tournaments, shipping_address

def create_50_test_users():
    """Create 50 test users with proper tournament distributions"""
    logger.info("Starting creation of 50 test users...")
    
    with app.app_context():
        created_users = 0
        created_tournaments = 0
        created_shipping = 0
        
        try:
            for i in range(50):
                if i % 10 == 0:
                    logger.info(f"Creating user {i+1}/50...")
                
                user, user_tournaments, shipping_address = create_user_with_tournaments()
                
                created_users += 1
                created_tournaments += len(user_tournaments)
                if shipping_address:
                    created_shipping += 1
                
                # Commit every 10 users to avoid memory issues
                if (i + 1) % 10 == 0:
                    db.session.commit()
                    logger.info(f"Committed batch ending at user {i+1}")
            
            # Final commit
            db.session.commit()
            
            logger.info(f"""
=== Test User Creation Complete ===
Created Users: {created_users}
Created UserTournaments: {created_tournaments}
Created ShippingAddresses: {created_shipping}
            """)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating test users: {str(e)}")
            db.session.rollback()
            return False

def test_results():
    """Test the results by querying counts"""
    logger.info("Testing results...")
    
    with app.app_context():
        # Count test users
        test_users_count = User.query.filter_by(test_user=True).count()
        logger.info(f"Users where test_user = True: {test_users_count}")
        
        # Count attending user tournaments
        attending_count = UserTournament.query.filter_by(attending=True).count()
        logger.info(f"UserTournaments where attending = True: {attending_count}")
        
        # Count users with lanyard orders
        lanyard_count = User.query.filter_by(lanyard_ordered=True, test_user=True).count()
        logger.info(f"Test users with lanyard_ordered = True: {lanyard_count}")
        
        # Sample user tournament session selections
        logger.info("\nSample user tournament session selections:")
        sample_tournaments = UserTournament.query.filter(
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        ).limit(3).all()
        
        for i, ut in enumerate(sample_tournaments, 1):
            user = User.query.get(ut.user_id)
            tournament = Tournament.query.get(ut.tournament_id)
            logger.info(f"{i}. {user.name} -> {tournament.name}: {ut.session_label}")

if __name__ == "__main__":
    success = create_50_test_users()
    
    if success:
        test_results()
        print("50 test users created successfully!")
    else:
        print("Failed to create test users")
        sys.exit(1)