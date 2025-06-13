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

def send_tournament_reminder_email(user_id, tournament_id, debug_email_override=None):
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
            to_email=debug_email_override or user.email,
            subject=f"{tournament.name} is just 2 weeks away! 🎾",
            content_html=reminder_html
        )
        
    except Exception as e:
        logger.error(f"Error sending tournament reminder to user {user_id}: {str(e)}", exc_info=True)
        return False

def send_morning_of_email(user_id, tournament_id, session_date, session_name, debug_email_override=None):
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
            to_email=debug_email_override or user.email,
            subject=f"Today's the day! {tournament.name} – {session_name} Session 🎾",
            content_html=morning_html
        )
        
    except Exception as e:
        logger.error(f"Error sending morning-of email to user {user_id}: {str(e)}", exc_info=True)
        return False

def send_welcome_email(user_id):
    """Send welcome email to new users with branded design"""
    try:
        user = db.session.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False
            
        # Check if user has opted out of emails
        if hasattr(user, 'notifications') and not user.notifications:
            logger.info(f"User {user.email} has opted out of emails")
            return False
        
        # Get upcoming Grand Slam and Masters 1000 tournaments only
        upcoming_tournaments = Tournament.query.filter(
            Tournament.start_date >= datetime.date.today(),
            Tournament.event_type.in_(['Grand Slam', 'Masters 1000'])
        ).order_by(Tournament.start_date).limit(2).all()
        
        # Get user's first name with fallback
        user_first_name = getattr(user, 'first_name', 'Member')
        
        # Generate tournament cards HTML
        tournament_cards_html = ""
        if upcoming_tournaments:
            for tournament in upcoming_tournaments:
                # Count registered users for this tournament
                registration_count = db.session.query(UserTournament).filter(
                    UserTournament.tournament_id == tournament.id,
                    UserTournament.attending == True
                ).count()
                
                # Format date range
                if tournament.start_date and tournament.end_date:
                    if tournament.start_date.month == tournament.end_date.month:
                        date_range = f"{tournament.start_date.strftime('%B %d')}-{tournament.end_date.strftime('%d, %Y')}"
                    else:
                        date_range = f"{tournament.start_date.strftime('%B %d')} - {tournament.end_date.strftime('%B %d, %Y')}"
                else:
                    date_range = tournament.start_date.strftime('%B %d, %Y') if tournament.start_date else "TBD"
                
                # Determine label and color
                if tournament.event_type == 'Grand Slam':
                    label = "Grand Slam"
                    label_color = "#EDB418"
                else:
                    label = "Masters 1000"
                    label_color = "#669127"
                
                tournament_cards_html += f"""
                <div style="border: 1px solid {label_color}33; border-radius: 8px; padding: 22px; background-color: white; margin-bottom: 15px;">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                    <div>
                      <h3 style="font-family: 'Crimson Text', Georgia, serif; font-size: 20px; margin: 0 0 5px 0; font-weight: 600;">{tournament.name}</h3>
                      <p style="margin: 0; font-size: 14px; color: #555;">{date_range}</p>
                      <p style="margin: 0; font-size: 14px; color: #555;">{tournament.location}</p>
                    </div>
                    <div style="background-color: {label_color}; color: #171717; font-size: 12px; padding: 4px 12px; border-radius: 20px; font-weight: 600; white-space: nowrap;">
                      {label}
                    </div>
                  </div>
                  <p style="font-size: 14px; margin-top: 18px; color: #171717;">
                    Join {registration_count}+ CourtSide Club members already registered
                  </p>
                </div>"""
        
        # Get base URL from config
        base_url = current_app.config.get('BASE_URL', 'https://courtsideclub.app')
        
        # Build the complete HTML email
        welcome_html = f"""
        <div style="max-width: 600px; margin: 0 auto; background-color: #FBFAFB; color: #171717; font-family: Inter, Arial, sans-serif; padding: 40px 30px;">
          
          <!-- Header -->
          <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="font-family: 'Crimson Text', Georgia, serif; font-size: 32px; font-weight: 600; margin: 0 0 10px 0;">
              Welcome to CourtSide Club
            </h1>
            <div style="height: 3px; width: 80px; background-color: #EDB418; margin: 0 auto 20px;"></div>
            <p style="font-size: 16px; line-height: 1.5; margin: 0;">
              You're now part of a discerning community that makes tennis more than just a spectator sport.
            </p>
          </div>

          <!-- Main Content -->
          <div style="margin-bottom: 40px;">
            <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
              Hi {user_first_name},
            </p>
            <p style="font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
              Welcome to CourtSide Club. We're thrilled you've joined our exclusive community of passionate tennis
              enthusiasts. Get ready to transform your match-day experience from a seat in the stands to an immersive
              connection with fellow fans who, like you, seek more from the world of tennis. Your membership opens the court
              to unparalleled camaraderie and elevated tournament moments.
            </p>

            <!-- Next Steps -->
            <div style="background-color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; border: 1px solid rgba(237, 180, 24, 0.2);">
              <h2 style="font-family: 'Crimson Text', Georgia, serif; font-size: 24px; margin-top: 0; margin-bottom: 25px; font-weight: 600;">
                Your Next Steps to Connect
              </h2>

              <div style="display: flex; align-items: flex-start; margin-bottom: 25px;">
                <div style="background-color: #669127; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 18px; flex-shrink: 0; border: 1px solid rgba(237, 180, 24, 0.3); font-weight: 700; font-size: 16px;">
                  1
                </div>
                <div>
                  <p style="margin: 0; font-size: 16px; font-weight: 600;">Choose Your Tournaments</p>
                  <p style="margin: 5px 0 0 0; font-size: 14px; color: #555;">Select the events you'll be attending this season to unlock connections with other members.</p>
                </div>
              </div>

              <div style="display: flex; align-items: flex-start; margin-bottom: 25px;">
                <div style="background-color: #669127; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 18px; flex-shrink: 0; border: 1px solid rgba(237, 180, 24, 0.3); font-weight: 700; font-size: 16px;">
                  2
                </div>
                <div>
                  <p style="margin: 0; font-size: 16px; font-weight: 600;">Complete Your Profile</p>
                  <p style="margin: 5px 0 0 0; font-size: 14px; color: #555;">Enhance your presence and discoverability within the club by sharing a bit more about your tennis journey.</p>
                </div>
              </div>

              <div style="display: flex; align-items: flex-start;">
                <div style="background-color: #669127; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 18px; flex-shrink: 0; border: 1px solid rgba(237, 180, 24, 0.3); font-weight: 700; font-size: 16px;">
                  3
                </div>
                <div>
                  <p style="margin: 0; font-size: 16px; font-weight: 600;">Claim Your Free Member Lanyard</p>
                  <p style="margin: 5px 0 0 0; font-size: 14px; color: #555;">Identify yourself as a valued member at events and access exclusive areas with your complimentary lanyard.</p>
                </div>
              </div>
            </div>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 35px 0;">
              <a href="{base_url}/login" style="background-color: #669127; color: white; padding: 16px 32px; border-radius: 4px; text-decoration: none; font-weight: 600; font-size: 16px; display: inline-block; letter-spacing: 0.3px;">
                Log In to Get Started
              </a>
            </div>

            <!-- Upcoming Tournaments -->"""
        
        # Add tournaments section if we have tournaments
        if tournament_cards_html:
            welcome_html += f"""
            <div style="margin-top: 40px;">
              <h2 style="font-family: 'Crimson Text', Georgia, serif; font-size: 24px; margin-bottom: 20px; font-weight: 600;">Upcoming Tournaments</h2>
              {tournament_cards_html}
            </div>"""
        
        welcome_html += """

          </div>

          <!-- Footer -->
          <div style="text-align: center; border-top: 1px solid #E5E5E5; padding-top: 30px; margin-top: 40px; font-family: 'Crimson Text', Georgia, serif; font-size: 20px; font-style: italic; color: #171717;">
            Tennis is better together.
            <div style="font-size: 14px; color: #666; margin-top: 20px;">
              <p>© 2024 CourtSide Club. All rights reserved.</p>
              <p>
                <a href="#" style="color: #669127; text-decoration: none; margin-right: 15px;">Privacy Policy</a>
                <a href="#" style="color: #669127; text-decoration: none;">Unsubscribe</a>
              </p>
            </div>
          </div>
        </div>
        """
        
        return send_email(
            to_email=user.email,
            subject="Welcome to CourtSide Club 🎾 Here's what's next",
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

def send_post_tournament_followup_email(user_id, tournament_id):
    """
    Send post-tournament follow-up email 1-2 days after user's last selected session
    
    Args:
        user_id: User ID
        tournament_id: Tournament ID
    
    Send to users where:
    - UserTournament.attending == True
    - Tournament has ended (based on user's last session)
    - User has not opted out of email
    - Email not already sent for this tournament
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
            
        # Count attendees who attended this tournament
        total_attendees = db.session.query(UserTournament).filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True
        ).count()
        
        # Count users who were open to meeting
        meetup_attendees = db.session.query(UserTournament).filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.open_to_meet == True
        ).count()
        
        # Get upcoming Grand Slam and Masters 1000 tournaments
        upcoming_tournaments = Tournament.query.filter(
            Tournament.start_date >= datetime.date.today(),
            Tournament.event_type.in_(['Grand Slam', 'Masters 1000'])
        ).order_by(Tournament.start_date).limit(3).all()
        
        # Generate upcoming tournaments HTML
        upcoming_tournaments_html = ""
        for tournament_item in upcoming_tournaments:
            # Format date range
            if tournament_item.start_date and tournament_item.end_date:
                if tournament_item.start_date.month == tournament_item.end_date.month:
                    date_range = f"{tournament_item.start_date.strftime('%B %d')}-{tournament_item.end_date.strftime('%d, %Y')}"
                else:
                    date_range = f"{tournament_item.start_date.strftime('%B %d')} - {tournament_item.end_date.strftime('%B %d, %Y')}"
            else:
                date_range = tournament_item.start_date.strftime('%B %d, %Y') if tournament_item.start_date else "TBD"
            
            # Determine event tag and color
            event_tag = "GRAND SLAM" if tournament_item.event_type == 'Grand Slam' else "MASTERS 1000"
            
            # Location formatting
            location = f"{tournament_item.city}, {tournament_item.country}" if tournament_item.city and tournament_item.country else tournament_item.location or "Location TBD"
            
            upcoming_tournaments_html += f"""
            <tr>
              <td style="padding: 15px; background-color: #FFFFFF; border-radius: 8px; margin-bottom: 15px; display: block;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                  <tr>
                    <td>
                      <span style="display: inline-block; background-color: #EDB418; color: #000000; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px; margin-bottom: 8px;">{event_tag}</span>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <p style="margin: 0 0 5px 0; font-family: 'Inter', Arial, sans-serif; font-size: 16px; font-weight: 600; color: #464C3F;">{tournament_item.name}</p>
                      <p style="margin: 0 0 5px 0; font-family: 'Inter', Arial, sans-serif; font-size: 14px; color: #464C3F;">{date_range}</p>
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-size: 14px; color: rgba(70, 76, 63, 0.8);">{location}</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            """ + ("" if tournament_item == upcoming_tournaments[-1] else """
            <tr>
              <td style="height: 15px;"></td>
            </tr>""")
        
        # Get base URL from config
        base_url = current_app.config.get('BASE_URL', 'https://courtsideclub.app')
        
        # Get user's first name with fallback
        user_first_name = getattr(user, 'first_name', 'Tennis Fan')
        
        followup_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>CourtSide Club - Post-Tournament Follow-Up</title>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600&display=swap');
          </style>
        </head>
        <body style="margin: 0; padding: 0; background-color: #FBFAFB; font-family: 'Inter', Arial, sans-serif; color: #464C3F;">
          <!-- Preview Text -->
          <div style="display: none; max-height: 0px; overflow: hidden;">
            Thanks for attending {tournament.name}! See what's coming up next at CourtSide Club.
          </div>
          
          <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" width="100%" style="max-width: 600px; margin: 0 auto;">
            <tr>
              <td style="padding: 40px 30px 30px 30px; text-align: center;">
                <!-- Header -->
                <h1 style="margin: 0; font-family: 'Crimson Text', Georgia, serif; font-size: 36px; font-weight: 600; color: #464C3F;">CourtSide Club</h1>
                <div style="height: 2px; background-color: #EDB418; width: 80px; margin: 15px auto 30px;"></div>
                
                <!-- Greeting & Main Message -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                  <tr>
                    <td style="padding: 0 0 20px 0; text-align: left;">
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-weight: 500; font-size: 18px; color: #464C3F;">Hey {user_first_name},</p>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 0; text-align: left;">
                      <p style="margin: 0 0 20px 0; font-family: 'Inter', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #464C3F;">Thank you for being part of CourtSide Club at {tournament.name}. We hope you had an unforgettable experience connecting with fellow tennis enthusiasts.</p>
                      
                      <p style="margin: 0 0 20px 0; font-family: 'Inter', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #464C3F;">You weren't the only one — over <strong>{total_attendees} CourtSide Club members</strong> went too!</p>
                      
                      <p style="margin: 0 0 30px 0; font-family: 'Inter', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #464C3F;">Already thinking about your next event? We'd love to have you back.</p>
                    </td>
                  </tr>
                </table>
                
                <!-- Upcoming Tournaments Section -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 30px;">
                  <tr>
                    <td style="padding: 0; text-align: left;">
                      <h2 style="margin: 0 0 20px 0; font-family: 'Crimson Text', Georgia, serif; font-size: 24px; font-weight: 700; color: #464C3F;">Upcoming Tournaments</h2>
                    </td>
                  </tr>
                  
                  {upcoming_tournaments_html}
                  
                </table>
                
                <!-- CTA Button -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 30px 0;">
                  <tr>
                    <td align="center">
                      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                          <td style="border-radius: 50px; background-color: #669127;">
                            <a href="{base_url}/blog" target="_blank" style="font-family: 'Inter', Arial, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 50px; padding: 14px 28px; border: 1px solid #669127; display: inline-block;">Visit the Blog →</a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
                
                <!-- Social Media Section -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 30px 0;">
                  <tr>
                    <td style="text-align: center; padding-bottom: 20px;">
                      <p style="margin: 0 0 15px 0; font-family: 'Inter', Arial, sans-serif; font-size: 16px; color: #464C3F;">Stay connected! Follow CourtSide Club for exclusive content and live updates.</p>
                      
                      <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 0 auto;">
                        <tr>
                          <!-- Instagram Icon -->
                          <td style="padding: 0 10px;">
                            <a href="https://instagram.com/courtsideclub" target="_blank" style="text-decoration: none;">
                              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 2.163C15.204 2.163 15.584 2.175 16.85 2.233C20.102 2.381 21.621 3.924 21.769 7.152C21.827 8.417 21.838 8.797 21.838 12.001C21.838 15.206 21.826 15.585 21.769 16.85C21.62 20.075 20.105 21.621 16.85 21.769C15.584 21.827 15.206 21.839 12 21.839C8.796 21.839 8.416 21.827 7.151 21.769C3.891 21.62 2.38 20.07 2.232 16.849C2.174 15.584 2.162 15.205 2.162 12C2.162 8.796 2.175 8.417 2.232 7.151C2.381 3.924 3.896 2.38 7.151 2.232C8.417 2.175 8.796 2.163 12 2.163ZM12 5.838C8.597 5.838 5.838 8.597 5.838 12S8.597 18.163 12 18.163S18.162 15.404 18.162 12S15.403 5.838 12 5.838ZM19.846 5.595C19.846 4.761 19.173 4.088 18.339 4.088C17.505 4.088 16.832 4.761 16.832 5.595C16.832 6.429 17.505 7.102 18.339 7.102C19.173 7.102 19.846 6.429 19.846 5.595ZM12 7.379C13.97 7.379 15.621 9.03 15.621 11C15.621 12.97 13.97 14.621 12 14.621C10.03 14.621 8.379 12.97 8.379 11C8.379 9.03 10.03 7.379 12 7.379Z" fill="#669127"/>
                              </svg>
                            </a>
                          </td>
                          
                          <!-- Twitter/X Icon -->
                          <td style="padding: 0 10px;">
                            <a href="https://x.com/courtsideclub" target="_blank" style="text-decoration: none;">
                              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M18.901 1.153H22.581L14.541 10.301L24 22.846H16.594L10.794 15.264L4.156 22.846H0.474L9.074 13.059L0 1.153H7.594L12.837 8.026L18.901 1.153ZM17.61 20.644H19.649L6.486 3.239H4.298L17.61 20.644Z" fill="#669127"/>
                              </svg>
                            </a>
                          </td>
                          
                          <!-- Facebook Icon -->
                          <td style="padding: 0 10px;">
                            <a href="https://facebook.com/courtsideclub" target="_blank" style="text-decoration: none;">
                              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M24 12C24 5.37258 18.6274 0 12 0C5.37258 0 0 5.37258 0 12C0 17.9895 4.3882 22.954 10.125 23.8542V15.4688H7.07812V12H10.125V9.35625C10.125 6.34875 11.9166 4.6875 14.6576 4.6875C15.9701 4.6875 17.3438 4.92188 17.3438 4.92188V7.875H15.8306C14.34 7.875 13.875 8.80008 13.875 9.75V12H17.2031L16.6711 15.4688H13.875V23.8542C19.6118 22.954 24 17.9895 24 12Z" fill="#669127"/>
                              </svg>
                            </a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
                
                <!-- Footer -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-top: 20px; border-top: 1px solid rgba(70, 76, 63, 0.2); padding-top: 20px;">
                  <tr>
                    <td style="text-align: center; padding-bottom: 15px;">
                      <p style="margin: 0; font-family: 'Crimson Text', Georgia, serif; font-style: italic; font-size: 18px; color: #464C3F;">Tennis is better together.</p>
                    </td>
                  </tr>
                  <tr>
                    <td style="text-align: center; padding-bottom: 20px;">
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-size: 14px; color: rgba(70, 76, 63, 0.8);">
                        <a href="{base_url}/privacy" target="_blank" style="color: rgba(70, 76, 63, 0.8); text-decoration: none; margin: 0 10px;">Privacy Policy</a> | 
                        <a href="{base_url}/unsubscribe" target="_blank" style="color: rgba(70, 76, 63, 0.8); text-decoration: none; margin: 0 10px;">Unsubscribe</a>
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td style="text-align: center;">
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-size: 12px; color: rgba(70, 76, 63, 0.8);">© 2025 CourtSide Club</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
        </html>
        """
        
        return send_email(
            to_email="richardbattlebaxter@gmail.com",  # Override for testing
            subject=f"How was {tournament.name}? 🎾",
            content_html=followup_html
        )
        
    except Exception as e:
        logger.error(f"Error sending post-tournament follow-up to user {user_id}: {str(e)}", exc_info=True)
        return False

def send_password_reset_email(to_email, first_name, reset_url):
    """
    Send password reset email with premium CourtSide Club branding
    
    Args:
        to_email: Recipient email address
        first_name: User's first name
        reset_url: Secure password reset URL with token
    """
    try:
        # Get base URL from config
        base_url = current_app.config.get('BASE_URL', 'https://courtsideclub.app')
        
        password_reset_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Reset Your CourtSide Club Password</title>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600&display=swap');
          </style>
        </head>
        <body style="margin: 0; padding: 0; background-color: #FBFAFB; font-family: 'Inter', Arial, sans-serif; color: #464C3F;">
          <!-- Preview Text -->
          <div style="display: none; max-height: 0px; overflow: hidden;">
            Reset your CourtSide Club password securely
          </div>
          
          <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" width="100%" style="max-width: 600px; margin: 0 auto;">
            <tr>
              <td style="padding: 40px 30px 30px 30px; text-align: center;">
                <!-- Header -->
                <h1 style="margin: 0; font-family: 'Crimson Text', Georgia, serif; font-size: 36px; font-weight: 600; color: #464C3F;">CourtSide Club</h1>
                <div style="height: 2px; background-color: #EDB418; width: 80px; margin: 15px auto 30px;"></div>
                
                <!-- Main Content -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                  <tr>
                    <td style="padding: 0 0 20px 0; text-align: left;">
                      <h2 style="margin: 0 0 20px 0; font-family: 'Crimson Text', Georgia, serif; font-size: 24px; font-weight: 700; color: #464C3F;">Reset Your Password</h2>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 0; text-align: left;">
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-weight: 500; font-size: 18px; color: #464C3F;">Hey {first_name},</p>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 20px 0; text-align: left;">
                      <p style="margin: 0 0 20px 0; font-family: 'Inter', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #464C3F;">We received a request to reset your CourtSide Club password. Click the button below to create a new password:</p>
                    </td>
                  </tr>
                </table>
                
                <!-- Reset Button -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 30px 0;">
                  <tr>
                    <td align="center">
                      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                        <tr>
                          <td style="border-radius: 50px; background-color: #669127;">
                            <a href="{reset_url}" target="_blank" style="font-family: 'Inter', Arial, sans-serif; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 50px; padding: 16px 32px; border: 1px solid #669127; display: inline-block;">Reset My Password</a>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
                
                <!-- Security Info -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 30px 0; background-color: #ffffff; border-radius: 8px; padding: 20px;">
                  <tr>
                    <td style="text-align: left;">
                      <h3 style="margin: 0 0 15px 0; font-family: 'Inter', Arial, sans-serif; font-size: 16px; font-weight: 600; color: #464C3F;">Security Information</h3>
                      <ul style="margin: 0; padding-left: 20px; font-family: 'Inter', Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #464C3F;">
                        <li style="margin-bottom: 8px;">This link will expire in 1 hour for your security</li>
                        <li style="margin-bottom: 8px;">If you didn't request this reset, you can safely ignore this email</li>
                        <li style="margin-bottom: 0;">Your current password remains unchanged until you create a new one</li>
                      </ul>
                    </td>
                  </tr>
                </table>
                
                <!-- Alternative Link -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: 20px 0;">
                  <tr>
                    <td style="text-align: left;">
                      <p style="margin: 0 0 10px 0; font-family: 'Inter', Arial, sans-serif; font-size: 14px; color: #464C3F;">If the button doesn't work, copy and paste this link into your browser:</p>
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-size: 14px; word-break: break-all; color: #669127;">
                        <a href="{reset_url}" style="color: #669127; text-decoration: none;">{reset_url}</a>
                      </p>
                    </td>
                  </tr>
                </table>
                
                <!-- Footer -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-top: 40px; border-top: 1px solid rgba(70, 76, 63, 0.2); padding-top: 20px;">
                  <tr>
                    <td style="text-align: center; padding-bottom: 15px;">
                      <p style="margin: 0; font-family: 'Crimson Text', Georgia, serif; font-style: italic; font-size: 18px; color: #464C3F;">Tennis is better together.</p>
                    </td>
                  </tr>
                  <tr>
                    <td style="text-align: center; padding-bottom: 20px;">
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-size: 14px; color: rgba(70, 76, 63, 0.8);">
                        <a href="{base_url}/privacy" target="_blank" style="color: rgba(70, 76, 63, 0.8); text-decoration: none; margin: 0 10px;">Privacy Policy</a> | 
                        <a href="{base_url}/contact" target="_blank" style="color: rgba(70, 76, 63, 0.8); text-decoration: none; margin: 0 10px;">Contact Support</a>
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td style="text-align: center;">
                      <p style="margin: 0; font-family: 'Inter', Arial, sans-serif; font-size: 12px; color: rgba(70, 76, 63, 0.8);">© 2025 CourtSide Club</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
        </html>
        """
        
        return send_email(
            to_email="richardbattlebaxter@gmail.com",  # Override for testing
            subject="Reset your CourtSide Club password",
            content_html=password_reset_html
        )
        
    except Exception as e:
        logger.error(f"Error sending password reset email to {to_email}: {str(e)}", exc_info=True)
        return False

# Lanyard order confirmation email function removed - functionality discontinued

# Lanyard delivery reminder email function removed - functionality discontinued