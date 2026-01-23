#!/usr/bin/env python3
"""
Certificate Frontend Test - Check what the frontend might be doing wrong
Testing the exact flow that the frontend would use
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://training-manager-13.preview.emergentagent.com/api"
USER_EMAIL = "maaman@gmail.com"
USER_PASSWORD = "mddrc1"

class CertificateFrontendTester:
    def __init__(self):
        self.user_token = None
        self.user_id = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_user(self):
        """Login as the specific user"""
        self.log(f"Logging in as user: {USER_EMAIL}")
        
        login_data = {
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.user_token = data['access_token']
                self.user_id = data['user']['id']
                self.log(f"✅ User login successful! User ID: {self.user_id}")
                return True
            else:
                self.log(f"❌ User login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ User login error: {str(e)}", "ERROR")
            return False
    
    def test_frontend_flow(self):
        """Test the exact flow that frontend would use"""
        self.log("=" * 60)
        self.log("TESTING FRONTEND CERTIFICATE FLOW")
        self.log("=" * 60)
        
        if not self.user_token or not self.user_id:
            self.log("❌ No user token or user ID available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.user_token}'}
        
        # Step 1: Get user's existing certificates (what frontend would do first)
        self.log("Step 1: Getting existing certificates...")
        try:
            response = self.session.get(f"{BASE_URL}/certificates/participant/{self.user_id}", headers=headers)
            
            if response.status_code == 200:
                certificates = response.json()
                self.log(f"✅ Found {len(certificates)} existing certificates")
                
                for i, cert in enumerate(certificates):
                    self.log(f"   Certificate {i+1}:")
                    self.log(f"     ID: {cert['id']}")
                    self.log(f"     Session ID: {cert['session_id']}")
                    self.log(f"     Program: {cert['program_name']}")
                    self.log(f"     Issue Date: {cert['issue_date']}")
                    self.log(f"     Certificate URL: {cert.get('certificate_url', 'N/A')}")
                    
                    # Test downloading each existing certificate
                    self.log(f"   Testing download for certificate {i+1}...")
                    download_response = self.session.get(f"{BASE_URL}/certificates/download/{cert['id']}", headers=headers)
                    
                    if download_response.status_code == 200:
                        self.log(f"   ✅ Certificate {i+1} download SUCCESSFUL!")
                        self.log(f"      File size: {len(download_response.content)} bytes")
                    else:
                        self.log(f"   ❌ Certificate {i+1} download FAILED: {download_response.status_code}", "ERROR")
                        self.log(f"      Error: {download_response.text}", "ERROR")
                        
                        # This might be the issue - old certificates with wrong participant_id
                        self.log(f"      Certificate participant_id: {cert.get('participant_id', 'N/A')}")
                        self.log(f"      Current user ID: {self.user_id}")
                        
                        if cert.get('participant_id') != self.user_id:
                            self.log(f"   ❌ MISMATCH! Certificate belongs to different participant!", "ERROR")
                
            else:
                self.log(f"❌ Failed to get certificates: {response.status_code} - {response.text}", "ERROR")
                
        except Exception as e:
            self.log(f"❌ Error getting certificates: {str(e)}", "ERROR")
        
        # Step 2: Get user's sessions (to see which ones can generate certificates)
        self.log("\nStep 2: Getting user's sessions...")
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.log(f"✅ Found {len(sessions)} sessions")
                
                for i, session in enumerate(sessions):
                    session_id = session['id']
                    self.log(f"   Session {i+1}: {session['name']} (ID: {session_id})")
                    
                    # Check participant access for this session
                    access_response = self.session.get(f"{BASE_URL}/participant-access/{session_id}", headers=headers)
                    
                    if access_response.status_code == 200:
                        access = access_response.json()
                        self.log(f"     Pre-test completed: {access['pre_test_completed']}")
                        self.log(f"     Post-test completed: {access['post_test_completed']}")
                        self.log(f"     Feedback submitted: {access['feedback_submitted']}")
                        
                        # Check if certificate can be generated
                        if access['pre_test_completed'] and access['post_test_completed'] and access['feedback_submitted']:
                            self.log(f"     ✅ Certificate can be generated for this session")
                            
                            # Try generating certificate
                            self.log(f"     Generating certificate...")
                            cert_response = self.session.post(f"{BASE_URL}/certificates/generate/{session_id}/{self.user_id}", headers=headers)
                            
                            if cert_response.status_code == 200:
                                cert_data = cert_response.json()
                                self.log(f"     ✅ Certificate generated!")
                                self.log(f"       Certificate ID: {cert_data.get('certificate_id')}")
                                self.log(f"       Download URL: {cert_data.get('download_url')}")
                                
                                # Test immediate download
                                cert_id = cert_data.get('certificate_id')
                                if cert_id:
                                    download_response = self.session.get(f"{BASE_URL}/certificates/download/{cert_id}", headers=headers)
                                    
                                    if download_response.status_code == 200:
                                        self.log(f"     ✅ Immediate download SUCCESSFUL!")
                                    else:
                                        self.log(f"     ❌ Immediate download FAILED: {download_response.status_code}", "ERROR")
                                        self.log(f"       Error: {download_response.text}", "ERROR")
                            else:
                                self.log(f"     ❌ Certificate generation failed: {cert_response.status_code}", "ERROR")
                                self.log(f"       Error: {cert_response.text}", "ERROR")
                        else:
                            self.log(f"     ❌ Certificate cannot be generated - requirements not met")
                    else:
                        self.log(f"     ❌ Failed to get participant access: {access_response.status_code}")
                
            else:
                self.log(f"❌ Failed to get sessions: {response.status_code} - {response.text}", "ERROR")
                
        except Exception as e:
            self.log(f"❌ Error getting sessions: {str(e)}", "ERROR")
        
        return True
    
    def run_test(self):
        """Run the complete test"""
        self.log("🔍 STARTING CERTIFICATE FRONTEND FLOW TEST")
        self.log(f"User: {USER_EMAIL}")
        self.log("=" * 80)
        
        if not self.login_user():
            return False
            
        return self.test_frontend_flow()

def main():
    """Main function to run the test"""
    tester = CertificateFrontendTester()
    success = tester.run_test()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()