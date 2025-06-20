"""
Post-Event Follow-Up Agent

This agent automatically sends thank-you emails to users who attended tournaments
that ended yesterday, including stats about total Let'CourtSide attendance.
"""

import os
import logging
from datetime import datetime, timedelta
from models import db, Tournament, User, UserTournament
from services.sendgrid_service import send_email
from utils.email_templates import load_email_template, render_template

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_post_event_followup_agent():
    """
    Send thank-you emails to users who attended tournaments that ended yesterday.
    """
    try:
        logger.info("Post-Event Follow-Up Agent: Starting execution")
        
        # Calculate yesterday's date
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Find tournaments that ended yesterday
        completed_tournaments = Tournament.query.filter(
            Tournament.end_date == yesterday
        ).all()
        
        if not completed_tournaments:
            logger.info(f"Post-Event Follow-Up Agent: No tournaments ended on {yesterday}")
            return "No tournaments ended yesterday"
        
        total_emails_sent = 0
        
        for tournament in completed_tournaments:
            logger.info(f"Post-Event Follow-Up Agent: Processing {tournament.name}")
            
            # Find all users who attended this tournament with session selections
            user_tournaments = db.session.query(UserTournament, User).join(
                User, UserTournament.user_id == User.id
            ).filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                UserTournament.session_label != ''
            ).all()
            
            # Count total attendees for this tournament
            total_attending = len(user_tournaments)
            
            if total_attending == 0:
                logger.info(f"Post-Event Follow-Up Agent: No qualifying attendees for {tournament.name}")
                continue
            
            tournament_emails_sent = 0
            
            for user_tournament, user in user_tournaments:
                # Skip users without valid email addresses
                if not user.email or '@' not in user.email:
                    logger.warning(f"Post-Event Follow-Up Agent: Skipping user {user.id} - invalid email")
                    continue
                
                # Load email template and prepare content
                template = load_email_template('post_event_followup')
                
                # Use first name if available, otherwise email prefix
                first_name = user.first_name if hasattr(user, 'first_name') and user.first_name else user.email.split('@')[0]
                
                # Render template with variables
                subject = render_template(template['subject'], 
                                        user={'first_name': first_name}, 
                                        tournament_name=tournament.name,
                                        total_attending=total_attending)
                
                body_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    {render_template(template['body'], 
                                   user={'first_name': first_name}, 
                                   tournament_name=tournament.name,
                                   total_attending=total_attending)}
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
                        logger.info(f"Post-Event Follow-Up Agent: Email sent to {user.email} (redirected to admin)")
                        tournament_emails_sent += 1
                        total_emails_sent += 1
                    else:
                        logger.error(f"Post-Event Follow-Up Agent: Failed to send email to {user.email}")
                        
                except Exception as e:
                    logger.error(f"Post-Event Follow-Up Agent: Email error for {user.email}: {str(e)}")
            
            logger.info(f"Post-Event Follow-Up Agent: Sent {tournament_emails_sent} emails for {tournament.name} ({total_attending} total attendees)")
        
        logger.info(f"Post-Event Follow-Up Agent: Completed - Sent {total_emails_sent} total emails")
        return f"Sent {total_emails_sent} post-event follow-up emails"
        
    except Exception as e:
        logger.error(f"Post-Event Follow-Up Agent: Error during execution: {str(e)}")
        raise e