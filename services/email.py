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
        
        followup_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p>What a tournament! We hope you had an incredible time at <strong>{tournament.name}</strong>.</p>

        <p><strong>🎾 Your Sessions:</strong> {user_tournament.session_label}</p>

        <p><strong>👥 The Numbers:</strong> {total_attendees} CourtSide Club members attended, with {meetup_attendees} open to meeting up. Pretty amazing community, right?</p>

        <p>📸 <strong>Share Your Experience:</strong> Did you snap any great courtside moments or meet fellow members? Tag us <strong>@courtsideclub</strong> on Instagram — we love seeing the community in action!</p>

        <p>🎾 <strong>What's Next:</strong> Keep an eye out for upcoming tournaments. The tennis calendar never stops, and neither does the CourtSide Club community.</p>

        <p>Thanks for being part of something special. Until the next tournament!</p>

        <p style="color:#666;">– The CourtSide Club Team</p>
        """
        
        return send_email(
            to_email="richardbattlebaxter@gmail.com",  # Override for testing
            subject=f"How was {tournament.name}? 🎾",
            content_html=followup_html
        )
        
    except Exception as e:
        logger.error(f"Error sending post-tournament follow-up to user {user_id}: {str(e)}", exc_info=True)
        return False

# Lanyard order confirmation email function removed - functionality discontinued

# Lanyard delivery reminder email function removed - functionality discontinued