"""
Test script for the new pre-tournament reminder email system
"""

import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
from app import app
from models import db, User, Tournament, UserTournament
from services.pre_tournament_email import send_pre_tournament_reminder_email, generate_pre_tournament_email_html

def test_pre_tournament_email():
    """Test the pre-tournament email generation and sending"""
    
    with app.app_context():
        try:
            print("Testing Pre-Tournament Email System")
            print("=" * 50)
            
            # Find a user with tournament registrations
            user_tournament = db.session.query(UserTournament).filter(
                UserTournament.attending == True,
                UserTournament.session_label != '',
                UserTournament.session_label.isnot(None)
            ).join(User).join(Tournament).first()
            
            if not user_tournament:
                print("❌ No users found with tournament registrations and sessions")
                return False
            
            user = user_tournament.user
            tournament = user_tournament.tournament
            
            print(f"📧 Testing with:")
            print(f"   User: {user.email}")
            print(f"   Tournament: {tournament.name}")
            print(f"   Sessions: {user_tournament.session_label}")
            print(f"   Start Date: {tournament.start_date}")
            print()
            
            # Test HTML generation
            print("🔧 Generating HTML content...")
            html_content = generate_pre_tournament_email_html(user.id, tournament.id)
            
            if not html_content:
                print("❌ Failed to generate HTML content")
                return False
            
            print(f"✅ HTML generated successfully ({len(html_content)} characters)")
            
            # Preview HTML structure
            if "Your Selected Sessions" in html_content:
                print("✅ Sessions section found in HTML")
            if "Tournament Details" in html_content:
                print("✅ Tournament details section found in HTML")
            if "Tennis is better together" in html_content:
                print("✅ Footer found in HTML")
            
            print()
            
            # Test email sending
            print("📤 Sending test email...")
            success = send_pre_tournament_reminder_email(
                user_id=user.id,
                tournament_id=tournament.id,
                debug_email_override="richardbattlebaxter@gmail.com"
            )
            
            if success:
                print("✅ Test email sent successfully to richardbattlebaxter@gmail.com")
                print(f"📧 Subject: 🎾 {tournament.name} starts soon — you're all set!")
                print()
                print("🎯 Check your email for:")
                print("   • Rich branded HTML design")
                print("   • Parsed session information with dates/times")
                print("   • Attendee counts for each session")
                print("   • Meetup compatibility information")
                print("   • Lanyard status messaging")
                print("   • Tournament location and schedule links")
                print("   • Professional footer with unsubscribe links")
                return True
            else:
                print("❌ Failed to send test email")
                return False
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def test_session_parsing():
    """Test the session parsing logic"""
    
    with app.app_context():
        try:
            print("\nTesting Session Parsing Logic")
            print("=" * 40)
            
            from services.pre_tournament_email import parse_session_label
            
            # Test data
            test_cases = [
                ("Day 1, Night 2", datetime(2025, 6, 15)),
                ("Day 3", datetime(2025, 7, 1)),  
                ("Night 1, Day 2, All Day 3", datetime(2025, 8, 20)),
                ("All Day 1", datetime(2025, 9, 10))
            ]
            
            for session_label, start_date in test_cases:
                print(f"\n🧪 Testing: '{session_label}' (starts {start_date.strftime('%B %d, %Y')})")
                
                sessions = parse_session_label(session_label, start_date)
                
                if sessions:
                    for session in sessions:
                        print(f"   ✅ {session['label']}")
                        print(f"      Date: {session['date']}")
                        print(f"      Time: {session['time']}")
                else:
                    print("   ❌ Failed to parse sessions")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing session parsing: {str(e)}")
            return False

if __name__ == "__main__":
    # Run tests
    test_session_parsing()
    test_pre_tournament_email()