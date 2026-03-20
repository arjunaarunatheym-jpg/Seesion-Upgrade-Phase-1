#!/usr/bin/env python3
"""
Participant Assignment Fix and Test Script
This script will:
1. Assign participant 566589 to an existing session
2. Create participant_access records
3. Enable release flags
4. Test the complete workflow
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://balance-sheet-ui.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
PARTICIPANT_IC = "566589"
PARTICIPANT_PASSWORD = "mddrc1"

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

def login_participant():
    """Login as participant 566589"""
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    login_data = {
        "email": PARTICIPANT_IC,
        "password": PARTICIPANT_PASSWORD
    }
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        token = data['access_token']
        participant_id = data['user']['id']
        log(f"✅ Participant login successful: {data['user']['full_name']}")
        return session, token, participant_id
    else:
        log(f"❌ Participant login failed: {response.status_code}", "ERROR")
        return None, None, None

def assign_participant_to_session():
    """Assign participant 566589 to the first available session"""
    admin_session, admin_token = login_admin()
    if not admin_token:
        return None, None
    
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    # Get participant ID
    participant_session, participant_token, participant_id = login_participant()
    if not participant_id:
        return None, None
    
    log("🔧 ASSIGNING PARTICIPANT 566589 TO SESSION...")
    
    # Get available sessions
    response = admin_session.get(f"{BASE_URL}/sessions", headers=headers)
    if response.status_code != 200:
        log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
        return None, None
    
    sessions = response.json()
    if not sessions:
        log("❌ No sessions available to assign participant to", "ERROR")
        return None, None
    
    # Use the first session (Defensive Riding session)
    target_session = sessions[0]
    session_id = target_session['id']
    session_name = target_session.get('name', 'Unknown')
    
    log(f"   Target session: {session_name} (ID: {session_id})")
    
    # Add participant to session by updating participant_ids array
    current_participant_ids = target_session.get('participant_ids', [])
    
    if participant_id not in current_participant_ids:
        updated_participant_ids = current_participant_ids + [participant_id]
        
        update_data = {
            "participant_ids": updated_participant_ids
        }
        
        response = admin_session.put(f"{BASE_URL}/sessions/{session_id}", json=update_data, headers=headers)
        
        if response.status_code == 200:
            log(f"   ✅ Participant added to session participant_ids array")
        else:
            log(f"   ❌ Failed to add participant to session: {response.status_code} - {response.text}", "ERROR")
            return None, None
    else:
        log(f"   ℹ️  Participant already in session participant_ids array")
    
    return session_id, participant_id

def create_participant_access_record(session_id, participant_id):
    """Create and configure participant_access record"""
    admin_session, admin_token = login_admin()
    if not admin_token:
        return False
    
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    log("🔧 CREATING AND CONFIGURING PARTICIPANT_ACCESS RECORD...")
    
    # Update participant access with all permissions enabled
    access_data = {
        "pre_test_released": True,
        "post_test_released": True,
        "feedback_released": True,
        "certificate_released": True
    }
    
    # Use query parameters for participant_id and session_id
    url = f"{BASE_URL}/participant-access/update?participant_id={participant_id}&session_id={session_id}"
    response = admin_session.post(url, json=access_data, headers=headers)
    
    if response.status_code == 200:
        log(f"   ✅ Participant access record created and configured")
        log(f"     Pre-test released: True")
        log(f"     Post-test released: True")
        log(f"     Feedback released: True")
        log(f"     Certificate released: True")
        return True
    else:
        log(f"   ❌ Failed to create participant access: {response.status_code} - {response.text}", "ERROR")
        return False

def test_participant_workflow():
    """Test the complete participant workflow after assignment"""
    participant_session, participant_token, participant_id = login_participant()
    if not participant_token:
        return False
    
    headers = {'Authorization': f'Bearer {participant_token}'}
    
    log("🧪 TESTING PARTICIPANT WORKFLOW AFTER ASSIGNMENT...")
    
    # Test 1: Get sessions
    log("\n   Test 1: GET /api/sessions")
    response = participant_session.get(f"{BASE_URL}/sessions", headers=headers)
    
    if response.status_code == 200:
        sessions = response.json()
        log(f"     ✅ Sessions retrieved: {len(sessions)} session(s)")
        
        if len(sessions) > 0:
            session = sessions[0]
            session_id = session['id']
            log(f"     Session: {session.get('name', 'Unknown')}")
            
            # Test 2: Get session details
            log(f"\n   Test 2: GET /api/sessions/{session_id}")
            detail_response = participant_session.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
            
            if detail_response.status_code == 200:
                log(f"     ✅ Session details retrieved successfully")
            else:
                log(f"     ❌ Session details failed: {detail_response.status_code}", "ERROR")
            
            # Test 3: Get available tests
            log(f"\n   Test 3: GET /api/sessions/{session_id}/tests/available")
            tests_response = participant_session.get(f"{BASE_URL}/sessions/{session_id}/tests/available", headers=headers)
            
            if tests_response.status_code == 200:
                tests_data = tests_response.json()
                log(f"     ✅ Test availability retrieved successfully")
                log(f"     Pre-test released: {tests_data.get('pre_test_released', False)}")
                log(f"     Post-test released: {tests_data.get('post_test_released', False)}")
            else:
                log(f"     ❌ Test availability failed: {tests_response.status_code}", "ERROR")
            
            # Test 4: Get certificates
            log(f"\n   Test 4: GET /api/certificates/my-certificates")
            cert_response = participant_session.get(f"{BASE_URL}/certificates/my-certificates", headers=headers)
            
            if cert_response.status_code == 200:
                certificates = cert_response.json()
                log(f"     ✅ Certificates retrieved: {len(certificates)} certificate(s)")
            else:
                log(f"     ❌ Certificates failed: {cert_response.status_code}", "ERROR")
            
            return True
        else:
            log(f"     ❌ No sessions returned after assignment", "ERROR")
            return False
    else:
        log(f"     ❌ Sessions retrieval failed: {response.status_code}", "ERROR")
        return False

def verify_database_state():
    """Verify the database state after assignment"""
    admin_session, admin_token = login_admin()
    if not admin_token:
        return False
    
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    log("🔍 VERIFYING DATABASE STATE AFTER ASSIGNMENT...")
    
    # Get participant ID
    _, _, participant_id = login_participant()
    if not participant_id:
        return False
    
    # Check sessions
    response = admin_session.get(f"{BASE_URL}/sessions", headers=headers)
    if response.status_code != 200:
        log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
        return False
    
    sessions = response.json()
    assigned_sessions = []
    
    for session in sessions:
        if participant_id in session.get('participant_ids', []):
            assigned_sessions.append(session)
            session_id = session['id']
            log(f"   ✅ Participant assigned to: {session.get('name', 'Unknown')}")
            
            # Check participant_access record
            participants_response = admin_session.get(f"{BASE_URL}/sessions/{session_id}/participants", headers=headers)
            
            if participants_response.status_code == 200:
                participants = participants_response.json()
                
                for participant in participants:
                    if participant.get('id') == participant_id:
                        access_info = participant.get('access_info', {})
                        if access_info:
                            log(f"     ✅ Participant_access record exists")
                            log(f"       Pre-test released: {access_info.get('pre_test_released', False)}")
                            log(f"       Post-test released: {access_info.get('post_test_released', False)}")
                            log(f"       Feedback released: {access_info.get('feedback_released', False)}")
                            log(f"       Certificate released: {access_info.get('certificate_released', False)}")
                        else:
                            log(f"     ❌ No participant_access record found", "ERROR")
    
    if assigned_sessions:
        log(f"✅ Database verification complete. Participant assigned to {len(assigned_sessions)} session(s)")
        return True
    else:
        log(f"❌ Database verification failed. Participant not assigned to any sessions", "ERROR")
        return False

def main():
    """Main execution function"""
    log("🚀 PARTICIPANT 566589 ASSIGNMENT FIX AND TEST")
    log("="*60)
    
    # Step 1: Assign participant to session
    session_id, participant_id = assign_participant_to_session()
    if not session_id or not participant_id:
        log("❌ Failed to assign participant to session", "ERROR")
        return False
    
    # Step 2: Create participant_access record
    if not create_participant_access_record(session_id, participant_id):
        log("❌ Failed to create participant_access record", "ERROR")
        return False
    
    # Step 3: Test participant workflow
    if not test_participant_workflow():
        log("❌ Participant workflow test failed", "ERROR")
        return False
    
    # Step 4: Verify database state
    if not verify_database_state():
        log("❌ Database verification failed", "ERROR")
        return False
    
    log("\n" + "="*60)
    log("🎉 PARTICIPANT 566589 ASSIGNMENT AND TESTING COMPLETE!")
    log("✅ Participant should now see sessions in their portal")
    log("✅ All endpoints should return proper data")
    log("✅ Participant portal should no longer show 'No sessions assigned'")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)