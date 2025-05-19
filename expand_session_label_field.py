"""
Database Migration to expand session_label column to TEXT type

This script alters the session_label column in the user_tournament table 
from a VARCHAR(255) to TEXT type to accommodate more session data.
"""
import os
import psycopg2
from psycopg2 import sql

def expand_session_label_field():
    """Alter the session_label column to TEXT type"""
    print("Starting session_label field expansion migration...")
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set")
        return
    
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the column exists
        cursor.execute("""
            SELECT data_type
            FROM information_schema.columns 
            WHERE table_name = 'user_tournament' AND column_name = 'session_label'
        """)
        
        column_type = cursor.fetchone()
        
        if not column_type:
            print("ERROR: session_label column not found")
            return
        
        print(f"Current data type of session_label: {column_type[0]}")
        
        if column_type[0].lower() != 'text':
            # Alter the column type to TEXT
            print("Altering session_label column to TEXT type...")
            cursor.execute(sql.SQL("""
                ALTER TABLE user_tournament
                ALTER COLUMN session_label TYPE TEXT
            """))
            print("Successfully expanded session_label column to TEXT type")
        else:
            print("session_label is already TEXT type. No changes needed.")
            
    except Exception as e:
        print(f"ERROR: Failed to alter session_label column: {e}")
    finally:
        if conn:
            conn.close()
    
    print("Migration completed.")

if __name__ == "__main__":
    expand_session_label_field()