# MDDRC Training Management Platform - PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving & Riding Centre (MDDRC). Features Admin, HR, Finance, Operations, and Marketing modules with Malaysian statutory compliance.

## Architecture
- **Frontend**: React + Shadcn/UI (port 3000)
- **Backend**: FastAPI + MongoDB (port 8001)
- **Database**: MongoDB (via MONGO_URL env var)

## Code Architecture (Post-Refactoring)
```
/app/backend/
├── server.py              # 536 lines - App init, middleware, DB, router registration
├── core/__init__.py       # Shared utilities: db, auth, helpers, path constants
├── models/__init__.py     # Pydantic models
├── routes/                # 38 modular route files
│   ├── __init__.py        # Router registry
│   ├── auth.py            # Authentication
│   ├── users.py           # User management + role-creation
│   ├── sessions_new.py    # Session CRUD + feedback export
│   ├── programs.py        # Training programs
│   ├── companies.py       # Company management
│   ├── hr.py              # HR & payroll (band-based EPF)
│   ├── marketing.py       # Leads, clients, quotations, PDF generation
│   ├── finance_invoices.py # Invoice CRUD + deleted invoice numbers
│   ├── finance_session.py # NEW: Session costing, expenses, profit
│   ├── finance_payments.py # Payment tracking
│   ├── finance_reports.py # P&L, AR Aging
│   ├── finance_billing.py # Billing parties
│   ├── finance_payables.py # Payables
│   ├── finance_petty_cash.py # Petty cash
│   ├── accounting.py      # Journal entries, audit trail
│   ├── settings.py        # App settings + indemnity/feedback questions
│   ├── templates.py       # NEW: Excel template downloads
│   ├── static_files.py    # NEW: Static file serving, uploads, debug
│   ├── reports_legacy.py  # NEW: Legacy report endpoints
│   ├── checklists.py      # Checklist templates + trainer checklist
│   ├── training_reports.py # Training report generation
│   ├── certificates.py    # Certificate management
│   ├── feedback.py        # Course feedback + bulk upload
│   ├── attendance.py      # Attendance tracking
│   ├── tests.py           # Assessment tests
│   ├── notifications.py   # Notifications
│   ├── security.py        # Security audit
│   ├── admin_kpis.py      # Dashboard KPIs
│   ├── admin_data_management.py # Data management
│   ├── health.py          # Health checks
│   ├── backup.py          # DB backup/export
│   ├── supervisor.py      # Supervisor portal
│   ├── super_admin.py     # Super admin
│   ├── superadmin_portal.py # Superadmin portal
│   ├── participant_access.py # Participant access
│   ├── vehicle_details.py # Vehicle details
│   └── reports.py         # Training reports (old module)
└── tests/
    └── test_critical_flows.py # 23 pytest cases
```

## What's Been Implemented

### Completed Features
- Full Auth system (JWT, role-based access, 8-char password requirement)
- Training Session CRUD with participant management
- Invoice generation with sequential numbering
- Band-based EPF statutory calculations (1001 Malaysian bands)
- Unified P&L with Journal-based Auditor view + AR Aging
- Interactive KPI drill-down dashboards (Admin + Finance)
- Searchable auto-creating Company Combobox for invoices
- Global mobile-friendly dialogs (overflow scroll fix)
- App Hardening: 23-case Pytest suite, DB Backup, Health Checks
- **Server.py Refactoring**: Monolith (16,865 lines) → Modular (536 lines + 38 route files)
- Checklist template 500 error FIXED (legacy data normalization)

### Refactoring Completed (Feb 2026)
- server.py: 16,865 → 536 lines (97% reduction)
- 280+ endpoints migrated to 38 modular route files
- 4 new route modules created: static_files.py, templates.py, finance_session.py, reports_legacy.py
- All 23 pytest cases pass post-refactoring
- Full frontend UI verified working

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1

## Prioritized Backlog

### P1 - High Priority
- Certificate auto-generation & Email notifications
- Trainer Contract Workflow (freelance staff contracts)
- Post-Training Evaluation System (3/6 month automated feedback)

### P2 - Medium Priority
- Balance Sheet report
- SST Summary report

### Future
- Multi-tenancy architecture
- Supervisor Portal / Client Self-Service Portal
- SaaS Monetization (Stripe Integration)
- Native Mobile App (Capacitor)
