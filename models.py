from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.ext.mutable import MutableList, MutableDict
from sqlalchemy import types
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

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(256))
    
    @property
    def name(self):
        """Legacy support for templates that use user.name"""
        return f"{self.first_name} {self.last_name}"
    attending = db.Column(MutableList.as_mutable(JsonEncodedList), default=[])
    raised_hand = db.Column(MutableDict.as_mutable(JsonEncodedDict), default={})
    lanyard_ordered = db.Column(db.Boolean, default=False)
    notifications = db.Column(db.Boolean, default=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    
    def __repr__(self):
        return f'<Tournament {self.name}>'

def load_user(user_id):
    return User.query.get(int(user_id))
