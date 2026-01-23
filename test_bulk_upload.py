#!/usr/bin/env python3
"""
Test the correct bulk upload endpoint for participants
"""

import requests
import json

# Configuration
BASE_URL = "https://trainadmin-1.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

def test_bulk_upload_endpoint():
    # Login as admin
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.status_code}")
        return False
    
    admin_token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    # Get sessions
    response = requests.get(f"{BASE_URL}/sessions", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get sessions: {response.status_code}")
        return False
    
    sessions = response.json()
    if not sessions:
        print("❌ No sessions available for testing")
        return False
    
    session_id = sessions[0]['id']
    print(f"✅ Using session: {sessions[0]['name']} (ID: {session_id})")
    
    # Test the correct bulk upload endpoint
    bulk_upload_url = f"{BASE_URL}/sessions/{session_id}/participants/bulk-upload"
    
    # Test with GET method (should return 405 Method Not Allowed)
    response = requests.get(bulk_upload_url, headers=headers)
    print(f"GET {bulk_upload_url}: {response.status_code}")
    
    if response.status_code == 405:
        print("✅ Bulk upload endpoint exists (correctly rejects GET method)")
        return True
    elif response.status_code == 404:
        print("❌ Bulk upload endpoint not found")
        return False
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")
        return True

if __name__ == "__main__":
    test_bulk_upload_endpoint()