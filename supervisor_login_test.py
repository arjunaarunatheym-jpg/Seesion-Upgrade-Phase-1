#!/usr/bin/env python3
"""
Supervisor Login Investigation Script
Tests supervisor creation and login functionality to identify the issue
"""

import requests
import json
import sys
from datetime import datetime
from pymongo import MongoClient
import os

# Configuration
BASE_URL = "https://finance-correction.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "driving_training_db"

class SupervisorLoginTester:
    def __init__(self):
        self.admin_token = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.mongo_client = MongoClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        
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
    
    def check_existing_supervisors(self):
        """Check existing supervisors in database"""
        self.log("\n" + "="*80)
        self.log("STEP 1: Checking existing supervisors in database")
        self.log("="*80)
        
        try:
            supervisors = list(self.db.users.find(
                {"role": "pic_supervisor"},
                {"_id": 0, "id": 1, "email": 1, "full_name": 1, "password": 1, "hashed_password": 1}
            ))
            
            self.log(f"\nFound {len(supervisors)} supervisor(s) in database:")
            
            for i, supervisor in enumerate(supervisors, 1):
                self.log(f"\n--- Supervisor {i} ---")
                self.log(f"  ID: {supervisor.get('id', 'N/A')}")
                self.log(f"  Email: {supervisor.get('email', 'N/A')}")
                self.log(f"  Full Name: {supervisor.get('full_name', 'N/A')}")
                self.log(f"  Has 'password' field: {('password' in supervisor)}")
                self.log(f"  Has 'hashed_password' field: {('hashed_password' in supervisor)}")
                
                if 'password' in supervisor:
                    self.log(f"  Password field value (first 20 chars): {supervisor['password'][:20]}...")
                if 'hashed_password' in supervisor:
                    self.log(f"  Hashed_password field value (first 20 chars): {supervisor['hashed_password'][:20]}...")
            
            return supervisors
            
        except Exception as e:
            self.log(f"❌ Error checking supervisors: {str(e)}", "ERROR")
            return []
    
    def create_test_program_and_company(self):
        """Create test program and company for session creation"""
        self.log("\n" + "="*80)
        self.log("STEP 2: Creating test program and company")
        self.log("="*80)
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create program
        program_data = {
            "name": "Supervisor Test Program",
            "description": "Program for testing supervisor creation",
            "pass_percentage": 70.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/programs", json=program_data, headers=headers)
            
            if response.status_code == 200:
                self.program_id = response.json()['id']
                self.log(f"✅ Test program created. ID: {self.program_id}")
            else:
                self.log(f"❌ Program creation failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Program creation error: {str(e)}", "ERROR")
            return False
        
        # Create company
        company_data = {
            "name": "Supervisor Test Company"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/companies", json=company_data, headers=headers)
            
            if response.status_code == 200:
                self.company_id = response.json()['id']
                self.log(f"✅ Test company created. ID: {self.company_id}")
                return True
            else:
                self.log(f"❌ Company creation failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Company creation error: {str(e)}", "ERROR")
            return False
    
    def create_session_with_supervisor(self):
        """Create a session with a new supervisor"""
        self.log("\n" + "="*80)
        self.log("STEP 3: Creating session with new supervisor")
        self.log("="*80)
        
        if not self.admin_token or not hasattr(self, 'program_id') or not hasattr(self, 'company_id'):
            self.log("❌ Missing required data", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create session with a new supervisor
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        supervisor_email = f"supervisor_test_{timestamp}@example.com"
        supervisor_password = "supervisor123"
        
        session_data = {
            "name": "Supervisor Test Session",
            "program_id": self.program_id,
            "company_id": self.company_id,
            "location": "Test Location",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "supervisors": [
                {
                    "email": supervisor_email,
                    "password": supervisor_password,
                    "full_name": "Test Supervisor",
                    "id_number": f"SUP{timestamp}",
                    "phone_number": "1234567890"
                }
            ]
        }
        
        self.log(f"\nCreating session with supervisor:")
        self.log(f"  Email: {supervisor_email}")
        self.log(f"  Password: {supervisor_password}")
        
        try:
            response = self.session.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data['session']['id']
                self.log(f"✅ Session created successfully. ID: {self.session_id}")
                
                # Check supervisor results
                if 'supervisor_results' in data and len(data['supervisor_results']) > 0:
                    supervisor_result = data['supervisor_results'][0]
                    self.log(f"\nSupervisor creation result:")
                    self.log(f"  Name: {supervisor_result.get('name', 'N/A')}")
                    self.log(f"  Email: {supervisor_result.get('email', 'N/A')}")
                    self.log(f"  Is Existing: {supervisor_result.get('is_existing', 'N/A')}")
                    
                    # Store for login test
                    self.new_supervisor_email = supervisor_email
                    self.new_supervisor_password = supervisor_password
                    
                    return True
                else:
                    self.log("❌ No supervisor results in response", "ERROR")
                    return False
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {str(e)}", "ERROR")
            return False
    
    def check_supervisor_in_database(self):
        """Check the newly created supervisor in database"""
        self.log("\n" + "="*80)
        self.log("STEP 4: Checking newly created supervisor in database")
        self.log("="*80)
        
        if not hasattr(self, 'new_supervisor_email'):
            self.log("❌ No new supervisor email available", "ERROR")
            return False
        
        try:
            supervisor = self.db.users.find_one(
                {"email": self.new_supervisor_email},
                {"_id": 0, "id": 1, "email": 1, "full_name": 1, "role": 1, "password": 1, "hashed_password": 1}
            )
            
            if supervisor:
                self.log(f"\n✅ Found newly created supervisor in database:")
                self.log(f"  ID: {supervisor.get('id', 'N/A')}")
                self.log(f"  Email: {supervisor.get('email', 'N/A')}")
                self.log(f"  Full Name: {supervisor.get('full_name', 'N/A')}")
                self.log(f"  Role: {supervisor.get('role', 'N/A')}")
                self.log(f"  Has 'password' field: {('password' in supervisor)}")
                self.log(f"  Has 'hashed_password' field: {('hashed_password' in supervisor)}")
                
                if 'password' in supervisor:
                    self.log(f"  Password field value (first 20 chars): {supervisor['password'][:20]}...")
                if 'hashed_password' in supervisor:
                    self.log(f"  Hashed_password field value (first 20 chars): {supervisor['hashed_password'][:20]}...")
                
                return True
            else:
                self.log("❌ Newly created supervisor not found in database", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error checking supervisor in database: {str(e)}", "ERROR")
            return False
    
    def test_login_new_supervisor(self):
        """Test login with newly created supervisor"""
        self.log("\n" + "="*80)
        self.log("STEP 5: Testing login with newly created supervisor")
        self.log("="*80)
        
        if not hasattr(self, 'new_supervisor_email') or not hasattr(self, 'new_supervisor_password'):
            self.log("❌ No new supervisor credentials available", "ERROR")
            return False
        
        login_data = {
            "email": self.new_supervisor_email,
            "password": self.new_supervisor_password
        }
        
        self.log(f"\nAttempting login with:")
        self.log(f"  Email: {self.new_supervisor_email}")
        self.log(f"  Password: {self.new_supervisor_password}")
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"\n✅ Login successful!")
                self.log(f"  User: {data['user']['full_name']}")
                self.log(f"  Role: {data['user']['role']}")
                self.log(f"  Email: {data['user']['email']}")
                return True
            else:
                self.log(f"\n❌ Login failed: {response.status_code}")
                self.log(f"  Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Login error: {str(e)}", "ERROR")
            return False
    
    def test_login_existing_supervisors(self, supervisors):
        """Test login with existing supervisors"""
        self.log("\n" + "="*80)
        self.log("STEP 6: Testing login with existing supervisors")
        self.log("="*80)
        
        if not supervisors:
            self.log("No existing supervisors to test")
            return True
        
        # Try common passwords
        common_passwords = ["supervisor123", "password123", "admin123", "test123"]
        
        for supervisor in supervisors:
            email = supervisor.get('email')
            if not email:
                continue
            
            self.log(f"\nTesting login for: {email}")
            
            for password in common_passwords:
                login_data = {
                    "email": email,
                    "password": password
                }
                
                try:
                    response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.log(f"  ✅ Login successful with password: {password}")
                        self.log(f"     User: {data['user']['full_name']}")
                        self.log(f"     Role: {data['user']['role']}")
                        break
                    elif response.status_code == 401:
                        self.log(f"  ❌ Login failed with password: {password} (401 Unauthorized)")
                    else:
                        self.log(f"  ❌ Login failed with password: {password} ({response.status_code})")
                        
                except Exception as e:
                    self.log(f"  ❌ Login error with password {password}: {str(e)}", "ERROR")
        
        return True
    
    def run_investigation(self):
        """Run the complete investigation"""
        self.log("\n" + "="*80)
        self.log("SUPERVISOR LOGIN INVESTIGATION")
        self.log("="*80)
        
        # Step 1: Login as admin
        if not self.login_admin():
            self.log("\n❌ INVESTIGATION FAILED: Could not login as admin", "ERROR")
            return False
        
        # Step 2: Check existing supervisors
        existing_supervisors = self.check_existing_supervisors()
        
        # Step 3: Create test program and company
        if not self.create_test_program_and_company():
            self.log("\n❌ INVESTIGATION FAILED: Could not create test data", "ERROR")
            return False
        
        # Step 4: Create session with new supervisor
        if not self.create_session_with_supervisor():
            self.log("\n❌ INVESTIGATION FAILED: Could not create session with supervisor", "ERROR")
            return False
        
        # Step 5: Check supervisor in database
        if not self.check_supervisor_in_database():
            self.log("\n❌ INVESTIGATION FAILED: Could not verify supervisor in database", "ERROR")
            return False
        
        # Step 6: Test login with new supervisor
        new_supervisor_login_success = self.test_login_new_supervisor()
        
        # Step 7: Test login with existing supervisors
        self.test_login_existing_supervisors(existing_supervisors)
        
        # Summary
        self.log("\n" + "="*80)
        self.log("INVESTIGATION SUMMARY")
        self.log("="*80)
        self.log(f"\nExisting supervisors found: {len(existing_supervisors)}")
        self.log(f"New supervisor login: {'✅ SUCCESS' if new_supervisor_login_success else '❌ FAILED'}")
        
        return True

if __name__ == "__main__":
    tester = SupervisorLoginTester()
    try:
        tester.run_investigation()
    except KeyboardInterrupt:
        print("\n\nInvestigation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
