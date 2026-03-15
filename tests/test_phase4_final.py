"""
Phase 4 Final Testing - Report Generation, Session Closure, Finance Flows, Payments, P&L, Petty Cash, Payslips
Session ID: d664b79d-91a1-4968-bd72-de82611cdb1f (RapidKL Bus Defensive Training)
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://session-excel-hub.preview.emergentagent.com')
SESSION_ID = "d664b79d-91a1-4968-bd72-de82611cdb1f"

# Test credentials
CREDENTIALS = {
    "admin": {"email": "arjuna@mddrc.com.my", "password": "Dana102229"},
    "finance": {"email": "sunder@sdc.com.my", "password": "mddrc1"},
    "coordinator": {"email": "malek@mddrc.com.my", "password": "mddrc1"},
    "supervisor": {"email": "rapidkl@gmail.com", "password": "mddrc1"},
    "marketer": {"email": "chandra.selvaguru@mddrc.com.my", "password": "mddrc1"},
    "trainer": {"email": "vijay@mddrc.com.my", "password": "mddrc1"},
}


class TestAuth:
    """Test authentication for all users"""
    
    @pytest.fixture(scope="class")
    def tokens(self):
        """Get tokens for all users"""
        tokens = {}
        for role, creds in CREDENTIALS.items():
            response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
            if response.status_code == 200:
                tokens[role] = response.json().get("access_token")
                print(f"✓ {role} login successful")
            else:
                print(f"✗ {role} login failed: {response.status_code} - {response.text}")
        return tokens
    
    def test_all_logins(self, tokens):
        """Verify all users can login"""
        assert "coordinator" in tokens, "Coordinator login required"
        assert "finance" in tokens or "admin" in tokens, "Finance or Admin login required"
        print(f"Logged in users: {list(tokens.keys())}")


class TestPartA_ReportAndSessionClosure:
    """Part A: Report Generation and Session Closure"""
    
    @pytest.fixture(scope="class")
    def coordinator_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["coordinator"])
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["supervisor"])
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_1_get_session_status(self, coordinator_token):
        """Check session status before report generation"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions/{SESSION_ID}/status", headers=headers)
        print(f"Session status response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Session: {data.get('session_name')}")
            print(f"Pre-test completed: {data.get('pre_test_completed')}/{data.get('total_participants')}")
            print(f"Post-test completed: {data.get('post_test_completed')}/{data.get('total_participants')}")
            print(f"Feedback completed: {data.get('feedback_completed')}/{data.get('total_participants')}")
        assert response.status_code == 200
    
    def test_2_check_existing_report(self, coordinator_token):
        """Check if report already exists"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/training-reports/{SESSION_ID}", headers=headers)
        print(f"Existing report check: {response.status_code}")
        if response.status_code == 200:
            print("Report already exists")
        elif response.status_code == 404:
            print("No report exists yet - will generate")
        return response.status_code
    
    def test_3_generate_report(self, coordinator_token):
        """Generate training report"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.post(
            f"{BASE_URL}/api/reports/generate",
            headers=headers,
            json={"session_id": SESSION_ID}
        )
        print(f"Generate report response: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"Report ID: {data.get('id')}")
            print(f"Report status: {data.get('status')}")
        else:
            print(f"Response: {response.text[:500]}")
        # Accept 200, 201, or 400 (if already exists)
        assert response.status_code in [200, 201, 400]
    
    def test_4_get_completion_checklist(self, coordinator_token):
        """Get session completion checklist"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions/{SESSION_ID}/completion-checklist", headers=headers)
        print(f"Completion checklist: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Checklist items: {data}")
        assert response.status_code == 200
    
    def test_5_mark_session_completed(self, coordinator_token):
        """Mark session as completed by coordinator"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.post(f"{BASE_URL}/api/sessions/{SESSION_ID}/mark-completed", headers=headers)
        print(f"Mark completed response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Session completion status: {data.get('completion_status')}")
        else:
            print(f"Response: {response.text[:500]}")
        # Accept 200 or 400 (if already completed)
        assert response.status_code in [200, 400]
    
    def test_6_supervisor_can_view_session(self, supervisor_token):
        """Verify supervisor can view session"""
        if not supervisor_token:
            pytest.skip("Supervisor login failed")
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/supervisor/sessions", headers=headers)
        print(f"Supervisor sessions: {response.status_code}")
        if response.status_code == 200:
            sessions = response.json()
            print(f"Supervisor can see {len(sessions)} sessions")
        assert response.status_code == 200


class TestPartB_FinanceInvoiceFlow:
    """Part B: Finance Invoice Flow and Payment Recording"""
    
    @pytest.fixture(scope="class")
    def finance_token(self):
        # Try finance first, then admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["finance"])
        if response.status_code == 200:
            return response.json().get("access_token")
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_1_get_invoices(self, finance_token):
        """Get all invoices"""
        headers = {"Authorization": f"Bearer {finance_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/invoices", headers=headers)
        print(f"Get invoices: {response.status_code}")
        if response.status_code == 200:
            invoices = response.json()
            print(f"Total invoices: {len(invoices)}")
            # Find invoice for our session
            session_invoice = next((inv for inv in invoices if inv.get("session_id") == SESSION_ID), None)
            if session_invoice:
                print(f"Session invoice: {session_invoice.get('invoice_number')} - Status: {session_invoice.get('status')}")
                return session_invoice
        assert response.status_code == 200
    
    def test_2_get_session_invoice(self, finance_token):
        """Get invoice for specific session"""
        headers = {"Authorization": f"Bearer {finance_token}"}
        # First get all invoices and find the one for our session
        response = requests.get(f"{BASE_URL}/api/finance/invoices", headers=headers)
        if response.status_code == 200:
            invoices = response.json()
            session_invoice = next((inv for inv in invoices if inv.get("session_id") == SESSION_ID), None)
            if session_invoice:
                invoice_id = session_invoice.get("id")
                # Get specific invoice
                response2 = requests.get(f"{BASE_URL}/api/finance/invoices/{invoice_id}", headers=headers)
                print(f"Get specific invoice: {response2.status_code}")
                if response2.status_code == 200:
                    inv = response2.json()
                    print(f"Invoice: {inv.get('invoice_number')}")
                    print(f"Status: {inv.get('status')}")
                    print(f"Total: RM {inv.get('total_amount', 0)}")
                    return inv
        return None
    
    def test_3_issue_invoice_if_needed(self, finance_token):
        """Issue invoice if in draft/approved status"""
        headers = {"Authorization": f"Bearer {finance_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/invoices", headers=headers)
        if response.status_code == 200:
            invoices = response.json()
            session_invoice = next((inv for inv in invoices if inv.get("session_id") == SESSION_ID), None)
            if session_invoice:
                invoice_id = session_invoice.get("id")
                status = session_invoice.get("status")
                print(f"Current invoice status: {status}")
                
                # If auto_draft, approve first
                if status == "auto_draft":
                    approve_resp = requests.post(f"{BASE_URL}/api/finance/invoices/{invoice_id}/approve", headers=headers)
                    print(f"Approve invoice: {approve_resp.status_code}")
                    if approve_resp.status_code == 200:
                        status = "approved"
                
                # If approved, issue
                if status == "approved":
                    issue_resp = requests.post(f"{BASE_URL}/api/finance/invoices/{invoice_id}/issue", headers=headers)
                    print(f"Issue invoice: {issue_resp.status_code}")
                    if issue_resp.status_code == 200:
                        print("Invoice issued successfully")
                        return True
                
                if status in ["issued", "paid"]:
                    print(f"Invoice already {status}")
                    return True
        return False
    
    def test_4_record_payment_CRITICAL(self, finance_token):
        """CRITICAL TEST: Record payment for invoice"""
        headers = {"Authorization": f"Bearer {finance_token}"}
        
        # Get session invoice
        response = requests.get(f"{BASE_URL}/api/finance/invoices", headers=headers)
        if response.status_code != 200:
            pytest.fail("Cannot get invoices")
        
        invoices = response.json()
        session_invoice = next((inv for inv in invoices if inv.get("session_id") == SESSION_ID), None)
        
        if not session_invoice:
            pytest.skip("No invoice found for session")
        
        invoice_id = session_invoice.get("id")
        invoice_status = session_invoice.get("status")
        total_amount = session_invoice.get("total_amount", 0)
        
        print(f"Invoice ID: {invoice_id}")
        print(f"Invoice Status: {invoice_status}")
        print(f"Total Amount: RM {total_amount}")
        
        # Can only record payment for issued invoices
        if invoice_status not in ["issued", "paid"]:
            print(f"Invoice status is '{invoice_status}' - need to issue first")
            # Try to issue
            if invoice_status == "auto_draft":
                requests.post(f"{BASE_URL}/api/finance/invoices/{invoice_id}/approve", headers=headers)
            approve_check = requests.get(f"{BASE_URL}/api/finance/invoices/{invoice_id}", headers=headers)
            if approve_check.status_code == 200 and approve_check.json().get("status") == "approved":
                requests.post(f"{BASE_URL}/api/finance/invoices/{invoice_id}/issue", headers=headers)
        
        # Re-check status
        check_resp = requests.get(f"{BASE_URL}/api/finance/invoices/{invoice_id}", headers=headers)
        if check_resp.status_code == 200:
            invoice_status = check_resp.json().get("status")
            total_amount = check_resp.json().get("total_amount", 0)
        
        if invoice_status not in ["issued", "paid"]:
            print(f"Cannot record payment - invoice status: {invoice_status}")
            pytest.skip(f"Invoice not in issued status: {invoice_status}")
        
        # Record payment
        payment_data = {
            "invoice_id": invoice_id,
            "amount": total_amount,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "bank_transfer",
            "reference_number": f"TEST-PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "notes": "Test payment from automated testing"
        }
        
        print(f"Recording payment: {payment_data}")
        
        payment_resp = requests.post(
            f"{BASE_URL}/api/finance/payments",
            headers=headers,
            json=payment_data
        )
        
        print(f"Payment response: {payment_resp.status_code}")
        print(f"Payment response body: {payment_resp.text[:500]}")
        
        if payment_resp.status_code in [200, 201]:
            payment = payment_resp.json()
            print(f"✓ Payment recorded successfully!")
            print(f"Payment ID: {payment.get('id')}")
            
            # Verify invoice status changed to paid
            verify_resp = requests.get(f"{BASE_URL}/api/finance/invoices/{invoice_id}", headers=headers)
            if verify_resp.status_code == 200:
                new_status = verify_resp.json().get("status")
                print(f"Invoice status after payment: {new_status}")
                assert new_status == "paid", f"Expected 'paid', got '{new_status}'"
        else:
            print(f"✗ Payment recording FAILED: {payment_resp.status_code}")
            print(f"Error: {payment_resp.text}")
        
        assert payment_resp.status_code in [200, 201], f"Payment recording failed: {payment_resp.text}"


class TestPartC_ProfitLoss:
    """Part C: Profit/Loss Ledger Verification"""
    
    @pytest.fixture(scope="class")
    def finance_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["finance"])
        if response.status_code == 200:
            return response.json().get("access_token")
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_1_get_profit_loss(self, finance_token):
        """Get Profit/Loss ledger"""
        headers = {"Authorization": f"Bearer {finance_token}"}
        year = datetime.now().year
        response = requests.get(f"{BASE_URL}/api/finance/profit-loss?year={year}", headers=headers)
        print(f"P&L response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"P&L Data: {data.get('summary', {})}")
            print(f"Total Income: RM {data.get('summary', {}).get('total_income', 0)}")
            print(f"Total Expenses: RM {data.get('summary', {}).get('total_expenses', 0)}")
            print(f"Net Profit: RM {data.get('summary', {}).get('net_profit', 0)}")
        else:
            print(f"Error: {response.text[:500]}")
        assert response.status_code == 200
    
    def test_2_get_finance_dashboard(self, finance_token):
        """Get finance dashboard"""
        headers = {"Authorization": f"Bearer {finance_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=headers)
        print(f"Finance dashboard: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Dashboard data: {data}")
        assert response.status_code == 200


class TestPartD_PettyCash:
    """Part D: Petty Cash"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_1_get_petty_cash_settings(self, admin_token):
        """Get petty cash settings"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/petty-cash/settings", headers=headers)
        print(f"Petty cash settings: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Current balance: RM {data.get('current_balance', 0)}")
            print(f"Float amount: RM {data.get('float_amount', 0)}")
        else:
            print(f"Response: {response.text[:300]}")
        assert response.status_code == 200
    
    def test_2_setup_petty_cash_if_needed(self, admin_token):
        """Setup petty cash if not configured"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Check if already setup
        check_resp = requests.get(f"{BASE_URL}/api/finance/petty-cash/settings", headers=headers)
        if check_resp.status_code == 200 and check_resp.json():
            print("Petty cash already configured")
            return
        
        # Setup petty cash
        setup_data = {
            "float_amount": 1000.0,
            "custodian_id": None,
            "custodian_name": "Admin"
        }
        response = requests.post(f"{BASE_URL}/api/finance/petty-cash/setup", headers=headers, json=setup_data)
        print(f"Setup petty cash: {response.status_code}")
        if response.status_code in [200, 201]:
            print("Petty cash setup successful")
        else:
            print(f"Setup response: {response.text[:300]}")
    
    def test_3_add_petty_cash_expense(self, admin_token):
        """Add petty cash expense"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        expense_data = {
            "type": "expense",
            "amount": 50.0,
            "description": "Test expense - office supplies",
            "category": "office_supplies",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "receipt_url": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/finance/petty-cash/transaction",
            headers=headers,
            json=expense_data
        )
        print(f"Add petty cash expense: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"Transaction ID: {data.get('id')}")
            print(f"New balance: RM {data.get('new_balance', 'N/A')}")
        else:
            print(f"Error: {response.text[:500]}")
        assert response.status_code in [200, 201, 400]  # 400 if insufficient balance
    
    def test_4_get_petty_cash_transactions(self, admin_token):
        """Get petty cash transactions"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/petty-cash/transactions", headers=headers)
        print(f"Get transactions: {response.status_code}")
        if response.status_code == 200:
            transactions = response.json()
            print(f"Total transactions: {len(transactions)}")
        assert response.status_code == 200
    
    def test_5_get_petty_cash_summary(self, admin_token):
        """Get petty cash summary"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        year = datetime.now().year
        response = requests.get(f"{BASE_URL}/api/finance/petty-cash/summary?year={year}", headers=headers)
        print(f"Petty cash summary: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Summary: {data}")
        assert response.status_code == 200


class TestPartE_Payroll:
    """Part E: Payroll - Payslips and Pay Advice"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_1_get_hr_staff(self, admin_token):
        """Get HR staff list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/staff", headers=headers)
        print(f"HR staff: {response.status_code}")
        if response.status_code == 200:
            staff = response.json()
            print(f"Total staff: {len(staff)}")
            for s in staff[:5]:
                print(f"  - {s.get('full_name')} ({s.get('email')})")
        assert response.status_code == 200
    
    def test_2_get_payslips(self, admin_token):
        """Get payslips"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/payslips", headers=headers)
        print(f"Payslips: {response.status_code}")
        if response.status_code == 200:
            payslips = response.json()
            print(f"Total payslips: {len(payslips)}")
            
            # Check for specific users
            target_emails = ["malek@mddrc.com.my", "chandra.selvaguru@mddrc.com.my", "vijay@mddrc.com.my"]
            for email in target_emails:
                user_payslips = [p for p in payslips if p.get("staff_email") == email]
                print(f"  {email}: {len(user_payslips)} payslips")
        else:
            print(f"Error: {response.text[:300]}")
        assert response.status_code == 200
    
    def test_3_get_pay_advice(self, admin_token):
        """Get pay advice"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/pay-advice", headers=headers)
        print(f"Pay advice: {response.status_code}")
        if response.status_code == 200:
            advice_list = response.json()
            print(f"Total pay advice: {len(advice_list)}")
        else:
            print(f"Error: {response.text[:300]}")
        assert response.status_code == 200
    
    def test_4_get_payroll_periods(self, admin_token):
        """Get payroll periods"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/payroll-periods", headers=headers)
        print(f"Payroll periods: {response.status_code}")
        if response.status_code == 200:
            periods = response.json()
            print(f"Total periods: {len(periods)}")
        assert response.status_code == 200
    
    def test_5_check_user_payslips(self, admin_token):
        """Check payslips for specific users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get staff list first
        staff_resp = requests.get(f"{BASE_URL}/api/hr/staff", headers=headers)
        if staff_resp.status_code != 200:
            pytest.skip("Cannot get staff list")
        
        staff_list = staff_resp.json()
        target_emails = ["malek@mddrc.com.my", "chandra.selvaguru@mddrc.com.my", "vijay@mddrc.com.my"]
        
        for email in target_emails:
            staff = next((s for s in staff_list if s.get("email") == email), None)
            if staff:
                print(f"✓ {email} found in HR staff")
            else:
                print(f"✗ {email} NOT in HR staff")


class TestSessionDetails:
    """Additional session verification"""
    
    @pytest.fixture(scope="class")
    def coordinator_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["coordinator"])
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_get_session_details(self, coordinator_token):
        """Get full session details"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions/{SESSION_ID}", headers=headers)
        print(f"Session details: {response.status_code}")
        if response.status_code == 200:
            session = response.json()
            print(f"Session: {session.get('name')}")
            print(f"Company: {session.get('company_name')}")
            print(f"Status: {session.get('status')}")
            print(f"Completion: {session.get('completion_status')}")
            print(f"Invoice: {session.get('invoice_number')} - {session.get('invoice_status')}")
            print(f"Participants: {len(session.get('participant_ids', []))}")
        assert response.status_code == 200
    
    def test_get_results_summary(self, coordinator_token):
        """Get session results summary"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions/{SESSION_ID}/results-summary", headers=headers)
        print(f"Results summary: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Summary: {data}")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
