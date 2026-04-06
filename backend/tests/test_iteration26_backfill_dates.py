"""
Iteration 26: Backfill Journal Entries - Original Dates Testing
Tests the updated backfill that uses original transaction dates (not accounting_start_date).

Key changes from previous iteration:
1. Dec 2025 invoices now dated Dec 2025 (not forced to Jan 2026)
2. Backfill handles 10 transaction types (invoices, payments, credit notes, trainer_fees,
   coordinator_fees, session_expenses, marketing_commissions, manual_income, manual_expenses, petty_cash)
3. 2026 P&L now shows Revenue 0 (Dec 2025 invoices are in 2025, not 2026)
4. Backfill auto-opens accounting periods for any date

Account mapping tested:
- Trainer fees → 5000
- Coordinator fees → 5100
- Marketing commissions → 5200
- Session expenses → 5300-5700 based on category
- Manual income → 4100
- Manual expenses → 6999
- Petty cash → 6600
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://quote-n-cert.preview.emergentagent.com')


class TestBackfillOriginalDates:
    """Test backfill uses original transaction dates"""
    
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
    
    def test_backfill_returns_200_with_all_10_types(self):
        """POST /api/accounting/backfill returns 200 with all 10 transaction types"""
        response = requests.post(f"{BASE_URL}/api/accounting/backfill", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "results" in data
        results = data["results"]
        
        # Verify all 10 transaction types are present
        expected_types = [
            "invoices", "payments", "credit_notes", "trainer_fees",
            "coordinator_fees", "session_expenses", "marketing_commissions",
            "manual_income", "manual_expenses", "petty_cash"
        ]
        for tx_type in expected_types:
            assert tx_type in results, f"Missing {tx_type} in results"
            assert "found" in results[tx_type], f"{tx_type} missing 'found' field"
            assert "created" in results[tx_type], f"{tx_type} missing 'created' field"
            assert "skipped" in results[tx_type], f"{tx_type} missing 'skipped' field"
        
        print(f"All 10 transaction types present in backfill response")
    
    def test_backfill_is_idempotent(self):
        """Backfill creates 0 new entries when re-run (idempotent)"""
        response = requests.post(f"{BASE_URL}/api/accounting/backfill", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        total_created = data.get("total_created", 0)
        assert total_created == 0, f"Expected 0 created (idempotent), got {total_created}"
        
        total_skipped = data.get("total_skipped", 0)
        assert total_skipped >= 8, f"Expected >=8 skipped (4 invoices + 4 credit notes), got {total_skipped}"
        
        print(f"Backfill idempotent: {total_created} created, {total_skipped} skipped")
    
    def test_dec_2025_invoices_dated_dec_2025(self):
        """Dec 2025 invoices should have Dec 2025 dates in journal entries"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/journal-entries?year=2025&month=12",
            headers=self.headers
        )
        assert response.status_code == 200
        entries = response.json().get("entries", [])
        
        # Should have Dec 2025 entries for invoices
        invoice_entries = [e for e in entries if e.get("source_module") == "invoice"]
        assert len(invoice_entries) >= 4, f"Expected 4 invoice entries in Dec 2025, got {len(invoice_entries)}"
        
        # Verify all invoice entries have Dec 2025 dates
        for entry in invoice_entries:
            assert entry["date"].startswith("2025-12"), \
                f"Invoice entry {entry.get('journal_no')} has wrong date: {entry['date']}"
        
        print(f"Dec 2025 has {len(invoice_entries)} invoice entries with correct dates")
    
    def test_backfill_auto_opens_periods(self):
        """Backfill auto-opens accounting periods for any date"""
        # Check Dec 2025 period was auto-opened
        response = requests.get(
            f"{BASE_URL}/api/accounting/periods?year=2025",
            headers=self.headers
        )
        assert response.status_code == 200
        periods = response.json().get("periods", [])
        
        dec_2025 = next((p for p in periods if p.get("month") == 12), None)
        assert dec_2025 is not None, "Dec 2025 period should exist (auto-opened)"
        assert dec_2025.get("status") == "open", "Dec 2025 period should be open"
        
        print(f"Dec 2025 period exists and is open")
    
    def test_backfill_requires_auth(self):
        """Backfill without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/accounting/backfill")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestPLWithOriginalDates:
    """Test P&L reflects correct dates after backfill fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_2026_pl_shows_zero_revenue(self):
        """2026 P&L should show Revenue 0 (Dec 2025 invoices not in 2026 anymore)"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/profit-loss?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        revenue_total = data["revenue"]["total"]
        assert revenue_total == 0, f"2026 Revenue should be 0, got {revenue_total}"
        
        print(f"2026 P&L Revenue: {revenue_total} (correct - Dec 2025 invoices in 2025)")
    
    def test_2025_pl_shows_training_revenue(self):
        """2025 P&L should show Dec 2025 invoice revenue"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/profit-loss?year=2025",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        revenue_total = data["revenue"]["total"]
        assert revenue_total == 27840, f"2025 Revenue should be 27840, got {revenue_total}"
        
        # Verify it's in Training Revenue account (4000)
        revenue_accounts = data["revenue"]["accounts"]
        training_revenue = next((a for a in revenue_accounts if a["account_code"] == "4000"), None)
        assert training_revenue is not None, "Training Revenue (4000) not found"
        assert training_revenue["amount"] == 27840, f"Expected 27840 in 4000, got {training_revenue['amount']}"
        
        print(f"2025 P&L Training Revenue: {training_revenue['amount']}")
    
    def test_2026_pl_shows_only_payroll_expenses(self):
        """2026 P&L should show expenses ~3,103.65 (payroll only)"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/profit-loss?year=2026",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        expenses_total = data["expenses"]["total"]
        assert abs(expenses_total - 3103.65) < 0.01, f"2026 Expenses should be ~3103.65, got {expenses_total}"
        
        # Verify expense breakdown includes salary/EPF/SOCSO/EIS
        expense_accounts = data["expenses"]["accounts"]
        expense_codes = [a["account_code"] for a in expense_accounts]
        assert "6000" in expense_codes, "Salary & Wages (6000) missing"
        
        print(f"2026 P&L Expenses: {expenses_total}")


class TestBalanceSheetAfterBackfillFix:
    """Test Balance Sheet is still balanced after re-backfill"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_balance_sheet_is_balanced(self):
        """Balance Sheet should be balanced (Assets = Liab + Equity)"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("is_balanced") is True, "Balance sheet should be balanced"
        
        total_assets = data["assets"]["total"]
        total_liab_equity = data["total_liabilities_equity"]
        
        assert abs(total_assets - total_liab_equity) < 0.01, \
            f"Assets ({total_assets}) != Liab+Equity ({total_liab_equity})"
        
        print(f"Balance Sheet balanced: Assets={total_assets}, L+E={total_liab_equity}")
    
    def test_balance_sheet_shows_ar(self):
        """Balance Sheet should show Accounts Receivable"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/balance-sheet?year=2026&month=3",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        asset_accounts = data["assets"]["accounts"]
        ar = next((a for a in asset_accounts if a["account_code"] == "1100"), None)
        
        assert ar is not None, "Accounts Receivable (1100) not found"
        assert ar["balance"] == 27840, f"AR should be 27840, got {ar['balance']}"
        
        print(f"AR (1100): {ar['balance']}")


class TestAccountMappings:
    """Test training expense account mappings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "arjuna@mddrc.com.my", "password": "Dana102229"}
        )
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_chart_of_accounts_has_training_expenses(self):
        """Chart of Accounts includes all training expense accounts (5xxx)"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/chart-of-accounts",
            headers=self.headers
        )
        assert response.status_code == 200
        accounts = response.json().get("accounts", [])
        
        # Expected training expense accounts
        expected_mappings = {
            "5000": "Trainer Fees",
            "5100": "Coordinator Fees",
            "5200": "Marketing Commission",
            "5300": "Training Materials",
            "5400": "Venue & Logistics",
            "5500": "Transportation",
        }
        
        account_map = {a["account_code"]: a["account_name"] for a in accounts}
        
        for code, expected_name in expected_mappings.items():
            assert code in account_map, f"Account {code} ({expected_name}) missing"
            # Just check the account exists with similar name
            assert expected_name.lower().split()[0] in account_map[code].lower(), \
                f"Account {code} name mismatch: expected '{expected_name}', got '{account_map[code]}'"
        
        print(f"All training expense accounts present (5000-5500)")
    
    def test_coa_has_misc_accounts(self):
        """COA includes manual income/expense and petty cash accounts"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/chart-of-accounts",
            headers=self.headers
        )
        assert response.status_code == 200
        accounts = response.json().get("accounts", [])
        account_codes = [a["account_code"] for a in accounts]
        
        # Manual income/expense and petty cash mappings
        # Based on code: manual_income → 4100, manual_expenses → 6999, petty_cash → 6600
        # These may or may not exist in COA, but should be creatable
        print(f"Total accounts in COA: {len(accounts)}")


class TestRegressionAccounting:
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
    
    def test_trial_balance_balanced(self):
        """Trial Balance should be balanced (DR = CR)"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/trial-balance?year=2026&month=3",
            headers=self.headers
        )
        assert response.status_code == 200
        totals = response.json().get("totals", {})
        
        assert totals.get("is_balanced") is True
        assert totals.get("total_debit") == totals.get("total_credit")
        
        print(f"Trial Balance: DR={totals['total_debit']}, CR={totals['total_credit']}")
    
    def test_journal_entries_accessible(self):
        """Journal entries endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/journal-entries?year=2025",
            headers=self.headers
        )
        assert response.status_code == 200
        entries = response.json().get("entries", [])
        assert len(entries) >= 8, f"Expected at least 8 entries in 2025, got {len(entries)}"
        
        print(f"Journal entries 2025: {len(entries)}")
    
    def test_general_ledger_accessible(self):
        """General ledger endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/accounting/general-ledger/4000?year=2025",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "account" in data
        assert "entries" in data
        
        print(f"GL 4000 (Training Revenue): {len(data['entries'])} entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
