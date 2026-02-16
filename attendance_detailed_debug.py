#!/usr/bin/env python3
"""
Detailed debug test for attendance records issue
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://finance-correction.preview.emergentagent.com/api"

def detailed_debug():
    session = requests.Session()
    
    # Login as admin
    admin_login = {"email": "admin@example.com", "password": "admin123"}
    response = session.post(f"{BASE_URL}/auth/login", json=admin_login)
    admin_token = response.json()['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    
    # Login as coordinator
    coordinator_login = {"email": "testcoordinator@bugfix.com", "password": "coordinator123"}
    response = session.post(f"{BASE_URL}/auth/login", json=coordinator_login)
    coordinator_token = response.json()['access_token']
    coordinator_headers = {'Authorization': f'Bearer {coordinator_token}'}
    
    # Login as participant
    participant_login = {"email": "testparticipant@bugfix.com", "password": "participant123"}
    response = session.post(f"{BASE_URL}/auth/login", json=participant_login)
    participant_token = response.json()['access_token']
    participant_headers = {'Authorization': f'Bearer {participant_token}'}
    participant_id = response.json()['user']['id']
    
    # Get sessions
    response = session.get(f"{BASE_URL}/sessions", headers=admin_headers)
    sessions = response.json()
    test_session = None
    for s in sessions:
        if "Critical Bug Fix Test Session" in s.get('name', ''):
            test_session = s
            break
    
    session_id = test_session['id']
    print(f"🎯 Testing session: {session_id}")
    print(f"👤 Participant ID: {participant_id}")
    
    # Create fresh attendance records
    today = datetime.now().date().isoformat()
    print(f"📅 Today's date: {today}")
    
    # Try to create a new attendance record for a different date
    import time
    time.sleep(1)  # Wait a second
    
    # Clock in with fresh session
    clock_in_data = {"session_id": session_id}
    response = session.post(f"{BASE_URL}/attendance/clock-in", json=clock_in_data, headers=participant_headers)
    print(f"🕐 Fresh clock-in: {response.status_code} - {response.text}")
    
    if response.status_code == 400:
        print("⚠️  Already clocked in, that's expected from previous test")
    
    # Check individual attendance first
    response = session.get(f"{BASE_URL}/attendance/{session_id}/{participant_id}", headers=participant_headers)
    print(f"\n👤 Individual attendance check: {response.status_code}")
    if response.status_code == 200:
        records = response.json()
        print(f"👤 Found {len(records)} individual records:")
        for i, record in enumerate(records):
            print(f"   Record {i+1}:")
            print(f"     ID: {record.get('id')}")
            print(f"     Participant ID: {record.get('participant_id')}")
            print(f"     Session ID: {record.get('session_id')}")
            print(f"     Date: {record.get('date')}")
            print(f"     Clock-in: {record.get('clock_in')}")
            print(f"     Clock-out: {record.get('clock_out')}")
    
    # Now check session-level attendance
    print(f"\n📊 Session-level attendance check...")
    response = session.get(f"{BASE_URL}/attendance/session/{session_id}", headers=coordinator_headers)
    print(f"📊 Session attendance response: {response.status_code}")
    
    if response.status_code == 200:
        records = response.json()
        print(f"📊 Found {len(records)} session-level records:")
        for i, record in enumerate(records):
            print(f"   Record {i+1}:")
            print(f"     ID: {record.get('id')}")
            print(f"     Participant ID: {record.get('participant_id')}")
            print(f"     Session ID: {record.get('session_id')}")
            print(f"     Date: {record.get('date')}")
            print(f"     Clock-in: {record.get('clock_in')}")
            print(f"     Clock-out: {record.get('clock_out')}")
            print(f"     Participant Name: {record.get('participant_name')}")
    else:
        print(f"❌ Session attendance failed: {response.text}")
    
    # Test with admin access too
    print(f"\n🔑 Testing with admin access...")
    response = session.get(f"{BASE_URL}/attendance/session/{session_id}", headers=admin_headers)
    print(f"🔑 Admin attendance response: {response.status_code}")
    
    if response.status_code == 200:
        records = response.json()
        print(f"🔑 Admin found {len(records)} records")
    else:
        print(f"❌ Admin attendance failed: {response.text}")

if __name__ == "__main__":
    detailed_debug()