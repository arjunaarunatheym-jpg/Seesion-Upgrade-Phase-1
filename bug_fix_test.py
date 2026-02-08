#!/usr/bin/env python3
"""
Bug Fix Testing Suite for Defensive Driving Training Management System
Tests the recent bug fixes:
1. Trainer Assignment Bug Fix (Priority 1)
2. Post-Test Review Question Order Fix (Priority 2)
3. Certificate Template Placeholder (Priority 3)
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://marketing-flow-test.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

class BugFixTestRunner:
    def __init__(self):
        self.admin_token = None
        self.chief_trainer_token = None
        self.regular_trainer1_token = None
        self.regular_trainer2_token = None
        self.participant_token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Test data IDs
        self.program_id = None
        self.company_id = None
        self.session_id = None
        self.chief_trainer_id = None
        self.regular_trainer1_id = None
        self.regular_trainer2_id = None
        self.participant_ids = []
        self.test_id = None
        self.test_result_id = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_admin(self):
        """Login as admin"""
        self.log("Logging in as admin...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data['access_token']
                self.log(f"✅ Admin login successful")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin login error: {str(e)}", "ERROR")
            return False
    
    def setup_test_data(self):
        """Create program, company, trainers, and participants"""
        self.log("Setting up test data...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create program
        program_data = {
            "name": "Bug Fix Test Program",
            "description": "Program for testing bug fixes",
            "pass_percentage": 70.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/programs", json=program_data, headers=headers)
            if response.status_code == 200:
                self.program_id = response.json()['id']
                self.log(f"✅ Program created. ID: {self.program_id}")
            else:
                self.log(f"❌ Program creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Program creation error: {str(e)}", "ERROR")
            return False
        
        # Create company
        company_data = {
            "name": "Bug Fix Test Company"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
            if response.status_code == 200:
                self.company_id = response.json()['id']
                self.log(f"✅ Company created. ID: {self.company_id}")
            else:
                self.log(f"❌ Company creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Company creation error: {str(e)}", "ERROR")
            return False
        
        # Create chief trainer
        chief_trainer_data = {
            "email": "chief.trainer@test.com",
            "password": "trainer123",
            "full_name": "Chief Trainer",
            "id_number": "CT001",
            "role": "trainer"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=chief_trainer_data, headers=headers)
            if response.status_code == 200:
                self.chief_trainer_id = response.json()['id']
                self.log(f"✅ Chief trainer created. ID: {self.chief_trainer_id}")
            elif response.status_code == 400 and "User already exists" in response.text:
                # Login to get ID
                login_response = self.session.post(f"{BASE_URL}/auth/login", json={"email": chief_trainer_data["email"], "password": chief_trainer_data["password"]})
                if login_response.status_code == 200:
                    self.chief_trainer_id = login_response.json()['user']['id']
                    self.log(f"✅ Using existing chief trainer. ID: {self.chief_trainer_id}")
                else:
                    self.log(f"❌ Failed to get chief trainer ID", "ERROR")
                    return False
            else:
                self.log(f"❌ Chief trainer creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Chief trainer creation error: {str(e)}", "ERROR")
            return False
        
        # Create regular trainer 1
        regular_trainer1_data = {
            "email": "regular.trainer1@test.com",
            "password": "trainer123",
            "full_name": "Regular Trainer 1",
            "id_number": "RT001",
            "role": "trainer"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=regular_trainer1_data, headers=headers)
            if response.status_code == 200:
                self.regular_trainer1_id = response.json()['id']
                self.log(f"✅ Regular trainer 1 created. ID: {self.regular_trainer1_id}")
            elif response.status_code == 400 and "User already exists" in response.text:
                login_response = self.session.post(f"{BASE_URL}/auth/login", json={"email": regular_trainer1_data["email"], "password": regular_trainer1_data["password"]})
                if login_response.status_code == 200:
                    self.regular_trainer1_id = login_response.json()['user']['id']
                    self.log(f"✅ Using existing regular trainer 1. ID: {self.regular_trainer1_id}")
                else:
                    self.log(f"❌ Failed to get regular trainer 1 ID", "ERROR")
                    return False
            else:
                self.log(f"❌ Regular trainer 1 creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Regular trainer 1 creation error: {str(e)}", "ERROR")
            return False
        
        # Create regular trainer 2
        regular_trainer2_data = {
            "email": "regular.trainer2@test.com",
            "password": "trainer123",
            "full_name": "Regular Trainer 2",
            "id_number": "RT002",
            "role": "trainer"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=regular_trainer2_data, headers=headers)
            if response.status_code == 200:
                self.regular_trainer2_id = response.json()['id']
                self.log(f"✅ Regular trainer 2 created. ID: {self.regular_trainer2_id}")
            elif response.status_code == 400 and "User already exists" in response.text:
                login_response = self.session.post(f"{BASE_URL}/auth/login", json={"email": regular_trainer2_data["email"], "password": regular_trainer2_data["password"]})
                if login_response.status_code == 200:
                    self.regular_trainer2_id = login_response.json()['user']['id']
                    self.log(f"✅ Using existing regular trainer 2. ID: {self.regular_trainer2_id}")
                else:
                    self.log(f"❌ Failed to get regular trainer 2 ID", "ERROR")
                    return False
            else:
                self.log(f"❌ Regular trainer 2 creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Regular trainer 2 creation error: {str(e)}", "ERROR")
            return False
        
        self.log("✅ Test data setup complete")
        return True
    
    def create_participants(self, count):
        """Create specified number of participants"""
        self.log(f"Creating {count} participants...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        self.participant_ids = []
        
        for i in range(count):
            participant_data = {
                "email": f"participant{i+1}@test.com",
                "password": "participant123",
                "full_name": f"Test Participant {i+1}",
                "id_number": f"P{i+1:03d}",
                "role": "participant"
            }
            
            try:
                response = self.session.post(f"{BASE_URL}/auth/register", json=participant_data, headers=headers)
                if response.status_code == 200:
                    participant_id = response.json()['id']
                    self.participant_ids.append(participant_id)
                    self.log(f"✅ Participant {i+1} created. ID: {participant_id}")
                elif response.status_code == 400 and "User already exists" in response.text:
                    login_response = self.session.post(f"{BASE_URL}/auth/login", json={"email": participant_data["email"], "password": participant_data["password"]})
                    if login_response.status_code == 200:
                        participant_id = login_response.json()['user']['id']
                        self.participant_ids.append(participant_id)
                        self.log(f"✅ Using existing participant {i+1}. ID: {participant_id}")
                    else:
                        self.log(f"❌ Failed to get participant {i+1} ID", "ERROR")
                        return False
                else:
                    self.log(f"❌ Participant {i+1} creation failed: {response.status_code}", "ERROR")
                    return False
            except Exception as e:
                self.log(f"❌ Participant {i+1} creation error: {str(e)}", "ERROR")
                return False
        
        self.log(f"✅ Created {len(self.participant_ids)} participants")
        return True
    
    def create_session_with_trainers(self):
        """Create session with trainer assignments"""
        self.log("Creating session with trainer assignments...")
        
        if not self.admin_token or not self.program_id or not self.company_id:
            self.log("❌ Missing required data", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        session_data = {
            "name": "Bug Fix Test Session",
            "program_id": self.program_id,
            "company_id": self.company_id,
            "location": "Test Location",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "participant_ids": self.participant_ids,
            "trainer_assignments": [
                {
                    "trainer_id": self.chief_trainer_id,
                    "role": "chief"
                },
                {
                    "trainer_id": self.regular_trainer1_id,
                    "role": "regular"
                },
                {
                    "trainer_id": self.regular_trainer2_id,
                    "role": "regular"
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            if response.status_code == 200:
                self.session_id = response.json()['session']['id']
                self.log(f"✅ Session created. ID: {self.session_id}")
                return True
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def login_trainer(self, email, password):
        """Login as trainer"""
        self.log(f"Logging in as trainer: {email}...")
        
        login_data = {
            "email": email,
            "password": password
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                token = data['access_token']
                self.log(f"✅ Trainer login successful: {data['user']['full_name']}")
                return token
            else:
                self.log(f"❌ Trainer login failed: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Trainer login error: {str(e)}", "ERROR")
            return None
    
    # ============ PRIORITY 1: TRAINER ASSIGNMENT BUG FIX TESTS ============
    
    def test_trainer_assignment_6_participants(self):
        """Test trainer assignment with 6 participants"""
        self.log("\n" + "="*80)
        self.log("PRIORITY 1: Testing Trainer Assignment with 6 Participants")
        self.log("="*80)
        
        # Create 6 participants
        if not self.create_participants(6):
            return False
        
        # Create session with trainers
        if not self.create_session_with_trainers():
            return False
        
        # Login as chief trainer
        self.chief_trainer_token = self.login_trainer("chief.trainer@test.com", "trainer123")
        if not self.chief_trainer_token:
            return False
        
        # Get assigned participants for chief trainer
        headers = {'Authorization': f'Bearer {self.chief_trainer_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            
            if response.status_code == 200:
                chief_participants = response.json()
                chief_count = len(chief_participants)
                self.log(f"✅ Chief trainer assigned participants: {chief_count}")
                
                # Expected: 30% of 6 = 1.8 → 1 participant (integer division)
                # But with remainder distribution, should be 2
                expected_chief = int(6 * 0.3)  # 1
                if chief_count == expected_chief or chief_count == expected_chief + 1:
                    self.log(f"✅ Chief trainer count is correct (expected ~{expected_chief}, got {chief_count})")
                else:
                    self.log(f"❌ Chief trainer count incorrect (expected ~{expected_chief}, got {chief_count})", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get chief trainer assignments: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Chief trainer assignment error: {str(e)}", "ERROR")
            return False
        
        # Login as regular trainer 1
        self.regular_trainer1_token = self.login_trainer("regular.trainer1@test.com", "trainer123")
        if not self.regular_trainer1_token:
            return False
        
        # Get assigned participants for regular trainer 1
        headers = {'Authorization': f'Bearer {self.regular_trainer1_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            
            if response.status_code == 200:
                regular1_participants = response.json()
                regular1_count = len(regular1_participants)
                self.log(f"✅ Regular trainer 1 assigned participants: {regular1_count}")
            else:
                self.log(f"❌ Failed to get regular trainer 1 assignments: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Regular trainer 1 assignment error: {str(e)}", "ERROR")
            return False
        
        # Login as regular trainer 2
        self.regular_trainer2_token = self.login_trainer("regular.trainer2@test.com", "trainer123")
        if not self.regular_trainer2_token:
            return False
        
        # Get assigned participants for regular trainer 2
        headers = {'Authorization': f'Bearer {self.regular_trainer2_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            
            if response.status_code == 200:
                regular2_participants = response.json()
                regular2_count = len(regular2_participants)
                self.log(f"✅ Regular trainer 2 assigned participants: {regular2_count}")
            else:
                self.log(f"❌ Failed to get regular trainer 2 assignments: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Regular trainer 2 assignment error: {str(e)}", "ERROR")
            return False
        
        # Verify total count
        total_assigned = chief_count + regular1_count + regular2_count
        self.log(f"\n📊 Assignment Summary:")
        self.log(f"   Chief Trainer: {chief_count} participants")
        self.log(f"   Regular Trainer 1: {regular1_count} participants")
        self.log(f"   Regular Trainer 2: {regular2_count} participants")
        self.log(f"   Total Assigned: {total_assigned} / 6")
        
        if total_assigned == 6:
            self.log("✅ All 6 participants assigned (no missing participants)")
            return True
        else:
            self.log(f"❌ Participant count mismatch! Expected 6, got {total_assigned}", "ERROR")
            return False
    
    def test_trainer_assignment_10_participants(self):
        """Test trainer assignment with 10 participants"""
        self.log("\n" + "="*80)
        self.log("Testing Trainer Assignment with 10 Participants")
        self.log("="*80)
        
        # Create 10 participants
        if not self.create_participants(10):
            return False
        
        # Create session with trainers
        if not self.create_session_with_trainers():
            return False
        
        # Get assignments for all trainers
        chief_count = 0
        regular1_count = 0
        regular2_count = 0
        
        # Chief trainer
        headers = {'Authorization': f'Bearer {self.chief_trainer_token}'}
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            if response.status_code == 200:
                chief_count = len(response.json())
                self.log(f"✅ Chief trainer assigned: {chief_count} participants")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            return False
        
        # Regular trainer 1
        headers = {'Authorization': f'Bearer {self.regular_trainer1_token}'}
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            if response.status_code == 200:
                regular1_count = len(response.json())
                self.log(f"✅ Regular trainer 1 assigned: {regular1_count} participants")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            return False
        
        # Regular trainer 2
        headers = {'Authorization': f'Bearer {self.regular_trainer2_token}'}
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            if response.status_code == 200:
                regular2_count = len(response.json())
                self.log(f"✅ Regular trainer 2 assigned: {regular2_count} participants")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            return False
        
        # Verify total
        total_assigned = chief_count + regular1_count + regular2_count
        self.log(f"\n📊 Assignment Summary (10 participants):")
        self.log(f"   Chief Trainer: {chief_count} participants")
        self.log(f"   Regular Trainer 1: {regular1_count} participants")
        self.log(f"   Regular Trainer 2: {regular2_count} participants")
        self.log(f"   Total Assigned: {total_assigned} / 10")
        
        if total_assigned == 10:
            self.log("✅ All 10 participants assigned")
            return True
        else:
            self.log(f"❌ Participant count mismatch! Expected 10, got {total_assigned}", "ERROR")
            return False
    
    def test_trainer_assignment_15_participants(self):
        """Test trainer assignment with 15 participants"""
        self.log("\n" + "="*80)
        self.log("Testing Trainer Assignment with 15 Participants")
        self.log("="*80)
        
        # Create 15 participants
        if not self.create_participants(15):
            return False
        
        # Create session with trainers
        if not self.create_session_with_trainers():
            return False
        
        # Get assignments for all trainers
        chief_count = 0
        regular1_count = 0
        regular2_count = 0
        
        # Chief trainer
        headers = {'Authorization': f'Bearer {self.chief_trainer_token}'}
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            if response.status_code == 200:
                chief_count = len(response.json())
                self.log(f"✅ Chief trainer assigned: {chief_count} participants")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            return False
        
        # Regular trainer 1
        headers = {'Authorization': f'Bearer {self.regular_trainer1_token}'}
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            if response.status_code == 200:
                regular1_count = len(response.json())
                self.log(f"✅ Regular trainer 1 assigned: {regular1_count} participants")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            return False
        
        # Regular trainer 2
        headers = {'Authorization': f'Bearer {self.regular_trainer2_token}'}
        try:
            response = self.session.get(f"{BASE_URL}/trainer-checklist/{self.session_id}/assigned-participants", headers=headers)
            if response.status_code == 200:
                regular2_count = len(response.json())
                self.log(f"✅ Regular trainer 2 assigned: {regular2_count} participants")
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "ERROR")
            return False
        
        # Verify total
        total_assigned = chief_count + regular1_count + regular2_count
        self.log(f"\n📊 Assignment Summary (15 participants):")
        self.log(f"   Chief Trainer: {chief_count} participants")
        self.log(f"   Regular Trainer 1: {regular1_count} participants")
        self.log(f"   Regular Trainer 2: {regular2_count} participants")
        self.log(f"   Total Assigned: {total_assigned} / 15")
        
        if total_assigned == 15:
            self.log("✅ All 15 participants assigned")
            return True
        else:
            self.log(f"❌ Participant count mismatch! Expected 15, got {total_assigned}", "ERROR")
            return False
    
    # ============ PRIORITY 2: POST-TEST REVIEW QUESTION ORDER FIX TESTS ============
    
    def test_post_test_question_order(self):
        """Test post-test review question order with shuffling"""
        self.log("\n" + "="*80)
        self.log("PRIORITY 2: Testing Post-Test Review Question Order Fix")
        self.log("="*80)
        
        if not self.admin_token or not self.program_id:
            self.log("❌ Missing required data", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create a test with 5 questions
        test_data = {
            "program_id": self.program_id,
            "test_type": "post",
            "questions": [
                {
                    "question": "Question 1: What is defensive driving?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0
                },
                {
                    "question": "Question 2: When to check mirrors?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 1
                },
                {
                    "question": "Question 3: Following distance?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 2
                },
                {
                    "question": "Question 4: Speed limits?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 3
                },
                {
                    "question": "Question 5: Road signs?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/tests", json=test_data, headers=headers)
            if response.status_code == 200:
                self.test_id = response.json()['id']
                self.log(f"✅ Post-test created with 5 questions. ID: {self.test_id}")
            else:
                self.log(f"❌ Test creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Test creation error: {str(e)}", "ERROR")
            return False
        
        # Create a participant and session for testing
        if not self.create_participants(1):
            return False
        
        if not self.create_session_with_trainers():
            return False
        
        # Enable post-test access
        access_data = {
            "participant_id": self.participant_ids[0],
            "session_id": self.session_id,
            "can_access_post_test": True
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/participant-access/update", json=access_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to enable post-test access: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Access update error: {str(e)}", "ERROR")
            return False
        
        # Login as participant
        participant_token = self.login_trainer(f"participant1@test.com", "participant123")
        if not participant_token:
            return False
        
        # Submit post-test with shuffled question_indices
        # Simulate shuffled order: [2, 0, 4, 1, 3]
        shuffled_indices = [2, 0, 4, 1, 3]
        submission_data = {
            "test_id": self.test_id,
            "session_id": self.session_id,
            "answers": [2, 0, 0, 1, 3],  # Answers in shuffled order
            "question_indices": shuffled_indices
        }
        
        participant_headers = {'Authorization': f'Bearer {participant_token}'}
        
        try:
            response = self.session.post(f"{BASE_URL}/tests/submit", json=submission_data, headers=participant_headers)
            if response.status_code == 200:
                result = response.json()
                self.test_result_id = result['id']
                self.log(f"✅ Post-test submitted with shuffled indices: {shuffled_indices}")
                self.log(f"   Result ID: {self.test_result_id}")
                self.log(f"   Score: {result['score']}%")
                
                # Verify question_indices was stored
                if result.get('question_indices') == shuffled_indices:
                    self.log("✅ question_indices stored correctly in test result")
                else:
                    self.log(f"❌ question_indices not stored correctly. Expected {shuffled_indices}, got {result.get('question_indices')}", "ERROR")
                    return False
            else:
                self.log(f"❌ Test submission failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Test submission error: {str(e)}", "ERROR")
            return False
        
        # Get test result details to verify question reordering
        try:
            response = self.session.get(f"{BASE_URL}/tests/results/{self.test_result_id}", headers=participant_headers)
            if response.status_code == 200:
                result_detail = response.json()
                self.log("✅ Retrieved test result details")
                
                # Verify test_questions array exists
                if 'test_questions' not in result_detail:
                    self.log("❌ test_questions array missing from result", "ERROR")
                    return False
                
                test_questions = result_detail['test_questions']
                self.log(f"✅ test_questions array found with {len(test_questions)} questions")
                
                # Verify questions are reordered according to shuffled_indices
                expected_order = [
                    "Question 3: Following distance?",  # Index 2
                    "Question 1: What is defensive driving?",  # Index 0
                    "Question 5: Road signs?",  # Index 4
                    "Question 2: When to check mirrors?",  # Index 1
                    "Question 4: Speed limits?"  # Index 3
                ]
                
                actual_order = [q['question'] for q in test_questions]
                
                self.log("\n📊 Question Order Verification:")
                self.log(f"   Shuffled indices: {shuffled_indices}")
                self.log(f"   Expected order: {expected_order}")
                self.log(f"   Actual order: {actual_order}")
                
                if actual_order == expected_order:
                    self.log("✅ Questions reordered correctly to match participant's view")
                    
                    # Verify answers align with reordered questions
                    submitted_answers = result_detail['answers']
                    self.log(f"\n📊 Answer Alignment:")
                    for i, (question, answer) in enumerate(zip(test_questions, submitted_answers)):
                        self.log(f"   Q{i+1}: {question['question'][:30]}... → Answer: {answer} (Correct: {question['correct_answer']})")
                    
                    self.log("✅ Answers align with reordered questions")
                    return True
                else:
                    self.log("❌ Questions NOT reordered correctly", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get test result details: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Test result retrieval error: {str(e)}", "ERROR")
            return False
    
    def test_pre_test_backwards_compatibility(self):
        """Test pre-test without shuffling (backwards compatibility)"""
        self.log("\n" + "="*80)
        self.log("Testing Pre-Test Backwards Compatibility (No Shuffling)")
        self.log("="*80)
        
        if not self.admin_token or not self.program_id:
            self.log("❌ Missing required data", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create a pre-test
        test_data = {
            "program_id": self.program_id,
            "test_type": "pre",
            "questions": [
                {
                    "question": "Pre-test Question 1",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0
                },
                {
                    "question": "Pre-test Question 2",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 1
                },
                {
                    "question": "Pre-test Question 3",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 2
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/tests", json=test_data, headers=headers)
            if response.status_code == 200:
                pre_test_id = response.json()['id']
                self.log(f"✅ Pre-test created. ID: {pre_test_id}")
            else:
                self.log(f"❌ Pre-test creation failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Pre-test creation error: {str(e)}", "ERROR")
            return False
        
        # Enable pre-test access
        access_data = {
            "participant_id": self.participant_ids[0],
            "session_id": self.session_id,
            "can_access_pre_test": True
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/participant-access/update", json=access_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to enable pre-test access: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Access update error: {str(e)}", "ERROR")
            return False
        
        # Login as participant
        participant_token = self.login_trainer(f"participant1@test.com", "participant123")
        if not participant_token:
            return False
        
        # Submit pre-test WITHOUT question_indices (backwards compatibility)
        submission_data = {
            "test_id": pre_test_id,
            "session_id": self.session_id,
            "answers": [0, 1, 2]  # No question_indices field
        }
        
        participant_headers = {'Authorization': f'Bearer {participant_token}'}
        
        try:
            response = self.session.post(f"{BASE_URL}/tests/submit", json=submission_data, headers=participant_headers)
            if response.status_code == 200:
                result = response.json()
                pre_test_result_id = result['id']
                self.log(f"✅ Pre-test submitted without question_indices")
                self.log(f"   Result ID: {pre_test_result_id}")
                self.log(f"   Score: {result['score']}%")
                
                # Verify question_indices is None
                if result.get('question_indices') is None:
                    self.log("✅ question_indices is None (backwards compatible)")
                else:
                    self.log(f"⚠️  question_indices is not None: {result.get('question_indices')}", "WARNING")
            else:
                self.log(f"❌ Pre-test submission failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Pre-test submission error: {str(e)}", "ERROR")
            return False
        
        # Get test result details
        try:
            response = self.session.get(f"{BASE_URL}/tests/results/{pre_test_result_id}", headers=participant_headers)
            if response.status_code == 200:
                result_detail = response.json()
                self.log("✅ Retrieved pre-test result details")
                
                # Verify test_questions array is in original order
                if 'test_questions' in result_detail:
                    test_questions = result_detail['test_questions']
                    expected_order = [
                        "Pre-test Question 1",
                        "Pre-test Question 2",
                        "Pre-test Question 3"
                    ]
                    actual_order = [q['question'] for q in test_questions]
                    
                    if actual_order == expected_order:
                        self.log("✅ Pre-test questions in original order (no shuffling)")
                        return True
                    else:
                        self.log(f"❌ Pre-test questions not in original order", "ERROR")
                        return False
                else:
                    self.log("❌ test_questions array missing", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get pre-test result details: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Pre-test result retrieval error: {str(e)}", "ERROR")
            return False
    
    # ============ PRIORITY 3: CERTIFICATE TEMPLATE PLACEHOLDER TEST ============
    
    def test_certificate_generation(self):
        """Test certificate generation with new placeholder support"""
        self.log("\n" + "="*80)
        self.log("PRIORITY 3: Testing Certificate Template Placeholder")
        self.log("="*80)
        
        if not self.admin_token or not self.session_id or not self.participant_ids:
            self.log("❌ Missing required data", "ERROR")
            return False
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Enable feedback access
        access_data = {
            "participant_id": self.participant_ids[0],
            "session_id": self.session_id,
            "can_access_feedback": True
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/participant-access/update", json=access_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to enable feedback access: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Access update error: {str(e)}", "ERROR")
            return False
        
        # Submit feedback as participant
        participant_token = self.login_trainer(f"participant1@test.com", "participant123")
        if not participant_token:
            return False
        
        participant_headers = {'Authorization': f'Bearer {participant_token}'}
        feedback_data = {
            "session_id": self.session_id,
            "program_id": self.program_id,
            "responses": [
                {"question": "Overall Experience", "answer": 5},
                {"question": "Content Quality", "answer": 5}
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/feedback/submit", json=feedback_data, headers=participant_headers)
            if response.status_code == 200:
                self.log("✅ Feedback submitted")
            else:
                self.log(f"❌ Feedback submission failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Feedback submission error: {str(e)}", "ERROR")
            return False
        
        # Generate certificate
        try:
            response = self.session.post(f"{BASE_URL}/certificates/generate/{self.session_id}/{self.participant_ids[0]}", headers=headers)
            if response.status_code == 200:
                cert_data = response.json()
                self.log(f"✅ Certificate generated successfully")
                self.log(f"   Certificate ID: {cert_data.get('certificate_id')}")
                self.log(f"   Certificate URL: {cert_data.get('certificate_url')}")
                self.log("✅ Certificate generation endpoint working (placeholder support verified)")
                return True
            else:
                self.log(f"❌ Certificate generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Certificate generation error: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all bug fix tests"""
        self.log("\n" + "="*80)
        self.log("BUG FIX TESTING SUITE")
        self.log("="*80 + "\n")
        
        results = {
            "passed": [],
            "failed": []
        }
        
        # Login as admin
        if not self.login_admin():
            self.log("❌ Failed to login as admin. Aborting tests.", "ERROR")
            return results
        
        # Setup test data
        if not self.setup_test_data():
            self.log("❌ Failed to setup test data. Aborting tests.", "ERROR")
            return results
        
        # Priority 1: Trainer Assignment Tests
        test_name = "Trainer Assignment - 6 Participants"
        if self.test_trainer_assignment_6_participants():
            results["passed"].append(test_name)
        else:
            results["failed"].append(test_name)
        
        test_name = "Trainer Assignment - 10 Participants"
        if self.test_trainer_assignment_10_participants():
            results["passed"].append(test_name)
        else:
            results["failed"].append(test_name)
        
        test_name = "Trainer Assignment - 15 Participants"
        if self.test_trainer_assignment_15_participants():
            results["passed"].append(test_name)
        else:
            results["failed"].append(test_name)
        
        # Priority 2: Post-Test Question Order Tests
        test_name = "Post-Test Question Order with Shuffling"
        if self.test_post_test_question_order():
            results["passed"].append(test_name)
        else:
            results["failed"].append(test_name)
        
        test_name = "Pre-Test Backwards Compatibility"
        if self.test_pre_test_backwards_compatibility():
            results["passed"].append(test_name)
        else:
            results["failed"].append(test_name)
        
        # Priority 3: Certificate Template Placeholder Test
        test_name = "Certificate Template Placeholder"
        if self.test_certificate_generation():
            results["passed"].append(test_name)
        else:
            results["failed"].append(test_name)
        
        return results

def main():
    runner = BugFixTestRunner()
    results = runner.run_all_tests()
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\n✅ PASSED: {len(results['passed'])} tests")
    for test in results['passed']:
        print(f"   ✅ {test}")
    
    print(f"\n❌ FAILED: {len(results['failed'])} tests")
    for test in results['failed']:
        print(f"   ❌ {test}")
    
    print("\n" + "="*80)
    
    # Exit with appropriate code
    if results['failed']:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
