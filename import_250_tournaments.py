#!/usr/bin/env python3
"""
Import ATP/WTA 250 tournaments from final_full_250_atp_wta.json
Only adds tournaments that don't already exist in the database.
"""

import json
import datetime
from app import app, db
from models import Tournament

def import_250_tournaments():
    """Import ATP/WTA 250 tournaments without affecting existing tournaments"""
    print("Starting ATP/WTA 250 tournament import...")
    
    try:
        # Load the tournaments from the JSON file
        with open('final_full_250_atp_wta.json', 'r') as f:
            tournaments_data = json.load(f)
        
        print(f"Found {len(tournaments_data)} tournaments in file")
        
        # Track the number of new tournaments added
        new_count = 0
        existing_count = 0
        
        # Process each tournament
        for t_data in tournaments_data:
            # Check if the tournament already exists
            existing = Tournament.query.get(t_data['id'])
            
            if existing:
                existing_count += 1
                print(f"Tournament already exists: {existing.name}")
                continue
            
            # Convert date strings to date objects
            start_date = datetime.datetime.strptime(t_data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(t_data['end_date'], '%Y-%m-%d').date()
            
            # Create the new tournament
            tournament = Tournament(
                id=t_data['id'],
                slug=t_data['id'],  # Use the id as the slug
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
            print(f"Added new tournament: {tournament.name} ({tournament.city}, {tournament.country})")
        
        # Commit the changes
        db.session.commit()
        print(f"\nImport complete!")
        print(f"- Added {new_count} new tournaments")
        print(f"- Skipped {existing_count} existing tournaments")
        print(f"- Total tournaments in file: {len(tournaments_data)}")
        
        # Verify the total count in database
        total_tournaments = Tournament.query.count()
        print(f"- Total tournaments now in database: {total_tournaments}")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error importing tournaments: {str(e)}")
        return False

if __name__ == "__main__":
    with app.app_context():
        import_250_tournaments()