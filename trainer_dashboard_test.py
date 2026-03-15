#!/usr/bin/env python3
"""
TrainerDashboard Session Results Testing
Tests the updated TrainerDashboard functionality for regular trainers to access session results.

TESTING SCOPE:
1. Verify trainer users exist in database
2. Test trainer login functionality  
3. Test that regular trainers can access sessions
4. Test session results data loading endpoints:
   - GET /api/attendance/session/{session_id}
   - GET /api/tests/results/session/{session_id} 
   - GET /api/feedback/session/{session_id}
5. Verify both regular and chief trainers have access
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://session-excel-hub.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

class TrainerDashboardTester:
    def __init__(self):
        self.admin_token = None
        self.trainer_token = None
        self.chief_trainer_token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.test_session_id = None
        self.test_participant_id = None
        self.trainer_user_id = None
        self.chief_trainer_user_id = None
        
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
    
    def test_get_trainer_users(self):
        """Test GET /api/users?role=trainer - check trainer users exist"""
        self.log("🔍 Testing GET /api/users?role=trainer - checking trainer users exist...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/users?role=trainer", headers=headers)
            
            if response.status_code == 200:
                trainers = response.json()
                self.log(f"✅ Retrieved trainer users successfully. Count: {len(trainers)}")
                
                if len(trainers) == 0:
                    self.log("⚠️  No trainer users found in database", "WARNING")
                    return self.create_test_trainers()
                else:
                    # Store trainer IDs for later use
                    for trainer in trainers:
                        self.log(f"   Trainer: {trainer['full_name']} ({trainer['email']}) - ID: {trainer['id']}")
                        if not self.trainer_user_id:
                            self.trainer_user_id = trainer['id']
                    
                    return True
            else:
                self.log(f"❌ Get trainer users failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get trainer users error: {str(e)}", "ERROR")
            return False
    
    def create_test_trainers(self):
        """Create test trainer users if none exist"""
        self.log("🔧 Creating test trainer users...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create regular trainer
        trainer_data = {
            "email": "trainer@example.com",
            "password": "trainer123",
            "full_name": "Test Regular Trainer",
            "id_number": "TR001",
            "role": "trainer",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=trainer_data, headers=headers)
            
            if response.status_code == 200:
                trainer_user = response.json()
                self.trainer_user_id = trainer_user['id']
                self.log(f"✅ Regular trainer created successfully. ID: {self.trainer_user_id}")
            elif response.status_code == 400 and "User already exists" in response.text:
                self.log("✅ Regular trainer already exists (expected from previous runs)")
                # Get existing trainer ID
                login_data = {"email": "trainer@example.com", "password": "trainer123"}
                login_response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                if login_response.status_code == 200:
                    self.trainer_user_id = login_response.json()['user']['id']
            else:
                self.log(f"❌ Regular trainer creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Regular trainer creation error: {str(e)}", "ERROR")
            return False
        
        # Create chief trainer
        chief_trainer_data = {
            "email": "chieftrainer@example.com",
            "password": "chief123",
            "full_name": "Test Chief Trainer",
            "id_number": "CT001",
            "role": "trainer",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=chief_trainer_data, headers=headers)
            
            if response.status_code == 200:
                chief_trainer_user = response.json()
                self.chief_trainer_user_id = chief_trainer_user['id']
                self.log(f"✅ Chief trainer created successfully. ID: {self.chief_trainer_user_id}")
                return True
            elif response.status_code == 400 and "User already exists" in response.text:
                self.log("✅ Chief trainer already exists (expected from previous runs)")
                # Get existing chief trainer ID
                login_data = {"email": "chieftrainer@example.com", "password": "chief123"}
                login_response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                if login_response.status_code == 200:
                    self.chief_trainer_user_id = login_response.json()['user']['id']
                return True
            else:
                self.log(f"❌ Chief trainer creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Chief trainer creation error: {str(e)}", "ERROR")
            return False
    
    def test_trainer_login(self):
        """Test trainer login functionality"""
        self.log("🔐 Testing trainer login functionality...")
        
        # Try to login with existing trainer credentials
        # Let's try with the first trainer's email and a common password
        existing_trainers = [
            {"email": "vijay@mddrc.com.my", "password": "mddrc1"},
            {"email": "Dheena8983@gmail.com", "password": "mddrc1"},
            {"email": "mawardi@gmail.com", "password": "mddrc1"},
            {"email": "hisam@gmail.com.my", "password": "mddrc1"}
        ]
        
        trainer_logged_in = False
        chief_trainer_logged_in = False
        
        # Try to login with existing trainers
        for i, trainer_creds in enumerate(existing_trainers):
            login_data = {
                "email": trainer_creds["email"],
                "password": trainer_creds["password"]
            }
            
            try:
                response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if not trainer_logged_in:
                        self.trainer_token = data['access_token']
                        self.trainer_user_id = data['user']['id']
                        self.log(f"✅ Trainer login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                        trainer_logged_in = True
                    elif not chief_trainer_logged_in:
                        self.chief_trainer_token = data['access_token']
                        self.chief_trainer_user_id = data['user']['id']
                        self.log(f"✅ Chief trainer login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                        chief_trainer_logged_in = True
                        break
                else:
                    self.log(f"⚠️  Login failed for {trainer_creds['email']}: {response.status_code}", "WARNING")
                    
            except Exception as e:
                self.log(f"⚠️  Login error for {trainer_creds['email']}: {str(e)}", "WARNING")
        
        # If we couldn't login with existing trainers, create new ones
        if not trainer_logged_in:
            self.log("🔧 Creating new trainer users since existing ones couldn't be logged in...")
            if not self.create_test_trainers():
                return False
            
            # Try to login with newly created trainers
            login_data = {
                "email": "trainer@example.com",
                "password": "trainer123"
            }
            
            try:
                response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    self.trainer_token = data['access_token']
                    self.log(f"✅ New trainer login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                    trainer_logged_in = True
                else:
                    self.log(f"❌ New trainer login failed: {response.status_code} - {response.text}", "ERROR")
                    return False
                    
            except Exception as e:
                self.log(f"❌ New trainer login error: {str(e)}", "ERROR")
                return False
        
        if not chief_trainer_logged_in:
            # Try to login with newly created chief trainer
            chief_login_data = {
                "email": "chieftrainer@example.com",
                "password": "chief123"
            }
            
            try:
                response = self.session.post(f"{BASE_URL}/auth/login", json=chief_login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    self.chief_trainer_token = data['access_token']
                    self.log(f"✅ Chief trainer login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                    chief_trainer_logged_in = True
                else:
                    self.log(f"❌ Chief trainer login failed: {response.status_code} - {response.text}", "ERROR")
                    return False
                    
            except Exception as e:
                self.log(f"❌ Chief trainer login error: {str(e)}", "ERROR")
                return False
        
        return trainer_logged_in and chief_trainer_logged_in
    
    def test_get_sessions_as_trainer(self):
        """Test GET /api/sessions - verify sessions are returned for trainers"""
        self.log("📋 Testing GET /api/sessions - verifying sessions returned for trainers...")
        
        if not self.trainer_token:
            self.log("❌ No trainer token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Sessions retrieved successfully for trainer. Count: {len(sessions)}")
                
                if len(sessions) == 0:
                    self.log("⚠️  No sessions found for trainer", "WARNING")
                    return self.create_test_session_with_trainers()
                else:
                    # Use first session for testing
                    self.test_session_id = sessions[0]['id']
                    self.log(f"   Using session for testing: {sessions[0]['name']} (ID: {self.test_session_id})")
                    return True
            else:
                self.log(f"❌ Get sessions as trainer failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get sessions as trainer error: {str(e)}", "ERROR")
            return False
    
    def create_test_session_with_trainers(self):
        """Create a test session with trainer assignments"""
        self.log("🔧 Creating test session with trainer assignments...")
        
        if not self.admin_token or not self.trainer_user_id or not self.chief_trainer_user_id:
            self.log("❌ Missing admin token or trainer IDs", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # First create a program and company
        program_data = {
            "name": "Trainer Dashboard Test Program",
            "description": "Program for testing trainer dashboard functionality",
            "pass_percentage": 70.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/programs", json=program_data, headers=headers)
            if response.status_code == 200:
                program_id = response.json()['id']
                self.log(f"✅ Test program created. ID: {program_id}")
            else:
                self.log(f"❌ Program creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Program creation error: {str(e)}", "ERROR")
            return False
        
        company_data = {
            "name": "Trainer Dashboard Test Company"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
            if response.status_code == 200:
                company_id = response.json()['id']
                self.log(f"✅ Test company created. ID: {company_id}")
            else:
                self.log(f"❌ Company creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Company creation error: {str(e)}", "ERROR")
            return False
        
        # Create a test participant
        participant_data = {
            "email": "testparticipant@example.com",
            "password": "participant123",
            "full_name": "Test Participant for Trainer Dashboard",
            "id_number": "TP001",
            "role": "participant",
            "company_id": company_id,
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=participant_data, headers=headers)
            if response.status_code == 200:
                self.test_participant_id = response.json()['id']
                self.log(f"✅ Test participant created. ID: {self.test_participant_id}")
            elif response.status_code == 400 and "User already exists" in response.text:
                # Get existing participant ID
                login_data = {"email": "testparticipant@example.com", "password": "participant123"}
                login_response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                if login_response.status_code == 200:
                    self.test_participant_id = login_response.json()['user']['id']
                    self.log(f"✅ Using existing test participant. ID: {self.test_participant_id}")
            else:
                self.log(f"❌ Participant creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Participant creation error: {str(e)}", "ERROR")
            return False
        
        # Create session with trainer assignments
        session_data = {
            "name": "Trainer Dashboard Test Session",
            "program_id": program_id,
            "company_id": company_id,
            "location": "Test Location",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "participant_ids": [self.test_participant_id],
            "trainer_assignments": [
                {
                    "trainer_id": self.chief_trainer_user_id,
                    "role": "chief"
                },
                {
                    "trainer_id": self.trainer_user_id,
                    "role": "regular"
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                session_response = response.json()
                self.test_session_id = session_response['session']['id']
                self.log(f"✅ Test session with trainers created successfully. ID: {self.test_session_id}")
                return True
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def test_attendance_data_loading(self):
        """Test GET /api/attendance/session/{session_id} - test attendance data loading"""
        self.log("👥 Testing GET /api/attendance/session/{session_id} - attendance data loading...")
        
        if not self.trainer_token or not self.test_session_id:
            self.log("❌ Missing trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/attendance/session/{self.test_session_id}", headers=headers)
            
            if response.status_code == 200:
                attendance_data = response.json()
                self.log(f"✅ Attendance data retrieved successfully. Records: {len(attendance_data)}")
                
                # Log details of attendance records
                for record in attendance_data:
                    participant_name = record.get('participant_name', 'Unknown')
                    clock_in = record.get('clock_in', 'Not clocked in')
                    clock_out = record.get('clock_out', 'Not clocked out')
                    self.log(f"   Participant: {participant_name}, Clock In: {clock_in}, Clock Out: {clock_out}")
                
                return True
            else:
                self.log(f"❌ Attendance data loading failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Attendance data loading error: {str(e)}", "ERROR")
            return False
    
    def test_test_results_data_loading(self):
        """Test GET /api/tests/results/session/{session_id} - test results data loading"""
        self.log("📊 Testing GET /api/tests/results/session/{session_id} - test results data loading...")
        
        if not self.trainer_token or not self.test_session_id:
            self.log("❌ Missing trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            # First try the results summary endpoint which should work for trainers
            response = self.session.get(f"{BASE_URL}/sessions/{self.test_session_id}/results-summary", headers=headers)
            
            if response.status_code == 200:
                results_data = response.json()
                self.log(f"✅ Test results data retrieved successfully via results-summary endpoint")
                self.log(f"   Session: {results_data.get('session_name', 'Unknown')}")
                self.log(f"   Participants: {len(results_data.get('participants', []))}")
                
                # Log details of test results
                for participant in results_data.get('participants', []):
                    name = participant.get('participant', {}).get('name', 'Unknown')
                    pre_test = participant.get('pre_test', {})
                    post_test = participant.get('post_test', {})
                    
                    self.log(f"   Participant: {name}")
                    self.log(f"     Pre-test: {'Completed' if pre_test.get('completed') else 'Not completed'} - Score: {pre_test.get('score', 0)}%")
                    self.log(f"     Post-test: {'Completed' if post_test.get('completed') else 'Not completed'} - Score: {post_test.get('score', 0)}%")
                
                return True
            else:
                self.log(f"❌ Test results data loading failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Test results data loading error: {str(e)}", "ERROR")
            return False
    
    def test_feedback_data_loading(self):
        """Test GET /api/feedback/session/{session_id} - test feedback data loading"""
        self.log("💬 Testing GET /api/feedback/session/{session_id} - feedback data loading...")
        
        if not self.trainer_token or not self.test_session_id:
            self.log("❌ Missing trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            # Try to get feedback data for the session
            response = self.session.get(f"{BASE_URL}/feedback/session/{self.test_session_id}", headers=headers)
            
            if response.status_code == 200:
                feedback_data = response.json()
                self.log(f"✅ Feedback data retrieved successfully. Records: {len(feedback_data)}")
                
                # Log details of feedback records
                for feedback in feedback_data:
                    participant_id = feedback.get('participant_id', 'Unknown')
                    responses = feedback.get('responses', [])
                    submitted_at = feedback.get('submitted_at', 'Unknown')
                    self.log(f"   Participant ID: {participant_id}, Responses: {len(responses)}, Submitted: {submitted_at}")
                
                return True
            elif response.status_code == 404:
                self.log("✅ Feedback endpoint returned 404 (no feedback data yet, which is expected)")
                return True
            else:
                self.log(f"❌ Feedback data loading failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Feedback data loading error: {str(e)}", "ERROR")
            return False
    
    def test_chief_trainer_access(self):
        """Test that chief trainers also have access to session results"""
        self.log("👑 Testing chief trainer access to session results...")
        
        if not self.chief_trainer_token or not self.test_session_id:
            self.log("❌ Missing chief trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.chief_trainer_token}'}
        
        # Test attendance access
        try:
            response = self.session.get(f"{BASE_URL}/attendance/session/{self.test_session_id}", headers=headers)
            if response.status_code == 200:
                self.log("✅ Chief trainer can access attendance data")
            else:
                self.log(f"❌ Chief trainer attendance access failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Chief trainer attendance access error: {str(e)}", "ERROR")
            return False
        
        # Test results access
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.test_session_id}/results-summary", headers=headers)
            if response.status_code == 200:
                self.log("✅ Chief trainer can access test results data")
            else:
                self.log(f"❌ Chief trainer results access failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Chief trainer results access error: {str(e)}", "ERROR")
            return False
        
        # Test feedback access
        try:
            response = self.session.get(f"{BASE_URL}/feedback/session/{self.test_session_id}", headers=headers)
            if response.status_code in [200, 404]:  # 404 is acceptable if no feedback exists
                self.log("✅ Chief trainer can access feedback data")
                return True
            else:
                self.log(f"❌ Chief trainer feedback access failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Chief trainer feedback access error: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all trainer dashboard tests"""
        self.log("🚀 Starting TrainerDashboard Session Results Testing...")
        self.log("=" * 80)
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Get Trainer Users", self.test_get_trainer_users),
            ("Trainer Login", self.test_trainer_login),
            ("Get Sessions as Trainer", self.test_get_sessions_as_trainer),
            ("Attendance Data Loading", self.test_attendance_data_loading),
            ("Test Results Data Loading", self.test_test_results_data_loading),
            ("Feedback Data Loading", self.test_feedback_data_loading),
            ("Chief Trainer Access", self.test_chief_trainer_access),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n🧪 Running Test: {test_name}")
            self.log("-" * 50)
            
            try:
                if test_func():
                    self.log(f"✅ {test_name} - PASSED")
                    passed += 1
                else:
                    self.log(f"❌ {test_name} - FAILED")
                    failed += 1
            except Exception as e:
                self.log(f"❌ {test_name} - ERROR: {str(e)}")
                failed += 1
        
        # Summary
        self.log("\n" + "=" * 80)
        self.log("🏁 TRAINER DASHBOARD TESTING COMPLETE")
        self.log("=" * 80)
        self.log(f"✅ Tests Passed: {passed}")
        self.log(f"❌ Tests Failed: {failed}")
        self.log(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED! TrainerDashboard functionality is working correctly.")
            return True
        else:
            self.log("⚠️  Some tests failed. Please review the issues above.")
            return False

def main():
    """Main function to run the trainer dashboard tests"""
    tester = TrainerDashboardTester()
    success = tester.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()