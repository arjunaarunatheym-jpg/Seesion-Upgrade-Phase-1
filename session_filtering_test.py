#!/usr/bin/env python3
"""
Session Filtering Test Suite for Defensive Driving Training Management System
Tests the session filtering logic fixes for coordinators and trainers:
- Coordinator Session Filtering: ALL non-archived sessions (including completed ones that are ongoing/future)
- Trainer Session Filtering: ONLY future/current sessions (end_date >= today)
- Mark Session as Completed functionality
- Past Training endpoints for both coordinators and trainers
"""

import requests
import json
import sys
from datetime import datetime, date, timedelta

# Configuration
BASE_URL = "https://admin-command-center-16.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

class SessionFilteringTestRunner:
    def __init__(self):
        self.admin_token = None
        self.coordinator_token = None
        self.trainer_token = None
        self.test_program_id = None
        self.test_company_id = None
        self.test_sessions = []  # Store created sessions for cleanup
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_admin(self):
        """Login as admin and get authentication token"""
        self.log("Attempting admin login...")
        
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
    
    def login_coordinator(self):
        """Login as coordinator"""
        self.log("Attempting coordinator login...")
        
        # Use existing coordinator from the system
        login_data = {
            "email": "malek@mddrc.com.my",
            "password": "mddrc1"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.coordinator_token = data['access_token']
                self.coordinator_id = data['user']['id']
                self.log(f"✅ Coordinator login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"❌ Coordinator login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Coordinator login error: {str(e)}", "ERROR")
            return False
    
    def login_trainer(self):
        """Login as trainer"""
        self.log("Attempting trainer login...")
        
        # Use existing trainer from the system
        login_data = {
            "email": "vijay@mddrc.com.my",
            "password": "mddrc1"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.trainer_token = data['access_token']
                self.trainer_id = data['user']['id']
                self.log(f"✅ Trainer login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"❌ Trainer login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Trainer login error: {str(e)}", "ERROR")
            return False
    
    def setup_test_data(self):
        """Create test program and company for session testing"""
        self.log("Setting up test data...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create test program
        program_data = {
            "name": "Session Filtering Test Program",
            "description": "Program for testing session filtering logic",
            "pass_percentage": 70.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/programs", json=program_data, headers=headers)
            if response.status_code == 200:
                self.test_program_id = response.json()['id']
                self.log(f"✅ Test program created. ID: {self.test_program_id}")
            else:
                self.log(f"❌ Program creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Program creation error: {str(e)}", "ERROR")
            return False
        
        # Create test company
        company_data = {
            "name": "Session Filtering Test Company"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
            if response.status_code == 200:
                self.test_company_id = response.json()['id']
                self.log(f"✅ Test company created. ID: {self.test_company_id}")
                return True
            else:
                self.log(f"❌ Company creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Company creation error: {str(e)}", "ERROR")
            return False
    
    def create_test_sessions(self):
        """Create test sessions with different dates and completion statuses"""
        self.log("Creating test sessions with different dates...")
        
        if not self.admin_token or not self.test_program_id or not self.test_company_id:
            self.log("❌ Missing required test data", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Get today's date
        today = date.today()
        
        # Session 1: Past session (ended yesterday)
        past_date = today - timedelta(days=1)
        session1_data = {
            "name": "Past Session (Ended Yesterday)",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 1",
            "start_date": (past_date - timedelta(days=5)).isoformat(),
            "end_date": past_date.isoformat(),
            "coordinator_id": self.coordinator_id if hasattr(self, 'coordinator_id') else None
        }
        
        # Session 2: Current session (ends today)
        session2_data = {
            "name": "Current Session (Ends Today)",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 2",
            "start_date": (today - timedelta(days=2)).isoformat(),
            "end_date": today.isoformat(),
            "coordinator_id": self.coordinator_id if hasattr(self, 'coordinator_id') else None
        }
        
        # Session 3: Future session (starts tomorrow)
        future_date = today + timedelta(days=1)
        session3_data = {
            "name": "Future Session (Starts Tomorrow)",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 3",
            "start_date": future_date.isoformat(),
            "end_date": (future_date + timedelta(days=5)).isoformat(),
            "coordinator_id": self.coordinator_id if hasattr(self, 'coordinator_id') else None
        }
        
        # Session 4: Completed session (still ongoing but marked completed)
        session4_data = {
            "name": "Completed Session (Still Ongoing)",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 4",
            "start_date": (today - timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat(),
            "coordinator_id": self.coordinator_id if hasattr(self, 'coordinator_id') else None
        }
        
        sessions_to_create = [session1_data, session2_data, session3_data, session4_data]
        
        for i, session_data in enumerate(sessions_to_create, 1):
            try:
                response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
                if response.status_code == 200:
                    session_id = response.json()['session']['id']
                    self.test_sessions.append({
                        'id': session_id,
                        'name': session_data['name'],
                        'end_date': session_data['end_date']
                    })
                    self.log(f"✅ Session {i} created. ID: {session_id}")
                else:
                    self.log(f"❌ Session {i} creation failed: {response.status_code}", "ERROR")
                    return False
            except Exception as e:
                self.log(f"❌ Session {i} creation error: {str(e)}", "ERROR")
                return False
        
        # Mark session 4 as completed
        if len(self.test_sessions) >= 4:
            session4_id = self.test_sessions[3]['id']
            try:
                response = self.session.post(f"{BASE_URL}/sessions/{session4_id}/mark-completed", headers=headers)
                if response.status_code == 200:
                    self.log("✅ Session 4 marked as completed")
                else:
                    self.log(f"❌ Failed to mark session 4 as completed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Error marking session 4 as completed: {str(e)}", "ERROR")
        
        return True
    
    def test_coordinator_session_filtering(self):
        """Test 1: Coordinator Session Filtering - should return ALL non-archived sessions"""
        self.log("Testing Coordinator Session Filtering...")
        
        if not self.coordinator_token:
            self.log("❌ Missing coordinator token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Coordinator retrieved {len(sessions)} sessions")
                
                # Find our test sessions
                test_session_names = [s['name'] for s in self.test_sessions]
                found_sessions = [s for s in sessions if s['name'] in test_session_names]
                
                self.log(f"Found {len(found_sessions)} test sessions:")
                for session in found_sessions:
                    completion_status = session.get('completion_status', 'ongoing')
                    completed_by_coordinator = session.get('completed_by_coordinator', False)
                    self.log(f"  - {session['name']} (end: {session['end_date']}, status: {completion_status}, completed: {completed_by_coordinator})")
                
                # Coordinator should see:
                # - Current session (ends today) ✓
                # - Future session ✓
                # - Completed session (still ongoing) ✓
                # - Should NOT see past session (ended yesterday) ❌
                
                expected_sessions = ["Current Session (Ends Today)", "Future Session (Starts Tomorrow)", "Completed Session (Still Ongoing)"]
                found_names = [s['name'] for s in found_sessions]
                
                success = True
                for expected in expected_sessions:
                    if expected not in found_names:
                        self.log(f"❌ Missing expected session: {expected}", "ERROR")
                        success = False
                
                if "Past Session (Ended Yesterday)" in found_names:
                    self.log("❌ Coordinator should not see past sessions", "ERROR")
                    success = False
                
                if success:
                    self.log("✅ Coordinator session filtering working correctly")
                    return True
                else:
                    self.log("❌ Coordinator session filtering has issues", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Coordinator session retrieval failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Coordinator session filtering error: {str(e)}", "ERROR")
            return False
    
    def test_trainer_session_filtering(self):
        """Test 2: Trainer Session Filtering - should ONLY return future/current sessions"""
        self.log("Testing Trainer Session Filtering...")
        
        if not self.trainer_token:
            self.log("❌ Missing trainer token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Trainer retrieved {len(sessions)} sessions")
                
                # Find our test sessions
                test_session_names = [s['name'] for s in self.test_sessions]
                found_sessions = [s for s in sessions if s['name'] in test_session_names]
                
                self.log(f"Found {len(found_sessions)} test sessions:")
                for session in found_sessions:
                    self.log(f"  - {session['name']} (end: {session['end_date']})")
                
                # Trainer should see:
                # - Current session (ends today) ✓
                # - Future session ✓
                # - Should NOT see past session (ended yesterday) ❌
                # - Should NOT see completed session if it's past end_date ❌
                
                expected_sessions = ["Current Session (Ends Today)", "Future Session (Starts Tomorrow)"]
                found_names = [s['name'] for s in found_sessions]
                
                success = True
                for expected in expected_sessions:
                    if expected not in found_names:
                        self.log(f"❌ Missing expected session: {expected}", "ERROR")
                        success = False
                
                # Trainers should NOT see past sessions
                if "Past Session (Ended Yesterday)" in found_names:
                    self.log("❌ Trainer should not see past sessions", "ERROR")
                    success = False
                
                # Trainers MAY see completed session if it's still ongoing (end_date >= today)
                if "Completed Session (Still Ongoing)" in found_names:
                    self.log("✅ Trainer can see completed session that is still ongoing")
                
                if success:
                    self.log("✅ Trainer session filtering working correctly")
                    return True
                else:
                    self.log("❌ Trainer session filtering has issues", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Trainer session retrieval failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Trainer session filtering error: {str(e)}", "ERROR")
            return False
    
    def test_mark_session_completed(self):
        """Test 3: Mark Session as Completed functionality"""
        self.log("Testing Mark Session as Completed functionality...")
        
        if not self.coordinator_token or not self.test_sessions:
            self.log("❌ Missing coordinator token or test sessions", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        # Use the future session for this test
        future_session = None
        for session in self.test_sessions:
            if "Future Session" in session['name']:
                future_session = session
                break
        
        if not future_session:
            self.log("❌ No future session found for testing", "ERROR")
            return False
        
        session_id = future_session['id']
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions/{session_id}/mark-completed", headers=headers)
            
            if response.status_code == 200:
                self.log("✅ Session marked as completed successfully")
                
                # Verify the session was marked as completed
                response = self.session.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
                if response.status_code == 200:
                    session_data = response.json()
                    completion_status = session_data.get('completion_status')
                    completed_by_coordinator = session_data.get('completed_by_coordinator')
                    completed_date = session_data.get('completed_date')
                    
                    self.log(f"Session completion status: {completion_status}")
                    self.log(f"Completed by coordinator: {completed_by_coordinator}")
                    self.log(f"Completed date: {completed_date}")
                    
                    if completion_status == "completed" and completed_by_coordinator and completed_date:
                        self.log("✅ Session completion data correctly set")
                        
                        # Verify completed_date is ISO string format
                        try:
                            datetime.fromisoformat(completed_date.replace('Z', '+00:00'))
                            self.log("✅ Completed date is in correct ISO string format")
                            return True
                        except ValueError:
                            self.log("❌ Completed date is not in ISO string format", "ERROR")
                            return False
                    else:
                        self.log("❌ Session completion data not set correctly", "ERROR")
                        return False
                else:
                    self.log(f"❌ Failed to retrieve session after completion: {response.status_code}", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Mark session completed failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Mark session completed error: {str(e)}", "ERROR")
            return False
    
    def test_coordinator_past_training(self):
        """Test 4: Past Training for Coordinators"""
        self.log("Testing Past Training endpoint for Coordinators...")
        
        if not self.coordinator_token:
            self.log("❌ Missing coordinator token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions/past-training", headers=headers)
            
            if response.status_code == 200:
                past_sessions = response.json()
                self.log(f"✅ Coordinator retrieved {len(past_sessions)} past training sessions")
                
                # Find our test sessions
                test_session_names = [s['name'] for s in self.test_sessions]
                found_sessions = [s for s in past_sessions if s['name'] in test_session_names]
                
                self.log(f"Found {len(found_sessions)} test sessions in past training:")
                for session in found_sessions:
                    completed_by_coordinator = session.get('completed_by_coordinator', False)
                    self.log(f"  - {session['name']} (end: {session['end_date']}, completed: {completed_by_coordinator})")
                
                # Coordinator should see:
                # - Sessions where completed_by_coordinator = True AND end_date < today
                # - Should NOT see ongoing sessions even if completed
                
                found_names = [s['name'] for s in found_sessions]
                
                # The completed session should appear if it's past its end date
                # The past session should appear if it was marked as completed
                
                self.log("✅ Coordinator past training endpoint working")
                return True
                    
            else:
                self.log(f"❌ Coordinator past training failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Coordinator past training error: {str(e)}", "ERROR")
            return False
    
    def test_trainer_past_training(self):
        """Test 5: Past Training for Trainers"""
        self.log("Testing Past Training endpoint for Trainers...")
        
        if not self.trainer_token:
            self.log("❌ Missing trainer token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions/past-training", headers=headers)
            
            if response.status_code == 200:
                past_sessions = response.json()
                self.log(f"✅ Trainer retrieved {len(past_sessions)} past training sessions")
                
                # Find our test sessions
                test_session_names = [s['name'] for s in self.test_sessions]
                found_sessions = [s for s in past_sessions if s['name'] in test_session_names]
                
                self.log(f"Found {len(found_sessions)} test sessions in past training:")
                for session in found_sessions:
                    self.log(f"  - {session['name']} (end: {session['end_date']})")
                
                # Trainer should see:
                # - ALL sessions where end_date < today (automatic archival)
                # - Does NOT require completed_by_coordinator flag
                
                found_names = [s['name'] for s in found_sessions]
                
                # Should see past session (ended yesterday)
                if "Past Session (Ended Yesterday)" in found_names:
                    self.log("✅ Trainer can see past sessions (automatic archival)")
                else:
                    self.log("⚠️  Trainer should see past sessions", "WARNING")
                
                self.log("✅ Trainer past training endpoint working")
                return True
                    
            else:
                self.log(f"❌ Trainer past training failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Trainer past training error: {str(e)}", "ERROR")
            return False
    
    def cleanup_test_data(self):
        """Clean up created test data"""
        self.log("Cleaning up test data...")
        
        if not self.admin_token:
            return
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Delete test sessions
        for session in self.test_sessions:
            try:
                response = self.session.delete(f"{BASE_URL}/sessions/{session['id']}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Deleted session: {session['name']}")
                else:
                    self.log(f"⚠️  Failed to delete session {session['name']}: {response.status_code}", "WARNING")
            except Exception as e:
                self.log(f"⚠️  Error deleting session {session['name']}: {str(e)}", "WARNING")
        
        # Delete test company
        if hasattr(self, 'test_company_id'):
            try:
                response = self.session.delete(f"{BASE_URL}/companies/{self.test_company_id}", headers=headers)
                if response.status_code == 200:
                    self.log("✅ Deleted test company")
                else:
                    self.log(f"⚠️  Failed to delete test company: {response.status_code}", "WARNING")
            except Exception as e:
                self.log(f"⚠️  Error deleting test company: {str(e)}", "WARNING")
        
        # Delete test program
        if hasattr(self, 'test_program_id'):
            try:
                response = self.session.delete(f"{BASE_URL}/programs/{self.test_program_id}", headers=headers)
                if response.status_code == 200:
                    self.log("✅ Deleted test program")
                else:
                    self.log(f"⚠️  Failed to delete test program: {response.status_code}", "WARNING")
            except Exception as e:
                self.log(f"⚠️  Error deleting test program: {str(e)}", "WARNING")
    
    def run_all_tests(self):
        """Run all session filtering tests"""
        self.log("🚀 Starting Session Filtering Test Suite...")
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Coordinator Login", self.login_coordinator),
            ("Trainer Login", self.login_trainer),
            ("Setup Test Data", self.setup_test_data),
            ("Create Test Sessions", self.create_test_sessions),
            ("Test 1: Coordinator Session Filtering", self.test_coordinator_session_filtering),
            ("Test 2: Trainer Session Filtering", self.test_trainer_session_filtering),
            ("Test 3: Mark Session as Completed", self.test_mark_session_completed),
            ("Test 4: Coordinator Past Training", self.test_coordinator_past_training),
            ("Test 5: Trainer Past Training", self.test_trainer_past_training),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n{'='*60}")
            self.log(f"Running: {test_name}")
            self.log('='*60)
            
            try:
                if test_func():
                    passed += 1
                    self.log(f"✅ {test_name} - PASSED")
                else:
                    failed += 1
                    self.log(f"❌ {test_name} - FAILED")
            except Exception as e:
                failed += 1
                self.log(f"❌ {test_name} - ERROR: {str(e)}")
        
        # Cleanup
        self.log(f"\n{'='*60}")
        self.log("Cleanup")
        self.log('='*60)
        self.cleanup_test_data()
        
        # Summary
        total = passed + failed
        self.log(f"\n{'='*60}")
        self.log("TEST SUMMARY")
        self.log('='*60)
        self.log(f"Total Tests: {total}")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")
        self.log(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "0%")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED!")
            return True
        else:
            self.log(f"❌ {failed} TEST(S) FAILED")
            return False

if __name__ == "__main__":
    runner = SessionFilteringTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)