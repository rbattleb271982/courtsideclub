import json
import datetime
from app import app, db
from models import Tournament

def import_tournaments():
    print("Starting tournament import...")
    
    try:
        # Load the tournaments from the JSON file
        with open('tournaments.json', 'r') as f:
            tournaments_data = json.load(f)
        
        # Track the number of new tournaments added
        new_count = 0
        
        # Process each tournament
        for t_data in tournaments_data:
            # Check if the tournament already exists
            existing = Tournament.query.get(t_data['id'])
            
            if existing:
                print(f"Tournament {t_data['id']} already exists, skipping.")
                continue
            
            # Convert date strings to date objects
            start_date = datetime.datetime.strptime(t_data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(t_data['end_date'], '%Y-%m-%d').date()
            
            # Create the new tournament
            tournament = Tournament(
                id=t_data['id'],
                name=t_data['name'],
                start_date=start_date,
                end_date=end_date,
                city=t_data['city'],
                country=t_data['country'],
                event_type=t_data['event_type'],
                tour_type=t_data['tour_type'],
                sessions=t_data.get('sessions', [])
            )
            
            # Add it to the database
            db.session.add(tournament)
            new_count += 1
            print(f"Added tournament: {tournament.name}")
        
        # Commit the changes
        db.session.commit()
        print(f"Import complete. Added {new_count} new tournaments.")
    
    except Exception as e:
        db.session.rollback()
        print(f"Error importing tournaments: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    with app.app_context():
        import_tournaments()