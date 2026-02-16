#!/usr/bin/env python3
"""
Coordinator Dashboard Specific Test
Focus on the specific issue: results-summary endpoint returning 0s despite data existing
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://finance-correction.preview.emergentagent.com/api"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"

class CoordinatorDashboardTester:
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
    
    def test_results_summary_endpoint(self):
        """Test the problematic results-summary endpoint"""
        self.log("=== TESTING RESULTS-SUMMARY ENDPOINT ===")
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        # Test the endpoint that's returning 0s
        self.log(f"Testing GET /api/sessions/{self.team_building_session_id}/results-summary")
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}/results-summary", headers=headers)
            
            self.log(f"Response Status: {response.status_code}")
            self.log(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ Results Summary Response:")
                self.log(f"   Raw Response: {json.dumps(data, indent=2)}")
                
                # Check specific fields
                total_participants = data.get('total_participants', 'N/A')
                pre_test_completed = data.get('pre_test_completed', 'N/A')
                post_test_completed = data.get('post_test_completed', 'N/A')
                
                self.log(f"   Total Participants: {total_participants}")
                self.log(f"   Pre-test Completed: {pre_test_completed}")
                self.log(f"   Post-test Completed: {post_test_completed}")
                
                # This is the issue - these should not be 0
                if total_participants == 0:
                    self.log("❌ ISSUE CONFIRMED: total_participants is 0 despite 3 participants existing", "ERROR")
                if pre_test_completed == 0:
                    self.log("❌ ISSUE CONFIRMED: pre_test_completed is 0 despite 4 pre-tests existing", "ERROR")
                if post_test_completed == 0:
                    self.log("❌ ISSUE CONFIRMED: post_test_completed is 0 despite 3 post-tests existing", "ERROR")
                
                return True
            else:
                self.log(f"❌ Results summary failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Results summary error: {str(e)}", "ERROR")
            return False
    
    def test_alternative_endpoints(self):
        """Test alternative endpoints that work correctly"""
        self.log("=== TESTING ALTERNATIVE ENDPOINTS ===")
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        # 1. Test session status endpoint (this works)
        self.log("1. Testing GET /api/sessions/{session_id}/status")
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}/status", headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.log("✅ Session Status (WORKING):")
                self.log(f"   {json.dumps(data, indent=2)}")
            else:
                self.log(f"❌ Session status failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Session status error: {str(e)}")
        
        # 2. Test direct test results endpoint (this works)
        self.log("2. Testing GET /api/tests/session/{session_id}/results")
        try:
            response = self.session.get(f"{BASE_URL}/tests/session/{self.team_building_session_id}/results", headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Direct Test Results (WORKING): {len(data)} results found")
                
                # Count by test type
                pre_count = sum(1 for r in data if r.get('test_type') == 'pre')
                post_count = sum(1 for r in data if r.get('test_type') == 'post')
                self.log(f"   Pre-tests: {pre_count}")
                self.log(f"   Post-tests: {post_count}")
            else:
                self.log(f"❌ Direct test results failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Direct test results error: {str(e)}")
        
        # 3. Test session details endpoint
        self.log("3. Testing GET /api/sessions/{session_id}")
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                participant_count = len(data.get('participant_ids', []))
                self.log(f"✅ Session Details (WORKING): {participant_count} participants")
            else:
                self.log(f"❌ Session details failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Session details error: {str(e)}")
    
    def test_coordinator_dashboard_data_flow(self):
        """Test the complete data flow that coordinator dashboard uses"""
        self.log("=== TESTING COORDINATOR DASHBOARD DATA FLOW ===")
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        # This is likely what the frontend is calling
        endpoints_to_test = [
            f"/sessions/{self.team_building_session_id}/results-summary",
            f"/sessions/{self.team_building_session_id}/participants",
            f"/sessions/{self.team_building_session_id}/analytics",
            f"/sessions/{self.team_building_session_id}"
        ]
        
        for endpoint in endpoints_to_test:
            self.log(f"Testing GET /api{endpoint}")
            try:
                response = self.session.get(f"{BASE_URL}{endpoint}", headers=headers)
                self.log(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        self.log(f"   Response: Array with {len(data)} items")
                    elif isinstance(data, dict):
                        self.log(f"   Response: Object with keys: {list(data.keys())}")
                    else:
                        self.log(f"   Response: {type(data)} - {str(data)[:100]}")
                else:
                    self.log(f"   Error: {response.text[:200]}")
                    
            except Exception as e:
                self.log(f"   Exception: {str(e)}")
    
    def run_test(self):
        """Run the complete test"""
        self.log("🔍 STARTING COORDINATOR DASHBOARD SPECIFIC TEST")
        self.log("=" * 60)
        
        if not self.login_coordinator():
            return False
        
        # Test the problematic endpoint
        self.test_results_summary_endpoint()
        
        # Test working endpoints for comparison
        self.test_alternative_endpoints()
        
        # Test complete data flow
        self.test_coordinator_dashboard_data_flow()
        
        self.log("\n🎯 ROOT CAUSE ANALYSIS:")
        self.log("The /api/sessions/{session_id}/results-summary endpoint is returning 0s")
        self.log("despite the database containing 7 test results and 3 participants.")
        self.log("This suggests the endpoint's calculation logic is incorrect.")
        self.log("\n✅ WORKING ENDPOINTS:")
        self.log("- /api/sessions/{session_id}/status")
        self.log("- /api/tests/session/{session_id}/results")
        self.log("- /api/sessions/{session_id}")
        self.log("\n❌ BROKEN ENDPOINT:")
        self.log("- /api/sessions/{session_id}/results-summary")
        
        return True

def main():
    tester = CoordinatorDashboardTester()
    tester.run_test()

if __name__ == "__main__":
    main()