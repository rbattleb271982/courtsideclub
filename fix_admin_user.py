#!/usr/bin/env python3
from app import app, db
from models import User

with app.app_context():
    user = User.query.filter_by(email='richardbattlebaxter@gmail.com').first()
    if user:
        user.is_admin = True
        db.session.commit()
        print(f'Set admin status: {user.is_admin}')
    else:
        print('User not found')