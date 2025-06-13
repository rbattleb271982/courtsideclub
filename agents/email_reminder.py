from datetime import datetime, timedelta
from models import db, User, Tournament, UserTournament
from services.pre_tournament_email import send_pre_tournament_reminder_email
import logging

logger = logging.getLogger(__name__)

def run_email_reminder(preview=False):
    """
    AI Agent: Send tournament reminder emails to users
    
    Finds users attending tournaments starting in 12-15 days and sends personalized reminder emails.
    
    Args:
        preview (bool): If True, logs email content without sending actual emails
    """
    try:
        logger.info(f"Email Reminder Agent: Starting execution (preview mode: {preview})")
        
        today = datetime.utcnow().date()
        window_start = today + timedelta(days=12)
        window_end = today + timedelta(days=15)

        tournaments = Tournament.query.filter(
            Tournament.start_date >= window_start,
            Tournament.start_date <= window_end
        ).all()

        if not tournaments:
            logger.info(f"Email Reminder Agent: No tournaments found in window {window_start} to {window_end}")
            return {"status": "success", "message": f"No tournaments in reminder window ({window_start} to {window_end})"}

        total_sent = 0
        total_skipped = 0
        max_emails = 3 if not preview else 1000  # Limit actual emails to 3 for safety
        
        # For non-preview mode, exit early after processing to avoid timeouts
        if not preview:
            logger.info("Email Reminder Agent: Running in production mode with email limits")

        for tournament in tournaments:
            logger.info(f"Email Reminder Agent: Processing {tournament.name}")
            
            user_tournaments = UserTournament.query.filter_by(
                tournament_id=tournament.id,
                attending=True
            ).filter(UserTournament.session_label != '').all()

            if not user_tournaments:
                logger.info(f"Email Reminder Agent: No attending users with sessions for {tournament.name}")
                continue

            total_attending = len(user_tournaments)
            total_meeting = sum(1 for ut in user_tournaments if ut.open_to_meet)

            for ut in user_tournaments:
                # Check email limit for safety
                if not preview and total_sent >= max_emails:
                    logger.info(f"Email Reminder Agent: Reached safety limit of {max_emails} emails")
                    break
                    
                user = ut.user
                if not user.email:
                    total_skipped += 1
                    continue

                # Check if user has opted out of notifications
                if hasattr(user, 'notifications') and not user.notifications:
                    total_skipped += 1
                    logger.info(f"Email Reminder Agent: Skipped {user.email} (opted out)")
                    continue

                if preview:
                    # Preview mode: just log the email content without sending
                    total_sent += 1
                    logger.info(f"Email Reminder Agent (PREVIEW): Would send rich email to {user.email} for {tournament.name}")
                else:
                    # Send rich HTML pre-tournament reminder email
                    debug_email = "richardbattlebaxter@gmail.com"
                    
                    try:
                        success = send_pre_tournament_reminder_email(
                            user_id=user.id,
                            tournament_id=tournament.id,
                            debug_email_override=debug_email
                        )
                        
                        if success:
                            total_sent += 1
                            logger.info(f"Email Reminder Agent: Sent rich email to {debug_email} for {user.email} ({tournament.name})")
                        else:
                            total_skipped += 1
                            logger.error(f"Email Reminder Agent: Failed to send rich email")
                    except Exception as e:
                        total_skipped += 1
                        logger.error(f"Email Reminder Agent: Error sending rich email: {str(e)}")
                        # Continue with next user instead of failing completely

        message = f"Sent {total_sent} reminder emails, skipped {total_skipped} users"
        logger.info(f"Email Reminder Agent: Completed - {message}")
        
        return {
            "status": "success", 
            "message": message,
            "tournaments_processed": len(tournaments),
            "emails_sent": total_sent,
            "emails_skipped": total_skipped
        }
        
    except Exception as e:
        error_message = f"Email Reminder Agent failed: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {"status": "error", "message": error_message}