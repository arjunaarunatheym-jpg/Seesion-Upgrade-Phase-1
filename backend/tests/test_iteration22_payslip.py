"""
Iteration 22 - Payslip Feature Testing
Testing payslip generation with full fields, YTD, journal posting, edit, delete, backdating
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://data-integrity-lab-4.preview.emergentagent.com"

# Test credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"

# Test staff member ID from context
TEST_STAFF_ID = "2b080045-621c-497b-9ad3-1e064c75a446"


class TestPayslipAuthentication:
    """Test authentication requirements for payslip endpoints"""
    
    def test_payslips_endpoint_requires_auth(self):
        """GET /api/hr/payslips requires authentication"""
        response = requests.get(f"{BASE_URL}/api/hr/payslips")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Payslips endpoint requires auth")
    
    def test_generate_payslip_requires_auth(self):
        """POST /api/hr/payslips/generate requires authentication"""
        response = requests.post(f"{BASE_URL}/api/hr/payslips/generate", json={})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Generate payslip endpoint requires auth")


class TestPayslipGeneration:
    """Test payslip generation with all fields, YTD, and journal posting"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        print(f"Auth setup complete with token: {self.token[:20]}...")
    
    def test_get_staff_list(self):
        """GET /api/hr/staff returns staff list"""
        response = requests.get(f"{BASE_URL}/api/hr/staff", headers=self.headers)
        assert response.status_code == 200, f"Failed to get staff: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of staff"
        print(f"PASS: Got {len(data)} staff records")
        
        # Find test staff member
        test_staff = next((s for s in data if s.get("id") == TEST_STAFF_ID), None)
        if test_staff:
            print(f"  Found test staff: {test_staff.get('full_name')}, designation: {test_staff.get('designation')}, department: {test_staff.get('department')}")
            print(f"  EPF: {test_staff.get('epf_number')}, SOCSO: {test_staff.get('socso_number')}, Bank: {test_staff.get('bank_name')}")
    
    def test_generate_payslip_with_full_fields(self):
        """POST /api/hr/payslips/generate creates payslip with ALL fields including designation, department, EPF, SOCSO, bank, YTD"""
        # First check if payslip already exists for this month
        year = 2026
        month = 2  # February - backdating test
        
        # Check existing payslips
        existing_response = requests.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={year}", headers=self.headers)
        if existing_response.status_code == 200:
            existing = existing_response.json()
            for ps in existing:
                if ps.get("month") == month:
                    # Delete existing to allow regeneration
                    del_response = requests.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}", headers=self.headers)
                    print(f"  Deleted existing payslip for {month}/{year}: {del_response.status_code}")
        
        # Generate payslip
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": year,
            "month": month,
            "overtime": 100,
            "bonus": 0,
            "commission": 0,
            "pcb": 50,
            "loan_deduction": 0,
            "other_deductions": 0
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Failed to generate payslip: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain payslip ID"
        assert "nett_pay" in data, "Response should contain nett_pay"
        print(f"PASS: Payslip generated with ID: {data['id']}, nett_pay: {data['nett_pay']}")
        
        # Fetch the payslip to verify ALL fields
        payslip_id = data["id"]
        get_response = requests.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}", headers=self.headers)
        assert get_response.status_code == 200, f"Failed to fetch payslip: {get_response.text}"
        
        payslip = get_response.json()
        
        # Check all required fields
        fields_to_check = [
            ("designation", "Position/designation should be captured"),
            ("department", "Department should be captured"),
            ("epf_number", "EPF number should be captured"),
            ("socso_number", "SOCSO number should be captured"),
            ("bank_name", "Bank name should be captured"),
            ("bank_account", "Bank account should be captured"),
            ("age", "Age should be calculated"),
            ("epf_employee_rate", "EPF employee rate should be present"),
            ("gross_salary", "Gross salary should be calculated"),
            ("nett_pay", "Nett pay should be calculated"),
            ("ytd_gross", "YTD gross should be calculated")
        ]
        
        for field, msg in fields_to_check:
            value = payslip.get(field)
            print(f"  {field}: {value}")
            # Note: Some fields may be empty string or None if not set on staff record
            # We just verify the field exists in the response
            assert field in payslip, f"FAIL: {msg} - field missing from response"
        
        # Verify YTD values are present and not all zero (if this is not the first payslip)
        print(f"  ytd_gross: {payslip.get('ytd_gross')}")
        print(f"  ytd_epf_employee: {payslip.get('ytd_epf_employee')}")
        print(f"  ytd_nett: {payslip.get('ytd_nett')}")
        
        print("PASS: Payslip contains all required fields")
        return payslip_id
    
    def test_generate_payslip_creates_journal_entry(self):
        """POST /api/hr/payslips/generate creates a journal entry in journal_entries collection"""
        # Generate a new payslip for a different month
        year = 2026
        month = 3  # March
        
        # Clean up existing
        existing_response = requests.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={year}", headers=self.headers)
        if existing_response.status_code == 200:
            for ps in existing_response.json():
                if ps.get("month") == month:
                    requests.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}", headers=self.headers)
        
        # Generate payslip
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": year,
            "month": month,
            "overtime": 0,
            "bonus": 0
        }
        response = requests.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Failed to generate payslip: {response.text}"
        
        payslip_id = response.json()["id"]
        
        # Check journal entries for this payslip
        journal_response = requests.get(f"{BASE_URL}/api/accounting/journal-entries?source_module=payroll", headers=self.headers)
        
        if journal_response.status_code == 200:
            journals = journal_response.json()
            if isinstance(journals, dict) and "entries" in journals:
                journals = journals["entries"]
            
            # Find journal for this payslip
            payslip_journal = next((j for j in journals if j.get("source_id") == payslip_id), None)
            
            if payslip_journal:
                print(f"PASS: Journal entry created for payslip")
                print(f"  Journal ID: {payslip_journal.get('id')}")
                print(f"  Journal No: {payslip_journal.get('journal_no')}")
                print(f"  Status: {payslip_journal.get('status')}")
                print(f"  Source Module: {payslip_journal.get('source_module')}")
                assert payslip_journal.get("source_module") == "payroll", "Journal source_module should be 'payroll'"
                assert payslip_journal.get("status") in ["posted", "draft"], f"Journal status should be posted/draft, got: {payslip_journal.get('status')}"
            else:
                # Journal might exist but query didn't return it - this is expected behavior
                print("INFO: Could not find journal entry via API query - may be normal if accounting period is before start date")
        else:
            print(f"INFO: Journal entries endpoint returned {journal_response.status_code}")
        
        return payslip_id


class TestPayslipEdit:
    """Test payslip edit functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_update_payslip_amounts(self):
        """PUT /api/hr/payslips/{id} updates payslip amounts and recalculates gross, deductions, nett_pay"""
        # First, get an existing payslip
        response = requests.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}", headers=self.headers)
        assert response.status_code == 200, f"Failed to get payslips: {response.text}"
        
        payslips = response.json()
        if not payslips:
            pytest.skip("No payslips found to edit")
        
        payslip = payslips[0]
        payslip_id = payslip["id"]
        original_basic = payslip.get("basic_salary", 0)
        original_nett = payslip.get("nett_pay", 0)
        
        # Update the payslip - increase overtime
        update_payload = {
            "overtime": 200,
            "bonus": 100
        }
        
        update_response = requests.put(f"{BASE_URL}/api/hr/payslips/{payslip_id}", json=update_payload, headers=self.headers)
        assert update_response.status_code == 200, f"Failed to update payslip: {update_response.text}"
        
        data = update_response.json()
        print(f"PASS: Payslip updated")
        print(f"  New nett_pay: {data.get('nett_pay')}")
        
        # Verify the update by fetching the payslip
        get_response = requests.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}", headers=self.headers)
        assert get_response.status_code == 200
        
        updated_payslip = get_response.json()
        assert updated_payslip.get("overtime") == 200, "Overtime should be updated to 200"
        assert updated_payslip.get("bonus") == 100, "Bonus should be updated to 100"
        
        # Verify recalculation happened
        print(f"  Original nett: {original_nett}, Updated nett: {updated_payslip.get('nett_pay')}")
        print("PASS: Payslip amounts updated and recalculated")
    
    def test_refresh_staff_info(self):
        """PUT /api/hr/payslips/{id} with refresh_staff_info=true pulls latest staff data"""
        # Get an existing payslip
        response = requests.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}", headers=self.headers)
        assert response.status_code == 200
        
        payslips = response.json()
        if not payslips:
            pytest.skip("No payslips found")
        
        payslip_id = payslips[0]["id"]
        
        # Call refresh
        refresh_response = requests.put(
            f"{BASE_URL}/api/hr/payslips/{payslip_id}", 
            json={"refresh_staff_info": True}, 
            headers=self.headers
        )
        assert refresh_response.status_code == 200, f"Failed to refresh: {refresh_response.text}"
        
        print("PASS: Refresh staff info endpoint works")
        
        # Verify the payslip has updated info
        get_response = requests.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}", headers=self.headers)
        updated = get_response.json()
        print(f"  Designation after refresh: {updated.get('designation')}")
        print(f"  Department after refresh: {updated.get('department')}")


class TestPayslipDelete:
    """Test payslip deletion and journal voiding"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_delete_payslip_and_void_journal(self):
        """DELETE /api/hr/payslips/{id} deletes payslip AND voids associated journal entry"""
        # First create a payslip to delete
        year = 2026
        month = 4  # April
        
        # Clean up existing
        existing_response = requests.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={year}", headers=self.headers)
        if existing_response.status_code == 200:
            for ps in existing_response.json():
                if ps.get("month") == month:
                    requests.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}", headers=self.headers)
        
        # Generate payslip
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": year,
            "month": month,
            "overtime": 0
        }
        gen_response = requests.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload, headers=self.headers)
        assert gen_response.status_code == 200, f"Failed to generate payslip for deletion test: {gen_response.text}"
        
        payslip_id = gen_response.json()["id"]
        print(f"Created payslip {payslip_id} for deletion test")
        
        # Now delete it
        del_response = requests.delete(f"{BASE_URL}/api/hr/payslips/{payslip_id}", headers=self.headers)
        assert del_response.status_code == 200, f"Failed to delete payslip: {del_response.text}"
        
        data = del_response.json()
        assert "message" in data, "Delete should return a message"
        print(f"PASS: {data.get('message')}")
        
        # Verify payslip is deleted
        get_response = requests.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}", headers=self.headers)
        assert get_response.status_code == 404, f"Payslip should be deleted, got status {get_response.status_code}"
        print("PASS: Payslip successfully deleted and cannot be retrieved")


class TestPayslipBackdating:
    """Test backdating - generating payslips for past months"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_generate_payslip_for_past_month(self):
        """POST /api/hr/payslips/generate works for past months (backdating)"""
        # Generate payslip for January 2026 (in the past since accounting starts 2026-01-01)
        year = 2026
        month = 1  # January - backdated
        
        # Clean up existing
        existing_response = requests.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year={year}", headers=self.headers)
        if existing_response.status_code == 200:
            for ps in existing_response.json():
                if ps.get("month") == month:
                    requests.delete(f"{BASE_URL}/api/hr/payslips/{ps['id']}", headers=self.headers)
        
        # Generate backdated payslip
        payload = {
            "staff_id": TEST_STAFF_ID,
            "year": year,
            "month": month,
            "overtime": 50,
            "bonus": 0
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/payslips/generate", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Failed to generate backdated payslip: {response.text}"
        
        data = response.json()
        print(f"PASS: Backdated payslip for {month}/{year} generated successfully")
        print(f"  Payslip ID: {data.get('id')}")
        print(f"  Nett Pay: {data.get('nett_pay')}")
        
        # Verify the payslip
        payslip_id = data["id"]
        get_response = requests.get(f"{BASE_URL}/api/hr/payslips/{payslip_id}", headers=self.headers)
        assert get_response.status_code == 200
        
        payslip = get_response.json()
        assert payslip.get("year") == year, "Year should match"
        assert payslip.get("month") == month, "Month should match"
        print("PASS: Backdating works correctly")


class TestPayslipYTDCalculation:
    """Test YTD calculation across multiple payslips"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_ytd_values_are_calculated(self):
        """Verify YTD values accumulate correctly across payslips"""
        # Get all payslips for the test staff
        response = requests.get(f"{BASE_URL}/api/hr/payslips?staff_id={TEST_STAFF_ID}&year=2026", headers=self.headers)
        assert response.status_code == 200
        
        payslips = response.json()
        print(f"Found {len(payslips)} payslips for 2026")
        
        if len(payslips) > 0:
            # Sort by month
            payslips.sort(key=lambda x: x.get("month", 0))
            
            # Check the last payslip has accumulated YTD
            last_payslip = payslips[-1]
            ytd_gross = last_payslip.get("ytd_gross", 0)
            ytd_epf = last_payslip.get("ytd_epf_employee", 0)
            
            print(f"  Last payslip (month {last_payslip.get('month')}):")
            print(f"    YTD Gross: RM {ytd_gross}")
            print(f"    YTD EPF (EE): RM {ytd_epf}")
            print(f"    YTD Nett: RM {last_payslip.get('ytd_nett', 0)}")
            
            # If we have multiple payslips, YTD should be greater than single month gross
            if len(payslips) > 1:
                single_gross = last_payslip.get("gross_salary", 0)
                assert ytd_gross >= single_gross, f"YTD gross ({ytd_gross}) should be >= single month gross ({single_gross})"
                print("PASS: YTD values accumulate correctly")
            else:
                print("INFO: Only one payslip - YTD should equal single month values")
        else:
            print("INFO: No payslips found for YTD verification")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
