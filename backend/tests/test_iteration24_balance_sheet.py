"""
Test Iteration 24: Balance Sheet UI Integration Tests
Testing the Balance Sheet tab under Finance > Accounting

Features tested:
- Balance Sheet endpoint (/api/accounting/balance-sheet)
- Balance Sheet Excel export (/api/accounting/balance-sheet/export/excel)
- Trial Balance regression check
- All Accounting sub-tabs availability
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://finance-flow-pro.preview.emergentagent.com')


class TestBalanceSheetBackend:
    """Balance Sheet Backend API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "arjuna@mddrc.com.my",
            "password": "Dana102229"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        # Token field is 'access_token' not 'token'
        token = data.get("access_token") or data.get("token")
        assert token, "No token in login response"
        return token
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authenticated headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    # Balance Sheet endpoint tests
    def test_balance_sheet_endpoint_returns_200(self, auth_headers):
        """Test that balance sheet endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Balance sheet failed: {response.text}"
    
    def test_balance_sheet_returns_expected_structure(self, auth_headers):
        """Test that balance sheet returns expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "period" in data, "Missing 'period' field"
        assert "assets" in data, "Missing 'assets' field"
        assert "liabilities" in data, "Missing 'liabilities' field"
        assert "equity" in data, "Missing 'equity' field"
        assert "total_liabilities_equity" in data, "Missing 'total_liabilities_equity' field"
        assert "is_balanced" in data, "Missing 'is_balanced' field"
    
    def test_balance_sheet_period_label_format(self, auth_headers):
        """Test that period label is in expected format"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Period should be like "As of March 2026"
        assert "As of" in data["period"], f"Period format unexpected: {data['period']}"
        assert "March" in data["period"] or "2026" in data["period"], f"Period doesn't contain month/year: {data['period']}"
    
    def test_balance_sheet_assets_section_structure(self, auth_headers):
        """Test assets section has expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assets = data.get("assets", {})
        assert "accounts" in assets, "Assets missing 'accounts'"
        assert "total" in assets, "Assets missing 'total'"
        assert isinstance(assets["accounts"], list), "Assets accounts should be a list"
    
    def test_balance_sheet_liabilities_section_structure(self, auth_headers):
        """Test liabilities section has expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        liabilities = data.get("liabilities", {})
        assert "accounts" in liabilities, "Liabilities missing 'accounts'"
        assert "total" in liabilities, "Liabilities missing 'total'"
    
    def test_balance_sheet_equity_section_structure(self, auth_headers):
        """Test equity section has expected structure with current_year_earnings"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        equity = data.get("equity", {})
        assert "accounts" in equity, "Equity missing 'accounts'"
        assert "total" in equity, "Equity missing 'total'"
        assert "current_year_earnings" in equity, "Equity missing 'current_year_earnings'"
    
    def test_balance_sheet_accounts_have_codes(self, auth_headers):
        """Test that accounts include account_code field"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check assets accounts for account_code
        for account in data.get("assets", {}).get("accounts", []):
            assert "account_code" in account, f"Asset account missing account_code: {account}"
            assert "account_name" in account, f"Asset account missing account_name: {account}"
            assert "balance" in account, f"Asset account missing balance: {account}"
    
    def test_balance_sheet_is_balanced_field_correct(self, auth_headers):
        """Test that is_balanced reflects actual balance status"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate if it should be balanced
        assets_total = data.get("assets", {}).get("total", 0)
        liabilities_equity_total = data.get("total_liabilities_equity", 0)
        
        # Check is_balanced reflects actual state (within rounding tolerance)
        is_balanced = abs(assets_total - liabilities_equity_total) < 0.01
        assert data["is_balanced"] == is_balanced, f"is_balanced mismatch: assets={assets_total}, l+e={liabilities_equity_total}, field={data['is_balanced']}"
    
    # Excel export tests
    def test_balance_sheet_excel_export_returns_200(self, auth_headers):
        """Test that balance sheet Excel export returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet/export/excel?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Excel export failed: {response.status_code}"
    
    def test_balance_sheet_excel_export_content_type(self, auth_headers):
        """Test that Excel export returns correct content type"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet/export/excel?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "xlsx" in content_type or "octet-stream" in content_type, f"Unexpected content type: {content_type}"
    
    # Trial Balance regression tests
    def test_trial_balance_endpoint_still_works(self, auth_headers):
        """REGRESSION: Trial Balance endpoint should still work"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/trial-balance?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Trial balance failed: {response.text}"
    
    def test_trial_balance_returns_expected_structure(self, auth_headers):
        """REGRESSION: Trial Balance returns expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/trial-balance?year=2026&month=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "period" in data, "Missing 'period'"
        assert "trial_balance" in data, "Missing 'trial_balance'"
        assert "totals" in data, "Missing 'totals'"
    
    # Other accounting endpoints still accessible
    def test_chart_of_accounts_endpoint(self, auth_headers):
        """Test Chart of Accounts endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/chart-of-accounts",
            headers=auth_headers
        )
        assert response.status_code == 200, f"COA failed: {response.text}"
    
    def test_journal_entries_endpoint(self, auth_headers):
        """Test Journal Entries list endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/journal-entries?year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Journal entries failed: {response.text}"
    
    def test_profit_loss_endpoint(self, auth_headers):
        """Test P&L endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/profit-loss?year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200, f"P&L failed: {response.text}"
    
    def test_accounting_settings_endpoint(self, auth_headers):
        """Test Accounting Settings endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/settings",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Settings failed: {response.text}"
    
    def test_accounting_periods_endpoint(self, auth_headers):
        """Test Accounting Periods endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/periods?year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Periods failed: {response.text}"
    
    # Authentication tests
    def test_balance_sheet_requires_auth(self):
        """Test that balance sheet requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3"
        )
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
    
    def test_balance_sheet_excel_requires_auth(self):
        """Test that Excel export requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet/export/excel?year=2026&month=3"
        )
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
