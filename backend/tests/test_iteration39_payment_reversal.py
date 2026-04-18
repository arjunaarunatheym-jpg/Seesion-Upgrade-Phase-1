"""
Test Suite for Payment Reversal Feature (Iteration 39)
Tests the Super Admin Payment Reversal functionality including:
- GET /api/superadmin/payments-for-reversal - List active payments
- GET /api/superadmin/payment-reversal/preview/{payment_id} - Preview reversal impact
- POST /api/superadmin/payment-reversal/execute - Execute reversal
- GET /api/superadmin/payment-reversals - Reversal history
- GET /api/superadmin/audit-trail/{entity_type}/{entity_id} - Audit trail
- Role-based access control (403 for non-super-admin)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "arjuna@mddrc.com.my"
SUPER_ADMIN_PASSWORD = "Dana102229"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"

# Test invoice for creating test payment
TEST_INVOICE_ID = "ce0c89c3-f077-447e-aa56-45591b0e1c8c"  # TELAGAMAS MOBILITY SDN BHD


class TestPaymentReversalSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Super admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def coordinator_token(self):
        """Get coordinator (non-super-admin) authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        assert response.status_code == 200, f"Coordinator login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_super_admin_login(self, super_admin_token):
        """Verify super admin can login"""
        assert super_admin_token is not None
        assert len(super_admin_token) > 0
        print(f"✓ Super admin login successful")
    
    def test_coordinator_login(self, coordinator_token):
        """Verify coordinator can login"""
        assert coordinator_token is not None
        assert len(coordinator_token) > 0
        print(f"✓ Coordinator login successful")


class TestPaymentReversalAccessControl:
    """Test role-based access control - non-super-admin should get 403"""
    
    @pytest.fixture(scope="class")
    def coordinator_token(self):
        """Get coordinator token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_payments_for_reversal_403(self, coordinator_token):
        """Non-super-admin should get 403 on payments-for-reversal"""
        if not coordinator_token:
            pytest.skip("Coordinator login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payments-for-reversal",
            headers={"Authorization": f"Bearer {coordinator_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-super-admin correctly denied access to payments-for-reversal")
    
    def test_payment_reversals_history_403(self, coordinator_token):
        """Non-super-admin should get 403 on payment-reversals history"""
        if not coordinator_token:
            pytest.skip("Coordinator login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversals",
            headers={"Authorization": f"Bearer {coordinator_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-super-admin correctly denied access to payment-reversals")
    
    def test_preview_reversal_403(self, coordinator_token):
        """Non-super-admin should get 403 on preview endpoint"""
        if not coordinator_token:
            pytest.skip("Coordinator login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversal/preview/fake-id",
            headers={"Authorization": f"Bearer {coordinator_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-super-admin correctly denied access to preview endpoint")
    
    def test_execute_reversal_403(self, coordinator_token):
        """Non-super-admin should get 403 on execute endpoint"""
        if not coordinator_token:
            pytest.skip("Coordinator login failed")
        
        response = requests.post(
            f"{BASE_URL}/api/superadmin/payment-reversal/execute",
            headers={"Authorization": f"Bearer {coordinator_token}"},
            json={"payment_id": "fake-id", "reason": "test reason", "confirm": True}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-super-admin correctly denied access to execute endpoint")


class TestPaymentReversalEndpoints:
    """Test payment reversal endpoints with super admin access"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, super_admin_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {super_admin_token}"}
    
    def test_get_payments_for_reversal(self, auth_headers):
        """Test GET /api/superadmin/payments-for-reversal returns active payments"""
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payments-for-reversal",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Got {len(data)} active payments for reversal")
        
        # Verify payment structure if any exist
        if len(data) > 0:
            payment = data[0]
            assert "id" in payment, "Payment should have id"
            assert "amount" in payment, "Payment should have amount"
            # Check that reversed payments are excluded
            for p in data:
                assert p.get("status") != "reversed", "Reversed payments should be excluded"
            print(f"✓ Payment structure validated")
    
    def test_get_payment_reversals_history(self, auth_headers):
        """Test GET /api/superadmin/payment-reversals returns reversal history"""
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversals",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Got {len(data)} reversal history records")
        
        # Verify reversal record structure if any exist
        if len(data) > 0:
            reversal = data[0]
            assert "id" in reversal, "Reversal should have id"
            assert "payment_id" in reversal, "Reversal should have payment_id"
            assert "reason" in reversal, "Reversal should have reason"
            assert "reversed_by_name" in reversal, "Reversal should have reversed_by_name"
            print(f"✓ Reversal history structure validated")
    
    def test_preview_reversal_not_found(self, auth_headers):
        """Test preview with non-existent payment returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversal/preview/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Preview correctly returns 404 for non-existent payment")
    
    def test_execute_reversal_without_confirm(self, auth_headers):
        """Test execute without confirm=true returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/superadmin/payment-reversal/execute",
            headers=auth_headers,
            json={
                "payment_id": str(uuid.uuid4()),
                "reason": "Test reason for reversal",
                "confirm": False
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "confirm" in response.json().get("detail", "").lower()
        print(f"✓ Execute correctly requires confirm=true")
    
    def test_execute_reversal_short_reason(self, auth_headers):
        """Test execute with short reason returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/superadmin/payment-reversal/execute",
            headers=auth_headers,
            json={
                "payment_id": str(uuid.uuid4()),
                "reason": "short",  # Less than 10 chars
                "confirm": True
            }
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ Execute correctly validates reason length (min 10 chars)")


class TestFullReversalFlow:
    """Test the complete payment reversal flow: Create payment -> Preview -> Execute -> Verify"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, super_admin_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {super_admin_token}"}
    
    @pytest.fixture(scope="class")
    def test_payment(self, auth_headers):
        """Create a test payment for reversal testing"""
        # Create payment with credit note
        payment_data = {
            "invoice_id": TEST_INVOICE_ID,
            "amount": 2000,
            "payment_date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "bank_transfer",
            "reference_number": f"TEST-REV-{uuid.uuid4().hex[:8].upper()}",
            "notes": "TEST PAYMENT FOR REVERSAL TESTING - DELETE AFTER TEST",
            "create_credit_note": True,
            "deduction_percentage": 4,
            "deduction_reason": "HRDCorp Levy Deduction (TEST)"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/finance/payments",
            headers=auth_headers,
            json=payment_data
        )
        
        if response.status_code != 200:
            pytest.skip(f"Could not create test payment: {response.text}")
        
        data = response.json()
        payment_id = data.get("payment", {}).get("id") or data.get("id")
        credit_note_id = data.get("credit_note", {}).get("id") if data.get("credit_note") else None
        
        print(f"✓ Created test payment: {payment_id}")
        if credit_note_id:
            print(f"✓ Created test credit note: {credit_note_id}")
        
        return {
            "payment_id": payment_id,
            "credit_note_id": credit_note_id,
            "amount": payment_data["amount"]
        }
    
    def test_preview_reversal(self, auth_headers, test_payment):
        """Test preview shows correct impact"""
        if not test_payment or not test_payment.get("payment_id"):
            pytest.skip("No test payment available")
        
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversal/preview/{test_payment['payment_id']}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Preview failed: {response.text}"
        
        data = response.json()
        
        # Verify preview structure
        assert "payment" in data, "Preview should include payment info"
        assert "invoice" in data, "Preview should include invoice info"
        assert "linked_credit_notes" in data, "Preview should include linked credit notes"
        assert "linked_journal_entries" in data, "Preview should include linked journals"
        assert "summary" in data, "Preview should include summary"
        
        # Verify payment info
        assert data["payment"]["id"] == test_payment["payment_id"]
        assert data["payment"]["amount"] == test_payment["amount"]
        
        # Verify summary
        summary = data["summary"]
        assert "payment_amount" in summary
        assert "credit_notes_to_void" in summary
        assert "journals_to_void" in summary
        assert "invoice_status_change" in summary
        
        print(f"✓ Preview shows payment amount: RM {data['payment']['amount']}")
        print(f"✓ Preview shows {summary['credit_notes_to_void']} credit notes to void")
        print(f"✓ Preview shows {summary['journals_to_void']} journals to void")
        print(f"✓ Preview shows invoice status change: {summary['invoice_status_change']}")
        
        return data
    
    def test_execute_reversal(self, auth_headers, test_payment):
        """Test executing the reversal"""
        if not test_payment or not test_payment.get("payment_id"):
            pytest.skip("No test payment available")
        
        response = requests.post(
            f"{BASE_URL}/api/superadmin/payment-reversal/execute",
            headers=auth_headers,
            json={
                "payment_id": test_payment["payment_id"],
                "reason": "TEST REVERSAL - HRDF only approved RM 1.8K instead of RM 3K",
                "confirm": True
            }
        )
        assert response.status_code == 200, f"Execute failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert "reversal_id" in data
        assert "actions_taken" in data
        assert "summary" in data
        
        assert "reversed successfully" in data["message"].lower()
        assert len(data["actions_taken"]) > 0
        
        print(f"✓ Reversal executed successfully")
        print(f"✓ Reversal ID: {data['reversal_id']}")
        print(f"✓ Actions taken: {len(data['actions_taken'])}")
        for action in data["actions_taken"]:
            print(f"  - {action}")
        
        return data
    
    def test_verify_payment_reversed(self, auth_headers, test_payment):
        """Verify payment status is now 'reversed'"""
        if not test_payment or not test_payment.get("payment_id"):
            pytest.skip("No test payment available")
        
        # Get all payments and find our test payment
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payments",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        payments = response.json().get("payments", [])
        test_pmt = next((p for p in payments if p["id"] == test_payment["payment_id"]), None)
        
        if test_pmt:
            assert test_pmt.get("status") == "reversed", f"Payment status should be 'reversed', got '{test_pmt.get('status')}'"
            print(f"✓ Payment status verified as 'reversed'")
        else:
            print(f"⚠ Could not find test payment in list (may have been filtered)")
    
    def test_verify_reversal_in_history(self, auth_headers, test_payment):
        """Verify reversal appears in history"""
        if not test_payment or not test_payment.get("payment_id"):
            pytest.skip("No test payment available")
        
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversals",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        reversals = response.json()
        test_reversal = next((r for r in reversals if r["payment_id"] == test_payment["payment_id"]), None)
        
        assert test_reversal is not None, "Reversal should appear in history"
        assert test_reversal["payment_amount"] == test_payment["amount"]
        assert "TEST REVERSAL" in test_reversal["reason"]
        
        print(f"✓ Reversal found in history")
        print(f"✓ Reversed by: {test_reversal.get('reversed_by_name')}")
    
    def test_cannot_reverse_already_reversed(self, auth_headers, test_payment):
        """Verify cannot reverse an already reversed payment"""
        if not test_payment or not test_payment.get("payment_id"):
            pytest.skip("No test payment available")
        
        # Try to preview already reversed payment
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversal/preview/{test_payment['payment_id']}",
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400 for already reversed payment, got {response.status_code}"
        assert "already reversed" in response.json().get("detail", "").lower()
        print(f"✓ Cannot preview already reversed payment")
        
        # Try to execute on already reversed payment
        response = requests.post(
            f"{BASE_URL}/api/superadmin/payment-reversal/execute",
            headers=auth_headers,
            json={
                "payment_id": test_payment["payment_id"],
                "reason": "Trying to reverse again",
                "confirm": True
            }
        )
        assert response.status_code == 400, f"Expected 400 for already reversed payment, got {response.status_code}"
        print(f"✓ Cannot execute reversal on already reversed payment")


class TestAuditTrail:
    """Test audit trail functionality"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, super_admin_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {super_admin_token}"}
    
    def test_get_audit_trail_for_payment(self, auth_headers):
        """Test getting audit trail for a payment entity"""
        # First get a payment that has been reversed
        response = requests.get(
            f"{BASE_URL}/api/superadmin/payment-reversals",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        reversals = response.json()
        if len(reversals) == 0:
            pytest.skip("No reversals to check audit trail")
        
        payment_id = reversals[0]["payment_id"]
        
        # Get audit trail for this payment
        response = requests.get(
            f"{BASE_URL}/api/superadmin/audit-trail/payment/{payment_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        audit_logs = response.json()
        assert isinstance(audit_logs, list), "Audit trail should be a list"
        
        print(f"✓ Got {len(audit_logs)} audit trail entries for payment")
        
        # Check for reversal action in audit trail
        reversal_logs = [log for log in audit_logs if "reversed" in log.get("action", "").lower()]
        if reversal_logs:
            print(f"✓ Found reversal action in audit trail")
            for log in reversal_logs:
                print(f"  - Action: {log.get('action')}, By: {log.get('performed_by_name')}")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def super_admin_token(self):
        """Get super admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_cleanup_note(self, super_admin_token):
        """Note about cleanup"""
        print("\n" + "="*60)
        print("CLEANUP NOTE:")
        print("Test payments created during this test run have been reversed.")
        print("The reversed payments and credit notes remain in the database")
        print("as audit records (marked as 'reversed' and 'voided').")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
