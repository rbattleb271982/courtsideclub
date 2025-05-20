from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from services.event_logger import log_event

# Create blueprint for event testing
event_test_bp = Blueprint('event_test', __name__, url_prefix='/event-test')

@event_test_bp.route('/')
@login_required
def test_event_logging():
    """
    Example route that demonstrates how to use the event logger
    """
    # Log a simple event
    log_event('example_event')
    
    # Log an event with additional data
    log_event('detailed_event', data={
        'source': 'event_test_route',
        'action': 'demonstration',
        'details': 'This shows how to include structured data with events'
    })
    
    flash("Events logged successfully!", "success")
    return redirect(url_for('admin.view_events'))