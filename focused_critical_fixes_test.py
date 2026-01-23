#!/usr/bin/env python3
"""
Focused Critical Backend Fixes Verification Test
Tests the 6 critical backend fixes with existing data to avoid setup issues
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://trainingapp-update.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"

class FocusedCriticalFixesTestRunner:
    def __init__(self):
        self.admin_token = None
        self.coordinator_token = None
        self.participant_token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_admin(self):
        """Login as admin and get authentication token"""
        self.log("🔐 Attempting admin login...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data['access_token']
                self.log(f"✅ Admin login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin login error: {str(e)}", "ERROR")
            return False
    
    def login_participant(self):
        """Login as existing participant"""
        self.log("🔐 Attempting participant login...")
        
        # Use existing participant from test_result.md
        login_data = {
            "email": "566589",  # IC number as email
            "password": "mddrc1"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.participant_token = data['access_token']
                self.participant_id = data['user']['id']
                self.log(f"✅ Participant login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"❌ Participant login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Participant login error: {str(e)}", "ERROR")
            return False

    def get_existing_data(self):
        """Get existing program and session data"""
        self.log("🔍 Getting existing data...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Get first program
        try:
            response = self.session.get(f"{BASE_URL}/programs", headers=headers)
            if response.status_code == 200:
                programs = response.json()
                if programs:
                    self.test_program_id = programs[0]['id']
                    self.log(f"✅ Using existing program. ID: {self.test_program_id}")
                else:
                    self.log("❌ No programs found", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get programs: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error getting programs: {str(e)}", "ERROR")
            return False
        
        # Get first session
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            if response.status_code == 200:
                sessions = response.json()
                if sessions:
                    self.test_session_id = sessions[0]['id']
                    self.log(f"✅ Using existing session. ID: {self.test_session_id}")
                else:
                    self.log("❌ No sessions found", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error getting sessions: {str(e)}", "ERROR")
            return False
        
        return True

    # ============ CRITICAL FIX 1: TrainingReport Model - coordinator_id Optional ============
    
    def test_training_reports_admin_all(self):
        """Test GET /api/training-reports/admin/all (was 500, should be 200 now)"""
        self.log("🧪 Testing FIX 1: GET /api/training-reports/admin/all...")
        
        if not self.admin_token:
            self.log("❌ Missing admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/training-reports/admin/all", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ FIX 1 SUCCESS: Training reports retrieved successfully. Count: {len(data)}")
                return True
            else:
                self.log(f"❌ FIX 1 FAILED: Training reports failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ FIX 1 ERROR: Training reports error: {str(e)}", "ERROR")
            return False

    # ============ CRITICAL FIX 2: Test Models - correct_answer as int ============
    
    def test_create_test_with_int_correct_answer(self):
        """Test POST /api/tests with correct_answer as int (was 422 validation error, should be 200 now)"""
        self.log("🧪 Testing FIX 2: POST /api/tests with correct_answer as int...")
        
        if not self.admin_token or not self.test_program_id:
            self.log("❌ Missing admin token or program ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        test_data = {
            "program_id": self.test_program_id,
            "title": "Critical Fixes Test - Int Correct Answer",
            "questions": [
                {
                    "question": "What is the recommended following distance in good weather conditions?",
                    "options": ["1 second", "2 seconds", "3 seconds", "4 seconds"],
                    "correct_answer": 2  # INT, not string
                },
                {
                    "question": "When should you check your mirrors while driving?",
                    "options": ["Only when changing lanes", "Every 5-8 seconds", "Only when parking", "Once per trip"],
                    "correct_answer": 1  # INT, not string
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/tests", json=test_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.created_test_id = data['id']
                self.log(f"✅ FIX 2 SUCCESS: Test created with int correct_answer. ID: {self.created_test_id}")
                
                # Verify correct_answer is stored as int
                for i, question in enumerate(data['questions']):
                    correct_answer = question.get('correct_answer')
                    if isinstance(correct_answer, int):
                        self.log(f"   ✅ Question {i+1} correct_answer is int: {correct_answer}")
                    else:
                        self.log(f"   ❌ Question {i+1} correct_answer is not int: {correct_answer} (type: {type(correct_answer)})", "ERROR")
                        return False
                
                return True
            else:
                self.log(f"❌ FIX 2 FAILED: Test creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ FIX 2 ERROR: Test creation error: {str(e)}", "ERROR")
            return False

    # ============ CRITICAL FIX 6: Added endpoint GET /api/sessions/{session_id}/tests/available ============
    
    def test_sessions_tests_available(self):
        """Test GET /api/sessions/{session_id}/tests/available (was 500, should be 200/403 now)"""
        self.log("🧪 Testing FIX 6: GET /api/sessions/{session_id}/tests/available...")
        
        if not self.participant_token or not self.test_session_id:
            self.log("❌ Missing participant token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.test_session_id}/tests/available", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ FIX 6 SUCCESS: Available tests retrieved successfully. Count: {len(data)}")
                
                # Verify tests don't include correct answers (security)
                for test in data:
                    for question in test.get('questions', []):
                        if 'correct_answer' in question:
                            self.log("❌ FIX 6 SECURITY ISSUE: Available tests include correct answers", "ERROR")
                            return False
                
                self.log("   ✅ Available tests correctly exclude correct answers")
                return True
            elif response.status_code == 403:
                self.log("✅ FIX 6 SUCCESS: Endpoint returns 403 (access control working)")
                return True
            else:
                self.log(f"❌ FIX 6 FAILED: Available tests failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ FIX 6 ERROR: Available tests error: {str(e)}", "ERROR")
            return False

    # ============ CRITICAL FIX 4 & 5: Feedback Models ============
    
    def test_feedback_templates_new_path(self):
        """Test GET /api/feedback/templates/program/{program_id} (new path, should be 200)"""
        self.log("🧪 Testing FIX 4: GET /api/feedback/templates/program/{program_id} (new path)...")
        
        if not self.admin_token or not self.test_program_id:
            self.log("❌ Missing admin token or program ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/feedback/templates/program/{self.test_program_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ FIX 4 SUCCESS: Feedback templates retrieved (new path). Count: {len(data)}")
                return True
            else:
                self.log(f"❌ FIX 4 FAILED: Feedback templates failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ FIX 4 ERROR: Feedback templates error: {str(e)}", "ERROR")
            return False
    
    def test_create_feedback_template_new_path(self):
        """Test POST /api/feedback/templates (new path, should be 200)"""
        self.log("🧪 Testing FIX 5: POST /api/feedback/templates (new path, title Optional)...")
        
        if not self.admin_token or not self.test_program_id:
            self.log("❌ Missing admin token or program ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test with title Optional (not provided)
        template_data = {
            "program_id": self.test_program_id,
            "questions": [
                {
                    "question": "Overall Training Experience",
                    "type": "rating",  # Changed from question_type to type
                    "required": True,  # Added required field
                    "options": ["1", "2", "3", "4", "5"]
                },
                {
                    "question": "Additional Comments",
                    "type": "text",  # Changed from question_type to type
                    "required": False  # Added required field
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/feedback/templates", json=template_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ FIX 5 SUCCESS: Feedback template created (new path, title Optional). ID: {data.get('id')}")
                
                # Verify question structure
                for i, question in enumerate(data.get('questions', [])):
                    if 'type' in question and 'required' in question:
                        self.log(f"   ✅ Question {i+1}: type='{question['type']}', required={question['required']}")
                    else:
                        self.log(f"   ❌ Question {i+1} missing 'type' or 'required' field", "ERROR")
                        return False
                
                return True
            else:
                self.log(f"❌ FIX 5 FAILED: Feedback template creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ FIX 5 ERROR: Feedback template creation error: {str(e)}", "ERROR")
            return False

    # ============ API PATH CHANGES VERIFICATION ============
    
    def test_checklists_templates_new_path(self):
        """Test GET /api/checklists/templates (new path, should be 200)"""
        self.log("🧪 Testing API PATH CHANGE: GET /api/checklists/templates (new path)...")
        
        if not self.admin_token:
            self.log("❌ Missing admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/checklists/templates", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ API PATH SUCCESS: Checklist templates retrieved (new path). Count: {len(data)}")
                return True
            else:
                self.log(f"❌ API PATH FAILED: Checklist templates failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ API PATH ERROR: Checklist templates error: {str(e)}", "ERROR")
            return False

    # ============ CRITICAL FIX 3: Test submission with List[int] answers ============
    
    def test_submit_test_with_int_answers(self):
        """Test POST /api/tests/submit with answers as List[int] (FIX 3)"""
        self.log("🧪 Testing FIX 3: POST /api/tests/submit with answers as List[int]...")
        
        if not self.participant_token or not hasattr(self, 'created_test_id') or not self.test_session_id:
            self.log("❌ Missing participant token, test ID, or session ID", "ERROR")
            return False
        
        # First, enable participant access to tests
        if not self.admin_token:
            self.log("❌ Missing admin token for access update", "ERROR")
            return False
            
        admin_headers = {'Authorization': f'Bearer {self.admin_token}'}
        access_data = {
            "participant_id": self.participant_id,
            "session_id": self.test_session_id,
            "can_access_pre_test": True,
            "can_access_post_test": True
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/participant-access/update", json=access_data, headers=admin_headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to enable participant access: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error enabling participant access: {str(e)}", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        # Submit test with int answers
        submission_data = {
            "test_id": self.created_test_id,
            "session_id": self.test_session_id,
            "answers": [2, 1]  # List[int], not List[str]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/tests/submit", json=submission_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ FIX 3 SUCCESS: Test submitted with List[int] answers. Result ID: {data.get('id')}")
                self.log(f"   Score: {data.get('score', 0)}%")
                self.log(f"   Passed: {data.get('passed', False)}")
                
                # Verify answers are stored as List[int]
                if 'answers' in data:
                    answers = data['answers']
                    if isinstance(answers, list) and all(isinstance(ans, int) for ans in answers):
                        self.log(f"   ✅ Answers stored as List[int]: {answers}")
                    else:
                        self.log(f"   ❌ Answers not stored as List[int]: {answers} (types: {[type(ans) for ans in answers]})", "ERROR")
                        return False
                
                return True
            else:
                self.log(f"❌ FIX 3 FAILED: Test submission failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ FIX 3 ERROR: Test submission error: {str(e)}", "ERROR")
            return False

    def run_all_tests(self):
        """Run all critical fixes tests"""
        self.log("🚀 Starting Focused Critical Backend Fixes Verification Test Suite...")
        self.log("=" * 80)
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Participant Login", self.login_participant),
            ("Get Existing Data", self.get_existing_data),
            ("FIX 1: Training Reports Admin All", self.test_training_reports_admin_all),
            ("FIX 2: Create Test with Int Correct Answer", self.test_create_test_with_int_correct_answer),
            ("FIX 6: Sessions Tests Available", self.test_sessions_tests_available),
            ("FIX 4: Feedback Templates New Path", self.test_feedback_templates_new_path),
            ("FIX 5: Create Feedback Template New Path", self.test_create_feedback_template_new_path),
            ("API PATH: Checklists Templates New Path", self.test_checklists_templates_new_path),
            ("FIX 3: Submit Test with Int Answers", self.test_submit_test_with_int_answers)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n🧪 Running: {test_name}")
            self.log("-" * 60)
            
            try:
                if test_func():
                    passed += 1
                    self.log(f"✅ PASSED: {test_name}")
                else:
                    failed += 1
                    self.log(f"❌ FAILED: {test_name}")
            except Exception as e:
                failed += 1
                self.log(f"❌ ERROR in {test_name}: {str(e)}", "ERROR")
        
        self.log("\n" + "=" * 80)
        self.log(f"🏁 FOCUSED CRITICAL FIXES TEST SUITE COMPLETE")
        self.log(f"✅ PASSED: {passed}")
        self.log(f"❌ FAILED: {failed}")
        self.log(f"📊 SUCCESS RATE: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            self.log("🎉 ALL CRITICAL FIXES VERIFIED SUCCESSFULLY!")
            return True
        else:
            self.log("⚠️  SOME CRITICAL FIXES STILL HAVE ISSUES")
            return False

if __name__ == "__main__":
    runner = FocusedCriticalFixesTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)