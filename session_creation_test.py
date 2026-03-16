#!/usr/bin/env python3
"""
Session Creation Test Suite for Defensive Driving Training Management System
Tests session creation functionality with admin credentials as requested:
- Test Case 1: Create a Simple Session
- Test Case 2: Verify Session Appears in List
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://hr-dispatcher-v2.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

class SessionCreationTestRunner:
    def __init__(self):
        self.admin_token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.created_session_id = None
        self.first_program_id = None
        self.first_company_id = None
        
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
    
    def get_first_program_id(self):
        """Get the first program ID from /programs endpoint"""
        self.log("Getting first program ID...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/programs", headers=headers)
            
            if response.status_code == 200:
                programs = response.json()
                if programs:
                    self.first_program_id = programs[0]['id']
                    self.log(f"✅ First program ID retrieved: {self.first_program_id}")
                    self.log(f"   Program Name: {programs[0]['name']}")
                    return True
                else:
                    self.log("❌ No programs found", "ERROR")
                    return False
            else:
                self.log(f"❌ Get programs failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get programs error: {str(e)}", "ERROR")
            return False
    
    def get_first_company_id(self):
        """Get the first company ID from /companies endpoint"""
        self.log("Getting first company ID...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/companies", headers=headers)
            
            if response.status_code == 200:
                companies = response.json()
                if companies:
                    self.first_company_id = companies[0]['id']
                    self.log(f"✅ First company ID retrieved: {self.first_company_id}")
                    self.log(f"   Company Name: {companies[0]['name']}")
                    return True
                else:
                    self.log("❌ No companies found", "ERROR")
                    return False
            else:
                self.log(f"❌ Get companies failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get companies error: {str(e)}", "ERROR")
            return False
    
    def test_create_simple_session(self):
        """Test Case 1: Create a Simple Session"""
        self.log("=== TEST CASE 1: Create a Simple Session ===")
        
        if not self.admin_token or not self.first_program_id or not self.first_company_id:
            self.log("❌ Missing admin token, program ID, or company ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Session data as specified in the request
        session_data = {
            "name": "Test Session Creation",
            "program_id": self.first_program_id,
            "company_id": self.first_company_id,
            "location": "Test Location",
            "start_date": "2025-12-01",
            "end_date": "2025-12-05",
            "participant_ids": [],
            "participants": [
                {
                    "full_name": "Test Participant",
                    "id_number": "990101-01-1234",
                    "email": f"testparticipant{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
                    "password": "mddrc1",
                    "phone_number": ""
                }
            ],
            "supervisor_ids": [],
            "supervisors": [],
            "trainer_assignments": [],
            "coordinator_id": None
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.created_session_id = data['session']['id']
                self.log(f"✅ Session created successfully!")
                self.log(f"   Session ID: {self.created_session_id}")
                self.log(f"   Session Name: {data['session']['name']}")
                self.log(f"   Program ID: {data['session']['program_id']}")
                self.log(f"   Company ID: {data['session']['company_id']}")
                self.log(f"   Location: {data['session']['location']}")
                self.log(f"   Start Date: {data['session']['start_date']}")
                self.log(f"   End Date: {data['session']['end_date']}")
                
                # Check completion_status and completed_by_coordinator
                completion_status = data['session'].get('completion_status', 'N/A')
                completed_by_coordinator = data['session'].get('completed_by_coordinator', 'N/A')
                
                self.log(f"   Completion Status: {completion_status}")
                self.log(f"   Completed by Coordinator: {completed_by_coordinator}")
                
                # Verify expected values
                if completion_status == "ongoing":
                    self.log("✅ Completion status is 'ongoing' as expected")
                else:
                    self.log(f"⚠️  Expected completion_status='ongoing', got '{completion_status}'", "WARNING")
                
                if completed_by_coordinator == False:
                    self.log("✅ Completed by coordinator is False as expected")
                else:
                    self.log(f"⚠️  Expected completed_by_coordinator=False, got '{completed_by_coordinator}'", "WARNING")
                
                # Check participant results
                if 'participant_results' in data:
                    self.log(f"   Participant Results: {len(data['participant_results'])} participants processed")
                    for i, participant in enumerate(data['participant_results']):
                        self.log(f"     Participant {i+1}: {participant['name']} (existing: {participant['is_existing']})")
                
                return True
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def test_verify_session_in_list(self):
        """Test Case 2: Verify Session Appears in List"""
        self.log("=== TEST CASE 2: Verify Session Appears in List ===")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Sessions list retrieved successfully. Total sessions: {len(sessions)}")
                
                # Look for our created session
                created_session = None
                for session in sessions:
                    if session['id'] == self.created_session_id:
                        created_session = session
                        break
                
                if created_session:
                    self.log("✅ Newly created session appears in the list!")
                    self.log(f"   Found Session: {created_session['name']}")
                    self.log(f"   Session ID: {created_session['id']}")
                    self.log(f"   Location: {created_session['location']}")
                    self.log(f"   Start Date: {created_session['start_date']}")
                    self.log(f"   End Date: {created_session['end_date']}")
                    return True
                else:
                    self.log("❌ Newly created session NOT found in sessions list", "ERROR")
                    self.log(f"   Looking for session ID: {self.created_session_id}")
                    self.log(f"   Available session IDs: {[s['id'] for s in sessions[:5]]}")  # Show first 5
                    return False
                    
            else:
                self.log(f"❌ Get sessions failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get sessions error: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all session creation tests"""
        self.log("🚀 Starting Session Creation Test Suite")
        self.log("=" * 60)
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Get First Program ID", self.get_first_program_id),
            ("Get First Company ID", self.get_first_company_id),
            ("Create Simple Session", self.test_create_simple_session),
            ("Verify Session in List", self.test_verify_session_in_list),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n🧪 Running: {test_name}")
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
        
        self.log("\n" + "=" * 60)
        self.log(f"🏁 Session Creation Test Suite Complete")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED!")
            return True
        else:
            self.log("⚠️  Some tests failed. Check the logs above for details.")
            return False

def main():
    """Main function to run the session creation tests"""
    runner = SessionCreationTestRunner()
    success = runner.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()