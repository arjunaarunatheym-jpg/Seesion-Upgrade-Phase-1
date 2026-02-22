#!/usr/bin/env python3
"""
Team Building Session Investigation Test Suite
Comprehensive workflow test for Training Management System focusing on the coordinator portal issue.

PRIMARY ISSUE TO INVESTIGATE:
Coordinator portal (malek@mddrc.com.my) shows 0/3 test completion for "Team Building" session 
despite tests being taken. Management and Analytics tabs show no test data.

TEST SEQUENCE:
PHASE 1: Database Investigation
PHASE 2: Backend API Testing  
PHASE 3: Participant Workflow Test
PHASE 4: Cross-Reference Check
PHASE 5: Analytics Calculation
"""

import requests
import json
import sys
from datetime import datetime
import pymongo
import os

# Configuration
BASE_URL = "https://payment-accuracy.preview.emergentagent.com/api"

# Test Credentials from review request
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"
ASSISTANT_ADMIN_EMAIL = "abillashaa@mddrc.com.my"
ASSISTANT_ADMIN_PASSWORD = "mddrc1"

# Participant credentials
PARTICIPANTS = [
    {"email": "team1", "password": "mddrc1"},
    {"email": "Team6", "password": "mddrc1"}, 
    {"email": "Team7", "password": "mddrc1"}
]

OTHER_USERS = [
    {"email": "vijay@mddrc.com.my", "password": "mddrc1"},
    {"email": "Dheena8983@gmail.com", "password": "mddrc1"}
]

class TeamBuildingInvestigator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Tokens for different users
        self.admin_token = None
        self.coordinator_token = None
        self.participant_tokens = {}
        
        # Investigation data
        self.team_building_session = None
        self.team_building_session_id = None
        self.program_id = None
        self.test_results_data = []
        self.participant_access_data = []
        
        # MongoDB connection
        self.mongo_client = None
        self.db = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def connect_to_database(self):
        """Connect to MongoDB database"""
        self.log("Connecting to MongoDB database...")
        
        try:
            # Get MongoDB URL from environment or use default
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            db_name = os.environ.get('DB_NAME', 'driving_training_db')
            
            self.mongo_client = pymongo.MongoClient(mongo_url)
            self.db = self.mongo_client[db_name]
            
            # Test connection
            self.db.command('ping')
            self.log("✅ Successfully connected to MongoDB database")
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to connect to MongoDB: {str(e)}", "ERROR")
            return False
    
    def login_user(self, email, password, role_name="user"):
        """Login a user and return token"""
        self.log(f"Attempting login for {role_name}: {email}")
        
        login_data = {
            "email": email,
            "password": password
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                token = data['access_token']
                user_info = data['user']
                self.log(f"✅ {role_name} login successful. User: {user_info['full_name']} ({user_info['role']})")
                return token
            else:
                self.log(f"❌ {role_name} login failed: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ {role_name} login error: {str(e)}", "ERROR")
            return None
    
    def setup_authentication(self):
        """Setup authentication for all test users"""
        self.log("=== SETTING UP AUTHENTICATION ===")
        
        # Login admin
        self.admin_token = self.login_user(ADMIN_EMAIL, ADMIN_PASSWORD, "Admin")
        if not self.admin_token:
            return False
            
        # Login coordinator
        self.coordinator_token = self.login_user(COORDINATOR_EMAIL, COORDINATOR_PASSWORD, "Coordinator")
        if not self.coordinator_token:
            return False
            
        # Login participants
        for i, participant in enumerate(PARTICIPANTS):
            token = self.login_user(participant["email"], participant["password"], f"Participant {i+1}")
            if token:
                self.participant_tokens[participant["email"]] = token
            else:
                self.log(f"⚠️ Failed to login participant {participant['email']}", "WARNING")
        
        self.log(f"✅ Authentication setup complete. Logged in {len(self.participant_tokens)} participants")
        return True
    
    # ============ PHASE 1: DATABASE INVESTIGATION ============
    
    def phase1_database_investigation(self):
        """PHASE 1: Check if Team Building session exists in database"""
        self.log("=== PHASE 1: DATABASE INVESTIGATION ===")
        
        if self.db is None:
            self.log("❌ Database connection not available", "ERROR")
            return False
        
        try:
            # 1. Check if "Team Building" session exists
            self.log("1. Searching for 'Team Building' session in database...")
            sessions_collection = self.db.sessions
            
            team_building_sessions = list(sessions_collection.find({
                "name": {"$regex": "Team Building", "$options": "i"}
            }))
            
            if not team_building_sessions:
                self.log("❌ No 'Team Building' session found in database", "ERROR")
                return False
            
            self.team_building_session = team_building_sessions[0]
            self.team_building_session_id = self.team_building_session['id']
            self.program_id = self.team_building_session.get('program_id')
            
            self.log(f"✅ Found 'Team Building' session:")
            self.log(f"   Session ID: {self.team_building_session_id}")
            self.log(f"   Session Name: {self.team_building_session['name']}")
            self.log(f"   Program ID: {self.program_id}")
            self.log(f"   Coordinator ID: {self.team_building_session.get('coordinator_id', 'N/A')}")
            
            # 2. Get session ID and program ID for "Team Building"
            self.log("2. Extracting session and program IDs...")
            self.log(f"   ✅ Session ID: {self.team_building_session_id}")
            self.log(f"   ✅ Program ID: {self.program_id}")
            
            # 3. Query test_results collection for this session_id
            self.log("3. Querying test_results collection for this session...")
            test_results_collection = self.db.test_results
            
            test_results = list(test_results_collection.find({
                "session_id": self.team_building_session_id
            }))
            
            self.test_results_data = test_results
            self.log(f"✅ Found {len(test_results)} test results for Team Building session")
            
            # 4. Verify if test results have test_type field
            self.log("4. Verifying test_type field in test results...")
            missing_test_type = 0
            for i, result in enumerate(test_results):
                if 'test_type' not in result:
                    missing_test_type += 1
                    self.log(f"   ⚠️ Test result {i+1} missing test_type field")
                else:
                    self.log(f"   ✅ Test result {i+1}: test_type = {result['test_type']}")
            
            if missing_test_type > 0:
                self.log(f"❌ {missing_test_type} test results missing test_type field", "ERROR")
            else:
                self.log("✅ All test results have test_type field")
            
            # 5. Check participant_access records for this session
            self.log("5. Checking participant_access records for this session...")
            participant_access_collection = self.db.participant_access
            
            participant_access = list(participant_access_collection.find({
                "session_id": self.team_building_session_id
            }))
            
            self.participant_access_data = participant_access
            self.log(f"✅ Found {len(participant_access)} participant_access records")
            
            for i, access in enumerate(participant_access):
                self.log(f"   Participant {i+1}: {access.get('participant_id', 'N/A')}")
                self.log(f"     - can_access_pre_test: {access.get('can_access_pre_test', False)}")
                self.log(f"     - can_access_post_test: {access.get('can_access_post_test', False)}")
                self.log(f"     - can_access_feedback: {access.get('can_access_feedback', False)}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Database investigation error: {str(e)}", "ERROR")
            return False
    
    # ============ PHASE 2: BACKEND API TESTING ============
    
    def phase2_backend_api_testing(self):
        """PHASE 2: Backend API Testing with coordinator credentials"""
        self.log("=== PHASE 2: BACKEND API TESTING ===")
        
        if not self.coordinator_token:
            self.log("❌ Coordinator token not available", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        try:
            # 1. Login Test (already done, but verify token works)
            self.log("1. Testing coordinator authentication...")
            response = self.session.get(f"{BASE_URL}/auth/me", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                self.log(f"✅ Coordinator authentication verified: {user_data['full_name']}")
            else:
                self.log(f"❌ Coordinator authentication failed: {response.status_code}", "ERROR")
                return False
            
            # 2. Get Coordinator Sessions
            self.log("2. Testing GET /api/sessions (coordinator sessions)...")
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Retrieved {len(sessions)} sessions for coordinator")
                
                # Find Team Building session
                team_building_found = False
                for session in sessions:
                    if "Team Building" in session.get('name', ''):
                        team_building_found = True
                        self.log(f"   ✅ Found Team Building session: {session['name']}")
                        self.log(f"      Session ID: {session['id']}")
                        self.log(f"      Coordinator ID: {session.get('coordinator_id', 'N/A')}")
                        break
                
                if not team_building_found:
                    self.log("❌ Team Building session not found in coordinator's sessions", "ERROR")
                    return False
            else:
                self.log(f"❌ Get coordinator sessions failed: {response.status_code} - {response.text}", "ERROR")
                return False
            
            # 3. Get Test Results for Team Building Session
            self.log("3. Testing GET /api/tests/session/{session_id}/results...")
            
            # Extract session ID from the sessions we just retrieved
            team_building_session_id = None
            for session in sessions:
                if "Team Building" in session.get('name', ''):
                    team_building_session_id = session['id']
                    self.team_building_session_id = team_building_session_id
                    break
            
            if not team_building_session_id:
                self.log("❌ Team Building session ID not available", "ERROR")
                return False
            
            response = self.session.get(f"{BASE_URL}/tests/session/{team_building_session_id}/results", headers=headers)
            
            if response.status_code == 200:
                test_results = response.json()
                self.log(f"✅ Retrieved {len(test_results)} test results from API")
                
                # Check if results include test_type
                for i, result in enumerate(test_results):
                    if 'test_type' in result:
                        self.log(f"   ✅ Test result {i+1}: test_type = {result['test_type']}")
                    else:
                        self.log(f"   ❌ Test result {i+1}: missing test_type field")
            else:
                self.log(f"❌ Get test results failed: {response.status_code} - {response.text}", "ERROR")
                if response.status_code == 404:
                    self.log("   This might indicate the endpoint doesn't exist or session not found")
                elif response.status_code == 403:
                    self.log("   This might indicate coordinator doesn't have access to this session")
            
            # 4. Get Participant List
            self.log("4. Testing GET /api/sessions/{session_id} (session details)...")
            response = self.session.get(f"{BASE_URL}/sessions/{team_building_session_id}", headers=headers)
            
            if response.status_code == 200:
                session_details = response.json()
                self.log(f"✅ Retrieved session details")
                
                participant_ids = session_details.get('participant_ids', [])
                self.log(f"   Participant IDs: {len(participant_ids)} participants")
                for i, pid in enumerate(participant_ids):
                    self.log(f"     Participant {i+1}: {pid}")
            else:
                self.log(f"❌ Get session details failed: {response.status_code} - {response.text}", "ERROR")
            
            # 5. Check Individual Participant Results
            self.log("5. Testing individual participant results...")
            if 'participant_ids' in locals() and participant_ids:
                for i, participant_id in enumerate(participant_ids[:3]):  # Test first 3 participants
                    self.log(f"   Testing participant {i+1}: {participant_id}")
                    response = self.session.get(f"{BASE_URL}/tests/results/participant/{participant_id}", headers=headers)
                    
                    if response.status_code == 200:
                        participant_results = response.json()
                        self.log(f"     ✅ Found {len(participant_results)} results for participant {i+1}")
                        
                        for j, result in enumerate(participant_results):
                            test_type = result.get('test_type', 'N/A')
                            score = result.get('score', 'N/A')
                            self.log(f"       Result {j+1}: {test_type} test, Score: {score}%")
                    else:
                        self.log(f"     ❌ Failed to get results for participant {i+1}: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Backend API testing error: {str(e)}", "ERROR")
            return False
    
    # ============ PHASE 3: PARTICIPANT WORKFLOW TEST ============
    
    def phase3_participant_workflow_test(self):
        """PHASE 3: Participant Workflow Test"""
        self.log("=== PHASE 3: PARTICIPANT WORKFLOW TEST ===")
        
        if not self.participant_tokens:
            self.log("❌ No participant tokens available", "ERROR")
            return False
        
        # Test with first available participant
        participant_email = list(self.participant_tokens.keys())[0]
        participant_token = self.participant_tokens[participant_email]
        headers = {'Authorization': f'Bearer {participant_token}'}
        
        try:
            # 1. Login as participant (already done)
            self.log(f"1. Testing with participant: {participant_email}")
            
            # 2. GET /api/sessions - verify "Team Building" session is visible
            self.log("2. Testing GET /api/sessions (participant view)...")
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Participant can see {len(sessions)} sessions")
                
                team_building_visible = False
                for session in sessions:
                    if "Team Building" in session.get('name', ''):
                        team_building_visible = True
                        self.log(f"   ✅ Team Building session visible to participant")
                        break
                
                if not team_building_visible:
                    self.log("❌ Team Building session not visible to participant", "ERROR")
            else:
                self.log(f"❌ Participant sessions failed: {response.status_code} - {response.text}", "ERROR")
            
            # 3. GET /api/sessions/{session_id}/tests/available - check available tests
            self.log("3. Testing GET /api/sessions/{session_id}/tests/available...")
            if self.team_building_session_id:
                response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}/tests/available", headers=headers)
                
                if response.status_code == 200:
                    available_tests = response.json()
                    self.log(f"✅ Found {len(available_tests)} available tests for participant")
                    
                    for i, test in enumerate(available_tests):
                        test_type = test.get('test_type', 'N/A')
                        questions_count = len(test.get('questions', []))
                        self.log(f"   Test {i+1}: {test_type} test with {questions_count} questions")
                        
                        # Check if correct answers are hidden
                        if test.get('questions'):
                            first_question = test['questions'][0]
                            if 'correct_answer' in first_question:
                                self.log(f"     ❌ SECURITY ISSUE: correct_answer visible to participant")
                            else:
                                self.log(f"     ✅ correct_answer properly hidden from participant")
                    
                    # 4. If tests available, take a pre-test
                    pre_tests = [t for t in available_tests if t.get('test_type') == 'pre']
                    if pre_tests:
                        self.log("4. Attempting to take pre-test...")
                        pre_test = pre_tests[0]
                        test_id = pre_test['id']
                        questions = pre_test.get('questions', [])
                        
                        if questions:
                            # Submit test with sample answers
                            answers = [0] * len(questions)  # Answer 'A' for all questions
                            
                            submission_data = {
                                "test_id": test_id,
                                "session_id": self.team_building_session_id,
                                "answers": answers
                            }
                            
                            response = self.session.post(f"{BASE_URL}/tests/submit", json=submission_data, headers=headers)
                            
                            if response.status_code == 200:
                                result = response.json()
                                self.log(f"✅ Pre-test submitted successfully")
                                self.log(f"   Score: {result.get('score', 'N/A')}%")
                                self.log(f"   Test Type: {result.get('test_type', 'N/A')}")
                                
                                # 5. Verify coordinator can now see this result
                                self.log("5. Verifying coordinator can see new result...")
                                coord_headers = {'Authorization': f'Bearer {self.coordinator_token}'}
                                response = self.session.get(f"{BASE_URL}/tests/session/{self.team_building_session_id}/results", headers=coord_headers)
                                
                                if response.status_code == 200:
                                    coord_results = response.json()
                                    self.log(f"✅ Coordinator can see {len(coord_results)} test results")
                                else:
                                    self.log(f"❌ Coordinator cannot access test results: {response.status_code}")
                            else:
                                self.log(f"❌ Pre-test submission failed: {response.status_code} - {response.text}")
                        else:
                            self.log("❌ Pre-test has no questions")
                    else:
                        self.log("⚠️ No pre-tests available for participant")
                        
                elif response.status_code == 403:
                    self.log("❌ Participant access denied to available tests (403 Forbidden)")
                elif response.status_code == 500:
                    self.log("❌ Server error when getting available tests (500 Internal Server Error)")
                    self.log("   This might be the KeyError: 'title' issue mentioned in test_result.md")
                else:
                    self.log(f"❌ Get available tests failed: {response.status_code} - {response.text}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Participant workflow test error: {str(e)}", "ERROR")
            return False
    
    # ============ PHASE 4: CROSS-REFERENCE CHECK ============
    
    def phase4_cross_reference_check(self):
        """PHASE 4: Cross-Reference Check"""
        self.log("=== PHASE 4: CROSS-REFERENCE CHECK ===")
        
        try:
            # 1. Compare database test_results vs API responses
            self.log("1. Comparing database test_results vs API responses...")
            
            if not self.test_results_data:
                self.log("❌ No database test results to compare")
                return False
            
            # Get API results for comparison
            coord_headers = {'Authorization': f'Bearer {self.coordinator_token}'}
            response = self.session.get(f"{BASE_URL}/tests/session/{self.team_building_session_id}/results", headers=coord_headers)
            
            api_results = []
            if response.status_code == 200:
                api_results = response.json()
                self.log(f"✅ Database has {len(self.test_results_data)} results, API returns {len(api_results)} results")
                
                if len(self.test_results_data) != len(api_results):
                    self.log("❌ MISMATCH: Database and API result counts don't match", "ERROR")
                else:
                    self.log("✅ Database and API result counts match")
            else:
                self.log(f"❌ Could not get API results for comparison: {response.status_code}")
            
            # 2. Check if session_id in test_results matches "Team Building" session
            self.log("2. Verifying session_id consistency...")
            session_id_mismatches = 0
            
            for i, result in enumerate(self.test_results_data):
                if result.get('session_id') != self.team_building_session_id:
                    session_id_mismatches += 1
                    self.log(f"   ❌ Result {i+1}: session_id mismatch")
                    self.log(f"      Expected: {self.team_building_session_id}")
                    self.log(f"      Found: {result.get('session_id', 'N/A')}")
            
            if session_id_mismatches == 0:
                self.log("✅ All test results have correct session_id")
            else:
                self.log(f"❌ {session_id_mismatches} test results have incorrect session_id", "ERROR")
            
            # 3. Verify test_type field exists and is "pre" or "post"
            self.log("3. Verifying test_type field values...")
            invalid_test_types = 0
            
            for i, result in enumerate(self.test_results_data):
                test_type = result.get('test_type')
                if test_type not in ['pre', 'post']:
                    invalid_test_types += 1
                    self.log(f"   ❌ Result {i+1}: invalid test_type = {test_type}")
                else:
                    self.log(f"   ✅ Result {i+1}: valid test_type = {test_type}")
            
            if invalid_test_types == 0:
                self.log("✅ All test results have valid test_type")
            else:
                self.log(f"❌ {invalid_test_types} test results have invalid test_type", "ERROR")
            
            # 4. Check if coordinator_id in session matches malek's ID
            self.log("4. Verifying coordinator assignment...")
            
            # Get malek's user ID
            coord_headers = {'Authorization': f'Bearer {self.coordinator_token}'}
            response = self.session.get(f"{BASE_URL}/auth/me", headers=coord_headers)
            
            if response.status_code == 200:
                malek_user_data = response.json()
                malek_id = malek_user_data['id']
                session_coordinator_id = self.team_building_session.get('coordinator_id')
                
                self.log(f"   Malek's ID: {malek_id}")
                self.log(f"   Session coordinator_id: {session_coordinator_id}")
                
                if malek_id == session_coordinator_id:
                    self.log("✅ Coordinator assignment is correct")
                else:
                    self.log("❌ MISMATCH: Coordinator assignment is incorrect", "ERROR")
                    self.log("   This could explain why malek cannot see the test results")
            else:
                self.log("❌ Could not verify coordinator assignment")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Cross-reference check error: {str(e)}", "ERROR")
            return False
    
    # ============ PHASE 5: ANALYTICS CALCULATION ============
    
    def phase5_analytics_calculation(self):
        """PHASE 5: Analytics Calculation"""
        self.log("=== PHASE 5: ANALYTICS CALCULATION ===")
        
        try:
            # 1. Manually calculate what stats should show
            self.log("1. Calculating expected statistics...")
            
            # Total participants in Team Building session
            total_participants = len(self.participant_access_data)
            self.log(f"   Total participants: {total_participants}")
            
            # Count pre-test and post-test results
            pre_test_count = 0
            post_test_count = 0
            
            for result in self.test_results_data:
                test_type = result.get('test_type')
                if test_type == 'pre':
                    pre_test_count += 1
                elif test_type == 'post':
                    post_test_count += 1
            
            self.log(f"   Pre-test results: {pre_test_count}")
            self.log(f"   Post-test results: {post_test_count}")
            
            # 2. Compare with what API returns
            self.log("2. Comparing with API analytics...")
            
            coord_headers = {'Authorization': f'Bearer {self.coordinator_token}'}
            
            # Try to get session results summary
            response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}/results-summary", headers=coord_headers)
            
            if response.status_code == 200:
                api_summary = response.json()
                self.log("✅ API results summary retrieved:")
                
                api_total = api_summary.get('total_participants', 0)
                api_pre_tests = api_summary.get('pre_test_completed', 0)
                api_post_tests = api_summary.get('post_test_completed', 0)
                
                self.log(f"   API Total participants: {api_total}")
                self.log(f"   API Pre-test completed: {api_pre_tests}")
                self.log(f"   API Post-test completed: {api_post_tests}")
                
                # Compare expected vs actual
                if total_participants == api_total:
                    self.log("✅ Total participants match")
                else:
                    self.log(f"❌ Total participants mismatch: Expected {total_participants}, API shows {api_total}")
                
                if pre_test_count == api_pre_tests:
                    self.log("✅ Pre-test counts match")
                else:
                    self.log(f"❌ Pre-test count mismatch: Expected {pre_test_count}, API shows {api_pre_tests}")
                
                if post_test_count == api_post_tests:
                    self.log("✅ Post-test counts match")
                else:
                    self.log(f"❌ Post-test count mismatch: Expected {post_test_count}, API shows {api_post_tests}")
                    
            else:
                self.log(f"❌ Could not get API results summary: {response.status_code} - {response.text}")
                self.log("   This might be the root cause of the coordinator portal issue")
            
            # Try alternative analytics endpoints
            self.log("3. Testing alternative analytics endpoints...")
            
            # Test session status endpoint
            response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}/status", headers=coord_headers)
            
            if response.status_code == 200:
                status_data = response.json()
                self.log("✅ Session status endpoint working:")
                self.log(f"   Status: {status_data}")
            else:
                self.log(f"❌ Session status endpoint failed: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Analytics calculation error: {str(e)}", "ERROR")
            return False
    
    def generate_investigation_report(self):
        """Generate final investigation report"""
        self.log("=== INVESTIGATION REPORT ===")
        
        self.log("SUMMARY OF FINDINGS:")
        
        # Database findings
        if self.team_building_session:
            self.log(f"✅ Team Building session found in database (ID: {self.team_building_session_id})")
        else:
            self.log("❌ Team Building session NOT found in database")
        
        if self.test_results_data:
            self.log(f"✅ {len(self.test_results_data)} test results found in database")
            
            # Check test_type distribution
            pre_count = sum(1 for r in self.test_results_data if r.get('test_type') == 'pre')
            post_count = sum(1 for r in self.test_results_data if r.get('test_type') == 'post')
            self.log(f"   - Pre-tests: {pre_count}")
            self.log(f"   - Post-tests: {post_count}")
        else:
            self.log("❌ NO test results found in database")
        
        if self.participant_access_data:
            self.log(f"✅ {len(self.participant_access_data)} participant access records found")
        else:
            self.log("❌ NO participant access records found")
        
        self.log("\nRECOMMENDATIONS:")
        self.log("1. Check coordinator_id assignment in Team Building session")
        self.log("2. Verify API endpoint /api/sessions/{session_id}/results-summary is working")
        self.log("3. Ensure test_type field is present in all test results")
        self.log("4. Check participant access permissions for Team Building session")
        self.log("5. Verify coordinator role permissions for accessing test results")
    
    def run_investigation(self):
        """Run the complete investigation"""
        self.log("🔍 STARTING TEAM BUILDING SESSION INVESTIGATION")
        self.log("=" * 80)
        
        success_count = 0
        total_phases = 5
        
        # Setup
        if not self.connect_to_database():
            self.log("❌ Cannot proceed without database connection", "ERROR")
            return False
        
        if not self.setup_authentication():
            self.log("❌ Cannot proceed without authentication", "ERROR")
            return False
        
        # Run investigation phases
        phases = [
            ("PHASE 1: Database Investigation", self.phase1_database_investigation),
            ("PHASE 2: Backend API Testing", self.phase2_backend_api_testing),
            ("PHASE 3: Participant Workflow Test", self.phase3_participant_workflow_test),
            ("PHASE 4: Cross-Reference Check", self.phase4_cross_reference_check),
            ("PHASE 5: Analytics Calculation", self.phase5_analytics_calculation)
        ]
        
        for phase_name, phase_func in phases:
            self.log(f"\n🔍 Starting {phase_name}...")
            try:
                if phase_func():
                    success_count += 1
                    self.log(f"✅ {phase_name} completed successfully")
                else:
                    self.log(f"❌ {phase_name} failed", "ERROR")
            except Exception as e:
                self.log(f"❌ {phase_name} crashed: {str(e)}", "ERROR")
        
        # Generate report
        self.generate_investigation_report()
        
        # Final summary
        self.log(f"\n🎯 INVESTIGATION COMPLETE: {success_count}/{total_phases} phases successful")
        
        if success_count == total_phases:
            self.log("🎉 All investigation phases completed successfully!")
            return True
        else:
            self.log(f"⚠️ {total_phases - success_count} phases failed - issues identified")
            return False

def main():
    """Main function to run the investigation"""
    investigator = TeamBuildingInvestigator()
    
    try:
        success = investigator.run_investigation()
        
        if success:
            print("\n" + "="*80)
            print("🎉 INVESTIGATION COMPLETED SUCCESSFULLY")
            print("="*80)
            sys.exit(0)
        else:
            print("\n" + "="*80)
            print("❌ INVESTIGATION COMPLETED WITH ISSUES")
            print("="*80)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Investigation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Investigation failed with error: {str(e)}")
        sys.exit(1)
    finally:
        # Cleanup
        if hasattr(investigator, 'mongo_client') and investigator.mongo_client:
            investigator.mongo_client.close()

if __name__ == "__main__":
    main()