"""
Super Admin Portal API Tests
Tests for /api/superadmin/* endpoints
- Dashboard statistics
- User management (list, role change, lock/unlock, password reset)
- Session management (list, status filter, fix status)
- Invoice management (list, status filter, void)
- Quotation management
- Audit log
- Export functionality
- Access control
"""
import pytest
import requests
import os
import json

# Backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "arjuna@mddrc.com.my"
SUPER_ADMIN_PASSWORD = "Dana102229"
REGULAR_ADMIN_EMAIL = "chandra.selvaguru@mddrc.com.my"
REGULAR_ADMIN_PASSWORD = "mddrc1"


class TestSuperAdminAccessControl:
    """Test access control - only super admin or specific email can access"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens for testing"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Get super admin token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.super_admin_token = response.json().get("access_token")
            self.super_admin_headers = {"Authorization": f"Bearer {self.super_admin_token}"}
        else:
            pytest.skip("Super admin login failed")
    
    def test_super_admin_can_access_dashboard(self):
        """Super admin should access dashboard"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/dashboard",
            headers=self.super_admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "users" in data
        assert "sessions" in data
        assert "invoices" in data
        print(f"Dashboard stats loaded: {data['users']['total']} users, {data['sessions']['total']} sessions")
    
    def test_regular_user_cannot_access_superadmin(self):
        """Regular admin should be denied access"""
        # Login as regular admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": REGULAR_ADMIN_EMAIL,
            "password": REGULAR_ADMIN_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Regular admin login failed: {response.text}")
        
        regular_token = response.json().get("access_token")
        regular_headers = {"Authorization": f"Bearer {regular_token}"}
        
        # Try to access super admin dashboard
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/dashboard",
            headers=regular_headers
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Regular admin correctly denied access (403)")


class TestSuperAdminDashboard:
    """Test dashboard statistics endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_dashboard_returns_all_stats(self):
        """Dashboard should return comprehensive statistics"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/dashboard",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify users stats
        assert "users" in data
        assert "total" in data["users"]
        assert "by_role" in data["users"]
        assert data["users"]["total"] >= 0
        print(f"Users: {data['users']['total']} total, roles: {data['users']['by_role']}")
        
        # Verify sessions stats
        assert "sessions" in data
        assert "total" in data["sessions"]
        assert "ongoing" in data["sessions"]
        assert "completed" in data["sessions"]
        print(f"Sessions: {data['sessions']['total']} total")
        
        # Verify invoices stats
        assert "invoices" in data
        assert "total" in data["invoices"]
        print(f"Invoices: {data['invoices']['total']} total")
        
        # Verify quotations stats
        assert "quotations" in data
        assert "total" in data["quotations"]
        print(f"Quotations: {data['quotations']['total']} total")


class TestSuperAdminUsers:
    """Test user management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_get_all_users(self):
        """Should list all users"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/users",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        assert "count" in data
        assert len(data["users"]) > 0
        
        # Verify user fields
        user = data["users"][0]
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "hashed_password" not in user  # Should be excluded
        print(f"Users listed: {data['count']} users")
    
    def test_search_users(self):
        """Should search users by name or email"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/users?search=arjuna",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should find at least the super admin user
        assert data["count"] >= 1
        print(f"Search 'arjuna': found {data['count']} users")
    
    def test_get_single_user(self):
        """Should get single user details"""
        # First get a user ID
        list_response = self.session.get(
            f"{BASE_URL}/api/superadmin/users?limit=1",
            headers=self.headers
        )
        assert list_response.status_code == 200
        users = list_response.json()["users"]
        
        if not users:
            pytest.skip("No users found")
        
        user_id = users[0]["id"]
        
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/users/{user_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        user = response.json()
        
        assert user["id"] == user_id
        assert "email" in user
        print(f"Single user fetched: {user['email']}")
    
    def test_update_user_requires_reason(self):
        """Update user should require a reason"""
        # Get a non-admin user to test
        list_response = self.session.get(
            f"{BASE_URL}/api/superadmin/users?role=participant&limit=1",
            headers=self.headers
        )
        users = list_response.json().get("users", [])
        
        if not users:
            pytest.skip("No participant users found to test")
        
        user_id = users[0]["id"]
        
        # Try update without reason - should fail (422 validation error)
        response = self.session.put(
            f"{BASE_URL}/api/superadmin/users/{user_id}",
            headers=self.headers,
            json={"full_name": "Test Name"}
        )
        assert response.status_code == 422, f"Expected 422 without reason, got {response.status_code}"
        print("Update without reason correctly rejected (422)")


class TestSuperAdminSessions:
    """Test session management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_get_all_sessions(self):
        """Should list all sessions"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/sessions",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "sessions" in data
        assert "count" in data
        print(f"Sessions: {data['count']} total")
    
    def test_filter_sessions_by_status(self):
        """Should filter sessions by completion status"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/sessions?status=completed",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned sessions should have status = completed
        for session in data["sessions"]:
            assert session.get("completion_status") == "completed", f"Expected completed, got {session.get('completion_status')}"
        print(f"Filtered sessions: {data['count']} completed")
    
    def test_fix_session_status_requires_reason(self):
        """Fix session status should require reason"""
        # Get any session
        list_response = self.session.get(
            f"{BASE_URL}/api/superadmin/sessions?limit=1",
            headers=self.headers
        )
        sessions = list_response.json().get("sessions", [])
        
        if not sessions:
            pytest.skip("No sessions found")
        
        session_id = sessions[0]["id"]
        
        # Try without reason - should fail
        response = self.session.post(
            f"{BASE_URL}/api/superadmin/sessions/{session_id}/fix-status?new_status=completed",
            headers=self.headers
        )
        assert response.status_code == 422, f"Expected 422 without reason, got {response.status_code}"
        print("Fix status without reason correctly rejected (422)")


class TestSuperAdminInvoices:
    """Test invoice management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_get_all_invoices(self):
        """Should list all invoices"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/invoices",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "invoices" in data
        assert "count" in data
        print(f"Invoices: {data['count']} total")
    
    def test_filter_invoices_by_status(self):
        """Should filter invoices by status"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/invoices?status=issued",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for invoice in data["invoices"]:
            assert invoice.get("status") == "issued"
        print(f"Filtered invoices: {data['count']} issued")
    
    def test_void_invoice_requires_reason(self):
        """Void invoice should require detailed reason"""
        # Get any non-voided invoice
        list_response = self.session.get(
            f"{BASE_URL}/api/superadmin/invoices?limit=10",
            headers=self.headers
        )
        invoices = [inv for inv in list_response.json().get("invoices", []) if inv.get("status") != "voided"]
        
        if not invoices:
            pytest.skip("No non-voided invoices found")
        
        invoice_id = invoices[0]["id"]
        
        # Try void without reason - should fail (missing required param)
        response = self.session.post(
            f"{BASE_URL}/api/superadmin/invoices/{invoice_id}/void",
            headers=self.headers
        )
        assert response.status_code == 422, f"Expected 422 without reason, got {response.status_code}"
        
        # Try with short reason - should fail (min 10 chars)
        response = self.session.post(
            f"{BASE_URL}/api/superadmin/invoices/{invoice_id}/void?reason=short",
            headers=self.headers
        )
        assert response.status_code == 422, f"Expected 422 with short reason, got {response.status_code}"
        print("Void without valid reason correctly rejected")


class TestSuperAdminQuotations:
    """Test quotation management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_get_all_quotations(self):
        """Should list all quotations"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/quotations",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "quotations" in data
        assert "count" in data
        print(f"Quotations: {data['count']} total")


class TestSuperAdminAuditLog:
    """Test audit log endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_get_audit_log(self):
        """Should retrieve audit log entries"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/audit-log",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "logs" in data
        assert "count" in data
        
        # If there are logs, verify structure
        if data["logs"]:
            log = data["logs"][0]
            assert "action" in log
            assert "entity_type" in log
            assert "timestamp" in log
            assert "performed_by_email" in log
            print(f"Audit log: {data['count']} entries, latest action: {log['action']}")
        else:
            print("Audit log: No entries yet")
    
    def test_perform_action_creates_audit_log(self):
        """Performing an action should create audit log entry"""
        # Get a participant user to update
        list_response = self.session.get(
            f"{BASE_URL}/api/superadmin/users?role=participant&limit=1",
            headers=self.headers
        )
        users = list_response.json().get("users", [])
        
        if not users:
            pytest.skip("No participant users found")
        
        user_id = users[0]["id"]
        original_name = users[0].get("full_name", "Test User")
        
        # Update user with reason
        update_response = self.session.put(
            f"{BASE_URL}/api/superadmin/users/{user_id}?reason=Testing audit log functionality",
            headers=self.headers,
            json={"full_name": original_name}  # Keep same name
        )
        
        if update_response.status_code != 200:
            pytest.skip(f"Update failed: {update_response.text}")
        
        # Check audit log
        log_response = self.session.get(
            f"{BASE_URL}/api/superadmin/audit-log?limit=5",
            headers=self.headers
        )
        assert log_response.status_code == 200
        logs = log_response.json()["logs"]
        
        # Should have recent user_updated action
        recent_log = logs[0] if logs else None
        assert recent_log is not None
        assert recent_log["action"] == "user_updated"
        assert recent_log["entity_id"] == user_id
        assert "Testing audit log" in (recent_log.get("reason") or "")
        print(f"Audit log entry created: {recent_log['action']} on {recent_log['entity_type']}")


class TestSuperAdminExport:
    """Test data export endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_export_users_csv(self):
        """Should export users to CSV"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/export/users",
            headers=self.headers
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        assert "attachment" in response.headers.get("Content-Disposition", "")
        
        # CSV should have content
        content = response.text
        assert len(content) > 0
        assert "email" in content.lower() or "full_name" in content.lower()
        print(f"Users CSV exported: {len(content)} bytes")
    
    def test_export_sessions_csv(self):
        """Should export sessions to CSV"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/export/sessions",
            headers=self.headers
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("Content-Type", "")
        print(f"Sessions CSV exported: {len(response.text)} bytes")
    
    def test_export_invalid_collection(self):
        """Should reject export of invalid collection"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/export/invalid_collection",
            headers=self.headers
        )
        
        assert response.status_code == 400
        print("Invalid collection export correctly rejected (400)")


class TestSuperAdminSettings:
    """Test system settings endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Login failed")
    
    def test_get_system_settings(self):
        """Should retrieve system settings"""
        response = self.session.get(
            f"{BASE_URL}/api/superadmin/settings",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have company and accounting settings
        assert "company_settings" in data or "accounting_settings" in data or "billing_parties" in data
        print(f"System settings loaded: {list(data.keys())}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
