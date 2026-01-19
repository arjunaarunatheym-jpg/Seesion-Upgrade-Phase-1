#!/usr/bin/env python3
"""
Certificate Debug Test - Specific User Investigation
Investigating certificate download issue for user: maaman@gmail.com

User Claims:
- Has completed pre-test ✓
- Has completed post-test ✓
- Has submitted feedback ✓
- Cannot download certificate ✗

Investigation Steps:
1. Login as this user
2. Check user's sessions
3. Check participant_access for each session
4. Check if feedback actually exists in database
5. Try to generate certificate
6. Check test results
7. Check certificate template
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://marketing-portal-3.preview.emergentagent.com/api"
USER_EMAIL = "maaman@gmail.com"
USER_PASSWORD = "mddrc1"

class CertificateDebugger:
    def __init__(self):
        self.user_token = None
        self.user_id = None
        self.user_sessions = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def step_1_login_user(self):
        """Step 1: Login as the specific user"""
        self.log("=" * 60)
        self.log("STEP 1: LOGIN AS SPECIFIC USER")
        self.log("=" * 60)
        self.log(f"Attempting login for user: {USER_EMAIL}")
        
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
                self.log(f"✅ User login successful!")
                self.log(f"   User ID: {self.user_id}")
                self.log(f"   Full Name: {data['user']['full_name']}")
                self.log(f"   Role: {data['user']['role']}")
                self.log(f"   Email: {data['user']['email']}")
                return True
            else:
                self.log(f"❌ User login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ User login error: {str(e)}", "ERROR")
            return False
    
    def step_2_check_user_sessions(self):
        """Step 2: Check user's sessions"""
        self.log("=" * 60)
        self.log("STEP 2: CHECK USER'S SESSIONS")
        self.log("=" * 60)
        
        if not self.user_token:
            self.log("❌ No user token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.user_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                self.user_sessions = sessions
                self.log(f"✅ Retrieved user sessions. Count: {len(sessions)}")
                
                if len(sessions) == 0:
                    self.log("❌ CRITICAL: User has NO sessions! This explains why certificate cannot be generated.", "ERROR")
                    return False
                
                for i, session in enumerate(sessions):
                    self.log(f"   Session {i+1}:")
                    self.log(f"     ID: {session['id']}")
                    self.log(f"     Name: {session['name']}")
                    self.log(f"     Program ID: {session['program_id']}")
                    self.log(f"     Company ID: {session['company_id']}")
                    self.log(f"     Start Date: {session['start_date']}")
                    self.log(f"     End Date: {session['end_date']}")
                
                return True
            else:
                self.log(f"❌ Get sessions failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get sessions error: {str(e)}", "ERROR")
            return False
    
    def step_3_check_participant_access(self):
        """Step 3: Check participant_access for each session"""
        self.log("=" * 60)
        self.log("STEP 3: CHECK PARTICIPANT_ACCESS FOR EACH SESSION")
        self.log("=" * 60)
        
        if not self.user_token or not self.user_sessions:
            self.log("❌ No user token or sessions available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.user_token}'}
        access_issues = []
        
        for i, session in enumerate(self.user_sessions):
            session_id = session['id']
            self.log(f"Checking participant_access for session {i+1}: {session['name']}")
            
            try:
                response = self.session.get(f"{BASE_URL}/participant-access/{session_id}", headers=headers)
                
                if response.status_code == 200:
                    access = response.json()
                    self.log(f"✅ Participant access found for session {i+1}")
                    self.log(f"   Access ID: {access['id']}")
                    self.log(f"   Can access pre-test: {access['can_access_pre_test']}")
                    self.log(f"   Can access post-test: {access['can_access_post_test']}")
                    self.log(f"   Can access feedback: {access['can_access_feedback']}")
                    self.log(f"   Pre-test completed: {access['pre_test_completed']}")
                    self.log(f"   Post-test completed: {access['post_test_completed']}")
                    self.log(f"   Feedback submitted: {access['feedback_submitted']}")
                    
                    # Check for issues
                    if not access['pre_test_completed']:
                        access_issues.append(f"Session {i+1}: Pre-test NOT completed")
                    if not access['post_test_completed']:
                        access_issues.append(f"Session {i+1}: Post-test NOT completed")
                    if not access['feedback_submitted']:
                        access_issues.append(f"Session {i+1}: Feedback NOT submitted")
                        
                else:
                    self.log(f"❌ Get participant access failed for session {i+1}: {response.status_code} - {response.text}", "ERROR")
                    access_issues.append(f"Session {i+1}: Cannot retrieve participant_access")
                    
            except Exception as e:
                self.log(f"❌ Get participant access error for session {i+1}: {str(e)}", "ERROR")
                access_issues.append(f"Session {i+1}: Error retrieving participant_access")
        
        if access_issues:
            self.log("❌ CRITICAL ISSUES FOUND:", "ERROR")
            for issue in access_issues:
                self.log(f"   - {issue}", "ERROR")
            return False
        else:
            self.log("✅ All participant_access records look good")
            return True
    
    def step_4_check_feedback_in_database(self):
        """Step 4: Check if feedback actually exists in database"""
        self.log("=" * 60)
        self.log("STEP 4: CHECK IF FEEDBACK EXISTS IN DATABASE")
        self.log("=" * 60)
        
        if not self.user_token or not self.user_sessions:
            self.log("❌ No user token or sessions available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.user_token}'}
        feedback_issues = []
        
        # We need admin access to check feedback in database
        # Let's try to get feedback for each session (this might require admin access)
        for i, session in enumerate(self.user_sessions):
            session_id = session['id']
            self.log(f"Checking feedback for session {i+1}: {session['name']}")
            
            try:
                # Try to get session feedback (might require admin access)
                response = self.session.get(f"{BASE_URL}/feedback/session/{session_id}", headers=headers)
                
                if response.status_code == 200:
                    feedback_list = response.json()
                    user_feedback = [f for f in feedback_list if f['participant_id'] == self.user_id]
                    
                    if user_feedback:
                        self.log(f"✅ Feedback found in database for session {i+1}")
                        feedback = user_feedback[0]
                        self.log(f"   Feedback ID: {feedback['id']}")
                        self.log(f"   Submitted at: {feedback['submitted_at']}")
                        self.log(f"   Response count: {len(feedback['responses'])}")
                    else:
                        self.log(f"❌ NO feedback found in database for session {i+1}", "ERROR")
                        feedback_issues.append(f"Session {i+1}: No feedback record in database")
                        
                elif response.status_code == 403:
                    self.log(f"⚠️  Cannot check feedback for session {i+1} (403 - need admin access)", "WARNING")
                    self.log("   Will check using alternative method...")
                    
                    # Alternative: Check if we can access feedback template (indicates feedback system is working)
                    program_id = session['program_id']
                    template_response = self.session.get(f"{BASE_URL}/feedback-templates/program/{program_id}", headers=headers)
                    
                    if template_response.status_code == 200:
                        template = template_response.json()
                        self.log(f"✅ Feedback template exists for program {program_id}")
                        self.log(f"   Template has {len(template['questions'])} questions")
                    else:
                        self.log(f"❌ No feedback template for program {program_id}", "ERROR")
                        feedback_issues.append(f"Session {i+1}: No feedback template")
                        
                else:
                    self.log(f"❌ Get feedback failed for session {i+1}: {response.status_code} - {response.text}", "ERROR")
                    feedback_issues.append(f"Session {i+1}: Cannot retrieve feedback")
                    
            except Exception as e:
                self.log(f"❌ Get feedback error for session {i+1}: {str(e)}", "ERROR")
                feedback_issues.append(f"Session {i+1}: Error retrieving feedback")
        
        if feedback_issues:
            self.log("❌ FEEDBACK ISSUES FOUND:", "ERROR")
            for issue in feedback_issues:
                self.log(f"   - {issue}", "ERROR")
            return False
        else:
            self.log("✅ Feedback checks passed")
            return True
    
    def step_5_try_generate_certificate(self):
        """Step 5: Try to generate certificate"""
        self.log("=" * 60)
        self.log("STEP 5: TRY TO GENERATE CERTIFICATE")
        self.log("=" * 60)
        
        if not self.user_token or not self.user_sessions or not self.user_id:
            self.log("❌ Missing required data", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.user_token}'}
        certificate_issues = []
        
        for i, session in enumerate(self.user_sessions):
            session_id = session['id']
            self.log(f"Attempting certificate generation for session {i+1}: {session['name']}")
            
            try:
                response = self.session.post(f"{BASE_URL}/certificates/generate/{session_id}/{self.user_id}", headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"✅ Certificate generated successfully for session {i+1}!")
                    self.log(f"   Certificate ID: {data.get('id', 'N/A')}")
                    self.log(f"   Download URL: {data.get('certificate_url', 'N/A')}")
                    self.log(f"   Issue Date: {data.get('issue_date', 'N/A')}")
                    
                    # Try to download the certificate
                    if 'certificate_url' in data:
                        download_url = data['certificate_url']
                        if download_url.startswith('/'):
                            download_url = BASE_URL.replace('/api', '') + download_url
                        
                        try:
                            download_response = self.session.get(download_url, headers=headers)
                            if download_response.status_code == 200:
                                self.log(f"✅ Certificate file downloaded successfully!")
                                self.log(f"   File size: {len(download_response.content)} bytes")
                                self.log(f"   Content type: {download_response.headers.get('content-type', 'N/A')}")
                            else:
                                self.log(f"❌ Certificate download failed: {download_response.status_code}", "ERROR")
                                certificate_issues.append(f"Session {i+1}: Certificate download failed")
                        except Exception as e:
                            self.log(f"❌ Certificate download error: {str(e)}", "ERROR")
                            certificate_issues.append(f"Session {i+1}: Certificate download error")
                    
                else:
                    self.log(f"❌ Certificate generation failed for session {i+1}: {response.status_code} - {response.text}", "ERROR")
                    certificate_issues.append(f"Session {i+1}: {response.text}")
                    
                    # Log the exact error for debugging
                    try:
                        error_data = response.json()
                        self.log(f"   Error details: {error_data}", "ERROR")
                    except:
                        pass
                    
            except Exception as e:
                self.log(f"❌ Certificate generation error for session {i+1}: {str(e)}", "ERROR")
                certificate_issues.append(f"Session {i+1}: Exception - {str(e)}")
        
        if certificate_issues:
            self.log("❌ CERTIFICATE GENERATION ISSUES:", "ERROR")
            for issue in certificate_issues:
                self.log(f"   - {issue}", "ERROR")
            return False
        else:
            self.log("✅ Certificate generation successful for all sessions")
            return True
    
    def step_6_check_test_results(self):
        """Step 6: Check test results"""
        self.log("=" * 60)
        self.log("STEP 6: CHECK TEST RESULTS")
        self.log("=" * 60)
        
        if not self.user_token or not self.user_id:
            self.log("❌ No user token or user ID available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.user_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/tests/results/participant/{self.user_id}", headers=headers)
            
            if response.status_code == 200:
                results = response.json()
                self.log(f"✅ Retrieved test results. Count: {len(results)}")
                
                if len(results) == 0:
                    self.log("❌ CRITICAL: User has NO test results!", "ERROR")
                    return False
                
                pre_tests = [r for r in results if r['test_type'] == 'pre']
                post_tests = [r for r in results if r['test_type'] == 'post']
                
                self.log(f"   Pre-test results: {len(pre_tests)}")
                self.log(f"   Post-test results: {len(post_tests)}")
                
                for i, result in enumerate(results):
                    self.log(f"   Result {i+1}:")
                    self.log(f"     ID: {result['id']}")
                    self.log(f"     Test Type: {result['test_type']}")
                    self.log(f"     Session ID: {result['session_id']}")
                    self.log(f"     Score: {result['score']}%")
                    self.log(f"     Passed: {result['passed']}")
                    self.log(f"     Submitted: {result['submitted_at']}")
                
                # Check if user has both pre and post test results
                if len(pre_tests) == 0:
                    self.log("❌ ISSUE: No pre-test results found", "ERROR")
                    return False
                if len(post_tests) == 0:
                    self.log("❌ ISSUE: No post-test results found", "ERROR")
                    return False
                
                return True
            else:
                self.log(f"❌ Get test results failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get test results error: {str(e)}", "ERROR")
            return False
    
    def step_7_check_certificate_template(self):
        """Step 7: Check certificate template"""
        self.log("=" * 60)
        self.log("STEP 7: CHECK CERTIFICATE TEMPLATE")
        self.log("=" * 60)
        
        # Check if certificate template file exists
        import os
        template_path = "/app/backend/static/templates/certificate_template.docx"
        
        if os.path.exists(template_path):
            file_size = os.path.getsize(template_path)
            self.log(f"✅ Certificate template file exists")
            self.log(f"   Path: {template_path}")
            self.log(f"   Size: {file_size} bytes")
            
            # Try to read the file to ensure it's valid
            try:
                with open(template_path, 'rb') as f:
                    content = f.read(100)  # Read first 100 bytes
                self.log(f"✅ Certificate template file is readable")
                return True
            except Exception as e:
                self.log(f"❌ Certificate template file is not readable: {str(e)}", "ERROR")
                return False
        else:
            self.log(f"❌ CRITICAL: Certificate template file does NOT exist at {template_path}", "ERROR")
            return False
    
    def run_investigation(self):
        """Run the complete investigation"""
        self.log("🔍 STARTING CERTIFICATE DEBUG INVESTIGATION")
        self.log(f"User: {USER_EMAIL}")
        self.log("=" * 80)
        
        investigation_steps = [
            ("Step 1: Login User", self.step_1_login_user),
            ("Step 2: Check User Sessions", self.step_2_check_user_sessions),
            ("Step 3: Check Participant Access", self.step_3_check_participant_access),
            ("Step 4: Check Feedback in Database", self.step_4_check_feedback_in_database),
            ("Step 5: Try Generate Certificate", self.step_5_try_generate_certificate),
            ("Step 6: Check Test Results", self.step_6_check_test_results),
            ("Step 7: Check Certificate Template", self.step_7_check_certificate_template),
        ]
        
        results = []
        
        for step_name, step_func in investigation_steps:
            self.log(f"\n🔍 {step_name}")
            try:
                result = step_func()
                results.append((step_name, result))
                if not result:
                    self.log(f"❌ {step_name} FAILED - Investigation may stop here", "ERROR")
                    # Continue with remaining steps to get full picture
            except Exception as e:
                self.log(f"❌ {step_name} ERROR: {str(e)}", "ERROR")
                results.append((step_name, False))
        
        # Final Summary
        self.log("\n" + "=" * 80)
        self.log("🔍 INVESTIGATION SUMMARY")
        self.log("=" * 80)
        
        passed = 0
        failed = 0
        
        for step_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} - {step_name}")
            if result:
                passed += 1
            else:
                failed += 1
        
        self.log(f"\nResults: {passed} passed, {failed} failed")
        
        if failed == 0:
            self.log("🎉 ALL CHECKS PASSED - Certificate should be working!")
            self.log("   If user still cannot download, check frontend implementation.")
        else:
            self.log("❌ ISSUES FOUND - These need to be fixed:")
            for step_name, result in results:
                if not result:
                    self.log(f"   - {step_name}")
        
        return failed == 0

def main():
    """Main function to run the certificate debug investigation"""
    debugger = CertificateDebugger()
    success = debugger.run_investigation()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()