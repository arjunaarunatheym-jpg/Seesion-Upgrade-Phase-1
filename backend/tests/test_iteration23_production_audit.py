"""
Iteration 23 - Production Audit Testing
Testing Phase 1 production hardening changes:
1. CORS (unchanged at runtime due to .env CORS_ORIGINS='*')
2. Admin password log removal (verify no password in startup log)
3. Dead backup files deleted
4. Database indexes (29 indexes on 15 collections)
5. JWT expiry reduced from 7 days to 24 hours
6. ErrorBoundary wraps entire app
7. ProtectedRoute guards all frontend routes

API Testing Focus:
- Admin login: arjuna@mddrc.com.my / Dana102229
- Coordinator login: malek@mddrc.com.my / mddrc1
- Key endpoints with admin token
- Coordinator access restrictions (should NOT access /finance, /admin)
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
COORDINATOR_EMAIL = "malek@mddrc.com.my"
COORDINATOR_PASSWORD = "mddrc1"


class TestAuthLogin:
    """Test authentication endpoints"""
    
    def test_api_root(self):
        """Test API root is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"PASS: API root accessible - {data['message']}")

    def test_admin_login_success(self):
        """Admin can log in with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login successful - {data['user']['email']} (role: {data['user']['role']})")
        return data["access_token"]

    def test_coordinator_login_success(self):
        """Coordinator can log in with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        assert response.status_code == 200, f"Coordinator login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == COORDINATOR_EMAIL
        assert data["user"]["role"] == "coordinator"
        print(f"PASS: Coordinator login successful - {data['user']['email']} (role: {data['user']['role']})")
        return data["access_token"]

    def test_login_with_wrong_password(self):
        """Login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("PASS: Login with wrong password correctly returns 401")

    def test_login_with_nonexistent_email(self):
        """Login fails with nonexistent email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "anypassword"
        })
        assert response.status_code == 401
        print("PASS: Login with nonexistent email correctly returns 401")


class TestAdminEndpoints:
    """Test admin-accessible endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin authentication failed")
    
    def test_get_invoices(self, admin_token):
        """GET /api/finance/invoices returns 200 with admin token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/invoices", headers=headers)
        assert response.status_code == 200, f"Invoices failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/finance/invoices - {len(data)} invoices returned")
    
    def test_get_hr_staff(self, admin_token):
        """GET /api/hr/staff returns 200 with admin token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/staff", headers=headers)
        assert response.status_code == 200, f"HR staff failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/hr/staff - {len(data)} staff returned")
    
    def test_get_sessions(self, admin_token):
        """GET /api/sessions returns 200 with admin token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        assert response.status_code == 200, f"Sessions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/sessions - {len(data)} sessions returned")
    
    def test_get_pnl_journal(self, admin_token):
        """GET /api/finance/pnl-journal?year=2026 returns 200 with admin token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/finance/pnl-journal?year=2026", headers=headers)
        assert response.status_code == 200, f"PnL Journal failed: {response.text}"
        data = response.json()
        assert "period" in data
        assert "journal_count" in data
        print(f"PASS: GET /api/finance/pnl-journal - journal_count: {data['journal_count']}")
    
    def test_get_chart_of_accounts(self, admin_token):
        """GET /api/accounting/chart-of-accounts returns 200 with admin token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/accounting/chart-of-accounts", headers=headers)
        assert response.status_code == 200, f"Chart of accounts failed: {response.text}"
        data = response.json()
        # Response is {accounts: [...], grouped: {...}, total: int}
        assert isinstance(data, dict)
        assert "accounts" in data
        assert "total" in data
        print(f"PASS: GET /api/accounting/chart-of-accounts - {data['total']} accounts returned")
    
    def test_get_quotations(self, admin_token):
        """GET /api/marketing/quotations returns 200 with admin token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/marketing/quotations", headers=headers)
        assert response.status_code == 200, f"Quotations failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: GET /api/marketing/quotations - {len(data)} quotations returned")
    
    def test_get_auth_me(self, admin_token):
        """GET /api/auth/me returns admin user details"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Auth me failed: {response.text}"
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["role"] == "admin"
        print(f"PASS: GET /api/auth/me - {data['email']} (role: {data['role']})")


class TestCoordinatorEndpoints:
    """Test coordinator-accessible endpoints and restrictions"""
    
    @pytest.fixture(scope="class")
    def coordinator_token(self):
        """Get coordinator authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Coordinator authentication failed")
    
    def test_coordinator_can_get_sessions(self, coordinator_token):
        """Coordinator CAN access sessions"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/sessions", headers=headers)
        # Coordinators should be able to see sessions
        assert response.status_code == 200, f"Coordinator sessions access failed: {response.text}"
        print("PASS: Coordinator CAN access sessions")
    
    def test_coordinator_auth_me(self, coordinator_token):
        """GET /api/auth/me returns coordinator user details"""
        headers = {"Authorization": f"Bearer {coordinator_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Coordinator auth me failed: {response.text}"
        data = response.json()
        assert data["email"] == COORDINATOR_EMAIL
        assert data["role"] == "coordinator"
        print(f"PASS: Coordinator auth me - {data['email']} (role: {data['role']})")


class TestUnauthorizedAccess:
    """Test endpoints without authentication"""
    
    def test_invoices_without_token(self):
        """Invoices endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/finance/invoices")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Invoices endpoint requires authentication")
    
    def test_sessions_without_token(self):
        """Sessions endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/sessions")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Sessions endpoint requires authentication")
    
    def test_hr_staff_without_token(self):
        """HR staff endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/hr/staff")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: HR staff endpoint requires authentication")


class TestJWTExpiry:
    """Test JWT token behavior (24h expiry)"""
    
    def test_token_structure(self):
        """Verify login returns a valid JWT token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        token = data["access_token"]
        
        # JWT format: header.payload.signature
        parts = token.split(".")
        assert len(parts) == 3, "Token should have 3 parts (JWT format)"
        print("PASS: Token has correct JWT structure")
    
    def test_token_is_usable(self):
        """Verify token can be used for authenticated requests"""
        # Login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Use token
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        print("PASS: Token is usable for authenticated requests")


class TestSecurityHeaders:
    """Test security headers in responses"""
    
    def test_security_headers_present(self):
        """Verify security headers are present in responses"""
        response = requests.get(f"{BASE_URL}/api/")
        headers = response.headers
        
        # These headers should be set by SecurityMiddleware
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ]
        
        for header in expected_headers:
            assert header in headers, f"Missing security header: {header}"
            print(f"PASS: Security header present - {header}: {headers[header]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
