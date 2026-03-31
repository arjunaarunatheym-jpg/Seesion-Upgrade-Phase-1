"""
Automated Test Suite — Critical Business Flows
Run: cd /app/backend && python -m pytest tests/test_critical_flows.py -v
"""
import pytest
import httpx
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"


@pytest.fixture(scope="module")
def token():
    """Get admin auth token."""
    r = httpx.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- AUTH ---
class TestAuth:
    def test_login_success(self):
        r = httpx.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["user"]["role"] in ["admin", "super_admin"]

    def test_login_wrong_password(self):
        r = httpx.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpass"}, timeout=15)
        assert r.status_code in [401, 400, 429]

    def test_protected_route_no_token(self):
        r = httpx.get(f"{API}/users", timeout=10)
        assert r.status_code in [401, 403, 422]


# --- HEALTH ---
class TestHealth:
    def test_basic_health(self):
        r = httpx.get(f"{API}/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] in ["healthy", "degraded"]

    def test_detailed_health(self, headers):
        r = httpx.get(f"{API}/health/detailed", headers=headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["summary"]["total"] > 0
        assert data["summary"]["passed"] > 0


# --- SETTINGS ---
class TestSettings:
    def test_get_settings(self, headers):
        r = httpx.get(f"{API}/settings", headers=headers, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "company_name" in data

    def test_update_settings(self, headers):
        r = httpx.put(f"{API}/settings", headers=headers, json={"sst_rate": 6.0}, timeout=10)
        assert r.status_code == 200


# --- COMPANIES ---
class TestCompanies:
    def test_list_companies(self, headers):
        r = httpx.get(f"{API}/companies", headers=headers, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# --- PROGRAMS ---
class TestPrograms:
    def test_list_programs(self, headers):
        r = httpx.get(f"{API}/programs", headers=headers, timeout=10)
        assert r.status_code == 200


# --- SESSIONS ---
class TestSessions:
    def test_list_sessions(self, headers):
        r = httpx.get(f"{API}/sessions", headers=headers, timeout=10)
        assert r.status_code == 200


# --- INVOICES ---
class TestInvoices:
    def test_list_invoices(self, headers):
        r = httpx.get(f"{API}/finance/invoices", headers=headers, timeout=10)
        assert r.status_code == 200


# --- HR & PAYROLL ---
class TestHR:
    def test_list_staff(self, headers):
        r = httpx.get(f"{API}/hr/staff", headers=headers, timeout=10)
        assert r.status_code == 200

    def test_statutory_calculation(self, headers):
        r = httpx.post(f"{API}/hr/statutory/calculate", headers=headers, json={
            "gross_salary": 3000, "nric": "850315101234"
        }, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["epf_employee"] > 0
        assert data["epf_employer"] > 0
        assert data["socso_employee"] >= 0
        assert data["eis_employee"] >= 0
        # EPF should be whole RM (no cents)
        assert data["epf_employee"] == int(data["epf_employee"])

    def test_statutory_age_60_plus(self, headers):
        r = httpx.post(f"{API}/hr/statutory/calculate", headers=headers, json={
            "gross_salary": 5000, "nric": "551130105325"
        }, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["epf_employee"] == 0  # Age 60+: no employee EPF
        assert data["epf_employer"] > 0   # Employer still pays 4%
        assert data["eis_employee"] == 0  # Age 57+: no EIS


# --- FINANCE REPORTS ---
class TestFinanceReports:
    def test_profit_loss(self, headers):
        r = httpx.get(f"{API}/finance/profit-loss?year=2026", headers=headers, timeout=15)
        assert r.status_code == 200

    def test_profit_loss_by_programme(self, headers):
        r = httpx.get(f"{API}/finance/profit-loss/by-programme?year=2026", headers=headers, timeout=15)
        assert r.status_code == 200

    def test_ar_aging(self, headers):
        r = httpx.get(f"{API}/finance/ar-aging", headers=headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "buckets" in data
        assert "by_company" in data


# --- KPI ---
class TestKPI:
    def test_dashboard_kpis(self, headers):
        r = httpx.get(f"{API}/admin/dashboard-kpis", headers=headers, timeout=15)
        assert r.status_code == 200

    def test_kpi_drilldown(self, headers):
        r = httpx.get(f"{API}/admin/kpi-drilldown/staff_count", headers=headers, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data


# --- BACKUP ---
class TestBackup:
    def test_list_collections(self, headers):
        r = httpx.get(f"{API}/backup/collections", headers=headers, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert len(data["collections"]) > 10

    def test_export_single_collection(self, headers):
        r = httpx.get(f"{API}/backup/export/users?format=json", headers=headers, timeout=15)
        assert r.status_code == 200


# --- LEADS ---
class TestLeads:
    def test_list_leads(self, headers):
        r = httpx.get(f"{API}/marketing/leads", headers=headers, timeout=10)
        assert r.status_code == 200


# --- USERS ---
class TestUsers:
    def test_list_users(self, headers):
        r = httpx.get(f"{API}/users", headers=headers, timeout=10)
        assert r.status_code == 200
