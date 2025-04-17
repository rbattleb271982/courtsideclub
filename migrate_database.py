"""
Database Migration Script

This script migrates data from the old JSON-based data structure to the new relational model.
It preserves all existing data by creating records in the new UserTournament table.

Steps:
1. Create the new tables if they don't exist
2. For each user, create UserTournament records for current tournaments
3. For each user, create entries in the past_tournaments association table
4. Log the results of the migration

This migration is designed to be idempotent (can be run multiple times safely).
"""

from flask import Flask
from models import db, User, Tournament, UserTournament
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask app for database migration"""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)
    return app

def migrate_data():
    """Migrate data from JSON fields to relational tables"""
    logger.info("Starting database migration")
    
    # Create tables if they don't exist
    db.create_all()
    logger.info("Ensured tables exist")
    
    # Get all users
    users = User.query.all()
    logger.info(f"Found {len(users)} users to migrate")
    
    users_migrated = 0
    user_tournaments_created = 0
    past_tournaments_created = 0
    errors = 0
    
    for user in users:
        try:
            # Migrate current tournament attendance
            if user.attending:
                for tournament_id, attendance_data in user.attending.items():
                    # Check if this tournament exists
                    tournament = Tournament.query.get(tournament_id)
                    if not tournament:
                        logger.warning(f"Tournament {tournament_id} not found for user {user.id}")
                        continue
                    
                    # Check if we already have a UserTournament record
                    user_tournament = UserTournament.query.filter_by(
                        user_id=user.id, tournament_id=tournament_id
                    ).first()
                    
                    if not user_tournament:
                        # Create a new UserTournament record
                        dates = []
                        sessions = []
                        
                        # Extract dates and sessions from the attendance data
                        if 'dates' in attendance_data:
                            # New format
                            dates = attendance_data.get('dates', [])
                            sessions = attendance_data.get('sessions', [])
                        else:
                            # Old format with day-to-session mapping
                            for day, day_sessions in attendance_data.items():
                                dates.append(day)
                                sessions.extend(day_sessions)
                        
                        # Check if raised hand exists for this tournament
                        open_to_meet = tournament_id in user.raised_hand
                        
                        user_tournament = UserTournament(
                            user_id=user.id,
                            tournament_id=tournament_id,
                            dates=dates,
                            sessions=sessions,
                            open_to_meet=open_to_meet
                        )
                        db.session.add(user_tournament)
                        user_tournaments_created += 1
            
            # Migrate past tournaments
            if user.past_tournaments_json:
                for tournament_id in user.past_tournaments_json:
                    # Check if this tournament exists
                    tournament = Tournament.query.get(tournament_id)
                    if not tournament:
                        logger.warning(f"Past tournament {tournament_id} not found for user {user.id}")
                        continue
                    
                    # Check if the tournament is already in the attended_tournaments relationship
                    if tournament not in user.attended_tournaments:
                        user.attended_tournaments.append(tournament)
                        past_tournaments_created += 1
            
            users_migrated += 1
            
        except Exception as e:
            logger.error(f"Error migrating user {user.id}: {str(e)}")
            errors += 1
    
    # Commit the changes
    try:
        db.session.commit()
        logger.info(f"Migration complete: {users_migrated} users migrated, "
                    f"{user_tournaments_created} user tournaments created, "
                    f"{past_tournaments_created} past tournaments created, "
                    f"{errors} errors")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error committing migration: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    with create_app().app_context():
        success = migrate_data()
        if success:
            print("Migration completed successfully!")
        else:
            print("Migration failed. Check the logs for details.")