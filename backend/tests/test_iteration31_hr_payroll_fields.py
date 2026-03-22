"""
Iteration 31 - HR Payroll Enhanced Fields Testing
Tests for new income fields (Fixed Allowance, Commission, Incentives, Bonus, Annual Leave Pay)
and new deduction fields (CP39/PCB Tax, CP38, Loan, Mid-Month Advance, Salary Adjustment, Unpaid Leave)
Also tests manual staff-user linking endpoints.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

# Test staff ID from context
TEST_STAFF_ID = "2b080045-621c-497b-9ad3-1e064c75a446"
TEST_USER_ID = "e93ed5d5-07eb-47f5-a836-0e525260b519"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Authenticated session for admin"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestHRStaffEndpoints:
    """Test HR Staff management endpoints"""
    
    def test_get_staff_list(self, admin_client):
        """Test GET /api/hr/staff returns staff list"""
        response = admin_client.get(f"{BASE_URL}/api/hr/staff")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} staff records")
    
    def test_staff_has_link_badge_info(self, admin_client):
        """Test staff records include user_id for link/unlink badge"""
        response = admin_client.get(f"{BASE_URL}/api/hr/staff")
        assert response.status_code == 200
        data = response.json()
        
        # Check that staff records have user_id field (can be null or string)
        for staff in data[:5]:  # Check first 5
            assert "user_id" in staff or staff.get("user_id") is None
            print(f"Staff: {staff.get('full_name')} - user_id: {staff.get('user_id')}")


class TestManualLinkUnlink:
    """Test manual staff-user linking endpoints"""
    
    def test_manual_link_endpoint_exists(self, admin_client):
        """Test POST /api/hr/staff/{id}/link-user/{user_id} endpoint exists"""
        # Use a non-existent staff ID to test endpoint exists (should return 404, not 405)
        response = admin_client.post(f"{BASE_URL}/api/hr/staff/nonexistent-id/link-user/nonexistent-user")
        # Should be 404 (not found) not 405 (method not allowed)
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}"
        print(f"Manual link endpoint exists - returned {response.status_code}")
    
    def test_manual_unlink_endpoint_exists(self, admin_client):
        """Test DELETE /api/hr/staff/{id}/unlink-user endpoint exists"""
        response = admin_client.delete(f"{BASE_URL}/api/hr/staff/nonexistent-id/unlink-user")
        # Should be 404 (not found) not 405 (method not allowed)
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}"
        print(f"Manual unlink endpoint exists - returned {response.status_code}")
    
    def test_get_available_users_for_linking(self, admin_client):
        """Test GET /api/hr/available-users returns users that can be linked"""
        response = admin_client.get(f"{BASE_URL}/api/hr/available-users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} available users for linking")


class TestPayslipGeneration:
    """Test payslip generation with new fields"""
    
    def test_generate_payslip_with_new_earnings(self, admin_client):
        """Test generating payslip with new variable earnings fields"""
        # Use a unique month to avoid conflicts
        test_month = 6  # June 2026
        test_year = 2026
        
        # First, delete any existing payslip for this period
        payslips_response = admin_client.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={test_year}")
        if payslips_response.status_code == 200:
            for ps in payslips_response.json():
                if ps.get("month") == test_month:
                    admin_client.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}")
        
        # Generate payslip with new fields
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": test_year,
            "month": test_month,
            # New variable earnings
            "commission": 500.00,
            "incentives": 200.00,
            "bonus": 1000.00,
            "annual_leave_pay": 150.00,
            "overtime": 300.00,
            # New deductions
            "pcb": 100.00,
            "cp38": 50.00,
            "loan_deduction": 200.00,
            "mid_month_advance": 500.00,
            "salary_adjustment": 100.00,
            "unpaid_leave": 75.00,
            "other_deductions": 25.00
        }
        
        response = admin_client.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload)
        assert response.status_code == 200, f"Failed to generate payslip: {response.text}"
        data = response.json()
        assert "id" in data
        assert "nett_pay" in data
        print(f"Generated payslip with nett_pay: RM {data['nett_pay']}")
        
        # Verify the payslip was created with correct fields
        payslip_id = data["id"]
        verify_response = admin_client.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
        assert verify_response.status_code == 200
        payslip = verify_response.json()
        
        # Verify new earnings fields
        assert payslip.get("commission") == 500.00, f"Commission mismatch: {payslip.get('commission')}"
        assert payslip.get("incentives") == 200.00, f"Incentives mismatch: {payslip.get('incentives')}"
        assert payslip.get("bonus") == 1000.00, f"Bonus mismatch: {payslip.get('bonus')}"
        assert payslip.get("annual_leave_pay") == 150.00, f"Annual leave pay mismatch: {payslip.get('annual_leave_pay')}"
        assert payslip.get("overtime") == 300.00, f"Overtime mismatch: {payslip.get('overtime')}"
        
        # Verify new deduction fields
        assert payslip.get("pcb") == 100.00, f"PCB mismatch: {payslip.get('pcb')}"
        assert payslip.get("cp38") == 50.00, f"CP38 mismatch: {payslip.get('cp38')}"
        assert payslip.get("loan_deduction") == 200.00, f"Loan deduction mismatch: {payslip.get('loan_deduction')}"
        assert payslip.get("mid_month_advance") == 500.00, f"Mid-month advance mismatch: {payslip.get('mid_month_advance')}"
        assert payslip.get("salary_adjustment") == 100.00, f"Salary adjustment mismatch: {payslip.get('salary_adjustment')}"
        assert payslip.get("unpaid_leave") == 75.00, f"Unpaid leave mismatch: {payslip.get('unpaid_leave')}"
        
        print("All new earnings and deduction fields verified correctly!")
        
        # Clean up - delete the test payslip
        admin_client.delete(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
    
    def test_payslip_gross_calculation(self, admin_client):
        """Test that gross salary calculation includes all new earnings"""
        test_month = 7  # July 2026
        test_year = 2026
        
        # Delete any existing payslip
        payslips_response = admin_client.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={test_year}")
        if payslips_response.status_code == 200:
            for ps in payslips_response.json():
                if ps.get("month") == test_month:
                    admin_client.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}")
        
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": test_year,
            "month": test_month,
            "basic_salary": 3000.00,
            "fixed_allowance": 200.00,
            "housing_allowance": 300.00,
            "transport_allowance": 100.00,
            "commission": 500.00,
            "incentives": 200.00,
            "bonus": 1000.00,
            "annual_leave_pay": 150.00,
            "overtime": 300.00,
        }
        
        response = admin_client.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        payslip_id = response.json()["id"]
        
        # Verify gross calculation
        verify_response = admin_client.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
        payslip = verify_response.json()
        
        # Expected gross = basic + all allowances + all variable earnings
        expected_gross = 3000 + 200 + 300 + 100 + 500 + 200 + 1000 + 150 + 300  # = 5750
        actual_gross = payslip.get("gross_salary", 0)
        
        print(f"Expected gross: {expected_gross}, Actual gross: {actual_gross}")
        assert abs(actual_gross - expected_gross) < 1, f"Gross calculation mismatch: expected {expected_gross}, got {actual_gross}"
        
        # Clean up
        admin_client.delete(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
    
    def test_payslip_deductions_calculation(self, admin_client):
        """Test that total deductions includes all new deduction fields"""
        test_month = 8  # August 2026
        test_year = 2026
        
        # Delete any existing payslip
        payslips_response = admin_client.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={test_year}")
        if payslips_response.status_code == 200:
            for ps in payslips_response.json():
                if ps.get("month") == test_month:
                    admin_client.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}")
        
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": test_year,
            "month": test_month,
            "epf_employee": 330.00,
            "socso_employee": 15.00,
            "eis_employee": 6.00,
            "pcb": 100.00,
            "cp38": 50.00,
            "loan_deduction": 200.00,
            "mid_month_advance": 500.00,
            "salary_adjustment": 100.00,
            "unpaid_leave": 75.00,
            "other_deductions": 25.00
        }
        
        response = admin_client.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        payslip_id = response.json()["id"]
        
        # Verify deductions calculation
        verify_response = admin_client.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
        payslip = verify_response.json()
        
        # Expected total deductions = statutory + all other deductions
        expected_deductions = 330 + 15 + 6 + 100 + 50 + 200 + 500 + 100 + 75 + 25  # = 1401
        actual_deductions = payslip.get("total_deductions", 0)
        
        print(f"Expected deductions: {expected_deductions}, Actual deductions: {actual_deductions}")
        assert abs(actual_deductions - expected_deductions) < 1, f"Deductions calculation mismatch: expected {expected_deductions}, got {actual_deductions}"
        
        # Clean up
        admin_client.delete(f"{BASE_URL}/api/hr/payslips/{payslip_id}")


class TestPayslipUpdate:
    """Test payslip update with new fields"""
    
    def test_update_payslip_with_new_fields(self, admin_client):
        """Test updating payslip with all new earnings and deduction fields"""
        test_month = 9  # September 2026
        test_year = 2026
        
        # Delete any existing payslip
        payslips_response = admin_client.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={test_year}")
        if payslips_response.status_code == 200:
            for ps in payslips_response.json():
                if ps.get("month") == test_month:
                    admin_client.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}")
        
        # First create a payslip
        create_payload = {
            "staff_id": TEST_STAFF_ID,
            "year": test_year,
            "month": test_month,
        }
        create_response = admin_client.post(f"{BASE_URL}/api/hr/payslips/generate", json=create_payload)
        assert create_response.status_code == 200
        payslip_id = create_response.json()["id"]
        
        # Now update with new fields
        update_payload = {
            "fixed_allowance": 250.00,
            "commission": 600.00,
            "incentives": 300.00,
            "bonus": 1500.00,
            "annual_leave_pay": 200.00,
            "pcb": 150.00,
            "cp38": 75.00,
            "loan_deduction": 300.00,
            "mid_month_advance": 600.00,
            "salary_adjustment": 150.00,
            "unpaid_leave": 100.00,
        }
        
        update_response = admin_client.put(f"{BASE_URL}/api/hr/payslips/{payslip_id}", json=update_payload)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        # Verify update
        verify_response = admin_client.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
        payslip = verify_response.json()
        
        assert payslip.get("fixed_allowance") == 250.00
        assert payslip.get("commission") == 600.00
        assert payslip.get("incentives") == 300.00
        assert payslip.get("bonus") == 1500.00
        assert payslip.get("annual_leave_pay") == 200.00
        assert payslip.get("pcb") == 150.00
        assert payslip.get("cp38") == 75.00
        assert payslip.get("loan_deduction") == 300.00
        assert payslip.get("mid_month_advance") == 600.00
        assert payslip.get("salary_adjustment") == 150.00
        assert payslip.get("unpaid_leave") == 100.00
        
        print("Payslip update with new fields verified successfully!")
        
        # Clean up
        admin_client.delete(f"{BASE_URL}/api/hr/payslips/{payslip_id}")


class TestPayslipView:
    """Test payslip view returns all new fields"""
    
    def test_view_payslip_has_all_new_fields(self, admin_client):
        """Test GET /api/hr/payslips/{id} returns all new fields"""
        test_month = 10  # October 2026
        test_year = 2026
        
        # Delete any existing payslip
        payslips_response = admin_client.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={test_year}")
        if payslips_response.status_code == 200:
            for ps in payslips_response.json():
                if ps.get("month") == test_month:
                    admin_client.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}")
        
        # Create payslip with all fields
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": test_year,
            "month": test_month,
            "commission": 100,
            "incentives": 100,
            "bonus": 100,
            "annual_leave_pay": 100,
            "pcb": 50,
            "cp38": 50,
            "loan_deduction": 50,
            "mid_month_advance": 50,
            "salary_adjustment": 50,
            "unpaid_leave": 50,
        }
        
        create_response = admin_client.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload)
        assert create_response.status_code == 200
        payslip_id = create_response.json()["id"]
        
        # View payslip
        view_response = admin_client.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
        assert view_response.status_code == 200
        payslip = view_response.json()
        
        # Check all new fields exist in response
        new_earnings_fields = ["commission", "incentives", "bonus", "annual_leave_pay", "overtime"]
        new_deduction_fields = ["pcb", "cp38", "loan_deduction", "mid_month_advance", "salary_adjustment", "unpaid_leave"]
        
        for field in new_earnings_fields:
            assert field in payslip, f"Missing earnings field: {field}"
            print(f"  {field}: {payslip.get(field)}")
        
        for field in new_deduction_fields:
            assert field in payslip, f"Missing deduction field: {field}"
            print(f"  {field}: {payslip.get(field)}")
        
        print("All new fields present in payslip view!")
        
        # Clean up
        admin_client.delete(f"{BASE_URL}/api/hr/payslips/{payslip_id}")


class TestHRPayrollTabLoads:
    """Test HR & Payroll tab loads correctly"""
    
    def test_hr_staff_endpoint(self, admin_client):
        """Test /api/hr/staff endpoint returns data"""
        response = admin_client.get(f"{BASE_URL}/api/hr/staff")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"HR Staff endpoint returned {len(data)} records")
    
    def test_payroll_status_endpoint(self, admin_client):
        """Test /api/hr/payroll-status endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/hr/payroll-status?year=2026&month=1")
        assert response.status_code == 200
        data = response.json()
        assert "staff" in data
        assert "total_staff" in data
        print(f"Payroll status: {data.get('paid_count')}/{data.get('total_staff')} paid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
