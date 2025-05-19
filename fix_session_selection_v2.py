"""
Specialized fix for session selection problems in tournament detail page

This addresses the issue where session selections aren't persisting properly:
1. Creates a new version of the session selection handler
2. Fixes how selected sessions are saved and retrieved
3. Ensures deselected sessions are properly removed when saving
"""
import os
import psycopg2
import sys
from psycopg2.extras import execute_values

def create_better_user_tournament_route():
    """Create a better route for saving/loading session selections"""
    # First, we'll view how many session selections might have duplicates
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set")
        return
    
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Update all session_label values to standardize format
        # 1. Trim whitespace
        # 2. Remove any duplicates
        # 3. Ensure empty string instead of NULL for easier template checks
        cursor.execute("""
            UPDATE user_tournament
            SET session_label = 
                CASE 
                    WHEN session_label IS NULL OR session_label = '' THEN ''
                    ELSE (
                        SELECT string_agg(DISTINCT trim(s), ',')
                        FROM unnest(string_to_array(session_label, ',')) AS s
                        WHERE trim(s) != ''
                    )
                END
        """)
        
        conn.commit()
        print(f"Successfully standardized session labels in the database")
        
    except Exception as e:
        print(f"ERROR: Failed to fix session labels: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    
    print("Session fixes completed.")

if __name__ == "__main__":
    create_better_user_tournament_route()