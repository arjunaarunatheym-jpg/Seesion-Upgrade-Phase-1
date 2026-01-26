#!/usr/bin/env python3
"""
Debug script to check test structure
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://tab-extraction.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

def login_admin():
    """Login as admin"""
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        token = data['access_token']
        print(f"✅ Admin login successful")
        return session, token
    else:
        print(f"❌ Admin login failed: {response.status_code}")
        return None, None

def debug_tests():
    """Debug test structure"""
    session, token = login_admin()
    if not token:
        return
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get session to find program_id
    sessions_response = session.get(f"{BASE_URL}/sessions", headers=headers)
    if sessions_response.status_code != 200:
        print(f"❌ Failed to get sessions: {sessions_response.status_code}")
        return
    
    sessions = sessions_response.json()
    if not sessions:
        print("❌ No sessions found")
        return
    
    # Get the first session's program_id
    session_data = sessions[0]
    program_id = session_data.get('program_id')
    print(f"Session: {session_data.get('name')}")
    print(f"Program ID: {program_id}")
    
    # Get tests for this program
    tests_response = session.get(f"{BASE_URL}/tests/program/{program_id}", headers=headers)
    
    if tests_response.status_code == 200:
        tests = tests_response.json()
        print(f"\nFound {len(tests)} tests:")
        
        for i, test in enumerate(tests):
            print(f"\nTest {i+1}:")
            print(f"  Fields: {list(test.keys())}")
            print(f"  ID: {test.get('id', 'N/A')}")
            print(f"  Title: {test.get('title', 'N/A')}")
            print(f"  Program ID: {test.get('program_id', 'N/A')}")
            print(f"  Questions count: {len(test.get('questions', []))}")
    else:
        print(f"❌ Failed to get tests: {tests_response.status_code} - {tests_response.text}")

if __name__ == "__main__":
    debug_tests()