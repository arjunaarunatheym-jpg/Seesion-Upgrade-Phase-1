#!/usr/bin/env python3
"""
CRITICAL ENDPOINT TESTING - Focus on failing endpoints from refactoring

This test focuses on the endpoints that are failing and provides detailed analysis
of what's broken and what needs to be fixed.
"""

import requests
import json
from datetime import datetime
import uuid

BASE_URL = "https://training-finance-hub-1.preview.emergentagent.com/api"

# Test credentials
CREDENTIALS = {
    "admin": {"email": "arjuna@mddrc.com.my", "password": "Dana102229"},
    "coordinator": {"email": "malek@mddrc.com.my", "password": "mddrc1"},
    "trainer": {"email": "vijay@mddrc.com.my", "password": "mddrc1"},
    "participant": {"email": "566589", "password": "mddrc1"}
}

class CriticalEndpointTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.tokens = {}
        self.test_data = {}
        self.critical_failures = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_all_users(self):
        """Login all user types"""
        self.log("🔐 Logging in all user types...")
        
        for role, creds in CREDENTIALS.items():
            try:
                response = self.session.post(f"{BASE_URL}/auth/login", json=creds)
                if response.status_code == 200:
                    data = response.json()
                    self.tokens[role] = data['access_token']
                    self.log(f"✅ {role.title()}: {data['user']['full_name']}")
                else:
                    self.log(f"❌ {role.title()} login failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ {role.title()} login error: {str(e)}", "ERROR")
    
    def test_critical_report_generation(self):
        """Test the critical report generation workflow"""
        self.log("📊 Testing CRITICAL Report Generation Workflow...")
        
        if "coordinator" not in self.tokens:
            self.log("❌ No coordinator token - skipping report tests", "ERROR")
            return
            
        headers = {'Authorization': f'Bearer {self.tokens["coordinator"]}'}
        
        # Test 1: Get coordinator reports (FAILING with 500)
        self.log("Testing GET /training-reports/coordinator...")
        try:
            response = self.session.get(f"{BASE_URL}/training-reports/coordinator", headers=headers)
            if response.status_code == 200:
                self.log("✅ Coordinator reports endpoint working")
            else:
                self.log(f"❌ CRITICAL FAILURE: GET /training-reports/coordinator returned {response.status_code}", "ERROR")
                self.log(f"   Error: {response.text[:300]}", "ERROR")
                self.critical_failures.append({
                    "endpoint": "GET /training-reports/coordinator",
                    "status": response.status_code,
                    "error": response.text[:500],
                    "impact": "Coordinators cannot view their reports"
                })
        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: /training-reports/coordinator - {str(e)}", "ERROR")
        
        # Test 2: Get all reports as admin (FAILING with 500)
        if "admin" in self.tokens:
            admin_headers = {'Authorization': f'Bearer {self.tokens["admin"]}'}
            self.log("Testing GET /training-reports/admin/all...")
            try:
                response = self.session.get(f"{BASE_URL}/training-reports/admin/all", headers=admin_headers)
                if response.status_code == 200:
                    self.log("✅ Admin reports endpoint working")
                else:
                    self.log(f"❌ CRITICAL FAILURE: GET /training-reports/admin/all returned {response.status_code}", "ERROR")
                    self.log(f"   Error: {response.text[:300]}", "ERROR")
                    self.critical_failures.append({
                        "endpoint": "GET /training-reports/admin/all",
                        "status": response.status_code,
                        "error": response.text[:500],
                        "impact": "Admins cannot view all reports"
                    })
            except Exception as e:
                self.log(f"❌ CRITICAL ERROR: /training-reports/admin/all - {str(e)}", "ERROR")
        
        # Test 3: DOCX Report Generation (CRITICAL WORKFLOW)
        self.log("Testing POST /training-reports/{session_id}/generate-docx...")
        
        # First get a session ID
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            if response.status_code == 200:
                sessions = response.json()
                if sessions:
                    session_id = sessions[0]['id']
                    self.log(f"Using session ID: {session_id}")
                    
                    # Test DOCX generation
                    docx_response = self.session.post(f"{BASE_URL}/training-reports/{session_id}/generate-docx", headers=headers)
                    if docx_response.status_code == 200:
                        self.log("✅ DOCX report generation working")
                    else:
                        self.log(f"❌ CRITICAL FAILURE: DOCX generation returned {docx_response.status_code}", "ERROR")
                        self.log(f"   Error: {docx_response.text[:300]}", "ERROR")
                        self.critical_failures.append({
                            "endpoint": f"POST /training-reports/{session_id}/generate-docx",
                            "status": docx_response.status_code,
                            "error": docx_response.text[:500],
                            "impact": "Report generation workflow broken"
                        })
                else:
                    self.log("⚠️  No sessions available for testing", "WARNING")
            else:
                self.log(f"❌ Cannot get sessions: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: DOCX generation test - {str(e)}", "ERROR")
    
    def test_critical_test_management(self):
        """Test critical test management endpoints"""
        self.log("📝 Testing CRITICAL Test Management...")
        
        if "admin" not in self.tokens:
            self.log("❌ No admin token - skipping test management", "ERROR")
            return
            
        headers = {'Authorization': f'Bearer {self.tokens["admin"]}'}
        
        # Get a program ID first
        try:
            response = self.session.get(f"{BASE_URL}/programs", headers=headers)
            if response.status_code == 200:
                programs = response.json()
                if programs:
                    program_id = programs[0]['id']
                    self.log(f"Using program ID: {program_id}")
                    
                    # Test create test (CRITICAL WORKFLOW)
                    test_data = {
                        "program_id": program_id,
                        "title": "Critical Test Creation",
                        "questions": [
                            {
                                "question": "Test question?",
                                "options": ["A", "B", "C", "D"],
                                "correct_answer": 0
                            }
                        ]
                    }
                    
                    self.log("Testing POST /tests...")
                    create_response = self.session.post(f"{BASE_URL}/tests", json=test_data, headers=headers)
                    if create_response.status_code == 200:
                        self.log("✅ Test creation working")
                        test_id = create_response.json()['id']
                        
                        # Test delete test
                        self.log("Testing DELETE /tests/{test_id}...")
                        delete_response = self.session.delete(f"{BASE_URL}/tests/{test_id}", headers=headers)
                        if delete_response.status_code == 200:
                            self.log("✅ Test deletion working")
                        else:
                            self.log(f"❌ Test deletion failed: {delete_response.status_code}", "ERROR")
                    else:
                        self.log(f"❌ CRITICAL FAILURE: Test creation returned {create_response.status_code}", "ERROR")
                        self.log(f"   Error: {create_response.text[:300]}", "ERROR")
                        self.critical_failures.append({
                            "endpoint": "POST /tests",
                            "status": create_response.status_code,
                            "error": create_response.text[:500],
                            "impact": "Cannot create tests - test management broken"
                        })
                else:
                    self.log("⚠️  No programs available for testing", "WARNING")
            else:
                self.log(f"❌ Cannot get programs: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: Test management - {str(e)}", "ERROR")
    
    def test_critical_session_operations(self):
        """Test critical session operations"""
        self.log("📅 Testing CRITICAL Session Operations...")
        
        if "admin" not in self.tokens:
            self.log("❌ No admin token - skipping session tests", "ERROR")
            return
            
        headers = {'Authorization': f'Bearer {self.tokens["admin"]}'}
        
        # Get required IDs
        try:
            # Get program and company
            programs_response = self.session.get(f"{BASE_URL}/programs", headers=headers)
            companies_response = self.session.get(f"{BASE_URL}/companies", headers=headers)
            
            if programs_response.status_code == 200 and companies_response.status_code == 200:
                programs = programs_response.json()
                companies = companies_response.json()
                
                if programs and companies:
                    program_id = programs[0]['id']
                    company_id = companies[0]['id']
                    
                    # Test session creation
                    session_data = {
                        "name": "Critical Test Session",
                        "program_id": program_id,
                        "company_id": company_id,
                        "location": "Test Location",
                        "start_date": "2024-12-01",
                        "end_date": "2024-12-31",
                        "participant_ids": [],
                        "participants": [],
                        "supervisors": [],
                        "supervisor_ids": [],
                        "trainer_assignments": [],
                        "coordinator_id": None
                    }
                    
                    self.log("Testing POST /sessions...")
                    create_response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
                    if create_response.status_code == 200:
                        self.log("✅ Session creation working")
                        session_id = create_response.json()['session_id']
                        
                        # Test session deletion
                        self.log("Testing DELETE /sessions/{session_id}...")
                        delete_response = self.session.delete(f"{BASE_URL}/sessions/{session_id}", headers=headers)
                        if delete_response.status_code == 200:
                            self.log("✅ Session deletion working")
                        else:
                            self.log(f"❌ Session deletion failed: {delete_response.status_code}", "ERROR")
                            self.critical_failures.append({
                                "endpoint": f"DELETE /sessions/{session_id}",
                                "status": delete_response.status_code,
                                "error": delete_response.text[:500],
                                "impact": "Cannot delete sessions"
                            })
                    else:
                        self.log(f"❌ CRITICAL FAILURE: Session creation returned {create_response.status_code}", "ERROR")
                        self.log(f"   Error: {create_response.text[:300]}", "ERROR")
                        self.critical_failures.append({
                            "endpoint": "POST /sessions",
                            "status": create_response.status_code,
                            "error": create_response.text[:500],
                            "impact": "Cannot create sessions - session management broken"
                        })
                else:
                    self.log("⚠️  Missing programs or companies for testing", "WARNING")
            else:
                self.log("❌ Cannot get programs/companies for session test", "ERROR")
        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: Session operations - {str(e)}", "ERROR")
    
    def test_participant_workflows(self):
        """Test critical participant workflows"""
        self.log("👤 Testing CRITICAL Participant Workflows...")
        
        if "participant" not in self.tokens:
            self.log("❌ No participant token - skipping participant tests", "ERROR")
            return
            
        headers = {'Authorization': f'Bearer {self.tokens["participant"]}'}
        
        # Test 1: Get participant sessions
        self.log("Testing GET /sessions (as participant)...")
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Participant can access sessions ({len(sessions)} found)")
                
                if sessions:
                    session_id = sessions[0]['id']
                    
                    # Test available tests
                    self.log("Testing GET /sessions/{session_id}/tests/available...")
                    tests_response = self.session.get(f"{BASE_URL}/sessions/{session_id}/tests/available", headers=headers)
                    if tests_response.status_code == 200:
                        self.log("✅ Available tests endpoint working")
                    else:
                        self.log(f"❌ Available tests failed: {tests_response.status_code}", "ERROR")
                        self.critical_failures.append({
                            "endpoint": f"GET /sessions/{session_id}/tests/available",
                            "status": tests_response.status_code,
                            "error": tests_response.text[:500],
                            "impact": "Participants cannot see available tests"
                        })
                else:
                    self.log("⚠️  Participant has no sessions assigned", "WARNING")
            else:
                self.log(f"❌ Participant cannot access sessions: {response.status_code}", "ERROR")
                self.critical_failures.append({
                    "endpoint": "GET /sessions (participant)",
                    "status": response.status_code,
                    "error": response.text[:500],
                    "impact": "Participants cannot see their sessions"
                })
        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: Participant workflows - {str(e)}", "ERROR")
        
        # Test 2: Certificate access
        self.log("Testing GET /certificates/my-certificates...")
        try:
            response = self.session.get(f"{BASE_URL}/certificates/my-certificates", headers=headers)
            if response.status_code == 200:
                certificates = response.json()
                self.log(f"✅ Certificate access working ({len(certificates)} certificates)")
            else:
                self.log(f"❌ Certificate access failed: {response.status_code}", "ERROR")
                self.critical_failures.append({
                    "endpoint": "GET /certificates/my-certificates",
                    "status": response.status_code,
                    "error": response.text[:500],
                    "impact": "Participants cannot access their certificates"
                })
        except Exception as e:
            self.log(f"❌ CRITICAL ERROR: Certificate access - {str(e)}", "ERROR")
    
    def generate_critical_report(self):
        """Generate final critical issues report"""
        self.log("📋 Generating Critical Issues Report...")
        
        print("\n" + "="*80)
        print("🚨 CRITICAL BACKEND ENDPOINT FAILURES REPORT")
        print("="*80)
        
        if not self.critical_failures:
            print("✅ NO CRITICAL FAILURES DETECTED!")
            print("All tested endpoints are working correctly.")
        else:
            print(f"❌ {len(self.critical_failures)} CRITICAL FAILURES DETECTED:")
            print("-" * 50)
            
            for i, failure in enumerate(self.critical_failures, 1):
                print(f"\n{i}. {failure['endpoint']}")
                print(f"   Status: {failure['status']}")
                print(f"   Impact: {failure['impact']}")
                print(f"   Error: {failure['error'][:200]}...")
        
        print("\n" + "="*80)
        print("PRIORITY FIXES NEEDED:")
        print("-" * 30)
        
        priority_fixes = [
            "1. Fix TrainingReport model validation errors (500 errors)",
            "2. Verify all route registrations are correct",
            "3. Test report generation workflow end-to-end",
            "4. Verify participant session assignment logic",
            "5. Test all CRUD operations for critical entities"
        ]
        
        for fix in priority_fixes:
            print(fix)
        
        print("\n" + "="*80)
    
    def run_critical_tests(self):
        """Run all critical endpoint tests"""
        self.log("🚨 STARTING CRITICAL ENDPOINT TESTING...")
        
        self.login_all_users()
        self.test_critical_report_generation()
        self.test_critical_test_management()
        self.test_critical_session_operations()
        self.test_participant_workflows()
        self.generate_critical_report()

def main():
    tester = CriticalEndpointTester()
    tester.run_critical_tests()

if __name__ == "__main__":
    main()