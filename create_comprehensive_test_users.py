"""
Create 150 test users with comprehensive variation for CourtSide Club
- Profile variations: complete, skipped, resumed
- Tournament attendance: 1-4 tournaments, some in next 9 days, some with none
- Session selections: day only, night only, both, or none
- Meetup preferences: opted in, opted out, never touched
- Lanyard workflow: eligible but not ordered, submitted address, sent, errors, skipped
- Email events: simulate each type of email event
- Past tournaments: some with 1-3, some with removals, some with 5+
- Urgent lanyard alerts: at least 3 users qualifying for urgent alerts
"""
import random
import string
from datetime import datetime, timedelta, date
from app import app, db
from models import User, Tournament, UserTournament, UserPastTournament, ShippingAddress, Event
from werkzeug.security import generate_password_hash
from sqlalchemy import desc, and_

# Configuration
NUM_USERS = 150
TEST_PASSWORD = "testuser123"  # Common password for all test users for easy login

# Sample data for generating realistic users
first_names = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James", 
    "Isabella", "Logan", "Charlotte", "Benjamin", "Amelia", "Mason", "Mia", 
    "Ethan", "Harper", "Alexander", "Evelyn", "Jacob", "Abigail", "Michael", 
    "Emily", "Elijah", "Elizabeth", "Daniel", "Sofia", "Matthew", "Avery", 
    "Aiden", "Ella", "Henry", "Scarlett", "Joseph", "Grace", "Jackson", 
    "Chloe", "Samuel", "Victoria", "David", "Riley", "Carter", "Aria", 
    "Wyatt", "Lily", "John", "Aubrey", "Owen", "Zoey", "Luke", "Penelope",
    "Nicholas", "Hannah", "Andrew", "Addison", "Joshua", "Eleanor", "Christopher",
    "Natalie", "Ryan", "Lucy", "Nathan", "Brooklyn", "Jonathan", "Audrey",
    "Christian", "Leah", "Julian", "Sarah", "Isaac", "Allison", "Aaron",
    "Gabriella", "Thomas", "Savannah", "Connor", "Anna", "Caleb", "Samantha"
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
    random_num = random.randint(1, 999)
    email_style = random.choice([
        f"{first_name.lower()}.{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{first_name.lower()}{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{first_name.lower()[0]}{last_name.lower()}{random_num}@{random.choice(domains)}",
        f"{last_name.lower()}.{first_name.lower()}{random_num}@{random.choice(domains)}"
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

def get_all_tournaments():
    """Get all tournaments"""
    return Tournament.query.all()

def get_past_tournaments():
    """Get tournaments that have already ended"""
    today = datetime.utcnow().date()
    return Tournament.query.filter(Tournament.end_date < today).all()

def get_session_selections(tournament, selection_type):
    """Get session selections based on the selection type"""
    all_sessions = tournament.sessions

    if not all_sessions or len(all_sessions) == 0:
        # If no sessions defined, create generic ones
        days = (tournament.end_date - tournament.start_date).days + 1
        all_sessions = []
        for day_offset in range(days):
            date = tournament.start_date + timedelta(days=day_offset)
            day_num = day_offset + 1
            all_sessions.extend([
                f"Day {day_num} - Day",
                f"Day {day_num} - Night"
            ])

    # Now select sessions based on type
    session_labels = []
    
    if selection_type == "none":
        return ""
    elif selection_type == "day_only":
        # Select only day sessions
        session_labels = [s for s in all_sessions if "Day" in s and "Night" not in s]
        if not session_labels and all_sessions:
            session_labels = [random.choice([s for s in all_sessions if "Night" not in s] or [all_sessions[0]])]
    elif selection_type == "night_only":
        # Select only night sessions
        session_labels = [s for s in all_sessions if "Night" in s]
        if not session_labels and all_sessions:
            session_labels = [random.choice([s for s in all_sessions if "Night" in s] or [all_sessions[-1]])]
    elif selection_type == "both":
        # Select a mix of day and night sessions
        day_sessions = [s for s in all_sessions if "Day" in s and "Night" not in s]
        night_sessions = [s for s in all_sessions if "Night" in s]
        
        if day_sessions and night_sessions:
            session_labels = [random.choice(day_sessions), random.choice(night_sessions)]
        elif all_sessions:
            # If we don't have proper day/night labels, just pick random sessions
            num_sessions = min(len(all_sessions), random.randint(1, 3))
            session_labels = random.sample(all_sessions, num_sessions)
    
    # Handle empty results
    if not session_labels and all_sessions:
        num_sessions = min(len(all_sessions), random.randint(1, 3))
        session_labels = random.sample(all_sessions, num_sessions)
    
    return ", ".join(session_labels) if session_labels else ""

def create_shipping_address(user, with_errors=False):
    """Create a shipping address for a user, optionally with errors"""
    # Generate address data
    if with_errors:
        # Create an address with some fields incomplete or malformed
        address = ShippingAddress(
            user_id=user.id,
            name=user.get_full_name(),
            address1=random.choice(["", "123 Main St"]),
            address2="",
            city=random.choice(["", "New York"]),
            state=random.choice(["", "NY"]),
            zip_code=random.choice(["", "123"]),  # Invalid zip
            country=random.choice(["", "USA"]),
            created_at=datetime.utcnow()
        )
    else:
        # Create a complete, valid address
        address = ShippingAddress(
            user_id=user.id,
            name=user.get_full_name(),
            address1=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Maple', 'Cedar'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr', 'Ln'])}",
            address2=random.choice(["", f"Apt {random.randint(1, 999)}", f"Suite {random.randint(100, 999)}"]),
            city=user.location.split(",")[0] if user.location else random.choice(["New York", "Chicago", "Los Angeles", "Houston", "Phoenix"]),
            state=user.location.split(",")[1].strip() if user.location and "," in user.location else random.choice(["NY", "IL", "CA", "TX", "AZ"]),
            zip_code=f"{random.randint(10000, 99999)}",
            country="USA",
            created_at=datetime.utcnow()
        )
    
    db.session.add(address)
    return address

def log_test_event(user_id, event_name, data=None):
    """Create a test event in the database"""
    if data is None:
        data = {}
    
    # Add standard metadata
    data.update({
        'ip_address': f"192.168.1.{random.randint(1, 255)}",
        'user_agent': "Test Browser",
        'timestamp': datetime.utcnow().isoformat(),
        'is_test_data': True
    })
    
    # Create and save the event
    event = Event(
        user_id=user_id,
        name=event_name,
        event_data=data,
        timestamp=datetime.utcnow() - timedelta(days=random.randint(0, 30))
    )
    
    db.session.add(event)
    return event

def create_profile_variation(variation_type):
    """Create a user with profile variation based on type"""
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    email = get_random_email(first_name, last_name)
    
    if variation_type == "complete":
        # Fully completed profile with location
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            name=f"{first_name} {last_name}",
            password_hash=generate_password_hash(TEST_PASSWORD),
            location=random.choice(locations),
            notifications=True,
            welcome_seen=True,
            is_admin=False,
            date_created=datetime.utcnow() - timedelta(days=random.randint(10, 60))
        )
    elif variation_type == "skipped":
        # Profile with minimal info, skipped setup
        user = User(
            email=email,
            first_name=first_name,  # Must include first_name due to database constraint
            last_name=last_name,    # Must include last_name due to database constraint
            name=f"{first_name} {last_name}",
            password_hash=generate_password_hash(TEST_PASSWORD),
            welcome_seen=True,
            is_admin=False,
            date_created=datetime.utcnow() - timedelta(days=random.randint(10, 60))
        )
        # Log that they skipped profile
        log_test_event(user.id, "user_skipped_profile")
    elif variation_type == "resumed":
        # Started minimal, then resumed later
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            name=f"{first_name} {last_name}",
            password_hash=generate_password_hash(TEST_PASSWORD),
            location=random.choice(locations),
            notifications=True,
            welcome_seen=True,
            is_admin=False,
            date_created=datetime.utcnow() - timedelta(days=random.randint(30, 90))
        )
        # Log that they skipped and then resumed
        log_test_event(user.id, "user_skipped_profile", {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(30, 60))).isoformat()})
        log_test_event(user.id, "user_resumed_profile", {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 20))).isoformat()})
    
    db.session.add(user)
    db.session.flush()  # To get the user ID
    
    return user

def create_tournament_participation(user, participation_type, future_tournaments, upcoming_tournaments):
    """Create tournament participation based on specified type"""
    if participation_type == "none":
        # User doesn't attend any tournaments
        return []
    
    user_tournaments = []
    
    if participation_type == "upcoming":
        # Ensure at least one upcoming tournament (within 9 days)
        if upcoming_tournaments:
            num_upcoming = random.randint(1, min(2, len(upcoming_tournaments)))
            selected_upcoming = random.sample(upcoming_tournaments, num_upcoming)
            
            for tournament in selected_upcoming:
                session_type = random.choice(["day_only", "night_only", "both", "none"])
                session_label = get_session_selections(tournament, session_type)
                
                ut = UserTournament(
                    user_id=user.id,
                    tournament_id=tournament.id,
                    session_label=session_label,
                    attending=True,
                    attendance_type='attending',
                    open_to_meet=random.choice([True, False]),
                    wants_to_meet=random.choice([True, False]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 7))
                )
                
                db.session.add(ut)
                user_tournaments.append(ut)
    
    # Add other future tournaments if needed
    available_tournaments = [t for t in future_tournaments if t not in (upcoming_tournaments or [])]
    
    if available_tournaments:
        num_tournaments = random.randint(0, min(3, len(available_tournaments)))
        if participation_type == "limited" and num_tournaments == 0:
            num_tournaments = 1  # Ensure at least one tournament for "limited" type
        
        if num_tournaments > 0:
            selected_tournaments = random.sample(available_tournaments, num_tournaments)
            
            for tournament in selected_tournaments:
                session_type = random.choice(["day_only", "night_only", "both", "none"])
                session_label = get_session_selections(tournament, session_type)
                
                # Randomize attendance type
                if session_label:
                    attending = True
                    attendance_type = random.choice(['attending', 'maybe'])
                else:
                    # If no sessions selected, sometimes mark as not attending
                    attending = random.choice([True, False])
                    attendance_type = 'attending' if attending else random.choice(['attending', 'maybe'])
                
                ut = UserTournament(
                    user_id=user.id,
                    tournament_id=tournament.id,
                    session_label=session_label,
                    attending=attending,
                    attendance_type=attendance_type,
                    open_to_meet=random.choice([True, False]),
                    wants_to_meet=random.choice([True, False]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                
                db.session.add(ut)
                user_tournaments.append(ut)
                
                # Sometimes log a session update event
                if random.random() < 0.4:
                    log_test_event(
                        user.id, 
                        "user_updated_sessions", 
                        {
                            "tournament_id": tournament.id,
                            "tournament_name": tournament.name,
                            "previous_sessions": "",
                            "new_sessions": session_label
                        }
                    )
    
    return user_tournaments

def create_meetup_variation(user, user_tournaments, variation_type):
    """Create meetup preference variation"""
    if not user_tournaments:
        return
    
    # Pick a random tournament to apply the meetup preference
    tournament = random.choice(user_tournaments)
    
    if variation_type == "opted_in":
        # User opted in to meetups
        tournament.wants_to_meet = True
        tournament.open_to_meet = True
        log_test_event(
            user.id, 
            "wants_to_meet_enabled", 
            {
                "tournament_id": tournament.tournament_id,
                "tournament_name": Tournament.query.get(tournament.tournament_id).name
            }
        )
    elif variation_type == "opted_out":
        # User initially opted in, then opted out
        tournament.wants_to_meet = False
        tournament.open_to_meet = False
        
        # Log the opt-in and opt-out events with appropriate timestamps
        log_test_event(
            user.id, 
            "wants_to_meet_enabled", 
            {
                "tournament_id": tournament.tournament_id,
                "tournament_name": Tournament.query.get(tournament.tournament_id).name,
                "timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 15))).isoformat()
            }
        )
        
        log_test_event(
            user.id, 
            "wants_to_meet_disabled", 
            {
                "tournament_id": tournament.tournament_id,
                "tournament_name": Tournament.query.get(tournament.tournament_id).name
            }
        )
    elif variation_type == "untouched":
        # Default state, user never touched meetup options
        tournament.wants_to_meet = random.choice([True, False])
        tournament.open_to_meet = random.choice([True, False])
    
    db.session.flush()

def create_lanyard_variation(user, variation_type):
    """Create lanyard order variation"""
    if variation_type == "none":
        # User not eligible for lanyard
        user.lanyard_ordered = False
        user.lanyard_sent = False
        return
    
    # For all other types, user is at least eligible
    user.lanyard_ordered = True
    
    if variation_type == "eligible_not_visited":
        # User is eligible but never visited order page
        log_test_event(
            user.id, 
            "lanyard_order_eligible",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 15))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_abandoned",
            {"reason": "never_visited"}
        )
    elif variation_type == "submitted_address":
        # User submitted a shipping address
        log_test_event(
            user.id, 
            "lanyard_order_eligible",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(10, 20))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_prompt_shown",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(8, 18))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_order_started",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 15))).isoformat()}
        )
        
        # Create the shipping address
        create_shipping_address(user)
        
        log_test_event(
            user.id, 
            "shipping_address_submitted",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 10))).isoformat()}
        )
    elif variation_type == "sent":
        # Lanyard was sent
        user.lanyard_sent = True
        user.lanyard_sent_date = datetime.utcnow() - timedelta(days=random.randint(1, 10))
        
        # Create the shipping address
        create_shipping_address(user)
        
        # Log the full lanyard lifecycle
        log_test_event(
            user.id, 
            "lanyard_order_eligible",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(20, 30))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_prompt_shown",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(15, 25))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_order_started",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(10, 20))).isoformat()}
        )
        log_test_event(
            user.id, 
            "shipping_address_submitted",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 15))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_marked_sent",
            {
                "admin_id": 1,
                "timestamp": user.lanyard_sent_date.isoformat()
            }
        )
    elif variation_type == "address_error":
        # User had address submission error
        log_test_event(
            user.id, 
            "lanyard_order_eligible",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(10, 20))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_prompt_shown",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(8, 18))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_order_started",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 15))).isoformat()}
        )
        
        # Create the address with errors
        create_shipping_address(user, with_errors=True)
        
        log_test_event(
            user.id, 
            "lanyard_error_submission",
            {
                "error": "incomplete_address",
                "timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 10))).isoformat()
            }
        )
    elif variation_type == "skipped":
        # User skipped entering address
        log_test_event(
            user.id, 
            "lanyard_order_eligible",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(10, 20))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_prompt_shown",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(8, 18))).isoformat()}
        )
        log_test_event(
            user.id, 
            "lanyard_order_started",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 15))).isoformat()}
        )
        log_test_event(
            user.id, 
            "shipping_address_skipped",
            {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 10))).isoformat()}
        )
    
    db.session.flush()

def create_email_events(user, event_types):
    """Create email-related events for the user"""
    for event_type in event_types:
        if event_type == "welcome":
            log_test_event(
                user.id,
                "welcome_email_sent",
                {
                    "email": user.email,
                    "timestamp": (datetime.utcnow() - timedelta(days=random.randint(30, 60))).isoformat()
                }
            )
        elif event_type == "reminder":
            # Find a tournament they're attending
            ut = UserTournament.query.filter_by(user_id=user.id, attending=True).first()
            if ut:
                tournament = Tournament.query.get(ut.tournament_id)
                log_test_event(
                    user.id,
                    "reminder_email_sent",
                    {
                        "email": user.email,
                        "tournament_id": tournament.id,
                        "tournament_name": tournament.name,
                        "tournament_date": tournament.start_date.isoformat(),
                        "timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 15))).isoformat()
                    }
                )
        elif event_type == "meetup":
            # Find a tournament where they want to meet others
            ut = UserTournament.query.filter_by(user_id=user.id, wants_to_meet=True).first()
            if ut:
                tournament = Tournament.query.get(ut.tournament_id)
                log_test_event(
                    user.id,
                    "meetup_email_sent",
                    {
                        "email": user.email,
                        "tournament_id": tournament.id,
                        "tournament_name": tournament.name,
                        "meetup_details": "Meet at the main entrance at 10 AM",
                        "timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 7))).isoformat()
                    }
                )
        elif event_type == "recap":
            # Use a past tournament or one they're attending
            ut = UserTournament.query.filter_by(user_id=user.id).first()
            if ut:
                tournament = Tournament.query.get(ut.tournament_id)
                log_test_event(
                    user.id,
                    "post_event_recap_sent",
                    {
                        "email": user.email,
                        "tournament_id": tournament.id,
                        "tournament_name": tournament.name,
                        "timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 5))).isoformat()
                    }
                )
        elif event_type == "lanyard_shipped":
            if user.lanyard_sent:
                log_test_event(
                    user.id,
                    "lanyard_shipped_email_sent",
                    {
                        "email": user.email,
                        "shipping_date": user.lanyard_sent_date.isoformat() if user.lanyard_sent_date else datetime.utcnow().isoformat(),
                        "timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 5))).isoformat()
                    }
                )
    
    db.session.flush()

def create_past_tournaments_variation(user, variation_type, past_tournaments):
    """Create past tournament variation for a user"""
    if not past_tournaments:
        return
    
    available_tournaments = past_tournaments.copy()
    
    if variation_type == "few":
        # User added 1-3 past tournaments
        count = random.randint(1, min(3, len(available_tournaments)))
        selected = random.sample(available_tournaments, count)
        
        for tournament in selected:
            past = UserPastTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(past)
            
            log_test_event(
                user.id,
                "past_tournament_added",
                {
                    "tournament_id": tournament.id,
                    "tournament_name": tournament.name
                }
            )
    
    elif variation_type == "removed":
        # User added and then removed some tournaments
        count = random.randint(3, min(5, len(available_tournaments)))
        selected = random.sample(available_tournaments, count)
        
        # Add all selected tournaments
        for tournament in selected:
            past = UserPastTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                created_at=datetime.utcnow() - timedelta(days=random.randint(10, 40))
            )
            db.session.add(past)
            
            log_test_event(
                user.id,
                "past_tournament_added",
                {
                    "tournament_id": tournament.id,
                    "tournament_name": tournament.name,
                    "timestamp": (datetime.utcnow() - timedelta(days=random.randint(10, 40))).isoformat()
                }
            )
        
        # Remove 1-2 of them
        to_remove = random.sample(selected, random.randint(1, min(2, len(selected))))
        for tournament in to_remove:
            # Don't actually remove from database for this test data
            # Instead just log that they were removed
            log_test_event(
                user.id,
                "past_tournament_removed",
                {
                    "tournament_id": tournament.id,
                    "tournament_name": tournament.name
                }
            )
    
    elif variation_type == "many":
        # User added 5+ past tournaments
        count = min(random.randint(5, 10), len(available_tournaments))
        selected = random.sample(available_tournaments, count)
        
        for tournament in selected:
            past = UserPastTournament(
                user_id=user.id,
                tournament_id=tournament.id,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 90))
            )
            db.session.add(past)
        
        # Log a special event for adding multiple past events
        log_test_event(
            user.id,
            "user_added_multiple_past_events",
            {
                "count": count
            }
        )
    
    db.session.flush()

def create_urgent_lanyard_user(future_tournaments, upcoming_tournaments):
    """Create a user that will qualify for the urgent lanyard alert"""
    # Create a user
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    email = get_random_email(first_name, last_name)
    
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        name=f"{first_name} {last_name}",
        password_hash=generate_password_hash(TEST_PASSWORD),
        location=random.choice(locations),
        lanyard_ordered=True,  # Must have ordered a lanyard
        lanyard_sent=False,    # Must not have been sent
        notifications=True,
        welcome_seen=True,
        is_admin=False,
        date_created=datetime.utcnow() - timedelta(days=random.randint(10, 30))
    )
    
    db.session.add(user)
    db.session.flush()
    
    # Create shipping address
    create_shipping_address(user)
    
    # Add tournament attendance for upcoming tournaments (within 9 days)
    if upcoming_tournaments:
        # Randomly select 1-2 upcoming tournaments
        num_tournaments = random.randint(1, min(2, len(upcoming_tournaments)))
        selected_tournaments = random.sample(upcoming_tournaments, num_tournaments)
        
        for tournament in selected_tournaments:
            # Create attendance with sessions selected
            session_label = get_session_selections(tournament, "both")
            
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
    
    # Log lanyard events
    log_test_event(
        user.id, 
        "lanyard_order_eligible",
        {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(5, 10))).isoformat()}
    )
    log_test_event(
        user.id, 
        "lanyard_prompt_shown",
        {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(3, 8))).isoformat()}
    )
    log_test_event(
        user.id, 
        "lanyard_order_started",
        {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 5))).isoformat()}
    )
    log_test_event(
        user.id, 
        "shipping_address_submitted",
        {"timestamp": (datetime.utcnow() - timedelta(days=random.randint(1, 3))).isoformat()}
    )
    
    return user

def create_comprehensive_test_users():
    """Create comprehensive test users with various permutations"""
    print(f"Creating {NUM_USERS} comprehensive test users...")
    
    users_created = []
    admin_user = None
    
    with app.app_context():
        # Get tournament data first
        all_tournaments = get_all_tournaments()
        future_tournaments = get_future_tournaments()
        upcoming_tournaments = get_tournaments_within_days(9)
        past_tournaments = get_past_tournaments()
        
        if not all_tournaments:
            print("No tournaments found in the database. Please import tournaments first.")
            return []
        
        print(f"Found {len(all_tournaments)} total tournaments")
        print(f"Found {len(future_tournaments)} future tournaments")
        print(f"Found {len(upcoming_tournaments)} upcoming tournaments (next 9 days)")
        print(f"Found {len(past_tournaments)} past tournaments")
        
        # First create the required urgent lanyard users (at least 3)
        urgent_users = []
        for i in range(3):
            print(f"Creating urgent lanyard user {i+1}/3...")
            user = create_urgent_lanyard_user(future_tournaments, upcoming_tournaments)
            urgent_users.append(user)
            users_created.append((user.email, TEST_PASSWORD))
        
        # Create remaining users with various permutations
        remaining_users = NUM_USERS - len(urgent_users)
        
        profile_types = ["complete", "skipped", "resumed"]
        tournament_types = ["none", "limited", "upcoming"]
        meetup_types = ["opted_in", "opted_out", "untouched"]
        lanyard_types = ["none", "eligible_not_visited", "submitted_address", "sent", "address_error", "skipped"]
        past_tournament_types = ["few", "removed", "many"]
        
        # Email events to distribute
        email_events = [
            ["welcome"],
            ["welcome", "reminder"],
            ["welcome", "reminder", "meetup"],
            ["welcome", "reminder", "recap"],
            ["welcome", "lanyard_shipped"]
        ]
        
        for i in range(remaining_users):
            try:
                # Randomly select permutation types
                profile_type = random.choice(profile_types)
                tournament_type = random.choice(tournament_types)
                meetup_type = random.choice(meetup_types)
                lanyard_type = random.choice(lanyard_types)
                past_tournament_type = random.choice(past_tournament_types)
                email_event_set = random.choice(email_events)
                
                print(f"Creating user {i+1}/{remaining_users} with profile={profile_type}, tournaments={tournament_type}, meetup={meetup_type}, lanyard={lanyard_type}, past={past_tournament_type}")
                
                # Create the user with profile variation
                user = create_profile_variation(profile_type)
                
                # Make the first user an admin
                if i == 0:
                    user.is_admin = True
                    admin_user = user
                
                # Create tournament participation
                user_tournaments = create_tournament_participation(
                    user, 
                    tournament_type, 
                    future_tournaments, 
                    upcoming_tournaments
                )
                
                # Create meetup variation if user has tournaments
                if user_tournaments:
                    create_meetup_variation(user, user_tournaments, meetup_type)
                
                # Create lanyard variation
                create_lanyard_variation(user, lanyard_type)
                
                # Create past tournament variation
                if past_tournaments:
                    create_past_tournaments_variation(user, past_tournament_type, past_tournaments)
                
                # Create email events
                create_email_events(user, email_event_set)
                
                # Add to users created list
                users_created.append((user.email, TEST_PASSWORD))
                
            except Exception as e:
                print(f"Error creating user {i+1}: {str(e)}")
                continue
        
        # Commit all changes to the database
        try:
            db.session.commit()
            print(f"Successfully committed {len(users_created)} test users to the database")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {str(e)}")
            return []
        
        # Print admin credentials
        if admin_user:
            print("\nADMIN CREDENTIALS:")
            print(f"Email: {admin_user.email}")
            print(f"Password: {TEST_PASSWORD}")
        
        # Print stats summary
        print("\nTest User Creation Summary:")
        print(f"Total users created: {len(users_created)}")
        print(f"Urgent lanyard users: {len(urgent_users)}")
        print(f"Users with lanyards ordered: {User.query.filter_by(lanyard_ordered=True).count()}")
        print(f"Users with lanyards sent: {User.query.filter_by(lanyard_sent=True).count()}")
        print(f"Total tournament registrations: {UserTournament.query.count()}")
        print(f"Total past tournament entries: {UserPastTournament.query.count()}")
        print(f"Total shipping addresses: {ShippingAddress.query.count()}")
        print(f"Total events logged: {Event.query.count()}")
        
        return users_created

if __name__ == "__main__":
    create_comprehensive_test_users()