"""
Database Migration to add 'lanyard_exported' column to users table

This script adds the 'lanyard_exported' column to the users table,
enabling tracking of which lanyard orders have been exported for fulfillment.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def add_lanyard_exported_column():
    """Add the lanyard_exported column to the users table if it doesn't exist"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create engine and connect
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'lanyard_exported'
            """))
            
            if result.fetchone():
                print("Column 'lanyard_exported' already exists in users table")
                return True
            
            # Add the column
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN lanyard_exported BOOLEAN DEFAULT FALSE
            """))
            
            # Commit the transaction
            conn.commit()
            print("Successfully added 'lanyard_exported' column to users table")
            return True
            
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = add_lanyard_exported_column()
    sys.exit(0 if success else 1)