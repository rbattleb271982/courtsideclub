import os
from flask import Flask, render_template
from flask_login import LoginManager
import logging
from models import db, User, load_user, Tournament
import datetime
from datetime import timedelta
from services.event_logger import log_event

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Initialize Flask app
app = Flask(__name__)

# Add ProxyFix middleware for Replit environment
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Add middleware to log all requests and responses for debugging
@app.before_request
def log_request_info():
    from flask import request
    import logging
    logging.info(f"=== REQUEST: {request.method} {request.path} ===")
    logging.info(f"Request cookies: {dict(request.cookies)}")
    logging.info(f"Request headers: {dict(request.headers)}")

@app.after_request
def log_response_info(response):
    import logging
    logging.info(f"=== RESPONSE: {response.status_code} ===")
    logging.info(f"Response headers: {dict(response.headers)}")
    
    # Add proper headers for iframe compatibility
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' *.replit.dev *.replit.co *.replit.com"
    
    return response

app.config.from_object('config.Config')

# Set the remember me cookie duration to 30 days
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

# Add custom Jinja2 filters
@app.template_filter('timedelta')
def timedelta_filter(n):
    """Add a number of days to a date"""
    return datetime.timedelta(days=n)

@app.template_filter('today')
def format_today(format_string):
    """Format today's date with the given format string"""
    return datetime.datetime.utcnow().strftime(format_string)

@app.template_filter('pluralize')
def pluralize(count, singular='', plural='s'):
    """Return singular or plural suffix based on count"""
    if int(count) == 1:
        return singular
    else:
        return plural
        
@app.template_filter('split')
def split_filter(value, delimiter=','):
    """Split a string by delimiter and return list"""
    if value is None:
        return []
    return value.split(delimiter)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,  # Recycle connections after 5 minutes
    'pool_pre_ping': True,  # Check connection validity before use
    'pool_timeout': 30,  # Timeout after 30 seconds
    'pool_size': 10,  # Maximum number of connections
    'max_overflow': 5,  # Maximum number of connections above pool_size
    'pool_reset_on_return': None,  # Don't reset pool on connection return
    'connect_args': {
        'connect_timeout': 10,  # Connection timeout in seconds
        'keepalives': 1,  # Enable TCP keepalives
        'keepalives_idle': 30,  # Seconds between TCP keepalives
        'keepalives_interval': 10,  # Seconds between TCP keepalive retransmits
        'keepalives_count': 5  # Number of TCP keepalive retransmits
    }
}

# Initialize the database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Set up the user loader
@login_manager.user_loader
def user_loader(user_id):
    return load_user(user_id)

# Initial data for tournaments
tournament_data = [
    {
        "id": "aus_open",
        "name": "Australian Open",
        "start_date": "2025-01-19",
        "end_date": "2025-02-01",
        "city": "Melbourne",
        "country": "Australia",
        "event_type": "Grand Slam",
        "tour_type": "ATP/WTA",
        "sessions": [
            {"day": "1", "date": "2025-01-19", "sessions": ["Day", "Night"]},
            {"day": "2", "date": "2025-01-20", "sessions": ["Day", "Night"]},
            {"day": "3", "date": "2025-01-21", "sessions": ["Day", "Night"]},
            {"day": "4", "date": "2025-01-22", "sessions": ["Day", "Night"]},
            {"day": "5", "date": "2025-01-23", "sessions": ["Day", "Night"]},
            {"day": "6", "date": "2025-01-24", "sessions": ["Day", "Night"]},
            {"day": "7", "date": "2025-01-25", "sessions": ["Day", "Night"]},
            {"day": "8", "date": "2025-01-26", "sessions": ["Day", "Night"]},
            {"day": "9", "date": "2025-01-27", "sessions": ["Day", "Night"]},
            {"day": "10", "date": "2025-01-28", "sessions": ["Day", "Night"]},
            {"day": "11", "date": "2025-01-29", "sessions": ["Day", "Night"]},
            {"day": "12", "date": "2025-01-30", "sessions": ["Day", "Night"]},
            {"day": "13", "date": "2025-01-31", "sessions": ["Day", "Night"]},
            {"day": "14", "date": "2025-02-01", "sessions": ["Day"]}
        ]
    },
    {
        "id": "indian_wells",
        "name": "Indian Wells",
        "start_date": "2025-03-10",
        "end_date": "2025-03-23",
        "city": "Indian Wells",
        "country": "USA",
        "event_type": "1000",
        "tour_type": "ATP/WTA",
        "sessions": [
            {"day": "1", "date": "2025-03-10", "sessions": ["Day"]},
            {"day": "2", "date": "2025-03-11", "sessions": ["Day"]},
            {"day": "3", "date": "2025-03-12", "sessions": ["Day"]},
            {"day": "4", "date": "2025-03-13", "sessions": ["Day"]},
            {"day": "5", "date": "2025-03-14", "sessions": ["Day"]},
            {"day": "6", "date": "2025-03-15", "sessions": ["Day"]},
            {"day": "7", "date": "2025-03-16", "sessions": ["Day"]},
            {"day": "8", "date": "2025-03-17", "sessions": ["Day"]},
            {"day": "9", "date": "2025-03-18", "sessions": ["Day"]},
            {"day": "10", "date": "2025-03-19", "sessions": ["Day"]},
            {"day": "11", "date": "2025-03-20", "sessions": ["Day"]},
            {"day": "12", "date": "2025-03-21", "sessions": ["Day"]},
            {"day": "13", "date": "2025-03-22", "sessions": ["Day"]},
            {"day": "14", "date": "2025-03-23", "sessions": ["Day"]}
        ]
    }
]

# Initialize the database tables and seed data
def init_db():
    with app.app_context():
        try:
            # Create all tables
            db.create_all()

            # Check if tournaments table is empty and seed initial data
            try:
                tournament_count = Tournament.query.count()
                if tournament_count == 0:
                    for t_data in tournament_data:
                        # Convert date strings to date objects
                        start_date = datetime.datetime.strptime(t_data['start_date'], '%Y-%m-%d').date()
                        end_date = datetime.datetime.strptime(t_data['end_date'], '%Y-%m-%d').date()

                        tournament = Tournament(
                            id=t_data['id'],
                            name=t_data['name'],
                            start_date=start_date,
                            end_date=end_date,
                            city=t_data['city'],
                            country=t_data['country'],
                            event_type=t_data['event_type'],
                            tour_type=t_data['tour_type'],
                            sessions=t_data['sessions']
                        )
                        db.session.add(tournament)

                    db.session.commit()
                    print("Database initialized with tournament data.")
                else:
                    print(f"Database already contains {tournament_count} tournaments. Skipping seed data.")
            except Exception as e:
                db.session.rollback()
                print(f"Error seeding tournament data: {str(e)}")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")

# Initialize the database
init_db()

# Import and register blueprints
from routes.auth import auth_bp
from routes.tournaments import tournaments_bp
from routes.debug import debug_bp
from routes.user import user_bp
from routes.main import main_bp
from routes.admin_routes import admin_bp
from routes.attendance_debug import attendance_debug_bp
from routes.event_test import event_test_bp
from routes.admin_agents import admin_agents_bp

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(tournaments_bp)
app.register_blueprint(user_bp)
app.register_blueprint(debug_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(attendance_debug_bp)
app.register_blueprint(event_test_bp)
app.register_blueprint(admin_agents_bp)

# Add context processor for current year
@app.context_processor
def inject_now():
    from datetime import datetime
    return {'current_year': datetime.now().year}

# Add error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler for all exceptions"""
    # Log the error to the standard logger first
    logging.error(f"Unhandled exception: {str(e)}", exc_info=True)
    
    # Track error in our event system with detailed information
    try:
        from flask import request, session
        from flask_login import current_user
        
        # Get basic error information
        error_type = type(e).__name__
        error_message = str(e)
        
        # Get request context information when available
        user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
        user_email = current_user.email if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
        
        # Capture request details
        request_data = {
            'url': str(request.url) if hasattr(request, 'url') else None,
            'method': request.method if hasattr(request, 'method') else None,
            'path': request.path if hasattr(request, 'path') else None,
            'user_agent': str(request.user_agent) if hasattr(request, 'user_agent') else None,
            'remote_addr': request.remote_addr if hasattr(request, 'remote_addr') else None,
        }
        
        # Log the error event
        log_event('application_error', data={
            'error_type': error_type,
            'error_message': error_message,
            'user_id': user_id,
            'user_email': user_email,
            'request': request_data,
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
    except Exception as log_error:
        # Prevent error tracking from causing additional errors
        logging.error(f"Error while tracking error event: {str(log_error)}")
    
    # Return the error template
    return render_template('error.html', error=str(e)), 500

# Add debug route for cookie inspection
@app.route('/debug/cookies')
def debug_cookies():
    from flask import request, session
    from flask_login import current_user
    return f"Cookies: {dict(request.cookies)}<br>Session: {dict(session)}<br>Current User: {current_user}<br>Is Authenticated: {current_user.is_authenticated}"

# Add a simple test route that doesn't require login
@app.route('/debug/session-test')
def session_test():
    from flask import request, session
    from flask_login import current_user
    import logging
    
    logging.info(f"=== SESSION TEST ROUTE ===")
    logging.info(f"Request cookies: {dict(request.cookies)}")
    logging.info(f"Session contents: {dict(session)}")
    logging.info(f"Current user: {current_user}")
    logging.info(f"Is authenticated: {current_user.is_authenticated}")
    
    return f"Session Test - Check logs for details"

# Add iframe test route for debugging preview window issues
@app.route('/iframe-test')
def iframe_test():
    """Simple test page to check iframe functionality"""
    from flask import render_template_string
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Iframe Test - CourtSide Club</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        </style>
    </head>
    <body>
        <h1>Iframe Test Page</h1>
        <div class="status success">✓ Page loaded successfully</div>
        <div class="status info" id="iframe-status">Checking iframe status...</div>
        <div class="status info">
            <strong>Current URL:</strong> <span id="current-url"></span>
        </div>
        <div class="status info">
            <strong>Session Status:</strong> 
            {% if current_user.is_authenticated %}
                Logged in as {{ current_user.email }}
            {% else %}
                Not logged in
            {% endif %}
        </div>
        
        <script>
            document.getElementById('current-url').textContent = window.location.href;
            
            if (window.parent !== window) {
                document.getElementById('iframe-status').innerHTML = 
                    '<strong>Status:</strong> Running inside iframe (Preview Window)';
                document.getElementById('iframe-status').className = 'status info';
            } else {
                document.getElementById('iframe-status').innerHTML = 
                    '<strong>Status:</strong> Running in full window (Direct Access)';
                document.getElementById('iframe-status').className = 'status success';
            }
        </script>
    </body>
    </html>
    ''')

# Background scheduler for AI agents
import threading, time, schedule
from agents.email_reminder import run_email_reminder
from agents.post_event_followup import run_post_event_followup_agent
from agents.pre_tournament_reminder import run_pre_tournament_reminder_agent

def run_scheduler():
    """Background scheduler that runs AI agents on a schedule"""
    schedule.every().day.at("10:00").do(run_email_reminder)
    schedule.every().day.at("10:00").do(run_pre_tournament_reminder_agent)
    schedule.every().day.at("10:10").do(run_post_event_followup_agent)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start the background scheduler in a daemon thread
threading.Thread(target=run_scheduler, daemon=True).start()

# Configure debug mode
app.debug = True