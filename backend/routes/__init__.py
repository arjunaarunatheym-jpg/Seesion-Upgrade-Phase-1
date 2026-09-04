"""
Routes package - All API routers are exported from here
"""
from fastapi import APIRouter

# Import individual routers
from .settings import router as settings_router
from .programs import router as programs_router
from .companies import router as companies_router
from .auth import router as auth_router
from .users import router as users_router
from .attendance import router as attendance_router
from .participant_access import router as participant_access_router
from .tests import router as tests_router
from .feedback import router as feedback_router
from .checklists import router as checklists_router
from .sessions_new import router as sessions_new_router
from .hr import router as hr_router
from .marketing import router as marketing_router
from .certificates import router as certificates_router
from .training_reports import router as training_reports_router
from .supervisor import router as supervisor_router
from .super_admin import router as super_admin_router
from .security import router as security_router
from .finance_billing import router as finance_billing_router
from .finance_invoices import router as finance_invoices_router
from .finance_payments import router as finance_payments_router
from .finance_petty_cash import router as finance_petty_cash_router
from .finance_reports import router as finance_reports_router
from .finance_payables import router as finance_payables_router
from .accounting import router as accounting_router
from .superadmin_portal import router as superadmin_portal_router
from .notifications import router as notifications_router
from .admin_kpis import router as admin_kpis_router
from .health import router as health_router
from .backup import router as backup_router
from .static_files import router as static_files_router
from .templates import router as templates_router
from .finance_session import router as finance_session_router
from .reports_legacy import router as reports_legacy_router
from .vehicle_details import router as vehicle_details_router
from .admin_data_management import router as admin_data_management_router
from .certificate_verify import router as certificate_verify_router
from .admin_fee import router as admin_fee_router
from .finance_source_of_truth import router as finance_source_of_truth_router
from .superadmin_finance_corrections import router as superadmin_finance_corrections_router

# Create combined router
def get_all_routers():
    """Return list of all routers with their prefixes already set"""
    return [
        settings_router,        # /settings
        programs_router,        # /programs
        companies_router,       # /companies
        auth_router,           # /auth/*
        users_router,          # /users
        attendance_router,     # /attendance/*
        participant_access_router,  # /participant-access/*
        tests_router,          # /tests/*
        feedback_router,       # /feedback-templates/*, /feedback/*, coordinator/chief-trainer feedback
        checklists_router,     # /checklist-templates/*, /checklists/*, /vehicle-*/
        sessions_new_router,   # /sessions/* (full CRUD now)
        hr_router,             # /hr/* (staff, payroll, pay advice)
        marketing_router,      # /marketing/* (clients, quotations)
        certificates_router,   # /certificates/*
        training_reports_router, # /training-reports/*
        supervisor_router,     # /supervisor/* (PIC supervisor)
        super_admin_router,    # /super-admin/* (testing panel)
        security_router,       # /security/* (admin security)
        finance_billing_router, # /finance/billing-parties (F1)
        finance_invoices_router, # /finance/invoices/* (F2)
        finance_payments_router, # /finance/payments/*, credit-notes/* (F3)
        finance_petty_cash_router, # /finance/petty-cash/*, manual-* (F6)
        finance_reports_router, # /finance/profit-loss/*, subledger/*, chart-of-accounts, general-ledger (F5)
        finance_payables_router, # /finance/payables/*, income/*, dashboard, company-settings (F4)
        accounting_router,      # /accounting/* (Chart of Accounts, Journal Entries, Trial Balance)
        superadmin_portal_router, # /superadmin/* (Super Admin Portal)
        notifications_router,   # /notifications/* (Email & Broadcast)
        health_router,          # /health, /health/detailed
        backup_router,          # /backup/*
        static_files_router,    # /static/*, /uploads/*, /debug/*, /checklist-photos/*
        templates_router,       # /templates/*
        finance_session_router, # /finance/session/*, /finance/pdf-layout-preview
        reports_legacy_router,  # /reports/* (legacy)
        vehicle_details_router, # /vehicle-details/*
        admin_data_management_router, # /admin-data/*
        certificate_verify_router, # /verify/* (public cert verification)
        admin_fee_router,        # /admin-fee/* (Administration Fee config + auto-application)
        finance_source_of_truth_router, # /finance/source-of-truth/* (Phase 2 canonical calc, READ-ONLY)
        superadmin_finance_corrections_router, # /superadmin/finance/* (Phase 3A God Mode corrections)
    ]

__all__ = [
    'settings_router',
    'programs_router', 
    'companies_router',
    'auth_router',
    'users_router',
    'attendance_router',
    'participant_access_router',
    'tests_router',
    'feedback_router',
    'checklists_router',
    'sessions_new_router',
    'hr_router',
    'marketing_router',
    'certificates_router',
    'training_reports_router',
    'supervisor_router',
    'super_admin_router',
    'security_router',
    'finance_billing_router',
    'finance_invoices_router',
    'finance_payments_router',
    'finance_petty_cash_router',
    'finance_reports_router',
    'finance_payables_router',
    'accounting_router',
    'superadmin_portal_router',
    'notifications_router',
    'admin_kpis_router',
    'health_router',
    'backup_router',
    'static_files_router',
    'templates_router',
    'finance_session_router',
    'reports_legacy_router',
    'vehicle_details_router',
    'admin_data_management_router',
    'certificate_verify_router',
    'admin_fee_router',
    'finance_source_of_truth_router',
    'superadmin_finance_corrections_router',
    'get_all_routers',
]
