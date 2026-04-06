#!/usr/bin/env python3
"""
Trainer Dashboard Session Results Access Test
Tests the backend permission fixes for regular trainers to access session results:
- GET /api/attendance/session/{session_id} - should now allow trainers
- GET /api/sessions/{session_id}/results-summary - should now allow trainers  
- GET /api/feedback/session/{session_id} - should now allow trainers
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://quote-n-cert.preview.emergentagent.com/api"

# Existing trainer credentials (corrected passwords)
TRAINER_CREDENTIALS = [
    {"email": "vijay@mddrc.com.my", "password": "mddrc1"},
    {"email": "Dheena8983@gmail.com", "password": "mddrc1"}
]

class TrainerAccessTester:
    def __init__(self):
        self.trainer_tokens = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.test_session_id = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_trainers(self):
        """Login all trainer accounts and get authentication tokens"""
        self.log("Logging in trainer accounts...")
        
        for i, creds in enumerate(TRAINER_CREDENTIALS):
            try:
                response = self.session.post(f"{BASE_URL}/auth/login", json=creds)
                
                if response.status_code == 200:
                    data = response.json()
                    token = data['access_token']
                    user_info = data['user']
                    self.trainer_tokens.append({
                        'token': token,
                        'email': creds['email'],
                        'user_id': user_info['id'],
                        'full_name': user_info['full_name'],
                        'role': user_info['role']
                    })
                    self.log(f"✅ Trainer {i+1} login successful: {user_info['full_name']} ({user_info['role']})")
                else:
                    self.log(f"❌ Trainer {i+1} login failed: {response.status_code} - {response.text}", "ERROR")
                    return False
                    
            except Exception as e:
                self.log(f"❌ Trainer {i+1} login error: {str(e)}", "ERROR")
                return False
        
        if len(self.trainer_tokens) > 0:
            self.log(f"✅ Successfully logged in {len(self.trainer_tokens)} trainers")
            return True
        else:
            self.log("❌ No trainers logged in successfully", "ERROR")
            return False
    
    def get_available_sessions(self):
        """Get available sessions using first trainer token"""
        self.log("Getting available sessions...")
        
        if not self.trainer_tokens:
            self.log("❌ No trainer tokens available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_tokens[0]["token"]}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Retrieved {len(sessions)} sessions")
                
                if sessions:
                    # Use the first available session for testing
                    self.test_session_id = sessions[0]['id']
                    session_name = sessions[0].get('name', 'Unknown')
                    self.log(f"✅ Using session for testing: {session_name} (ID: {self.test_session_id})")
                    return True
                else:
                    self.log("❌ No sessions available for testing", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get sessions: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error getting sessions: {str(e)}", "ERROR")
            return False
    
    def test_attendance_endpoint_access(self):
        """Test GET /api/attendance/session/{session_id} access for trainers"""
        self.log("Testing attendance endpoint access for trainers...")
        
        if not self.trainer_tokens or not self.test_session_id:
            self.log("❌ Missing trainer tokens or session ID", "ERROR")
            return False
        
        results = []
        
        for i, trainer in enumerate(self.trainer_tokens):
            headers = {'Authorization': f'Bearer {trainer["token"]}'}
            
            try:
                response = self.session.get(f"{BASE_URL}/attendance/session/{self.test_session_id}", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"✅ Trainer {i+1} ({trainer['full_name']}) - Attendance access SUCCESS")
                    self.log(f"   Retrieved {len(data)} attendance records")
                    results.append(True)
                elif response.status_code == 403:
                    self.log(f"❌ Trainer {i+1} ({trainer['full_name']}) - Attendance access DENIED (403)", "ERROR")
                    results.append(False)
                else:
                    self.log(f"❌ Trainer {i+1} ({trainer['full_name']}) - Unexpected response: {response.status_code}", "ERROR")
                    results.append(False)
                    
            except Exception as e:
                self.log(f"❌ Trainer {i+1} attendance test error: {str(e)}", "ERROR")
                results.append(False)
        
        success_count = sum(results)
        total_count = len(results)
        
        if success_count == total_count:
            self.log(f"✅ Attendance endpoint access: {success_count}/{total_count} trainers successful")
            return True
        else:
            self.log(f"❌ Attendance endpoint access: {success_count}/{total_count} trainers successful", "ERROR")
            return False
    
    def test_results_summary_endpoint_access(self):
        """Test GET /api/sessions/{session_id}/results-summary access for trainers"""
        self.log("Testing results summary endpoint access for trainers...")
        
        if not self.trainer_tokens or not self.test_session_id:
            self.log("❌ Missing trainer tokens or session ID", "ERROR")
            return False
        
        results = []
        
        for i, trainer in enumerate(self.trainer_tokens):
            headers = {'Authorization': f'Bearer {trainer["token"]}'}
            
            try:
                response = self.session.get(f"{BASE_URL}/sessions/{self.test_session_id}/results-summary", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    participants = data.get('participants', [])
                    self.log(f"✅ Trainer {i+1} ({trainer['full_name']}) - Results summary access SUCCESS")
                    self.log(f"   Retrieved results for {len(participants)} participants")
                    results.append(True)
                elif response.status_code == 403:
                    self.log(f"❌ Trainer {i+1} ({trainer['full_name']}) - Results summary access DENIED (403)", "ERROR")
                    results.append(False)
                else:
                    self.log(f"❌ Trainer {i+1} ({trainer['full_name']}) - Unexpected response: {response.status_code}", "ERROR")
                    results.append(False)
                    
            except Exception as e:
                self.log(f"❌ Trainer {i+1} results summary test error: {str(e)}", "ERROR")
                results.append(False)
        
        success_count = sum(results)
        total_count = len(results)
        
        if success_count == total_count:
            self.log(f"✅ Results summary endpoint access: {success_count}/{total_count} trainers successful")
            return True
        else:
            self.log(f"❌ Results summary endpoint access: {success_count}/{total_count} trainers successful", "ERROR")
            return False
    
    def test_feedback_endpoint_access(self):
        """Test GET /api/feedback/session/{session_id} access for trainers"""
        self.log("Testing feedback endpoint access for trainers...")
        
        if not self.trainer_tokens or not self.test_session_id:
            self.log("❌ Missing trainer tokens or session ID", "ERROR")
            return False
        
        results = []
        
        for i, trainer in enumerate(self.trainer_tokens):
            headers = {'Authorization': f'Bearer {trainer["token"]}'}
            
            try:
                response = self.session.get(f"{BASE_URL}/feedback/session/{self.test_session_id}", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"✅ Trainer {i+1} ({trainer['full_name']}) - Feedback access SUCCESS")
                    self.log(f"   Retrieved {len(data)} feedback records")
                    results.append(True)
                elif response.status_code == 403:
                    self.log(f"❌ Trainer {i+1} ({trainer['full_name']}) - Feedback access DENIED (403)", "ERROR")
                    results.append(False)
                else:
                    self.log(f"❌ Trainer {i+1} ({trainer['full_name']}) - Unexpected response: {response.status_code}", "ERROR")
                    results.append(False)
                    
            except Exception as e:
                self.log(f"❌ Trainer {i+1} feedback test error: {str(e)}", "ERROR")
                results.append(False)
        
        success_count = sum(results)
        total_count = len(results)
        
        if success_count == total_count:
            self.log(f"✅ Feedback endpoint access: {success_count}/{total_count} trainers successful")
            return True
        else:
            self.log(f"❌ Feedback endpoint access: {success_count}/{total_count} trainers successful", "ERROR")
            return False
    
    def test_trainer_role_verification(self):
        """Verify that logged in users are actually trainers"""
        self.log("Verifying trainer roles...")
        
        if not self.trainer_tokens:
            self.log("❌ No trainer tokens available", "ERROR")
            return False
        
        all_trainers = True
        for i, trainer in enumerate(self.trainer_tokens):
            if trainer['role'] != 'trainer':
                self.log(f"❌ User {i+1} ({trainer['full_name']}) has role '{trainer['role']}', expected 'trainer'", "ERROR")
                all_trainers = False
            else:
                self.log(f"✅ User {i+1} ({trainer['full_name']}) confirmed as trainer")
        
        return all_trainers
    
    def run_all_tests(self):
        """Run all trainer access tests"""
        self.log("=" * 80)
        self.log("TRAINER DASHBOARD SESSION RESULTS ACCESS TEST")
        self.log("=" * 80)
        
        tests = [
            ("Trainer Login", self.login_trainers),
            ("Trainer Role Verification", self.test_trainer_role_verification),
            ("Get Available Sessions", self.get_available_sessions),
            ("Attendance Endpoint Access", self.test_attendance_endpoint_access),
            ("Results Summary Endpoint Access", self.test_results_summary_endpoint_access),
            ("Feedback Endpoint Access", self.test_feedback_endpoint_access),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            self.log(f"\n--- {test_name} ---")
            try:
                result = test_func()
                results.append((test_name, result))
                if result:
                    self.log(f"✅ {test_name}: PASSED")
                else:
                    self.log(f"❌ {test_name}: FAILED", "ERROR")
            except Exception as e:
                self.log(f"❌ {test_name}: ERROR - {str(e)}", "ERROR")
                results.append((test_name, False))
        
        # Summary
        self.log("\n" + "=" * 80)
        self.log("TEST SUMMARY")
        self.log("=" * 80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            self.log(f"{test_name}: {status}")
        
        self.log(f"\nOverall Result: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED - Trainer access fixes are working!")
            return True
        else:
            self.log("❌ SOME TESTS FAILED - Trainer access issues remain", "ERROR")
            return False

def main():
    """Main test execution"""
    tester = TrainerAccessTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Trainer access testing completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Trainer access testing failed")
        sys.exit(1)

if __name__ == "__main__":
    main()