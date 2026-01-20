#!/usr/bin/env python3
"""
Super Admin Finance Features Backend Test Suite
Tests the comprehensive finance management capabilities within the Data Management tab.

Test Coverage:
1. GET /api/finance/admin/invoices - List all invoices
2. PUT /api/finance/admin/invoices/{invoice_id}/number - Edit invoice number
3. POST /api/finance/admin/invoices/{invoice_id}/void - Void invoice
4. PUT /api/finance/admin/invoices/{invoice_id}/backdate - Backdate invoice
5. PUT /api/finance/admin/invoices/{invoice_id}/override - Override invoice amount
6. GET /api/finance/admin/payments - List all payments
7. DELETE /api/finance/admin/payments/{payment_id} - Delete payment record
8. POST /api/finance/admin/sequence/reset - Reset sequence counter
9. GET /api/finance/admin/audit-trail - View audit trail
10. Access Control Testing - Verify admin/finance role restrictions

Test Credentials:
- Admin: arjuna@mddrc.com.my / Dana102229
- Finance: munirah@sdc.com.my / mddrc1 (if exists)
"""

import requests
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

# Configuration from frontend/.env
BASE_URL = "https://hr-quote-system.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
FINANCE_EMAIL = "munirah@sdc.com.my"
FINANCE_PASSWORD = "mddrc1"

class SuperAdminFinanceTest:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.admin_token = None
        self.finance_token = None
        self.test_invoice_id = None
        self.test_payment_id = None
        self.test_results = []
        self.failed_tests = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_admin(self) -> bool:
        """Login as admin and get authentication token"""
        self.log("🔐 Attempting admin login...")
        
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data['access_token']
                self.log(f"✅ Admin login successful: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin login error: {str(e)}", "ERROR")
            return False
    
    def login_finance(self) -> bool:
        """Login as finance user and get authentication token"""
        self.log("🔐 Attempting finance user login...")
        
        login_data = {
            "email": FINANCE_EMAIL,
            "password": FINANCE_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.finance_token = data['access_token']
                self.log(f"✅ Finance login successful: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"⚠️  Finance user login failed: {response.status_code} - {response.text}", "WARNING")
                self.log("   Will test with admin user only", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"⚠️  Finance user login error: {str(e)}", "WARNING")
            return False
    
    def test_get_admin_invoices(self) -> bool:
        """Test GET /api/finance/admin/invoices"""
        self.log("📋 Testing GET /api/finance/admin/invoices...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/admin/invoices", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Admin invoices retrieved successfully. Count: {len(data)}")
                
                # Store first invoice ID for testing if available
                if data and len(data) > 0:
                    self.test_invoice_id = data[0]['id']
                    self.log(f"   Using invoice ID for testing: {self.test_invoice_id}")
                    self.log(f"   Invoice Number: {data[0].get('invoice_number', 'N/A')}")
                    self.log(f"   Status: {data[0].get('status', 'N/A')}")
                    self.log(f"   Total Amount: {data[0].get('total_amount', 0)}")
                else:
                    self.log("⚠️  No invoices found - some tests will be skipped", "WARNING")
                
                return True
            else:
                self.log(f"❌ Get admin invoices failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get admin invoices error: {str(e)}", "ERROR")
            return False
    
    def test_get_admin_payments(self) -> bool:
        """Test GET /api/finance/admin/payments"""
        self.log("💰 Testing GET /api/finance/admin/payments...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/admin/payments", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Admin payments retrieved successfully. Count: {len(data)}")
                
                # Store first payment ID for testing if available
                if data and len(data) > 0:
                    self.test_payment_id = data[0]['id']
                    self.log(f"   Using payment ID for testing: {self.test_payment_id}")
                    self.log(f"   Payment Amount: {data[0].get('amount', 0)}")
                    self.log(f"   Payment Method: {data[0].get('payment_method', 'N/A')}")
                    self.log(f"   Payment Date: {data[0].get('payment_date', 'N/A')}")
                    
                    # Check if enriched with invoice data
                    if 'invoice_number' in data[0]:
                        self.log(f"   ✅ Payment enriched with invoice data: {data[0]['invoice_number']}")
                    else:
                        self.log("   ⚠️  Payment not enriched with invoice data", "WARNING")
                else:
                    self.log("⚠️  No payments found - payment deletion test will be skipped", "WARNING")
                
                return True
            else:
                self.log(f"❌ Get admin payments failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get admin payments error: {str(e)}", "ERROR")
            return False
    
    def test_edit_invoice_number(self) -> bool:
        """Test PUT /api/finance/admin/invoices/{invoice_id}/number"""
        self.log("🔢 Testing PUT /api/finance/admin/invoices/{invoice_id}/number...")
        
        if not self.admin_token or not self.test_invoice_id:
            self.log("❌ No admin token or invoice ID available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test data from review request
        edit_data = {
            "year": 2026,
            "month": 2,
            "sequence": 5,
            "reason": "Testing invoice number change functionality"
        }
        
        try:
            response = self.session.put(
                f"{BASE_URL}/finance/admin/invoices/{self.test_invoice_id}/number", 
                json=edit_data, 
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Invoice number updated successfully")
                self.log(f"   New Invoice Number: {data.get('invoice_number', 'N/A')}")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                
                # Verify audit trail was created
                if 'audit_trail_id' in data:
                    self.log(f"   ✅ Audit trail created: {data['audit_trail_id']}")
                
                return True
            else:
                self.log(f"❌ Edit invoice number failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Edit invoice number error: {str(e)}", "ERROR")
            return False
    
    def test_void_invoice(self) -> bool:
        """Test POST /api/finance/admin/invoices/{invoice_id}/void"""
        self.log("🚫 Testing POST /api/finance/admin/invoices/{invoice_id}/void...")
        
        if not self.admin_token or not self.test_invoice_id:
            self.log("❌ No admin token or invoice ID available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        void_data = {
            "reason": "Testing void functionality - automated test"
        }
        
        try:
            response = self.session.post(
                f"{BASE_URL}/finance/admin/invoices/{self.test_invoice_id}/void", 
                json=void_data, 
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Invoice voided successfully")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                
                # Verify audit trail was created
                if 'audit_trail_id' in data:
                    self.log(f"   ✅ Audit trail created: {data['audit_trail_id']}")
                
                return True
            else:
                self.log(f"❌ Void invoice failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Void invoice error: {str(e)}", "ERROR")
            return False
    
    def test_backdate_invoice(self) -> bool:
        """Test PUT /api/finance/admin/invoices/{invoice_id}/backdate"""
        self.log("📅 Testing PUT /api/finance/admin/invoices/{invoice_id}/backdate...")
        
        if not self.admin_token or not self.test_invoice_id:
            self.log("❌ No admin token or invoice ID available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        backdate_data = {
            "new_date": "2025-12-15",
            "reason": "Testing backdate functionality - automated test"
        }
        
        try:
            response = self.session.put(
                f"{BASE_URL}/finance/admin/invoices/{self.test_invoice_id}/backdate", 
                json=backdate_data, 
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Invoice backdated successfully")
                self.log(f"   New Date: {data.get('new_date', 'N/A')}")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                
                # Verify audit trail was created
                if 'audit_trail_id' in data:
                    self.log(f"   ✅ Audit trail created: {data['audit_trail_id']}")
                
                return True
            else:
                self.log(f"❌ Backdate invoice failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Backdate invoice error: {str(e)}", "ERROR")
            return False
    
    def test_override_invoice_amount(self) -> bool:
        """Test PUT /api/finance/admin/invoices/{invoice_id}/override"""
        self.log("💵 Testing PUT /api/finance/admin/invoices/{invoice_id}/override...")
        
        if not self.admin_token or not self.test_invoice_id:
            self.log("❌ No admin token or invoice ID available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        override_data = {
            "total_amount": 10000.00,
            "reason": "Testing override functionality - automated test",
            "skip_validation": True
        }
        
        try:
            response = self.session.put(
                f"{BASE_URL}/finance/admin/invoices/{self.test_invoice_id}/override", 
                json=override_data, 
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Invoice amount overridden successfully")
                self.log(f"   New Amount: {data.get('total_amount', 'N/A')}")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                
                # Verify audit trail was created
                if 'audit_trail_id' in data:
                    self.log(f"   ✅ Audit trail created: {data['audit_trail_id']}")
                
                return True
            else:
                self.log(f"❌ Override invoice amount failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Override invoice amount error: {str(e)}", "ERROR")
            return False
    
    def test_delete_payment(self) -> bool:
        """Test DELETE /api/finance/admin/payments/{payment_id}"""
        self.log("🗑️  Testing DELETE /api/finance/admin/payments/{payment_id}...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        if not self.test_payment_id:
            self.log("⚠️  No payment ID available - skipping payment deletion test", "WARNING")
            return True  # Not a failure, just no data to test with
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        delete_data = {
            "reason": "Testing payment deletion functionality - automated test"
        }
        
        try:
            response = self.session.delete(
                f"{BASE_URL}/finance/admin/payments/{self.test_payment_id}", 
                json=delete_data, 
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Payment deleted successfully")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                
                # Verify audit trail was created
                if 'audit_trail_id' in data:
                    self.log(f"   ✅ Audit trail created: {data['audit_trail_id']}")
                
                return True
            else:
                self.log(f"❌ Delete payment failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Delete payment error: {str(e)}", "ERROR")
            return False
    
    def test_reset_sequence_counter(self) -> bool:
        """Test POST /api/finance/admin/sequence/reset"""
        self.log("🔄 Testing POST /api/finance/admin/sequence/reset...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        reset_data = {
            "year": 2026,
            "month": 2,
            "new_sequence": 100,
            "reason": "Testing sequence reset functionality - automated test"
        }
        
        try:
            response = self.session.post(
                f"{BASE_URL}/finance/admin/sequence/reset", 
                json=reset_data, 
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Sequence counter reset successfully")
                self.log(f"   New Sequence: {data.get('new_sequence', 'N/A')}")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                
                # Verify audit trail was created
                if 'audit_trail_id' in data:
                    self.log(f"   ✅ Audit trail created: {data['audit_trail_id']}")
                
                return True
            else:
                self.log(f"❌ Reset sequence counter failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Reset sequence counter error: {str(e)}", "ERROR")
            return False
    
    def test_get_audit_trail(self) -> bool:
        """Test GET /api/finance/admin/audit-trail"""
        self.log("📜 Testing GET /api/finance/admin/audit-trail...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Test without filters
            response = self.session.get(f"{BASE_URL}/finance/admin/audit-trail", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Audit trail retrieved successfully. Count: {len(data)}")
                
                # Check if we have audit entries from our tests
                if data and len(data) > 0:
                    self.log(f"   Latest entry: {data[0].get('action', 'N/A')} on {data[0].get('entity_type', 'N/A')}")
                    self.log(f"   Changed by: {data[0].get('changed_by', 'N/A')}")
                    self.log(f"   Timestamp: {data[0].get('timestamp', 'N/A')}")
                
                # Test with filters
                filter_params = {
                    "entity_type": "invoice",
                    "start_date": "2025-01-01",
                    "end_date": "2026-12-31"
                }
                
                response_filtered = self.session.get(
                    f"{BASE_URL}/finance/admin/audit-trail", 
                    headers=headers, 
                    params=filter_params
                )
                
                if response_filtered.status_code == 200:
                    filtered_data = response_filtered.json()
                    self.log(f"   ✅ Filtered audit trail retrieved. Count: {len(filtered_data)}")
                
                return True
            else:
                self.log(f"❌ Get audit trail failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get audit trail error: {str(e)}", "ERROR")
            return False
    
    def test_access_control_non_admin(self) -> bool:
        """Test access control - non-admin users should be denied"""
        self.log("🔒 Testing access control for non-admin users...")
        
        # Create a test participant user
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        admin_headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Create test participant
        participant_data = {
            "email": f"testparticipant_{uuid.uuid4().hex[:8]}@test.com",
            "password": "testpass123",
            "full_name": "Test Participant Finance",
            "id_number": f"TFIN{uuid.uuid4().hex[:6].upper()}",
            "role": "participant",
            "location": "Test Location"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=participant_data, headers=admin_headers)
            
            if response.status_code == 200:
                self.log("✅ Test participant created for access control testing")
                
                # Login as participant
                login_data = {
                    "email": participant_data["email"],
                    "password": participant_data["password"]
                }
                
                login_response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
                
                if login_response.status_code == 200:
                    participant_token = login_response.json()['access_token']
                    participant_headers = {'Authorization': f'Bearer {participant_token}'}
                    
                    # Test access to finance admin endpoints (should fail with 403)
                    test_endpoints = [
                        f"{BASE_URL}/finance/admin/invoices",
                        f"{BASE_URL}/finance/admin/payments",
                        f"{BASE_URL}/finance/admin/audit-trail"
                    ]
                    
                    access_denied_count = 0
                    for endpoint in test_endpoints:
                        try:
                            test_response = self.session.get(endpoint, headers=participant_headers)
                            if test_response.status_code == 403:
                                access_denied_count += 1
                                self.log(f"   ✅ Access correctly denied to {endpoint}")
                            else:
                                self.log(f"   ❌ Access incorrectly allowed to {endpoint} (Status: {test_response.status_code})", "ERROR")
                        except Exception as e:
                            self.log(f"   ❌ Error testing {endpoint}: {str(e)}", "ERROR")
                    
                    if access_denied_count == len(test_endpoints):
                        self.log("✅ Access control working correctly - all endpoints denied to non-admin")
                        return True
                    else:
                        self.log(f"❌ Access control failed - {access_denied_count}/{len(test_endpoints)} endpoints properly secured", "ERROR")
                        return False
                else:
                    self.log("❌ Failed to login as test participant", "ERROR")
                    return False
            else:
                self.log("❌ Failed to create test participant", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Access control test error: {str(e)}", "ERROR")
            return False
    
    def test_finance_user_access(self) -> bool:
        """Test that finance users can access the endpoints"""
        self.log("👤 Testing finance user access...")
        
        if not self.finance_token:
            self.log("⚠️  No finance token available - skipping finance user access test", "WARNING")
            return True  # Not a failure, just no finance user to test with
            
        headers = {'Authorization': f'Bearer {self.finance_token}'}
        
        # Test key endpoints that finance users should have access to
        test_endpoints = [
            f"{BASE_URL}/finance/admin/invoices",
            f"{BASE_URL}/finance/admin/payments",
            f"{BASE_URL}/finance/admin/audit-trail"
        ]
        
        success_count = 0
        for endpoint in test_endpoints:
            try:
                response = self.session.get(endpoint, headers=headers)
                if response.status_code == 200:
                    success_count += 1
                    self.log(f"   ✅ Finance user access granted to {endpoint}")
                else:
                    self.log(f"   ❌ Finance user access denied to {endpoint} (Status: {response.status_code})", "ERROR")
            except Exception as e:
                self.log(f"   ❌ Error testing finance access to {endpoint}: {str(e)}", "ERROR")
        
        if success_count == len(test_endpoints):
            self.log("✅ Finance user access working correctly")
            return True
        else:
            self.log(f"❌ Finance user access failed - {success_count}/{len(test_endpoints)} endpoints accessible", "ERROR")
            return False
    
    def run_comprehensive_test(self):
        """Run all Super Admin Finance Features tests"""
        self.log("🚀 Starting Super Admin Finance Features Testing...")
        
        # Step 1: Authentication
        self.log("\n" + "="*60)
        self.log("STEP 1: AUTHENTICATION")
        self.log("="*60)
        
        if not self.login_admin():
            self.log("❌ CRITICAL: Admin login failed - cannot proceed with tests", "ERROR")
            return False
        
        # Try to login finance user (optional)
        self.login_finance()
        
        # Step 2: Test core endpoints
        self.log("\n" + "="*60)
        self.log("STEP 2: CORE FINANCE ADMIN ENDPOINTS")
        self.log("="*60)
        
        tests = [
            ("Get Admin Invoices", self.test_get_admin_invoices),
            ("Get Admin Payments", self.test_get_admin_payments),
            ("Edit Invoice Number", self.test_edit_invoice_number),
            ("Void Invoice", self.test_void_invoice),
            ("Backdate Invoice", self.test_backdate_invoice),
            ("Override Invoice Amount", self.test_override_invoice_amount),
            ("Delete Payment", self.test_delete_payment),
            ("Reset Sequence Counter", self.test_reset_sequence_counter),
            ("Get Audit Trail", self.test_get_audit_trail),
        ]
        
        for test_name, test_func in tests:
            self.log(f"\n--- {test_name} ---")
            try:
                result = test_func()
                self.test_results.append({
                    "test": test_name,
                    "passed": result,
                    "timestamp": datetime.now().isoformat()
                })
                if not result:
                    self.failed_tests.append(test_name)
            except Exception as e:
                self.log(f"❌ {test_name} crashed: {str(e)}", "ERROR")
                self.test_results.append({
                    "test": test_name,
                    "passed": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                self.failed_tests.append(test_name)
        
        # Step 3: Access Control Testing
        self.log("\n" + "="*60)
        self.log("STEP 3: ACCESS CONTROL TESTING")
        self.log("="*60)
        
        access_tests = [
            ("Non-Admin Access Control", self.test_access_control_non_admin),
            ("Finance User Access", self.test_finance_user_access),
        ]
        
        for test_name, test_func in access_tests:
            self.log(f"\n--- {test_name} ---")
            try:
                result = test_func()
                self.test_results.append({
                    "test": test_name,
                    "passed": result,
                    "timestamp": datetime.now().isoformat()
                })
                if not result:
                    self.failed_tests.append(test_name)
            except Exception as e:
                self.log(f"❌ {test_name} crashed: {str(e)}", "ERROR")
                self.test_results.append({
                    "test": test_name,
                    "passed": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                self.failed_tests.append(test_name)
        
        # Step 4: Generate final report
        self.generate_final_report()
        
        return len(self.failed_tests) == 0
    
    def generate_final_report(self):
        """Generate final test report"""
        self.log("\n" + "="*80)
        self.log("SUPER ADMIN FINANCE FEATURES TEST REPORT")
        self.log("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['passed']])
        failed_tests = len(self.failed_tests)
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({pass_rate:.1f}%)")
        print(f"Failed: {failed_tests}")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  • {test}")
        
        if passed_tests > 0:
            print(f"\n✅ PASSED TESTS:")
            for result in self.test_results:
                if result['passed']:
                    print(f"  • {result['test']}")
        
        # Critical endpoints status
        critical_endpoints = [
            "Get Admin Invoices",
            "Edit Invoice Number", 
            "Void Invoice",
            "Get Audit Trail",
            "Non-Admin Access Control"
        ]
        
        print(f"\n🔥 CRITICAL ENDPOINTS STATUS:")
        for endpoint in critical_endpoints:
            status = "✅ WORKING" if endpoint not in self.failed_tests else "❌ FAILING"
            print(f"  {endpoint}: {status}")
        
        print("\n" + "="*80)
        
        # Overall status
        if len(self.failed_tests) == 0:
            self.log("🎉 ALL SUPER ADMIN FINANCE FEATURES TESTS PASSED!", "SUCCESS")
        elif len(self.failed_tests) <= 2:
            self.log(f"⚠️  MOSTLY WORKING - {len(self.failed_tests)} minor issues found", "WARNING")
        else:
            self.log(f"❌ MULTIPLE ISSUES FOUND - {len(self.failed_tests)} tests failed", "ERROR")

def main():
    """Main test execution"""
    tester = SuperAdminFinanceTest()
    success = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()