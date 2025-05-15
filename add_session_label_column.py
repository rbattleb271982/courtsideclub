"""
Database Migration to add session_label and wants_to_meet columns to user_tournament table

This script adds the 'session_label' and 'wants_to_meet' columns to the user_tournament table,
enabling new attendance session handling.
"""
import os
import sys
import psycopg2
from psycopg2 import sql

def add_session_label_column():
    """Add the session_label and wants_to_meet columns to the user_tournament table if they don't exist"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        conn.autocommit = True
        cur = conn.cursor()

        # Check if columns already exist
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_tournament' 
            AND column_name = 'session_label'
        """)
        session_label_exists = cur.fetchone() is not None

        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_tournament' 
            AND column_name = 'wants_to_meet'
        """)
        wants_to_meet_exists = cur.fetchone() is not None

        # Add session_label column if it doesn't exist
        if not session_label_exists:
            print("Adding session_label column to user_tournament table...")
            cur.execute("""
                ALTER TABLE user_tournament
                ADD COLUMN session_label VARCHAR(255)
            """)
            print("session_label column added successfully.")
        else:
            print("session_label column already exists.")

        # Add wants_to_meet column if it doesn't exist
        if not wants_to_meet_exists:
            print("Adding wants_to_meet column to user_tournament table...")
            cur.execute("""
                ALTER TABLE user_tournament
                ADD COLUMN wants_to_meet BOOLEAN DEFAULT TRUE
            """)
            print("wants_to_meet column added successfully.")
        else:
            print("wants_to_meet column already exists.")

        # Update existing records - set wants_to_meet based on open_to_meet
        print("Updating existing records...")
        cur.execute("""
            UPDATE user_tournament
            SET wants_to_meet = open_to_meet
            WHERE wants_to_meet IS NULL
        """)
        
        # Set session_label based on sessions list for existing records
        print("Updating session_label for existing records...")
        cur.execute("""
            SELECT id, sessions FROM user_tournament 
            WHERE sessions IS NOT NULL AND session_label IS NULL
        """)
        rows = cur.fetchall()
        for row in rows:
            id, sessions = row
            if sessions:
                try:
                    import json
                    sessions_list = json.loads(sessions) if isinstance(sessions, str) else sessions
                    session_label = ", ".join(sessions_list)
                    cur.execute(sql.SQL("UPDATE user_tournament SET session_label = %s WHERE id = %s"), 
                              (session_label, id))
                except Exception as e:
                    print(f"Error updating session_label for ID {id}: {e}")

        print("Migration completed successfully.")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    print("Starting migration to add session_label and wants_to_meet columns...")
    result = add_session_label_column()
    if result:
        print("Migration successful!")
    else:
        print("Migration failed!")
        sys.exit(1)