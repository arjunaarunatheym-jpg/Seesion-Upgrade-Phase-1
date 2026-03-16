#!/usr/bin/env python3
"""
Backend Test Suite for Automatic User Detection and Reusability Feature
Tests the new find-or-create logic for participants and supervisors during session creation.

Test Scenarios:
1. Check User Exists Endpoint (POST /api/users/check-exists)
2. Session Creation with New Participants
3. Session Creation with Existing Participants
4. Session Creation with New Supervisors
5. Session Creation with Existing Supervisors
6. Mix of New and Existing Users
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://hr-dispatcher-v2.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

class UserReusabilityTestRunner:
    def __init__(self):
        self.admin_token = None
        self.participant_token = None
        self.test_program_id = None
        self.test_company_id = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Track created resources
        self.created_sessions = []
        self.created_user_ids = []
        
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
    
    def setup_test_data(self):
        """Create test program and company for testing"""
        self.log("Setting up test data (program and company)...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create test program
        program_data = {
            "name": "User Reusability Test Program",
            "description": "Program for testing user reusability feature",
            "pass_percentage": 70.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/programs", json=program_data, headers=headers)
            
            if response.status_code == 200:
                self.test_program_id = response.json()['id']
                self.log(f"✅ Test program created. ID: {self.test_program_id}")
            else:
                self.log(f"❌ Program creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Program creation error: {str(e)}", "ERROR")
            return False
        
        # Create test company
        company_data = {
            "name": "User Reusability Test Company"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
            
            if response.status_code == 200:
                self.test_company_id = response.json()['id']
                self.log(f"✅ Test company created. ID: {self.test_company_id}")
                return True
            else:
                self.log(f"❌ Company creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Company creation error: {str(e)}", "ERROR")
            return False
    
    # ============ TEST 1: Check User Exists Endpoint ============
    
    def test_check_user_exists_without_auth(self):
        """Test POST /api/users/check-exists without authentication (should return 403)"""
        self.log("Test 1.1: Check user exists without authentication (should fail)...")
        
        try:
            # No Authorization header
            response = self.session.post(
                f"{BASE_URL}/users/check-exists",
                params={
                    "full_name": "Test User",
                    "email": "test@example.com"
                }
            )
            
            if response.status_code == 403:
                self.log("✅ Unauthenticated check-exists correctly returned 403")
                return True
            else:
                self.log(f"❌ Expected 403 for unauthenticated request, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Check user exists without auth error: {str(e)}", "ERROR")
            return False
    
    def test_check_user_exists_as_participant(self):
        """Test POST /api/users/check-exists as participant (should return 403)"""
        self.log("Test 1.2: Check user exists as participant (should fail)...")
        
        # First, create and login as participant
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
        
        admin_headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create participant user
        participant_data = {
            "email": "checkexists_participant@example.com",
            "password": "participant123",
            "full_name": "Check Exists Test Participant",
            "id_number": "CETP001",
            "role": "participant"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=participant_data, headers=admin_headers)
            
            if response.status_code == 200:
                self.log("✅ Participant user created")
            elif response.status_code == 400 and "User already exists" in response.text:
                self.log("✅ Participant user already exists")
            else:
                self.log(f"❌ Participant creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Participant creation error: {str(e)}", "ERROR")
            return False
        
        # Login as participant
        login_data = {
            "email": "checkexists_participant@example.com",
            "password": "participant123"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                participant_token = response.json()['access_token']
                self.log("✅ Participant login successful")
            else:
                self.log(f"❌ Participant login failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Participant login error: {str(e)}", "ERROR")
            return False
        
        # Try to check user exists as participant
        participant_headers = {'Authorization': f'Bearer {participant_token}'}
        
        try:
            response = self.session.post(
                f"{BASE_URL}/users/check-exists",
                params={
                    "full_name": "Test User",
                    "email": "test@example.com"
                },
                headers=participant_headers
            )
            
            if response.status_code == 403:
                self.log("✅ Participant check-exists correctly returned 403 Forbidden")
                return True
            else:
                self.log(f"❌ Expected 403 for participant, got: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Check user exists as participant error: {str(e)}", "ERROR")
            return False
    
    def test_check_user_exists_no_match(self):
        """Test POST /api/users/check-exists with name but no match (should return exists: false)"""
        self.log("Test 1.3: Check user exists with no match...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.post(
                f"{BASE_URL}/users/check-exists",
                params={
                    "full_name": "NonExistent User XYZ123",
                    "email": "nonexistent_xyz123@example.com"
                },
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('exists') == False and data.get('user') is None:
                    self.log("✅ Check-exists correctly returned exists: false for non-existent user")
                    return True
                else:
                    self.log(f"❌ Expected exists: false, got: {data}", "ERROR")
                    return False
            else:
                self.log(f"❌ Check user exists failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Check user exists error: {str(e)}", "ERROR")
            return False
    
    # ============ TEST 2: Session Creation with New Participants ============
    
    def test_create_session_with_new_participants(self):
        """Test session creation with 2 new participants"""
        self.log("Test 2: Create session with 2 new participants...")
        
        if not self.admin_token or not self.test_program_id or not self.test_company_id:
            self.log("❌ Missing admin token, program ID, or company ID", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        session_data = {
            "name": "Session with New Participants",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "participant_ids": [],
            "supervisor_ids": [],
            "participants": [
                {
                    "email": "newparticipant1@example.com",
                    "password": "password123",
                    "full_name": "New Participant One",
                    "id_number": "NP001",
                    "phone_number": "+60123456789"
                },
                {
                    "email": "newparticipant2@example.com",
                    "password": "password123",
                    "full_name": "New Participant Two",
                    "id_number": "NP002",
                    "phone_number": "+60123456790"
                }
            ],
            "supervisors": []
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                session_obj = data.get('session')
                participant_results = data.get('participant_results', [])
                
                self.log(f"✅ Session created successfully. ID: {session_obj['id']}")
                self.created_sessions.append(session_obj['id'])
                
                # Verify participant_results
                if len(participant_results) == 2:
                    self.log(f"✅ Received 2 participant results")
                    
                    # Check is_existing flags (should all be False for new participants)
                    all_new = all(not result.get('is_existing', True) for result in participant_results)
                    if all_new:
                        self.log("✅ All participants correctly marked as is_existing: false")
                    else:
                        self.log(f"❌ Expected all new participants, got: {participant_results}", "ERROR")
                        return False
                    
                    # Verify participants are in session
                    if len(session_obj.get('participant_ids', [])) == 2:
                        self.log("✅ 2 participants assigned to session")
                        
                        # Store user IDs for later tests
                        self.new_participant_1_email = "newparticipant1@example.com"
                        self.new_participant_1_name = "New Participant One"
                        self.new_participant_2_email = "newparticipant2@example.com"
                        self.new_participant_2_name = "New Participant Two"
                        
                        return True
                    else:
                        self.log(f"❌ Expected 2 participants in session, got: {len(session_obj.get('participant_ids', []))}", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 2 participant results, got: {len(participant_results)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def test_verify_participants_created_in_db(self):
        """Verify that participants were actually created in the users collection"""
        self.log("Test 2.1: Verify participants created in database...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Get all users with role participant
            response = self.session.get(f"{BASE_URL}/users?role=participant", headers=headers)
            
            if response.status_code == 200:
                users = response.json()
                
                # Find our test participants
                participant1 = next((u for u in users if u['email'] == self.new_participant_1_email), None)
                participant2 = next((u for u in users if u['email'] == self.new_participant_2_email), None)
                
                if participant1 and participant2:
                    self.log("✅ Both participants found in users collection")
                    self.log(f"   Participant 1: {participant1['full_name']} (ID: {participant1['id']})")
                    self.log(f"   Participant 2: {participant2['full_name']} (ID: {participant2['id']})")
                    
                    # Store IDs for later tests
                    self.new_participant_1_id = participant1['id']
                    self.new_participant_2_id = participant2['id']
                    
                    return True
                else:
                    self.log(f"❌ Participants not found in database. P1: {participant1 is not None}, P2: {participant2 is not None}", "ERROR")
                    return False
            else:
                self.log(f"❌ Get users failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Verify participants error: {str(e)}", "ERROR")
            return False
    
    # ============ TEST 3: Check User Exists with Existing User ============
    
    def test_check_user_exists_by_name_and_email(self):
        """Test POST /api/users/check-exists with name + email (should find existing user)"""
        self.log("Test 3.1: Check user exists by name + email...")
        
        if not self.admin_token or not hasattr(self, 'new_participant_1_email'):
            self.log("❌ Missing admin token or participant email", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.post(
                f"{BASE_URL}/users/check-exists",
                params={
                    "full_name": self.new_participant_1_name,
                    "email": self.new_participant_1_email
                },
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('exists') == True and data.get('user') is not None:
                    user = data['user']
                    self.log(f"✅ Check-exists correctly found existing user by name + email")
                    self.log(f"   User: {user['full_name']} ({user['email']})")
                    return True
                else:
                    self.log(f"❌ Expected exists: true, got: {data}", "ERROR")
                    return False
            else:
                self.log(f"❌ Check user exists failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Check user exists error: {str(e)}", "ERROR")
            return False
    
    def test_check_user_exists_by_name_and_phone(self):
        """Test POST /api/users/check-exists with name + phone (should find existing user)"""
        self.log("Test 3.2: Check user exists by name + phone...")
        
        if not self.admin_token or not hasattr(self, 'new_participant_1_name'):
            self.log("❌ Missing admin token or participant name", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.post(
                f"{BASE_URL}/users/check-exists",
                params={
                    "full_name": self.new_participant_1_name,
                    "phone_number": "+60123456789"
                },
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('exists') == True and data.get('user') is not None:
                    user = data['user']
                    self.log(f"✅ Check-exists correctly found existing user by name + phone")
                    self.log(f"   User: {user['full_name']} (Phone: {user.get('phone_number', 'N/A')})")
                    return True
                else:
                    self.log(f"❌ Expected exists: true, got: {data}", "ERROR")
                    return False
            else:
                self.log(f"❌ Check user exists failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Check user exists error: {str(e)}", "ERROR")
            return False
    
    # ============ TEST 4: Session Creation with Existing Participants ============
    
    def test_create_session_with_existing_participant(self):
        """Test session creation with existing participant (same name + email)"""
        self.log("Test 4: Create session with existing participant...")
        
        if not self.admin_token or not self.test_program_id or not self.test_company_id:
            self.log("❌ Missing admin token, program ID, or company ID", "ERROR")
            return False
        
        if not hasattr(self, 'new_participant_1_email'):
            self.log("❌ Missing participant email from previous test", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create session with same participant (same name + email, but different ID number)
        session_data = {
            "name": "Session with Existing Participant",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 2",
            "start_date": "2024-02-01",
            "end_date": "2024-02-28",
            "participant_ids": [],
            "supervisor_ids": [],
            "participants": [
                {
                    "email": self.new_participant_1_email,  # Same email
                    "password": "password123",
                    "full_name": self.new_participant_1_name,  # Same name
                    "id_number": "NP001_UPDATED",  # Different ID number
                    "phone_number": "+60123456789"  # Same phone
                }
            ],
            "supervisors": []
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                session_obj = data.get('session')
                participant_results = data.get('participant_results', [])
                
                self.log(f"✅ Session created successfully. ID: {session_obj['id']}")
                self.created_sessions.append(session_obj['id'])
                
                # Verify participant_results
                if len(participant_results) == 1:
                    result = participant_results[0]
                    
                    # Check is_existing flag (should be True)
                    if result.get('is_existing') == True:
                        self.log("✅ Participant correctly marked as is_existing: true")
                        self.log(f"   Name: {result['name']}, Email: {result['email']}")
                        
                        # Verify same user ID is used
                        if len(session_obj.get('participant_ids', [])) == 1:
                            session_participant_id = session_obj['participant_ids'][0]
                            
                            if hasattr(self, 'new_participant_1_id') and session_participant_id == self.new_participant_1_id:
                                self.log(f"✅ Same user ID used in both sessions: {session_participant_id}")
                                return True
                            else:
                                self.log(f"❌ Different user ID used. Expected: {getattr(self, 'new_participant_1_id', 'N/A')}, Got: {session_participant_id}", "ERROR")
                                return False
                        else:
                            self.log(f"❌ Expected 1 participant in session, got: {len(session_obj.get('participant_ids', []))}", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Expected is_existing: true, got: {result.get('is_existing')}", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 1 participant result, got: {len(participant_results)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def test_verify_user_data_updated(self):
        """Verify that user data was updated (ID number changed)"""
        self.log("Test 4.1: Verify user data was updated...")
        
        if not self.admin_token or not hasattr(self, 'new_participant_1_id'):
            self.log("❌ Missing admin token or participant ID", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/users/{self.new_participant_1_id}", headers=headers)
            
            if response.status_code == 200:
                user = response.json()
                
                # Check if ID number was updated
                if user.get('id_number') == "NP001_UPDATED":
                    self.log(f"✅ User data updated successfully. New ID number: {user['id_number']}")
                    return True
                else:
                    self.log(f"❌ User ID number not updated. Expected: NP001_UPDATED, Got: {user.get('id_number')}", "ERROR")
                    return False
            else:
                self.log(f"❌ Get user failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Verify user data error: {str(e)}", "ERROR")
            return False
    
    def test_verify_no_duplicate_users(self):
        """Verify that no duplicate users were created"""
        self.log("Test 4.2: Verify no duplicate users created...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/users?role=participant", headers=headers)
            
            if response.status_code == 200:
                users = response.json()
                
                # Count users with same email
                matching_users = [u for u in users if u['email'] == self.new_participant_1_email]
                
                if len(matching_users) == 1:
                    self.log(f"✅ No duplicate users created. Found exactly 1 user with email {self.new_participant_1_email}")
                    return True
                else:
                    self.log(f"❌ Found {len(matching_users)} users with same email (expected 1)", "ERROR")
                    return False
            else:
                self.log(f"❌ Get users failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Verify no duplicates error: {str(e)}", "ERROR")
            return False
    
    # ============ TEST 5: Session Creation with New Supervisor ============
    
    def test_create_session_with_new_supervisor(self):
        """Test session creation with 1 new supervisor"""
        self.log("Test 5: Create session with 1 new supervisor...")
        
        if not self.admin_token or not self.test_program_id or not self.test_company_id:
            self.log("❌ Missing admin token, program ID, or company ID", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        session_data = {
            "name": "Session with New Supervisor",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 3",
            "start_date": "2024-03-01",
            "end_date": "2024-03-31",
            "participant_ids": [],
            "supervisor_ids": [],
            "participants": [],
            "supervisors": [
                {
                    "email": "newsupervisor1@example.com",
                    "password": "password123",
                    "full_name": "New Supervisor One",
                    "id_number": "NS001",
                    "phone_number": "+60123456791"
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                session_obj = data.get('session')
                supervisor_results = data.get('supervisor_results', [])
                
                self.log(f"✅ Session created successfully. ID: {session_obj['id']}")
                self.created_sessions.append(session_obj['id'])
                
                # Verify supervisor_results
                if len(supervisor_results) == 1:
                    result = supervisor_results[0]
                    
                    # Check is_existing flag (should be False for new supervisor)
                    if result.get('is_existing') == False:
                        self.log("✅ Supervisor correctly marked as is_existing: false")
                        self.log(f"   Name: {result['name']}, Email: {result['email']}")
                        
                        # Verify supervisor is in session
                        if len(session_obj.get('supervisor_ids', [])) == 1:
                            self.log("✅ 1 supervisor assigned to session")
                            
                            # Store supervisor info for later tests
                            self.new_supervisor_1_email = "newsupervisor1@example.com"
                            self.new_supervisor_1_name = "New Supervisor One"
                            
                            return True
                        else:
                            self.log(f"❌ Expected 1 supervisor in session, got: {len(session_obj.get('supervisor_ids', []))}", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Expected is_existing: false, got: {result.get('is_existing')}", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 1 supervisor result, got: {len(supervisor_results)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def test_verify_supervisor_created_with_correct_role(self):
        """Verify that supervisor was created with role 'pic_supervisor'"""
        self.log("Test 5.1: Verify supervisor created with correct role...")
        
        if not self.admin_token or not hasattr(self, 'new_supervisor_1_email'):
            self.log("❌ Missing admin token or supervisor email", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/users?role=pic_supervisor", headers=headers)
            
            if response.status_code == 200:
                users = response.json()
                
                # Find our test supervisor
                supervisor = next((u for u in users if u['email'] == self.new_supervisor_1_email), None)
                
                if supervisor:
                    self.log(f"✅ Supervisor found with role 'pic_supervisor'")
                    self.log(f"   Supervisor: {supervisor['full_name']} (ID: {supervisor['id']})")
                    
                    # Store ID for later tests
                    self.new_supervisor_1_id = supervisor['id']
                    
                    return True
                else:
                    self.log(f"❌ Supervisor not found with role 'pic_supervisor'", "ERROR")
                    return False
            else:
                self.log(f"❌ Get users failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Verify supervisor error: {str(e)}", "ERROR")
            return False
    
    # ============ TEST 6: Session Creation with Existing Supervisor ============
    
    def test_create_session_with_existing_supervisor(self):
        """Test session creation with existing supervisor (same name + email)"""
        self.log("Test 6: Create session with existing supervisor...")
        
        if not self.admin_token or not self.test_program_id or not self.test_company_id:
            self.log("❌ Missing admin token, program ID, or company ID", "ERROR")
            return False
        
        if not hasattr(self, 'new_supervisor_1_email'):
            self.log("❌ Missing supervisor email from previous test", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create session with same supervisor
        session_data = {
            "name": "Session with Existing Supervisor",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 4",
            "start_date": "2024-04-01",
            "end_date": "2024-04-30",
            "participant_ids": [],
            "supervisor_ids": [],
            "participants": [],
            "supervisors": [
                {
                    "email": self.new_supervisor_1_email,  # Same email
                    "password": "password123",
                    "full_name": self.new_supervisor_1_name,  # Same name
                    "id_number": "NS001_UPDATED",  # Different ID number
                    "phone_number": "+60123456791"  # Same phone
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                session_obj = data.get('session')
                supervisor_results = data.get('supervisor_results', [])
                
                self.log(f"✅ Session created successfully. ID: {session_obj['id']}")
                self.created_sessions.append(session_obj['id'])
                
                # Verify supervisor_results
                if len(supervisor_results) == 1:
                    result = supervisor_results[0]
                    
                    # Check is_existing flag (should be True)
                    if result.get('is_existing') == True:
                        self.log("✅ Supervisor correctly marked as is_existing: true")
                        self.log(f"   Name: {result['name']}, Email: {result['email']}")
                        
                        # Verify same user ID is used
                        if len(session_obj.get('supervisor_ids', [])) == 1:
                            session_supervisor_id = session_obj['supervisor_ids'][0]
                            
                            if hasattr(self, 'new_supervisor_1_id') and session_supervisor_id == self.new_supervisor_1_id:
                                self.log(f"✅ Same supervisor ID used in both sessions: {session_supervisor_id}")
                                return True
                            else:
                                self.log(f"❌ Different supervisor ID used. Expected: {getattr(self, 'new_supervisor_1_id', 'N/A')}, Got: {session_supervisor_id}", "ERROR")
                                return False
                        else:
                            self.log(f"❌ Expected 1 supervisor in session, got: {len(session_obj.get('supervisor_ids', []))}", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Expected is_existing: true, got: {result.get('is_existing')}", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 1 supervisor result, got: {len(supervisor_results)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    # ============ TEST 7: Mix of New and Existing Users ============
    
    def test_create_session_with_mixed_users(self):
        """Test session creation with mix of new and existing users"""
        self.log("Test 7: Create session with mix of new and existing users...")
        
        if not self.admin_token or not self.test_program_id or not self.test_company_id:
            self.log("❌ Missing admin token, program ID, or company ID", "ERROR")
            return False
        
        if not hasattr(self, 'new_participant_1_email') or not hasattr(self, 'new_supervisor_1_email'):
            self.log("❌ Missing participant or supervisor email from previous tests", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        session_data = {
            "name": "Session with Mixed Users",
            "program_id": self.test_program_id,
            "company_id": self.test_company_id,
            "location": "Test Location 5",
            "start_date": "2024-05-01",
            "end_date": "2024-05-31",
            "participant_ids": [],
            "supervisor_ids": [],
            "participants": [
                {
                    "email": "brandnewparticipant@example.com",  # New participant
                    "password": "password123",
                    "full_name": "Brand New Participant",
                    "id_number": "BNP001",
                    "phone_number": "+60123456792"
                },
                {
                    "email": self.new_participant_1_email,  # Existing participant
                    "password": "password123",
                    "full_name": self.new_participant_1_name,
                    "id_number": "NP001_UPDATED",
                    "phone_number": "+60123456789"
                }
            ],
            "supervisors": [
                {
                    "email": self.new_supervisor_1_email,  # Existing supervisor
                    "password": "password123",
                    "full_name": self.new_supervisor_1_name,
                    "id_number": "NS001_UPDATED",
                    "phone_number": "+60123456791"
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                session_obj = data.get('session')
                participant_results = data.get('participant_results', [])
                supervisor_results = data.get('supervisor_results', [])
                
                self.log(f"✅ Session created successfully. ID: {session_obj['id']}")
                self.created_sessions.append(session_obj['id'])
                
                # Verify participant_results
                if len(participant_results) == 2:
                    self.log(f"✅ Received 2 participant results")
                    
                    # Find new and existing participants
                    new_participant = next((r for r in participant_results if r['email'] == "brandnewparticipant@example.com"), None)
                    existing_participant = next((r for r in participant_results if r['email'] == self.new_participant_1_email), None)
                    
                    if new_participant and existing_participant:
                        # Check is_existing flags
                        if new_participant.get('is_existing') == False and existing_participant.get('is_existing') == True:
                            self.log("✅ Correct is_existing flags for participants")
                            self.log(f"   New: {new_participant['name']} (is_existing: false)")
                            self.log(f"   Existing: {existing_participant['name']} (is_existing: true)")
                        else:
                            self.log(f"❌ Incorrect is_existing flags. New: {new_participant.get('is_existing')}, Existing: {existing_participant.get('is_existing')}", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Could not find expected participants in results", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 2 participant results, got: {len(participant_results)}", "ERROR")
                    return False
                
                # Verify supervisor_results
                if len(supervisor_results) == 1:
                    result = supervisor_results[0]
                    
                    # Check is_existing flag (should be True)
                    if result.get('is_existing') == True:
                        self.log("✅ Existing supervisor correctly marked as is_existing: true")
                        self.log(f"   Supervisor: {result['name']} (is_existing: true)")
                        
                        # Verify all users are properly linked
                        if len(session_obj.get('participant_ids', [])) == 2 and len(session_obj.get('supervisor_ids', [])) == 1:
                            self.log("✅ All users properly linked to session")
                            self.log(f"   Participants: {len(session_obj['participant_ids'])}, Supervisors: {len(session_obj['supervisor_ids'])}")
                            return True
                        else:
                            self.log(f"❌ Incorrect user counts in session. Participants: {len(session_obj.get('participant_ids', []))}, Supervisors: {len(session_obj.get('supervisor_ids', []))}", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Expected is_existing: true for supervisor, got: {result.get('is_existing')}", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 1 supervisor result, got: {len(supervisor_results)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def test_verify_participant_access_created_for_all(self):
        """Verify that participant_access records were created for all participants"""
        self.log("Test 7.1: Verify participant_access records created for all participants...")
        
        if not self.admin_token or not self.created_sessions:
            self.log("❌ Missing admin token or session IDs", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Check the last created session (mixed users session)
        last_session_id = self.created_sessions[-1]
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{last_session_id}/participants", headers=headers)
            
            if response.status_code == 200:
                participants = response.json()
                
                if len(participants) == 2:
                    self.log(f"✅ Found 2 participants with access records")
                    
                    # Verify all have access records
                    all_have_access = all('access' in p for p in participants)
                    if all_have_access:
                        self.log("✅ All participants have participant_access records")
                        return True
                    else:
                        self.log(f"❌ Some participants missing access records", "ERROR")
                        return False
                else:
                    self.log(f"❌ Expected 2 participants, got: {len(participants)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Get session participants failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Verify participant access error: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("=" * 80)
        self.log("STARTING USER REUSABILITY FEATURE TESTS")
        self.log("=" * 80)
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Setup Test Data", self.setup_test_data),
            ("Test 1.1: Check User Exists Without Auth", self.test_check_user_exists_without_auth),
            ("Test 1.2: Check User Exists As Participant", self.test_check_user_exists_as_participant),
            ("Test 1.3: Check User Exists No Match", self.test_check_user_exists_no_match),
            ("Test 2: Create Session with New Participants", self.test_create_session_with_new_participants),
            ("Test 2.1: Verify Participants Created in DB", self.test_verify_participants_created_in_db),
            ("Test 3.1: Check User Exists by Name + Email", self.test_check_user_exists_by_name_and_email),
            ("Test 3.2: Check User Exists by Name + Phone", self.test_check_user_exists_by_name_and_phone),
            ("Test 4: Create Session with Existing Participant", self.test_create_session_with_existing_participant),
            ("Test 4.1: Verify User Data Updated", self.test_verify_user_data_updated),
            ("Test 4.2: Verify No Duplicate Users", self.test_verify_no_duplicate_users),
            ("Test 5: Create Session with New Supervisor", self.test_create_session_with_new_supervisor),
            ("Test 5.1: Verify Supervisor Created with Correct Role", self.test_verify_supervisor_created_with_correct_role),
            ("Test 6: Create Session with Existing Supervisor", self.test_create_session_with_existing_supervisor),
            ("Test 7: Create Session with Mixed Users", self.test_create_session_with_mixed_users),
            ("Test 7.1: Verify Participant Access Created for All", self.test_verify_participant_access_created_for_all),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log("")
            self.log(f"Running: {test_name}")
            self.log("-" * 80)
            
            try:
                result = test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"❌ Test crashed: {str(e)}", "ERROR")
                failed += 1
        
        self.log("")
        self.log("=" * 80)
        self.log("TEST SUMMARY")
        self.log("=" * 80)
        self.log(f"Total Tests: {passed + failed}")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")
        self.log("=" * 80)
        
        return failed == 0

if __name__ == "__main__":
    runner = UserReusabilityTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
