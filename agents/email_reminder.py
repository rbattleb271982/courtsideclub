import datetime
from flask import current_app
from models import db, User, Tournament, UserTournament
from services.email import send_tournament_reminder_email
import logging

logger = logging.getLogger(__name__)

def run_email_reminder():
    """
    AI Agent: Send tournament reminder emails to users
    
    Finds users attending tournaments starting in 2 weeks and sends reminder emails.
    Only sends to users who have:
    - UserTournament.attending == True
    - UserTournament.session_label is not empty
    - User.notifications == True (haven't opted out)
    """
    try:
        logger.info("Email Reminder Agent: Starting execution")
        
        # Calculate date range (2 weeks from today)
        target_date = datetime.date.today() + datetime.timedelta(days=14)
        
        # Find tournaments starting in 2 weeks
        upcoming_tournaments = Tournament.query.filter(
            Tournament.start_date == target_date
        ).all()
        
        if not upcoming_tournaments:
            logger.info(f"Email Reminder Agent: No tournaments starting on {target_date}")
            return {"status": "success", "message": f"No tournaments starting on {target_date}"}
        
        total_sent = 0
        total_skipped = 0
        
        for tournament in upcoming_tournaments:
            logger.info(f"Email Reminder Agent: Processing {tournament.name}")
            
            # Find users attending this tournament with sessions selected
            user_tournaments = db.session.query(UserTournament).filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                UserTournament.session_label != ''
            ).all()
            
            for user_tournament in user_tournaments:
                user = db.session.get(User, user_tournament.user_id)
                
                if not user:
                    continue
                    
                # Check if user has opted out of notifications
                if hasattr(user, 'notifications') and not user.notifications:
                    total_skipped += 1
                    logger.info(f"Email Reminder Agent: Skipped {user.email} (opted out)")
                    continue
                
                # Send reminder email
                success = send_tournament_reminder_email(
                    user_id=user.id,
                    tournament_id=tournament.id
                )
                
                if success:
                    total_sent += 1
                    logger.info(f"Email Reminder Agent: Sent reminder to {user.email}")
                else:
                    total_skipped += 1
                    logger.error(f"Email Reminder Agent: Failed to send to {user.email}")
        
        message = f"Sent {total_sent} reminder emails, skipped {total_skipped} users"
        logger.info(f"Email Reminder Agent: Completed - {message}")
        
        return {
            "status": "success",
            "message": message,
            "tournaments_processed": len(upcoming_tournaments),
            "emails_sent": total_sent,
            "emails_skipped": total_skipped
        }
        
    except Exception as e:
        error_message = f"Email Reminder Agent failed: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {"status": "error", "message": error_message}