"""
Test script to send the enhanced Post-Tournament Follow-Up email
"""

import os
import sys
from datetime import datetime, timedelta
from services.email import send_post_tournament_followup_email
from models import db, User, Tournament, UserTournament
from app import app

def test_post_tournament_email():
    """Send a test post-tournament follow-up email with enhanced design"""
    with app.app_context():
        try:
            # Find a test tournament and user
            test_tournament = Tournament.query.filter_by(name='Australian Open').first()
            if not test_tournament:
                test_tournament = Tournament.query.first()
            
            if not test_tournament:
                print("No tournaments found in database")
                return False
            
            # Find a test user with tournament registration
            test_user = User.query.filter_by(email='testuser1@example.com').first()
            if not test_user:
                test_user = User.query.first()
            
            if not test_user:
                print("No users found in database")
                return False
            
            # Find or create user tournament registration
            user_tournament = UserTournament.query.filter_by(
                user_id=test_user.id,
                tournament_id=test_tournament.id,
                attending=True
            ).first()
            
            if not user_tournament:
                # Create a test registration
                user_tournament = UserTournament(
                    user_id=test_user.id,
                    tournament_id=test_tournament.id,
                    attending=True,
                    session_label="Day 1, Night 2, Day 3",
                    open_to_meet=True,
                    wants_to_meet=True
                )
                db.session.add(user_tournament)
                db.session.commit()
                print(f"Created test tournament registration for {test_user.email}")
            
            # Send the enhanced post-tournament follow-up email
            print(f"Sending enhanced post-tournament follow-up email for:")
            print(f"- User: {test_user.first_name or 'Test User'} ({test_user.email})")
            print(f"- Tournament: {test_tournament.name}")
            print(f"- Sessions: {user_tournament.session_label}")
            print(f"- Sending to: richardbattlebaxter@gmail.com")
            
            success = send_post_tournament_followup_email(
                user_id=test_user.id,
                tournament_id=test_tournament.id
            )
            
            if success:
                print("✅ Enhanced post-tournament follow-up email sent successfully!")
                return True
            else:
                print("❌ Failed to send enhanced email")
                return False
                
        except Exception as e:
            print(f"Error sending test email: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_post_tournament_email()
    if success:
        print("\nTest completed successfully. Check richardbattlebaxter@gmail.com for the enhanced email.")
    else:
        print("\nTest failed. Check the error messages above.")