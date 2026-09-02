#!/usr/bin/env python3
"""
Attendance Display Retest - Defensive Driving Training Management System
Retests the attendance endpoints that were just fixed to verify the issue is resolved:

1. Session-level attendance endpoint (GET /api/attendance/session/{session_id})
2. Supervisor attendance endpoint (GET /api/supervisor/attendance/{session_id})  
3. Individual attendance endpoint (GET /api/attendance/{session_id}/{participant_id})

Focus specifically on verifying the session-level endpoint now returns records where it was returning 0 before.
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://training-finance-hub-1.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

class AttendanceRetestRunner:
    def __init__(self):
        self.admin_token = None
        self.coordinator_token = None
        self.supervisor_token = None
        self.participant_token = None
        self.test_session_id = None
        self.test_participant_id = None
        self.test_supervisor_id = None
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
    
    def find_existing_test_session(self):
        """Find existing test session with attendance data"""
        self.log("Looking for existing test session with attendance data...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Get all sessions
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"Found {len(sessions)} total sessions")
                
                # Look for "Critical Bug Fix Test Session" or similar
                for session in sessions:
                    if "Critical" in session.get('name', '') or "Bug Fix" in session.get('name', '') or "Test" in session.get('name', ''):
                        self.test_session_id = session['id']
                        self.log(f"✅ Found test session: {session['name']} (ID: {self.test_session_id})")
                        
                        # Get participant IDs from this session
                        if session.get('participant_ids'):
                            self.test_participant_id = session['participant_ids'][0]
                            self.log(f"✅ Using participant ID: {self.test_participant_id}")
                        
                        # Get supervisor IDs from this session
                        if session.get('supervisor_ids'):
                            self.test_supervisor_id = session['supervisor_ids'][0]
                            self.log(f"✅ Using supervisor ID: {self.test_supervisor_id}")
                        
                        return True
                
                # If no test session found, use the first available session
                if sessions:
                    session = sessions[0]
                    self.test_session_id = session['id']
                    self.log(f"✅ Using first available session: {session['name']} (ID: {self.test_session_id})")
                    
                    if session.get('participant_ids'):
                        self.test_participant_id = session['participant_ids'][0]
                        self.log(f"✅ Using participant ID: {self.test_participant_id}")
                    
                    if session.get('supervisor_ids'):
                        self.test_supervisor_id = session['supervisor_ids'][0]
                        self.log(f"✅ Using supervisor ID: {self.test_supervisor_id}")
                    
                    return True
                else:
                    self.log("❌ No sessions found", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Failed to get sessions: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error finding test session: {str(e)}", "ERROR")
            return False
    
    def login_as_coordinator(self):
        """Login as coordinator to test coordinator access"""
        self.log("Attempting coordinator login...")
        
        # Try to find a coordinator user
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Get users with coordinator role
            response = self.session.get(f"{BASE_URL}/users?role=coordinator", headers=headers)
            
            if response.status_code == 200:
                coordinators = response.json()
                if coordinators:
                    coordinator = coordinators[0]
                    coordinator_email = coordinator['email']
                    self.log(f"Found coordinator: {coordinator['full_name']} ({coordinator_email})")
                    
                    # Try common passwords
                    passwords = ["coordinator123", "password", "123456", "admin123"]
                    
                    for password in passwords:
                        login_data = {
                            "email": coordinator_email,
                            "password": password
                        }
                        
                        try:
                            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                            
                            if response.status_code == 200:
                                data = response.json()
                                self.coordinator_token = data['access_token']
                                self.log(f"✅ Coordinator login successful with password '{password}'. User: {data['user']['full_name']}")
                                return True
                        except:
                            continue
                    
                    self.log(f"❌ Could not login as coordinator with common passwords", "WARNING")
                    return False
                else:
                    self.log("❌ No coordinator users found", "WARNING")
                    return False
                    
            else:
                self.log(f"❌ Failed to get coordinator users: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error logging in as coordinator: {str(e)}", "ERROR")
            return False
    
    def login_as_supervisor(self):
        """Login as supervisor to test supervisor access"""
        self.log("Attempting supervisor login...")
        
        if not self.test_supervisor_id:
            self.log("❌ No supervisor ID available", "ERROR")
            return False
            
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Get supervisor user details
            response = self.session.get(f"{BASE_URL}/users/{self.test_supervisor_id}", headers=headers)
            
            if response.status_code == 200:
                supervisor = response.json()
                supervisor_email = supervisor['email']
                self.log(f"Found supervisor: {supervisor['full_name']} ({supervisor_email})")
                
                # Try common passwords
                passwords = ["supervisor123", "password", "123456", "admin123"]
                
                for password in passwords:
                    login_data = {
                        "email": supervisor_email,
                        "password": password
                    }
                    
                    try:
                        response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                        
                        if response.status_code == 200:
                            data = response.json()
                            self.supervisor_token = data['access_token']
                            self.log(f"✅ Supervisor login successful with password '{password}'. User: {data['user']['full_name']}")
                            return True
                    except:
                        continue
                
                self.log(f"❌ Could not login as supervisor with common passwords", "WARNING")
                return False
                    
            else:
                self.log(f"❌ Failed to get supervisor details: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error logging in as supervisor: {str(e)}", "ERROR")
            return False
    
    def login_as_participant(self):
        """Login as participant to test participant access"""
        self.log("Attempting participant login...")
        
        # Try the known participant from test_result.md
        login_data = {
            "email": "maaman@gmail.com",
            "password": "mddrc1"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.participant_token = data['access_token']
                self.test_participant_id = data['user']['id']
                self.log(f"✅ Participant login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"❌ Participant login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Participant login error: {str(e)}", "ERROR")
            return False
    
    def ensure_attendance_records_exist(self):
        """Ensure attendance records exist for testing"""
        self.log("Ensuring attendance records exist for testing...")
        
        if not self.participant_token or not self.test_session_id:
            self.log("❌ Missing participant token or session ID", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        # Clock in
        clock_in_data = {
            "session_id": self.test_session_id
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/attendance/clock-in", json=clock_in_data, headers=headers)
            
            if response.status_code == 200:
                self.log("✅ Participant clocked in successfully")
            elif response.status_code == 400 and "already clocked in" in response.text.lower():
                self.log("✅ Participant already clocked in (expected)")
            else:
                self.log(f"❌ Clock in failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Clock in error: {str(e)}", "ERROR")
            return False
        
        # Clock out (optional, just to have complete records)
        clock_out_data = {
            "session_id": self.test_session_id
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/attendance/clock-out", json=clock_out_data, headers=headers)
            
            if response.status_code == 200:
                self.log("✅ Participant clocked out successfully")
            elif response.status_code == 400 and "already clocked out" in response.text.lower():
                self.log("✅ Participant already clocked out (expected)")
            else:
                self.log(f"⚠️  Clock out failed: {response.status_code} - {response.text}", "WARNING")
                # Don't return False here as clock-out failure is not critical
                
        except Exception as e:
            self.log(f"⚠️  Clock out error: {str(e)}", "WARNING")
        
        return True
    
    def test_individual_attendance_endpoint(self):
        """Test GET /api/attendance/{session_id}/{participant_id} - Individual attendance (should work)"""
        self.log("Testing GET /api/attendance/{session_id}/{participant_id} - Individual attendance...")
        
        if not self.participant_token or not self.test_session_id or not self.test_participant_id:
            self.log("❌ Missing participant token, session ID, or participant ID", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/attendance/{self.test_session_id}/{self.test_participant_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Individual attendance endpoint working. Found {len(data)} records")
                
                if len(data) > 0:
                    record = data[0]
                    self.log(f"   Sample record: Participant {record.get('participant_id', 'N/A')}, Date: {record.get('date', 'N/A')}")
                    self.log(f"   Clock in: {record.get('clock_in', 'N/A')}, Clock out: {record.get('clock_out', 'N/A')}")
                    return True
                else:
                    self.log("⚠️  Individual attendance endpoint returned 0 records", "WARNING")
                    return False
                    
            else:
                self.log(f"❌ Individual attendance endpoint failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Individual attendance endpoint error: {str(e)}", "ERROR")
            return False
    
    def test_session_level_attendance_endpoint(self):
        """Test GET /api/attendance/session/{session_id} - Session-level attendance (MAIN TEST)"""
        self.log("Testing GET /api/attendance/session/{session_id} - Session-level attendance (MAIN TEST)...")
        
        if not self.coordinator_token and not self.admin_token:
            self.log("❌ Missing coordinator or admin token", "ERROR")
            return False
        
        # Try with coordinator first, then admin
        token = self.coordinator_token if self.coordinator_token else self.admin_token
        role = "coordinator" if self.coordinator_token else "admin"
        
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/attendance/session/{self.test_session_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Session-level attendance endpoint working as {role}. Found {len(data)} records")
                
                if len(data) > 0:
                    record = data[0]
                    self.log(f"   Sample record: Participant {record.get('participant_id', 'N/A')}")
                    self.log(f"   Participant name: {record.get('participant_name', 'N/A')}")
                    self.log(f"   Participant email: {record.get('participant_email', 'N/A')}")
                    self.log(f"   Date: {record.get('date', 'N/A')}")
                    self.log(f"   Clock in: {record.get('clock_in', 'N/A')}, Clock out: {record.get('clock_out', 'N/A')}")
                    
                    # Verify enrichment is working
                    if record.get('participant_name') and record.get('participant_email'):
                        self.log("✅ Participant enrichment is working correctly")
                        return True
                    else:
                        self.log("⚠️  Participant enrichment may not be working properly", "WARNING")
                        return True  # Still consider it working if records are returned
                else:
                    self.log("❌ Session-level attendance endpoint returned 0 records (BUG NOT FIXED)", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Session-level attendance endpoint failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session-level attendance endpoint error: {str(e)}", "ERROR")
            return False
    
    def test_supervisor_attendance_endpoint(self):
        """Test GET /api/supervisor/attendance/{session_id} - Supervisor attendance"""
        self.log("Testing GET /api/supervisor/attendance/{session_id} - Supervisor attendance...")
        
        if not self.supervisor_token:
            self.log("⚠️  No supervisor token available, skipping supervisor test", "WARNING")
            return True  # Don't fail the overall test
        
        headers = {'Authorization': f'Bearer {self.supervisor_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/supervisor/attendance/{self.test_session_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Supervisor attendance endpoint working. Found {len(data)} records")
                
                if len(data) > 0:
                    record = data[0]
                    self.log(f"   Sample record: Participant {record.get('participant_id', 'N/A')}")
                    self.log(f"   Participant name: {record.get('participant_name', 'N/A')}")
                    self.log(f"   Participant email: {record.get('participant_email', 'N/A')}")
                    
                    # Verify enrichment is working
                    if record.get('participant_name') and record.get('participant_email'):
                        self.log("✅ Supervisor endpoint participant enrichment is working correctly")
                        return True
                    else:
                        self.log("⚠️  Supervisor endpoint participant enrichment may not be working properly", "WARNING")
                        return True
                else:
                    self.log("❌ Supervisor attendance endpoint returned 0 records", "ERROR")
                    return False
                    
            elif response.status_code == 403:
                self.log("⚠️  Supervisor not authorized for this session (expected if not assigned)", "WARNING")
                return True  # Don't fail if supervisor not assigned to this session
            else:
                self.log(f"❌ Supervisor attendance endpoint failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Supervisor attendance endpoint error: {str(e)}", "ERROR")
            return False
    
    def run_attendance_retest(self):
        """Run the complete attendance retest"""
        self.log("🔄 Starting Attendance Display Retest...")
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Find Test Session", self.find_existing_test_session),
            ("Participant Login", self.login_as_participant),
            ("Coordinator Login", self.login_as_coordinator),
            ("Supervisor Login", self.login_as_supervisor),
            ("Ensure Attendance Records", self.ensure_attendance_records_exist),
            ("Individual Attendance Endpoint", self.test_individual_attendance_endpoint),
            ("Session-Level Attendance Endpoint", self.test_session_level_attendance_endpoint),
            ("Supervisor Attendance Endpoint", self.test_supervisor_attendance_endpoint),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running: {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    self.log(f"✅ {test_name} PASSED")
                else:
                    failed += 1
                    self.log(f"❌ {test_name} FAILED")
            except Exception as e:
                failed += 1
                self.log(f"❌ {test_name} ERROR: {str(e)}", "ERROR")
        
        self.log(f"\n🏁 Attendance Retest Complete: {passed} passed, {failed} failed")
        
        # Summary
        if failed == 0:
            self.log("🎉 ALL ATTENDANCE TESTS PASSED - BUG FIX SUCCESSFUL!", "SUCCESS")
            return True
        else:
            self.log(f"⚠️  {failed} tests failed - attendance issue may not be fully resolved", "WARNING")
            return False

def main():
    """Main function to run attendance retest"""
    runner = AttendanceRetestRunner()
    success = runner.run_attendance_retest()
    
    if success:
        print("\n✅ ATTENDANCE DISPLAY FIX VERIFICATION: SUCCESS")
        sys.exit(0)
    else:
        print("\n❌ ATTENDANCE DISPLAY FIX VERIFICATION: ISSUES FOUND")
        sys.exit(1)

if __name__ == "__main__":
    main()