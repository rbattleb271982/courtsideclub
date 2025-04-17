import os
from flask import Flask
from flask_login import LoginManager
import logging
from models import db, User, load_user, Tournament
import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
        # Create all tables
        db.create_all()
        
        # Check if tournaments table is empty and seed initial data
        if Tournament.query.count() == 0:
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

# Initialize the database
init_db()

# Import and register blueprints
from routes.auth import auth_bp
from routes.tournaments import tournaments_bp
from routes.user import user_bp

app.register_blueprint(auth_bp)
app.register_blueprint(tournaments_bp)
app.register_blueprint(user_bp)

# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
