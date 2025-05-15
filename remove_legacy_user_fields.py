"""
Migration script to remove legacy JSON attendance fields from the User model.

This script removes the following columns from the users table:
- attending
- raised_hand
- past_tournaments
"""
import os
import sys
import psycopg2
from psycopg2 import sql

def run():
    """Remove legacy fields from the users table"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        conn.autocommit = True
        cur = conn.cursor()

        # Check if columns exist before attempting to drop them
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'attending'
        """)
        attending_exists = cur.fetchone() is not None

        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'raised_hand'
        """)
        raised_hand_exists = cur.fetchone() is not None

        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'past_tournaments'
        """)
        past_tournaments_exists = cur.fetchone() is not None

        # Drop attending column if it exists
        if attending_exists:
            print("Dropping 'attending' column from users table...")
            cur.execute("ALTER TABLE users DROP COLUMN IF EXISTS attending")
            print("'attending' column dropped successfully.")
        else:
            print("'attending' column does not exist.")

        # Drop raised_hand column if it exists
        if raised_hand_exists:
            print("Dropping 'raised_hand' column from users table...")
            cur.execute("ALTER TABLE users DROP COLUMN IF EXISTS raised_hand")
            print("'raised_hand' column dropped successfully.")
        else:
            print("'raised_hand' column does not exist.")

        # Drop past_tournaments column if it exists
        if past_tournaments_exists:
            print("Dropping 'past_tournaments' column from users table...")
            cur.execute("ALTER TABLE users DROP COLUMN IF EXISTS past_tournaments")
            print("'past_tournaments' column dropped successfully.")
        else:
            print("'past_tournaments' column does not exist.")

        print("Migration completed successfully.")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    print("Starting migration to remove legacy user fields...")
    result = run()
    if result:
        print("Migration successful!")
    else:
        print("Migration failed!")
        sys.exit(1)