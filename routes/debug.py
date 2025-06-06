from flask import Blueprint, jsonify, render_template
from models import db, User, Tournament, UserTournament
from services.sendgrid_service import send_email
import logging
import os
import sys
import traceback
import datetime
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
            lanyard_ordered=False,
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
    from_email = current_app.config.get('FROM_EMAIL', 'noreply@courtsideclub.app')

    # Send the email
    status_code = send_email(
        to_email=recipient_email,
        subject='CourtSideClub Test Email',
        content_html='<p>This is a test email from CourtSideClub 🎾</p>'
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

    <p>Welcome to <strong>CourtSideClub</strong> – the community for tennis fans who want more than just a seat in the stands.</p>

    <p>Here's what you can do starting today:</p>
    <ul>
      <li>📍 Choose the tournaments you're attending</li>
      <li>🤝 Raise your hand to meet other fans</li>
      <li>🧢 Get your free lanyard to help you connect in person</li>
    </ul>

    <p>Some of the biggest tournaments coming up:</p>
    {tournament_html}

    <p>Ready to dive in? <a href="https://bafb033d-26a4-47de-b4d6-96666ed788fe-00-2cbmkxn1203ip.kirk.replit.dev/login">Log in to pick your tournaments</a> and join the community.</p>

    <p>Thanks for joining CourtSideClub — we're excited to have you with us!<br>
    – The CourtSideClub Team</p>
    """

    send_email(
        to_email=user.email,
        subject="Welcome to CourtSideClub 🎾 Here's what's next",
        content_html=welcome_email_html
    )

    return f"Welcome email sent to {user.email}"

@debug_bp.route('/debug/send-reminder/<int:user_id>/<tournament_slug>')
def send_reminder(user_id, tournament_slug):
    from models import User, Tournament, UserTournament

    user = db.session.get(User, user_id)
    tournament = Tournament.query.filter_by(slug=tournament_slug).first()

    if not user or not tournament:
        return "Invalid user or tournament slug", 404

    # Check if the user has a lanyard ordered
    has_lanyard = user.lanyard_ordered if hasattr(user, 'lanyard_ordered') else False

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

    <p>Thanks for being part of CourtSideClub — we can't wait to see you there!<br>
    – The CourtSideClub Team</p>
    """

    send_email(
        to_email=user.email,
        subject=f"{tournament.name} is just 2 weeks away! 🎾",
        content_html=reminder_html
    )

    return f"Tournament reminder sent to {user.email}"

@debug_bp.route('/debug/send_test_email')
def send_test_email():
    """Send a basic test email using SendGrid"""
    from services.sendgrid_service import send_email
    import os
    from flask import current_app
    
    # Your test email address
    test_email = "richardbattlebaxter@gmail.com"
    
    # Get FROM_EMAIL from config
    from_email = current_app.config.get('FROM_EMAIL', 'noreply@courtsideclub.app')
    
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
        from services.email import send_tournament_reminder_email
        
        # Override the user's email for testing purposes
        original_email = user.email
        user.email = "richardbattlebaxter@gmail.com"
        
        success = send_tournament_reminder_email(user_id, tournament_id)
        
        # Restore original email
        user.email = original_email
        
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
        
        # Send the morning-of email to your address for testing
        original_email = user.email
        user.email = "richardbattlebaxter@gmail.com"
        
        success = send_morning_of_email(user_id, tournament_id, session_date, session_name)
        
        # Restore original email
        user.email = original_email
        
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
        original_email = user.email
        user.email = "richardbattlebaxter@gmail.com"
        
        success = send_welcome_email(user_id)
        
        # Restore original email
        user.email = original_email
        
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