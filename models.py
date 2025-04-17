from flask_login import UserMixin
from replit import db

class User(UserMixin):
    def __init__(self, id, email, name, attending=None, raised_hand=None, 
                 lanyard_ordered=False, notifications=True):
        self.id = id
        self.email = email
        self.name = name
        self.attending = attending or []
        self.raised_hand = raised_hand or {}
        self.lanyard_ordered = lanyard_ordered
        self.notifications = notifications
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return self.id
    
def load_user(user_id):
    user_data = db.get(user_id)
    if not user_data:
        return None
    
    return User(
        user_id,
        user_data.get('email'),
        user_data.get('name'),
        user_data.get('attending', []),
        user_data.get('raised_hand', {}),
        user_data.get('lanyard_ordered', False),
        user_data.get('notifications', True)
    )
