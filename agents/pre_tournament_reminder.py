"""
Pre-Tournament Reminder Agent

This agent automatically sends reminder emails to users 1-2 days before their
earliest selected tournament session begins.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from models import db, Tournament, User, UserTournament
from services.sendgrid_service import send_email
from utils.email_templates import load_email_template, render_template

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
                
                # Load email template and prepare content
                template = load_email_template('pre_tournament_reminder')
                
                # Use first name if available, otherwise email prefix
                first_name = user.first_name if hasattr(user, 'first_name') and user.first_name else user.email.split('@')[0]
                
                # Render template with variables
                subject = render_template(template['subject'], 
                                        user={'first_name': first_name}, 
                                        tournament_name=tournament.name)
                
                body_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    {render_template(template['body'], 
                                   user={'first_name': first_name}, 
                                   tournament_name=tournament.name)}
                </div>
                """
                
                # Send email (all debug emails go to admin)
                admin_email = os.environ.get('ADMIN_EMAIL', 'richardbattlebaxter@gmail.com')
                
                try:
                    success = send_email(
                        to_email=admin_email,  # Debug: send to admin instead of user
                        subject=f"[DEBUG for {user.email}] {subject}",
                        content_html=body_html
                    )
                    
                    if success:
                        emails_sent += 1
                        logger.info(f"Pre-Tournament Reminder Agent: Email sent to {user.email} for {tournament.name} (earliest session: {earliest_session_date})")
                    else:
                        emails_skipped += 1
                        logger.error(f"Pre-Tournament Reminder Agent: Failed to send email to {user.email}")
                        
                except Exception as e:
                    emails_skipped += 1
                    logger.error(f"Pre-Tournament Reminder Agent: Error sending email to {user.email}: {str(e)}")
                    
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