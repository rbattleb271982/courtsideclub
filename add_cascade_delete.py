"""
Database Migration to add CASCADE DELETE Rules

This script alters foreign key constraints in the database to add CASCADE DELETE rules.
This ensures that when a User is deleted, all related data in past_tournaments and user_tournament
tables is also deleted.
"""

from app import db
import sys

def add_cascade_delete_rules():
    """
    Add CASCADE DELETE rules to existing foreign key constraints.
    
    This function drops existing foreign key constraints and recreates them with ON DELETE CASCADE.
    """
    print("Starting migration to add CASCADE DELETE rules...")
    
    try:
        # Get the database connection and create a cursor
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        
        # Drop existing foreign key constraints
        # In the past_tournaments association table
        print("Dropping existing foreign key constraints...")
        cursor.execute("""
        ALTER TABLE past_tournaments
        DROP CONSTRAINT IF EXISTS past_tournaments_user_id_fkey;
        """)
        
        cursor.execute("""
        ALTER TABLE past_tournaments
        DROP CONSTRAINT IF EXISTS past_tournaments_tournament_id_fkey;
        """)
        
        # In the user_tournament table
        cursor.execute("""
        ALTER TABLE user_tournament
        DROP CONSTRAINT IF EXISTS user_tournament_user_id_fkey;
        """)
        
        cursor.execute("""
        ALTER TABLE user_tournament
        DROP CONSTRAINT IF EXISTS user_tournament_tournament_id_fkey;
        """)
        
        # Recreate constraints with CASCADE DELETE
        print("Creating new foreign key constraints with CASCADE DELETE...")
        cursor.execute("""
        ALTER TABLE past_tournaments
        ADD CONSTRAINT past_tournaments_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        """)
        
        cursor.execute("""
        ALTER TABLE past_tournaments
        ADD CONSTRAINT past_tournaments_tournament_id_fkey
        FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE;
        """)
        
        cursor.execute("""
        ALTER TABLE user_tournament
        ADD CONSTRAINT user_tournament_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        """)
        
        cursor.execute("""
        ALTER TABLE user_tournament
        ADD CONSTRAINT user_tournament_tournament_id_fkey
        FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE;
        """)
        
        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        
if __name__ == "__main__":
    # Import the app directly
    from main import app
    with app.app_context():
        add_cascade_delete_rules()