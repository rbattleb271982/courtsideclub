import os
import logging
from app import app
from models import db, Tournament

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def add_and_populate_slug():
    with app.app_context():
        try:
            # Add the column
            db.session.execute("ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS slug TEXT;")
            db.session.commit()
            logger.info("Added slug column")

            # Populate slugs
            tournaments = Tournament.query.all()
            for t in tournaments:
                t.slug = t.id.lower().replace("_", "-")
            db.session.commit()
            logger.info("Populated slug values")

            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = add_and_populate_slug()
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1)