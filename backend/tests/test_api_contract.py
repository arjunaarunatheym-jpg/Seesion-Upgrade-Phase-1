"""
API CONTRACT TEST - REFACTORING SAFETY NET
==========================================
Run this BEFORE and AFTER any backend refactoring.

Purpose:
- Ensures all 307 API endpoints remain accessible at the EXACT same URLs
- Catches routing mistakes (like duplicate prefixes, typos, etc.)
- Does NOT test authentication or business logic - only that routes EXIST

Usage:
    # Before refactoring - save baseline
    python -m pytest tests/test_api_contract.py -v
    
    # After refactoring - verify nothing broke
    python -m pytest tests/test_api_contract.py -v

If ANY test fails after refactoring with 404, STOP and ROLLBACK immediately.
"""

import pytest
import httpx
import asyncio
from typing import List, Tuple

# Base URL for testing
BASE_URL = "http://localhost:8001"

# All 307 endpoints extracted from server.py
# Format: (HTTP_METHOD, PATH)
ALL_ENDPOINTS: List[Tuple[str, str]] = [
    # Root
    ("GET", "/api/"),
    ("GET", "/health"),
    
    # Auth endpoints
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/forgot-password"),
    ("POST", "/api/auth/change-password"),
    ("POST", "/api/auth/reset-password"),
    
    # Companies
    ("POST", "/api/companies"),
    ("GET", "/api/companies"),
    ("PUT", "/api/companies/{company_id}"),
    ("DELETE", "/api/companies/{company_id}"),
    
    # Programs
    ("POST", "/api/programs"),
    ("GET", "/api/programs"),
    ("PUT", "/api/programs/{program_id}"),
    ("DELETE", "/api/programs/{program_id}"),
    
    # Sessions
    ("GET", "/api/sessions"),
    ("POST", "/api/sessions"),
    ("GET", "/api/sessions/calendar"),
    ("GET", "/api/sessions/past-training"),
    ("GET", "/api/sessions/{session_id}"),
    ("PUT", "/api/sessions/{session_id}"),
    ("DELETE", "/api/sessions/{session_id}"),
    ("PUT", "/api/sessions/{session_id}/toggle-status"),
    ("POST", "/api/sessions/{session_id}/mark-completed"),
    ("GET", "/api/sessions/{session_id}/participants"),
    ("POST", "/api/sessions/{session_id}/participants"),
    ("POST", "/api/sessions/{session_id}/participants/bulk-upload"),
    ("GET", "/api/sessions/{session_id}/participants/attendance"),
    ("GET", "/api/sessions/{session_id}/participants/enriched"),
    ("POST", "/api/sessions/{session_id}/participants/{participant_id}/attendance"),
    ("GET", "/api/sessions/{session_id}/results-summary"),
    ("GET", "/api/sessions/{session_id}/status"),
    ("GET", "/api/sessions/{session_id}/completion-checklist"),
    ("GET", "/api/sessions/{session_id}/indemnity-records"),
    ("GET", "/api/sessions/{session_id}/indemnity-records/export"),
    ("POST", "/api/sessions/{session_id}/release-pre-test"),
    ("POST", "/api/sessions/{session_id}/release-post-test"),
    ("POST", "/api/sessions/{session_id}/release-feedback"),
    ("GET", "/api/sessions/{session_id}/tests/available"),
    ("DELETE", "/api/sessions/bulk/delete-all"),
    
    # Users
    ("GET", "/api/users"),
    ("POST", "/api/users/check-exists"),
    ("GET", "/api/users/export/participants"),
    ("GET", "/api/users/{user_id}"),
    ("PUT", "/api/users/{user_id}"),
    ("DELETE", "/api/users/{user_id}"),
    ("PUT", "/api/users/profile"),
    
    # Attendance
    ("GET", "/api/attendance/session/{session_id}"),
    ("GET", "/api/attendance/{session_id}/{participant_id}"),
    ("POST", "/api/attendance/clock-in"),
    ("POST", "/api/attendance/clock-out"),
    
    # Tests
    ("POST", "/api/tests"),
    ("POST", "/api/tests/bulk-upload"),
    ("GET", "/api/tests/program/{program_id}"),
    ("GET", "/api/tests/{test_id}"),
    ("DELETE", "/api/tests/{test_id}"),
    ("POST", "/api/tests/submit"),
    ("POST", "/api/tests/super-admin-submit"),
    ("GET", "/api/tests/results/session/{session_id}"),
    ("GET", "/api/tests/results/participant/{participant_id}"),
    ("GET", "/api/tests/results/{result_id}"),
    ("PUT", "/api/tests/results/{result_id}"),
    
    # Certificates
    ("GET", "/api/certificates/session/{session_id}"),
    ("GET", "/api/certificates/repository"),
    ("GET", "/api/certificates/participant/{participant_id}"),
    ("GET", "/api/certificates/my-certificates"),
    ("GET", "/api/certificates/eligibility/{session_id}/{participant_id}"),
    ("POST", "/api/certificates/generate/{session_id}/{participant_id}"),
    ("POST", "/api/certificates/upload/{session_id}/{participant_id}"),
    ("GET", "/api/certificates/download/{certificate_id}"),
    ("GET", "/api/certificates/download/{session_id}/{participant_id}"),
    ("GET", "/api/certificates/preview/{certificate_id}"),
    
    # Checklists
    ("GET", "/api/checklist-templates"),
    ("POST", "/api/checklist-templates"),
    ("GET", "/api/checklist-templates/program/{program_id}"),
    ("PUT", "/api/checklist-templates/{template_id}"),
    ("DELETE", "/api/checklist-templates/{template_id}"),
    ("DELETE", "/api/checklist-templates/{template_id}/items/{item_index}"),
    ("POST", "/api/checklist-templates/bulk-upload"),
    ("GET", "/api/checklists/session/{session_id}"),
    ("GET", "/api/checklists/pending"),
    ("GET", "/api/checklists/participant/{participant_id}"),
    ("POST", "/api/checklists/submit"),
    ("POST", "/api/checklists/verify"),
    ("GET", "/api/checklists/templates"),
    ("GET", "/api/checklists/templates/program/{program_id}"),
    ("POST", "/api/checklist-photos/upload"),
    
    # Feedback
    ("GET", "/api/feedback-templates/program/{program_id}"),
    ("POST", "/api/feedback-templates"),
    ("DELETE", "/api/feedback-templates/{template_id}"),
    ("POST", "/api/feedback-templates/bulk-upload"),
    ("GET", "/api/feedback/session/{session_id}"),
    ("GET", "/api/feedback/company/{company_id}"),
    ("GET", "/api/feedback/templates/program/{program_id}"),
    ("POST", "/api/feedback/submit"),
    ("GET", "/api/chief-trainer-feedback-template"),
    ("PUT", "/api/chief-trainer-feedback-template"),
    ("GET", "/api/chief-trainer-feedback/{session_id}"),
    ("POST", "/api/chief-trainer-feedback/{session_id}"),
    ("GET", "/api/coordinator-feedback-template"),
    ("PUT", "/api/coordinator-feedback-template"),
    ("GET", "/api/coordinator-feedback/{session_id}"),
    ("POST", "/api/coordinator-feedback/{session_id}"),
    
    # Reports & Training Reports
    ("POST", "/api/reports/generate"),
    ("GET", "/api/reports/session/{session_id}"),
    ("PUT", "/api/reports/{report_id}"),
    ("POST", "/api/reports/{report_id}/publish"),
    ("GET", "/api/training-reports/{session_id}"),
    ("POST", "/api/training-reports"),
    ("GET", "/api/training-reports/admin/all"),
    ("GET", "/api/training-reports/coordinator/{coordinator_id}"),
    ("GET", "/api/training-reports/supervisor/sessions"),
    ("POST", "/api/training-reports/{session_id}/generate-ai-report"),
    ("POST", "/api/training-reports/{session_id}/generate-docx"),
    ("POST", "/api/training-reports/{session_id}/upload-edited-docx"),
    ("POST", "/api/training-reports/{session_id}/upload-final-pdf"),
    ("POST", "/api/training-reports/{session_id}/submit-final"),
    ("GET", "/api/training-reports/{session_id}/download-docx"),
    ("GET", "/api/training-reports/{session_id}/download-pdf"),
    
    # Settings
    ("GET", "/api/settings"),
    ("PUT", "/api/settings"),
    ("POST", "/api/settings/upload-logo"),
    ("POST", "/api/settings/upload-certificate-template"),
    
    # Templates
    ("GET", "/api/templates/checklist"),
    ("GET", "/api/templates/feedback"),
    ("GET", "/api/templates/pre-post-assessment"),
    ("GET", "/api/templates/program-checklist-items"),
    ("GET", "/api/templates/program-feedback-questions"),
    ("GET", "/api/templates/program-test-questions"),
    
    # Participant Access
    ("GET", "/api/participant-access/session/{session_id}"),
    ("GET", "/api/participant-access/{session_id}"),
    ("POST", "/api/participant-access/session/{session_id}/toggle"),
    ("POST", "/api/participant-access/update"),
    
    # Vehicle Details & Checklists
    ("GET", "/api/vehicle-details/{session_id}/{participant_id}"),
    ("POST", "/api/vehicle-details/submit"),
    ("GET", "/api/vehicle-checklists/{session_id}/{participant_id}"),
    
    # Supervisor
    ("GET", "/api/supervisor/sessions"),
    ("GET", "/api/supervisor/attendance/{session_id}"),
    
    # Trainer Checklist
    ("GET", "/api/trainer-checklist/{session_id}/assigned-participants"),
    ("POST", "/api/trainer-checklist/submit"),
    
    # Super Admin (Quick Testing)
    ("POST", "/api/super-admin/attendance/clock-in"),
    ("POST", "/api/super-admin/attendance/clock-out"),
    ("POST", "/api/super-admin/checklist/submit"),
    ("POST", "/api/super-admin/feedback/submit"),
    ("POST", "/api/super-admin/vehicle-details"),
    
    # Finance - Billing Parties
    ("POST", "/api/finance/billing-parties"),
    ("GET", "/api/finance/billing-parties"),
    ("PUT", "/api/finance/billing-parties/{party_id}"),
    ("DELETE", "/api/finance/billing-parties/{party_id}"),
    
    # Finance - Dashboard & Settings
    ("GET", "/api/finance/dashboard"),
    ("GET", "/api/finance/company-settings"),
    ("PUT", "/api/finance/company-settings"),
    ("POST", "/api/finance/company-settings/upload-logo"),
    ("POST", "/api/finance/company-settings/upload-indemnity-form"),
    
    # Finance - Invoices
    ("GET", "/api/finance/invoices"),
    ("GET", "/api/finance/invoices/export"),
    ("GET", "/api/finance/invoices/{invoice_id}"),
    ("PUT", "/api/finance/invoices/{invoice_id}"),
    ("POST", "/api/finance/invoices/{invoice_id}/approve"),
    ("POST", "/api/finance/invoices/{invoice_id}/issue"),
    ("POST", "/api/finance/invoices/{invoice_id}/cancel"),
    ("POST", "/api/finance/invoices/{invoice_id}/create-replacement"),
    ("POST", "/api/finance/invoices/{invoice_id}/reverse-void"),
    
    # Finance - Admin Invoice Operations
    ("GET", "/api/finance/admin/invoices"),
    ("POST", "/api/finance/admin/invoices/{invoice_id}/void"),
    ("PUT", "/api/finance/admin/invoices/{invoice_id}/number"),
    ("PUT", "/api/finance/admin/invoices/{invoice_id}/backdate"),
    ("PUT", "/api/finance/admin/invoices/{invoice_id}/edit-paid"),
    ("PUT", "/api/finance/admin/invoices/{invoice_id}/override"),
    ("POST", "/api/finance/admin/sequence/reset"),
    
    # Finance - Credit Notes
    ("GET", "/api/finance/credit-notes"),
    ("POST", "/api/finance/credit-notes"),
    ("GET", "/api/finance/credit-notes/{cn_id}"),
    ("PUT", "/api/finance/credit-notes/{cn_id}"),
    ("POST", "/api/finance/credit-notes/{cn_id}/approve"),
    ("POST", "/api/finance/credit-notes/{cn_id}/issue"),
    ("PUT", "/api/finance/admin/credit-notes/{cn_id}/number"),
    ("PUT", "/api/finance/admin/credit-notes/{cn_id}/backdate"),
    ("PUT", "/api/finance/admin/credit-notes/{cn_id}/edit"),
    ("PUT", "/api/finance/admin/credit-notes/{cn_id}/void"),
    
    # Finance - Payments
    ("GET", "/api/finance/payments"),
    ("POST", "/api/finance/payments"),
    ("GET", "/api/finance/payments/{payment_id}/receipt"),
    ("GET", "/api/finance/admin/payments"),
    ("DELETE", "/api/finance/admin/payments/{payment_id}"),
    
    # Finance - Session Costing
    ("GET", "/api/finance/session/{session_id}/costing"),
    ("POST", "/api/finance/session/{session_id}/expenses"),
    ("DELETE", "/api/finance/session/{session_id}/expense/{expense_id}"),
    ("POST", "/api/finance/session/{session_id}/invoice"),
    ("POST", "/api/finance/session/{session_id}/credit-note"),
    ("POST", "/api/finance/session/{session_id}/trainer-fees"),
    ("POST", "/api/finance/session/{session_id}/coordinator-fee"),
    ("POST", "/api/finance/session/{session_id}/marketing"),
    ("POST", "/api/finance/session/{session_id}/calculate-profit"),
    ("GET", "/api/finance/session/{session_id}/payables-report"),
    
    # Finance - Payables
    ("GET", "/api/finance/payables/trainer-fees"),
    ("GET", "/api/finance/payables/coordinator-fees"),
    ("GET", "/api/finance/payables/marketing-commissions"),
    ("POST", "/api/finance/trainer-fees/{fee_id}/mark-paid"),
    ("POST", "/api/finance/coordinator-fees/{fee_id}/mark-paid"),
    ("GET", "/api/finance/payables/periods"),
    ("POST", "/api/finance/payables/periods"),
    ("POST", "/api/finance/payables/periods/{period_id}/close"),
    ("POST", "/api/finance/payables/periods/{period_id}/reopen"),
    ("GET", "/api/finance/payables/period-status"),
    ("GET", "/api/finance/payables/export-excel"),
    
    # Finance - Income Tracking
    ("GET", "/api/finance/income/trainer/{trainer_id}"),
    ("GET", "/api/finance/income/coordinator/{coordinator_id}"),
    ("GET", "/api/finance/income/marketing/{marketing_id}"),
    ("POST", "/api/finance/income/trainer/{record_id}/mark-paid"),
    ("POST", "/api/finance/income/coordinator/{record_id}/mark-paid"),
    ("POST", "/api/finance/income/commission/{record_id}/mark-paid"),
    
    # Finance - Manual Entries
    ("GET", "/api/finance/manual-expenses"),
    ("POST", "/api/finance/manual-expense"),
    ("DELETE", "/api/finance/manual-expense/{entry_id}"),
    ("GET", "/api/finance/manual-income"),
    ("POST", "/api/finance/manual-income"),
    ("DELETE", "/api/finance/manual-income/{entry_id}"),
    
    # Finance - Reports & Ledgers
    ("GET", "/api/finance/profit-loss"),
    ("GET", "/api/finance/profit-loss/by-programme"),
    ("GET", "/api/finance/general-ledger"),
    ("GET", "/api/finance/chart-of-accounts"),
    ("GET", "/api/finance/expense-categories"),
    ("GET", "/api/finance/audit-log"),
    ("GET", "/api/finance/subledger/trainers"),
    ("GET", "/api/finance/subledger/marketing"),
    ("GET", "/api/finance/subledger/payroll"),
    ("GET", "/api/finance/marketing-users"),
    
    # Finance - Petty Cash
    ("GET", "/api/finance/petty-cash/settings"),
    ("POST", "/api/finance/petty-cash/setup"),
    ("GET", "/api/finance/petty-cash/transactions"),
    ("POST", "/api/finance/petty-cash/transaction"),
    ("DELETE", "/api/finance/petty-cash/transaction/{transaction_id}"),
    ("POST", "/api/finance/petty-cash/approve/{transaction_id}"),
    ("POST", "/api/finance/petty-cash/reject/{transaction_id}"),
    ("GET", "/api/finance/petty-cash/summary"),
    ("POST", "/api/finance/petty-cash/reconcile"),
    ("GET", "/api/finance/petty-cash/reconciliations"),
    
    # Finance - Audit
    ("GET", "/api/finance/admin/audit-trail"),
    ("GET", "/api/finance/admin/audit-trail/export"),
    
    # HR Module
    ("GET", "/api/hr/staff"),
    ("POST", "/api/hr/staff"),
    ("PUT", "/api/hr/staff/{staff_id}"),
    ("DELETE", "/api/hr/staff/{staff_id}"),
    ("GET", "/api/hr/available-users"),
    ("GET", "/api/hr/payroll-periods"),
    ("POST", "/api/hr/payroll-periods"),
    ("PUT", "/api/hr/payroll-periods/{period_id}/close"),
    ("GET", "/api/hr/payslips"),
    ("POST", "/api/hr/payslips/generate"),
    ("GET", "/api/hr/payslips/{payslip_id}"),
    ("DELETE", "/api/hr/payslips/{payslip_id}"),
    ("GET", "/api/hr/my-payslips"),
    ("GET", "/api/hr/pay-advice"),
    ("POST", "/api/hr/pay-advice/generate"),
    ("POST", "/api/hr/pay-advice/bulk-generate"),
    ("GET", "/api/hr/pay-advice/{advice_id}"),
    ("DELETE", "/api/hr/pay-advice/{advice_id}"),
    ("POST", "/api/hr/pay-advice/{advice_id}/lock"),
    ("POST", "/api/hr/pay-advice/{advice_id}/unlock"),
    ("POST", "/api/hr/pay-advice/bulk-lock"),
    ("GET", "/api/hr/my-pay-advice"),
    ("GET", "/api/hr/statutory-rates"),
    ("POST", "/api/hr/statutory-rates/upload"),
    ("GET", "/api/hr/statutory-rates/templates/{rate_type}"),
    ("GET", "/api/hr/ea-form/{staff_id}/{year}"),
    ("GET", "/api/hr/my-ea-form/{year}"),
    
    # Marketing Module
    ("GET", "/api/marketing/clients"),
    ("GET", "/api/marketing/clients/all"),
    ("POST", "/api/marketing/clients"),
    ("PUT", "/api/marketing/clients/{client_id}"),
    ("DELETE", "/api/marketing/clients/{client_id}"),
    ("GET", "/api/marketing/clients/export"),
    ("GET", "/api/marketing/description-items"),
    ("GET", "/api/marketing/description-items/all"),
    ("POST", "/api/marketing/description-items"),
    ("PUT", "/api/marketing/description-items/{item_id}"),
    ("DELETE", "/api/marketing/description-items/{item_id}"),
    ("GET", "/api/marketing/quotations"),
    ("POST", "/api/marketing/quotations"),
    ("GET", "/api/marketing/quotations/{quotation_id}"),
    ("PUT", "/api/marketing/quotations/{quotation_id}"),
    ("POST", "/api/marketing/quotations/{quotation_id}/submit"),
    ("POST", "/api/marketing/quotations/{quotation_id}/approve"),
    ("POST", "/api/marketing/quotations/{quotation_id}/reject"),
    ("POST", "/api/marketing/quotations/{quotation_id}/mark-sent"),
    ("POST", "/api/marketing/quotations/{quotation_id}/client-response"),
    ("GET", "/api/marketing/quotations/{quotation_id}/download-pdf"),
    ("GET", "/api/marketing/stats"),
    ("GET", "/api/marketing/programmes"),
    ("GET", "/api/marketing/default-terms"),
    ("GET", "/api/marketing/pdf-templates"),
    ("PUT", "/api/marketing/pdf-templates"),
    
    # Security
    ("GET", "/api/security/status"),
    ("GET", "/api/security/audit-log"),
    ("POST", "/api/security/block-ip"),
    ("POST", "/api/security/unblock-ip"),
    
    # Debug
    ("GET", "/api/debug/database-info"),
    
    # Static Files
    ("GET", "/api/static/certificates/{filename}"),
    ("GET", "/api/static/certificates_pdf/{filename}"),
    ("GET", "/api/static/checklist-photos/{filename}"),
    ("GET", "/api/static/logos/{filename}"),
    ("GET", "/api/static/templates/{filename}"),
    ("GET", "/api/uploads/company/{filename}"),
    ("GET", "/api/uploads/indemnity/{filename}"),
]


def normalize_path(path: str) -> str:
    """Replace path parameters with test values for route existence check"""
    replacements = {
        "{company_id}": "test-company-id",
        "{program_id}": "test-program-id",
        "{session_id}": "test-session-id",
        "{user_id}": "test-user-id",
        "{participant_id}": "test-participant-id",
        "{test_id}": "test-test-id",
        "{result_id}": "test-result-id",
        "{certificate_id}": "test-certificate-id",
        "{template_id}": "test-template-id",
        "{item_index}": "0",
        "{report_id}": "test-report-id",
        "{party_id}": "test-party-id",
        "{invoice_id}": "test-invoice-id",
        "{cn_id}": "test-cn-id",
        "{payment_id}": "test-payment-id",
        "{expense_id}": "test-expense-id",
        "{fee_id}": "test-fee-id",
        "{period_id}": "test-period-id",
        "{record_id}": "test-record-id",
        "{entry_id}": "test-entry-id",
        "{transaction_id}": "test-transaction-id",
        "{staff_id}": "test-staff-id",
        "{payslip_id}": "test-payslip-id",
        "{advice_id}": "test-advice-id",
        "{rate_type}": "epf",
        "{year}": "2024",
        "{client_id}": "test-client-id",
        "{item_id}": "test-item-id",
        "{quotation_id}": "test-quotation-id",
        "{coordinator_id}": "test-coordinator-id",
        "{trainer_id}": "test-trainer-id",
        "{marketing_id}": "test-marketing-id",
        "{filename}": "test.pdf",
    }
    for placeholder, value in replacements.items():
        path = path.replace(placeholder, value)
    return path


class TestAPIContract:
    """
    API Contract Tests - Run before and after refactoring
    
    These tests verify that all API routes EXIST (return something other than 404).
    They do NOT verify correct functionality - that's for integration tests.
    """
    
    @pytest.mark.parametrize("method,path", ALL_ENDPOINTS)
    def test_endpoint_exists(self, method: str, path: str):
        """
        Verify each endpoint exists and doesn't return 404.
        
        Acceptable responses:
        - 200, 201: Success (route works)
        - 401, 403: Auth required (route exists)
        - 400, 422: Bad request/validation (route exists)
        - 500: Server error (route exists but has bug)
        
        NOT acceptable:
        - 404: Route not found (REFACTORING BROKE IT!)
        """
        normalized_path = normalize_path(path)
        
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            try:
                response = client.request(method, normalized_path)
                
                # 404 means the route doesn't exist - FAIL!
                assert response.status_code != 404, (
                    f"\n{'='*60}\n"
                    f"🚨 BROKEN ROUTE DETECTED!\n"
                    f"{'='*60}\n"
                    f"Method: {method}\n"
                    f"Path: {path}\n"
                    f"Tested: {normalized_path}\n"
                    f"Status: 404 NOT FOUND\n"
                    f"{'='*60}\n"
                    f"This route existed before refactoring but is now missing!\n"
                    f"ROLLBACK IMMEDIATELY and check router prefix configuration.\n"
                    f"{'='*60}"
                )
                
                # Log successful route check
                print(f"✅ {method:6} {path} -> {response.status_code}")
                
            except httpx.ConnectError:
                pytest.fail(
                    f"Cannot connect to {BASE_URL}. "
                    "Make sure the backend is running: sudo supervisorctl restart backend"
                )


def run_quick_check():
    """
    Quick sanity check - run a few critical endpoints.
    Use this for fast verification during development.
    """
    critical_endpoints = [
        ("GET", "/api/"),
        ("GET", "/health"),
        ("GET", "/api/programs"),
        ("GET", "/api/sessions"),
        ("GET", "/api/users"),
        ("GET", "/api/finance/dashboard"),
        ("GET", "/api/marketing/quotations"),
    ]
    
    print("\n🔍 Quick API Contract Check\n")
    
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        all_passed = True
        for method, path in critical_endpoints:
            try:
                response = client.request(method, path)
                if response.status_code == 404:
                    print(f"❌ {method} {path} -> 404 NOT FOUND")
                    all_passed = False
                else:
                    print(f"✅ {method} {path} -> {response.status_code}")
            except Exception as e:
                print(f"❌ {method} {path} -> ERROR: {e}")
                all_passed = False
        
        print()
        if all_passed:
            print("✅ All critical endpoints are accessible!")
        else:
            print("❌ Some endpoints are broken! Check the output above.")
        
        return all_passed


if __name__ == "__main__":
    # Run quick check when executed directly
    import sys
    success = run_quick_check()
    sys.exit(0 if success else 1)
