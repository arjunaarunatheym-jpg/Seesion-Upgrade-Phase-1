#!/usr/bin/env python3
"""
Test Type Field Investigation
Check why test_type filtering is not working in the frontend data flow
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://trainadmin-1.preview.emergentagent.com/api"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"

class TestTypeInvestigator:
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
        login_data = {
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.coordinator_token = data['access_token']
                self.log(f"✅ Coordinator login successful")
                return True
            else:
                self.log(f"❌ Login failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Login error: {str(e)}", "ERROR")
            return False
    
    def investigate_test_type_issue(self):
        """Investigate the test_type field issue"""
        self.log("=== INVESTIGATING TEST_TYPE FIELD ISSUE ===")
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        # Get test results from the endpoint the frontend uses
        self.log("1. GET /api/tests/results/session/{session_id} (frontend endpoint)")
        try:
            response = self.session.get(f"{BASE_URL}/tests/results/session/{self.team_building_session_id}", headers=headers)
            if response.status_code == 200:
                test_results = response.json()
                self.log(f"✅ Retrieved {len(test_results)} test results")
                
                # Check each result for test_type field
                pre_count = 0
                post_count = 0
                missing_type_count = 0
                
                for i, result in enumerate(test_results):
                    test_type = result.get('test_type')
                    self.log(f"   Result {i+1}:")
                    self.log(f"     ID: {result.get('id', 'N/A')}")
                    self.log(f"     Participant: {result.get('participant_name', 'N/A')}")
                    self.log(f"     Score: {result.get('score', 'N/A')}%")
                    self.log(f"     test_type: {test_type}")
                    
                    if test_type == 'pre':
                        pre_count += 1
                    elif test_type == 'post':
                        post_count += 1
                    else:
                        missing_type_count += 1
                        self.log(f"     ❌ Missing or invalid test_type!")
                
                self.log(f"\n📊 SUMMARY:")
                self.log(f"   Pre-tests: {pre_count}")
                self.log(f"   Post-tests: {post_count}")
                self.log(f"   Missing/Invalid type: {missing_type_count}")
                
                # This is what JavaScript would do
                js_pre_filter = [r for r in test_results if r.get('test_type') == 'pre']
                js_post_filter = [r for r in test_results if r.get('test_type') == 'post']
                
                self.log(f"\n🔍 JAVASCRIPT FILTER RESULTS:")
                self.log(f"   testResults.filter(r => r.test_type === 'pre').length = {len(js_pre_filter)}")
                self.log(f"   testResults.filter(r => r.test_type === 'post').length = {len(js_post_filter)}")
                
                if len(js_pre_filter) == 0 and len(js_post_filter) == 0:
                    self.log("❌ ROOT CAUSE CONFIRMED: JavaScript filtering returns 0 for both pre and post tests", "ERROR")
                
            else:
                self.log(f"❌ Get test results failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"❌ Get test results error: {str(e)}")
            return False
        
        # Compare with results-summary endpoint
        self.log("\n2. GET /api/sessions/{session_id}/results-summary (working endpoint)")
        try:
            response = self.session.get(f"{BASE_URL}/sessions/{self.team_building_session_id}/results-summary", headers=headers)
            if response.status_code == 200:
                data = response.json()
                test_results_summary = data.get('test_results', [])
                
                self.log(f"✅ Results-summary has {len(test_results_summary)} test results")
                
                pre_count = 0
                post_count = 0
                
                for i, result in enumerate(test_results_summary):
                    test_type = result.get('test_type')
                    if test_type == 'pre':
                        pre_count += 1
                    elif test_type == 'post':
                        post_count += 1
                
                self.log(f"   Pre-tests: {pre_count}")
                self.log(f"   Post-tests: {post_count}")
                
            else:
                self.log(f"❌ Results-summary failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Results-summary error: {str(e)}")
        
        return True
    
    def check_backend_routes(self):
        """Check which backend route is being called"""
        self.log("\n=== CHECKING BACKEND ROUTES ===")
        
        # The frontend calls /tests/results/session/{session_id}
        # Let's see what this maps to in the backend
        
        headers = {'Authorization': f'Bearer {self.coordinator_token}'}
        
        # Try different possible endpoints
        endpoints_to_test = [
            f"/tests/results/session/{self.team_building_session_id}",
            f"/tests/session/{self.team_building_session_id}/results",
            f"/sessions/{self.team_building_session_id}/test-results"
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
                        if data:
                            first_item = data[0]
                            test_type = first_item.get('test_type', 'MISSING')
                            self.log(f"   First item test_type: {test_type}")
                    else:
                        self.log(f"   Response: {type(data)}")
                elif response.status_code == 404:
                    self.log(f"   Not found")
                else:
                    self.log(f"   Error: {response.text[:100]}")
                    
            except Exception as e:
                self.log(f"   Exception: {str(e)}")
    
    def run_investigation(self):
        """Run the complete investigation"""
        self.log("🔍 STARTING TEST_TYPE FIELD INVESTIGATION")
        self.log("=" * 60)
        
        if not self.login_coordinator():
            return False
        
        self.investigate_test_type_issue()
        self.check_backend_routes()
        
        self.log("\n🎯 FINDINGS:")
        self.log("The coordinator dashboard shows 0/3 test completion because:")
        self.log("1. The frontend correctly finds 3 participants")
        self.log("2. The frontend gets 7 test results from /api/tests/results/session/{session_id}")
        self.log("3. BUT when filtering by test_type === 'pre' or 'post', it gets 0 results")
        self.log("4. This suggests the test_type field is missing or has wrong values")
        self.log("\n💡 SOLUTION:")
        self.log("Fix the /api/tests/results/session/{session_id} endpoint to include")
        self.log("proper test_type fields, or update frontend to use results-summary endpoint.")
        
        return True

def main():
    investigator = TestTypeInvestigator()
    investigator.run_investigation()

if __name__ == "__main__":
    main()