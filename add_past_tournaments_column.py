from app import app, db
from models import User
from sqlalchemy import Column, JSON, text
from sqlalchemy.dialects.postgresql import JSONB

print("Starting migration to add past_tournaments column...")

def add_past_tournaments_column():
    """Add the past_tournaments column to the users table if it doesn't exist"""
    
    with app.app_context():
        # Check if column exists
        conn = db.engine.connect()
        exists = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='past_tournaments'"
        )).fetchone()
        
        if not exists:
            print("Column 'past_tournaments' does not exist. Adding it...")
            conn.execute(text("ALTER TABLE users ADD COLUMN past_tournaments TEXT DEFAULT '[]'"))
            conn.execute(text("COMMIT"))
            print("Column 'past_tournaments' added successfully.")
        else:
            print("Column 'past_tournaments' already exists. Skipping migration.")
        
        conn.close()

if __name__ == "__main__":
    add_past_tournaments_column()
    print("Migration completed successfully!")