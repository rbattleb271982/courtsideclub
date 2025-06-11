"""
Create test lanyard orders for testing the Lanyard Export Agent
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, ShippingAddress

def create_lanyard_test_data():
    """Create test users with lanyard orders for testing the export agent"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create engine and session
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Find users who don't have lanyard orders yet and update them
        test_users = session.query(User).filter(
            User.email.like('%test%'),
            User.lanyard_ordered == False
        ).limit(5).all()
        
        if not test_users:
            print("No test users found without lanyard orders")
            return True
        
        for i, user in enumerate(test_users):
            # Mark user as having ordered a lanyard
            user.lanyard_ordered = True
            user.lanyard_exported = False  # Ensure they're ready for export
            
            # Create shipping address if it doesn't exist
            existing_address = session.query(ShippingAddress).filter_by(user_id=user.id).first()
            if not existing_address:
                shipping_address = ShippingAddress(
                    user_id=user.id,
                    name=user.get_full_name(),
                    address1=f"{123 + i} Test Street",
                    address2=f"Apt {i + 1}" if i % 2 == 0 else "",
                    city="Test City",
                    state="CA",
                    zip_code=f"9000{i}",
                    country="United States"
                )
                session.add(shipping_address)
        
        session.commit()
        print(f"✅ Created {len(test_users)} test lanyard orders for export testing")
        
        # Display the test users created
        for user in test_users:
            print(f"   - {user.get_full_name()} ({user.email})")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"Error creating test lanyard data: {e}")
        return False

if __name__ == "__main__":
    success = create_lanyard_test_data()
    sys.exit(0 if success else 1)