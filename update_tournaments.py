import json
import datetime
import logging
import os
from app import app, db
from models import Tournament

def update_tournaments_from_file(filename):
    """Import tournaments from a specific JSON file"""
    print(f"Starting tournament import from {filename}...")
    
    try:
        # Check if file exists
        if not os.path.exists(filename):
            print(f"Error: File {filename} not found")
            return False
        
        # Load the tournaments from the JSON file
        with open(filename, 'r') as f:
            tournaments_data = json.load(f)
        
        # Track the number of new tournaments added
        new_count = 0
        updated_count = 0
        
        # Process each tournament
        for t_data in tournaments_data:
            # Check if the tournament already exists
            existing = Tournament.query.get(t_data['id'])
            
            # Convert date strings to date objects
            start_date = datetime.datetime.strptime(t_data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(t_data['end_date'], '%Y-%m-%d').date()
            
            if existing:
                # Update the existing tournament
                existing.name = t_data['name']
                existing.start_date = start_date
                existing.end_date = end_date
                existing.city = t_data['city']
                existing.country = t_data['country']
                existing.event_type = t_data['event_type']
                existing.tour_type = t_data['tour_type']
                existing.sessions = t_data.get('sessions', [])
                updated_count += 1
                print(f"Updated tournament: {existing.name}")
            else:
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
        print(f"Import complete. Added {new_count} new tournaments, updated {updated_count} existing ones.")
    
    except Exception as e:
        db.session.rollback()
        print(f"Error importing tournaments: {str(e)}")
        logging.error(f"Error importing tournaments: {str(e)}")
        return False
    
    return True

def clean_tournaments():
    """Remove all tournaments from the database"""
    try:
        count = Tournament.query.count()
        Tournament.query.delete()
        db.session.commit()
        print(f"Removed {count} tournaments from the database.")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error cleaning tournaments: {str(e)}")
        return False

if __name__ == "__main__":
    with app.app_context():
        # Option to clean all tournaments before import
        # Uncomment the next line to clear all tournaments before importing new ones
        clean_tournaments()
        
        # Update from the full tournaments list
        update_tournaments_from_file('full_tournaments.json')