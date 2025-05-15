import logging
from models import db

def log_event(user_id, event_name, event_data=None):
    """
    Log a user event to the database
    
    Args:
        user_id (int): ID of the user performing the action
        event_name (str): Name of the event (e.g., 'profile_updated', 'tournament_registered')
        event_data (dict, optional): Additional event data
    """
    try:
        # Import here to avoid circular import
        from models import Event
        
        # Create and save the event
        event = Event(
            user_id=user_id, 
            name=event_name, 
            event_data=event_data or {}
        )
        db.session.add(event)
        db.session.commit()
        logging.info(f"Event logged: {event_name} for user {user_id}")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to log event {event_name}: {str(e)}")