#!/usr/bin/env python3
"""
Debug test for attendance records issue
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://marketing-portal-3.preview.emergentagent.com/api"

def debug_attendance():
    # Login as admin
    admin_login = {"email": "admin@example.com", "password": "admin123"}
    session = requests.Session()
    
    response = session.post(f"{BASE_URL}/auth/login", json=admin_login)
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.status_code}")
        return
    
    admin_token = response.json()['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    
    # Login as participant
    participant_login = {"email": "testparticipant@bugfix.com", "password": "participant123"}
    response = session.post(f"{BASE_URL}/auth/login", json=participant_login)
    if response.status_code != 200:
        print(f"❌ Participant login failed: {response.status_code}")
        return
    
    participant_token = response.json()['access_token']
    participant_headers = {'Authorization': f'Bearer {participant_token}'}
    participant_id = response.json()['user']['id']
    
    # Get the test session ID (from previous test)
    response = session.get(f"{BASE_URL}/sessions", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Failed to get sessions: {response.status_code}")
        return
    
    sessions = response.json()
    test_session = None
    for s in sessions:
        if "Critical Bug Fix Test Session" in s.get('name', ''):
            test_session = s
            break
    
    if not test_session:
        print("❌ Test session not found")
        return
    
    session_id = test_session['id']
    print(f"✅ Found test session: {session_id}")
    
    # Clock in
    clock_in_data = {"session_id": session_id}
    response = session.post(f"{BASE_URL}/attendance/clock-in", json=clock_in_data, headers=participant_headers)
    print(f"🕐 Clock-in response: {response.status_code} - {response.text}")
    
    # Clock out
    clock_out_data = {"session_id": session_id}
    response = session.post(f"{BASE_URL}/attendance/clock-out", json=clock_out_data, headers=participant_headers)
    print(f"🕐 Clock-out response: {response.status_code} - {response.text}")
    
    # Check attendance records as coordinator
    coordinator_login = {"email": "testcoordinator@bugfix.com", "password": "coordinator123"}
    response = session.post(f"{BASE_URL}/auth/login", json=coordinator_login)
    if response.status_code != 200:
        print(f"❌ Coordinator login failed: {response.status_code}")
        return
    
    coordinator_token = response.json()['access_token']
    coordinator_headers = {'Authorization': f'Bearer {coordinator_token}'}
    
    # Get attendance records
    response = session.get(f"{BASE_URL}/attendance/session/{session_id}", headers=coordinator_headers)
    print(f"📊 Attendance records response: {response.status_code}")
    if response.status_code == 200:
        records = response.json()
        print(f"📊 Found {len(records)} attendance records")
        for record in records:
            print(f"   - Participant: {record.get('participant_id')}")
            print(f"     Clock-in: {record.get('clock_in')}")
            print(f"     Clock-out: {record.get('clock_out')}")
            print(f"     Date: {record.get('date')}")
    else:
        print(f"❌ Failed to get attendance records: {response.text}")
    
    # Check individual participant attendance
    response = session.get(f"{BASE_URL}/attendance/{session_id}/{participant_id}", headers=participant_headers)
    print(f"👤 Individual attendance response: {response.status_code}")
    if response.status_code == 200:
        records = response.json()
        print(f"👤 Individual records: {len(records)}")
        for record in records:
            print(f"   - Clock-in: {record.get('clock_in')}")
            print(f"     Clock-out: {record.get('clock_out')}")
    else:
        print(f"❌ Individual attendance failed: {response.text}")

if __name__ == "__main__":
    debug_attendance()