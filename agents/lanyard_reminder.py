"""
Lanyard Reminder Agent

This agent automatically sends email reminders to users who have ordered lanyards
and are attending tournaments starting in exactly 3 days.
"""

import os
import logging
from datetime import datetime, timedelta
from models import db, Tournament, User, UserTournament
from services.sendgrid_service import send_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_lanyard_reminder_agent():
    """
    Send lanyard reminders to users attending tournaments in exactly 3 days
    who have ordered lanyards and have session selections.
    """
    try:
        logger.info("Lanyard Reminder Agent: Starting execution")
        
        # Calculate target date (3 days from today)
        today = datetime.now().date()
        target_date = today + timedelta(days=3)
        
        # Find tournaments starting in exactly 3 days
        upcoming_tournaments = Tournament.query.filter(
            Tournament.start_date == target_date
        ).all()
        
        if not upcoming_tournaments:
            logger.info(f"Lanyard Reminder Agent: No tournaments starting on {target_date}")
            return "No tournaments starting in 3 days"
        
        total_emails_sent = 0
        
        for tournament in upcoming_tournaments:
            logger.info(f"Lanyard Reminder Agent: Processing {tournament.name}")
            
            # Find users attending this tournament with lanyard orders and session selections
            user_tournaments = db.session.query(UserTournament, User).join(
                User, UserTournament.user_id == User.id
            ).filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                UserTournament.session_label != '',
                User.lanyard_ordered == True
            ).all()
            
            tournament_emails_sent = 0
            
            for user_tournament, user in user_tournaments:
                # Skip users without valid email addresses
                if not user.email or '@' not in user.email:
                    logger.warning(f"Lanyard Reminder Agent: Skipping user {user.id} - invalid email")
                    continue
                
                # Prepare email content
                subject = f"🎾 Don't forget your lanyard — {tournament.name} is coming up!"
                
                # Use first name if available, otherwise email prefix
                first_name = user.first_name if hasattr(user, 'first_name') and user.first_name else user.email.split('@')[0]
                
                body_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <p>Hey {first_name},</p>
                    
                    <p>You're attending <strong>{tournament.name}</strong> soon!</p>
                    
                    <p>If you ordered a lanyard, don't forget to bring it so other CourtSide Club members can spot you.</p>
                    
                    <p>Want to see who else is going?<br>
                    👉 <a href="https://courtsideclub.com/login" style="color: #006400; text-decoration: none;">Log in to your dashboard</a></p>
                    
                    <p>—<br>
                    The Lounge is Courtside.</p>
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
                        logger.info(f"Lanyard Reminder Agent: Email sent to {user.email} (redirected to admin)")
                        tournament_emails_sent += 1
                        total_emails_sent += 1
                    else:
                        logger.error(f"Lanyard Reminder Agent: Failed to send email to {user.email}")
                        
                except Exception as e:
                    logger.error(f"Lanyard Reminder Agent: Email error for {user.email}: {str(e)}")
            
            logger.info(f"Lanyard Reminder Agent: Sent {tournament_emails_sent} emails for {tournament.name}")
        
        logger.info(f"Lanyard Reminder Agent: Completed - Sent {total_emails_sent} total emails")
        return f"Sent {total_emails_sent} lanyard reminder emails"
        
    except Exception as e:
        logger.error(f"Lanyard Reminder Agent: Error during execution: {str(e)}")
        raise e