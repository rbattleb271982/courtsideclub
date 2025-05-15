from flask import Blueprint, jsonify, render_template
from models import db, User, Tournament
import logging
import os
import sys
import traceback
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
            attending={},
            raised_hand={},
            past_tournaments=[],
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
    
    # Use provided email or default
    recipient_email = email if email else 'your_email@example.com'
    
    status_code = send_email(
        to_email=recipient_email,
        subject='CourtSideClub Test Email',
        content_html='<p>This is a test email from CourtSideClub 🎾</p>'
    )
    
    if status_code:
        return f"Test email sent to {recipient_email} with status code: {status_code}"
    else:
        return "Failed to send email. Check server logs for details."
