#!/usr/bin/env python3
"""
Session Costing Feature Test Suite for Finance Portal Phase 1
Tests all Session Costing endpoints and profit calculation logic
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://data-integrity-lab-4.preview.emergentagent.com/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

class SessionCostingTestRunner:
    def __init__(self):
        self.admin_token = None
        self.session_id = None
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
    
    def get_first_session_id(self):
        """Get the first available session ID for testing"""
        self.log("Getting first available session ID...")
        
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
                    self.log(f"✅ Using session ID: {self.session_id} (Name: {session_name})")
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
    
    def test_get_session_costing(self):
        """Test GET /api/finance/session/{session_id}/costing"""
        self.log("Testing GET /api/finance/session/{session_id}/costing...")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/session/{self.session_id}/costing", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Session costing retrieved successfully")
                self.log(f"   Session ID: {data.get('session_id', 'N/A')}")
                self.log(f"   Session Name: {data.get('session_name', 'N/A')}")
                self.log(f"   Company Name: {data.get('company_name', 'N/A')}")
                self.log(f"   Invoice Total: RM {data.get('invoice_total', 0)}")
                self.log(f"   Gross Revenue: RM {data.get('gross_revenue', 0)}")
                self.log(f"   Total Expenses: RM {data.get('total_expenses', 0)}")
                self.log(f"   Net Profit: RM {data.get('profit', 0)}")
                return True
            else:
                self.log(f"❌ Get session costing failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get session costing error: {str(e)}", "ERROR")
            return False
    
    def test_get_expense_categories(self):
        """Test GET /api/finance/expense-categories"""
        self.log("Testing GET /api/finance/expense-categories...")
        
        if not self.admin_token:
            self.log("❌ Missing admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/expense-categories", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Expense categories retrieved successfully. Count: {len(data)}")
                
                # Check if we have 10 expense categories as expected
                if len(data) == 10:
                    self.log("✅ Found expected 10 expense categories")
                else:
                    self.log(f"⚠️  Expected 10 expense categories, found {len(data)}", "WARNING")
                
                # Log the categories
                for category in data:
                    self.log(f"   - {category}")
                
                return True
            else:
                self.log(f"❌ Get expense categories failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get expense categories error: {str(e)}", "ERROR")
            return False
    
    def test_get_marketing_users(self):
        """Test GET /api/finance/marketing-users"""
        self.log("Testing GET /api/finance/marketing-users...")
        
        if not self.admin_token:
            self.log("❌ Missing admin token", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = self.session.get(f"{BASE_URL}/finance/marketing-users", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Marketing users retrieved successfully. Count: {len(data)}")
                
                # Log the marketing users
                for user in data:
                    self.log(f"   - {user.get('full_name', 'N/A')} ({user.get('email', 'N/A')})")
                
                return True
            else:
                self.log(f"❌ Get marketing users failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Get marketing users error: {str(e)}", "ERROR")
            return False
    
    def test_save_trainer_fees(self):
        """Test POST /api/finance/session/{session_id}/trainer-fees"""
        self.log("Testing POST /api/finance/session/{session_id}/trainer-fees...")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Sample trainer fees data - API expects List[dict] directly
        trainer_fees_data = [
            {
                "trainer_id": "trainer-1",
                "trainer_name": "John Doe",
                "role": "chief_trainer",
                "fee_amount": 800.0,
                "remark": "Chief trainer fee"
            },
            {
                "trainer_id": "trainer-2", 
                "trainer_name": "Jane Smith",
                "role": "trainer",
                "fee_amount": 700.0,
                "remark": "Regular trainer fee"
            }
        ]
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/trainer-fees", 
                                       json=trainer_fees_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Trainer fees saved successfully")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                self.log(f"   Total trainer fees: RM {sum(fee['fee_amount'] for fee in trainer_fees_data)}")
                return True
            else:
                self.log(f"❌ Save trainer fees failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Save trainer fees error: {str(e)}", "ERROR")
            return False
    
    def test_save_coordinator_fee(self):
        """Test POST /api/finance/session/{session_id}/coordinator-fee"""
        self.log("Testing POST /api/finance/session/{session_id}/coordinator-fee...")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Sample coordinator fee data (RM 50/day x 2 days = RM 100)
        coordinator_fee_data = {
            "coordinator_id": "coordinator-1",
            "coordinator_name": "Alice Johnson",
            "num_days": 2,
            "daily_rate": 50.0,
            "total_fee": 100.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/coordinator-fee", 
                                       json=coordinator_fee_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Coordinator fee saved successfully")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                self.log(f"   Coordinator fee: RM {coordinator_fee_data['total_fee']} ({coordinator_fee_data['num_days']} days x RM {coordinator_fee_data['daily_rate']}/day)")
                return True
            else:
                self.log(f"❌ Save coordinator fee failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Save coordinator fee error: {str(e)}", "ERROR")
            return False
    
    def test_save_expenses(self):
        """Test POST /api/finance/session/{session_id}/expenses"""
        self.log("Testing POST /api/finance/session/{session_id}/expenses...")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Sample expenses data - API expects List[dict] directly
        expenses_data = [
            {
                "category": "accommodation",
                "description": "Hotel accommodation for trainers",
                "expense_type": "fixed",
                "actual_amount": 200.0,
                "quantity": 2,
                "unit_price": 100.0,
                "remark": "2 nights accommodation"
            },
            {
                "category": "allowance",
                "description": "Meal allowance",
                "expense_type": "fixed", 
                "actual_amount": 150.0,
                "quantity": 3,
                "unit_price": 50.0,
                "remark": "Meal allowance for 3 people"
            },
            {
                "category": "petrol",
                "description": "Fuel costs",
                "expense_type": "fixed",
                "actual_amount": 150.0,
                "quantity": 1,
                "unit_price": 150.0,
                "remark": "Travel fuel costs"
            }
        ]
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/expenses", 
                                       json=expenses_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Expenses saved successfully")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                total_expenses = sum(expense['actual_amount'] for expense in expenses_data)
                self.log(f"   Total expenses: RM {total_expenses}")
                return True
            else:
                self.log(f"❌ Save expenses failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Save expenses error: {str(e)}", "ERROR")
            return False
    
    def test_save_marketing_commission(self):
        """Test POST /api/finance/session/{session_id}/marketing"""
        self.log("Testing POST /api/finance/session/{session_id}/marketing...")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Sample marketing commission data (10% of profit)
        marketing_data = {
            "marketing_user_id": "marketing-1",
            "marketing_user_name": "Bob Wilson",
            "commission_type": "percentage",
            "commission_rate": 10.0,
            "fixed_amount": 0.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/marketing", 
                                       json=marketing_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Marketing commission saved successfully")
                self.log(f"   Message: {data.get('message', 'N/A')}")
                self.log(f"   Commission: {marketing_data['commission_rate']}% of profit")
                return True
            else:
                self.log(f"❌ Save marketing commission failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Save marketing commission error: {str(e)}", "ERROR")
            return False
    
    def test_profit_calculation_verification(self):
        """Test profit calculation with specific values as per requirements"""
        self.log("Testing profit calculation verification...")
        self.log("Expected calculation: Invoice 10000, Tax 6%, Trainer fees 1500, Coordinator 100, Expenses 500, Marketing 10%")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Step 1: Set up invoice amount (this would typically be done in invoice management)
        # For testing, we'll assume the invoice is already set to 10000 with 6% tax
        
        # Step 2: Save trainer fees (1500 total)
        trainer_fees_data = [
            {
                "trainer_id": "test-trainer-1",
                "trainer_name": "Test Trainer",
                "role": "chief_trainer",
                "fee_amount": 1500.0,
                "remark": "Test trainer fee for calculation"
            }
        ]
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/trainer-fees", 
                                       json=trainer_fees_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to set trainer fees: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error setting trainer fees: {str(e)}", "ERROR")
            return False
        
        # Step 3: Save coordinator fee (50/day x 2 days = 100)
        coordinator_fee_data = {
            "coordinator_id": "test-coordinator-1",
            "coordinator_name": "Test Coordinator",
            "num_days": 2,
            "daily_rate": 50.0,
            "total_fee": 100.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/coordinator-fee", 
                                       json=coordinator_fee_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to set coordinator fee: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error setting coordinator fee: {str(e)}", "ERROR")
            return False
        
        # Step 4: Save expenses (500 total)
        expenses_data = [
            {
                "category": "accommodation",
                "description": "Test accommodation expense",
                "expense_type": "fixed",
                "actual_amount": 500.0,
                "quantity": 1,
                "unit_price": 500.0,
                "remark": "Test expense for calculation"
            }
        ]
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/expenses", 
                                       json=expenses_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to set expenses: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error setting expenses: {str(e)}", "ERROR")
            return False
        
        # Step 5: Save marketing commission (10%)
        marketing_data = {
            "marketing_user_id": "test-marketing-1",
            "marketing_user_name": "Test Marketing",
            "commission_type": "percentage",
            "commission_rate": 10.0,
            "fixed_amount": 0.0
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/marketing", 
                                       json=marketing_data, headers=headers)
            if response.status_code != 200:
                self.log(f"❌ Failed to set marketing commission: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Error setting marketing commission: {str(e)}", "ERROR")
            return False
        
        # Step 6: Get updated costing and verify calculations
        try:
            response = self.session.get(f"{BASE_URL}/finance/session/{self.session_id}/costing", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Expected calculations:
                # Invoice: 10000, Tax: 6% = 600, Gross Revenue: 10000 - 600 = 9400
                # Expenses: Trainer 1500 + Coordinator 100 + Other 500 = 2100
                # Profit before marketing: 9400 - 2100 = 7300
                # Marketing commission: 7300 * 10% = 730
                # Net profit: 7300 - 730 = 6570
                
                invoice_total = data.get('invoice_total', 0)
                tax_amount = data.get('less_tax', 0)
                gross_revenue = data.get('gross_revenue', 0)
                trainer_fees_total = data.get('trainer_fees_total', 0)
                coordinator_fees_total = data.get('coordinator_fees_total', 0)
                cash_expenses_total = data.get('cash_expenses_total', 0)
                marketing_commission = data.get('marketing_commission', 0)
                net_profit = data.get('profit', 0)
                
                self.log("📊 PROFIT CALCULATION VERIFICATION:")
                self.log(f"   Invoice Total: RM {invoice_total}")
                self.log(f"   Less Tax (6%): RM {tax_amount}")
                self.log(f"   Gross Revenue: RM {gross_revenue}")
                self.log(f"   Trainer Fees: RM {trainer_fees_total}")
                self.log(f"   Coordinator Fees: RM {coordinator_fees_total}")
                self.log(f"   Cash Expenses: RM {cash_expenses_total}")
                self.log(f"   Marketing Commission: RM {marketing_commission}")
                self.log(f"   Net Profit: RM {net_profit}")
                
                # Verify calculations (allowing for small floating point differences)
                expected_gross_revenue = 9400  # 10000 - 600
                expected_expenses_total = 2100  # 1500 + 100 + 500
                expected_profit_before_marketing = 7300  # 9400 - 2100
                expected_marketing_commission = 730  # 7300 * 10%
                expected_net_profit = 6570  # 7300 - 730
                
                tolerance = 0.01  # Allow 1 cent difference for floating point
                
                if abs(gross_revenue - expected_gross_revenue) <= tolerance:
                    self.log("✅ Gross Revenue calculation correct")
                else:
                    self.log(f"❌ Gross Revenue incorrect. Expected: {expected_gross_revenue}, Got: {gross_revenue}", "ERROR")
                
                total_expenses = trainer_fees_total + coordinator_fees_total + cash_expenses_total
                if abs(total_expenses - expected_expenses_total) <= tolerance:
                    self.log("✅ Total expenses calculation correct")
                else:
                    self.log(f"❌ Total expenses incorrect. Expected: {expected_expenses_total}, Got: {total_expenses}", "ERROR")
                
                if abs(marketing_commission - expected_marketing_commission) <= tolerance:
                    self.log("✅ Marketing commission calculation correct")
                else:
                    self.log(f"❌ Marketing commission incorrect. Expected: {expected_marketing_commission}, Got: {marketing_commission}", "ERROR")
                
                if abs(net_profit - expected_net_profit) <= tolerance:
                    self.log("✅ Net profit calculation correct")
                    return True
                else:
                    self.log(f"❌ Net profit incorrect. Expected: {expected_net_profit}, Got: {net_profit}", "ERROR")
                    return False
                    
            else:
                self.log(f"❌ Failed to get costing for verification: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Profit calculation verification error: {str(e)}", "ERROR")
            return False
    
    def test_error_handling(self):
        """Test error handling with invalid data"""
        self.log("Testing error handling with invalid data...")
        
        if not self.admin_token or not self.session_id:
            self.log("❌ Missing admin token or session ID", "ERROR")
            return False
            
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        # Test 1: Invalid trainer fees data (missing required fields)
        self.log("Testing invalid trainer fees data...")
        invalid_trainer_data = [
            {
                "trainer_id": "",  # Empty trainer ID
                "fee_amount": -100.0,  # Negative amount
            }
        ]
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/{self.session_id}/trainer-fees", 
                                       json=invalid_trainer_data, headers=headers)
            
            if response.status_code >= 400:
                self.log("✅ Invalid trainer fees correctly rejected")
            else:
                self.log("⚠️  Invalid trainer fees accepted (should be rejected)", "WARNING")
        except Exception as e:
            self.log(f"❌ Error testing invalid trainer fees: {str(e)}", "ERROR")
        
        # Test 2: Invalid session ID
        self.log("Testing invalid session ID...")
        valid_data = [
            {
                "trainer_id": "test-trainer",
                "trainer_name": "Test Trainer",
                "role": "trainer",
                "fee_amount": 500.0
            }
        ]
        
        try:
            response = self.session.post(f"{BASE_URL}/finance/session/invalid-session-id/trainer-fees", 
                                       json=valid_data, headers=headers)
            
            if response.status_code == 404:
                self.log("✅ Invalid session ID correctly returned 404")
            else:
                self.log(f"⚠️  Invalid session ID returned {response.status_code} (expected 404)", "WARNING")
        except Exception as e:
            self.log(f"❌ Error testing invalid session ID: {str(e)}", "ERROR")
        
        # Test 3: Unauthorized access (no token)
        self.log("Testing unauthorized access...")
        try:
            response = self.session.get(f"{BASE_URL}/finance/session/{self.session_id}/costing")
            
            if response.status_code == 401 or response.status_code == 403:
                self.log("✅ Unauthorized access correctly rejected")
                return True
            else:
                self.log(f"⚠️  Unauthorized access returned {response.status_code} (expected 401/403)", "WARNING")
                return False
        except Exception as e:
            self.log(f"❌ Error testing unauthorized access: {str(e)}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all session costing tests"""
        self.log("🚀 Starting Session Costing Feature Test Suite...")
        
        tests = [
            ("Admin Login", self.login_admin),
            ("Get First Session ID", self.get_first_session_id),
            ("Get Session Costing", self.test_get_session_costing),
            ("Get Expense Categories", self.test_get_expense_categories),
            ("Get Marketing Users", self.test_get_marketing_users),
            ("Save Trainer Fees", self.test_save_trainer_fees),
            ("Save Coordinator Fee", self.test_save_coordinator_fee),
            ("Save Expenses", self.test_save_expenses),
            ("Save Marketing Commission", self.test_save_marketing_commission),
            ("Profit Calculation Verification", self.test_profit_calculation_verification),
            ("Error Handling", self.test_error_handling),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n--- Running Test: {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    self.log(f"✅ {test_name} PASSED")
                else:
                    failed += 1
                    self.log(f"❌ {test_name} FAILED", "ERROR")
            except Exception as e:
                failed += 1
                self.log(f"❌ {test_name} FAILED with exception: {str(e)}", "ERROR")
        
        self.log(f"\n🏁 SESSION COSTING TEST SUITE COMPLETED")
        self.log(f"📊 Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED!")
            return True
        else:
            self.log(f"⚠️  {failed} test(s) failed")
            return False

if __name__ == "__main__":
    runner = SessionCostingTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)