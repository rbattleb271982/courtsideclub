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
        
        # Base URL for links
        base_url = current_app.config.get('BASE_URL', 'https://letcourtside.com')
        
        # Generate HTML using the React component structure
        html = generate_email_html_template(
            user_first_name=user_first_name,
            tournament_name=tournament_name,
            sessions=sessions,
            meetup_count=meetup_count,
            schedule_url=schedule_url,
            location=location,
            base_url=base_url
        )
        
        return html
        
    except Exception as e:
        logger.error(f"Error generating pre-tournament email HTML: {str(e)}", exc_info=True)
        return None

def generate_email_html_template(user_first_name, tournament_name, sessions, meetup_count, schedule_url, location, base_url):
    """Generate the actual HTML email template using React-style component structure"""
    
    # Complete HTML template with React component styling
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Your Let'CourtSide Tournament Starts Soon</title>
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');
          body {{
            background-color: #FBFAFB; 
            margin: 0; 
            padding: 0; 
            font-family: 'Inter', Arial, sans-serif;
            -webkit-text-size-adjust: 100%; 
            -ms-text-size-adjust: 100%;
            color: #464C3F;
          }}
          .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 45px 25px;
            background-color: #FBFAFB;
          }}
          h1, h2 {{
            font-family: 'Crimson Text', Georgia, serif;
            color: #464C3F;
            margin: 0 0 24px 0;
            font-weight: 600;
          }}
          h1 {{
            font-size: 32px;
            letter-spacing: 0.5px;
            line-height: 1.2;
            text-align: center;
          }}
          p {{
            font-family: 'Inter', Arial, sans-serif;
            font-size: 16px;
            line-height: 1.6;
            margin: 0 0 22px 0;
            font-weight: 400;
          }}
          .checklist-item {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 16px;
          }}
          .checklist-number {{
            background-color: #669127;
            color: white;
            width: 38px;
            height: 38px;
            border-radius: 50%;
            font-family: 'Inter', Arial, sans-serif;
            font-weight: 500;
            font-size: 18px;
            line-height: 38px;
            text-align: center;
            margin-right: 12px;
            flex-shrink: 0;
          }}
          .checklist-text {{
            background-color: white;
            border-radius: 14px;
            padding: 22px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            color: #464C3F;
            font-weight: 500;
            font-size: 16px;
            line-height: 1.5;
          }}
          .cta-button {{
            display: inline-block;
            background-color: #669127;
            color: white;
            border-radius: 10px;
            font-family: 'Inter', Arial, sans-serif;
            font-weight: 600;
            font-size: 16px;
            line-height: 1.5;
            padding: 14px 32px;
            text-decoration: none;
            letter-spacing: 0.3px;
          }}
          .cta-button:hover {{
            background-color: #557a20;
          }}
          .secondary-link {{
            color: #669127;
            font-family: 'Inter', Arial, sans-serif;
            font-weight: 500;
            font-size: 16px;
            line-height: 1.5;
            text-decoration: none;
            text-align: center;
            display: block;
            margin-top: 10px;
            margin-bottom: 45px;
          }}
          .secondary-link:hover {{
            text-decoration: underline;
          }}
          .footer {{
            border-top: 1px solid #EDB418;
            padding: 35px 0 20px 0;
            text-align: center;
            font-family: 'Crimson Text', Georgia, serif;
            font-style: italic;
            font-size: 19px;
            letter-spacing: 0.3px;
            margin-top: 20px;
            color: #464C3F;
          }}
          .footer-links {{
            font-family: 'Inter', Arial, sans-serif;
            font-size: 14px;
            color: #464C3F;
            font-weight: 400;
            margin-top: 12px;
            margin-bottom: 0;
          }}
          .footer-links a {{
            color: #464C3F;
            text-decoration: none;
            margin: 0 6px;
          }}
          .footer-links a:hover {{
            text-decoration: underline;
          }}
        </style>
    </head>
    <body>
        <div class="container">
          <h1>Let'CourtSide</h1>
          <h2>Almost time — your Let'CourtSide tournament starts soon</h2>
          <p>Hi {user_first_name},</p>
          <p>Your visit to <strong>{tournament_name}</strong> is just around the corner. We're excited to help you connect with fellow tennis enthusiasts and make the most of your match day.</p>
          
          <!-- Checklist -->
          <div class="checklist-item">
            <div class="checklist-number">1</div>
            <div class="checklist-text">Confirm your session selections — review and finalize your planned matches and events.</div>
          </div>
          <div class="checklist-item">
            <div class="checklist-number">2</div>
            <div class="checklist-text">Invite a friend — share the experience and meet other fans.</div>
          </div>
          <div class="checklist-item">
            <div class="checklist-number">3</div>
            <div class="checklist-text">Get ready for match day — enjoy every moment courtside.</div>
          </div>
          
          <!-- Call to actions -->
          <div style="text-align: center; margin-bottom: 20px;">
            <a href="{base_url}/my-tournaments" class="cta-button">View My Tournaments</a>
          </div>
          <a href="{base_url}/blog" class="secondary-link">Visit the Blog →</a>
          
          <!-- Footer -->
          <div class="footer">
            Tennis is better together.
            <div class="footer-links">
              <a href="{base_url}/privacy">Privacy Policy</a> | <a href="{base_url}/unsubscribe">Unsubscribe</a>
            </div>
            <div style="font-size: 12px; margin-top: 8px;">© 2025 Let'CourtSide. All rights reserved.</div>
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