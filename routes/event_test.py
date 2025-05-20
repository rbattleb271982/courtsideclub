from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from services.event_logger import log_event
from datetime import datetime

# Create blueprint for event testing
event_test_bp = Blueprint('event_test', __name__, url_prefix='/event-test')

@event_test_bp.route('/')
@login_required
def test_event_logging():
    """
    Example route that demonstrates how to use the event logger
    """
    # Only admins can run test events
    if not current_user.is_admin:
        flash("Access denied. Only admins can run test events.", "danger")
        return redirect(url_for('main.public_home'))
    
    # Log a variety of events to demonstrate the event tracking system
    
    # Account events
    log_event('user_login', data={'login_method': 'password'})
    log_event('profile_updated', data={'fields': ['first_name', 'last_name', 'location']})
    
    # Tournament events
    tournament_id = "indian_wells"
    log_event('attend_tournament', data={
        'tournament_id': tournament_id,
        'tournament_name': 'BNP Paribas Open',
    })
    log_event('session_selected', data={
        'tournament_id': tournament_id,
        'sessions': ['Day 1 - Day', 'Day 2 - Night']
    })
    log_event('wants_to_meet_enabled', data={'tournament_id': tournament_id})
    
    # Lanyard events
    log_event('lanyard_order_eligible', data={'eligible_count': 1})
    log_event('lanyard_order_started', data={'timestamp': datetime.utcnow().isoformat()})
    
    # Admin events
    log_event('admin_tournament_updated', data={
        'tournament_id': tournament_id,
        'fields_updated': ['about', 'surface', 'draw_url'],
        'admin_user': current_user.email
    })
    
    # Email events
    log_event('reminder_email_sent', data={
        'email_type': 'tournament_reminder',
        'tournament_id': tournament_id,
        'days_before': 7
    })
    
    flash("Test events logged successfully! Check the event log to see them.", "success")
    return redirect(url_for('admin.view_events'))