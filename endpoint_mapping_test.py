#!/usr/bin/env python3
"""
Endpoint Mapping Test - Compare old server endpoints with new modular structure
This script identifies missing endpoints after refactoring
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://cert-designer-3.preview.emergentagent.com/api"
ADMIN_TOKEN = None

def login_admin():
    """Login as admin and get token"""
    global ADMIN_TOKEN
    login_data = {
        "email": "arjuna@mddrc.com.my",
        "password": "Dana102229"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        ADMIN_TOKEN = response.json()['access_token']
        print("✅ Admin login successful")
        return True
    else:
        print(f"❌ Admin login failed: {response.status_code}")
        return False

def test_endpoint(method, endpoint, expected_status=200, description=""):
    """Test a single endpoint"""
    if not ADMIN_TOKEN:
        print("❌ No admin token")
        return False
        
    headers = {'Authorization': f'Bearer {ADMIN_TOKEN}'}
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json={}, headers=headers)
        else:
            return False
            
        status = "✅ WORKING" if response.status_code == expected_status else f"❌ FAILING ({response.status_code})"
        print(f"{method.upper()} {endpoint}: {status} - {description}")
        
        if response.status_code != expected_status:
            print(f"   Error: {response.text[:200]}...")
            
        return response.status_code == expected_status
        
    except Exception as e:
        print(f"{method.upper()} {endpoint}: ❌ ERROR - {str(e)}")
        return False

def main():
    """Test critical endpoints that should exist"""
    print("🔍 ENDPOINT MAPPING TEST - IDENTIFYING MISSING ENDPOINTS")
    print("=" * 60)
    
    if not login_admin():
        return
    
    print("\n📊 TESTING REPORT ENDPOINTS:")
    test_endpoint("GET", "/training-reports/coordinator", 200, "Get coordinator reports")
    test_endpoint("GET", "/training-reports/admin/all", 200, "Get all reports (admin)")
    test_endpoint("POST", "/training-reports/generate", 400, "Generate report (missing data)")
    
    print("\n📝 TESTING TEST MANAGEMENT ENDPOINTS:")
    test_endpoint("POST", "/tests", 400, "Create test (missing data)")
    test_endpoint("GET", "/tests/program/test-id", 200, "Get tests by program")
    test_endpoint("DELETE", "/tests/test-id", 404, "Delete test (not found)")
    
    print("\n💬 TESTING FEEDBACK ENDPOINTS:")
    test_endpoint("GET", "/feedback-templates", 404, "Get feedback templates (old path)")
    test_endpoint("GET", "/feedback/templates", 404, "Get feedback templates (new path)")
    test_endpoint("GET", "/feedback/templates/program/test-id", 200, "Get feedback templates by program")
    test_endpoint("POST", "/feedback/templates", 400, "Create feedback template")
    test_endpoint("POST", "/feedback/submit", 400, "Submit feedback")
    
    print("\n✅ TESTING CHECKLIST ENDPOINTS:")
    test_endpoint("GET", "/checklist-templates", 404, "Get checklist templates (old path)")
    test_endpoint("GET", "/checklists/templates", 200, "Get checklist templates (new path)")
    test_endpoint("GET", "/checklists/templates/program/test-id", 200, "Get checklist templates by program")
    test_endpoint("POST", "/checklists/templates", 400, "Create checklist template")
    test_endpoint("POST", "/checklists/submit", 400, "Submit checklist")
    
    print("\n⏰ TESTING ATTENDANCE ENDPOINTS:")
    test_endpoint("POST", "/attendance/clock-in", 400, "Clock in")
    test_endpoint("POST", "/attendance/clock-out", 400, "Clock out")
    test_endpoint("GET", "/attendance/session/test-id", 200, "Get session attendance")
    
    print("\n🏆 TESTING CERTIFICATE ENDPOINTS:")
    test_endpoint("GET", "/certificates/my-certificates", 200, "Get my certificates")
    test_endpoint("POST", "/certificates/generate/session-id/participant-id", 404, "Generate certificate")
    
    print("\n🔑 TESTING PARTICIPANT ACCESS ENDPOINTS:")
    test_endpoint("POST", "/participant-access/update", 400, "Update participant access")
    
    print("\n📅 TESTING SESSION ENDPOINTS:")
    test_endpoint("GET", "/sessions", 200, "Get sessions")
    test_endpoint("POST", "/sessions", 400, "Create session")
    test_endpoint("GET", "/sessions/calendar", 200, "Get calendar")
    test_endpoint("GET", "/sessions/past-training", 200, "Get past training")
    test_endpoint("DELETE", "/sessions/test-id", 404, "Delete session")
    
    print("\n👥 TESTING USER ENDPOINTS:")
    test_endpoint("GET", "/users", 200, "Get users")
    test_endpoint("POST", "/auth/register", 400, "Register user")
    test_endpoint("DELETE", "/users/test-id", 404, "Delete user")
    
    print("\n🏢 TESTING COMPANY/PROGRAM ENDPOINTS:")
    test_endpoint("GET", "/companies", 200, "Get companies")
    test_endpoint("GET", "/programs", 200, "Get programs")
    test_endpoint("POST", "/companies", 400, "Create company")
    test_endpoint("POST", "/programs", 400, "Create program")
    
    print("\n" + "=" * 60)
    print("ENDPOINT MAPPING TEST COMPLETE")

if __name__ == "__main__":
    main()