"""
Direct database query to capture tournament session data
"""
from app import app, db
from models import Tournament, User, UserTournament
import json

def debug_tournament_data():
    """Debug tournament session data directly from database"""
    with app.app_context():
        # Get Roland Garros tournament
        tournament = Tournament.query.filter_by(slug='roland_garros').first()
        
        print("="*80)
        print("DIRECT DATABASE QUERY RESULTS:")
        print(f"Tournament found: {tournament is not None}")
        
        if tournament:
            print(f"Tournament name: {tournament.name}")
            print(f"Tournament.sessions raw: {tournament.sessions}")
            print(f"Tournament.sessions type: {type(tournament.sessions)}")
            
            if tournament.sessions:
                print(f"Sessions length: {len(tournament.sessions)}")
                for i, session in enumerate(tournament.sessions):
                    print(f"Session {i}: {session}")
            else:
                print("Sessions is empty or None")
        
        # Get test user
        user = User.query.filter_by(email='richardbattlebaxter@gmail.com').first()
        print(f"User found: {user is not None}")
        
        if user and tournament:
            # Get user tournament record
            user_tournament = UserTournament.query.filter_by(
                user_id=user.id,
                tournament_id=tournament.id
            ).first()
            
            print(f"UserTournament record: {user_tournament is not None}")
            if user_tournament:
                print(f"User attending: {user_tournament.attending}")
                print(f"Session label: {user_tournament.session_label}")
                print(f"Wants to meet: {user_tournament.wants_to_meet}")
        
        # Count total attending users
        total_attending = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True
        ).count()
        
        total_meeting = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            wants_to_meet=True
        ).count()
        
        print(f"Total users attending: {total_attending}")
        print(f"Total users open to meeting: {total_meeting}")
        print("="*80)

if __name__ == '__main__':
    debug_tournament_data()