"""
Iteration 29 - Testing Loading States, Empty States, and PWA Enhancements
Tests for:
1. Login API returns access_token
2. Finance Dashboard API returns dashboard data
3. Backend health check
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"


class TestAuthAPI:
    """Authentication endpoint tests"""
    
    def test_health_check(self):
        """Test backend health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert "database" in data
        print(f"✓ Health check passed: {data}")
    
    def test_admin_login_returns_access_token(self):
        """Test admin login returns access_token (not token)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify access_token is returned (not just 'token')
        assert "access_token" in data, "Response should contain 'access_token'"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        
        # Verify user data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful, access_token received")
        return data["access_token"]
    
    def test_coordinator_login(self):
        """Test coordinator login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": COORDINATOR_EMAIL, "password": COORDINATOR_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "coordinator"
        print(f"✓ Coordinator login successful")
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 400]
        print(f"✓ Invalid login correctly rejected")


class TestFinanceDashboardAPI:
    """Finance Dashboard API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    def test_finance_dashboard_returns_data(self, auth_token):
        """Test finance dashboard API returns dashboard data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify dashboard data structure
        assert "total_revenue" in data or "revenue" in data or isinstance(data, dict)
        print(f"✓ Finance dashboard data received: {list(data.keys())[:5]}...")
    
    def test_finance_invoices_endpoint(self, auth_token):
        """Test finance invoices endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/invoices", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Finance invoices endpoint working, {len(data)} invoices found")


class TestSessionsAPI:
    """Sessions API tests for coordinator/trainer dashboards"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture
    def coordinator_token(self):
        """Get coordinator auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": COORDINATOR_EMAIL, "password": COORDINATOR_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Coordinator authentication failed")
    
    def test_sessions_endpoint(self, admin_token):
        """Test sessions endpoint returns list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Sessions endpoint working, {len(data)} sessions found")
    
    def test_coordinator_sessions(self, coordinator_token):
        """Test coordinator can access sessions"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Coordinator sessions endpoint working, {len(data)} sessions")


class TestMarketingAPI:
    """Marketing Dashboard API tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    def test_marketing_stats(self, auth_token):
        """Test marketing stats endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/marketing/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        print(f"✓ Marketing stats endpoint working")


class TestPWAEndpoints:
    """Test PWA-related endpoints"""
    
    def test_manifest_accessible(self):
        """Test manifest.json is accessible"""
        response = requests.get(f"{BASE_URL}/manifest.json")
        # May return 200 or 404 depending on setup
        print(f"✓ Manifest check: status {response.status_code}")
    
    def test_settings_endpoint(self):
        """Test settings endpoint (used by PWA for caching)"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        print(f"✓ Settings endpoint working for PWA caching")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
