#!/usr/bin/env python3
"""
Trainer Session Results Access Test - Final Verification
Tests that all session results endpoints now work for regular trainers:
1. GET /api/attendance/session/{session_id} - Should allow "trainer" role
2. GET /api/tests/results/session/{session_id} - Should allow "trainer" role  
3. GET /api/feedback/session/{session_id} - Should allow "trainer" role
4. GET /api/sessions/{session_id}/results-summary - Should allow all trainers (not just chief)

Uses existing trainer: vijay@mddrc.com.my / mddrc1 (regular trainer)
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://trainingfix.preview.emergentagent.com/api"
TRAINER_EMAIL = "vijay@mddrc.com.my"
TRAINER_PASSWORD = "mddrc1"

class TrainerSessionResultsTest:
    def __init__(self):
        self.trainer_token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.test_session_id = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_trainer(self):
        """Login as regular trainer vijay@mddrc.com.my"""
        self.log("Attempting trainer login...")
        
        login_data = {
            "email": TRAINER_EMAIL,
            "password": TRAINER_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.trainer_token = data['access_token']
                user_info = data['user']
                self.log(f"✅ Trainer login successful. User: {user_info['full_name']} ({user_info['role']})")
                self.log(f"   Email: {user_info['email']}")
                self.log(f"   ID: {user_info['id']}")
                return True
            else:
                self.log(f"❌ Trainer login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Trainer login error: {str(e)}", "ERROR")
            return False
    
    def get_available_sessions(self):
        """Get available sessions for the trainer"""
        self.log("Getting available sessions for trainer...")
        
        if not self.trainer_token:
            self.log("❌ No trainer token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Retrieved {len(sessions)} sessions")
                
                if sessions:
                    # Use the first session for testing
                    self.test_session_id = sessions[0]['id']
                    session_name = sessions[0]['name']
                    self.log(f"✅ Using session for testing: {session_name} (ID: {self.test_session_id})")
                    
                    # Log all available sessions
                    for i, session in enumerate(sessions):
                        self.log(f"   Session {i+1}: {session['name']} (ID: {session['id']})")
                    
                    return True
                else:
                    self.log("❌ No sessions available for trainer", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Get sessions failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get sessions error: {str(e)}", "ERROR")
            return False
    
    def test_attendance_session_endpoint(self):
        """Test GET /api/attendance/session/{session_id} - Should allow trainer role"""
        self.log("Testing GET /api/attendance/session/{session_id} for regular trainer...")
        
        if not self.trainer_token or not self.test_session_id:
            self.log("❌ Missing trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/attendance/session/{self.test_session_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Attendance session endpoint SUCCESS - Regular trainer can access")
                self.log(f"   Retrieved {len(data)} attendance records")
                return True
            elif response.status_code == 403:
                self.log("❌ Attendance session endpoint FAILED - 403 Forbidden for regular trainer", "ERROR")
                self.log(f"   Response: {response.text}")
                return False
            else:
                self.log(f"❌ Attendance session endpoint FAILED - {response.status_code}: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Attendance session endpoint error: {str(e)}", "ERROR")
            return False
    
    def test_test_results_session_endpoint(self):
        """Test GET /api/tests/results/session/{session_id} - Should allow trainer role"""
        self.log("Testing GET /api/tests/results/session/{session_id} for regular trainer...")
        
        if not self.trainer_token or not self.test_session_id:
            self.log("❌ Missing trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/tests/results/session/{self.test_session_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Test results session endpoint SUCCESS - Regular trainer can access")
                self.log(f"   Retrieved {len(data)} test results")
                return True
            elif response.status_code == 403:
                self.log("❌ Test results session endpoint FAILED - 403 Forbidden for regular trainer", "ERROR")
                self.log(f"   Response: {response.text}")
                return False
            else:
                self.log(f"❌ Test results session endpoint FAILED - {response.status_code}: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Test results session endpoint error: {str(e)}", "ERROR")
            return False
    
    def test_feedback_session_endpoint(self):
        """Test GET /api/feedback/session/{session_id} - Should allow trainer role"""
        self.log("Testing GET /api/feedback/session/{session_id} for regular trainer...")
        
        if not self.trainer_token or not self.test_session_id:
            self.log("❌ Missing trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/feedback/session/{self.test_session_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Feedback session endpoint SUCCESS - Regular trainer can access")
                self.log(f"   Retrieved {len(data)} feedback records")
                return True
            elif response.status_code == 403:
                self.log("❌ Feedback session endpoint FAILED - 403 Forbidden for regular trainer", "ERROR")
                self.log(f"   Response: {response.text}")
                return False
            else:
                self.log(f"❌ Feedback session endpoint FAILED - {response.status_code}: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Feedback session endpoint error: {str(e)}", "ERROR")
            return False
    
    def test_results_summary_endpoint(self):
        """Test GET /api/sessions/{session_id}/results-summary - Should allow all trainers"""
        self.log("Testing GET /api/sessions/{session_id}/results-summary for regular trainer...")
        
        if not self.trainer_token or not self.test_session_id:
            self.log("❌ Missing trainer token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.test_session_id}/results-summary", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Results summary endpoint SUCCESS - Regular trainer can access")
                self.log(f"   Session: {data.get('session_name', 'N/A')}")
                self.log(f"   Participants: {len(data.get('participants', []))}")
                return True
            elif response.status_code == 403:
                self.log("❌ Results summary endpoint FAILED - 403 Forbidden for regular trainer", "ERROR")
                self.log(f"   Response: {response.text}")
                return False
            else:
                self.log(f"❌ Results summary endpoint FAILED - {response.status_code}: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Results summary endpoint error: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all trainer session results access tests"""
        self.log("=" * 80)
        self.log("TRAINER SESSION RESULTS ACCESS - FINAL VERIFICATION TEST")
        self.log("=" * 80)
        
        tests = [
            ("Trainer Login", self.login_trainer),
            ("Get Available Sessions", self.get_available_sessions),
            ("Attendance Session Endpoint", self.test_attendance_session_endpoint),
            ("Test Results Session Endpoint", self.test_test_results_session_endpoint),
            ("Feedback Session Endpoint", self.test_feedback_session_endpoint),
            ("Results Summary Endpoint", self.test_results_summary_endpoint),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running Test: {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    self.log(f"✅ {test_name} PASSED")
                else:
                    failed += 1
                    self.log(f"❌ {test_name} FAILED")
            except Exception as e:
                failed += 1
                self.log(f"❌ {test_name} FAILED with exception: {str(e)}", "ERROR")
        
        self.log("\n" + "=" * 80)
        self.log("FINAL VERIFICATION RESULTS")
        self.log("=" * 80)
        self.log(f"Total Tests: {passed + failed}")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED - Regular trainers can now access all session results endpoints!")
            return True
        else:
            self.log(f"❌ {failed} test(s) failed - Some endpoints still restrict regular trainer access")
            return False

def main():
    """Main function to run the trainer session results test"""
    test_runner = TrainerSessionResultsTest()
    success = test_runner.run_all_tests()
    
    if success:
        print("\n🎉 VERIFICATION COMPLETE: All session results endpoints working for regular trainers!")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED: Some endpoints still need fixes")
        sys.exit(1)

if __name__ == "__main__":
    main()