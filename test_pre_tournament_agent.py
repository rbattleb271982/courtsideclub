"""
Test the pre-tournament reminder agent with real timing logic
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
from app import app
from models import db, Tournament, User, UserTournament
from agents.pre_tournament_reminder import run_pre_tournament_reminder_agent

def create_test_scenario():
    """Create a test scenario with tournaments in the 1-2 day window"""
    
    with app.app_context():
        try:
            print("Creating Test Scenario for Pre-Tournament Agent")
            print("=" * 55)
            
            # Set tournament dates to trigger the 1-2 day window
            today = datetime.utcnow().date()
            tomorrow = today + timedelta(days=1)
            day_after_tomorrow = today + timedelta(days=2)
            
            # Find a tournament we can modify for testing
            tournament = db.session.query(Tournament).filter(
                Tournament.name.contains('Open')
            ).first()
            
            if not tournament:
                print("No suitable tournament found for testing")
                return False
            
            # Temporarily update the tournament start date
            original_start_date = tournament.start_date
            tournament.start_date = tomorrow  # Set to tomorrow for testing
            
            print(f"Modified tournament: {tournament.name}")
            print(f"Set start date to: {tournament.start_date} (tomorrow)")
            
            # Find users with sessions for this tournament
            user_tournaments = db.session.query(UserTournament).filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.session_label != '',
                UserTournament.session_label.isnot(None)
            ).limit(3).all()
            
            print(f"Found {len(user_tournaments)} users attending this tournament")
            
            if user_tournaments:
                for ut in user_tournaments:
                    print(f"  - {ut.user.email}: {ut.session_label}")
            
            # Commit the temporary change
            db.session.commit()
            
            print("\nRunning Pre-Tournament Reminder Agent...")
            print("-" * 40)
            
            # Run the agent
            result = run_pre_tournament_reminder_agent()
            print(f"Agent result: {result}")
            
            # Restore original start date
            tournament.start_date = original_start_date
            db.session.commit()
            
            print(f"\nRestored tournament start date to: {original_start_date}")
            
            return True
            
        except Exception as e:
            print(f"Error in test scenario: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_agent_timing_logic():
    """Test the agent's timing logic without sending emails"""
    
    with app.app_context():
        try:
            print("\nTesting Agent Timing Logic")
            print("=" * 35)
            
            today = datetime.utcnow().date()
            
            # Test tournaments at different day intervals
            test_days = [0, 1, 2, 3, 7, 14]
            
            for days in test_days:
                test_date = today + timedelta(days=days)
                
                tournaments = db.session.query(Tournament).filter(
                    Tournament.start_date == test_date
                ).count()
                
                print(f"Day +{days} ({test_date}): {tournaments} tournaments")
                
                if days in [1, 2]:
                    print(f"  ✅ This would trigger pre-tournament emails")
                else:
                    print(f"  ⏸️  Outside the 1-2 day window")
            
            return True
            
        except Exception as e:
            print(f"Error testing timing logic: {str(e)}")
            return False

if __name__ == "__main__":
    test_agent_timing_logic()
    create_test_scenario()