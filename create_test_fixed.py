#!/usr/bin/env python3
"""
Create a test for the program to fix the test availability endpoint
"""

import requests
import json

# Configuration
BASE_URL = "https://marketing-flow-test.preview.emergentagent.com/api"
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

def create_test():
    """Create a test for the program"""
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
    print(f"Creating test for program: {program_id}")
    
    # Create a pre-test
    test_data = {
        "program_id": program_id,
        "title": "Pre-Test - Defensive Riding",
        "questions": [
            {
                "question": "What is the recommended following distance in good weather conditions?",
                "options": ["1 second", "2 seconds", "3 seconds", "4 seconds"],
                "correct_answer": "2"
            },
            {
                "question": "When should you check your mirrors while riding?",
                "options": ["Only when changing lanes", "Every 5-8 seconds", "Only when parking", "Once per trip"],
                "correct_answer": "1"
            }
        ]
    }
    
    response = session.post(f"{BASE_URL}/tests", json=test_data, headers=headers)
    
    if response.status_code == 200:
        test = response.json()
        print(f"✅ Pre-test created successfully: {test.get('id')}")
    else:
        print(f"❌ Pre-test creation failed: {response.status_code} - {response.text}")
        return
    
    # Create a post-test
    test_data = {
        "program_id": program_id,
        "title": "Post-Test - Defensive Riding",
        "questions": [
            {
                "question": "What is the recommended following distance in good weather conditions?",
                "options": ["1 second", "2 seconds", "3 seconds", "4 seconds"],
                "correct_answer": "2"
            },
            {
                "question": "When should you check your mirrors while riding?",
                "options": ["Only when changing lanes", "Every 5-8 seconds", "Only when parking", "Once per trip"],
                "correct_answer": "1"
            }
        ]
    }
    
    response = session.post(f"{BASE_URL}/tests", json=test_data, headers=headers)
    
    if response.status_code == 200:
        test = response.json()
        print(f"✅ Post-test created successfully: {test.get('id')}")
    else:
        print(f"❌ Post-test creation failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    create_test()