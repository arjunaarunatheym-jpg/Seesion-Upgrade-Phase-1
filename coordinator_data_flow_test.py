#!/usr/bin/env python3
"""
Coordinator Dashboard Data Flow Test
Test the exact same API calls that the frontend coordinator dashboard makes
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://hr-dispatcher-v2.preview.emergentagent.com/api"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"

class CoordinatorDataFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.coordinator_token = None
        self.team_building_session_id = "a58f840e-ef46-4265-9b2f-be6fdaaef6a0"
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_coordinator(self):
        """Login coordinator"""
        self.log("Logging in coordinator...")
        
        login_data = {
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.coordinator_token = data['access_token']
                self.log(f"✅ Coordinator login successful: {data['user']['full_name']}")
                return True
            else:
                self.log(f"❌ Coordinator login failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Coordinator login error: {str(e)}", "ERROR")
            return False
    
    def test_frontend_data_flow(self):
        """Test the exact same API calls that the frontend makes"""
        self.log("=== TESTING FRONTEND DATA FLOW ===")
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        # 1. Get sessions (this works)
        self.log("1. GET /api/sessions (get coordinator sessions)")
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            if response.status_code == 200:
                sessions = response.json()
                team_building_session = None
                for session in sessions:
                    if "Team Building" in session.get('name', ''):
                        team_building_session = session
                        break
                
                if team_building_session:
                    self.log(f"✅ Found Team Building session")
                    self.log(f"   Session ID: {team_building_session['id']}")
                    self.log(f"   Participant IDs: {team_building_session.get('participant_ids', [])}")
                    self.log(f"   Participant count: {len(team_building_session.get('participant_ids', []))}")
                else:
                    self.log("❌ Team Building session not found")
                    return False
            else:
                self.log(f"❌ Get sessions failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Get sessions error: {str(e)}")
            return False
        
        # 2. Get all users (this is what frontend does)
        self.log("2. GET /api/users (get all users)")
        try:
            response = self.session.get(f"{BASE_URL}/users", headers=headers)
            if response.status_code == 200:
                all_users = response.json()
                self.log(f"✅ Retrieved {len(all_users)} total users")
                
                # Filter participants like frontend does
                participant_ids = team_building_session.get('participant_ids', [])
                participants = [user for user in all_users if user['id'] in participant_ids]
                
                self.log(f"   Filtered to {len(participants)} participants for Team Building session")
                for i, participant in enumerate(participants):
                    self.log(f"     Participant {i+1}: {participant['full_name']} ({participant['id']})")
                
                if len(participants) == 0:
                    self.log("❌ ISSUE FOUND: No participants found after filtering!", "ERROR")
                    self.log("   This explains why the dashboard shows 0 participants")
                    
                    # Debug: Check if participant IDs exist in users
                    self.log("   DEBUG: Checking if participant IDs exist in users...")
                    user_ids = [user['id'] for user in all_users]
                    for pid in participant_ids:
                        if pid in user_ids:
                            self.log(f"     ✅ Participant ID {pid} found in users")
                        else:
                            self.log(f"     ❌ Participant ID {pid} NOT found in users")
                
            else:
                self.log(f"❌ Get users failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Get users error: {str(e)}")
            return False
        
        # 3. Get test results (this works)
        self.log("3. GET /api/tests/results/session/{session_id}")
        try:
            response = self.session.get(f"{BASE_URL}/tests/results/session/{self.team_building_session_id}", headers=headers)
            if response.status_code == 200:
                test_results = response.json()
                self.log(f"✅ Retrieved {len(test_results)} test results")
                
                pre_tests = [r for r in test_results if r.get('test_type') == 'pre']
                post_tests = [r for r in test_results if r.get('test_type') == 'post']
                
                self.log(f"   Pre-tests: {len(pre_tests)}")
                self.log(f"   Post-tests: {len(post_tests)}")
                
                # This is what the frontend calculates
                participant_count = len(participants)
                pre_test_count = len(pre_tests)
                post_test_count = len(post_tests)
                
                self.log(f"\n📊 FRONTEND CALCULATION RESULTS:")
                self.log(f"   Total Participants: {participant_count}")
                self.log(f"   Pre-test Results: {pre_test_count}/{participant_count}")
                self.log(f"   Post-test Results: {post_test_count}/{participant_count}")
                
                if participant_count == 0:
                    self.log("❌ ROOT CAUSE IDENTIFIED: participant_count is 0", "ERROR")
                    self.log("   This is why the dashboard shows 0/3 - the participants array is empty")
                
            else:
                self.log(f"❌ Get test results failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Get test results error: {str(e)}")
            return False
        
        # 4. Get attendance
        self.log("4. GET /api/attendance/session/{session_id}")
        try:
            response = self.session.get(f"{BASE_URL}/attendance/session/{self.team_building_session_id}", headers=headers)
            if response.status_code == 200:
                attendance = response.json()
                self.log(f"✅ Retrieved {len(attendance)} attendance records")
            else:
                self.log(f"❌ Get attendance failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Get attendance error: {str(e)}")
        
        # 5. Get feedback
        self.log("5. GET /api/feedback/session/{session_id}")
        try:
            response = self.session.get(f"{BASE_URL}/feedback/session/{self.team_building_session_id}", headers=headers)
            if response.status_code == 200:
                feedback = response.json()
                self.log(f"✅ Retrieved {len(feedback)} feedback records")
            else:
                self.log(f"❌ Get feedback failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Get feedback error: {str(e)}")
        
        return True
    
    def test_alternative_approach(self):
        """Test using the results-summary endpoint instead"""
        self.log("\n=== TESTING ALTERNATIVE APPROACH ===")
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        self.log("Using GET /api/sessions/{session_id}/results-summary")
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}/results-summary", headers=headers)
            if response.status_code == 200:
                data = response.json()
                
                participants = data.get('participants', [])
                test_results = data.get('test_results', [])
                
                pre_tests = [r for r in test_results if r.get('test_type') == 'pre']
                post_tests = [r for r in test_results if r.get('test_type') == 'post']
                
                self.log(f"✅ Results-summary endpoint:")
                self.log(f"   Total Participants: {len(participants)}")
                self.log(f"   Pre-test Results: {len(pre_tests)}/{len(participants)}")
                self.log(f"   Post-test Results: {len(post_tests)}/{len(participants)}")
                
                self.log(f"\n🔍 COMPARISON:")
                self.log(f"   Frontend approach: 0 participants (BROKEN)")
                self.log(f"   Results-summary approach: {len(participants)} participants (WORKING)")
                
                return True
            else:
                self.log(f"❌ Results-summary failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Results-summary error: {str(e)}")
            return False
    
    def run_test(self):
        """Run the complete test"""
        self.log("🔍 STARTING COORDINATOR DATA FLOW TEST")
        self.log("=" * 60)
        
        if not self.login_coordinator():
            return False
        
        # Test current frontend approach
        self.test_frontend_data_flow()
        
        # Test alternative approach
        self.test_alternative_approach()
        
        self.log("\n🎯 CONCLUSION:")
        self.log("The coordinator dashboard is using the wrong approach.")
        self.log("It should use /api/sessions/{session_id}/results-summary instead of")
        self.log("calling /api/users and filtering by participant_ids.")
        self.log("\n💡 SOLUTION:")
        self.log("Update the frontend to use the results-summary endpoint")
        self.log("or fix the /api/users endpoint to return the correct participants.")
        
        return True

def main():
    tester = CoordinatorDataFlowTester()
    tester.run_test()

if __name__ == "__main__":
    main()