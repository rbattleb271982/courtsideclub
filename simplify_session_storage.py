"""
Migration script to simplify session storage in UserTournament model.

This script migrates all data from dates and sessions arrays to the session_label field.
"""
import os
import sys
import json
import psycopg2
from psycopg2 import sql

def run():
    """Migrate session data to session_label and prepare to remove legacy fields"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        conn.autocommit = True
        cur = conn.cursor()

        print("Fetching all UserTournament records...")
        cur.execute("""
            SELECT id, dates, sessions, session_label 
            FROM user_tournament 
            WHERE (dates IS NOT NULL AND dates != '[]') 
               OR (sessions IS NOT NULL AND sessions != '[]')
        """)
        rows = cur.fetchall()
        
        updated_count = 0
        for row in rows:
            id, dates_json, sessions_json, current_label = row
            
            # Skip if session_label is already set
            if current_label:
                continue
                
            try:
                dates = json.loads(dates_json) if dates_json else []
                sessions = json.loads(sessions_json) if sessions_json else []
                
                # Create a readable session label
                label_parts = []
                
                # Add dates
                if dates:
                    date_str = ", ".join(dates)
                    label_parts.append(f"Dates: {date_str}")
                
                # Add sessions
                if sessions:
                    session_str = ", ".join(sessions)
                    if label_parts:
                        label_parts.append(f"Sessions: {session_str}")
                    else:
                        label_parts.append(f"Sessions: {session_str}")
                
                # Combine into a single label
                session_label = " | ".join(label_parts) if label_parts else None
                
                if session_label:
                    # Update the record
                    cur.execute(
                        "UPDATE user_tournament SET session_label = %s WHERE id = %s",
                        (session_label, id)
                    )
                    updated_count += 1
            except Exception as e:
                print(f"Error processing record {id}: {e}")
                continue
        
        print(f"Updated {updated_count} records with session labels.")
        print("Migration completed successfully.")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    print("Starting migration to simplify session storage...")
    result = run()
    if result:
        print("Migration successful!")
    else:
        print("Migration failed!")
        sys.exit(1)