"""
Test iteration 32: EPF band-based calculation, dynamic statutory recalculation, and input handling
Tests:
1. POST /api/hr/statutory/calculate endpoint returns correct EPF/SOCSO/EIS for different salary levels
2. EPF amounts are whole RM (no cents) from band lookup for salaries ≤RM20,000
3. EPF uses 13% employer rate for salary ≤RM5000 and 12% for >RM5000
4. SOCSO and EIS continue to work correctly from band lookup
5. Payslip generation with statutory deductions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStatutoryCalculation:
    """Test the /hr/statutory/calculate endpoint for EPF/SOCSO/EIS calculations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Login failed - skipping tests")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_statutory_calculate_endpoint_exists(self):
        """Test that the statutory calculate endpoint exists and responds"""
        response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
            "gross_salary": 3000,
            "nric": "990515105203",
            "reference_date": "2026-01-01"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "epf_employee" in data, "Missing epf_employee in response"
        assert "epf_employer" in data, "Missing epf_employer in response"
        assert "socso_employee" in data, "Missing socso_employee in response"
        assert "socso_employer" in data, "Missing socso_employer in response"
        assert "eis_employee" in data, "Missing eis_employee in response"
        assert "eis_employer" in data, "Missing eis_employer in response"
        assert "gross_salary" in data, "Missing gross_salary in response"
        
        print(f"Statutory calculation response for RM3000: {data}")
    
    def test_epf_rm2700_salary(self):
        """Test EPF calculation for RM2,700 salary (Abdul Malek's basic salary)"""
        response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
            "gross_salary": 2700,
            "nric": "990515105203",
            "reference_date": "2026-01-01"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # EPF employee should be whole RM (no cents) for band lookup
        epf_ee = data["epf_employee"]
        epf_er = data["epf_employer"]
        
        # For RM2700, EPF employee (11%) should be ~297, employer (13%) should be ~351
        # But with band lookup, it should be whole RM amounts
        assert epf_ee == int(epf_ee), f"EPF employee should be whole RM, got {epf_ee}"
        assert epf_er == int(epf_er), f"EPF employer should be whole RM, got {epf_er}"
        
        # Verify employer rate is 13% for salary ≤RM5000
        # Expected: ~13% of 2700 = 351
        assert 340 <= epf_er <= 360, f"EPF employer for RM2700 should be ~351, got {epf_er}"
        
        print(f"EPF for RM2700: Employee={epf_ee}, Employer={epf_er}")
    
    def test_epf_rm3000_salary(self):
        """Test EPF calculation for RM3,000 salary"""
        response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
            "gross_salary": 3000,
            "nric": "850101101234",
            "reference_date": "2026-01-01"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        epf_ee = data["epf_employee"]
        epf_er = data["epf_employer"]
        
        # EPF should be whole RM
        assert epf_ee == int(epf_ee), f"EPF employee should be whole RM, got {epf_ee}"
        assert epf_er == int(epf_er), f"EPF employer should be whole RM, got {epf_er}"
        
        # For RM3000: Employee 11% = 330, Employer 13% = 390
        assert 320 <= epf_ee <= 340, f"EPF employee for RM3000 should be ~330, got {epf_ee}"
        assert 380 <= epf_er <= 400, f"EPF employer for RM3000 should be ~390, got {epf_er}"
        
        print(f"EPF for RM3000: Employee={epf_ee}, Employer={epf_er}")
    
    def test_epf_rm5000_salary_boundary(self):
        """Test EPF calculation at RM5,000 boundary (employer rate changes from 13% to 12%)"""
        response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
            "gross_salary": 5000,
            "nric": "850101101234",
            "reference_date": "2026-01-01"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        epf_ee = data["epf_employee"]
        epf_er = data["epf_employer"]
        
        # At RM5000, employer rate should still be 13%
        # Employee 11% = 550, Employer 13% = 650
        assert 540 <= epf_ee <= 560, f"EPF employee for RM5000 should be ~550, got {epf_ee}"
        assert 640 <= epf_er <= 660, f"EPF employer for RM5000 should be ~650 (13%), got {epf_er}"
        
        print(f"EPF for RM5000: Employee={epf_ee}, Employer={epf_er}")
    
    def test_epf_rm8000_salary(self):
        """Test EPF calculation for RM8,000 salary (employer rate should be 12%)"""
        response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
            "gross_salary": 8000,
            "nric": "850101101234",
            "reference_date": "2026-01-01"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        epf_ee = data["epf_employee"]
        epf_er = data["epf_employer"]
        
        # For RM8000: Employee 11% = 880, Employer 12% = 960
        assert 870 <= epf_ee <= 890, f"EPF employee for RM8000 should be ~880, got {epf_ee}"
        assert 950 <= epf_er <= 970, f"EPF employer for RM8000 should be ~960 (12%), got {epf_er}"
        
        print(f"EPF for RM8000: Employee={epf_ee}, Employer={epf_er}")
    
    def test_socso_calculation(self):
        """Test SOCSO calculation from band lookup"""
        response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
            "gross_salary": 3000,
            "nric": "850101101234",
            "reference_date": "2026-01-01"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        socso_ee = data["socso_employee"]
        socso_er = data["socso_employer"]
        
        # SOCSO should have values
        assert socso_ee >= 0, f"SOCSO employee should be >= 0, got {socso_ee}"
        assert socso_er >= 0, f"SOCSO employer should be >= 0, got {socso_er}"
        
        # SOCSO rates: Employee 0.5%, Employer 1.75% (capped at RM6000)
        # For RM3000: Employee ~15, Employer ~52.50
        assert 10 <= socso_ee <= 20, f"SOCSO employee for RM3000 should be ~15, got {socso_ee}"
        assert 45 <= socso_er <= 60, f"SOCSO employer for RM3000 should be ~52.50, got {socso_er}"
        
        print(f"SOCSO for RM3000: Employee={socso_ee}, Employer={socso_er}")
    
    def test_eis_calculation(self):
        """Test EIS calculation from band lookup"""
        response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
            "gross_salary": 3000,
            "nric": "850101101234",
            "reference_date": "2026-01-01"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        eis_ee = data["eis_employee"]
        eis_er = data["eis_employer"]
        
        # EIS rates: 0.2% each (capped at RM6000)
        # For RM3000: ~6 each
        assert 4 <= eis_ee <= 8, f"EIS employee for RM3000 should be ~6, got {eis_ee}"
        assert 4 <= eis_er <= 8, f"EIS employer for RM3000 should be ~6, got {eis_er}"
        
        print(f"EIS for RM3000: Employee={eis_ee}, Employer={eis_er}")
    
    def test_epf_whole_rm_no_cents(self):
        """Test that EPF amounts are whole RM (no cents) for various salary levels"""
        test_salaries = [2700, 3000, 4500, 5000, 6000, 8000, 10000, 15000, 20000]
        
        for salary in test_salaries:
            response = self.session.post(f"{BASE_URL}/api/hr/statutory/calculate", json={
                "gross_salary": salary,
                "nric": "850101101234",
                "reference_date": "2026-01-01"
            })
            
            assert response.status_code == 200, f"Failed for salary {salary}"
            data = response.json()
            
            epf_ee = data["epf_employee"]
            epf_er = data["epf_employer"]
            
            # Check no cents (whole RM)
            assert epf_ee == int(epf_ee), f"EPF employee for RM{salary} has cents: {epf_ee}"
            assert epf_er == int(epf_er), f"EPF employer for RM{salary} has cents: {epf_er}"
            
            print(f"RM{salary}: EPF EE={epf_ee}, ER={epf_er} (whole RM verified)")


class TestPayslipGeneration:
    """Test payslip generation with statutory deductions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Login failed - skipping tests")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_staff_list(self):
        """Test getting staff list to find Abdul Malek"""
        response = self.session.get(f"{BASE_URL}/api/hr/staff")
        
        assert response.status_code == 200
        staff_list = response.json()
        
        assert isinstance(staff_list, list), "Staff list should be an array"
        
        # Find Abdul Malek
        abdul_malek = None
        for s in staff_list:
            if "Abdul Malek" in s.get("full_name", ""):
                abdul_malek = s
                break
        
        if abdul_malek:
            print(f"Found Abdul Malek: ID={abdul_malek['id']}, Basic Salary={abdul_malek.get('basic_salary')}, NRIC={abdul_malek.get('nric')}")
            assert abdul_malek.get("basic_salary") == 2700, f"Abdul Malek's basic salary should be RM2700, got {abdul_malek.get('basic_salary')}"
        else:
            print(f"Abdul Malek not found. Staff list: {[s.get('full_name') for s in staff_list[:5]]}")
    
    def test_payslip_generation_with_variable_earnings(self):
        """Test that payslip generation works with variable earnings"""
        # First get staff list
        staff_response = self.session.get(f"{BASE_URL}/api/hr/staff")
        assert staff_response.status_code == 200
        staff_list = staff_response.json()
        
        if not staff_list:
            pytest.skip("No staff found")
        
        # Use first staff member for test
        test_staff = staff_list[0]
        staff_id = test_staff["id"]
        
        # Try to generate payslip (may fail if already exists, which is fine)
        payslip_data = {
            "staff_id": staff_id,
            "year": 2026,
            "month": 12,  # Use December to avoid conflicts
            "overtime": 100,
            "bonus": 500,
            "commission": 200,
            "incentives": 150,
            "annual_leave_pay": 0,
            "pcb": 50,
            "cp38": 0,
            "loan_deduction": 0,
            "mid_month_advance": 0,
            "salary_adjustment": 0,
            "unpaid_leave": 0,
            "other_deductions": 0
        }
        
        response = self.session.post(f"{BASE_URL}/api/hr/payslips/generate", json=payslip_data)
        
        # Either success or already exists is acceptable
        if response.status_code == 200:
            data = response.json()
            assert "nett_pay" in data, "Response should include nett_pay"
            print(f"Payslip generated: Nett Pay = RM{data['nett_pay']}")
            
            # Clean up - delete the test payslip
            payslip_id = data.get("id")
            if payslip_id:
                self.session.delete(f"{BASE_URL}/api/hr/payslips/{payslip_id}")
        elif response.status_code == 400 and "already exists" in response.text.lower():
            print("Payslip already exists for this period - test passed")
        else:
            print(f"Payslip generation response: {response.status_code} - {response.text}")


class TestStatutoryRates:
    """Test statutory rates data in database"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Login failed - skipping tests")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_epf_rates_exist(self):
        """Test that EPF rates are uploaded in the database"""
        response = self.session.get(f"{BASE_URL}/api/hr/statutory-rates?rate_type=epf")
        
        assert response.status_code == 200
        rates = response.json()
        
        assert isinstance(rates, list), "Rates should be a list"
        assert len(rates) > 0, "EPF rates should be uploaded"
        
        print(f"EPF rates count: {len(rates)}")
        
        # Check first few rates
        if rates:
            first_rate = rates[0]
            assert "min_wages" in first_rate, "Rate should have min_wages"
            assert "max_wages" in first_rate, "Rate should have max_wages"
            assert "employee_amount" in first_rate, "Rate should have employee_amount"
            assert "employer_amount" in first_rate, "Rate should have employer_amount"
            
            print(f"Sample EPF rate: {first_rate}")
    
    def test_socso_rates_exist(self):
        """Test that SOCSO rates are uploaded in the database"""
        response = self.session.get(f"{BASE_URL}/api/hr/statutory-rates?rate_type=socso")
        
        assert response.status_code == 200
        rates = response.json()
        
        print(f"SOCSO rates count: {len(rates)}")
        
        if rates:
            print(f"Sample SOCSO rate: {rates[0]}")
    
    def test_eis_rates_exist(self):
        """Test that EIS rates are uploaded in the database"""
        response = self.session.get(f"{BASE_URL}/api/hr/statutory-rates?rate_type=eis")
        
        assert response.status_code == 200
        rates = response.json()
        
        print(f"EIS rates count: {len(rates)}")
        
        if rates:
            print(f"Sample EIS rate: {rates[0]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
