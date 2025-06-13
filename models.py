from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy import types, Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
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
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Handle malformed JSON by returning empty list
            return []

class JsonEncodedDict(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return '{}'
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Handle malformed JSON by returning empty dict
            return {}

# Create a proper UserPastTournament model for the many-to-many relationship
class UserPastTournament(db.Model):
    __tablename__ = 'user_past_tournament'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tournament_id = db.Column(db.String(50), db.ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", back_populates="past_tournaments")
    tournament = db.relationship("Tournament")

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
    
    # Legacy fields have been removed:
    # attending = db.Column(MutableDict.as_mutable(JsonEncodedDict), default={})
    # raised_hand = db.Column(MutableDict.as_mutable(JsonEncodedDict), default={})
    # past_tournaments_json = db.Column('past_tournaments', MutableList.as_mutable(JsonEncodedList), default=[])
    
    # Relationship for current tournament registrations
    tournament_registrations = relationship('UserTournament', 
                                           back_populates='user',
                                           cascade="all, delete-orphan")
    
    # Relationship for past tournaments the user has attended
    past_tournaments = relationship('UserPastTournament',
                                   back_populates='user',
                                   cascade="all, delete-orphan")
    
    location = db.Column(db.String(100))
    # lanyard_ordered = db.Column(db.Boolean, default=False)  # Removed - functionality discontinued
    # lanyard_sent = db.Column(db.Boolean, default=False)  # Removed - functionality discontinued
    lanyard_sent_date = db.Column(db.DateTime, nullable=True)
    lanyard_exported = db.Column(db.Boolean, default=False)
    notifications = db.Column(db.Boolean, default=True)
    welcome_seen = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    test_user = db.Column(db.Boolean, default=False)
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
    slug = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    tour_type = db.Column(db.String(50), nullable=False)
    about = db.Column(db.Text)
    draw_url = db.Column(db.String(255))
    schedule_url = db.Column(db.String(255))
    external_url = db.Column(db.String(255))
    bracket_url = db.Column(db.String(255))
    sessions = db.Column(MutableList.as_mutable(JsonEncodedList), default=[])
    
    # New optional fields for admin use
    surface = db.Column(db.String(50), nullable=True)  # e.g., "Hard", "Clay", "Grass"
    commentary = db.Column(db.Text, nullable=True)  # Editorial commentary for tournament
    summary = db.Column(db.Text, nullable=True)  # AI-generated summary for tournament
    
    user_registrations = relationship('UserTournament', back_populates='tournament')
    
    @property
    def location(self):
        """Return formatted location string matching public site format"""
        return f"{self.city}, {self.country}"
    
    def __repr__(self):
        return f'<Tournament {self.name}>'

class UserTournament(db.Model):
    __tablename__ = 'user_tournament'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tournament_id = db.Column(db.String(50), db.ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    
    # Legacy fields for selected dates and sessions - will be phased out
    # dates = db.Column(MutableList.as_mutable(JsonEncodedList), default=[])
    # sessions = db.Column(MutableList.as_mutable(JsonEncodedList), default=[])
    
    # Primary field for session information - changed from String(255) to Text
    session_label = db.Column(db.Text)
    
    # Whether the user is actually attending this tournament
    attending = db.Column(db.Boolean, default=False)
    
    # Type of attendance: 'attending' or 'maybe'
    attendance_type = db.Column(db.String(20), default='attending')
    
    # Whether the user is open to meeting (original field)
    open_to_meet = db.Column(db.Boolean, default=True)
    
    # Additional field for the new implementation
    wants_to_meet = db.Column(db.Boolean, default=True)
    
    # When the user registered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='tournament_registrations', cascade="all, delete")
    tournament = relationship('Tournament', back_populates='user_registrations')
    
    def __repr__(self):
        return f'<UserTournament user_id={self.user_id} tournament_id={self.tournament_id}>'

class ShippingAddress(db.Model):
    __tablename__ = 'shipping_addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address1 = db.Column(db.String(255), nullable=False)
    address2 = db.Column(db.String(255))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = relationship('User', backref=backref('shipping_address', uselist=False, cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f'<ShippingAddress user_id={self.user_id}>'

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_data = db.Column(MutableDict.as_mutable(JsonEncodedDict), default={})
    
    # Relationship to user
    user = relationship('User', backref=backref('events', cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<Event {self.name} by User {self.user_id}>"

class UserWishlistTournament(db.Model):
    __tablename__ = 'user_wishlist_tournaments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tournament_id = db.Column(db.String(50), db.ForeignKey('tournaments.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', backref=backref('wishlist_tournaments', cascade="all, delete-orphan"))
    tournament = relationship('Tournament')
    
    def __repr__(self):
        return f"<WishlistTournament {self.tournament_id} for User {self.user_id}>"


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship('User', backref='blog_posts')
    
    def __repr__(self):
        return f"<BlogPost {self.title}>"
    
    @property
    def summary(self):
        """Return excerpt or first 120 characters of content"""
        return self.excerpt or (self.content[:120] + "..." if len(self.content) > 120 else self.content)


def load_user(user_id):
    import logging
    logging.info(f"User loader called with user_id: {user_id}")
    try:
        user = User.query.get(int(user_id))
        if user:
            logging.info(f"User loader found user: {user.email}")
        else:
            logging.info(f"User loader: No user found with ID {user_id}")
        return user
    except Exception as e:
        logging.error(f"User loader error: {e}")
        return None
