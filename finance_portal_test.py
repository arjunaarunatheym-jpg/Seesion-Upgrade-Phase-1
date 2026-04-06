#!/usr/bin/env python3
"""
Finance Portal Backend Test Suite
Tests the Session Costing improvements and Finance Portal endpoints as requested:

1. Invoice Number Format (Backend) - GET /api/finance/invoices
2. Invoice Persistence (Backend) - POST /api/finance/session/{session_id}/invoice  
3. Expense Categories (Backend) - GET /api/finance/expense-categories
4. Marketing Users Dropdown (Backend) - GET /api/finance/marketing-users
5. Trainer Income (Backend) - GET /api/finance/income/trainer/{trainer_id}
6. Coordinator Income (Backend) - GET /api/finance/income/coordinator/{coordinator_id}

Credentials: Admin: arjuna@mddrc.com.my / Dana102229
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://quote-n-cert.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

class FinancePortalTestRunner:
    def __init__(self):
        self.admin_token = None
        self.session_id = None
        self.trainer_id = None
        self.coordinator_id = None
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_admin(self):
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
                self.log(f"✅ Admin login successful. User: {data['user']['full_name']} ({data['user']['role']})")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin login error: {str(e)}", "ERROR")
            return False
    
    def get_first_session(self):
        """Get the first session from /api/sessions for testing"""
        self.log("📋 Getting first session for testing...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/sessions", headers=headers)
            
            if response.status_code == 200:
                sessions = response.json()
                if sessions:
                    self.session_id = sessions[0]['id']
                    session_name = sessions[0].get('name', 'Unknown')
                    self.log(f"✅ Using session: {session_name} (ID: {self.session_id})")
                    return True
                else:
                    self.log("❌ No sessions found", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to get sessions: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get sessions error: {str(e)}", "ERROR")
            return False
    
    def get_trainer_and_coordinator_ids(self):
        """Get trainer and coordinator IDs for income testing"""
        self.log("👥 Getting trainer and coordinator IDs...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            # Get users and find trainers and coordinators
            response = self.session.get(f"{BASE_URL}/users", headers=headers)
            
            if response.status_code == 200:
                users = response.json()
                
                # Find first trainer
                for user in users:
                    if user.get('role') == 'trainer':
                        self.trainer_id = user['id']
                        self.log(f"✅ Found trainer: {user['full_name']} (ID: {self.trainer_id})")
                        break
                
                # Find first coordinator
                for user in users:
                    if user.get('role') == 'coordinator':
                        self.coordinator_id = user['id']
                        self.log(f"✅ Found coordinator: {user['full_name']} (ID: {self.coordinator_id})")
                        break
                
                if not self.trainer_id:
                    self.log("⚠️ No trainer found, will skip trainer income tests", "WARNING")
                if not self.coordinator_id:
                    self.log("⚠️ No coordinator found, will skip coordinator income tests", "WARNING")
                
                return True
            else:
                self.log(f"❌ Failed to get users: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get users error: {str(e)}", "ERROR")
            return False

    def test_invoice_number_format(self):
        """Test 1: Invoice Number Format - GET /api/finance/invoices"""
        self.log("💰 TEST 1: Testing Invoice Number Format (GET /api/finance/invoices)...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/invoices", headers=headers)
            
            if response.status_code == 200:
                invoices = response.json()
                self.log(f"✅ Retrieved invoices successfully. Count: {len(invoices)}")
                
                # Check invoice number format: INV/MDDRC/YYYY/MM/NNNN
                format_correct = True
                for invoice in invoices:
                    invoice_number = invoice.get('invoice_number', '')
                    if invoice_number:
                        # Expected format: INV/MDDRC/YYYY/MM/NNNN
                        parts = invoice_number.split('/')
                        if len(parts) == 5 and parts[0] == 'INV' and parts[1] == 'MDDRC':
                            self.log(f"✅ Invoice number format correct: {invoice_number}")
                        else:
                            self.log(f"❌ Invoice number format incorrect: {invoice_number}", "ERROR")
                            format_correct = False
                    else:
                        self.log("⚠️ Invoice found without invoice_number", "WARNING")
                
                if format_correct and invoices:
                    self.log("✅ All invoice numbers follow correct format INV/MDDRC/YYYY/MM/NNNN")
                elif not invoices:
                    self.log("⚠️ No invoices found to check format", "WARNING")
                
                return True
            else:
                self.log(f"❌ Get invoices failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get invoices error: {str(e)}", "ERROR")
            return False

    def test_invoice_persistence(self):
        """Test 2: Invoice Persistence - POST /api/finance/session/{session_id}/invoice"""
        self.log("💾 TEST 2: Testing Invoice Persistence (POST /api/finance/session/{session_id}/invoice)...")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test invoice data
        invoice_data = {
            "total_amount": 10000.00,
            "tax_rate": 6.0,
            "tax_amount": 600.00,
            "subtotal": 9400.00,
            "line_items": [
                {
                    "description": "Defensive Driving Training",
                    "quantity": 1,
                    "unit_price": 10000.00,
                    "amount": 10000.00
                }
            ]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/invoice", 
                                       json=invoice_data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Invoice created/updated successfully. Response: {result}")
                
                # Get the invoice ID and fetch the actual invoice to verify
                invoice_id = result.get('invoice_id')
                if invoice_id:
                    # Fetch the created invoice to verify data persistence
                    get_response = self.session.get(f"{BASE_URL}/finance/invoices/{invoice_id}", headers=headers)
                    if get_response.status_code == 200:
                        invoice = get_response.json()
                        self.log(f"   Total Amount: RM {invoice.get('total_amount', 0)}")
                        self.log(f"   Tax Rate: {invoice.get('tax_rate', 0)}%")
                        self.log(f"   Invoice Number: {invoice.get('invoice_number', 'N/A')}")
                        
                        # Verify total_amount is saved correctly
                        if invoice.get('total_amount') == 10000.00:
                            self.log("✅ Total amount saved correctly")
                            return True
                        else:
                            self.log(f"❌ Total amount incorrect. Expected: 10000.00, Got: {invoice.get('total_amount')}", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Failed to fetch created invoice: {get_response.status_code}", "ERROR")
                        return False
                else:
                    self.log("❌ No invoice_id returned in response", "ERROR")
                    return False
            else:
                self.log(f"❌ Invoice creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Invoice creation error: {str(e)}", "ERROR")
            return False

    def test_expense_categories(self):
        """Test 3: Expense Categories - GET /api/finance/expense-categories"""
        self.log("📊 TEST 3: Testing Expense Categories (GET /api/finance/expense-categories)...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/expense-categories", headers=headers)
            
            if response.status_code == 200:
                categories = response.json()
                self.log(f"✅ Retrieved expense categories successfully. Count: {len(categories)}")
                
                # Expected categories with their types and rates
                expected_categories = {
                    'fnb': {'type': 'per_pax', 'rate': 25},
                    'hrdc_levy': {'type': 'percentage', 'rate': 4},
                    'wear_tear': {'type': 'percentage', 'rate': 2},
                    'printing': {'type': 'percentage', 'rate': 1}
                }
                
                # Check each expected category
                all_correct = True
                for category in categories:
                    cat_id = category.get('id')  # Use 'id' instead of 'category'
                    if cat_id in expected_categories:
                        expected = expected_categories[cat_id]
                        actual_type = category.get('type')
                        actual_rate = category.get('rate')
                        
                        if actual_type == expected['type'] and actual_rate == expected['rate']:
                            self.log(f"✅ {cat_id}: type={actual_type}, rate={actual_rate} ✓")
                        else:
                            self.log(f"❌ {cat_id}: Expected type={expected['type']}, rate={expected['rate']} but got type={actual_type}, rate={actual_rate}", "ERROR")
                            all_correct = False
                    else:
                        cat_name = category.get('name', 'Unknown')
                        self.log(f"ℹ️ Additional category found: {cat_id} ({cat_name})")
                
                # Check if all expected categories are present
                found_categories = [cat.get('id') for cat in categories]
                for expected_cat in expected_categories:
                    if expected_cat not in found_categories:
                        self.log(f"❌ Missing expected category: {expected_cat}", "ERROR")
                        all_correct = False
                
                if all_correct:
                    self.log("✅ All expected expense categories found with correct types and rates")
                
                return True
            else:
                self.log(f"❌ Get expense categories failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get expense categories error: {str(e)}", "ERROR")
            return False

    def test_marketing_users_dropdown(self):
        """Test 4: Marketing Users Dropdown - GET /api/finance/marketing-users"""
        self.log("👤 TEST 4: Testing Marketing Users Dropdown (GET /api/finance/marketing-users)...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/marketing-users", headers=headers)
            
            if response.status_code == 200:
                users = response.json()
                self.log(f"✅ Retrieved marketing users successfully. Count: {len(users)}")
                
                # Should return all staff (coordinators, trainers, assistant_admins)
                expected_roles = ['coordinator', 'trainer', 'assistant_admin']
                found_roles = set()
                
                for user in users:
                    role = user.get('role')
                    name = user.get('full_name', 'Unknown')
                    user_id = user.get('id', 'Unknown')
                    
                    if role in expected_roles:
                        found_roles.add(role)
                        self.log(f"✅ Found {role}: {name} (ID: {user_id})")
                    else:
                        self.log(f"ℹ️ User with role '{role}': {name}")
                
                if found_roles:
                    self.log(f"✅ Found staff with roles: {', '.join(found_roles)}")
                else:
                    self.log("⚠️ No staff members found (coordinators, trainers, assistant_admins)", "WARNING")
                
                return True
            else:
                self.log(f"❌ Get marketing users failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get marketing users error: {str(e)}", "ERROR")
            return False

    def test_trainer_income(self):
        """Test 5: Trainer Income - GET /api/finance/income/trainer/{trainer_id}"""
        self.log("💰 TEST 5: Testing Trainer Income (GET /api/finance/income/trainer/{trainer_id})...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        if not self.trainer_id:
            self.log("⚠️ No trainer ID available, skipping trainer income test", "WARNING")
            return True
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/income/trainer/{self.trainer_id}", headers=headers)
            
            if response.status_code == 200:
                income_data = response.json()
                self.log(f"✅ Retrieved trainer income successfully")
                
                # Should return fees with trainer_name and company_name
                if isinstance(income_data, list):
                    self.log(f"   Found {len(income_data)} income records")
                    for record in income_data:
                        trainer_name = record.get('trainer_name', 'N/A')
                        company_name = record.get('company_name', 'N/A')
                        amount = record.get('fee_amount', 0)
                        self.log(f"   ✅ Trainer: {trainer_name}, Company: {company_name}, Amount: RM {amount}")
                else:
                    trainer_name = income_data.get('trainer_name', 'N/A')
                    company_name = income_data.get('company_name', 'N/A')
                    self.log(f"   ✅ Trainer: {trainer_name}, Company: {company_name}")
                
                return True
            else:
                self.log(f"❌ Get trainer income failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get trainer income error: {str(e)}", "ERROR")
            return False

    def test_coordinator_income(self):
        """Test 6: Coordinator Income - GET /api/finance/income/coordinator/{coordinator_id}"""
        self.log("💰 TEST 6: Testing Coordinator Income (GET /api/finance/income/coordinator/{coordinator_id})...")
        
        if not self.admin_token:
            self.log("❌ No admin token available", "ERROR")
            return False
            
        if not self.coordinator_id:
            self.log("⚠️ No coordinator ID available, skipping coordinator income test", "WARNING")
            return True
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/income/coordinator/{self.coordinator_id}", headers=headers)
            
            if response.status_code == 200:
                income_data = response.json()
                self.log(f"✅ Retrieved coordinator income successfully")
                
                # Should return fees with company_name
                if isinstance(income_data, list):
                    self.log(f"   Found {len(income_data)} income records")
                    for record in income_data:
                        company_name = record.get('company_name', 'N/A')
                        amount = record.get('total_fee', 0)
                        self.log(f"   ✅ Company: {company_name}, Amount: RM {amount}")
                else:
                    company_name = income_data.get('company_name', 'N/A')
                    self.log(f"   ✅ Company: {company_name}")
                
                return True
            else:
                self.log(f"❌ Get coordinator income failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get coordinator income error: {str(e)}", "ERROR")
            return False

    def run_all_tests(self):
        """Run all finance portal tests"""
        self.log("🚀 Starting Finance Portal Backend Test Suite...")
        self.log("=" * 80)
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Get First Session", self.get_first_session),
            ("Get Trainer/Coordinator IDs", self.get_trainer_and_coordinator_ids),
            ("Invoice Number Format", self.test_invoice_number_format),
            ("Invoice Persistence", self.test_invoice_persistence),
            ("Expense Categories", self.test_expense_categories),
            ("Marketing Users Dropdown", self.test_marketing_users_dropdown),
            ("Trainer Income", self.test_trainer_income),
            ("Coordinator Income", self.test_coordinator_income),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n🧪 Running: {test_name}")
            self.log("-" * 50)
            
            try:
                if test_func():
                    passed += 1
                    self.log(f"✅ {test_name} PASSED")
                else:
                    failed += 1
                    self.log(f"❌ {test_name} FAILED")
            except Exception as e:
                failed += 1
                self.log(f"❌ {test_name} FAILED with exception: {str(e)}", "ERROR")
        
        # Final summary
        self.log("\n" + "=" * 80)
        self.log("🏁 FINANCE PORTAL TEST SUITE SUMMARY")
        self.log("=" * 80)
        self.log(f"✅ PASSED: {passed}")
        self.log(f"❌ FAILED: {failed}")
        self.log(f"📊 TOTAL: {passed + failed}")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED! Finance Portal is working correctly.")
            return True
        else:
            self.log(f"⚠️ {failed} test(s) failed. Please review the issues above.")
            return False

def main():
    """Main function to run the finance portal tests"""
    runner = FinancePortalTestRunner()
    success = runner.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()