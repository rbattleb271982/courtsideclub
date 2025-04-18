from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy import types, Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

# Custom field types to store JSON data
class JsonEncodedList(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return '[]'
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return json.loads(value)

class JsonEncodedDict(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return '{}'
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        return json.loads(value)

# Many-to-many association table for past tournaments
past_tournaments = Table(
    'past_tournaments',
    db.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('tournament_id', db.String(50), ForeignKey('tournaments.id', ondelete='CASCADE'))
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # These fields were added in a migration
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    # Original name field still exists in the database
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(256))
    
    # Keep these for backward compatibility during migration
    attending = db.Column(MutableDict.as_mutable(JsonEncodedDict), default={})
    raised_hand = db.Column(MutableDict.as_mutable(JsonEncodedDict), default={})
    past_tournaments_json = db.Column('past_tournaments', MutableList.as_mutable(JsonEncodedList), default=[])
    
    # New relationships
    attended_tournaments = relationship(
        'Tournament',
        secondary=past_tournaments,
        backref=db.backref('attendees', lazy='dynamic')
    )
    
    tournament_registrations = relationship('UserTournament', 
                                           back_populates='user',
                                           cascade="all, delete-orphan")
    
    lanyard_ordered = db.Column(db.Boolean, default=False)
    notifications = db.Column(db.Boolean, default=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_full_name(self):
        """Get the user's full name, preferring first_name/last_name if available"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.name:
            return self.name
        else:
            return self.email.split('@')[0]  # Fallback to username from email
    
    def get_id(self):
        return str(self.id)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Tournament(db.Model):
    __tablename__ = 'tournaments'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    tour_type = db.Column(db.String(50), nullable=False)
    sessions = db.Column(MutableList.as_mutable(JsonEncodedList), default=[])
    
    user_registrations = relationship('UserTournament', back_populates='tournament')
    
    def __repr__(self):
        return f'<Tournament {self.name}>'

class UserTournament(db.Model):
    __tablename__ = 'user_tournament'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tournament_id = db.Column(db.String(50), db.ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    
    # Store selected dates and sessions
    dates = db.Column(MutableList.as_mutable(JsonEncodedList), default=[])
    sessions = db.Column(MutableList.as_mutable(JsonEncodedList), default=[])
    
    # Whether the user is open to meeting
    open_to_meet = db.Column(db.Boolean, default=True)
    
    # When the user registered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='tournament_registrations', cascade="all, delete")
    tournament = relationship('Tournament', back_populates='user_registrations')
    
    def __repr__(self):
        return f'<UserTournament user_id={self.user_id} tournament_id={self.tournament_id}>'

def load_user(user_id):
    return User.query.get(int(user_id))
