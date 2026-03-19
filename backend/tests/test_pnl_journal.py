"""
Test: Phase C - Journal-Based P&L (Auditor P&L Tab)
Tests the pnl-journal endpoints added in finance_reports.py (lines 1004-1346)

Endpoints tested:
- GET /api/finance/pnl-journal - Auditor-grade P&L statement from journal entries
- GET /api/finance/pnl-journal/export - Excel export
- GET /api/finance/pnl-journal/drilldown/{account_code} - Account drill-down
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPnLJournalAuth:
    """Test authentication and authorization for pnl-journal endpoints"""
    
    def setup_method(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pnl_journal_requires_auth(self):
        """pnl-journal should return 401 or 403 without auth"""
        response = requests.get(f"{BASE_URL}/api/finance/pnl-journal?year=2026")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASSED - pnl-journal requires authentication (got {response.status_code})")
    
    def test_pnl_journal_export_requires_auth(self):
        """pnl-journal/export should return 401 or 403 without auth"""
        response = requests.get(f"{BASE_URL}/api/finance/pnl-journal/export?year=2026")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASSED - pnl-journal/export requires authentication (got {response.status_code})")
    
    def test_pnl_journal_drilldown_requires_auth(self):
        """pnl-journal/drilldown should return 401 or 403 without auth"""
        response = requests.get(f"{BASE_URL}/api/finance/pnl-journal/drilldown/4000?year=2026")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASSED - pnl-journal/drilldown requires authentication (got {response.status_code})")


class TestPnLJournalEndpoint:
    """Test the main pnl-journal endpoint"""
    
    def setup_method(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pnl_journal_year_2026(self):
        """GET /api/finance/pnl-journal?year=2026 returns valid JSON structure"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "period" in data, "Missing 'period' field"
        assert "journal_count" in data, "Missing 'journal_count' field"
        assert "sections" in data, "Missing 'sections' field"
        assert "summary" in data, "Missing 'summary' field"
        assert "warnings" in data, "Missing 'warnings' field"
        
        # Verify sections structure
        sections = data["sections"]
        expected_sections = ["revenue", "cost_of_sales", "other_income", "operating_expense", "other_expense"]
        for sec in expected_sections:
            assert sec in sections, f"Missing section '{sec}'"
            assert "label" in sections[sec], f"Missing 'label' in section '{sec}'"
            assert "accounts" in sections[sec], f"Missing 'accounts' in section '{sec}'"
            assert "total" in sections[sec], f"Missing 'total' in section '{sec}'"
        
        # Verify summary structure
        summary = data["summary"]
        summary_fields = ["total_revenue", "other_income", "total_income", "cost_of_sales", 
                         "gross_profit", "gross_margin_pct", "operating_expenses", 
                         "net_profit", "net_margin_pct"]
        for field in summary_fields:
            assert field in summary, f"Missing summary field '{field}'"
        
        print(f"PASSED - pnl-journal?year=2026: period={data['period']}, journal_count={data['journal_count']}")
        print(f"  Summary: net_profit={summary['net_profit']}, gross_profit={summary['gross_profit']}")
    
    def test_pnl_journal_year_2025(self):
        """GET /api/finance/pnl-journal?year=2025 returns valid JSON (may have 0 journals)"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal?year=2025",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "period" in data
        assert "journal_count" in data
        assert data["period"] == "Year 2025"
        
        print(f"PASSED - pnl-journal?year=2025: journal_count={data['journal_count']}")
    
    def test_pnl_journal_month_filter(self):
        """GET /api/finance/pnl-journal?year=2026&month=1 returns valid JSON with month filter"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal?year=2026&month=1",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "period" in data
        assert "January" in data["period"], f"Expected January in period, got {data['period']}"
        assert "journal_count" in data
        
        print(f"PASSED - pnl-journal with month filter: period={data['period']}, journals={data['journal_count']}")
    
    def test_pnl_journal_date_range_filter(self):
        """GET /api/finance/pnl-journal?date_from=2026-01-01&date_to=2026-03-31 returns valid JSON"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal?date_from=2026-01-01&date_to=2026-03-31",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "period" in data
        assert "date_from" in data
        assert "date_to" in data
        assert data["date_from"] == "2026-01-01"
        assert data["date_to"] == "2026-03-31"
        
        print(f"PASSED - pnl-journal with date range: {data['date_from']} to {data['date_to']}")
    
    def test_pnl_journal_posted_only_default_true(self):
        """Verify posted_only defaults to true"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # posted_only should default to True
        assert data.get("posted_only") == True, f"Expected posted_only=True, got {data.get('posted_only')}"
        print("PASSED - posted_only defaults to True")


class TestPnLJournalExport:
    """Test the pnl-journal Excel export endpoint"""
    
    def setup_method(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pnl_journal_export_returns_excel(self):
        """GET /api/finance/pnl-journal/export?year=2026 returns Excel file"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal/export?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        expected_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert expected_type in content_type, f"Expected Excel content type, got {content_type}"
        
        # Check content-disposition for filename
        content_disposition = response.headers.get("content-disposition", "")
        assert "PnL_" in content_disposition, f"Expected PnL filename, got {content_disposition}"
        assert ".xlsx" in content_disposition, f"Expected .xlsx extension"
        
        # Verify file has content
        assert len(response.content) > 100, "Excel file seems too small"
        
        print(f"PASSED - pnl-journal/export returns Excel ({len(response.content)} bytes)")


class TestPnLJournalDrilldown:
    """Test the pnl-journal drilldown endpoint"""
    
    def setup_method(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pnl_journal_drilldown_income_account(self):
        """GET /api/finance/pnl-journal/drilldown/4000?year=2026 returns valid drilldown data"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal/drilldown/4000?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "account_code" in data, "Missing 'account_code' field"
        assert "account_name" in data, "Missing 'account_name' field"
        assert "entries" in data, "Missing 'entries' array"
        assert "total_debit" in data, "Missing 'total_debit' field"
        assert "total_credit" in data, "Missing 'total_credit' field"
        
        assert data["account_code"] == "4000"
        assert isinstance(data["entries"], list)
        assert isinstance(data["total_debit"], (int, float))
        assert isinstance(data["total_credit"], (int, float))
        
        print(f"PASSED - drilldown/4000: {len(data['entries'])} entries, debit={data['total_debit']}, credit={data['total_credit']}")
    
    def test_pnl_journal_drilldown_expense_account(self):
        """GET /api/finance/pnl-journal/drilldown/5001?year=2026 returns valid drilldown data"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal/drilldown/5001?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["account_code"] == "5001"
        assert "entries" in data
        assert "total_debit" in data
        assert "total_credit" in data
        
        print(f"PASSED - drilldown/5001: {len(data['entries'])} entries")
    
    def test_pnl_journal_drilldown_with_date_range(self):
        """Drilldown with date_from and date_to parameters"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal/drilldown/4000?date_from=2026-01-01&date_to=2026-06-30",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["date_from"] == "2026-01-01"
        assert data["date_to"] == "2026-06-30"
        
        print(f"PASSED - drilldown with date range filter")
    
    def test_pnl_journal_drilldown_entry_structure(self):
        """Verify drilldown entry structure (when entries exist)"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal/drilldown/4000?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # If there are entries, verify structure
        if len(data["entries"]) > 0:
            entry = data["entries"][0]
            expected_fields = ["journal_no", "date", "description", "debit", "credit"]
            for field in expected_fields:
                assert field in entry, f"Missing field '{field}' in drilldown entry"
            print(f"PASSED - drilldown entries have correct structure: {list(entry.keys())}")
        else:
            print("PASSED - drilldown returns empty entries (0 journals in DB - expected)")


class TestDataIntegrity:
    """Test data integrity of P&L calculations"""
    
    def setup_method(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_summary_calculations(self):
        """Verify P&L summary calculations are consistent"""
        response = requests.get(
            f"{BASE_URL}/api/finance/pnl-journal?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        summary = data["summary"]
        sections = data["sections"]
        
        # total_income = revenue.total + other_income.total
        calc_total_income = sections["revenue"]["total"] + sections["other_income"]["total"]
        assert abs(summary["total_income"] - calc_total_income) < 0.01, \
            f"total_income mismatch: {summary['total_income']} vs {calc_total_income}"
        
        # gross_profit = revenue.total - cost_of_sales.total
        calc_gross = sections["revenue"]["total"] - sections["cost_of_sales"]["total"]
        assert abs(summary["gross_profit"] - calc_gross) < 0.01, \
            f"gross_profit mismatch: {summary['gross_profit']} vs {calc_gross}"
        
        # operating_expenses = operating_expense.total + other_expense.total
        calc_opex = sections["operating_expense"]["total"] + sections["other_expense"]["total"]
        assert abs(summary["operating_expenses"] - calc_opex) < 0.01, \
            f"operating_expenses mismatch: {summary['operating_expenses']} vs {calc_opex}"
        
        print("PASSED - All P&L summary calculations are consistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
