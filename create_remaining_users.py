"""
Create remaining test users to reach 750 total
- Continue from current count
- Create in efficient batches
- Include all required relationships
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
    "Skylar", "Charles", "Violet", "Josiah", "Claire", "Hudson", "Bella", "Christian", "Aurora", "Hunter",
    "Lucy", "Connor", "Anna", "Eli", "Samantha", "Ezra", "Caroline", "Aaron", "Genesis", "Landon",
    "Aaliyah", "Adrian", "Kennedy", "Jonathan", "Kinsley", "Nolan", "Allison", "Jeremiah", "Maya", "Easton",
    "Sarah", "Elias", "Madelyn", "Colton", "Adeline", "Cameron", "Alexa", "Carson", "Ariana", "Robert",
    "Elena", "Angel", "Maria", "Maverick", "Eva", "Nicholas", "Melanie", "Dominic", "Naomi", "Jaxson",
    "Isla", "Greyson", "Ashley", "Adam", "Nicole", "Ian", "Leila", "Austin", "Hailey", "Santiago",
    "Gabriella", "Jordan", "Katherine", "Cooper", "Natalia", "Brayden", "Alice", "Roman", "Trinity", "Evan"
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
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez",
    "Powell", "Jenkins", "Perry", "Russell", "Sullivan", "Bell", "Coleman", "Butler", "Henderson", "Barnes",
    "Gonzales", "Fisher", "Vasquez", "Simmons", "Romero", "Jordan", "Patterson", "Alexander", "Hamilton", "Graham",
    "Reynolds", "Griffin", "Wallace", "Moreno", "West", "Cole", "Hayes", "Bryant", "Herrera", "Gibson",
    "Ellis", "Tran", "Medina", "Aguilar", "Stevens", "Murray", "Ford", "Castro", "Marshall", "Owens"
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

def create_user_batch(batch_size=100):
    """Create a batch of users efficiently"""
    tournaments = Tournament.query.all()
    
    users_created = 0
    
    for i in range(batch_size):
        # Create user
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        email = get_random_email(first_name, last_name)
        
        # Ensure unique email
        attempt = 0
        while User.query.filter_by(email=email).first() and attempt < 10:
            email = get_random_email(first_name, last_name)
            attempt += 1
        
        user = User(
            email=email,
            password_hash=generate_password_hash(f"TestPass{random.randint(100, 999)}"),
            first_name=first_name,
            last_name=last_name,
            name=f"{first_name} {last_name}",
            notifications=random.choice([True, False]),
            welcome_seen=True,
            test_user=True
        )
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Add tournaments
        num_tournaments = random.randint(2, min(8, len(tournaments)))
        selected_tournaments = random.sample(tournaments, num_tournaments)
        
        has_sessions = False
        
        for tournament in selected_tournaments:
            attending = random.choice([True, False])
            open_to_meet = random.choice([True, False])
            wants_to_meet = random.choice([True, False]) if attending else False
            
            session_selections = []
            if attending:
                num_sessions = random.randint(1, 4)
                session_selections = get_random_sessions(tournament, num_sessions)
                if session_selections:
                    has_sessions = True
            
            user_tournament = UserTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                attending=attending,
                open_to_meet=open_to_meet,
                wants_to_meet=wants_to_meet,
                session_label=','.join(session_selections) if session_selections else None
            )
            
            db.session.add(user_tournament)
        
        # Add lanyard order and shipping if has sessions
        if has_sessions:
            user.lanyard_ordered = True
            
            full_name = f"{user.first_name} {user.last_name}"
            address = ShippingAddress(
                user_id=user.id,
                name=full_name,
                address1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine'])} {random.choice(['St', 'Ave', 'Blvd'])}",
                address2=random.choice(["", f"Apt {random.randint(1, 999)}"]) if random.random() < 0.3 else "",
                city=random.choice(CITIES),
                state=random.choice(US_STATES),
                zip_code=f"{random.randint(10000, 99999)}",
                country="USA"
            )
            
            db.session.add(address)
        
        users_created += 1
    
    return users_created

def create_remaining_users():
    """Create remaining users to reach 750 total"""
    
    with app.app_context():
        # Check current count
        current_count = User.query.filter_by(test_user=True).count()
        target = 750
        remaining = target - current_count
        
        logger.info(f"Current test users: {current_count}")
        logger.info(f"Target: {target}")
        logger.info(f"Need to create: {remaining}")
        
        if remaining <= 0:
            logger.info("Already have enough test users!")
            return True
        
        try:
            total_created = 0
            batch_size = 50  # Smaller batches for reliability
            
            while total_created < remaining:
                current_batch_size = min(batch_size, remaining - total_created)
                
                logger.info(f"Creating batch of {current_batch_size} users... ({total_created + 1}-{total_created + current_batch_size})")
                
                batch_created = create_user_batch(current_batch_size)
                total_created += batch_created
                
                # Commit this batch
                db.session.commit()
                logger.info(f"Committed batch. Total created so far: {total_created}")
                
                # Quick sanity check
                if total_created >= remaining:
                    break
            
            logger.info(f"Successfully created {total_created} additional users")
            return True
            
        except Exception as e:
            logger.error(f"Error creating users: {str(e)}")
            db.session.rollback()
            return False

def verify_final_results():
    """Verify final results and show sample data"""
    with app.app_context():
        # Final counts
        test_users = User.query.filter_by(test_user=True).count()
        attending = UserTournament.query.filter_by(attending=True).count()
        lanyard_orders = User.query.filter_by(lanyard_ordered=True, test_user=True).count()
        shipping_addresses = ShippingAddress.query.count()
        
        logger.info(f"""
=== FINAL RESULTS ===
Users where test_user = True: {test_users}
UserTournaments where attending = True: {attending}
Users with lanyard_ordered = True: {lanyard_orders}
Total shipping addresses: {shipping_addresses}
        """)
        
        # Sample user tournament session selections
        logger.info("\nSample user tournament session selections:")
        samples = UserTournament.query.filter(
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        ).limit(3).all()
        
        for i, ut in enumerate(samples, 1):
            user = User.query.get(ut.user_id)
            tournament = Tournament.query.get(ut.tournament_id)
            logger.info(f"{i}. {user.name} -> {tournament.name}: {ut.session_label}")

if __name__ == "__main__":
    success = create_remaining_users()
    
    if success:
        verify_final_results()
        print("User creation completed successfully!")
    else:
        print("Failed to create remaining users")
        sys.exit(1)