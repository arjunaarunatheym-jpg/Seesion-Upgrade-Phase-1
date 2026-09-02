#!/usr/bin/env python3
"""
COMPREHENSIVE BACKEND API ENDPOINT TESTING - POST REFACTORING VALIDATION

This test suite validates ALL API endpoints across all portals after the backend refactoring.
It tests endpoints from the new modular structure against the old monolithic server.

Test Coverage:
- Authentication endpoints
- User management (all roles)
- Session management (CRUD operations)
- Report generation workflow
- Participant management
- Test results (pre/post tests)
- Attendance (clock in/out)
- Feedback submission
- Certificate generation
- Calendar & Past Training
- All portal-specific endpoints

Test Credentials:
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
- Trainer: vijay@mddrc.com.my / mddrc1
- Participant: 566589 (IC number) / mddrc1
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

# Configuration
BASE_URL = "https://training-finance-hub-1.preview.emergentagent.com/api"

# Test credentials from review request
TEST_CREDENTIALS = {
    "admin": {"email": "arjuna@mddrc.com.my", "password": "Dana102229"},
    "coordinator": {"email": "malek@mddrc.com.my", "password": "mddrc1"},
    "trainer": {"email": "vijay@mddrc.com.my", "password": "mddrc1"},
    "participant": {"email": "566589", "password": "mddrc1"}  # IC number as email
}

class ComprehensiveAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.tokens = {}
        self.test_data = {}
        self.failed_endpoints = []
        self.passed_endpoints = []
        self.missing_endpoints = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_user(self, role: str) -> bool:
        """Login as specific role and store token"""
        self.log(f"Logging in as {role}...")
        
        creds = TEST_CREDENTIALS.get(role)
        if not creds:
            self.log(f"❌ No credentials found for role: {role}", "ERROR")
            return False
            
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=creds)
            
            if response.status_code == 200:
                data = response.json()
                self.tokens[role] = data['access_token']
                self.log(f"✅ {role.title()} login successful: {data['user']['full_name']}")
                return True
            else:
                self.log(f"❌ {role.title()} login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ {role.title()} login error: {str(e)}", "ERROR")
            return False
    
    def test_endpoint(self, method: str, endpoint: str, role: str, data: dict = None, 
                     expected_status: int = 200, description: str = "") -> bool:
        """Test a single endpoint"""
        if role not in self.tokens:
            self.log(f"❌ No token for role {role}", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.tokens[role]}'}
        url = f"{BASE_URL}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                self.log(f"❌ Unsupported method: {method}", "ERROR")
                return False
                
            endpoint_desc = f"{method.upper()} {endpoint}"
            if description:
                endpoint_desc += f" ({description})"
                
            if response.status_code == expected_status:
                self.log(f"✅ {endpoint_desc} - Status: {response.status_code}")
                self.passed_endpoints.append({
                    "endpoint": f"{method.upper()} {endpoint}",
                    "role": role,
                    "status": response.status_code,
                    "description": description
                })
                return True
            else:
                self.log(f"❌ {endpoint_desc} - Expected: {expected_status}, Got: {response.status_code}", "ERROR")
                self.log(f"   Response: {response.text[:200]}...", "ERROR")
                self.failed_endpoints.append({
                    "endpoint": f"{method.upper()} {endpoint}",
                    "role": role,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "error": response.text[:500],
                    "description": description
                })
                return False
                
        except Exception as e:
            self.log(f"❌ {method.upper()} {endpoint} error: {str(e)}", "ERROR")
            self.failed_endpoints.append({
                "endpoint": f"{method.upper()} {endpoint}",
                "role": role,
                "error": str(e),
                "description": description
            })
            return False
    
    def setup_test_data(self):
        """Create test data for comprehensive testing"""
        self.log("Setting up test data...")
        
        # Create test program
        program_data = {
            "name": "Comprehensive Test Program",
            "description": "Program for comprehensive API testing",
            "pass_percentage": 75.0
        }
        
        if self.test_endpoint("POST", "/programs", "admin", program_data, 200, "Create test program"):
            # Store program ID for later use
            response = self.session.post(f"{BASE_URL}/programs", 
                                       json=program_data, 
                                       headers={'Authorization': f'Bearer {self.tokens["admin"]}'})
            if response.status_code == 200:
                self.test_data['program_id'] = response.json()['id']
        
        # Create test company
        company_data = {
            "name": "Comprehensive Test Company"
        }
        
        if self.test_endpoint("POST", "/companies", "admin", company_data, 200, "Create test company"):
            response = self.session.post(f"{BASE_URL}/companies", 
                                       json=company_data, 
                                       headers={'Authorization': f'Bearer {self.tokens["admin"]}'})
            if response.status_code == 200:
                self.test_data['company_id'] = response.json()['id']
    
    def test_authentication_endpoints(self):
        """Test all authentication endpoints"""
        self.log("🔐 Testing Authentication Endpoints...")
        
        # Test login endpoints (already tested in login_user)
        self.log("✅ Login endpoints already validated during setup")
        
        # Test /auth/me endpoint
        for role in ["admin", "coordinator", "trainer", "participant"]:
            if role in self.tokens:
                self.test_endpoint("GET", "/auth/me", role, None, 200, f"Get current user info as {role}")
        
        # Test forgot password
        forgot_data = {"email": "test@example.com"}
        self.test_endpoint("POST", "/auth/forgot-password", "admin", forgot_data, 200, "Forgot password")
        
        # Test reset password
        reset_data = {"email": "test@example.com", "new_password": "newpass123"}
        self.test_endpoint("POST", "/auth/reset-password", "admin", reset_data, 404, "Reset password (user not found)")
    
    def test_user_management_endpoints(self):
        """Test user management endpoints"""
        self.log("👥 Testing User Management Endpoints...")
        
        # Test GET /users
        self.test_endpoint("GET", "/users", "admin", None, 200, "Get all users as admin")
        self.test_endpoint("GET", "/users?role=participant", "admin", None, 200, "Get participants as admin")
        self.test_endpoint("GET", "/users", "coordinator", None, 200, "Get users as coordinator")
        
        # Test user creation via registration
        new_user_data = {
            "email": f"testuser_{uuid.uuid4().hex[:8]}@test.com",
            "password": "testpass123",
            "full_name": "Test User Comprehensive",
            "id_number": f"TEST{uuid.uuid4().hex[:6].upper()}",
            "role": "participant",
            "location": "Test Location"
        }
        
        if self.test_endpoint("POST", "/auth/register", "admin", new_user_data, 200, "Create new user"):
            # Get the created user ID for further testing
            response = self.session.post(f"{BASE_URL}/auth/register", 
                                       json=new_user_data, 
                                       headers={'Authorization': f'Bearer {self.tokens["admin"]}'})
            if response.status_code == 200:
                self.test_data['test_user_id'] = response.json()['id']
        
        # Test user update and delete if we have a test user
        if 'test_user_id' in self.test_data:
            user_id = self.test_data['test_user_id']
            
            # Test GET specific user
            self.test_endpoint("GET", f"/users/{user_id}", "admin", None, 200, "Get specific user")
            
            # Test user update
            update_data = {"location": "Updated Location"}
            self.test_endpoint("PUT", f"/users/{user_id}", "admin", update_data, 200, "Update user")
            
            # Test user delete
            self.test_endpoint("DELETE", f"/users/{user_id}", "admin", None, 200, "Delete user")
    
    def test_session_management_endpoints(self):
        """Test session management endpoints"""
        self.log("📅 Testing Session Management Endpoints...")
        
        # Test GET sessions for different roles
        self.test_endpoint("GET", "/sessions", "admin", None, 200, "Get sessions as admin")
        self.test_endpoint("GET", "/sessions", "coordinator", None, 200, "Get sessions as coordinator")
        self.test_endpoint("GET", "/sessions", "trainer", None, 200, "Get sessions as trainer")
        self.test_endpoint("GET", "/sessions", "participant", None, 200, "Get sessions as participant")
        
        # Test calendar endpoint
        self.test_endpoint("GET", "/sessions/calendar", "admin", None, 200, "Get calendar as admin")
        self.test_endpoint("GET", "/sessions/calendar", "coordinator", None, 200, "Get calendar as coordinator")
        self.test_endpoint("GET", "/sessions/calendar", "trainer", None, 200, "Get calendar as trainer")
        self.test_endpoint("GET", "/sessions/calendar", "participant", None, 403, "Get calendar as participant (should fail)")
        
        # Test past training endpoint
        self.test_endpoint("GET", "/sessions/past-training", "admin", None, 200, "Get past training as admin")
        self.test_endpoint("GET", "/sessions/past-training", "coordinator", None, 200, "Get past training as coordinator")
        self.test_endpoint("GET", "/sessions/past-training", "trainer", None, 200, "Get past training as trainer")
        
        # Create a test session if we have required data
        if 'program_id' in self.test_data and 'company_id' in self.test_data:
            session_data = {
                "name": "Comprehensive Test Session",
                "program_id": self.test_data['program_id'],
                "company_id": self.test_data['company_id'],
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
            
            if self.test_endpoint("POST", "/sessions", "admin", session_data, 200, "Create session"):
                # Get session ID for further testing
                response = self.session.post(f"{BASE_URL}/sessions", 
                                           json=session_data, 
                                           headers={'Authorization': f'Bearer {self.tokens["admin"]}'})
                if response.status_code == 200:
                    self.test_data['session_id'] = response.json()['session_id']
        
        # Test session-specific endpoints if we have a session
        if 'session_id' in self.test_data:
            session_id = self.test_data['session_id']
            
            # Test GET specific session
            self.test_endpoint("GET", f"/sessions/{session_id}", "admin", None, 200, "Get specific session")
            
            # Test session participants
            self.test_endpoint("GET", f"/sessions/{session_id}/participants", "admin", None, 200, "Get session participants")
            
            # Test session status
            self.test_endpoint("GET", f"/sessions/{session_id}/status", "admin", None, 200, "Get session status")
            
            # Test session results summary
            self.test_endpoint("GET", f"/sessions/{session_id}/results-summary", "admin", None, 200, "Get session results summary")
            
            # Test release endpoints
            self.test_endpoint("POST", f"/sessions/{session_id}/release-pre-test", "admin", None, 200, "Release pre-test")
            self.test_endpoint("POST", f"/sessions/{session_id}/release-post-test", "admin", None, 200, "Release post-test")
            self.test_endpoint("POST", f"/sessions/{session_id}/release-feedback", "admin", None, 200, "Release feedback")
            self.test_endpoint("POST", f"/sessions/{session_id}/release-certificate", "admin", None, 200, "Release certificate")
            
            # Test mark completed
            self.test_endpoint("POST", f"/sessions/{session_id}/mark-completed", "admin", None, 200, "Mark session completed")
            
            # Test session update
            update_data = {"location": "Updated Test Location"}
            self.test_endpoint("PUT", f"/sessions/{session_id}", "admin", update_data, 200, "Update session")
            
            # Test session delete (should be last)
            self.test_endpoint("DELETE", f"/sessions/{session_id}", "admin", None, 200, "Delete session")
    
    def test_report_endpoints(self):
        """Test training report endpoints"""
        self.log("📊 Testing Report Endpoints...")
        
        # Test get reports
        self.test_endpoint("GET", "/training-reports/coordinator", "coordinator", None, 200, "Get coordinator reports")
        self.test_endpoint("GET", "/training-reports/admin/all", "admin", None, 200, "Get all reports as admin")
        
        # Test report generation if we have a session
        if 'session_id' in self.test_data:
            session_id = self.test_data['session_id']
            
            # Test generate report
            report_data = {"session_id": session_id}
            self.test_endpoint("POST", "/training-reports/generate", "coordinator", report_data, 200, "Generate report")
            
            # Test get session report
            self.test_endpoint("GET", f"/training-reports/session/{session_id}", "coordinator", None, 200, "Get session report")
            
            # Test DOCX generation (critical workflow)
            self.test_endpoint("POST", f"/training-reports/{session_id}/generate-docx", "coordinator", None, 200, "Generate DOCX report")
            
            # Test DOCX download
            self.test_endpoint("GET", f"/training-reports/{session_id}/download-docx", "coordinator", None, 200, "Download DOCX report")
    
    def test_test_management_endpoints(self):
        """Test test management endpoints"""
        self.log("📝 Testing Test Management Endpoints...")
        
        if 'program_id' not in self.test_data:
            self.log("⚠️  Skipping test management - no program ID available", "WARNING")
            return
        
        program_id = self.test_data['program_id']
        
        # Test create pre-test
        pre_test_data = {
            "program_id": program_id,
            "test_type": "pre",
            "questions": [
                {
                    "question": "What is defensive driving?",
                    "options": ["Aggressive driving", "Safe driving", "Fast driving", "Slow driving"],
                    "correct_answer": 1
                }
            ]
        }
        
        if self.test_endpoint("POST", "/tests", "admin", pre_test_data, 200, "Create pre-test"):
            # Get test ID for further testing
            response = self.session.post(f"{BASE_URL}/tests", 
                                       json=pre_test_data, 
                                       headers={'Authorization': f'Bearer {self.tokens["admin"]}'})
            if response.status_code == 200:
                self.test_data['test_id'] = response.json()['id']
        
        # Test get tests by program
        self.test_endpoint("GET", f"/tests/program/{program_id}", "admin", None, 200, "Get tests by program")
        
        # Test delete test if we have one
        if 'test_id' in self.test_data:
            test_id = self.test_data['test_id']
            self.test_endpoint("DELETE", f"/tests/{test_id}", "admin", None, 200, "Delete test")
    
    def test_attendance_endpoints(self):
        """Test attendance endpoints"""
        self.log("⏰ Testing Attendance Endpoints...")
        
        if 'session_id' not in self.test_data:
            self.log("⚠️  Skipping attendance tests - no session ID available", "WARNING")
            return
        
        session_id = self.test_data['session_id']
        
        # Test clock-in
        clock_in_data = {"session_id": session_id}
        self.test_endpoint("POST", "/attendance/clock-in", "participant", clock_in_data, 200, "Clock in")
        
        # Test clock-out
        clock_out_data = {"session_id": session_id}
        self.test_endpoint("POST", "/attendance/clock-out", "participant", clock_out_data, 200, "Clock out")
        
        # Test get session attendance
        self.test_endpoint("GET", f"/attendance/session/{session_id}", "coordinator", None, 200, "Get session attendance")
    
    def test_feedback_endpoints(self):
        """Test feedback endpoints"""
        self.log("💬 Testing Feedback Endpoints...")
        
        # Test get feedback templates
        self.test_endpoint("GET", "/feedback-templates", "admin", None, 200, "Get feedback templates")
        
        # Test create feedback template
        template_data = {
            "name": "Test Feedback Template",
            "questions": [
                {"question": "How was the training?", "type": "rating"},
                {"question": "Any suggestions?", "type": "text"}
            ]
        }
        self.test_endpoint("POST", "/feedback-templates", "admin", template_data, 200, "Create feedback template")
        
        if 'session_id' in self.test_data and 'program_id' in self.test_data:
            session_id = self.test_data['session_id']
            program_id = self.test_data['program_id']
            
            # Test submit feedback
            feedback_data = {
                "session_id": session_id,
                "program_id": program_id,
                "responses": [
                    {"question": "Overall Training Experience", "answer": 5},
                    {"question": "Suggestions", "answer": "Great training!"}
                ]
            }
            self.test_endpoint("POST", "/feedback/submit", "participant", feedback_data, 200, "Submit feedback")
            
            # Test get session feedback
            self.test_endpoint("GET", f"/feedback/session/{session_id}", "coordinator", None, 200, "Get session feedback")
    
    def test_certificate_endpoints(self):
        """Test certificate endpoints"""
        self.log("🏆 Testing Certificate Endpoints...")
        
        # Test get participant certificates
        self.test_endpoint("GET", "/certificates/my-certificates", "participant", None, 200, "Get my certificates")
        
        if 'session_id' in self.test_data:
            session_id = self.test_data['session_id']
            
            # Get participant ID for certificate generation
            if "participant" in self.tokens:
                response = self.session.get(f"{BASE_URL}/auth/me", 
                                          headers={'Authorization': f'Bearer {self.tokens["participant"]}'})
                if response.status_code == 200:
                    participant_id = response.json()['id']
                    
                    # Test certificate generation
                    self.test_endpoint("POST", f"/certificates/generate/{session_id}/{participant_id}", 
                                     "admin", None, 200, "Generate certificate")
    
    def test_checklist_endpoints(self):
        """Test checklist endpoints"""
        self.log("✅ Testing Checklist Endpoints...")
        
        # Test get checklist templates
        self.test_endpoint("GET", "/checklist-templates", "admin", None, 200, "Get checklist templates")
        
        # Test create checklist template
        checklist_data = {
            "name": "Test Vehicle Checklist",
            "items": ["Tires", "Brakes", "Lights", "Mirrors"]
        }
        self.test_endpoint("POST", "/checklist-templates", "admin", checklist_data, 200, "Create checklist template")
    
    def test_company_program_endpoints(self):
        """Test company and program endpoints"""
        self.log("🏢 Testing Company & Program Endpoints...")
        
        # Test get companies
        self.test_endpoint("GET", "/companies", "admin", None, 200, "Get companies")
        
        # Test get programs
        self.test_endpoint("GET", "/programs", "admin", None, 200, "Get programs")
        
        # Company and program creation already tested in setup_test_data
    
    def test_participant_access_endpoints(self):
        """Test participant access endpoints"""
        self.log("🔑 Testing Participant Access Endpoints...")
        
        if 'session_id' in self.test_data:
            session_id = self.test_data['session_id']
            
            # Get participant ID
            if "participant" in self.tokens:
                response = self.session.get(f"{BASE_URL}/auth/me", 
                                          headers={'Authorization': f'Bearer {self.tokens["participant"]}'})
                if response.status_code == 200:
                    participant_id = response.json()['id']
                    
                    # Test update participant access
                    access_data = {
                        "participant_id": participant_id,
                        "session_id": session_id,
                        "can_access_pre_test": True,
                        "can_access_post_test": True,
                        "can_access_feedback": True
                    }
                    self.test_endpoint("POST", "/participant-access/update", "admin", access_data, 200, "Update participant access")
    
    def run_comprehensive_test(self):
        """Run all comprehensive tests"""
        self.log("🚀 Starting Comprehensive Backend API Testing...")
        
        # Step 1: Login all users
        self.log("Step 1: Authenticating all user roles...")
        for role in TEST_CREDENTIALS.keys():
            if not self.login_user(role):
                self.log(f"⚠️  Failed to login {role}, some tests will be skipped", "WARNING")
        
        # Step 2: Setup test data
        if "admin" in self.tokens:
            self.setup_test_data()
        
        # Step 3: Run all endpoint tests
        self.test_authentication_endpoints()
        self.test_user_management_endpoints()
        self.test_company_program_endpoints()
        self.test_session_management_endpoints()
        self.test_report_endpoints()
        self.test_test_management_endpoints()
        self.test_attendance_endpoints()
        self.test_feedback_endpoints()
        self.test_certificate_endpoints()
        self.test_checklist_endpoints()
        self.test_participant_access_endpoints()
        
        # Step 4: Generate comprehensive report
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate final comprehensive test report"""
        self.log("📋 Generating Final Test Report...")
        
        total_tests = len(self.passed_endpoints) + len(self.failed_endpoints)
        pass_rate = (len(self.passed_endpoints) / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*80)
        print("COMPREHENSIVE BACKEND API TEST REPORT")
        print("="*80)
        print(f"Total Endpoints Tested: {total_tests}")
        print(f"Passed: {len(self.passed_endpoints)} ({pass_rate:.1f}%)")
        print(f"Failed: {len(self.failed_endpoints)}")
        print(f"Missing: {len(self.missing_endpoints)}")
        
        if self.failed_endpoints:
            print("\n❌ FAILED ENDPOINTS:")
            print("-" * 50)
            for failure in self.failed_endpoints:
                print(f"• {failure['endpoint']} ({failure['role']})")
                if 'expected' in failure and 'actual' in failure:
                    print(f"  Expected: {failure['expected']}, Got: {failure['actual']}")
                if 'error' in failure:
                    print(f"  Error: {failure['error'][:200]}...")
                if failure.get('description'):
                    print(f"  Description: {failure['description']}")
                print()
        
        if self.passed_endpoints:
            print("\n✅ PASSED ENDPOINTS:")
            print("-" * 50)
            for success in self.passed_endpoints:
                desc = f" - {success['description']}" if success.get('description') else ""
                print(f"• {success['endpoint']} ({success['role']}){desc}")
        
        print("\n" + "="*80)
        
        # Critical workflow status
        critical_workflows = [
            "POST /training-reports/",
            "POST /sessions",
            "DELETE /sessions/",
            "POST /tests",
            "POST /attendance/clock-in",
            "POST /feedback/submit",
            "POST /certificates/generate"
        ]
        
        print("CRITICAL WORKFLOW STATUS:")
        print("-" * 30)
        for workflow in critical_workflows:
            status = "✅ WORKING" if any(workflow in ep['endpoint'] for ep in self.passed_endpoints) else "❌ FAILING"
            print(f"{workflow}: {status}")
        
        print("\n" + "="*80)

def main():
    """Main test execution"""
    tester = ComprehensiveAPITester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()