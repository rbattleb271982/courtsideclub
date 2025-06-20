from flask import Blueprint, jsonify, render_template
from models import db, User, Tournament, UserTournament, BlogPost
from services.sendgrid_service import send_email
import logging
import os
import sys
import traceback
import datetime
import textwrap
from werkzeug.security import generate_password_hash

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize blueprint
debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug/system-info')
def system_info():
    """Route to check system configuration and database connection"""
    try:
        # Check database connection and count users
        user_count = User.query.count()
        tournament_count = Tournament.query.count()

        # Database URL (with password hidden)
        db_url = os.environ.get('DATABASE_URL', '')
        if '://' in db_url:
            parts = db_url.split('://')
            if '@' in parts[1]:
                # Hide password in connection string
                userpass, hostdbname = parts[1].split('@', 1)
                if ':' in userpass:
                    user, _ = userpass.split(':', 1)
                    masked_url = f"{parts[0]}://{user}:****@{hostdbname}"
                else:
                    masked_url = f"{parts[0]}://{userpass}@{hostdbname}"
            else:
                masked_url = db_url
        else:
            masked_url = "Not in standard format"

        # Check database columns
        columns_info = {}
        try:
            with db.engine.connect() as conn:
                result = conn.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                """)
                columns_info['users'] = [row[0] for row in result]
        except Exception as e:
            columns_info['error'] = str(e)

        return jsonify({
            'status': 'ok',
            'database': {
                'connected': True,
                'user_count': user_count,
                'tournament_count': tournament_count,
                'url': masked_url,
                'columns': columns_info
            },
            'environment': {
                'python_version': sys.version,
                'env_vars': [k for k in os.environ.keys() if not k.startswith('_')]
            }
        })
    except Exception as e:
        logger.error(f"Error in system info: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debug_bp.route('/debug/test-user-creation')
def test_user_creation():
    """Test user creation in the database"""
    try:
        # Create a test user with a unique email
        import random
        import string
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        test_email = f"test_{random_str}@example.com"

        # Create a new test user
        test_user = User(
            email=test_email,
            first_name="Debug",
            last_name="User",
            name="Debug User",
            password_hash=generate_password_hash("password123"),
            notifications=True
        )

        # Save to database
        db.session.add(test_user)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': f'Created test user with email {test_email}',
            'user_id': test_user.id
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating test user: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debug_bp.route('/debug/error-simulation')
def error_simulation():
    """Simulate different types of errors to test error handling"""
    try:
        # Intentionally cause a database error
        error_type = "database"

        if error_type == "database":
            # Try to access a non-existent table
            result = db.session.execute("SELECT * FROM non_existent_table")
            return jsonify({'result': [dict(row) for row in result]})

        return jsonify({'message': 'No error simulation selected'})
    except Exception as e:
        logger.error(f"Simulated error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
@debug_bp.route('/debug/tournament-dates')
def tournament_dates():
    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    dates = [{"name": t.name, "start": t.start_date.strftime('%Y-%m-%d'), "end": t.end_date.strftime('%Y-%m-%d')} for t in tournaments]
    return jsonify(dates)

@debug_bp.route('/test-email')
@debug_bp.route('/test-email/<email>')
def test_email(email=None):
    """Test sending an email via SendGrid"""
    from services.sendgrid_service import send_email
    import os

    # Use provided email or default
    recipient_email = email if email else 'your_email@example.com'

    # Get API key (for debugging purposes)
    api_key = os.environ.get('SENDGRID_API_KEY')
    api_key_status = "Not provided" if not api_key else f"Provided (length: {len(api_key)})"

    # Get FROM_EMAIL from config
    from flask import current_app
    from_email = current_app.config.get('FROM_EMAIL', 'noreply@letcourtside.com')

    # Send the email
    status_code = send_email(
        to_email=recipient_email,
        subject='LetCourtSide Test Email',
        content_html='<p>This is a test email from LetCourtSide 🎾</p>'
    )

    # Prepare the result message
    if status_code:
        message = f"""
        <h1>Email Test Successful</h1>
        <p><strong>Status Code:</strong> {status_code}</p>
        <p><strong>Sent to:</strong> {recipient_email}</p>
        <p><strong>From:</strong> {from_email}</p>
        <p><strong>API Key Status:</strong> {api_key_status}</p>
        <p>Check your inbox for the test email!</p>
        """
        return message
    else:
        message = f"""
        <h1>Email Test Failed</h1>
        <p><strong>Recipient:</strong> {recipient_email}</p>
        <p><strong>From:</strong> {from_email}</p>
        <p><strong>API Key Status:</strong> {api_key_status}</p>
        <p>Please check the server logs for details. Errors are usually related to:</p>
        <ul>
            <li>Invalid API key</li>
            <li>Unverified sender domain/email</li>
            <li>SendGrid account restrictions</li>
        </ul>
        """
        return message
@debug_bp.route('/debug/send-welcome/<int:user_id>')
def send_welcome_email(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return f"User with ID {user_id} not found", 404

    # Get user's name or use a default greeting
    user_name = user.first_name if hasattr(user, 'first_name') and user.first_name else "Tennis Fan"

    upcoming_tournaments = [
        {"name": "Rome Masters", "date": "May 20"},
        {"name": "Roland-Garros", "date": "May 26"},
        {"name": "Queen's Club", "date": "June 17"}
    ]

    tournament_lines = "".join([
        f"<li>🎾 {t['name']} – {t['date']}</li>" for t in upcoming_tournaments
    ])
    tournament_html = f"<ul>{tournament_lines}</ul>"

    welcome_email_html = f"""
    <p>Hi {user_name},</p>

    <p>Welcome to <strong>LetCourtSide</strong> – the community for tennis fans who want more than just a seat in the stands.</p>

    <p>Here's what you can do starting today:</p>
    <ul>
      <li>📍 Choose the tournaments you're attending</li>
      <li>🤝 Raise your hand to meet other fans</li>
      <li>🧢 Get your free lanyard to help you connect in person</li>
    </ul>

    <p>Some of the biggest tournaments coming up:</p>
    {tournament_html}

    <p>Ready to dive in? <a href="https://bafb033d-26a4-47de-b4d6-96666ed788fe-00-2cbmkxn1203ip.kirk.replit.dev/login">Log in to pick your tournaments</a> and join the community.</p>

    <p>Thanks for joining LetCourtSide — we're excited to have you with us!<br>
    – The LetCourtSide Team</p>
    """

    send_email(
        to_email="richardbattlebaxter@gmail.com",
        subject="Welcome to LetCourtSide 🎾 Here's what's next",
        content_html=welcome_email_html
    )

    return f"Welcome email sent to richardbattlebaxter@gmail.com (test user: {user.email})"

@debug_bp.route('/debug/send-reminder/<int:user_id>/<tournament_slug>')
def send_reminder(user_id, tournament_slug):
    from models import User, Tournament, UserTournament

    user = db.session.get(User, user_id)
    tournament = Tournament.query.filter_by(slug=tournament_slug).first()

    if not user or not tournament:
        return "Invalid user or tournament slug", 404

    # Lanyard functionality has been discontinued
    has_lanyard = False

    # Get sessions user selected and meeting status
    meetup_msg = ""
    lanyard_msg = ""

    # Get user's tournament registration
    user_tournament = db.session.query(UserTournament).filter_by(
        user_id=user.id,
        tournament_id=tournament.id,
        attending=True
    ).first()

    # Build session info with meetup counts
    session_lines = ""
    if user_tournament and user_tournament.session_label:
        # Count others who are attending this tournament and open to meeting
        count = db.session.query(UserTournament).filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.open_to_meet == True,
            UserTournament.user_id != user.id,
            UserTournament.attending == True
        ).count()

        count_line = (
            f"– <strong>{count} other fan{'s' if count != 1 else ''}</strong> who are open to meeting up"
            if count > 0 else
            "– you're the first to raise your hand for this one!"
        )
        session_lines += f"<li>✅ {user_tournament.session_label} {count_line}</li>"

    # Final HTML for session summary
    session_summary_html = (
        f"<p>Here are the sessions you've selected:</p><ul>{session_lines}</ul>"
        if session_lines else
        "<p>You haven't selected any sessions for this tournament yet.</p>"
    )

    # Determine meeting message based on user's preferences
    open_to_meet = user_tournament and user_tournament.open_to_meet if user_tournament else False
    meetup_msg = (
        "<p>👋 Great news — you're set to meet other fans at the tournament! We'll send you final details about meeting spots soon.</p>"
        if open_to_meet else
        "<p>Want to meet other fans? <a href=\"https://bafb033d-26a4-47de-b4d6-96666ed788fe-00-2cbmkxn1203ip.kirk.replit.dev/login\">Update your preferences</a> to join the meetup.</p>"
    )

    # Build lanyard message
    lanyard_msg = (
        "<p>🎉 Your lanyard is on its way — bring it with you to help fellow fans spot you!</p>"
        if has_lanyard else
        '<p>🧢 Don’t forget — your free lanyard is still waiting. <a href="https://bafb033d-26a4-47de-b4d6-96666ed788fe-00-2cbmkxn1203ip.kirk.replit.dev/login">Log in to claim yours</a> so it arrives before the tournament!</p>'
    )

    reminder_html = f"""
    <p>Hi {user.first_name},</p>

    <p>We're two weeks away from <strong>{tournament.name}</strong>, and we want to make sure you're ready.</p>

    {session_summary_html}

    {lanyard_msg}

    <p>🗓 Want to plan your day? <a href="{tournament.schedule_url}">Check the official tournament schedule</a>.</p>

    <p>📍 The tournament takes place in <strong>{tournament.city}, {tournament.country}</strong>. Make sure to plan ahead for entry and transport.</p>

    <p>🎒 Pro tip: bring sunscreen, a refillable water bottle, and your lanyard. The courtside energy is real — stay ready.</p>

    <p>Need to make a change? You can <a href="https://bafb033d-26a4-47de-b4d6-96666ed788fe-00-2cbmkxn1203ip.kirk.replit.dev/login">log into your account</a> anytime to update your session or raise your hand.</p>

    <p>Thanks for being part of LetCourtSide — we can't wait to see you there!<br>
    – The LetCourtSide Team</p>
    """

    send_email(
        to_email="richardbattlebaxter@gmail.com",
        subject=f"{tournament.name} is just 2 weeks away! 🎾",
        content_html=reminder_html
    )

    return f"Tournament reminder sent to richardbattlebaxter@gmail.com (test user: {user.email})"

@debug_bp.route('/debug/send_test_email')
def send_test_email():
    """Send a basic test email using SendGrid"""
    from services.sendgrid_service import send_email
    import os
    from flask import current_app
    
    # Your test email address
    test_email = "richardbattlebaxter@gmail.com"
    
    # Get FROM_EMAIL from config
    from_email = current_app.config.get('FROM_EMAIL', 'noreply@letcourtside.com')
    
    # Check if SendGrid API key is available
    api_key = os.environ.get('SENDGRID_API_KEY')
    api_key_status = "Not provided" if not api_key else f"Available (length: {len(api_key)})"
    
    # Send the test email
    try:
        success = send_email(
            to_email=test_email,
            subject='CourtSide Club - Debug Test Email',
            content_html='''
            <h2>Debug Test Email</h2>
            <p>This is a test email from the CourtSide Club debug system.</p>
            <p><strong>Purpose:</strong> Testing SendGrid email functionality</p>
            <p><strong>Timestamp:</strong> {}</p>
            <p>If you received this email, the SendGrid integration is working correctly!</p>
            '''.format(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
        )
        
        if success:
            return f'''
            <h1>✅ Email Test Successful</h1>
            <p><strong>Sent to:</strong> {test_email}</p>
            <p><strong>From:</strong> {from_email}</p>
            <p><strong>API Key Status:</strong> {api_key_status}</p>
            <p><strong>Result:</strong> Email sent successfully</p>
            <p>Check your inbox for the test email!</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        else:
            return f'''
            <h1>❌ Email Test Failed</h1>
            <p><strong>Recipient:</strong> {test_email}</p>
            <p><strong>From:</strong> {from_email}</p>
            <p><strong>API Key Status:</strong> {api_key_status}</p>
            <p><strong>Result:</strong> Email sending failed</p>
            <p>Common issues:</p>
            <ul>
                <li>Invalid or missing SendGrid API key</li>
                <li>Unverified sender domain/email</li>
                <li>SendGrid account restrictions</li>
                <li>Network connectivity issues</li>
            </ul>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
            
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}", exc_info=True)
        return f'''
        <h1>❌ Email Test Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><strong>API Key Status:</strong> {api_key_status}</p>
        <p>Check the server logs for detailed error information.</p>
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        ''', 500

@debug_bp.route('/debug/send_tournament_reminder')
@debug_bp.route('/debug/send_tournament_reminder/<int:user_id>/<int:tournament_id>')
def send_tournament_reminder_debug(user_id=None, tournament_id=None):
    """Debug route to test tournament reminder email"""
    from services.email import send_tournament_reminder_email
    
    try:
        # Use default test values if not provided
        if not user_id:
            # Find a test user with tournament attendance
            test_user = db.session.query(User).join(UserTournament).filter(
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                User.notifications == True
            ).first()
            if test_user:
                user_id = test_user.id
            else:
                return '''
                <h1>❌ No Test User Found</h1>
                <p>No users found with tournament attendance and notifications enabled.</p>
                <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
                '''
        
        if not tournament_id:
            # Find a tournament this user is attending
            user_tournament = db.session.query(UserTournament).filter_by(
                user_id=user_id,
                attending=True
            ).first()
            if user_tournament:
                tournament_id = user_tournament.tournament_id
            else:
                return '''
                <h1>❌ No Tournament Found</h1>
                <p>User is not attending any tournaments.</p>
                <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
                '''
        
        # Get user and tournament details
        user = db.session.get(User, user_id)
        tournament = db.session.get(Tournament, tournament_id)
        
        if not user or not tournament:
            return f'''
            <h1>❌ Invalid User or Tournament</h1>
            <p>User ID: {user_id}, Tournament ID: {tournament_id}</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        
        # Send the reminder email to your address for testing
        from services.sendgrid_service import send_email
        from services.email import get_session_attendees_count, get_session_meetup_count
        from flask import current_app
        
        # Get user's tournament registration
        user_tournament = db.session.query(UserTournament).filter_by(
            user_id=user.id,
            tournament_id=tournament.id,
            attending=True
        ).first()
        
        if not user_tournament or not user_tournament.session_label:
            return '''
            <h1>❌ No Session Data</h1>
            <p>User is not attending tournament or has no sessions selected.</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        
        # Count attendees and meetup users
        attendees_count = get_session_attendees_count(tournament.id, user_tournament.session_label)
        meetup_count = get_session_meetup_count(tournament.id, user_tournament.session_label)
        
        # Exclude current user from meetup count if they're open to meet
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
            meetup_msg = f"<p>Want to meet other fans? <a href=\"https://letcourtside.com/login\">Update your preferences</a> to join the meetup.</p>"
        
        # Lanyard message - functionality discontinued
        lanyard_msg = ""
        
        # Build schedule URL
        schedule_link = ""
        if hasattr(tournament, 'schedule_url') and tournament.schedule_url:
            schedule_link = f"<p>🗓 Want to plan your day? <a href=\"{tournament.schedule_url}\">Check the official tournament schedule</a>.</p>"
        
        reminder_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p>We're two weeks away from <strong>{tournament.name}</strong>, and we want to make sure you're ready.</p>

        {session_summary}

        {lanyard_msg}

        {schedule_link}

        <p>📍 The tournament takes place in <strong>{tournament.city}, {tournament.country}</strong>. Make sure to plan ahead for entry and transport.</p>

        <p>🎒 Pro tip: bring sunscreen, a refillable water bottle, and your lanyard. The courtside energy is real — stay ready.</p>

        <p>Need to make a change? You can <a href=\"https://letcourtside.com/login\">log into your account</a> anytime to update your session or raise your hand.</p>

        <p>Thanks for being part of LetCourtSide — we can't wait to see you there!<br>
        – The LetCourtSide Team</p>
        """
        
        # Send directly to your email
        success = send_email(
            to_email="richardbattlebaxter@gmail.com",
            subject=f"{tournament.name} is just 2 weeks away! 🎾",
            content_html=reminder_html
        )
        
        if success:
            return f'''
            <h1>✅ Tournament Reminder Sent</h1>
            <p><strong>User:</strong> {user.email} ({getattr(user, 'first_name', 'No name')})</p>
            <p><strong>Tournament:</strong> {tournament.name}</p>
            <p><strong>Location:</strong> {tournament.city}, {tournament.country}</p>
            <p><strong>Dates:</strong> {tournament.start_date} to {tournament.end_date}</p>
            <p>Check the recipient's inbox for the reminder email!</p>
            <p><a href="/debug/send_test_email">Send Test Email</a> | <a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        else:
            return f'''
            <h1>❌ Tournament Reminder Failed</h1>
            <p><strong>User:</strong> {user.email}</p>
            <p><strong>Tournament:</strong> {tournament.name}</p>
            <p>Check server logs for detailed error information.</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
            
    except Exception as e:
        logger.error(f"Error in tournament reminder debug: {str(e)}", exc_info=True)
        return f'''
        <h1>❌ Debug Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        ''', 500

@debug_bp.route('/debug/send_morning_email')
@debug_bp.route('/debug/send_morning_email/<int:user_id>/<int:tournament_id>/<session_date>/<session_name>')
def send_morning_email_debug(user_id=None, tournament_id=None, session_date=None, session_name=None):
    """Debug route to test morning-of tournament email"""
    from services.email import send_morning_of_email
    
    try:
        # Use default test values if not provided
        if not user_id:
            # Find a test user with tournament attendance
            test_user = db.session.query(User).join(UserTournament).filter(
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                User.notifications == True
            ).first()
            if test_user:
                user_id = test_user.id
            else:
                return '''
                <h1>❌ No Test User Found</h1>
                <p>No users found with tournament attendance and notifications enabled.</p>
                <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
                '''
        
        if not tournament_id:
            # Find a tournament this user is attending
            user_tournament = db.session.query(UserTournament).filter_by(
                user_id=user_id,
                attending=True
            ).first()
            if user_tournament:
                tournament_id = user_tournament.tournament_id
            else:
                return '''
                <h1>❌ No Tournament Found</h1>
                <p>User is not attending any tournaments.</p>
                <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
                '''
        
        # Default session info if not provided
        if not session_date:
            session_date = datetime.datetime.now().strftime('%Y-%m-%d')
        if not session_name:
            session_name = "Day"
        
        # Get user and tournament details
        user = db.session.get(User, user_id)
        tournament = db.session.get(Tournament, tournament_id)
        
        if not user or not tournament:
            return f'''
            <h1>❌ Invalid User or Tournament</h1>
            <p>User ID: {user_id}, Tournament ID: {tournament_id}</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        
        # Use the updated send_morning_of_email function with override for testing
        from services.email import send_morning_of_email
        from services.sendgrid_service import send_email
        from services.email import get_session_attendees_count, get_session_meetup_count
        
        # Get user's tournament registration
        user_tournament = db.session.query(UserTournament).filter_by(
            user_id=user.id,
            tournament_id=tournament.id,
            attending=True
        ).first()
        
        if not user_tournament or not user_tournament.session_label:
            return '''
            <h1>❌ No Session Data</h1>
            <p>User is not attending tournament or has no sessions selected.</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        
        # Check if user's session matches the requested session
        session_label = user_tournament.session_label.lower()
        if session_name.lower() not in session_label:
            # Still send test email even if session doesn't match exactly
            pass
            
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
        
        # Lanyard reminder - functionality discontinued
        lanyard_msg = ""
        
        morning_html = f"""
        <p>Hi {getattr(user, 'first_name', 'Tennis Fan')},</p>

        <p><strong>It's game day!</strong> You're all set for <strong>{tournament.name}</strong>, and we're so glad you're part of it.</p>

        <p><strong>🎾 Today's Session:</strong> {session_display}<br>
        <strong>👥 {session_attendees} fan{'s' if session_attendees != 1 else ''}</strong> are attending — <strong>{meetup_count} open to meeting up</strong>.</p>

        {meetup_info}

        {lanyard_msg}

        <p>📸 Tag your meetups on Instagram <strong>@letcourtside</strong> — we love seeing CSC in the wild!</p>

        <p>☀️ Soak up the vibe, say hey to fellow members, and enjoy your day courtside. The energy is real.</p>

        <p>– The LetCourtSide Team</p>
        """
        
        success = send_email(
            to_email="richardbattlebaxter@gmail.com",
            subject=f"Today's the day! {tournament.name} – {session_name} Session 🎾",
            content_html=morning_html
        )
        
        if success:
            return f'''
            <h1>✅ Morning-Of Email Sent</h1>
            <p><strong>User:</strong> {user.email} ({getattr(user, 'first_name', 'No name')})</p>
            <p><strong>Tournament:</strong> {tournament.name}</p>
            <p><strong>Session:</strong> {session_date} – {session_name} Session</p>
            <p><strong>Location:</strong> {tournament.city}, {tournament.country}</p>
            <p>Check the recipient's inbox for the morning-of email!</p>
            <p><a href="/debug/send_test_email">Send Test Email</a> | <a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        else:
            return f'''
            <h1>❌ Morning-Of Email Failed</h1>
            <p><strong>User:</strong> {user.email}</p>
            <p><strong>Tournament:</strong> {tournament.name}</p>
            <p><strong>Session:</strong> {session_date} – {session_name}</p>
            <p>Check server logs for detailed error information.</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
            
    except Exception as e:
        logger.error(f"Error in morning email debug: {str(e)}", exc_info=True)
        return f'''
        <h1>❌ Debug Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        ''', 500

@debug_bp.route('/debug/send_welcome_email')
@debug_bp.route('/debug/send_welcome_email/<int:user_id>')
def send_welcome_email_debug(user_id=None):
    """Debug route to test welcome email"""
    from services.email import send_welcome_email
    
    try:
        # Use default test user if not provided
        if not user_id:
            # Find a test user
            test_user = db.session.query(User).filter(
                User.notifications == True
            ).first()
            if test_user:
                user_id = test_user.id
            else:
                return '''
                <h1>❌ No Test User Found</h1>
                <p>No users found with notifications enabled.</p>
                <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
                '''
        
        # Get user details
        user = db.session.get(User, user_id)
        if not user:
            return f'''
            <h1>❌ Invalid User</h1>
            <p>User ID: {user_id}</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        
        # Send the welcome email to your address for testing
        from services.sendgrid_service import send_email
        
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

        <p>Ready to dive in? <a href="https://courtsideclub.app/login">Log in to pick your tournaments</a> and join the community.</p>

        <p>Thanks for joining CourtSideClub — we're excited to have you with us!<br>
        – The CourtSideClub Team</p>
        """
        
        success = send_email(
            to_email="richardbattlebaxter@gmail.com",
            subject="Welcome to CourtSideClub 🎾 Here's what's next",
            content_html=welcome_html
        )
        
        if success:
            return f'''
            <h1>✅ Welcome Email Sent</h1>
            <p><strong>User:</strong> {user.email} ({getattr(user, 'first_name', 'No name')})</p>
            <p>Check the recipient's inbox for the welcome email!</p>
            <p><a href="/debug/send_test_email">Send Test Email</a> | <a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        else:
            return f'''
            <h1>❌ Welcome Email Failed</h1>
            <p><strong>User:</strong> {user.email}</p>
            <p>Check server logs for detailed error information.</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
            
    except Exception as e:
        logger.error(f"Error in welcome email debug: {str(e)}", exc_info=True)
        return f'''
        <h1>❌ Debug Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        ''', 500

@debug_bp.route('/debug/email_status')
def email_status():
    """Debug route to check email system status and eligible users"""
    try:
        # Check SendGrid API key
        api_key = os.environ.get('SENDGRID_API_KEY')
        api_key_status = "Available" if api_key else "Missing"
        
        # Count users with notifications enabled
        users_with_notifications = User.query.filter_by(notifications=True).count()
        total_users = User.query.count()
        
        # Count users attending tournaments
        attending_users = db.session.query(User).join(UserTournament).filter(
            UserTournament.attending == True
        ).distinct().count()
        
        # Count users with session selections
        users_with_sessions = db.session.query(User).join(UserTournament).filter(
            UserTournament.attending == True,
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        ).distinct().count()
        
        # Get sample eligible users
        sample_users = db.session.query(User).join(UserTournament).filter(
            UserTournament.attending == True,
            UserTournament.session_label.isnot(None),
            User.notifications == True
        ).limit(5).all()
        
        sample_list = ""
        for user in sample_users:
            sample_list += f"<li>{user.email} ({getattr(user, 'first_name', 'No name')})</li>"
        
        return f'''
        <h1>📧 Email System Status</h1>
        
        <h2>SendGrid Configuration</h2>
        <p><strong>API Key:</strong> {api_key_status}</p>
        <p><strong>From Email:</strong> richardbattlebaxter@gmail.com</p>
        
        <h2>User Statistics</h2>
        <p><strong>Total Users:</strong> {total_users}</p>
        <p><strong>Users with Notifications Enabled:</strong> {users_with_notifications}</p>
        <p><strong>Users Attending Tournaments:</strong> {attending_users}</p>
        <p><strong>Users with Session Selections:</strong> {users_with_sessions}</p>
        
        <h2>Sample Eligible Users (for email testing)</h2>
        <ul>{sample_list}</ul>
        
        <h2>Debug Email Routes</h2>
        <ul>
            <li><a href="/debug/send_test_email">Send Basic Test Email</a></li>
            <li><a href="/debug/send_welcome_email">Send Welcome Email</a></li>
            <li><a href="/debug/send_tournament_reminder">Send Tournament Reminder</a></li>
            <li><a href="/debug/send_morning_email">Send Morning-Of Email</a></li>
        </ul>
        
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        '''
        
    except Exception as e:
        logger.error(f"Error in email status debug: {str(e)}", exc_info=True)
        return f'''
        <h1>❌ Email Status Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        ''', 500

@debug_bp.route('/debug/send_post_tournament_email')
def send_post_tournament_email():
    """Send a test post-tournament follow-up email"""
    try:
        from models import User, Tournament, UserTournament
        from services.email import send_post_tournament_followup_email
        
        # Find a user with tournament attendance
        user_tournament = db.session.query(UserTournament).filter(
            UserTournament.attending == True
        ).first()
        
        if not user_tournament:
            return '''
            <h1>❌ No Attending Users</h1>
            <p>No users found attending tournaments.</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        
        user = db.session.get(User, user_tournament.user_id)
        tournament = db.session.get(Tournament, user_tournament.tournament_id)
        
        success = send_post_tournament_followup_email(user.id, tournament.id)
        
        if success:
            return f'''
            <h1>✅ Post-Tournament Follow-Up Email Sent</h1>
            <p><strong>User:</strong> {user.email} ({getattr(user, 'first_name', 'N/A')})</p>
            <p><strong>Tournament:</strong> {tournament.name}</p>
            <p><strong>Sessions:</strong> {user_tournament.session_label or 'N/A'}</p>
            <p>Check the recipient's inbox for the post-tournament follow-up email!</p>
            <p><a href="/debug/send_test_email">Send Test Email</a> | <a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
        else:
            return '''
            <h1>❌ Email Send Failed</h1>
            <p>Failed to send post-tournament follow-up email. Check logs for details.</p>
            <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
            '''
            
    except Exception as e:
        return f'''
        <h1>❌ Error</h1>
        <p>Error sending post-tournament follow-up email: {str(e)}</p>
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        '''

# Lanyard confirmation email debug route removed - functionality discontinued

# Lanyard delivery reminder email debug route removed - functionality discontinued

def seed_real_blogs():
    """Create a welcome blog post for each tournament"""
    tournaments = Tournament.query.all()
    created_count = 0

    for t in tournaments:
        title = f"Welcome to CourtSide Club at {t.name}"
        slug = f"welcome-{t.slug}"
        
        # Check if blog post already exists
        existing = BlogPost.query.filter_by(slug=slug).first()
        if existing:
            continue
            
        content = textwrap.dedent(f"""
            Welcome to CourtSide Club at {t.name}!

            We're thrilled you're thinking about attending {t.name}. CourtSide Club was created to make your tennis experience more social, memorable, and fun — whether you're traveling solo or meeting up with friends.

            By joining, you'll be able to:
            - See who else is attending {t.name}
            - Coordinate sessions and match days
            - Get a free lanyard that makes in-person connections easy
            - Stay in the loop on possible meetups or premium seat opportunities

            Our vision is to create a fan-first experience at the biggest tournaments around the world — and {t.name} is no exception.

            Want to be part of it? Just mark your attendance, order your lanyard, and we'll see you there.

            — The CourtSide Club Team
        """).strip()

        blog = BlogPost(
            title=title,
            slug=slug,
            content=content,
            published=True,
            created_at=datetime.datetime.utcnow()
        )
        db.session.add(blog)
        created_count += 1

    db.session.commit()
    return f"Created {created_count} welcome blog posts for tournaments."

@debug_bp.route("/debug/seed-welcome-blogs")
def seed_welcome_blogs():
    """Debug route to create welcome blog posts for all tournaments"""
    try:
        result = seed_real_blogs()
        return f"""
        <h1>✅ Welcome Blog Posts Created</h1>
        <p><strong>Result:</strong> {result}</p>
        <p><a href="/blog">View Blog</a> | <a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        """
    except Exception as e:
        logger.error(f"Error creating welcome blog posts: {str(e)}", exc_info=True)
        return f"""
        <h1>❌ Blog Creation Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/debug/system-info">View System Info</a> | <a href="/">Back to Home</a></p>
        """, 500

