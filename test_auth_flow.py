#!/usr/bin/env python3
"""
Test authentication flow to verify website functionality
"""

import requests
from requests.sessions import Session

def test_authentication_flow():
    """Test the complete authentication flow"""
    
    # Create a session to maintain cookies
    session = Session()
    
    base_url = "https://bafb033d-26a4-47de-b4d6-96666ed788fe-00-2cbmkxn1203ip.kirk.replit.dev"
    
    print("Testing authentication flow...")
    
    # Step 1: Get login page
    print("1. Getting login page...")
    login_page = session.get(f"{base_url}/login")
    print(f"   Login page status: {login_page.status_code}")
    
    # Step 2: Submit login credentials
    print("2. Submitting login credentials...")
    login_data = {
        'email': 'sessiontest@example.com',
        'password': 'testpass123'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"   Login response status: {login_response.status_code}")
    print(f"   Login response headers: {dict(login_response.headers)}")
    
    if 'Location' in login_response.headers:
        redirect_url = login_response.headers['Location']
        print(f"   Redirect URL: {redirect_url}")
        
        # Step 3: Follow redirect to login-success
        if 'login-success' in redirect_url:
            print("3. Following redirect to login-success...")
            success_response = session.get(f"{base_url}{redirect_url}")
            print(f"   Login-success status: {success_response.status_code}")
            
            # Step 4: Try to access authenticated page
            print("4. Testing access to /my-tournaments...")
            tournaments_response = session.get(f"{base_url}/my-tournaments")
            print(f"   My-tournaments status: {tournaments_response.status_code}")
            
            if tournaments_response.status_code == 200:
                print("   SUCCESS: User is authenticated and can access protected pages!")
                return True
            elif tournaments_response.status_code == 302:
                print(f"   REDIRECT: Still being redirected to {tournaments_response.headers.get('Location', 'unknown')}")
            else:
                print(f"   ERROR: Unexpected status code {tournaments_response.status_code}")
    
    print("Authentication flow test completed.")
    return False

if __name__ == "__main__":
    test_authentication_flow()