"""
Database Migration: Remove lanyard_ordered and lanyard_sent fields
Preserves lanyard_exported field for admin tracking
"""

import sys
sys.path.append('.')

from app import app
from models import db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upgrade():
    """Remove lanyard_ordered and lanyard_sent columns from users table"""
    with app.app_context():
        try:
            logger.info("Starting migration: removing lanyard_ordered and lanyard_sent columns")
            
            # Check if columns exist before attempting to drop them
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('lanyard_ordered', 'lanyard_sent')
            """))
            
            existing_columns = [row[0] for row in result]
            logger.info(f"Found existing columns: {existing_columns}")
            
            # Drop lanyard_ordered column if it exists
            if 'lanyard_ordered' in existing_columns:
                logger.info("Dropping lanyard_ordered column...")
                db.session.execute(text("ALTER TABLE users DROP COLUMN lanyard_ordered"))
                logger.info("✅ Dropped lanyard_ordered column")
            else:
                logger.info("lanyard_ordered column does not exist - skipping")
            
            # Drop lanyard_sent column if it exists
            if 'lanyard_sent' in existing_columns:
                logger.info("Dropping lanyard_sent column...")
                db.session.execute(text("ALTER TABLE users DROP COLUMN lanyard_sent"))
                logger.info("✅ Dropped lanyard_sent column")
            else:
                logger.info("lanyard_sent column does not exist - skipping")
            
            # Verify lanyard_exported still exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'lanyard_exported'
            """))
            
            if result.fetchone():
                logger.info("✅ Confirmed lanyard_exported column is preserved")
            else:
                logger.warning("⚠️  lanyard_exported column not found - may need to be added")
            
            db.session.commit()
            logger.info("✅ Migration completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}")
            db.session.rollback()
            raise

def downgrade():
    """Re-add lanyard_ordered and lanyard_sent columns (for rollback)"""
    with app.app_context():
        try:
            logger.info("Starting rollback: re-adding lanyard_ordered and lanyard_sent columns")
            
            # Add lanyard_ordered column back
            logger.info("Adding lanyard_ordered column...")
            db.session.execute(text("ALTER TABLE users ADD COLUMN lanyard_ordered BOOLEAN DEFAULT FALSE"))
            logger.info("✅ Added lanyard_ordered column")
            
            # Add lanyard_sent column back
            logger.info("Adding lanyard_sent column...")
            db.session.execute(text("ALTER TABLE users ADD COLUMN lanyard_sent BOOLEAN DEFAULT FALSE"))
            logger.info("✅ Added lanyard_sent column")
            
            db.session.commit()
            logger.info("✅ Rollback completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "upgrade":
            upgrade()
        elif sys.argv[1] == "downgrade":
            downgrade()
        else:
            print("Usage: python remove_lanyard_fields_migration.py [upgrade|downgrade]")
    else:
        print("Running upgrade by default...")
        upgrade()