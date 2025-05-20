"""
Script to list available tournaments
"""
from app import app
from models import Tournament

with app.app_context():
    tournaments = Tournament.query.all()
    print(f"Total tournaments: {len(tournaments)}")
    print("\nSample tournaments:")
    for t in tournaments[:10]:
        print(f"ID: {t.id}, Name: {t.name}, Start: {t.start_date}, End: {t.end_date}")