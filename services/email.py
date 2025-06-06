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

def send_lanyard_order_confirmation_email(user_id):
    """
    Send lanyard order confirmation email immediately after order submission
    
    Args:
        user_id: User ID who placed the order
    """
    try:
        user = db.session.get(User, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False
            
        # Check if user has opted out of emails
        if hasattr(user, 'notifications') and not user.notifications:
            logger.info(f"User {user.email} has opted out of emails")
            return False
        
        # Get shipping address
        from models import ShippingAddress
        shipping_address = ShippingAddress.query.filter_by(user_id=user.id).first()
        
        shipping_info = ""
        if shipping_address:
            shipping_info = f"""
            <p><strong>📦 Shipping Details:</strong></p>
            <p>{shipping_address.name}<br>
            {shipping_address.address1}<br>
            {shipping_address.address2 + '<br>' if shipping_address.address2 else ''}
            {shipping_address.city}, {shipping_address.state} {shipping_address.zip_code}<br>
            {shipping_address.country}</p>
            """
        
        confirmation_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p><strong>Your lanyard is on the way!</strong> 🎉</p>

        <p>We've received your lanyard order and it's heading into production. You should receive it within 7-10 business days.</p>

        {shipping_info}

        <p><strong>🧢 What's the lanyard for?</strong> Your CourtSide Club lanyard helps other members spot you at tournaments — it's like a friendly signal that you're part of the community and open to connecting.</p>

        <p><strong>📅 Pro tip:</strong> Bring your lanyard to any tournament you're attending. It's amazing how many conversations start with "Hey, are you part of CourtSide Club too?"</p>

        <p>Questions about your order? Just reply to this email and we'll help you out.</p>

        <p>Thanks for being part of <strong>CourtSide Club</strong>!</p>

        <p style="color:#666;">– The CourtSide Club Team</p>
        """
        
        return send_email(
            to_email="richardbattlebaxter@gmail.com",  # Override for testing
            subject="Your CourtSide Club lanyard is on the way! 🧢",
            content_html=confirmation_html
        )
        
    except Exception as e:
        logger.error(f"Error sending lanyard confirmation to user {user_id}: {str(e)}", exc_info=True)
        return False

def send_lanyard_delivery_reminder_email(user_id, tournament_id, session_date, session_name):
    """
    Send lanyard delivery reminder 2-3 days before each session for users with lanyard orders
    
    Args:
        user_id: User ID
        tournament_id: Tournament ID  
        session_date: Date of the session
        session_name: Session name (e.g., "Day", "Night")
    
    Send to users where:
    - UserTournament.attending == True
    - User.lanyard_ordered == True
    - Session is 2-3 days away
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
            
        # Check if user has lanyard ordered
        if not getattr(user, 'lanyard_ordered', False):
            logger.info(f"User {user.email} has not ordered a lanyard")
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
            
        # Count attendees for this specific session
        session_attendees = get_session_attendees_count(tournament.id, session_name)
        meetup_count = get_session_meetup_count(tournament.id, session_name)
        
        # Exclude current user from meetup count if they're open to meet
        if user_tournament.open_to_meet:
            meetup_count = max(0, meetup_count - 1)
        
        # Clean session display name
        session_display = f"{session_name} Session"
        
        # Calculate days until session
        try:
            session_date_obj = datetime.datetime.strptime(session_date, '%Y-%m-%d').date()
            days_until = (session_date_obj - datetime.date.today()).days
            timing_msg = f"in {days_until} day{'s' if days_until != 1 else ''}"
        except:
            timing_msg = "soon"
        
        reminder_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p><strong>Don't forget your lanyard!</strong> 🧢</p>

        <p>Your <strong>{tournament.name}</strong> session is coming up {timing_msg}, and your CourtSide Club lanyard is the perfect way to connect with fellow members.</p>

        <p><strong>🎾 Your Session:</strong> {session_display}<br>
        <strong>👥 {session_attendees} fan{'s' if session_attendees != 1 else ''}</strong> attending — <strong>{meetup_count} open to meeting up</strong></p>

        <p><strong>🟢 Why bring your lanyard?</strong> It's like a friendly beacon that says "I'm part of CourtSide Club too!" — perfect for sparking conversations and finding your tennis community at the tournament.</p>

        <p>📸 Tag your meetups on Instagram <strong>@courtsideclub</strong> when you're there. We love seeing the community in action!</p>

        <p>🌟 Have an amazing time at <strong>{tournament.name}</strong>. The energy courtside is incredible when you're surrounded by fellow tennis fans.</p>

        <p style="color:#666;">– The CourtSide Club Team</p>
        """
        
        return send_email(
            to_email="richardbattlebaxter@gmail.com",  # Override for testing
            subject=f"Bring your lanyard to {tournament.name}! 🧢",
            content_html=reminder_html
        )
        
    except Exception as e:
        logger.error(f"Error sending lanyard delivery reminder to user {user_id}: {str(e)}", exc_info=True)
        return False