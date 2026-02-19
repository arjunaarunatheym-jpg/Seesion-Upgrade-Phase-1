#!/usr/bin/env python3
"""
Certificate Download Test - Testing the specific download issue
Testing both download methods for the user: maaman@gmail.com
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://collapsible-tables.preview.emergentagent.com/api"
USER_EMAIL = "maaman@gmail.com"
USER_PASSWORD = "mddrc1"

class CertificateDownloadTester:
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
    
    def test_certificate_generation_and_download(self):
        """Test certificate generation and both download methods"""
        self.log("=" * 60)
        self.log("TESTING CERTIFICATE GENERATION AND DOWNLOAD")
        self.log("=" * 60)
        
        if not self.user_token or not self.user_id:
            self.log("❌ No user token or user ID available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.user_token}'}
        
        # Get user's sessions first
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to get sessions: {response.status_code}", "ERROR")
                return False
                
            sessions = response.json()
            if not sessions:
                self.log("❌ No sessions found for user", "ERROR")
                return False
                
            session = sessions[0]  # Use first session
            session_id = session['id']
            self.log(f"Using session: {session['name']} (ID: {session_id})")
            
        except Exception as e:
            self.log(f"❌ Error getting sessions: {str(e)}", "ERROR")
            return False
        
        # Step 1: Generate certificate
        self.log("Step 1: Generating certificate...")
        try:
            response = self.session.post(f"{BASE_URL}/certificates/generate/{session_id}/{self.user_id}", headers=headers)
            
            if response.status_code == 200:
                cert_data = response.json()
                self.log("✅ Certificate generated successfully!")
                self.log(f"   Certificate ID: {cert_data.get('certificate_id', 'N/A')}")
                self.log(f"   Certificate URL: {cert_data.get('certificate_url', 'N/A')}")
                self.log(f"   Download URL: {cert_data.get('download_url', 'N/A')}")
                
                certificate_id = cert_data.get('certificate_id')
                certificate_url = cert_data.get('certificate_url')
                download_url = cert_data.get('download_url')
                
            else:
                self.log(f"❌ Certificate generation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Certificate generation error: {str(e)}", "ERROR")
            return False
        
        # Step 2: Test direct file access (certificate_url)
        self.log("\nStep 2: Testing direct file access...")
        if certificate_url:
            try:
                # Convert relative URL to full URL
                if certificate_url.startswith('/'):
                    full_url = BASE_URL.replace('/api', '') + certificate_url
                else:
                    full_url = certificate_url
                
                self.log(f"Trying direct access: {full_url}")
                response = self.session.get(full_url, headers=headers)
                
                if response.status_code == 200:
                    self.log("✅ Direct file access SUCCESSFUL!")
                    self.log(f"   File size: {len(response.content)} bytes")
                    self.log(f"   Content type: {response.headers.get('content-type', 'N/A')}")
                else:
                    self.log(f"❌ Direct file access failed: {response.status_code} - {response.text}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ Direct file access error: {str(e)}", "ERROR")
        
        # Step 3: Test download endpoint (download_url)
        self.log("\nStep 3: Testing download endpoint...")
        if download_url:
            try:
                # Convert relative URL to full URL
                if download_url.startswith('/'):
                    full_download_url = BASE_URL.replace('/api', '') + download_url
                else:
                    full_download_url = download_url
                
                self.log(f"Trying download endpoint: {full_download_url}")
                response = self.session.get(full_download_url, headers=headers)
                
                if response.status_code == 200:
                    self.log("✅ Download endpoint SUCCESSFUL!")
                    self.log(f"   File size: {len(response.content)} bytes")
                    self.log(f"   Content type: {response.headers.get('content-type', 'N/A')}")
                    self.log(f"   Content disposition: {response.headers.get('content-disposition', 'N/A')}")
                elif response.status_code == 403:
                    self.log("❌ Download endpoint failed with 403 FORBIDDEN", "ERROR")
                    self.log("   This is the ISSUE! User cannot access their own certificate via download endpoint", "ERROR")
                    
                    # Let's check what certificate ID we're using
                    self.log(f"   Certificate ID being used: {certificate_id}")
                    
                    # Try to get certificate details to debug
                    cert_response = self.session.get(f"{BASE_URL}/certificates/participant/{self.user_id}", headers=headers)
                    if cert_response.status_code == 200:
                        certs = cert_response.json()
                        self.log(f"   User has {len(certs)} certificates in database:")
                        for i, cert in enumerate(certs):
                            self.log(f"     Certificate {i+1}: ID={cert.get('id')}, Session={cert.get('session_id')}")
                    
                else:
                    self.log(f"❌ Download endpoint failed: {response.status_code} - {response.text}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ Download endpoint error: {str(e)}", "ERROR")
        
        # Step 4: Test without authentication (should fail)
        self.log("\nStep 4: Testing download without authentication (should fail)...")
        if download_url:
            try:
                if download_url.startswith('/'):
                    full_download_url = BASE_URL.replace('/api', '') + download_url
                else:
                    full_download_url = download_url
                
                # Remove authorization header
                no_auth_session = requests.Session()
                no_auth_session.headers.update({'Content-Type': 'application/json'})
                
                response = no_auth_session.get(full_download_url)
                
                if response.status_code == 403:
                    self.log("✅ Download without auth correctly returns 403 (expected)")
                elif response.status_code == 401:
                    self.log("✅ Download without auth correctly returns 401 (expected)")
                else:
                    self.log(f"⚠️  Download without auth returned: {response.status_code} (unexpected)", "WARNING")
                    
            except Exception as e:
                self.log(f"❌ Download without auth error: {str(e)}", "ERROR")
        
        return True
    
    def run_test(self):
        """Run the complete test"""
        self.log("🔍 STARTING CERTIFICATE DOWNLOAD TEST")
        self.log(f"User: {USER_EMAIL}")
        self.log("=" * 80)
        
        if not self.login_user():
            return False
            
        return self.test_certificate_generation_and_download()

def main():
    """Main function to run the test"""
    tester = CertificateDownloadTester()
    success = tester.run_test()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()