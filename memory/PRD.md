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
- `/api/finance/invoices` - Invoice CRUD operations
- `/api/finance/pnl-journal` - **NEW** Journal-based Auditor P&L endpoint
- `/api/finance/pnl-journal/drilldown/{account_code}` - **NEW** Drilldown into P&L accounts
- `/api/finance/pnl-journal/export` - **NEW** Export P&L to Excel
- `/api/accounting/chart-of-accounts` - Unified COA source of truth
- `/api/accounting/upgrade-coa` - COA migration endpoint
- `/api/finance/session/{session_id}/additional-invoice` - Create linked invoices
- `/api/marketing/quotations/{id}/download-pdf` - PDF generation with rich text
- `/api/settings/indemnity-sections` - Admin-managed indemnity content
- `/api/settings/feedback-questions` - GET/POST feedback questions (Admin)
- `/api/sessions/{session_id}/export-template` - Download Excel template
- `/api/sessions/{session_id}/import-data` - Import Excel data
- `/api/marketing/leads` - Lead CRUD
- `/api/notifications/settings` - Email notification settings CRUD
- `/api/notifications/broadcast` - Send broadcast emails
- `/api/superadmin/dashboard` - Super Admin dashboard stats

## Current Status (Mar 2026)

### Recently Completed (Mar 19, 2026)
- **3-Phase Finance Reporting Overhaul — COMPLETE**
  - Phase A: Unified Chart of Accounts (46 accounts) with `statement_type` and `pnl_section` fields
  - Phase B: New journal-based P&L endpoint (`/api/finance/pnl-journal`) with date filters, drill-down, Excel export
  - Phase C: Auditor P&L tab in Finance Portal with summary cards, filter controls, drill-down dialog, print, Excel export
  - Fixed critical bug: `pnl-journal` endpoint return statement was misplaced as dead code
  - Added missing `<TabsContent>` for Auditor P&L in `ProfitLossLedger.jsx`
  - Fixed drilldown month filter to correctly pass date range params
  - All 14 backend tests passed, frontend verified (iteration_21)

### Previously Completed
- CEO P&L Multi-Invoice Fix, Journal Reference Improvement
- Pay Advice Generation Fix, Calendar View for All Staff
- Marketing "My Sessions" Tab, Smart Email Dispatcher
- Email & Notifications System, Auto-Lead for Returning Clients
- Revenue Recognition Fix, Marketing Pipeline Month/Year Grouping
- Excel Import/Export Refinement, Certificate Template Designer
- Super Admin Portal, Credit Notes Month/Year Grouping
- Fixed broken exports (Marketing CSV, Invoice Excel)
- Payment recording and credit note flow overhaul
- 2-decimal financial precision fix
- Printable branded P&L statement (CEO view)
- Year-over-Year Comparison tab
- Print COA feature
- Removed ~667 lines duplicate HR code from server.py

### Upcoming (P0/P1)
- Trainer Contract Workflow — Generate & email freelance contract for trainers
- `server.py` refactoring — Move remaining endpoints to modular route files
- Post-Training Evaluation System — Automated evaluation forms
- Automated Certificate Generation Workflow
- SaaS Monetization — Stripe integration for tiered subscription plans

### Backlog (P2)
- Journal entry "Unknown" descriptions fix
- Payables Excel export verification
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
│   │   ├── marketing.py           # Quotation + lead notifications
│   │   ├── sessions_new.py        # Session management
│   │   ├── notifications.py       # Notification settings + broadcast
│   │   └── hr.py                  # HR/Payroll routes
│   ├── utils/
│   │   └── email_notifications.py # Smart email dispatcher
│   ├── models/                    # Pydantic models
│   └── server.py                  # Main FastAPI app (still contains tech debt)
└── frontend/
    └── src/
        ├── components/
        │   ├── ledger/
        │   │   ├── AuditorPnLTab.jsx     # Journal-based P&L with drill-down
        │   │   ├── CEOPnLTab.jsx         # Programme-based P&L
        │   │   ├── YoYComparisonTab.jsx  # Year-over-year comparison
        │   │   └── GeneralLedgerTab.jsx  # General Ledger view
        │   ├── finance/                  # Finance sub-components
        │   └── ProfitLossLedger.jsx      # Container for all P&L tabs
        ├── pages/
        │   └── FinanceDashboard.jsx      # Finance Portal page
        └── utils/
            ├── printPnL.js               # Print P&L utility
            └── printReceipt.js           # Print receipt utility
```

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
