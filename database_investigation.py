#!/usr/bin/env python3
"""
Database Investigation Script - Check participant 566589 assignment status
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://trainingfix.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
PARTICIPANT_IC = "566589"

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

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
        log(f"✅ Admin login successful")
        return session, token
    else:
        log(f"❌ Admin login failed: {response.status_code}", "ERROR")
        return None, None

def investigate_database():
    """Investigate database state for participant 566589"""
    session, token = login_admin()
    if not token:
        return
    
    headers = {'Authorization': f'Bearer {token}'}
    
    log("🔍 INVESTIGATING DATABASE STATE FOR PARTICIPANT 566589")
    log("="*60)
    
    # 1. Check all sessions in system
    log("1. CHECKING ALL SESSIONS IN SYSTEM:")
    response = session.get(f"{BASE_URL}/sessions", headers=headers)
    
    if response.status_code == 200:
        sessions = response.json()
        log(f"   Total sessions found: {len(sessions)}")
        
        participant_566589_id = None
        
        for i, session_data in enumerate(sessions):
            log(f"\n   Session {i+1}: {session_data.get('name', 'Unknown')}")
            log(f"     ID: {session_data.get('id', 'N/A')}")
            log(f"     Company: {session_data.get('company_name', 'Unknown')}")
            log(f"     Program: {session_data.get('program_name', 'Unknown')}")
            log(f"     Dates: {session_data.get('start_date', 'N/A')} to {session_data.get('end_date', 'N/A')}")
            log(f"     Status: {session_data.get('status', 'N/A')}")
            log(f"     Participant IDs count: {len(session_data.get('participant_ids', []))}")
            
            # Check participants in this session
            if session_data.get('participant_ids'):
                log(f"     Participant IDs: {session_data['participant_ids']}")
                
                # Get participant details
                participants_response = session.get(f"{BASE_URL}/sessions/{session_data['id']}/participants", headers=headers)
                if participants_response.status_code == 200:
                    participants = participants_response.json()
                    log(f"     Participants in session:")
                    for p in participants:
                        log(f"       - {p.get('full_name', 'Unknown')} (IC: {p.get('id_number', 'N/A')}, ID: {p.get('id', 'N/A')})")
                        if p.get('id_number') == PARTICIPANT_IC:
                            participant_566589_id = p.get('id')
                            log(f"         🎯 FOUND PARTICIPANT 566589! User ID: {participant_566589_id}")
    else:
        log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
        return
    
    # 2. Check all users to find participant 566589
    log(f"\n2. SEARCHING FOR PARTICIPANT 566589 IN USER DATABASE:")
    
    # Try to find user by IC number
    users_response = session.get(f"{BASE_URL}/users", headers=headers)
    if users_response.status_code == 200:
        users = users_response.json()
        log(f"   Total users in system: {len(users)}")
        
        found_566589 = False
        for user in users:
            if user.get('id_number') == PARTICIPANT_IC:
                found_566589 = True
                participant_566589_id = user.get('id')
                log(f"   ✅ FOUND USER 566589:")
                log(f"     Name: {user.get('full_name', 'Unknown')}")
                log(f"     ID: {user.get('id', 'N/A')}")
                log(f"     IC Number: {user.get('id_number', 'N/A')}")
                log(f"     Email: {user.get('email', 'N/A')}")
                log(f"     Role: {user.get('role', 'N/A')}")
                break
        
        if not found_566589:
            log(f"   ❌ USER 566589 NOT FOUND IN USER DATABASE", "ERROR")
            return
    else:
        log(f"❌ Failed to get users: {users_response.status_code}", "ERROR")
        return
    
    # 3. Check if participant 566589 is assigned to any sessions
    log(f"\n3. CHECKING SESSION ASSIGNMENTS FOR PARTICIPANT 566589 (ID: {participant_566589_id}):")
    
    assigned_sessions = []
    for session_data in sessions:
        if participant_566589_id in session_data.get('participant_ids', []):
            assigned_sessions.append(session_data)
            log(f"   ✅ ASSIGNED TO: {session_data.get('name', 'Unknown')} (ID: {session_data.get('id')})")
    
    if not assigned_sessions:
        log(f"   ❌ PARTICIPANT 566589 IS NOT ASSIGNED TO ANY SESSIONS", "ERROR")
        log(f"   🔍 This explains why the participant portal shows 'No sessions assigned'")
    
    # 4. Check participant_access records
    log(f"\n4. CHECKING PARTICIPANT_ACCESS RECORDS:")
    
    if assigned_sessions:
        for session_data in assigned_sessions:
            session_id = session_data['id']
            participants_response = session.get(f"{BASE_URL}/sessions/{session_id}/participants", headers=headers)
            
            if participants_response.status_code == 200:
                participants = participants_response.json()
                
                for participant in participants:
                    if participant.get('id') == participant_566589_id:
                        access_info = participant.get('access_info', {})
                        if access_info:
                            log(f"   ✅ PARTICIPANT_ACCESS RECORD FOUND for session {session_data.get('name')}:")
                            log(f"     Access ID: {access_info.get('id', 'N/A')}")
                            log(f"     Pre-test released: {access_info.get('pre_test_released', False)}")
                            log(f"     Post-test released: {access_info.get('post_test_released', False)}")
                            log(f"     Feedback released: {access_info.get('feedback_released', False)}")
                            log(f"     Certificate released: {access_info.get('certificate_released', False)}")
                        else:
                            log(f"   ❌ NO PARTICIPANT_ACCESS RECORD for session {session_data.get('name')}", "ERROR")
    else:
        log(f"   ⚠️  Cannot check participant_access records - no sessions assigned")
    
    # 5. Summary and recommendations
    log(f"\n5. SUMMARY AND RECOMMENDATIONS:")
    log("="*60)
    
    if not assigned_sessions:
        log("❌ ROOT CAUSE IDENTIFIED: Participant 566589 is not assigned to any sessions")
        log("📋 RECOMMENDATIONS:")
        log("   1. Admin needs to create a session and assign participant 566589")
        log("   2. Or add participant 566589 to an existing session")
        log("   3. Ensure participant_access records are created when assigning")
        log("   4. Enable appropriate release flags (pre-test, post-test, feedback, certificate)")
    else:
        log("✅ Participant is assigned to sessions - investigating other issues...")

if __name__ == "__main__":
    investigate_database()