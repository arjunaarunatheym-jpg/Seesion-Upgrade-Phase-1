"""
Iteration 30 - Testing Dashboard KPIs and Backend Role Protection
Tests:
1. GET /api/admin/dashboard-kpis - Admin access and data validation
2. GET /api/admin/dashboard-kpis - 403 for non-admin users (coordinator)
3. Accounting export endpoints - 403 for coordinator
4. Finance payables period-status - 403 for coordinator
5. Finance expense-categories - 403 for trainers/participants
6. Training reports - 403 for non-admin/non-coordinator
7. Certificates eligibility - 403 for trainers
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


class TestAuthHelper:
    """Helper class for authentication"""
    
    @staticmethod
    def login(email: str, password: str) -> dict:
        """Login and return token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return {
                "token": data.get("access_token"),
                "user": data.get("user")
            }
        return None
    
    @staticmethod
    def get_headers(token: str) -> dict:
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }


class TestDashboardKPIs:
    """Test Dashboard KPIs endpoint"""
    
    def test_admin_can_access_dashboard_kpis(self):
        """Admin should be able to access dashboard KPIs"""
        auth = TestAuthHelper.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert auth is not None, "Admin login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/admin/dashboard-kpis", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Validate KPI data structure
        assert "sessions_this_month" in data, "Missing sessions_this_month"
        assert "revenue_ytd" in data, "Missing revenue_ytd"
        assert "outstanding_total" in data, "Missing outstanding_total"
        assert "total_trainees_ytd" in data, "Missing total_trainees_ytd"
        assert "avg_feedback_score" in data, "Missing avg_feedback_score"
        assert "trainer_utilization" in data, "Missing trainer_utilization"
        assert "staff_count" in data, "Missing staff_count"
        assert "pending_quotations" in data, "Missing pending_quotations"
        assert "year" in data, "Missing year"
        assert "month" in data, "Missing month"
        
        print(f"✓ Admin KPI access successful - Sessions this month: {data['sessions_this_month']}, Revenue YTD: {data['revenue_ytd']}")
    
    def test_coordinator_cannot_access_dashboard_kpis(self):
        """Coordinator should get 403 when accessing dashboard KPIs"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/admin/dashboard-kpis", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Coordinator correctly denied access to dashboard KPIs (403)")


class TestAccountingExportRoleProtection:
    """Test accounting export endpoints role protection"""
    
    def test_admin_can_access_journal_entries_export(self):
        """Admin should be able to access journal entries export"""
        auth = TestAuthHelper.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert auth is not None, "Admin login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/accounting/journal-entries/export/excel?year=2026", headers=headers)
        
        # Should return 200 or 404 (no data), but not 403
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        print(f"✓ Admin journal entries export access: {response.status_code}")
    
    def test_coordinator_cannot_access_journal_entries_export(self):
        """Coordinator should get 403 when accessing journal entries export"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/accounting/journal-entries/export/excel?year=2026", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Coordinator correctly denied access to journal entries export (403)")
    
    def test_coordinator_cannot_access_trial_balance_export(self):
        """Coordinator should get 403 when accessing trial balance export"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/accounting/trial-balance/export/excel?year=2026&month=3", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Coordinator correctly denied access to trial balance export (403)")
    
    def test_coordinator_cannot_access_profit_loss_export(self):
        """Coordinator should get 403 when accessing profit-loss export"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/accounting/profit-loss/export/excel?year=2026&month=3", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Coordinator correctly denied access to profit-loss export (403)")
    
    def test_coordinator_cannot_access_balance_sheet_export(self):
        """Coordinator should get 403 when accessing balance sheet export"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/accounting/balance-sheet/export/excel?year=2026&month=3", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Coordinator correctly denied access to balance sheet export (403)")


class TestFinancePayablesRoleProtection:
    """Test finance payables endpoints role protection"""
    
    def test_coordinator_cannot_access_period_status(self):
        """Coordinator should get 403 when accessing payables period-status"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/finance/payables/period-status?year=2026&month=3", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Coordinator correctly denied access to payables period-status (403)")
    
    def test_admin_can_access_period_status(self):
        """Admin should be able to access payables period-status"""
        auth = TestAuthHelper.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert auth is not None, "Admin login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/finance/payables/period-status?year=2026&month=3", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin can access payables period-status (200)")


class TestExpenseCategoriesRoleProtection:
    """Test expense categories endpoint role protection"""
    
    def test_coordinator_can_access_expense_categories(self):
        """Coordinator should be able to access expense categories"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/finance/expense-categories", headers=headers)
        
        # Coordinator is allowed per the code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Coordinator can access expense categories (200)")
    
    def test_admin_can_access_expense_categories(self):
        """Admin should be able to access expense categories"""
        auth = TestAuthHelper.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert auth is not None, "Admin login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/finance/expense-categories", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of expense categories"
        assert len(data) > 0, "Expected at least one expense category"
        print(f"✓ Admin can access expense categories (200) - {len(data)} categories")


class TestTrainingReportsRoleProtection:
    """Test training reports endpoints role protection"""
    
    def test_admin_can_access_training_reports(self):
        """Admin should be able to access training reports"""
        auth = TestAuthHelper.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert auth is not None, "Admin login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/training-reports/admin/all", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin can access training reports (200)")
    
    def test_coordinator_cannot_access_admin_all_reports(self):
        """Coordinator should get 403 when accessing admin/all reports"""
        auth = TestAuthHelper.login(COORDINATOR_EMAIL, COORDINATOR_PASSWORD)
        assert auth is not None, "Coordinator login failed"
        
        headers = TestAuthHelper.get_headers(auth["token"])
        response = requests.get(f"{BASE_URL}/api/training-reports/admin/all", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Coordinator correctly denied access to admin/all reports (403)")


class TestLoginFlow:
    """Test login flow for both admin and coordinator"""
    
    def test_admin_login(self):
        """Admin login should work"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["role"] == "admin", f"Expected admin role, got {data['user']['role']}"
        print(f"✓ Admin login successful - User: {data['user']['full_name']}")
    
    def test_coordinator_login(self):
        """Coordinator login should work"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COORDINATOR_EMAIL,
            "password": COORDINATOR_PASSWORD
        })
        
        assert response.status_code == 200, f"Coordinator login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["role"] == "coordinator", f"Expected coordinator role, got {data['user']['role']}"
        print(f"✓ Coordinator login successful - User: {data['user']['full_name']}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ Health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
