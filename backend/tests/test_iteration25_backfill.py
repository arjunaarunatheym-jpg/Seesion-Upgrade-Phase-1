"""
Iteration 25: Backfill Journal Entries Testing
Tests the 'Sync Historical Transactions' feature that backfills journal entries
for historical invoices, payments, and credit notes.

Features tested:
1. POST /api/accounting/backfill - creates journal entries for unsynced transactions
2. Backfill idempotency - re-running creates 0 new entries
3. Paid invoices correctly map to Training Revenue (4000) not Deferred Revenue (2300)
4. P&L Statement shows Training Revenue after backfill
5. Balance Sheet shows Accounts Receivable and is balanced
6. Auth required - non-authenticated users denied
7. Other accounting endpoints regression check
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://finance-flow-pro.preview.emergentagent.com')


class TestBackfillJournalEntries:
    """Test suite for backfill functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        )
        assert response.status_code == 200, "Login failed"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_backfill_endpoint_returns_200(self):
        """POST /api/accounting/backfill returns 200 OK"""
        response = requests.post(f"{BASE_URL}/api/accounting/backfill", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data
        assert "results" in data
        print(f"Backfill message: {data['message']}")
    
    def test_backfill_idempotency(self):
        """Backfill is idempotent - re-running creates 0 new entries"""
        response = requests.post(f"{BASE_URL}/api/accounting/backfill", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Since backfill already ran, should create 0 new entries
        results = data.get("results", {})
        invoices = results.get("invoices", {})
        payments = results.get("payments", {})
        credit_notes = results.get("credit_notes", {})
        
        total_created = invoices.get("created", 0) + payments.get("created", 0) + credit_notes.get("created", 0)
        assert total_created == 0, f"Expected 0 created, got {total_created}"
        
        # Verify skipped duplicates
        assert invoices.get("skipped_duplicate", 0) >= 0
        assert credit_notes.get("skipped_duplicate", 0) >= 0
        print(f"Invoices: {invoices.get('skipped_duplicate', 0)} skipped (already synced)")
        print(f"Credit Notes: {credit_notes.get('skipped_duplicate', 0)} skipped (already synced)")
    
    def test_backfill_requires_authentication(self):
        """Backfill without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/accounting/backfill")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_backfill_returns_accounting_start_date(self):
        """Backfill response includes accounting_start_date"""
        response = requests.post(f"{BASE_URL}/api/accounting/backfill", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "accounting_start_date" in data
        assert data["accounting_start_date"] == "2026-01-01"


class TestProfitLossAfterBackfill:
    """Test P&L Statement reflects backfilled transactions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pnl_shows_training_revenue(self):
        """P&L Statement shows Training Revenue RM 27,840"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/profit-loss?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "revenue" in data
        revenue_accounts = data["revenue"].get("accounts", [])
        revenue_total = data["revenue"].get("total", 0)
        
        # Find Training Revenue account (4000)
        training_revenue = next(
            (acc for acc in revenue_accounts if acc["account_code"] == "4000"),
            None
        )
        
        assert training_revenue is not None, "Training Revenue account (4000) not found"
        assert training_revenue["amount"] == 27840, f"Expected 27840, got {training_revenue['amount']}"
        assert revenue_total == 27840, f"Revenue total expected 27840, got {revenue_total}"
        print(f"Training Revenue: RM {training_revenue['amount']}")
    
    def test_pnl_shows_expenses(self):
        """P&L Statement shows expenses ~RM 3,103.65"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/profit-loss?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "expenses" in data
        expenses_total = data["expenses"].get("total", 0)
        assert abs(expenses_total - 3103.65) < 0.01, f"Expected ~3103.65, got {expenses_total}"
        print(f"Total Expenses: RM {expenses_total}")
    
    def test_pnl_no_deferred_revenue_for_paid_invoices(self):
        """Paid invoices should NOT be in Deferred Revenue (2300)"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/profit-loss?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Revenue should be in 4000 (Training Revenue), not 2300 (Deferred Revenue)
        revenue_accounts = data["revenue"].get("accounts", [])
        deferred_revenue = next(
            (acc for acc in revenue_accounts if acc["account_code"] == "2300"),
            None
        )
        assert deferred_revenue is None, "Deferred Revenue (2300) should not appear in P&L revenue"


class TestBalanceSheetAfterBackfill:
    """Test Balance Sheet reflects backfilled transactions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_balance_sheet_shows_accounts_receivable(self):
        """Balance Sheet shows Accounts Receivable (1100) with RM 27,840"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "assets" in data
        asset_accounts = data["assets"].get("accounts", [])
        
        # Find Accounts Receivable (1100)
        ar_account = next(
            (acc for acc in asset_accounts if acc["account_code"] == "1100"),
            None
        )
        
        assert ar_account is not None, "Accounts Receivable (1100) not found in assets"
        assert ar_account["balance"] == 27840, f"Expected AR 27840, got {ar_account['balance']}"
        print(f"Accounts Receivable (1100): RM {ar_account['balance']}")
    
    def test_balance_sheet_is_balanced(self):
        """Balance Sheet Total Assets = Total Liabilities + Equity"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("is_balanced") is True, "Balance sheet should be balanced"
        
        total_assets = data["assets"]["total"]
        total_liabilities_equity = data["total_liabilities_equity"]
        
        assert abs(total_assets - total_liabilities_equity) < 0.01, \
            f"Assets ({total_assets}) != Liab+Equity ({total_liabilities_equity})"
        print(f"Balance Sheet: Assets={total_assets}, Liab+Equity={total_liabilities_equity}, Balanced=True")
    
    def test_balance_sheet_current_year_earnings(self):
        """Balance Sheet Equity includes Current Year Earnings"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        equity = data.get("equity", {})
        current_year_earnings = equity.get("current_year_earnings", 0)
        
        # Net Profit = Revenue - Expenses = 27840 - 3103.65 = 24736.35
        expected_earnings = 24736.35
        assert abs(current_year_earnings - expected_earnings) < 0.01, \
            f"Expected Current Year Earnings ~{expected_earnings}, got {current_year_earnings}"
        print(f"Current Year Earnings: RM {current_year_earnings}")


class TestAccountingRegressionCheck:
    """Regression tests for other accounting endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_chart_of_accounts_accessible(self):
        """GET /api/accounting/chart-of-accounts returns accounts"""
        response = requests.get(f"{BASE_URL}/api/accounting/chart-of-accounts", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert len(data["accounts"]) > 0
        print(f"Chart of Accounts: {len(data['accounts'])} accounts")
    
    def test_trial_balance_accessible(self):
        """GET /api/accounting/trial-balance returns balanced data"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/trial-balance?year=2026&month=3",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert data["totals"]["is_balanced"] is True
        print(f"Trial Balance: DR={data['totals']['total_debit']}, CR={data['totals']['total_credit']}")
    
    def test_journal_entries_accessible(self):
        """GET /api/accounting/journal-entries returns entries"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/journal-entries?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        print(f"Journal Entries: {len(data['entries'])} entries")
    
    def test_general_ledger_accessible(self):
        """GET /api/accounting/general-ledger/{account} returns ledger"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/general-ledger/1100?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "account" in data
        assert "entries" in data
        print(f"General Ledger 1100 (AR): {len(data['entries'])} entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
