#!/usr/bin/env python3
"""
Test script to debug tournament detail page with authenticated user
"""

import requests
from models import User
from app import app

def test_tournament_detail():
    with app.app_context():
        # Find a test user
        test_user = User.query.filter_by(test_user=True).first()
        if not test_user:
            print("No test users found")
            return
        
        print(f"Using test user: {test_user.email}")
        
        # Create a session with the test server
        session = requests.Session()
        
        # Try to login as the test user
        login_data = {
            'email': test_user.email,
            'password': 'testpass123'  # Standard test user password
        }
        
        try:
            # Login
            login_response = session.post('http://localhost:5000/login', data=login_data)
            print(f"Login response status: {login_response.status_code}")
            
            # Access tournament detail page
            tournament_response = session.get('http://localhost:5000/tournaments/wimbledon')
            print(f"Tournament detail response status: {tournament_response.status_code}")
            
            if tournament_response.status_code == 200:
                print("Successfully accessed tournament detail page")
                # Check if the page contains tournament days
                if "tournament_days length: 0" in tournament_response.text:
                    print("FOUND ISSUE: tournament_days length is 0")
                else:
                    print("Tournament days appear to be working")
            else:
                print("Failed to access tournament detail page")
                
        except Exception as e:
            print(f"Error during test: {e}")

if __name__ == "__main__":
    test_tournament_detail()