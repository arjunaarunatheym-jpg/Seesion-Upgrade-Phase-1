#!/usr/bin/env python3
"""
Backend Test Suite for Defensive Driving Training Management System - Participant Session Assignment Testing
Tests the participant session assignment workflow after refactoring:
- Participant Session Retrieval (GET /api/sessions)
- Session Details with Participant Access (GET /api/sessions/{session_id})
- Participant Access Endpoints
- Test Availability for Participants (GET /api/sessions/{session_id}/tests/available)
- Certificate Access (GET /api/certificates/my-certificates)
- Database verification for participant_access records
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://finance-correction.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
PARTICIPANT_IC = "566589"
PARTICIPANT_PASSWORD = "mddrc1"

class ParticipantSessionTestRunner:
    def __init__(self):
        self.admin_token = None
        self.participant_token = None
        self.participant_id = None
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
    
    def login_participant_566589(self):
        """Login as participant 566589 and get authentication token"""
        self.log("Attempting participant 566589 login...")
        
        login_data = {
            "email": PARTICIPANT_IC,
            "password": PARTICIPANT_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.participant_token = data['access_token']
                self.participant_id = data['user']['id']
                self.log(f"✅ Participant login successful. User: {data['user']['full_name']} (ID: {data['user']['id']})")
                self.log(f"   IC Number: {data['user'].get('id_number', 'N/A')}")
                self.log(f"   Role: {data['user']['role']}")
                return True
            else:
                self.log(f"❌ Participant login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Participant login error: {str(e)}", "ERROR")
            return False
    
    def test_participant_session_retrieval(self):
        """Test GET /api/sessions - should return participant's assigned sessions"""
        self.log("Testing GET /api/sessions for participant session retrieval...")
        
        if not self.participant_token:
            self.log("❌ Missing participant token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Sessions retrieved successfully. Count: {len(sessions)}")
                
                if len(sessions) == 0:
                    self.log("❌ CRITICAL ISSUE: No sessions assigned to participant 566589", "ERROR")
                    self.log("   This explains why participant portal shows 'No sessions assigned'", "ERROR")
                    return False
                
                # Log session details
                for i, session in enumerate(sessions):
                    self.log(f"   Session {i+1}: {session.get('name', 'Unknown')}")
                    self.log(f"     ID: {session.get('id', 'N/A')}")
                    self.log(f"     Company: {session.get('company_name', 'Unknown')}")
                    self.log(f"     Program: {session.get('program_name', 'Unknown')}")
                    self.log(f"     Dates: {session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')}")
                    
                    # Check if participant is in participant_ids
                    participant_ids = session.get('participant_ids', [])
                    if self.participant_id in participant_ids:
                        self.log(f"     ✅ Participant {self.participant_id} found in participant_ids array")
                    else:
                        self.log(f"     ❌ Participant {self.participant_id} NOT found in participant_ids array", "ERROR")
                
                return True
            else:
                self.log(f"❌ Session retrieval failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session retrieval error: {str(e)}", "ERROR")
            return False
    
    def test_database_participant_access(self):
        """Test database verification for participant_access records"""
        self.log("Testing database verification for participant_access records...")
        
        if not self.admin_token or not self.participant_id:
            self.log("❌ Missing admin token or participant ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # First get all sessions to check participant_access
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code != 200:
                self.log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
                return False
            
            sessions = response.json()
            participant_access_found = False
            
            for session in sessions:
                if self.participant_id in session.get('participant_ids', []):
                    session_id = session['id']
                    self.log(f"   Checking participant_access for session: {session['name']} (ID: {session_id})")
                    
                    # Get session participants to check access records
                    participants_response = self.session.get(f"{BASE_URL}/sessions/{session_id}/participants", headers=headers)
                    
                    if participants_response.status_code == 200:
                        participants = participants_response.json()
                        
                        for participant in participants:
                            if participant.get('id') == self.participant_id:
                                access_info = participant.get('access_info', {})
                                if access_info:
                                    participant_access_found = True
                                    self.log(f"     ✅ Participant_access record found")
                                    self.log(f"       Access ID: {access_info.get('id', 'N/A')}")
                                    self.log(f"       Pre-test released: {access_info.get('pre_test_released', False)}")
                                    self.log(f"       Post-test released: {access_info.get('post_test_released', False)}")
                                    self.log(f"       Feedback released: {access_info.get('feedback_released', False)}")
                                    self.log(f"       Certificate released: {access_info.get('certificate_released', False)}")
                                else:
                                    self.log(f"     ❌ No participant_access record found for participant in session", "ERROR")
                    else:
                        self.log(f"     ❌ Failed to get session participants: {participants_response.status_code}", "ERROR")
            
            if not participant_access_found:
                self.log("❌ CRITICAL ISSUE: No participant_access records found for participant 566589", "ERROR")
                return False
            
            return True
                
        except Exception as e:
            self.log(f"❌ Database verification error: {str(e)}", "ERROR")
            return False
    
    def test_session_details_with_participant_access(self):
        """Test GET /api/sessions/{session_id} - verify session data includes participant information"""
        self.log("Testing GET /api/sessions/{session_id} for session details with participant access...")
        
        if not self.participant_token:
            self.log("❌ Missing participant token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        try:
            # First get sessions to find one to test
            sessions_response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if sessions_response.status_code != 200:
                self.log(f"❌ Failed to get sessions: {sessions_response.status_code}", "ERROR")
                return False
            
            sessions = sessions_response.json()
            
            if len(sessions) == 0:
                self.log("❌ No sessions available to test session details", "ERROR")
                return False
            
            # Test the first session
            session_id = sessions[0]['id']
            self.log(f"   Testing session details for: {sessions[0].get('name', 'Unknown')} (ID: {session_id})")
            
            response = self.session.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
            
            if response.status_code == 200:
                session = response.json()
                self.log(f"✅ Session details retrieved successfully")
                self.log(f"   Session Name: {session.get('name', 'Unknown')}")
                self.log(f"   Company: {session.get('company_name', 'Unknown')}")
                self.log(f"   Program: {session.get('program_name', 'Unknown')}")
                self.log(f"   Participant IDs count: {len(session.get('participant_ids', []))}")
                
                # Verify participant is in the session
                if self.participant_id in session.get('participant_ids', []):
                    self.log(f"   ✅ Participant {self.participant_id} confirmed in session participant_ids")
                    return True
                else:
                    self.log(f"   ❌ Participant {self.participant_id} NOT found in session participant_ids", "ERROR")
                    return False
            else:
                self.log(f"❌ Session details retrieval failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session details test error: {str(e)}", "ERROR")
            return False
    
    def test_availability_for_participants(self):
        """Test GET /api/sessions/{session_id}/tests/available - verify test availability"""
        self.log("Testing GET /api/sessions/{session_id}/tests/available for test availability...")
        
        if not self.participant_token:
            self.log("❌ Missing participant token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        try:
            # First get sessions to find one to test
            sessions_response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if sessions_response.status_code != 200:
                self.log(f"❌ Failed to get sessions: {sessions_response.status_code}", "ERROR")
                return False
            
            sessions = sessions_response.json()
            
            if len(sessions) == 0:
                self.log("❌ No sessions available to test test availability", "ERROR")
                return False
            
            # Test the first session
            session_id = sessions[0]['id']
            self.log(f"   Testing test availability for session: {sessions[0].get('name', 'Unknown')} (ID: {session_id})")
            
            response = self.session.get(f"{BASE_URL}/sessions/{session_id}/tests/available", headers=headers)
            
            if response.status_code == 200:
                tests_data = response.json()
                self.log(f"✅ Test availability retrieved successfully")
                self.log(f"   Pre-test available: {tests_data.get('pre_test') is not None}")
                self.log(f"   Post-test available: {tests_data.get('post_test') is not None}")
                self.log(f"   Pre-test released: {tests_data.get('pre_test_released', False)}")
                self.log(f"   Post-test released: {tests_data.get('post_test_released', False)}")
                self.log(f"   Pre-test submitted: {tests_data.get('pre_test_submitted', False)}")
                self.log(f"   Post-test submitted: {tests_data.get('post_test_submitted', False)}")
                
                # Check if any tests are available
                if tests_data.get('pre_test') is None and tests_data.get('post_test') is None:
                    self.log("❌ ISSUE: No tests available for participant", "ERROR")
                    return False
                
                return True
            else:
                self.log(f"❌ Test availability check failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Test availability error: {str(e)}", "ERROR")
            return False
    
    def test_certificate_access(self):
        """Test GET /api/certificates/my-certificates - verify participant can retrieve certificates"""
        self.log("Testing GET /api/certificates/my-certificates for certificate access...")
        
        if not self.participant_token:
            self.log("❌ Missing participant token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/certificates/my-certificates", headers=headers)
            
            if response.status_code == 200:
                certificates = response.json()
                self.log(f"✅ Certificate access successful. Count: {len(certificates)}")
                
                if len(certificates) == 0:
                    self.log("   ℹ️  No certificates found for participant (expected if none generated yet)")
                else:
                    for i, cert in enumerate(certificates):
                        self.log(f"   Certificate {i+1}:")
                        self.log(f"     ID: {cert.get('id', 'N/A')}")
                        self.log(f"     Certificate Number: {cert.get('certificate_number', 'N/A')}")
                        self.log(f"     Session ID: {cert.get('session_id', 'N/A')}")
                        self.log(f"     Issue Date: {cert.get('issue_date', 'N/A')}")
                
                return True
            else:
                self.log(f"❌ Certificate access failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Certificate access error: {str(e)}", "ERROR")
            return False
    
    def test_session_participant_linkage(self):
        """Test session-participant linkage in database"""
        self.log("Testing session-participant linkage verification...")
        
        if not self.admin_token or not self.participant_id:
            self.log("❌ Missing admin token or participant ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Get all sessions and check participant linkage
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code != 200:
                self.log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
                return False
            
            sessions = response.json()
            linked_sessions = 0
            
            for session in sessions:
                participant_ids = session.get('participant_ids', [])
                if self.participant_id in participant_ids:
                    linked_sessions += 1
                    self.log(f"   ✅ Participant linked to session: {session.get('name', 'Unknown')} (ID: {session['id']})")
            
            self.log(f"✅ Session-participant linkage check complete. Linked sessions: {linked_sessions}")
            
            if linked_sessions == 0:
                self.log("❌ CRITICAL ISSUE: Participant 566589 is not linked to any sessions", "ERROR")
                return False
            
            return True
                
        except Exception as e:
            self.log(f"❌ Session-participant linkage error: {str(e)}", "ERROR")
            return False
    
    def test_participant_ids_array_check(self):
        """Test if participant_ids array is being checked correctly"""
        self.log("Testing participant_ids array filtering logic...")
        
        if not self.participant_token or not self.participant_id:
            self.log("❌ Missing participant token or participant ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.participant_token}'}
        
        try:
            # Get sessions as participant (should be filtered by participant_ids)
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                participant_sessions = response.json()
                self.log(f"✅ Participant sessions retrieved. Count: {len(participant_sessions)}")
                
                # Now get all sessions as admin to compare
                admin_headers = {'Authorization': f'Bearer {self.admin_token}'}
                admin_response = self.session.get(f"{BASE_URL}/sessions", headers=admin_headers)
                
                if admin_response.status_code == 200:
                    all_sessions = admin_response.json()
                    self.log(f"   Total sessions in system: {len(all_sessions)}")
                    
                    # Check filtering logic
                    expected_sessions = []
                    for session in all_sessions:
                        if self.participant_id in session.get('participant_ids', []):
                            expected_sessions.append(session['id'])
                    
                    actual_session_ids = [s['id'] for s in participant_sessions]
                    
                    self.log(f"   Expected sessions for participant: {len(expected_sessions)}")
                    self.log(f"   Actual sessions returned: {len(actual_session_ids)}")
                    
                    if set(expected_sessions) == set(actual_session_ids):
                        self.log("   ✅ Participant_ids array filtering working correctly")
                        return True
                    else:
                        self.log("   ❌ Participant_ids array filtering NOT working correctly", "ERROR")
                        self.log(f"     Expected: {expected_sessions}")
                        self.log(f"     Actual: {actual_session_ids}")
                        return False
                else:
                    self.log(f"❌ Failed to get admin sessions: {admin_response.status_code}", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get participant sessions: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Participant IDs array check error: {str(e)}", "ERROR")
            return False
    
    def test_release_flags_verification(self):
        """Test release flags in participant_access records"""
        self.log("Testing release flags in participant_access records...")
        
        if not self.admin_token or not self.participant_id:
            self.log("❌ Missing admin token or participant ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Get sessions and check participant_access release flags
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code != 200:
                self.log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
                return False
            
            sessions = response.json()
            access_records_checked = 0
            
            for session in sessions:
                if self.participant_id in session.get('participant_ids', []):
                    session_id = session['id']
                    self.log(f"   Checking release flags for session: {session.get('name', 'Unknown')}")
                    
                    # Get session participants to check access records
                    participants_response = self.session.get(f"{BASE_URL}/sessions/{session_id}/participants", headers=headers)
                    
                    if participants_response.status_code == 200:
                        participants = participants_response.json()
                        
                        for participant in participants:
                            if participant.get('id') == self.participant_id:
                                access_info = participant.get('access_info', {})
                                if access_info:
                                    access_records_checked += 1
                                    self.log(f"     Release flags:")
                                    self.log(f"       Pre-test: {access_info.get('pre_test_released', False)}")
                                    self.log(f"       Post-test: {access_info.get('post_test_released', False)}")
                                    self.log(f"       Feedback: {access_info.get('feedback_released', False)}")
                                    self.log(f"       Certificate: {access_info.get('certificate_released', False)}")
                                    
                                    # Check if any are released
                                    any_released = any([
                                        access_info.get('pre_test_released', False),
                                        access_info.get('post_test_released', False),
                                        access_info.get('feedback_released', False),
                                        access_info.get('certificate_released', False)
                                    ])
                                    
                                    if not any_released:
                                        self.log(f"     ⚠️  No release flags are enabled - participant cannot access any features", "WARNING")
            
            if access_records_checked == 0:
                self.log("❌ No participant_access records found to check release flags", "ERROR")
                return False
            
            self.log(f"✅ Release flags verification complete. Records checked: {access_records_checked}")
            return True
                
        except Exception as e:
            self.log(f"❌ Release flags verification error: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all participant session assignment tests"""
        self.log("🚀 Starting Participant Session Assignment Workflow Testing...")
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Login Participant 566589", self.login_participant_566589),
            ("Test 1: Participant Session Retrieval", self.test_participant_session_retrieval),
            ("Test 2: Database Verification - Participant Access Records", self.test_database_participant_access),
            ("Test 3: Session Details with Participant Access", self.test_session_details_with_participant_access),
            ("Test 4: Test Availability for Participants", self.test_availability_for_participants),
            ("Test 5: Certificate Access", self.test_certificate_access),
            ("Test 6: Verify Session-Participant Linkage", self.test_session_participant_linkage),
            ("Test 7: Check Participant IDs Array in Sessions", self.test_participant_ids_array_check),
            ("Test 8: Verify Release Flags in Participant Access", self.test_release_flags_verification)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n{'='*60}")
            self.log(f"Running: {test_name}")
            self.log('='*60)
            
            try:
                if test_func():
                    self.log(f"✅ {test_name} - PASSED")
                    passed += 1
                else:
                    self.log(f"❌ {test_name} - FAILED")
                    failed += 1
            except Exception as e:
                self.log(f"❌ {test_name} - ERROR: {str(e)}", "ERROR")
                failed += 1
        
        # Summary
        self.log(f"\n{'='*60}")
        self.log("PARTICIPANT SESSION ASSIGNMENT TESTING SUMMARY")
        self.log('='*60)
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"📊 Total: {passed + failed}")
        self.log(f"🎯 Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "0.0%")
        
        if failed == 0:
            self.log("🎉 ALL PARTICIPANT SESSION ASSIGNMENT TESTS PASSED!")
            return True
        else:
            self.log(f"⚠️  {failed} test(s) failed. Please review the issues above.")
            return False


if __name__ == "__main__":
    runner = ParticipantSessionTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)