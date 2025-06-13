"""
Pre-Tournament Reminder Email Service
Generates rich HTML emails using React-style component structure
"""

import os
import logging
from datetime import datetime, timedelta
from models import db, User, Tournament, UserTournament
from services.email import send_email
from flask import current_app

logger = logging.getLogger(__name__)

def parse_session_label(session_label, tournament_start_date):
    """Parse session label string into structured session data"""
    if not session_label or not tournament_start_date:
        return []
    
    sessions = []
    session_parts = [s.strip() for s in session_label.split(',') if s.strip()]
    
    for part in session_parts:
        session = parse_single_session(part, tournament_start_date)
        if session:
            sessions.append(session)
    
    return sessions

def parse_single_session(session_str, tournament_start_date):
    """Parse a single session string like 'Day 1' or 'Night 2' into structured data"""
    session_str = session_str.strip().lower()
    
    # Extract day number and session type
    day_num = None
    session_type = None
    
    # Look for patterns like "day 1", "night 2", "all day 3"
    if 'all day' in session_str:
        session_type = 'All Day'
        # Extract number after "all day"
        parts = session_str.replace('all day', '').strip().split()
        if parts and parts[0].isdigit():
            day_num = int(parts[0])
    elif session_str.startswith('day'):
        session_type = 'Day Session'
        # Extract number after "day"
        parts = session_str.replace('day', '').strip().split()
        if parts and parts[0].isdigit():
            day_num = int(parts[0])
    elif session_str.startswith('night'):
        session_type = 'Night Session'
        # Extract number after "night"
        parts = session_str.replace('night', '').strip().split()
        if parts and parts[0].isdigit():
            day_num = int(parts[0])
    
    if not day_num or not session_type:
        # Fallback: try to extract any number and default to Day Session
        import re
        numbers = re.findall(r'\d+', session_str)
        if numbers:
            day_num = int(numbers[0])
            session_type = 'Day Session'
        else:
            return None
    
    # Calculate the actual date
    session_date = tournament_start_date + timedelta(days=day_num - 1)
    
    # Format date
    formatted_date = session_date.strftime("%B %d, %Y")
    
    # Set time ranges based on session type
    if session_type == 'Day Session':
        time_range = "10:00 AM - 6:00 PM"
    elif session_type == 'Night Session':
        time_range = "6:00 PM - 11:00 PM"
    elif session_type == 'All Day':
        time_range = "10:00 AM - 9:00 PM"
    else:
        time_range = "TBD"
    
    # Create label
    label = f"Day {day_num} – {session_type}"
    
    return {
        'label': label,
        'date': formatted_date,
        'time': time_range,
        'day_num': day_num,
        'session_type': session_type,
        'attendees': 0  # Will be populated later
    }

def get_session_attendee_count(tournament_id, session_label_fragment):
    """Count attendees for a specific session"""
    try:
        # Count users who have this session in their session_label and are attending
        count = db.session.query(UserTournament).filter(
            UserTournament.tournament_id == tournament_id,
            UserTournament.attending == True,
            UserTournament.session_label.contains(session_label_fragment)
        ).count()
        
        return max(0, count)
    except Exception as e:
        logger.error(f"Error counting session attendees: {str(e)}")
        return 0

def get_meetup_count(tournament_id, user_id):
    """Get count of users open to meeting up at this tournament (excluding current user)"""
    try:
        count = db.session.query(UserTournament).filter(
            UserTournament.tournament_id == tournament_id,
            UserTournament.attending == True,
            UserTournament.open_to_meet == True,
            UserTournament.user_id != user_id
        ).count()
        
        return max(0, count)
    except Exception as e:
        logger.error(f"Error counting meetup users: {str(e)}")
        return 0

def generate_pre_tournament_email_html(user_id, tournament_id):
    """Generate the HTML for the pre-tournament reminder email"""
    try:
        # Get user and tournament data
        user = db.session.get(User, user_id)
        tournament = db.session.get(Tournament, tournament_id)
        
        if not user or not tournament:
            logger.error(f"User {user_id} or Tournament {tournament_id} not found")
            return None
        
        # Get user's tournament registration
        user_tournament = db.session.query(UserTournament).filter_by(
            user_id=user_id,
            tournament_id=tournament_id,
            attending=True
        ).first()
        
        if not user_tournament or not user_tournament.session_label:
            logger.error(f"User {user_id} not attending tournament {tournament_id} or no sessions selected")
            return None
        
        # Parse sessions
        sessions = parse_session_label(user_tournament.session_label, tournament.start_date)
        
        if not sessions:
            logger.error(f"Could not parse sessions for user {user_id}, tournament {tournament_id}")
            return None
        
        # Add attendee counts to sessions
        for session in sessions:
            # Create a search fragment for this session
            search_fragment = f"{session['session_type'].split()[0].lower()} {session['day_num']}"
            session['attendees'] = get_session_attendee_count(tournament_id, search_fragment)
        
        # Get meetup count
        meetup_count = get_meetup_count(tournament_id, user_id)
        
        # Prepare template data
        user_first_name = getattr(user, 'first_name', None) or 'Member'
        tournament_name = tournament.name
        location = f"{tournament.city}, {tournament.country}" if tournament.city and tournament.country else "Tournament Location"
        schedule_url = getattr(tournament, 'schedule_url', '#') or '#'
        lanyard_ordered = getattr(user, 'lanyard_ordered', False)
        
        # Base URL for links
        base_url = current_app.config.get('BASE_URL', 'https://courtsideclub.app')
        
        # Generate HTML using the React component structure
        html = generate_email_html_template(
            user_first_name=user_first_name,
            tournament_name=tournament_name,
            sessions=sessions,
            meetup_count=meetup_count,
            lanyard_ordered=lanyard_ordered,
            schedule_url=schedule_url,
            location=location,
            base_url=base_url
        )
        
        return html
        
    except Exception as e:
        logger.error(f"Error generating pre-tournament email HTML: {str(e)}", exc_info=True)
        return None

def generate_email_html_template(user_first_name, tournament_name, sessions, meetup_count, lanyard_ordered, schedule_url, location, base_url):
    """Generate the actual HTML email template"""
    
    # Generate sessions HTML
    sessions_html = ""
    for idx, session in enumerate(sessions):
        border_style = 'border-bottom: 1px solid #e6f0d9; padding-bottom: 15px;' if idx < len(sessions) - 1 else ''
        
        sessions_html += f"""
        <div style="{border_style}">
            <p style="font-weight: 600; margin-bottom: 5px;">{session['label']}</p>
            <p style="margin: 0; font-size: 14px; color: #555;">
                {session['date']} • {session['time']} — {session['attendees']} fan{'s' if session['attendees'] != 1 else ''} attending
            </p>
        </div>
        """
    
    # Generate lanyard message
    if lanyard_ordered:
        lanyard_html = """
        Your lanyard is on the way! Don't forget to bring it to make meeting other members easier.
        """
    else:
        lanyard_html = f"""
        Haven't ordered your free CourtSide Club lanyard yet? 
        <a href="{base_url}/lanyard/order" style="color: #669127; text-decoration: underline;">Order now</a>
        to stand out and connect at the tournament.
        """
    
    # Complete HTML template
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tournament Reminder - CourtSide Club</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #FBFAFB; color: #464C3F; font-family: Inter, Arial, sans-serif; padding: 40px 30px;">
            
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="font-family: 'Crimson Text', Georgia, serif; font-size: 24px; margin: 0; color: #464C3F;">CourtSide Club</h1>
            </div>

            <!-- Title -->
            <h1 style="font-family: 'Crimson Text', Georgia, serif; font-weight: 600; font-size: 28px; margin-bottom: 20px; line-height: 1.3; text-align: center;">
                Almost time — your CourtSide Club tournament starts soon
            </h1>

            <!-- Greeting -->
            <p style="font-size: 18px; font-weight: 500; margin-bottom: 20px;">
                Hi {user_first_name},
            </p>

            <!-- Intro -->
            <p style="margin-bottom: 30px;">
                Your visit to <strong>{tournament_name}</strong> is just around the corner. We're excited to enhance your
                tournament experience and help you connect with fellow tennis enthusiasts.
            </p>

            <!-- Sessions & Attendees -->
            <div style="background-color: #fff; border-radius: 12px; border: 1px solid rgba(102, 145, 39, 0.3); padding: 20px; margin-bottom: 30px;">
                <h2 style="font-family: 'Crimson Text', Georgia, serif; font-size: 20px; font-weight: 600; margin-bottom: 20px;">
                    Your Selected Sessions
                </h2>
                {sessions_html}
            </div>

            <!-- Meetup Info -->
            <p style="margin-bottom: 30px; font-weight: 600;">
                {meetup_count} fan{'s' if meetup_count != 1 else ''} attending are open to meeting up — a great way to connect!
            </p>

            <!-- Lanyard Status -->
            <p style="margin-bottom: 30px;">
                {lanyard_html}
            </p>

            <!-- Tournament Logistics -->
            <div style="background-color: #fff; border-radius: 12px; border: 1px solid rgba(102, 145, 39, 0.3); padding: 20px; margin-bottom: 30px;">
                <h2 style="font-family: 'Crimson Text', Georgia, serif; font-size: 20px; font-weight: 600; margin-bottom: 20px;">
                    Tournament Details
                </h2>
                <p>Location: <strong>{location}</strong></p>
                <p>
                    Official schedule: 
                    <a href="{schedule_url}" style="color: #669127; text-decoration: underline;">View here</a>
                </p>
                <p>
                    Travel tips: 
                    <a href="{base_url}/blog" style="color: #669127; text-decoration: underline;">Learn more</a>
                </p>
            </div>

            <!-- CTA -->
            <div style="text-align: center; margin-bottom: 40px;">
                <a href="{base_url}/my-tournaments" style="display: inline-block; background-color: #669127; color: #fff; text-decoration: none; padding: 16px 32px; border-radius: 50px; font-weight: 600; font-size: 16px;">
                    View My Tournaments
                </a>
            </div>

            <!-- Footer -->
            <div style="text-align: center; border-top: 1px solid rgba(70, 76, 63, 0.2); padding-top: 30px; margin-top: 40px; font-family: 'Crimson Text', Georgia, serif; font-size: 18px; font-style: italic; color: #464C3F;">
                Tennis is better together.
                <div style="font-size: 14px; color: #666; margin-top: 20px;">
                    <p>© 2025 CourtSide Club. All rights reserved.</p>
                    <p>
                        <a href="{base_url}/privacy" style="color: #669127; text-decoration: none; margin-right: 15px;">Privacy Policy</a>
                        <a href="{base_url}/unsubscribe" style="color: #669127; text-decoration: none;">Unsubscribe</a>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_pre_tournament_reminder_email(user_id, tournament_id, debug_email_override=None):
    """Send the pre-tournament reminder email to a user"""
    try:
        # Generate the HTML content
        html_content = generate_pre_tournament_email_html(user_id, tournament_id)
        
        if not html_content:
            logger.error(f"Failed to generate HTML content for user {user_id}, tournament {tournament_id}")
            return False
        
        # Get user and tournament for subject line
        user = db.session.get(User, user_id)
        tournament = db.session.get(Tournament, tournament_id)
        
        if not user or not tournament:
            logger.error(f"User {user_id} or Tournament {tournament_id} not found for email send")
            return False
        
        # Send email
        subject = f"🎾 {tournament.name} starts soon — you're all set!"
        
        # Use debug email override or send to actual user
        recipient_email = debug_email_override or user.email
        
        success = send_email(
            to_email=recipient_email,
            subject=subject,
            content_html=html_content
        )
        
        if success:
            logger.info(f"Pre-tournament reminder email sent to {recipient_email} for tournament {tournament.name}")
        else:
            logger.error(f"Failed to send pre-tournament reminder email to {recipient_email}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in send_pre_tournament_reminder_email: {str(e)}", exc_info=True)
        return False