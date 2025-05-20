
from flask import request
from models import db, Event
from datetime import datetime
from utils.event_meta import event_descriptions as EVENT_DESCRIPTIONS

def log_event(user_id, event_name, data=None):
    """
    Log an event to the database with the given name and optional data
    
    Args:
        user_id (int): The ID of the user who triggered the event
        event_name (str): The name/type of the event (must match EVENT_DESCRIPTIONS)
        data (dict): Optional dictionary of additional event data
    """
    if event_name not in EVENT_DESCRIPTIONS:
        raise ValueError(f"Invalid event name: {event_name}")
        
    if data is None:
        data = {}
        
    # Add standard metadata
    data.update({
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Create and save the event
    event = Event(
        user_id=user_id,
        name=event_name,
        event_data=data
    )
    
    db.session.add(event)
    db.session.commit()

def get_event_description(event_name):
    """Get the human-readable description for an event type"""
    return EVENT_DESCRIPTIONS.get(event_name, "Unknown event type")
