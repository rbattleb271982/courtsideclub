"""
Create remaining test users efficiently using bulk operations
"""
import logging
import random
from app import app, db
from models import User, Tournament, UserTournament, ShippingAddress
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_bulk_users(target_count=750):
    """Create test users efficiently using bulk operations"""
    
    with app.app_context():
        current_count = User.query.filter_by(test_user=True).count()
        remaining = target_count - current_count
        
        if remaining <= 0:
            logger.info(f"Already have {current_count} test users (target: {target_count})")
            return True
        
        logger.info(f"Creating {remaining} more users to reach {target_count} total")
        
        # Get tournaments once
        tournaments = Tournament.query.all()
        tournament_ids = [t.id for t in tournaments]
        
        # Names and domains for variation
        names = [(f"User{i}", f"Test{i}") for i in range(1, remaining + 1)]
        
        try:
            batch_size = 100
            created_total = 0
            
            while created_total < remaining:
                current_batch = min(batch_size, remaining - created_total)
                users_batch = []
                tournaments_batch = []
                addresses_batch = []
                
                # Create users batch
                for i in range(current_batch):
                    user_num = created_total + i + 1
                    first_name = f"TestUser{user_num}"
                    last_name = f"LastName{user_num}"
                    email = f"testuser{user_num}@test{random.randint(1,5)}.com"
                    
                    user = User(
                        email=email,
                        password_hash=generate_password_hash("TestPass123"),
                        first_name=first_name,
                        last_name=last_name,
                        name=f"{first_name} {last_name}",
                        notifications=True,
                        welcome_seen=True,
                        test_user=True
                    )
                    
                    users_batch.append(user)
                
                # Add users to get IDs
                db.session.add_all(users_batch)
                db.session.flush()
                
                # Create tournament relationships
                for user in users_batch:
                    # 3-6 tournaments per user
                    num_tournaments = random.randint(3, 6)
                    selected_tournaments = random.sample(tournament_ids, min(num_tournaments, len(tournament_ids)))
                    
                    has_lanyard = False
                    
                    for tournament_id in selected_tournaments:
                        attending = random.choice([True, False])
                        
                        # Simple session selection
                        session_label = None
                        if attending:
                            sessions = random.choice([
                                "Day Session", "Night Session", "Day Session,Night Session",
                                "Morning Session", "Afternoon Session"
                            ])
                            session_label = sessions
                            has_lanyard = True
                        
                        user_tournament = UserTournament(
                            user_id=user.id,
                            tournament_id=tournament_id,
                            attending=attending,
                            open_to_meet=random.choice([True, False]),
                            wants_to_meet=attending and random.choice([True, False]),
                            session_label=session_label
                        )
                        
                        tournaments_batch.append(user_tournament)
                    
                    # Create shipping address if has lanyard
                    if has_lanyard:
                        user.lanyard_ordered = True
                        
                        address = ShippingAddress(
                            user_id=user.id,
                            name=f"{user.first_name} {user.last_name}",
                            address1=f"{random.randint(100, 999)} Test St",
                            city="Test City",
                            state="NY",
                            zip_code=f"{random.randint(10000, 99999)}",
                            country="USA"
                        )
                        
                        addresses_batch.append(address)
                
                # Add all tournaments and addresses
                db.session.add_all(tournaments_batch)
                db.session.add_all(addresses_batch)
                
                # Commit this batch
                db.session.commit()
                
                created_total += current_batch
                logger.info(f"Created batch of {current_batch} users. Total: {current_count + created_total}")
            
            logger.info(f"Successfully created {created_total} users")
            return True
            
        except Exception as e:
            logger.error(f"Error creating users: {str(e)}")
            db.session.rollback()
            return False

def verify_results():
    """Verify the final results"""
    with app.app_context():
        test_users = User.query.filter_by(test_user=True).count()
        attending = UserTournament.query.filter_by(attending=True).count()
        lanyard_orders = User.query.filter_by(lanyard_ordered=True, test_user=True).count()
        shipping_addresses = ShippingAddress.query.count()
        
        print(f"Users where test_user = True: {test_users}")
        print(f"UserTournaments where attending = True: {attending}")
        print(f"Users with lanyard_ordered = True: {lanyard_orders}")
        print(f"Total shipping addresses: {shipping_addresses}")
        
        # Sample session selections
        print("\nSample user tournament session selections:")
        samples = UserTournament.query.filter(
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        ).limit(3).all()
        
        for i, ut in enumerate(samples, 1):
            user = User.query.get(ut.user_id)
            tournament = Tournament.query.get(ut.tournament_id)
            print(f"{i}. {user.name} -> {tournament.name}: {ut.session_label}")

if __name__ == "__main__":
    success = create_bulk_users()
    if success:
        verify_results()
        print("\n750 test users created successfully!")
    else:
        print("Failed to create test users")