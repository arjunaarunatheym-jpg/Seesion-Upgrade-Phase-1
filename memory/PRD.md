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

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- PDF Generation: fpdf2
- Authentication: JWT + bcrypt (24h expiry)
- Email: Resend API

## Current Status (Mar 2026)

### Production Audit Phase 1 — COMPLETE (Mar 20, 2026)
**Zero-risk fixes applied:**
- CORS default hardened ('' instead of '*' fallback)
- Admin password removed from startup logs
- Dead backup files deleted (1.3MB)
- 29 database indexes added across 15 collections
- JWT expiry reduced from 7 days to 24 hours

**Additive safety fixes applied:**
- ErrorBoundary wraps entire app (prevents white-screen crashes)
- ProtectedRoute guards on all frontend routes
- Role-based access enforced: coordinator blocked from /finance, /admin
- All 20/20 backend tests passed, all frontend flows verified (iteration_23)

### Phase 1 Items Still Pending (Higher Risk — Need Careful Planning)
- Remove 55 duplicate route definitions (24 in server.py, 31 cross-file)
- Add `_id` exclusion to 96 MongoDB queries
- Replace 106 bare `except:` clauses
- Add Pydantic validation models for financial inputs

### Previous Session Completions
- 3-Phase Finance Reporting Overhaul (Auditor P&L)
- Payslip System Overhaul (edit, journal posting, delete with void)
- Credit Note & Payment Flow Fix
- Export Fixes (Marketing CSV, Invoice Excel)
- CEO P&L, YoY Comparison, Print COA
- Duplicate HR code removal (~667 lines)

### Phase 2 — Operational Improvements (Planned)
- Unify to single P&L system (journal-based)
- Implement invoice status state machine
- Consolidate 5 audit log collections into 1
- Consolidate 3 attendance collections into 1
- Add MongoDB schema validation
- Continue server.py modularization
- Add responsive breakpoints to 6 mobile-critical pages
- Write integration tests for critical financial paths
- Enforce password policy (8+ chars, complexity)

### Phase 3 — Scaling & Polish (Planned)
- Migrate financial calculations to Decimal
- Break mega-components into sub-components
- Implement refresh token mechanism
- Feature-based frontend directory restructure
- Loading skeletons and empty states
- CI/CD pipeline

### Feature Backlog
- (P0) Trainer Contract Workflow
- (P1) Post-Training Evaluation System
- (P1) Automated Certificate Generation
- (P1) SaaS Monetization (Stripe)
- (P2) Client Portal / Trainer Portal
- (P2) Cash Basis P&L Report
- (P2) Native App (Capacitor)
- (P2) Privacy Policy Page

## Architecture
```
/app/
├── backend/
│   ├── routes/ (18 files - authoritative endpoints)
│   ├── utils/
│   ├── models/
│   └── server.py (16,854 lines - needs modularization)
└── frontend/
    └── src/
        ├── components/
        │   ├── ErrorBoundary.jsx (NEW)
        │   ├── ProtectedRoute.jsx (NEW)
        │   ├── ledger/ (P&L tabs)
        │   ├── finance/ (sub-components)
        │   └── HRModule.jsx
        ├── pages/ (13 pages)
        └── App.js (route definitions)
```

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1

## Full Audit Report
See `/app/PRODUCTION_AUDIT_REPORT.md` for the complete 38-issue audit with severity classifications and 3-phase roadmap.
