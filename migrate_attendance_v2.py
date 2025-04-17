import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def migrate_attendance_data_v2():
    """
    Migrate user attendance data from single date/session to multiple dates/sessions format:
    Old: {"tournament_id": {"date": "2025-01-19", "session": "Day"}}
    New: {"tournament_id": {"dates": ["2025-01-19"], "sessions": ["Day"]}}
    """
    print("Starting attendance data v2 migration...")
    
    # Connect directly to the database
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    conn.autocommit = False
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get users with older format attendance data
            cur.execute("SELECT id, email, attending FROM users WHERE attending IS NOT NULL")
            users = cur.fetchall()
            count = 0
            
            for user in users:
                try:
                    # Parse the attending data
                    attending_data = user['attending']
                    
                    # Skip if it's not a valid JSON object
                    if not attending_data.startswith('{'):
                        continue
                    
                    old_attending = json.loads(attending_data)
                    new_attending = {}
                    updated = False
                    
                    # Check each tournament entry
                    for tournament_id, attendance_info in old_attending.items():
                        # Check if it has the old format (has 'date' or 'session' keys)
                        if 'date' in attendance_info or 'session' in attendance_info:
                            updated = True
                            # Convert to new format
                            dates = []
                            sessions = []
                            
                            # Handle date field
                            if 'date' in attendance_info and attendance_info['date']:
                                dates.append(attendance_info['date'])
                            
                            # Handle session field
                            if 'session' in attendance_info and attendance_info['session']:
                                sessions.append(attendance_info['session'])
                            
                            # Create new format entry
                            new_attending[tournament_id] = {
                                'dates': dates,
                                'sessions': sessions if sessions else ['Day']  # Default to Day if empty
                            }
                        else:
                            # Already in new format, keep as is
                            new_attending[tournament_id] = attendance_info
                    
                    # Only update if changes were made
                    if updated:
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
    migrate_attendance_data_v2()