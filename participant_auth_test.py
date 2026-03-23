#!/usr/bin/env python3
"""
Test participant authorization for calendar and past training endpoints
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://payroll-fix-19.preview.emergentagent.com/api"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def test_participant_authorization():
    """Test that participants are properly denied access to calendar and past training endpoints"""
    
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    # Login as admin first to create a participant
    admin_login = {
        "email": "arjuna@mddrc.com.my",
        "password": "Dana102229"
    }
    
    try:
        response = session.post(f"{BASE_URL}/auth/login", json=admin_login)
        if response.status_code == 200:
            admin_token = response.json()['access_token']
            log("✅ Admin login successful")
        else:
            log(f"❌ Admin login failed: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Admin login error: {str(e)}", "ERROR")
        return False
    
    # Create a test participant
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    participant_data = {
        "email": "testparticipant@example.com",
        "password": "participant123",
        "full_name": "Test Participant for Auth",
        "id_number": "TPAUTH001",
        "role": "participant",
        "location": "Test Location"
    }
    
    try:
        response = session.post(f"{BASE_URL}/auth/register", json=participant_data, headers=admin_headers)
        if response.status_code == 200:
            log("✅ Test participant created successfully")
        elif response.status_code == 400 and "User already exists" in response.text:
            log("✅ Test participant already exists (expected)")
        else:
            log(f"❌ Participant creation failed: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Participant creation error: {str(e)}", "ERROR")
        return False
    
    # Login as participant
    participant_login = {
        "email": "testparticipant@example.com",
        "password": "participant123"
    }
    
    try:
        response = session.post(f"{BASE_URL}/auth/login", json=participant_login)
        if response.status_code == 200:
            participant_token = response.json()['access_token']
            log("✅ Participant login successful")
        else:
            log(f"❌ Participant login failed: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Participant login error: {str(e)}", "ERROR")
        return False
    
    participant_headers = {'Authorization': f'Bearer {participant_token}'}
    
    # Test calendar endpoint access (should fail)
    log("Testing participant access to calendar endpoint...")
    try:
        response = session.get(f"{BASE_URL}/sessions/calendar", headers=participant_headers)
        if response.status_code == 403:
            log("✅ Participant correctly denied access to calendar endpoint (403)")
        else:
            log(f"❌ Expected 403 for participant calendar access, got: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Participant calendar test error: {str(e)}", "ERROR")
        return False
    
    # Test past training endpoint access (should fail)
    log("Testing participant access to past training endpoint...")
    try:
        response = session.get(f"{BASE_URL}/sessions/past-training", headers=participant_headers)
        if response.status_code == 403:
            log("✅ Participant correctly denied access to past training endpoint (403)")
        else:
            log(f"❌ Expected 403 for participant past training access, got: {response.status_code}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Participant past training test error: {str(e)}", "ERROR")
        return False
    
    log("🎉 All participant authorization tests passed!")
    return True

if __name__ == "__main__":
    success = test_participant_authorization()
    exit(0 if success else 1)