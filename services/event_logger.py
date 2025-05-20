from models import Event, db
from flask_login import current_user
from datetime import datetime

"""
Standard CourtSide Club Event Types
-----------------------------------

ACCOUNT EVENTS:
- user_signup: User creates an account
- user_login: User logs in successfully
- profile_updated: User updates their profile
- location_set: User saves their location
- user_opt_out_email: User disables email notifications

TOURNAMENT EVENTS:
- attend_tournament: User indicates they're attending a tournament
- tournament_unattend: User unselects attendance for a tournament
- session_selected: User selects and saves sessions
- wants_to_meet_enabled: User checks "Open to meeting" option
- wants_to_meet_disabled: User unchecks "Open to meeting" option
- past_tournament_added: User adds a past tournament to their profile
- past_tournament_removed: User removes a past tournament from their profile

LANYARD EVENTS:
- lanyard_order_eligible: User becomes eligible for a lanyard
- lanyard_order_started: User visits the lanyard order page
- shipping_address_submitted: User submits shipping information

ADMIN EVENTS:
- lanyard_marked_sent: Admin marks a lanyard as sent
- admin_meetup_set: Admin sets meetup location/time
- admin_bulk_lanyards_sent: Admin uses "Mark All as Sent"
- admin_tournament_updated: Admin edits tournament details
- lanyard_export: Admin exports lanyard CSV

EMAIL EVENTS:
- welcome_email_sent: Welcome email is sent to user
- reminder_email_sent: Reminder email is sent to user
- meetup_email_sent: Meetup email is sent to user
- post_event_email_sent: Post-event email or survey is sent to user
"""

def log_event(name, user=None, data=None):
    """
    Log an event to the database
    
    Args:
        name (str): The name of the event (see list of standard event types above)
        user (User, optional): The user who performed the action. Defaults to current_user.
        data (dict, optional): Additional data to store with the event. Defaults to None.
    """
    try:
        event = Event(
            name=name,
            user_id=user.id if user else current_user.id if current_user.is_authenticated else None,
            timestamp=datetime.utcnow(),
            event_data=data or {}
        )
        db.session.add(event)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error logging event: {str(e)}")
        db.session.rollback()
        return False