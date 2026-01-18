#!/usr/bin/env python3
"""
Attendance Records Display Issue Testing
Testing the stuck task: "Attendance records display issue"
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://financeflow-209.preview.emergentagent.com/api"

class AttendanceDisplayTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.admin_token = None
        self.coordinator_token = None
        self.participant_token = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_admin(self):
        """Login as admin"""
        login_data = {"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            self.admin_token = response.json()['access_token']
            self.log("✅ Admin login successful")
            return True
        else:
            self.log(f"❌ Admin login failed: {response.status_code}", "ERROR")
            return False
    
    def login_coordinator(self):
        """Login as coordinator"""
        login_data = {"email": "malek@mddrc.com.my", "password": "mddrc1"}
        response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            self.coordinator_token = response.json()['access_token']
            self.log("✅ Coordinator login successful")
            return True
        else:
            self.log(f"❌ Coordinator login failed: {response.status_code}", "ERROR")
            return False
    
    def login_participant(self):
        """Login as participant"""
        login_data = {"email": "566589", "password": "mddrc1"}
        response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.participant_token = data['access_token']
            self.participant_id = data['user']['id']
            self.log(f"✅ Participant login successful: {data['user']['full_name']}")
            return True
        else:
            self.log(f"❌ Participant login failed: {response.status_code}", "ERROR")
            return False
    
    def get_headers(self, role):
        """Get headers for API calls"""
        tokens = {
            'admin': self.admin_token,
            'coordinator': self.coordinator_token,
            'participant': self.participant_token
        }
        
        if tokens[role]:
            return {'Authorization': f'Bearer {tokens[role]}'}
        return {}
    
    def test_attendance_flow(self):
        """Test complete attendance flow"""
        self.log("🕐 TESTING ATTENDANCE RECORDS DISPLAY ISSUE")
        self.log("=" * 60)
        
        # Login all users
        if not (self.login_admin() and self.login_coordinator() and self.login_participant()):
            self.log("❌ Failed to login required users", "ERROR")
            return False
        
        # Get a session to test with
        sessions_response = self.session.get(f"{BASE_URL}/sessions", headers=self.get_headers('admin'))
        if sessions_response.status_code != 200:
            self.log("❌ Cannot get sessions", "ERROR")
            return False
        
        sessions = sessions_response.json()
        if not sessions:
            self.log("❌ No sessions available for testing", "ERROR")
            return False
        
        session_id = sessions[0]['id']
        self.log(f"📋 Testing with session: {session_id}")
        
        # Test 1: Participant Clock-In
        self.log("\n1️⃣ Testing Participant Clock-In")
        clock_in_data = {"session_id": session_id}
        
        clock_in_response = self.session.post(f"{BASE_URL}/attendance/clock-in", 
                                            json=clock_in_data, 
                                            headers=self.get_headers('participant'))
        
        if clock_in_response.status_code == 200:
            self.log("✅ Participant clock-in successful")
            clock_in_result = clock_in_response.json()
            attendance_id = clock_in_result.get('id')
            self.log(f"   Attendance ID: {attendance_id}")
        else:
            self.log(f"❌ Participant clock-in failed: {clock_in_response.status_code} - {clock_in_response.text}", "ERROR")
            return False
        
        # Test 2: Participant Clock-Out
        self.log("\n2️⃣ Testing Participant Clock-Out")
        clock_out_data = {"session_id": session_id}
        
        clock_out_response = self.session.post(f"{BASE_URL}/attendance/clock-out", 
                                             json=clock_out_data, 
                                             headers=self.get_headers('participant'))
        
        if clock_out_response.status_code == 200:
            self.log("✅ Participant clock-out successful")
        else:
            self.log(f"❌ Participant clock-out failed: {clock_out_response.status_code} - {clock_out_response.text}", "ERROR")
        
        # Test 3: Individual Attendance Query (should work)
        self.log("\n3️⃣ Testing Individual Attendance Query")
        individual_response = self.session.get(f"{BASE_URL}/attendance/{session_id}/{self.participant_id}", 
                                             headers=self.get_headers('coordinator'))
        
        if individual_response.status_code == 200:
            individual_data = individual_response.json()
            self.log(f"✅ Individual attendance query successful: {len(individual_data)} records")
            for record in individual_data:
                self.log(f"   Record: {record.get('date')} - Clock-in: {record.get('clock_in')} - Clock-out: {record.get('clock_out')}")
        else:
            self.log(f"❌ Individual attendance query failed: {individual_response.status_code}", "ERROR")
        
        # Test 4: Session-Level Attendance Display (the problematic one)
        self.log("\n4️⃣ Testing Session-Level Attendance Display (THE ISSUE)")
        session_attendance_response = self.session.get(f"{BASE_URL}/attendance/session/{session_id}", 
                                                     headers=self.get_headers('coordinator'))
        
        if session_attendance_response.status_code == 200:
            session_attendance_data = session_attendance_response.json()
            self.log(f"📊 Session-level attendance query result: {len(session_attendance_data)} records")
            
            if len(session_attendance_data) == 0:
                self.log("❌ CRITICAL ISSUE CONFIRMED: Session-level attendance returns 0 records despite individual records existing", "ERROR")
                
                # Let's investigate the database directly by checking what the API is doing
                self.log("\n🔍 INVESTIGATING THE ISSUE...")
                
                # Check if the issue is in the participant enrichment logic
                self.log("   Checking participant enrichment logic...")
                
                # Get session participants
                participants_response = self.session.get(f"{BASE_URL}/sessions/{session_id}/participants", 
                                                       headers=self.get_headers('admin'))
                
                if participants_response.status_code == 200:
                    participants = participants_response.json()
                    self.log(f"   Session has {len(participants)} participants")
                    
                    # Check if our test participant is in the session
                    participant_in_session = False
                    for participant in participants:
                        if participant['user']['id'] == self.participant_id:
                            participant_in_session = True
                            self.log(f"   ✅ Test participant found in session: {participant['user']['full_name']}")
                            break
                    
                    if not participant_in_session:
                        self.log("   ❌ Test participant NOT found in session - this could be the issue!", "ERROR")
                        
                        # Add participant to session
                        self.log("   🔧 Adding participant to session...")
                        add_participant_data = {"participant_ids": [self.participant_id]}
                        add_response = self.session.post(f"{BASE_URL}/sessions/{session_id}/participants", 
                                                       json=add_participant_data, 
                                                       headers=self.get_headers('admin'))
                        
                        if add_response.status_code == 200:
                            self.log("   ✅ Participant added to session")
                            
                            # Retry session-level attendance query
                            self.log("   🔄 Retrying session-level attendance query...")
                            retry_response = self.session.get(f"{BASE_URL}/attendance/session/{session_id}", 
                                                            headers=self.get_headers('coordinator'))
                            
                            if retry_response.status_code == 200:
                                retry_data = retry_response.json()
                                self.log(f"   📊 Retry result: {len(retry_data)} records")
                                
                                if len(retry_data) > 0:
                                    self.log("   ✅ ISSUE RESOLVED: Session-level attendance now returns records!")
                                    for record in retry_data:
                                        participant_name = record.get('participant_name', 'Unknown')
                                        clock_in = record.get('clock_in', 'N/A')
                                        clock_out = record.get('clock_out', 'N/A')
                                        self.log(f"      {participant_name}: {clock_in} - {clock_out}")
                                    return True
                                else:
                                    self.log("   ❌ Issue still persists after adding participant to session", "ERROR")
                        else:
                            self.log(f"   ❌ Failed to add participant to session: {add_response.status_code}", "ERROR")
                else:
                    self.log(f"   ❌ Cannot get session participants: {participants_response.status_code}", "ERROR")
                
                return False
            else:
                self.log("✅ Session-level attendance working correctly")
                for record in session_attendance_data:
                    participant_name = record.get('participant_name', 'Unknown')
                    clock_in = record.get('clock_in', 'N/A')
                    clock_out = record.get('clock_out', 'N/A')
                    self.log(f"   {participant_name}: {clock_in} - {clock_out}")
                return True
        else:
            self.log(f"❌ Session-level attendance query failed: {session_attendance_response.status_code}", "ERROR")
            return False
    
    def test_supervisor_attendance_access(self):
        """Test supervisor access to attendance records"""
        self.log("\n👔 Testing Supervisor Attendance Access")
        
        # Try to create a supervisor user for testing
        if not self.admin_token:
            self.log("❌ No admin token for supervisor creation", "ERROR")
            return False
        
        supervisor_data = {
            "email": "test.supervisor@mddrc.com.my",
            "password": "mddrc1",
            "full_name": "Test Supervisor",
            "id_number": "SUP001",
            "role": "supervisor"
        }
        
        create_response = self.session.post(f"{BASE_URL}/auth/register", 
                                          json=supervisor_data, 
                                          headers=self.get_headers('admin'))
        
        if create_response.status_code == 200 or (create_response.status_code == 400 and "already exists" in create_response.text):
            # Login as supervisor
            supervisor_login = {"email": "test.supervisor@mddrc.com.my", "password": "mddrc1"}
            login_response = self.session.post(f"{BASE_URL}/auth/login", json=supervisor_login)
            
            if login_response.status_code == 200:
                supervisor_token = login_response.json()['access_token']
                supervisor_headers = {'Authorization': f'Bearer {supervisor_token}'}
                
                # Test supervisor access to attendance
                sessions_response = self.session.get(f"{BASE_URL}/sessions", headers=supervisor_headers)
                if sessions_response.status_code == 200:
                    sessions = sessions_response.json()
                    if sessions:
                        session_id = sessions[0]['id']
                        attendance_response = self.session.get(f"{BASE_URL}/attendance/session/{session_id}", 
                                                             headers=supervisor_headers)
                        
                        if attendance_response.status_code == 200:
                            self.log("✅ Supervisor can access attendance records")
                            return True
                        else:
                            self.log(f"❌ Supervisor attendance access failed: {attendance_response.status_code}", "ERROR")
                            return False
                else:
                    self.log(f"❌ Supervisor cannot access sessions: {sessions_response.status_code}", "ERROR")
                    return False
            else:
                self.log(f"❌ Supervisor login failed: {login_response.status_code}", "ERROR")
                return False
        else:
            self.log(f"❌ Supervisor creation failed: {create_response.status_code}", "ERROR")
            return False

if __name__ == "__main__":
    tester = AttendanceDisplayTester()
    success = tester.test_attendance_flow()
    
    if success:
        print("\n🎉 ATTENDANCE TESTING COMPLETE - ISSUE RESOLVED!")
    else:
        print("\n❌ ATTENDANCE TESTING COMPLETE - ISSUE PERSISTS!")
    
    # Also test supervisor access
    tester.test_supervisor_attendance_access()