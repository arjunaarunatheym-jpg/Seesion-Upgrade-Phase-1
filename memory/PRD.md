# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). The system manages training sessions, participants, invoicing, and coordination across multiple user roles.

## User Personas
- **System Administrator**: Manages programs, users, companies, settings
- **Coordinator**: Manages training sessions, participants, attendance
- **Finance**: Handles invoicing, payments, P&L, payables
- **Marketing**: Manages clients, quotations, commissions
- **Trainer**: Conducts training, provides feedback
- **Participant**: Attends training, completes tests, feedback

## Core Features Implemented
1. **Authentication & Authorization** - JWT-based login with role-based access
2. **Training Session Management** - Create, schedule, manage training sessions
3. **Participant Management** - Registration, attendance tracking, certificates
4. **Invoice System** - Auto-generation, approval workflow, PDF generation
5. **Multi-Invoice per Session** - Link multiple invoices from different companies to a single session
6. **Finance Portal** - Full accounting, P&L ledger, payables, credit notes
7. **Quotation System** - Marketing quotations with admin approval workflow
8. **Indemnity Form** - Multi-step wizard with digital signature capture

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- PDF Generation: fpdf2
- Authentication: JWT + bcrypt
- Email: Resend API

## API Endpoints (Key)
- `/api/auth/login` - User authentication
- `/api/finance/pnl-journal` - Journal-based Auditor P&L endpoint
- `/api/finance/pnl-journal/drilldown/{account_code}` - Drilldown into P&L accounts
- `/api/finance/pnl-journal/export` - Export P&L to Excel
- `/api/accounting/chart-of-accounts` - Unified COA source of truth
- `/api/accounting/upgrade-coa` - COA migration endpoint
- `/api/hr/payslips/generate` - Generate payslip with full staff info, YTD, journal posting
- `/api/hr/payslips/{id}` - GET/PUT/DELETE payslip (with journal entry management)

## Current Status (Mar 2026)

### Recently Completed (Mar 19, 2026)
- **3-Phase Finance Reporting Overhaul — COMPLETE**
  - Phase A: Unified COA (46 accounts) with statement_type and pnl_section fields
  - Phase B: Journal-based P&L endpoint with filters, drill-down, Excel export
  - Phase C: Auditor P&L tab with summary cards, filters, drill-down dialog, print/export
  - Fixed critical bug: pnl-journal endpoint return statement was misplaced
  - All 14 backend tests passed, frontend verified (iteration_21)

- **Payslip System Overhaul — COMPLETE**
  - Fixed root cause: Duplicate endpoints in routes/hr.py (simplified) vs server.py (complete) — routes/hr.py was taking priority but missing staff info, YTD, journal posting
  - Updated routes/hr.py with complete payslip generation including: designation, department, EPF/SOCSO numbers, bank info, YTD calculations, journal posting
  - Added Edit Payslip endpoint (PUT /api/hr/payslips/{id}) with staff info refresh, amount editing, gross/nett recalculation, YTD recalculation, journal re-posting
  - Added journal entry voiding on payslip delete
  - Fixed post_payroll() field name mismatches (nett_pay vs net_pay, full_name vs employee_name)
  - Removed ~377 lines of duplicate payslip code from server.py
  - Added Edit button + dialog to frontend with live calculation preview
  - Backdating works — generate payslips for any past month/year
  - All tested via curl + frontend screenshots + testing agent (iteration_22)

### Upcoming (P0/P1)
- Trainer Contract Workflow
- Post-Training Evaluation System
- Automated Certificate Generation Workflow
- SaaS Monetization (Stripe Integration)
- server.py continued refactoring

### Backlog (P2)
- Journal entry "Unknown" descriptions fix
- Convert to Native App (Capacitor)
- Privacy Policy Page
- Client Portal / Trainer Portal
- Enhanced Data Management tables with search/pagination
- WYSIWYG PDF Template Editor
- Collapsible table UI in Admin Dashboard
- Cash Basis P&L report

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── accounting.py          # COA source of truth, journal posting, migration
│   │   ├── finance_reports.py     # Journal-based P&L, export, drilldown, subledgers, GL
│   │   ├── finance_payments.py    # Payment recording, credit notes
│   │   ├── finance_invoices.py    # Invoice CRUD, Excel export
│   │   ├── hr.py                  # Complete HR/Payroll (payslip CRUD with journals)
│   │   ├── marketing.py           # Quotation + lead notifications
│   │   ├── sessions_new.py        # Session management
│   │   └── notifications.py       # Notification settings + broadcast
│   ├── utils/
│   │   └── email_notifications.py # Smart email dispatcher
│   └── server.py                  # Main FastAPI app (reduced tech debt)
└── frontend/
    └── src/
        ├── components/
        │   ├── ledger/
        │   │   ├── AuditorPnLTab.jsx     # Journal-based P&L with drill-down
        │   │   ├── CEOPnLTab.jsx         # Programme-based P&L
        │   │   ├── YoYComparisonTab.jsx  # Year-over-year comparison
        │   │   └── GeneralLedgerTab.jsx  # General Ledger view
        │   ├── finance/                  # Finance sub-components
        │   ├── HRModule.jsx              # HR & Payroll with Edit payslip dialog
        │   └── ProfitLossLedger.jsx      # Container for all P&L tabs
        └── pages/
            └── FinanceDashboard.jsx      # Finance Portal page
```

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
