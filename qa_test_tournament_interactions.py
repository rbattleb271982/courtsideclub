"""
QA Test Script for Tournament Interactions

This script simulates multiple users interacting with the tournament system:
- 25+ tournament/session combinations
- Mix of "Attending", "Maybe Attending", and cancellations
- Multiple users selecting the same sessions
- Lanyard orders for eligible users

Run this script to create test data for QA verification.
"""
import logging
import random
from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_test_users():
    """Get all test users for QA"""
    users = User.query.filter(
        (User.email.like('%test%@example.com')) | 
        (User.email == 'richardbattlebaxter@gmail.com')
    ).all()
    return users

def get_tournaments():
    """Get all tournaments for QA testing"""
    # Focus on upcoming tournaments
    current_tournaments = Tournament.query.all()
    return current_tournaments

def create_test_interactions():
    """Create various test interactions for QA analysis"""
    users = get_test_users()
    if not users:
        logger.error("No test users found. Please run create_qa_test_users.py first.")
        return
    
    tournaments = get_tournaments()
    if not tournaments:
        logger.error("No tournaments found in the database.")
        return
    
    logger.info(f"Found {len(users)} test users and {len(tournaments)} tournaments")
    
    # Store counts for reporting
    interaction_count = 0
    attending_count = 0
    maybe_count = 0
    lanyard_orders = 0
    
    # Create predictable overlapping tournament selections to test shared attendance
    # These tournaments will have multiple users attending the same sessions
    # Select more shared tournaments for greater testing coverage
    shared_tournaments = random.sample(tournaments, min(6, len(tournaments)))
    logger.info(f"Selected shared tournaments: {[t.name for t in shared_tournaments]}")
    
    # Create individual interactions for each user
    for user in users:
        logger.info(f"Creating interactions for user: {user.email}")
        
        # Each user will attend 3-6 tournaments with various configurations for more coverage
        user_tournament_count = random.randint(3, 6)
        
        # Make sure at least two shared tournaments are included
        user_tournaments = random.sample(shared_tournaments, min(3, len(shared_tournaments)))
        
        # Add some individual tournaments to reach desired count
        remaining_tournaments = [t for t in tournaments if t not in user_tournaments]
        if remaining_tournaments and len(user_tournaments) < user_tournament_count:
            additional_count = min(user_tournament_count - len(user_tournaments), len(remaining_tournaments))
            user_tournaments.extend(random.sample(remaining_tournaments, additional_count))
        
        # Create attendance records for each selected tournament
        for tournament in user_tournaments:
            # Decide attendance type (80% attending, 20% maybe)
            is_attending = random.random() < 0.8
            attendance_type = "attending" if is_attending else "maybe"
            
            if is_attending:
                attending_count += 1
            else:
                maybe_count += 1
                
            # Check if there's already a record
            existing = UserTournament.query.filter_by(
                user_id=user.id,
                tournament_id=tournament.id
            ).first()
            
            if existing:
                # Update existing record
                existing.attendance_type = attendance_type
                existing.attending = is_attending
                logger.info(f"Updated existing attendance record for {user.email} at {tournament.name}")
            else:
                # Create new attendance record
                new_attendance = UserTournament(
                    user_id=user.id,
                    tournament_id=tournament.id,
                    attendance_type=attendance_type,
                    attending=is_attending,
                    wants_to_meet=random.random() < 0.9  # 90% want to meet
                )
                db.session.add(new_attendance)
                logger.info(f"Created new {attendance_type} record for {user.email} at {tournament.name}")
            
            # Only select sessions for "attending" users
            if is_attending:
                # Add session selections for this tournament
                session_labels = []
                
                # Get session days from tournament data if available
                session_days_count = 5  # Default if no data available
                
                if tournament.sessions and len(tournament.sessions) > 0:
                    session_days_count = min(len(tournament.sessions), 14)  # Cap at 14 days
                
                # Select 1-3 random days
                num_days = random.randint(1, min(3, session_days_count))
                selected_days = random.sample(range(1, session_days_count + 1), num_days)
                
                for day in selected_days:
                    # Randomly choose session type (Day, Night, or both)
                    session_types = ["Day", "Night"]
                    selected_types = random.sample(session_types, random.randint(1, 2))
                    
                    for session_type in selected_types:
                        session_label = f"Day {day} - {session_type}"
                        session_labels.append(session_label)
                        interaction_count += 1
                
                # Join all session labels with commas
                sessions_str = ", ".join(session_labels)
                
                # Update the session_label in the database
                existing = UserTournament.query.filter_by(
                    user_id=user.id,
                    tournament_id=tournament.id
                ).first()
                
                if existing:
                    existing.session_label = sessions_str
                    logger.info(f"Added sessions for {user.email} at {tournament.name}: {sessions_str}")
                
            db.session.commit()
        
        # Create shipping address and lanyard orders for 5 users
        if lanyard_orders < 5 and random.random() < 0.7:
            # Check if user has at least one tournament they're attending with sessions
            attending_with_sessions = UserTournament.query.filter_by(
                user_id=user.id,
                attending=True
            ).filter(UserTournament.session_label != None).filter(UserTournament.session_label != '').first()
            
            if attending_with_sessions:
                # Set user as having ordered lanyard
                user.lanyard_ordered = True
                
                # Create shipping address if needed
                existing_address = ShippingAddress.query.filter_by(user_id=user.id).first()
                
                if not existing_address:
                    new_address = ShippingAddress(
                        user_id=user.id,
                        name=user.get_full_name(),
                        address1=f"{random.randint(100, 9999)} Main St",
                        city=random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]),
                        state=random.choice(["NY", "CA", "IL", "TX", "AZ"]),
                        zip_code=f"{random.randint(10000, 99999)}",
                        country="United States"
                    )
                    db.session.add(new_address)
                
                db.session.commit()
                lanyard_orders += 1
                logger.info(f"Created lanyard order for {user.email}")
    
    logger.info(f"QA data generation complete:")
    logger.info(f"- Total session interactions: {interaction_count}")
    logger.info(f"- Attending records: {attending_count}")
    logger.info(f"- Maybe attending records: {maybe_count}")
    logger.info(f"- Lanyard orders: {lanyard_orders}")

def cancel_some_attendances():
    """Cancel some attendances to test that functionality"""
    users = get_test_users()
    
    cancellations = 0
    
    for user in random.sample(users, 3):  # Cancel for 3 random users
        # Find an attending record
        attending_record = UserTournament.query.filter_by(
            user_id=user.id,
            attending=True
        ).first()
        
        if attending_record:
            logger.info(f"Cancelling attendance for {user.email} at {attending_record.tournament_id}")
            db.session.delete(attending_record)
            cancellations += 1
    
    db.session.commit()
    logger.info(f"Cancelled {cancellations} attendance records")

if __name__ == "__main__":
    with app.app_context():
        logger.info("Starting QA test data generation")
        create_test_interactions()
        cancel_some_attendances()
        logger.info("QA test data generation complete")