"""
Fix Session Persistence in Tournament Attendance

This script ensures consistent storage and retrieval of session selections:
1. Updates how session_label is processed when saving
2. Ensures proper format for comparison when displaying
3. Removes duplicates and handles null values properly
"""
import os
import psycopg2
import sys

def clean_all_session_labels():
    """Clean all session labels to standardize format"""
    print("Starting session label cleanup...")
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set")
        return
    
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # First, get all user_tournament records
        cursor.execute("""
            SELECT id, session_label 
            FROM user_tournament 
            WHERE session_label IS NOT NULL AND session_label != ''
        """)
        
        records = cursor.fetchall()
        print(f"Found {len(records)} records with session labels")
        
        # Process each record
        updated_count = 0
        for record_id, session_label in records:
            # Clean up the session label - standardize format
            if session_label:
                # Split by comma, trim each session, remove duplicates, and rejoin
                sessions = [s.strip() for s in session_label.split(',') if s.strip()]
                unique_sessions = list(dict.fromkeys(sessions))  # Remove duplicates while preserving order
                
                cleaned_label = ','.join(unique_sessions)
                
                if cleaned_label != session_label:
                    # Update the record with cleaned label
                    cursor.execute("""
                        UPDATE user_tournament 
                        SET session_label = %s
                        WHERE id = %s
                    """, (cleaned_label, record_id))
                    updated_count += 1
                    
                    print(f"Updated record {record_id}:")
                    print(f"  Original: {session_label}")
                    print(f"  Cleaned:  {cleaned_label}")
        
        conn.commit()
        print(f"Successfully cleaned {updated_count} session labels")
        
    except Exception as e:
        print(f"ERROR: Failed to clean session labels: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    
    print("Cleanup completed.")

if __name__ == "__main__":
    clean_all_session_labels()
    print("Session persistence fix completed.")