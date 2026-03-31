"""
Test HR Payroll Status and Auto-Link Users Endpoints
Tests for iteration 28 - payroll status, auto-link, and my-payslips endpoints
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://backend-split-5.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"


class TestPayrollStatusEndpoints:
    """Test payroll status and auto-link endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        return None
    
    def get_coordinator_token(self):
        """Get coordinator authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        return None
    
    def test_admin_login(self):
        """Test admin login works"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Admin login successful, token received")
    
    def test_coordinator_login(self):
        """Test coordinator login works"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        assert response.status_code == 200, f"Coordinator login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Coordinator login successful, user: {data.get('user', {}).get('full_name')}")
    
    def test_payroll_status_endpoint(self):
        """Test GET /api/hr/payroll-status returns correct data structure"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get current month payroll status
        now = datetime.now()
        response = self.session.get(f"{BASE_URL}/api/hr/payroll-status?year={now.year}&month={now.month}")
        
        assert response.status_code == 200, f"Payroll status failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "year" in data, "Missing 'year' in response"
        assert "month" in data, "Missing 'month' in response"
        assert "total_staff" in data, "Missing 'total_staff' in response"
        assert "paid_count" in data, "Missing 'paid_count' in response"
        assert "unpaid_count" in data, "Missing 'unpaid_count' in response"
        assert "staff" in data, "Missing 'staff' array in response"
        
        print(f"Payroll status for {data['month']}/{data['year']}: {data['paid_count']} paid, {data['unpaid_count']} unpaid out of {data['total_staff']} staff")
        
        # Verify staff array structure if not empty
        if data['staff']:
            staff_item = data['staff'][0]
            assert "staff_id" in staff_item, "Missing 'staff_id' in staff item"
            assert "full_name" in staff_item, "Missing 'full_name' in staff item"
            assert "has_payslip" in staff_item, "Missing 'has_payslip' in staff item"
            print(f"Sample staff: {staff_item['full_name']} - has_payslip: {staff_item['has_payslip']}")
    
    def test_auto_link_users_endpoint(self):
        """Test POST /api/hr/staff/auto-link-users is idempotent"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First call
        response1 = self.session.post(f"{BASE_URL}/api/hr/staff/auto-link-users")
        assert response1.status_code == 200, f"Auto-link first call failed: {response1.text}"
        data1 = response1.json()
        
        assert "message" in data1, "Missing 'message' in response"
        assert "linked" in data1, "Missing 'linked' count in response"
        print(f"First auto-link call: {data1['message']}, linked: {data1['linked']}")
        
        # Second call (should be idempotent - no new links)
        response2 = self.session.post(f"{BASE_URL}/api/hr/staff/auto-link-users")
        assert response2.status_code == 200, f"Auto-link second call failed: {response2.text}"
        data2 = response2.json()
        
        # Second call should link 0 or same message about all linked
        print(f"Second auto-link call: {data2['message']}, linked: {data2['linked']}")
        # Idempotency check - second call should not link more than first
        assert data2['linked'] <= data1['linked'], "Auto-link is not idempotent"
    
    def test_my_payslips_endpoint_as_coordinator(self):
        """Test GET /api/hr/my-payslips returns data for linked staff"""
        token = self.get_coordinator_token()
        assert token, "Failed to get coordinator token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/hr/my-payslips")
        
        # Should return 200 even if empty (returns [] if no staff record linked)
        assert response.status_code == 200, f"My payslips failed: {response.text}"
        data = response.json()
        
        # Response should be a list
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Coordinator my-payslips returned {len(data)} payslips")
        
        # If payslips exist, verify structure
        if data:
            payslip = data[0]
            assert "year" in payslip, "Missing 'year' in payslip"
            assert "month" in payslip, "Missing 'month' in payslip"
            assert "nett_pay" in payslip, "Missing 'nett_pay' in payslip"
            print(f"Sample payslip: {payslip.get('month')}/{payslip.get('year')} - Nett: {payslip.get('nett_pay')}")
    
    def test_my_pay_advice_endpoint_as_coordinator(self):
        """Test GET /api/hr/my-pay-advice returns data for coordinator"""
        token = self.get_coordinator_token()
        assert token, "Failed to get coordinator token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/hr/my-pay-advice")
        
        assert response.status_code == 200, f"My pay advice failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Coordinator my-pay-advice returned {len(data)} pay advice records")
        
        if data:
            advice = data[0]
            assert "year" in advice, "Missing 'year' in pay advice"
            assert "month" in advice, "Missing 'month' in pay advice"
            print(f"Sample pay advice: {advice.get('month')}/{advice.get('year')}")
    
    def test_staff_list_shows_user_id(self):
        """Test GET /api/hr/staff returns user_id for linked staff"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/hr/staff")
        
        assert response.status_code == 200, f"Staff list failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Staff list returned {len(data)} staff records")
        
        # Check for linked staff
        linked_count = sum(1 for s in data if s.get('user_id'))
        unlinked_count = sum(1 for s in data if not s.get('user_id'))
        print(f"Linked staff: {linked_count}, Unlinked staff: {unlinked_count}")
        
        # Verify structure
        if data:
            staff = data[0]
            assert "id" in staff, "Missing 'id' in staff"
            assert "full_name" in staff, "Missing 'full_name' in staff"
            # user_id may be null for unlinked staff
            print(f"Sample staff: {staff.get('full_name')} - user_id: {staff.get('user_id')}")


class TestFinanceDashboardHRTab:
    """Test Finance Dashboard HR & Payroll tab access"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_hr_staff_endpoint(self):
        """Test HR staff endpoint works for admin"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/hr/staff")
        assert response.status_code == 200, f"HR staff endpoint failed: {response.text}"
        print(f"HR staff endpoint returned {len(response.json())} records")
    
    def test_hr_payslips_endpoint(self):
        """Test HR payslips endpoint works for admin"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/hr/payslips")
        assert response.status_code == 200, f"HR payslips endpoint failed: {response.text}"
        print(f"HR payslips endpoint returned {len(response.json())} records")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
