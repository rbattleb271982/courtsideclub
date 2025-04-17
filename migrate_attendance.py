import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def migrate_attendance_data():
    """
    Migrate user attendance data from list format to dictionary format:
    Old: ["aus_open", "indian_wells"]
    New: {"aus_open": {"date": "2025-01-19", "session": "Day"}, "indian_wells": {...}}
    """
    print("Starting attendance data migration...")
    
    # Connect directly to the database
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    conn.autocommit = False
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get users with list-formatted attendance data
            cur.execute("SELECT id, email, attending FROM users WHERE attending IS NOT NULL")
            users = cur.fetchall()
            count = 0
            
            for user in users:
                try:
                    # Parse the attending data
                    attending_data = user['attending']
                    
                    # Check if it's a list format (JSON array)
                    if attending_data.startswith('['):
                        old_attending = json.loads(attending_data)
                        
                        # Only process if it's actually a list
                        if isinstance(old_attending, list):
                            new_attending = {}
                            
                            for tournament_id in old_attending:
                                # Set default values for date and session
                                new_attending[tournament_id] = {
                                    "date": None,
                                    "session": "Day"  # Default to Day session
                                }
                            
                            # Update the user record
                            cur.execute(
                                "UPDATE users SET attending = %s WHERE id = %s",
                                (json.dumps(new_attending), user['id'])
                            )
                            count += 1
                            print(f"Migrated attendance data for {user['email']}")
                except Exception as e:
                    print(f"Error processing user {user['email']}: {str(e)}")
                    continue
            
            # Commit all changes
            conn.commit()
            print(f"Migration complete. Updated {count} users.")
            
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {str(e)}")
        return False
    finally:
        conn.close()
    
    return True

if __name__ == "__main__":
    migrate_attendance_data()