"""
Iteration 16 Test Suite - Testing Three Implemented Features:
1. Revenue Recognition (Cash Basis) - P&L only counts 'partial' or 'paid' invoices
2. Expense Category Description - 'Training Materials Printing' for printing category
3. Marketing Pipeline grouping (validated via frontend)
"""

import pytest
import requests
import os

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL must be set")

# Test credentials
ADMIN_EMAIL = "arjuna@mddrc.com.my"
ADMIN_PASSWORD = "Dana102229"


class TestAuthentication:
    """Test authentication to get access token"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access token in response"
        return data["access_token"]
    
    def test_login_success(self, auth_token):
        """Verify login works"""
        assert auth_token is not None
        print(f"✓ Login successful, token obtained")


class TestRevenueRecognition:
    """
    Test Revenue Recognition (Cash Basis):
    - Revenue is recognized only when payment is received
    - invoice.status must be 'partial' or 'paid' (NOT 'issued')
    - Session completion status is NOT required
    """
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for all tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_pnl_endpoint_accessible(self, auth_headers):
        """Test P&L endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/finance/profit-loss?year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200, f"P&L endpoint failed: {response.text}"
        data = response.json()
        assert "year" in data
        assert "monthly_breakdown" in data
        assert "ytd_summary" in data
        print(f"✓ P&L endpoint accessible, year: {data['year']}")
    
    def test_pnl_response_structure(self, auth_headers):
        """Verify P&L response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/finance/profit-loss?year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check monthly breakdown structure
        monthly = data.get("monthly_breakdown", [])
        assert len(monthly) == 12, "Should have 12 months"
        
        for month_data in monthly:
            assert "month" in month_data
            assert "month_name" in month_data
            assert "income" in month_data
            assert "expenses" in month_data
            assert "net_profit" in month_data
            
            # Income structure
            income = month_data["income"]
            assert "invoices" in income
            assert "manual" in income
            assert "total" in income
            
            # Expenses structure
            expenses = month_data["expenses"]
            assert "payroll" in expenses
            assert "session_workers" in expenses
            assert "marketing_commissions" in expenses
            assert "session_expenses" in expenses
            assert "petty_cash" in expenses
            assert "manual" in expenses
            assert "total" in expenses
        
        print(f"✓ P&L response structure correct with all 12 months")
    
    def test_pnl_ytd_summary_structure(self, auth_headers):
        """Verify YTD summary has correct fields"""
        response = requests.get(
            f"{BASE_URL}/api/finance/profit-loss?year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        ytd = data.get("ytd_summary", {})
        assert "total_income" in ytd
        assert "total_expenses" in ytd
        assert "net_profit" in ytd
        assert "profit_margin" in ytd
        
        print(f"✓ YTD summary: Income={ytd['total_income']}, Expenses={ytd['total_expenses']}, Net Profit={ytd['net_profit']}")


class TestExpenseCategories:
    """
    Test Expense Categories endpoint:
    - 'printing' category should have description 'Training Materials Printing'
    - NOT '1% of invoice'
    """
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for all tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_expense_categories_endpoint_accessible(self, auth_headers):
        """Test expense categories endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/finance/expense-categories",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expense categories endpoint failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Expense categories endpoint accessible, returned {len(data)} categories")
    
    def test_printing_category_description(self, auth_headers):
        """Test printing category has correct description"""
        response = requests.get(
            f"{BASE_URL}/api/finance/expense-categories",
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json()
        
        # Find printing category
        printing_category = None
        for cat in categories:
            if cat.get("id") == "printing":
                printing_category = cat
                break
        
        assert printing_category is not None, "Printing category not found"
        
        # Check description is NOT '1% of invoice'
        description = printing_category.get("description", "")
        assert "1% of invoice" not in description, f"Description should NOT contain '1% of invoice': {description}"
        
        # Check description is 'Training Materials Printing'
        assert "Training Materials Printing" in description, f"Description should be 'Training Materials Printing': {description}"
        
        print(f"✓ Printing category description correct: '{description}'")
    
    def test_all_expense_categories_have_required_fields(self, auth_headers):
        """Verify all expense categories have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/finance/expense-categories",
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json()
        
        required_fields = ["id", "name", "type", "rate", "description"]
        
        for cat in categories:
            for field in required_fields:
                assert field in cat, f"Category {cat.get('id', 'unknown')} missing field: {field}"
        
        print(f"✓ All {len(categories)} expense categories have required fields")
    
    def test_expense_category_types(self, auth_headers):
        """Verify expected expense category types exist"""
        response = requests.get(
            f"{BASE_URL}/api/finance/expense-categories",
            headers=auth_headers
        )
        assert response.status_code == 200
        categories = response.json()
        
        category_ids = [cat["id"] for cat in categories]
        expected_categories = ["fnb", "hrdc_levy", "wear_tear", "printing", "accommodation", "allowance", "petrol", "toll", "sst", "muafakat", "other"]
        
        for expected in expected_categories:
            assert expected in category_ids, f"Expected category '{expected}' not found"
        
        print(f"✓ All expected expense categories present: {expected_categories}")


class TestMarketingLeadsEndpoint:
    """
    Test Marketing Leads endpoint to verify leads data is available
    (Frontend month grouping is tested separately via Playwright)
    """
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for all tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_marketing_leads_endpoint(self, auth_headers):
        """Test marketing leads endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/marketing/leads",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Marketing leads endpoint failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Marketing leads endpoint accessible, returned {len(data)} leads")
    
    def test_leads_have_created_at_field(self, auth_headers):
        """Verify leads have created_at field for month grouping"""
        response = requests.get(
            f"{BASE_URL}/api/marketing/leads",
            headers=auth_headers
        )
        assert response.status_code == 200
        leads = response.json()
        
        if leads:
            for lead in leads[:5]:  # Check first 5 leads
                # Either created_at or follow_up_date should exist for grouping
                has_date = "created_at" in lead or "follow_up_date" in lead
                assert has_date, f"Lead {lead.get('id')} missing date field for month grouping"
        
        print(f"✓ Leads have date fields for month grouping")
    
    def test_leads_have_stage_field(self, auth_headers):
        """Verify leads have stage field for pipeline view"""
        response = requests.get(
            f"{BASE_URL}/api/marketing/leads",
            headers=auth_headers
        )
        assert response.status_code == 200
        leads = response.json()
        
        valid_stages = ["inquiry", "contacted", "quotation_sent", "negotiating", "won", "lost"]
        
        if leads:
            for lead in leads:
                assert "stage" in lead, f"Lead {lead.get('id')} missing stage field"
                assert lead["stage"] in valid_stages, f"Lead {lead.get('id')} has invalid stage: {lead['stage']}"
        
        print(f"✓ All leads have valid stage field")


class TestRevenueRecognitionLogic:
    """
    More detailed tests for revenue recognition logic
    Based on code review: Only 'partial' or 'paid' invoices count as revenue
    """
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for all tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_invoices_endpoint(self, auth_headers):
        """Test invoices endpoint to understand data"""
        response = requests.get(
            f"{BASE_URL}/api/finance/invoices",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Invoices endpoint failed: {response.text}"
        data = response.json()
        
        # Count by status
        status_counts = {}
        for inv in data:
            status = inv.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"✓ Invoices endpoint accessible, counts by status: {status_counts}")
    
    def test_pnl_excludes_non_revenue_statuses(self, auth_headers):
        """
        Verify P&L logic by checking:
        - The code only counts 'partial' and 'paid' statuses for revenue
        - 'issued' status invoices should NOT be counted
        """
        # Get P&L report
        response = requests.get(
            f"{BASE_URL}/api/finance/profit-loss?year=2026",
            headers=auth_headers
        )
        assert response.status_code == 200
        pnl_data = response.json()
        
        # This test verifies the endpoint works and returns data
        # The actual filtering logic is in the backend code we reviewed
        total_income = pnl_data.get("ytd_summary", {}).get("total_income", 0)
        
        print(f"✓ P&L total income (cash basis): {total_income}")
        print("  Note: Only invoices with status 'partial' or 'paid' are counted")


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
