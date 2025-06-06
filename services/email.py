import os
import datetime
from flask import current_app
from models import db, User, Tournament, UserTournament
from services.sendgrid_service import send_email
import logging

logger = logging.getLogger(__name__)

def get_session_attendees_count(tournament_id, session_label, date_str=None):
    """Get count of users attending a specific session"""
    query = db.session.query(UserTournament).filter(
        UserTournament.tournament_id == tournament_id,
        UserTournament.attending == True,
        UserTournament.session_label.ilike(f'%{session_label}%')
    )
    return query.count()

def get_session_meetup_count(tournament_id, session_label, date_str=None):
    """Get count of users open to meeting for a specific session"""
    query = db.session.query(UserTournament).filter(
        UserTournament.tournament_id == tournament_id,
        UserTournament.attending == True,
        UserTournament.open_to_meet == True,
        UserTournament.session_label.ilike(f'%{session_label}%')
    )
    return query.count()

def send_tournament_reminder_email(user_id, tournament_id):
    """
    Send pre-tournament reminder email (2 weeks before)
    
    Send to users where:
    - UserTournament.attending == True
    - UserTournament.session_label is not empty
    - User has not opted out of email
    """
    try:
        user = db.session.get(User, user_id)
        tournament = db.session.get(Tournament, tournament_id)
        
        if not user or not tournament:
            logger.error(f"User {user_id} or tournament {tournament_id} not found")
            return False
            
        # Check if user has opted out of emails
        if hasattr(user, 'notifications') and not user.notifications:
            logger.info(f"User {user.email} has opted out of emails")
            return False
            
        # Get user's tournament registration
        user_tournament = db.session.query(UserTournament).filter_by(
            user_id=user.id,
            tournament_id=tournament.id,
            attending=True
        ).first()
        
        if not user_tournament or not user_tournament.session_label:
            logger.info(f"User {user.email} not attending {tournament.name} or no sessions selected")
            return False
            
        # Count others attending and open to meeting
        attendees_count = get_session_attendees_count(tournament.id, user_tournament.session_label)
        meetup_count = get_session_meetup_count(tournament.id, user_tournament.session_label)
        
        # Exclude current user from meetup count
        if user_tournament.open_to_meet:
            meetup_count = max(0, meetup_count - 1)
            
        # Build session summary
        session_summary = f"<p>Here are the sessions you've selected:</p>"
        session_summary += f"<ul><li>✅ {user_tournament.session_label}"
        
        if meetup_count > 0:
            session_summary += f" – <strong>{meetup_count} other fan{'s' if meetup_count != 1 else ''}</strong> who are open to meeting up"
        else:
            session_summary += " – you're the first to raise your hand for this one!"
            
        session_summary += "</li></ul>"
        
        # Meetup message based on user's preferences
        if user_tournament.open_to_meet:
            meetup_msg = "<p>👋 Great news — you're set to meet other fans at the tournament! We'll send you final details about meeting spots soon.</p>"
        else:
            meetup_msg = f"<p>Want to meet other fans? <a href=\"{current_app.config.get('BASE_URL', 'https://courtsideclub.app')}/login\">Update your preferences</a> to join the meetup.</p>"
        
        # Lanyard message
        has_lanyard = getattr(user, 'lanyard_ordered', False)
        if has_lanyard:
            lanyard_msg = "<p>🧢 <strong>Your lanyard is on its way</strong> — bring it with you to help fellow fans spot you!</p>"
        else:
            lanyard_msg = f"<p>🧢 <strong>Don't forget:</strong> your free lanyard is still waiting. <a href=\"{current_app.config.get('BASE_URL', 'https://courtsideclub.app')}/login\">Log in to claim yours</a> so it arrives before the tournament.</p>"
        
        # Build schedule URL
        schedule_link = ""
        if hasattr(tournament, 'schedule_url') and tournament.schedule_url:
            schedule_link = f"<p>📅 Want to plan your visit? <a href=\"{tournament.schedule_url}\">Check the official tournament schedule</a>.</p>"
        
        reminder_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p>We're just two weeks away from <strong>the {tournament.name}</strong> — here's a quick look at your plans so you're ready to go:</p>

        <p><strong>🎾 Sessions You've Selected:</strong></p>
        <ul>
          <li>✅ {user_tournament.session_label}</li>
        </ul>

        <p><strong>👋 {meetup_count} other member{'s' if meetup_count != 1 else ''}</strong> are open to meeting up at these sessions.</p>

        <hr style="border:none; border-top:1px solid #ddd;">

        {lanyard_msg}

        {schedule_link}

        <p>📍 The tournament is taking place in <strong>{tournament.city}, {tournament.country}</strong>. Make sure to plan ahead for entry and transport.</p>

        <p>🎒 <strong>Pro tip:</strong> Bring sunscreen, a refillable water bottle, and your lanyard. The courtside energy is real — stay ready.</p>

        <hr style="border:none; border-top:1px solid #ddd;">

        <p>Need to make a change? <a href=\"{current_app.config.get('BASE_URL', 'https://courtsideclub.app')}/login\">Log in to update your sessions or raise your hand</a>.</p>

        <p>Thanks for being part of <strong>CourtSide Club</strong> — we can't wait to see you there!</p>

        <p style="color:#666;">– The CourtSide Club Team</p>
        """
        
        return send_email(
            to_email=user.email,
            subject=f"{tournament.name} is just 2 weeks away! 🎾",
            content_html=reminder_html
        )
        
    except Exception as e:
        logger.error(f"Error sending tournament reminder to user {user_id}: {str(e)}", exc_info=True)
        return False

def send_morning_of_email(user_id, tournament_id, session_date, session_name):
    """
    Send morning-of tournament email for specific session
    
    Args:
        user_id: User ID
        tournament_id: Tournament ID
        session_date: Date of the session (YYYY-MM-DD format)
        session_name: Session name (e.g., "Day", "Night")
    
    Send to users where:
    - UserTournament.attending == True
    - The current date matches one of the days in their session_label
    - User has not opted out of email
    """
    try:
        user = db.session.get(User, user_id)
        tournament = db.session.get(Tournament, tournament_id)
        
        if not user or not tournament:
            logger.error(f"User {user_id} or tournament {tournament_id} not found")
            return False
            
        # Check if user has opted out of emails
        if hasattr(user, 'notifications') and not user.notifications:
            logger.info(f"User {user.email} has opted out of emails")
            return False
            
        # Get user's tournament registration
        user_tournament = db.session.query(UserTournament).filter_by(
            user_id=user.id,
            tournament_id=tournament.id,
            attending=True
        ).first()
        
        if not user_tournament or not user_tournament.session_label:
            logger.info(f"User {user.email} not attending {tournament.name} or no sessions selected")
            return False
            
        # Check if user's session matches today's session
        session_label = user_tournament.session_label.lower()
        if session_name.lower() not in session_label:
            logger.info(f"User {user.email} not attending {session_name} session")
            return False
            
        # Count attendees for this specific session
        session_attendees = get_session_attendees_count(tournament.id, session_name)
        meetup_count = get_session_meetup_count(tournament.id, session_name)
        
        # Exclude current user from meetup count if they're open to meet
        if user_tournament.open_to_meet:
            meetup_count = max(0, meetup_count - 1)
        
        # Clean session display name (remove date formatting)
        session_display = f"{session_name} Session"
        
        # Meetup info (if set by admin)
        meetup_info = ""
        if hasattr(tournament, 'meetup_location') and hasattr(tournament, 'meetup_time') and tournament.meetup_location and tournament.meetup_time:
            meetup_info = f"<p>📍 <strong>Meet-up Spot:</strong> {tournament.meetup_location} at {tournament.meetup_time}</p>"
        
        # Lanyard reminder (only if user has lanyard)
        has_lanyard = getattr(user, 'lanyard_ordered', False)
        if has_lanyard:
            lanyard_msg = "<p>🟢 Don't forget your <strong>CourtSide Club</strong> lanyard so other members can find you!</p>"
        else:
            lanyard_msg = ""
        
        morning_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p><strong>It's game day!</strong> You're all set for <strong>{tournament.name}</strong>, and we're so glad you're part of it.</p>

        <p><strong>🎾 Today's Session:</strong> {session_display}<br>
        <strong>👥 {session_attendees} fan{'s' if session_attendees != 1 else ''}</strong> are attending — <strong>{meetup_count} open to meeting up</strong>.</p>

        {meetup_info}

        {lanyard_msg}

        <p>📸 Tag your meetups on Instagram <strong>@courtsideclub</strong> — we love seeing CSC in the wild!</p>

        <p>☀️ Soak up the vibe, say hey to fellow members, and enjoy your day courtside. The energy is real.</p>

        <p>– The CourtSide Club Team</p>
        """
        
        return send_email(
            to_email=user.email,
            subject=f"Today's the day! {tournament.name} – {session_name} Session 🎾",
            content_html=morning_html
        )
        
    except Exception as e:
        logger.error(f"Error sending morning-of email to user {user_id}: {str(e)}", exc_info=True)
        return False

def send_welcome_email(user_id):
    """Send welcome email to new users"""
    try:
        user = db.session.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False
            
        # Check if user has opted out of emails
        if hasattr(user, 'notifications') and not user.notifications:
            logger.info(f"User {user.email} has opted out of emails")
            return False
        
        # Get upcoming tournaments
        upcoming_tournaments = Tournament.query.filter(
            Tournament.start_date >= datetime.date.today()
        ).order_by(Tournament.start_date).limit(3).all()
        
        tournament_html = ""
        if upcoming_tournaments:
            tournament_lines = "".join([
                f"<li>🎾 {t.name} – {t.start_date.strftime('%B %d')}</li>" 
                for t in upcoming_tournaments
            ])
            tournament_html = f"<p>Some of the biggest tournaments coming up:</p><ul>{tournament_lines}</ul>"
        
        welcome_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p>Welcome to <strong>CourtSideClub</strong> – the community for tennis fans who want more than just a seat in the stands.</p>

        <p>Here's what you can do starting today:</p>
        <ul>
          <li>📍 Choose the tournaments you're attending</li>
          <li>🤝 Raise your hand to meet other fans</li>
          <li>🧢 Get your free lanyard to help you connect in person</li>
        </ul>

        {tournament_html}

        <p>Ready to dive in? <a href="{current_app.config.get('BASE_URL', 'https://courtsideclub.app')}/login">Log in to pick your tournaments</a> and join the community.</p>

        <p>Thanks for joining CourtSideClub — we're excited to have you with us!<br>
        – The CourtSideClub Team</p>
        """
        
        return send_email(
            to_email=user.email,
            subject="Welcome to CourtSideClub 🎾 Here's what's next",
            content_html=welcome_html
        )
        
    except Exception as e:
        logger.error(f"Error sending welcome email to user {user_id}: {str(e)}", exc_info=True)
        return False

def get_eligible_users_for_tournament_reminder(tournament_id, days_before=14):
    """Get users eligible for tournament reminder emails"""
    tournament = db.session.get(Tournament, tournament_id)
    if not tournament:
        return []
        
    # Calculate reminder date
    reminder_date = tournament.start_date - datetime.timedelta(days=days_before)
    today = datetime.date.today()
    
    if today != reminder_date:
        return []
    
    # Get eligible users
    eligible_users = db.session.query(User).join(UserTournament).filter(
        UserTournament.tournament_id == tournament_id,
        UserTournament.attending == True,
        UserTournament.session_label.isnot(None),
        UserTournament.session_label != '',
        User.notifications == True
    ).all()
    
    return eligible_users

def get_eligible_users_for_morning_email(tournament_id, session_date, session_name):
    """Get users eligible for morning-of emails for a specific session"""
    # Get eligible users for this specific session
    eligible_users = db.session.query(User).join(UserTournament).filter(
        UserTournament.tournament_id == tournament_id,
        UserTournament.attending == True,
        UserTournament.session_label.ilike(f'%{session_name}%'),
        User.notifications == True
    ).all()
    
    return eligible_users