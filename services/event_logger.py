from models import Event, db
from flask_login import current_user
from datetime import datetime

def log_event(name, user=None, data=None):
    """
    Log an event to the database
    
    Args:
        name (str): The name of the event (e.g., 'tournament_view', 'login')
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