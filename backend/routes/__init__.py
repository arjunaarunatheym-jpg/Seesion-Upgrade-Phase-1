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

# Create combined router for easy registration
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
    'get_all_routers',
]
