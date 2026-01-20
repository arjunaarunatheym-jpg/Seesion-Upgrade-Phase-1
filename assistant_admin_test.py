#!/usr/bin/env python3
"""
Assistant Admin Role Testing Suite for Defensive Driving Training Management System
Tests the assistant_admin role creation and functionality in the Admin Dashboard Staff Management refactor.

TEST OBJECTIVES:
1. Verify that assistant_admin role can be created via POST /api/auth/register endpoint
2. Verify that assistant_admins are correctly filtered and displayed
3. Verify that assistant_admin users can login successfully
4. Verify that assistant_admin has appropriate permissions (should have limited permissions similar to what was defined earlier)

AUTHENTICATION:
- Admin credentials: admin@example.com / admin123
- Use admin JWT token for creating assistant_admin users
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://hr-quote-system.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

class AssistantAdminTestRunner:
    def __init__(self):
        self.admin_token = None
        self.assistant_admin_token = None
        self.assistant_admin_id = None
        self.test_participant_id = None
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
    
    def test_create_assistant_admin(self):
        """Test POST /api/auth/register - Create assistant_admin user"""
        self.log("Testing POST /api/auth/register - Creating assistant_admin user...")
        
        if not self.admin_token:
            self.log("❌ Missing admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        assistant_admin_data = {
            "email": "assistant.admin@example.com",
            "password": "assistant123",
            "full_name": "Test Assistant Admin",
            "id_number": "AA001",
            "role": "assistant_admin",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=assistant_admin_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.assistant_admin_id = data['id']
                self.log(f"✅ Assistant admin created successfully. ID: {self.assistant_admin_id}")
                self.log(f"   Full Name: {data['full_name']}")
                self.log(f"   Email: {data['email']}")
                self.log(f"   Role: {data['role']}")
                self.log(f"   ID Number: {data['id_number']}")
                return True
            elif response.status_code == 400 and "User already exists" in response.text:
                self.log("✅ Assistant admin user already exists (expected from previous runs)")
                # Try to get the existing user ID by logging in
                return self.get_existing_assistant_admin_id()
            else:
                self.log(f"❌ Assistant admin creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin creation error: {str(e)}", "ERROR")
            return False
    
    def get_existing_assistant_admin_id(self):
        """Get existing assistant admin ID by logging in"""
        self.log("Getting existing assistant admin ID...")
        
        login_data = {
            "email": "assistant.admin@example.com",
            "password": "assistant123"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.assistant_admin_id = data['user']['id']
                self.log(f"✅ Using existing assistant admin. ID: {self.assistant_admin_id}")
                return True
            else:
                self.log(f"❌ Failed to get existing assistant admin ID: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error getting existing assistant admin ID: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_login(self):
        """Test assistant_admin user login"""
        self.log("Testing assistant_admin user login...")
        
        login_data = {
            "email": "assistant.admin@example.com",
            "password": "assistant123"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.assistant_admin_token = data['access_token']
                user = data['user']
                self.log(f"✅ Assistant admin login successful. User: {user['full_name']} ({user['role']})")
                self.log(f"   Email: {user['email']}")
                self.log(f"   ID Number: {user['id_number']}")
                
                # Verify role is correct
                if user['role'] == 'assistant_admin':
                    self.log("✅ Role verification passed: assistant_admin")
                    return True
                else:
                    self.log(f"❌ Role verification failed: expected 'assistant_admin', got '{user['role']}'", "ERROR")
                    return False
            else:
                self.log(f"❌ Assistant admin login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin login error: {str(e)}", "ERROR")
            return False
    
    def test_get_users_with_assistant_admin_filter(self):
        """Test GET /api/users with role=assistant_admin filter"""
        self.log("Testing GET /api/users with role=assistant_admin filter...")
        
        if not self.admin_token:
            self.log("❌ Missing admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/users?role=assistant_admin", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Retrieved assistant_admin users successfully. Count: {len(data)}")
                
                # Verify all returned users have assistant_admin role
                assistant_admins = [user for user in data if user['role'] == 'assistant_admin']
                if len(assistant_admins) == len(data):
                    self.log("✅ All returned users have assistant_admin role")
                    
                    # Check if our test assistant admin is in the list
                    test_admin = next((user for user in data if user.get('email') == 'assistant.admin@example.com'), None)
                    if test_admin:
                        self.log(f"✅ Test assistant admin found in filtered results: {test_admin['full_name']}")
                        return True
                    else:
                        self.log("❌ Test assistant admin not found in filtered results", "ERROR")
                        return False
                else:
                    self.log(f"❌ Filter failed: expected {len(data)} assistant_admin users, found {len(assistant_admins)}", "ERROR")
                    return False
            else:
                self.log(f"❌ Get assistant_admin users failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get assistant_admin users error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_create_participant(self):
        """Test assistant_admin can create participants (allowed permission)"""
        self.log("Testing assistant_admin can create participants (allowed permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        participant_data = {
            "email": "test.participant.aa@example.com",
            "password": "participant123",
            "full_name": "Test Participant Created by Assistant Admin",
            "id_number": "TPAA001",
            "role": "participant",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=participant_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.test_participant_id = data['id']
                self.log(f"✅ Assistant admin successfully created participant. ID: {self.test_participant_id}")
                self.log(f"   Full Name: {data['full_name']}")
                self.log(f"   Role: {data['role']}")
                return True
            elif response.status_code == 400 and "User already exists" in response.text:
                self.log("✅ Participant already exists (expected from previous runs)")
                return True
            else:
                self.log(f"❌ Assistant admin participant creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin participant creation error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_create_coordinator(self):
        """Test assistant_admin cannot create coordinators (restricted permission)"""
        self.log("Testing assistant_admin cannot create coordinators (restricted permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        coordinator_data = {
            "email": "test.coordinator.aa@example.com",
            "password": "coordinator123",
            "full_name": "Test Coordinator by Assistant Admin",
            "id_number": "TCAA001",
            "role": "coordinator",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=coordinator_data, headers=headers)
            
            if response.status_code == 403:
                self.log("✅ Assistant admin correctly denied permission to create coordinator (403 Forbidden)")
                return True
            else:
                self.log(f"❌ Expected 403 for coordinator creation, got: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin coordinator creation test error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_create_trainer(self):
        """Test assistant_admin cannot create trainers (restricted permission)"""
        self.log("Testing assistant_admin cannot create trainers (restricted permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        trainer_data = {
            "email": "test.trainer.aa@example.com",
            "password": "trainer123",
            "full_name": "Test Trainer by Assistant Admin",
            "id_number": "TTAA001",
            "role": "trainer",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=trainer_data, headers=headers)
            
            if response.status_code == 403:
                self.log("✅ Assistant admin correctly denied permission to create trainer (403 Forbidden)")
                return True
            else:
                self.log(f"❌ Expected 403 for trainer creation, got: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin trainer creation test error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_create_admin(self):
        """Test assistant_admin cannot create admin users (restricted permission)"""
        self.log("Testing assistant_admin cannot create admin users (restricted permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        admin_data = {
            "email": "test.admin.aa@example.com",
            "password": "admin123",
            "full_name": "Test Admin by Assistant Admin",
            "id_number": "TAAA001",
            "role": "admin",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=admin_data, headers=headers)
            
            if response.status_code == 403:
                self.log("✅ Assistant admin correctly denied permission to create admin (403 Forbidden)")
                return True
            else:
                self.log(f"❌ Expected 403 for admin creation, got: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin admin creation test error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_create_programs(self):
        """Test assistant_admin cannot create programs (admin-only permission)"""
        self.log("Testing assistant_admin cannot create programs (admin-only permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        program_data = {
            "name": "Test Program by Assistant Admin",
            "description": "Program created by assistant admin (should fail)",
            "pass_percentage": 75.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/programs", json=program_data, headers=headers)
            
            if response.status_code == 403:
                self.log("✅ Assistant admin correctly denied permission to create programs (403 Forbidden)")
                return True
            else:
                self.log(f"❌ Expected 403 for program creation, got: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin program creation test error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_create_companies(self):
        """Test assistant_admin cannot create companies (admin-only permission)"""
        self.log("Testing assistant_admin cannot create companies (admin-only permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        company_data = {
            "name": "Test Company by Assistant Admin"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
            
            if response.status_code == 403:
                self.log("✅ Assistant admin correctly denied permission to create companies (403 Forbidden)")
                return True
            else:
                self.log(f"❌ Expected 403 for company creation, got: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin company creation test error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_view_users(self):
        """Test assistant_admin cannot view users (restricted permission)"""
        self.log("Testing assistant_admin cannot view users (restricted permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/users", headers=headers)
            
            if response.status_code == 403:
                self.log("✅ Assistant admin correctly denied permission to view users (403 Forbidden)")
                return True
            else:
                self.log(f"❌ Expected 403 for user viewing, got: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin view users test error: {str(e)}", "ERROR")
            return False
    
    def test_assistant_admin_permissions_delete_users(self):
        """Test assistant_admin cannot delete users (admin-only permission)"""
        self.log("Testing assistant_admin cannot delete users (admin-only permission)...")
        
        if not self.assistant_admin_token:
            self.log("❌ Missing assistant admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.assistant_admin_token}'}
        
        # Use test participant ID if available, otherwise use dummy ID (test should fail with 403 anyway)
        test_user_id = self.test_participant_id if self.test_participant_id else "dummy-user-id-for-delete-test"
        
        try:
            response = self.session.delete(f"{BASE_URL}/users/{test_user_id}", headers=headers)
            
            if response.status_code == 403:
                self.log("✅ Assistant admin correctly denied permission to delete users (403 Forbidden)")
                return True
            else:
                self.log(f"❌ Expected 403 for user deletion, got: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Assistant admin user deletion test error: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all assistant admin tests"""
        self.log("🚀 Starting Assistant Admin Role Testing Suite...")
        self.log("=" * 80)
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Create Assistant Admin", self.test_create_assistant_admin),
            ("Assistant Admin Login", self.test_assistant_admin_login),
            ("Filter Assistant Admins", self.test_get_users_with_assistant_admin_filter),
            ("Assistant Admin Can Create Participants", self.test_assistant_admin_permissions_create_participant),
            ("Assistant Admin Cannot Create Coordinators", self.test_assistant_admin_permissions_create_coordinator),
            ("Assistant Admin Cannot Create Trainers", self.test_assistant_admin_permissions_create_trainer),
            ("Assistant Admin Cannot Create Admins", self.test_assistant_admin_permissions_create_admin),
            ("Assistant Admin Cannot Create Programs", self.test_assistant_admin_permissions_create_programs),
            ("Assistant Admin Cannot Create Companies", self.test_assistant_admin_permissions_create_companies),
            ("Assistant Admin Cannot View Users", self.test_assistant_admin_permissions_view_users),
            ("Assistant Admin Cannot Delete Users", self.test_assistant_admin_permissions_delete_users),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n🧪 Running Test: {test_name}")
            self.log("-" * 60)
            
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
        
        self.log("\n" + "=" * 80)
        self.log("🏁 ASSISTANT ADMIN ROLE TESTING COMPLETE")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"📊 Success Rate: {(passed / (passed + failed)) * 100:.1f}%")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED! Assistant Admin role functionality is working correctly.")
            return True
        else:
            self.log(f"⚠️  {failed} test(s) failed. Please review the issues above.")
            return False

def main():
    """Main function to run the assistant admin tests"""
    runner = AssistantAdminTestRunner()
    success = runner.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()