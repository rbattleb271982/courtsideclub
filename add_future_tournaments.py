"""
Add future tournaments to populate the logged-out Browse Tournaments page
"""
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("DATABASE_URL environment variable not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def add_future_tournaments():
    """Add future tournaments for the logged-out browse page"""
    
    # Get today's date for future tournaments
    today = datetime.now().date()
    
    # Future tournaments to add
    tournaments = [
        {
            'id': 'wimbledon_2025',
            'name': 'Wimbledon',
            'slug': 'wimbledon',
            'city': 'London',
            'country': 'United Kingdom',
            'start_date': today + timedelta(days=30),
            'end_date': today + timedelta(days=43),
            'event_type': 'Grand Slam',
            'tour_type': 'ATP/WTA',
            'official_url': 'https://www.wimbledon.com',
            'sessions': ['Day 1 - Day', 'Day 1 - Night', 'Day 2 - Day', 'Day 2 - Night', 'Day 3 - Day', 'Day 3 - Night', 'Day 4 - Day', 'Day 4 - Night', 'Day 5 - Day', 'Day 5 - Night', 'Day 6 - Day', 'Day 6 - Night', 'Day 7 - Day', 'Day 7 - Night', 'Day 8 - Day', 'Day 8 - Night', 'Day 9 - Day', 'Day 9 - Night', 'Day 10 - Day', 'Day 10 - Night', 'Day 11 - Day', 'Day 11 - Night', 'Day 12 - Day', 'Day 12 - Night', 'Day 13 - Day', 'Day 13 - Night', 'Day 14 - Day', 'Day 14 - Night']
        },
        {
            'id': 'us_open_2025',
            'name': 'US Open',
            'slug': 'us_open_2025',
            'city': 'New York',
            'country': 'United States',
            'start_date': today + timedelta(days=60),
            'end_date': today + timedelta(days=73),
            'event_type': 'Grand Slam',
            'tour_type': 'ATP/WTA',
            'official_url': 'https://www.usopen.org',
            'sessions': ['Day 1 - Day', 'Day 1 - Night', 'Day 2 - Day', 'Day 2 - Night', 'Day 3 - Day', 'Day 3 - Night', 'Day 4 - Day', 'Day 4 - Night', 'Day 5 - Day', 'Day 5 - Night', 'Day 6 - Day', 'Day 6 - Night', 'Day 7 - Day', 'Day 7 - Night', 'Day 8 - Day', 'Day 8 - Night', 'Day 9 - Day', 'Day 9 - Night', 'Day 10 - Day', 'Day 10 - Night', 'Day 11 - Day', 'Day 11 - Night', 'Day 12 - Day', 'Day 12 - Night', 'Day 13 - Day', 'Day 13 - Night', 'Day 14 - Day', 'Day 14 - Night']
        },
        {
            'id': 'australian_open_2026',
            'name': 'Australian Open',
            'slug': 'australian_open_2026',
            'city': 'Melbourne',
            'country': 'Australia',
            'start_date': today + timedelta(days=90),
            'end_date': today + timedelta(days=103),
            'event_type': 'Grand Slam',
            'tour_type': 'ATP/WTA',
            'official_url': 'https://www.ausopen.com',
            'sessions': ['Day 1 - Day', 'Day 1 - Night', 'Day 2 - Day', 'Day 2 - Night', 'Day 3 - Day', 'Day 3 - Night', 'Day 4 - Day', 'Day 4 - Night', 'Day 5 - Day', 'Day 5 - Night', 'Day 6 - Day', 'Day 6 - Night', 'Day 7 - Day', 'Day 7 - Night', 'Day 8 - Day', 'Day 8 - Night', 'Day 9 - Day', 'Day 9 - Night', 'Day 10 - Day', 'Day 10 - Night', 'Day 11 - Day', 'Day 11 - Night', 'Day 12 - Day', 'Day 12 - Night', 'Day 13 - Day', 'Day 13 - Night', 'Day 14 - Day', 'Day 14 - Night']
        },
        {
            'id': 'indian_wells_2025',
            'name': 'Indian Wells Masters',
            'slug': 'indian_wells_2025',
            'city': 'Indian Wells',
            'country': 'United States',
            'start_date': today + timedelta(days=120),
            'end_date': today + timedelta(days=133),
            'event_type': 'Masters 1000',
            'tour_type': 'ATP/WTA',
            'official_url': 'https://www.bnpparibasopen.com',
            'sessions': ['Day 1 - Day', 'Day 1 - Night', 'Day 2 - Day', 'Day 2 - Night', 'Day 3 - Day', 'Day 3 - Night', 'Day 4 - Day', 'Day 4 - Night', 'Day 5 - Day', 'Day 5 - Night', 'Day 6 - Day', 'Day 6 - Night', 'Day 7 - Day', 'Day 7 - Night', 'Day 8 - Day', 'Day 8 - Night', 'Day 9 - Day', 'Day 9 - Night', 'Day 10 - Day', 'Day 10 - Night', 'Day 11 - Day', 'Day 11 - Night', 'Day 12 - Day', 'Day 12 - Night', 'Day 13 - Day', 'Day 13 - Night', 'Day 14 - Day', 'Day 14 - Night']
        },
        {
            'id': 'miami_open_2025',
            'name': 'Miami Open',
            'slug': 'miami_open_2025',
            'city': 'Miami',
            'country': 'United States',
            'start_date': today + timedelta(days=150),
            'end_date': today + timedelta(days=163),
            'event_type': 'Masters 1000',
            'tour_type': 'ATP/WTA',
            'official_url': 'https://www.miamiopen.com',
            'sessions': ['Day 1 - Day', 'Day 1 - Night', 'Day 2 - Day', 'Day 2 - Night', 'Day 3 - Day', 'Day 3 - Night', 'Day 4 - Day', 'Day 4 - Night', 'Day 5 - Day', 'Day 5 - Night', 'Day 6 - Day', 'Day 6 - Night', 'Day 7 - Day', 'Day 7 - Night', 'Day 8 - Day', 'Day 8 - Night', 'Day 9 - Day', 'Day 9 - Night', 'Day 10 - Day', 'Day 10 - Night', 'Day 11 - Day', 'Day 11 - Night', 'Day 12 - Day', 'Day 12 - Night', 'Day 13 - Day', 'Day 13 - Night', 'Day 14 - Day', 'Day 14 - Night']
        }
    ]
    
    for tournament in tournaments:
        # Check if tournament already exists
        existing = session.execute(
            text("SELECT id FROM tournaments WHERE slug = :slug"),
            {'slug': tournament['slug']}
        ).fetchone()
        
        if not existing:
            # Insert new tournament
            query = text("""
                INSERT INTO tournaments (id, name, slug, city, country, start_date, end_date, event_type, tour_type, external_url, sessions)
                VALUES (:id, :name, :slug, :city, :country, :start_date, :end_date, :event_type, :tour_type, :external_url, :sessions)
            """)
            
            session.execute(query, {
                'id': tournament['id'],
                'name': tournament['name'],
                'slug': tournament['slug'],
                'city': tournament['city'],
                'country': tournament['country'],
                'start_date': tournament['start_date'],
                'end_date': tournament['end_date'],
                'event_type': tournament['event_type'],
                'tour_type': tournament['tour_type'],
                'external_url': tournament['official_url'],
                'sessions': tournament['sessions']
            })
            
            print(f"Added tournament: {tournament['name']}")
        else:
            print(f"Tournament already exists: {tournament['name']}")
    
    session.commit()
    print("Future tournaments added successfully!")

if __name__ == "__main__":
    add_future_tournaments()
    session.close()