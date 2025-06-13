"""
Pre-Tournament Reminder Agent

This agent automatically sends rich HTML reminder emails to users 1-2 days before their
earliest selected tournament session begins.
"""

import os
import logging
from datetime import datetime, timedelta
from models import db, Tournament, User, UserTournament
from services.pre_tournament_email import send_pre_tournament_reminder_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_pre_tournament_reminder_agent():
    """
    Send reminder emails to users whose earliest selected session is 1-2 days away.
    """
    try:
        logger.info("Pre-Tournament Reminder Agent: Starting execution")
        
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)
        
        # Get all UserTournament records where user is attending with sessions
        user_tournaments = UserTournament.query.filter(
            UserTournament.attending == True,
            UserTournament.session_label != '',
            UserTournament.session_label.isnot(None)
        ).join(User).join(Tournament).all()
        
        if not user_tournaments:
            logger.info("Pre-Tournament Reminder Agent: No qualifying user tournaments found")
            return "No qualifying users found"
        
        emails_sent = 0
        emails_skipped = 0
        
        for ut in user_tournaments:
            try:
                user = ut.user
                tournament = ut.tournament
                
                # Skip if user has no valid email
                if not user.email or '@' not in user.email:
                    logger.warning(f"Pre-Tournament Reminder Agent: Skipping user {user.id} - invalid email")
                    emails_skipped += 1
                    continue
                
                # Parse session labels to find earliest session date
                session_labels = [s.strip() for s in ut.session_label.split(',') if s.strip()]
                
                if not session_labels:
                    emails_skipped += 1
                    continue
                
                # For sessions, we'll use the tournament start date as the session date
                # since the sessions are stored as simple string labels
                earliest_session_date = tournament.start_date
                
                if earliest_session_date is None:
                    emails_skipped += 1
                    continue
                
                # Check if earliest session is 1-2 days away
                days_until_session = (earliest_session_date - today).days
                
                if days_until_session not in [1, 2]:
                    continue  # Not in the 1-2 day window
                
                # Send rich HTML pre-tournament reminder email
                admin_email = os.environ.get('ADMIN_EMAIL', 'richardbattlebaxter@gmail.com')
                
                try:
                    success = send_pre_tournament_reminder_email(
                        user_id=user.id,
                        tournament_id=tournament.id,
                        debug_email_override=admin_email  # Debug: send to admin instead of user
                    )
                    
                    if success:
                        emails_sent += 1
                        logger.info(f"Pre-Tournament Reminder Agent: Rich email sent to {user.email} for {tournament.name} (earliest session: {earliest_session_date})")
                    else:
                        emails_skipped += 1
                        logger.error(f"Pre-Tournament Reminder Agent: Failed to send rich email to {user.email}")
                        
                except Exception as e:
                    emails_skipped += 1
                    logger.error(f"Pre-Tournament Reminder Agent: Error sending rich email to {user.email}: {str(e)}")
                    
            except Exception as e:
                emails_skipped += 1
                logger.error(f"Pre-Tournament Reminder Agent: Error processing user tournament {ut.id}: {str(e)}")
                continue
        
        result_message = f"Sent {emails_sent} emails, skipped {emails_skipped}"
        logger.info(f"Pre-Tournament Reminder Agent: Completed - {result_message}")
        return result_message
        
    except Exception as e:
        error_msg = f"Pre-Tournament Reminder Agent failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

if __name__ == "__main__":
    # For testing purposes
    result = run_pre_tournament_reminder_agent()
    print(f"Agent result: {result}")