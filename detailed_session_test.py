#!/usr/bin/env python3
"""
Detailed Session Creation Test - Verify exact response structure
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://balance-sheet-ui.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

def test_session_creation_response():
    """Test the exact response structure of session creation"""
    session = requests.Session()
    session.headers.update({'Content-Type': 'application/json'})
    
    # Login
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    admin_token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    # Get first program and company
    programs = session.get(f"{BASE_URL}/programs", headers=headers).json()
    companies = session.get(f"{BASE_URL}/companies", headers=headers).json()
    
    if not programs or not companies:
        print("❌ No programs or companies found")
        return False
    
    # Create session
    session_data = {
        "name": "Detailed Test Session",
        "program_id": programs[0]['id'],
        "company_id": companies[0]['id'],
        "location": "Test Location",
        "start_date": "2025-12-01",
        "end_date": "2025-12-05",
        "participant_ids": [],
        "participants": [
            {
                "full_name": "Detailed Test Participant",
                "id_number": "990101-01-5678",
                "email": f"detailedtest{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
                "password": "mddrc1",
                "phone_number": ""
            }
        ],
        "supervisor_ids": [],
        "supervisors": [],
        "trainer_assignments": [],
        "coordinator_id": None
    }
    
    response = session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
    
    if response.status_code not in [200, 201]:
        print(f"❌ Session creation failed: {response.status_code} - {response.text}")
        return False
    
    data = response.json()
    
    print("✅ Session Creation Response Analysis:")
    print("=" * 50)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Keys: {list(data.keys())}")
    
    if 'session' in data:
        session_obj = data['session']
        print(f"\nSession Object Keys: {list(session_obj.keys())}")
        print(f"Session ID: {session_obj.get('id')}")
        print(f"Session Name: {session_obj.get('name')}")
        print(f"Completion Status: {session_obj.get('completion_status')}")
        print(f"Completed by Coordinator: {session_obj.get('completed_by_coordinator')}")
        
        # Verify expected values
        if session_obj.get('completion_status') == 'ongoing':
            print("✅ completion_status = 'ongoing' ✓")
        else:
            print(f"❌ completion_status = '{session_obj.get('completion_status')}' (expected 'ongoing')")
        
        if session_obj.get('completed_by_coordinator') == False:
            print("✅ completed_by_coordinator = False ✓")
        else:
            print(f"❌ completed_by_coordinator = '{session_obj.get('completed_by_coordinator')}' (expected False)")
    
    if 'participant_results' in data:
        print(f"\nParticipant Results: {data['participant_results']}")
    
    if 'supervisor_results' in data:
        print(f"Supervisor Results: {data['supervisor_results']}")
    
    print("\n" + "=" * 50)
    print("Full Response Structure:")
    print(json.dumps(data, indent=2))
    
    return True

if __name__ == "__main__":
    test_session_creation_response()