#!/usr/bin/env python3
"""
API Issue Diagnosis Test
Identifies specific API endpoint issues found during E2E testing
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://tab-extraction.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

class APIDiagnosisRunner:
    def __init__(self):
        self.admin_token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_admin(self):
        """Login as admin"""
        self.log("Logging in as admin...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data['access_token']
                self.log(f"✅ Admin login successful")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin login error: {str(e)}", "ERROR")
            return False

    def test_session_creation_issue(self):
        """Test session creation to identify the 'id' error"""
        self.log("=== TESTING SESSION CREATION ISSUE ===")
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # First create a company and program
        company_data = {"name": "Test Company Diagnosis"}
        try:
            response = self.session.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
            if response.status_code == 200:
                company_id = response.json()['id']
                self.log(f"✅ Company created: {company_id}")
            else:
                self.log(f"❌ Company creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Company creation error: {str(e)}", "ERROR")
            return False
        
        program_data = {
            "name": "Test Program Diagnosis",
            "description": "Test program",
            "pass_percentage": 70.0
        }
        try:
            response = self.session.post(f"{BASE_URL}/programs", json=program_data, headers=headers)
            if response.status_code == 200:
                program_id = response.json()['id']
                self.log(f"✅ Program created: {program_id}")
            else:
                self.log(f"❌ Program creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Program creation error: {str(e)}", "ERROR")
            return False
        
        # Now test session creation
        session_data = {
            "name": "Test Session Diagnosis",
            "program_id": program_id,
            "company_id": company_id,
            "location": "Test Location",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "coordinator_ids": [],
            "trainer_ids": [],
            "participant_ids": [],
            "participants": [],
            "supervisors": [],
            "supervisor_ids": [],
            "trainer_assignments": []
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            self.log(f"Session creation response: {response.status_code}")
            self.log(f"Response text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Session created successfully: {result}")
                return result.get('session_id')
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False

    def test_test_creation_issue(self):
        """Test test creation to identify missing 'title' field"""
        self.log("=== TESTING TEST CREATION ISSUE ===")
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Get a program ID first
        try:
            response = self.session.get(f"{BASE_URL}/programs", headers=headers)
            if response.status_code == 200:
                programs = response.json()
                if programs:
                    program_id = programs[0]['id']
                    self.log(f"✅ Using program ID: {program_id}")
                else:
                    self.log("❌ No programs found", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get programs: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Get programs error: {str(e)}", "ERROR")
            return False
        
        # Test without title (current failing case)
        test_data_without_title = {
            "program_id": program_id,
            "test_type": "pre",
            "questions": [
                {
                    "question": "Test question?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/tests", json=test_data_without_title, headers=headers)
            self.log(f"Test creation (no title) response: {response.status_code}")
            self.log(f"Response text: {response.text}")
            
            if response.status_code != 200:
                self.log(f"❌ Expected failure - missing title field", "ERROR")
        except Exception as e:
            self.log(f"❌ Test creation error: {str(e)}", "ERROR")
        
        # Test with title (should work)
        test_data_with_title = {
            "program_id": program_id,
            "title": "Diagnosis Pre-Test",
            "test_type": "pre",
            "questions": [
                {
                    "question": "Test question?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/tests", json=test_data_with_title, headers=headers)
            self.log(f"Test creation (with title) response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Test created successfully with title: {result['id']}")
                return result['id']
            else:
                self.log(f"❌ Test creation with title failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Test creation with title error: {str(e)}", "ERROR")
            return False

    def test_participant_access_issue(self):
        """Test participant access update to identify query parameter issue"""
        self.log("=== TESTING PARTICIPANT ACCESS ISSUE ===")
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test current failing approach (body parameters)
        access_data = {
            "participant_id": "test-participant-id",
            "session_id": "test-session-id",
            "can_access_pre_test": True
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/participant-access/update", json=access_data, headers=headers)
            self.log(f"Participant access (body params) response: {response.status_code}")
            self.log(f"Response text: {response.text}")
            
            if response.status_code != 200:
                self.log(f"❌ Body parameters approach failed", "ERROR")
        except Exception as e:
            self.log(f"❌ Participant access body params error: {str(e)}", "ERROR")
        
        # Test query parameters approach
        try:
            params = {
                "participant_id": "test-participant-id",
                "session_id": "test-session-id"
            }
            access_body = {"can_access_pre_test": True}
            
            response = self.session.post(f"{BASE_URL}/participant-access/update", params=params, json=access_body, headers=headers)
            self.log(f"Participant access (query params) response: {response.status_code}")
            self.log(f"Response text: {response.text}")
            
            if response.status_code == 200:
                self.log(f"✅ Query parameters approach works")
                return True
            else:
                self.log(f"❌ Query parameters approach failed", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Participant access query params error: {str(e)}", "ERROR")
            return False

    def test_available_tests_endpoint(self):
        """Test the available tests endpoint that returns 404"""
        self.log("=== TESTING AVAILABLE TESTS ENDPOINT ===")
        
        # Create a participant first
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        participant_data = {
            "email": "diagnosis.participant@test.com",
            "password": "test123",
            "full_name": "Diagnosis Test Participant",
            "id_number": "DIAG001",
            "role": "participant",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=participant_data, headers=headers)
            if response.status_code == 200:
                participant_id = response.json()['id']
                self.log(f"✅ Participant created: {participant_id}")
            elif response.status_code == 400 and "already exists" in response.text:
                # Login to get participant token
                login_data = {"email": "diagnosis.participant@test.com", "password": "test123"}
                login_response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                if login_response.status_code == 200:
                    participant_token = login_response.json()['access_token']
                    participant_id = login_response.json()['user']['id']
                    self.log(f"✅ Using existing participant: {participant_id}")
                else:
                    self.log("❌ Failed to login existing participant", "ERROR")
                    return False
            else:
                self.log(f"❌ Participant creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Participant creation error: {str(e)}", "ERROR")
            return False
        
        # Login as participant
        login_data = {"email": "diagnosis.participant@test.com", "password": "test123"}
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                participant_token = response.json()['access_token']
                self.log(f"✅ Participant login successful")
            else:
                self.log(f"❌ Participant login failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Participant login error: {str(e)}", "ERROR")
            return False
        
        # Test available tests endpoint with fake session ID
        p_headers = {'Authorization': f'Bearer {participant_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions/fake-session-id/tests/available", headers=p_headers)
            self.log(f"Available tests response: {response.status_code}")
            self.log(f"Response text: {response.text}")
            
            if response.status_code == 404:
                self.log(f"✅ Expected 404 for non-existent session")
                return True
            else:
                self.log(f"❌ Unexpected response: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Available tests error: {str(e)}", "ERROR")
            return False

    def run_diagnosis(self):
        """Run all diagnostic tests"""
        self.log("🔍 STARTING API ISSUE DIAGNOSIS")
        self.log("=" * 60)
        
        if not self.login_admin():
            return False
        
        # Test each issue
        issues = [
            ("Session Creation 'id' Error", self.test_session_creation_issue),
            ("Test Creation Missing 'title' Field", self.test_test_creation_issue),
            ("Participant Access Query Parameters", self.test_participant_access_issue),
            ("Available Tests 404 Error", self.test_available_tests_endpoint)
        ]
        
        results = {}
        
        for issue_name, test_func in issues:
            self.log(f"\n--- Testing: {issue_name} ---")
            try:
                result = test_func()
                results[issue_name] = result
            except Exception as e:
                self.log(f"❌ {issue_name} test failed with exception: {str(e)}", "ERROR")
                results[issue_name] = False
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("🏁 DIAGNOSIS RESULTS SUMMARY")
        self.log("=" * 60)
        
        for issue_name, result in results.items():
            status = "✅ RESOLVED" if result else "❌ ISSUE FOUND"
            self.log(f"{status}: {issue_name}")
        
        return results

def main():
    runner = APIDiagnosisRunner()
    runner.run_diagnosis()

if __name__ == "__main__":
    main()