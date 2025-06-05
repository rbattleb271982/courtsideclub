"""
Create 25 test users at a time for efficiency
"""
import logging
import random
import sys
from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIRST_NAMES = ["Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella", "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia", "Lucas", "Harper", "Henry", "Evelyn", "Alexander"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "test.com"]
US_STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]

def get_random_email(first_name, last_name):
    username = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}"
    domain = random.choice(EMAIL_DOMAINS)
    return f"{username}@{domain}"

def get_random_sessions(tournament, num_sessions):
    if not tournament.sessions:
        return []
    
    if isinstance(tournament.sessions, list):
        available_sessions = tournament.sessions
    elif isinstance(tournament.sessions, str):
        available_sessions = tournament.sessions.split(',') if tournament.sessions else []
    else:
        return []
    
    available_sessions = [s.strip() for s in available_sessions if s and s.strip()]
    
    if available_sessions:
        num_to_select = min(num_sessions, len(available_sessions))
        return random.sample(available_sessions, num_to_select)
    
    return []

def create_25_users():
    with app.app_context():
        tournaments = Tournament.query.all()
        created = 0
        
        try:
            for i in range(25):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                email = get_random_email(first_name, last_name)
                
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
                db.session.flush()
                
                # Add 2-6 tournaments per user
                num_tournaments = random.randint(2, min(6, len(tournaments)))
                selected_tournaments = random.sample(tournaments, num_tournaments)
                
                has_sessions = False
                
                for tournament in selected_tournaments:
                    attending = random.choice([True, False])
                    open_to_meet = random.choice([True, False])
                    wants_to_meet = random.choice([True, False]) if attending else False
                    
                    session_selections = []
                    if attending:
                        num_sessions = random.randint(1, 3)
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
                
                # Add shipping address if has sessions
                if has_sessions:
                    user.lanyard_ordered = True
                    
                    address = ShippingAddress(
                        user_id=user.id,
                        name=f"{first_name} {last_name}",
                        address1=f"{random.randint(100, 999)} Main St",
                        city=random.choice(CITIES),
                        state=random.choice(US_STATES),
                        zip_code=f"{random.randint(10000, 99999)}",
                        country="USA"
                    )
                    
                    db.session.add(address)
                
                created += 1
            
            db.session.commit()
            logger.info(f"Successfully created {created} users")
            return True
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = create_25_users()
    if success:
        with app.app_context():
            total = User.query.filter_by(test_user=True).count()
            print(f"25 users created successfully! Total test users: {total}")
    else:
        print("Failed to create users")
        sys.exit(1)