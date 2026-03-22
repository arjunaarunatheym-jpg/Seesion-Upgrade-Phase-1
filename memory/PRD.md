# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). Manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Authentication: JWT + bcrypt (24h expiry)

## Current Status (Mar 2026)

### Dashboard Analytics/KPIs + Backend Role Protection — COMPLETE (Mar 22, 2026)
**What was built**:
- **Dashboard KPIs**: New `GET /api/admin/dashboard-kpis` endpoint aggregating 8 business metrics. KPI cards component displaying Sessions This Month, Revenue YTD, Outstanding Invoices, Trainees YTD, Avg Feedback Score, Trainer Utilization, Active Staff, Pending Quotations
- **Backend Role Protection**: Role-based access guards added to 15 endpoints across 6 route files (accounting exports, finance payables, HR templates, reports, training reports, certificates). Unauthorized roles receive 403 errors.
- Testing: 100% — Backend 16/16, Frontend all flows (iteration_30)

### Quick Wins Batch — COMPLETE (Mar 22, 2026)
- Database Indexing: 25 new indexes across 19 collections
- PWA Enhancements: Service worker v2, cache-first, offline page
- Loading States & Empty States: Skeleton loaders + empty states across all dashboards
- Testing: 100% (iteration_29)

### Previous Completions
- Balance Sheet UI, Comprehensive Backfill System, Reset & Re-sync
- Full mobile responsive overhaul (all 9 dashboards)
- Payroll portal fixes & status indicators
- Production Audit Phase 1

## Architecture
```
/app/
├── backend/
│   ├── routes/
│   │   ├── admin_kpis.py        # NEW: Dashboard KPI metrics
│   │   ├── accounting.py        # MODIFIED: Role guards on 4 export endpoints
│   │   ├── finance_payables.py  # MODIFIED: Role guards on 2 endpoints
│   │   ├── hr.py                # MODIFIED: Role guard on statutory download
│   │   ├── reports.py           # MODIFIED: Role guards on 3 endpoints
│   │   ├── training_reports.py  # MODIFIED: Role guards on 3 endpoints
│   │   └── certificates.py     # MODIFIED: Role guards on 2 endpoints
│   └── server.py
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── DashboardKPIs.jsx # NEW: KPI cards component
    │   │   ├── EmptyState.jsx    # NEW: Reusable empty state
    │   │   └── ui/skeleton.jsx   # MODIFIED: Extended with variants
    │   └── pages/
    │       └── AdminDashboard.jsx # MODIFIED: KPI cards integrated
    └── public/
        ├── service-worker.js     # MODIFIED: Enhanced caching v2
        └── offline.html          # MODIFIED: Improved UI
```

## Known Issues
- Pre-existing 500 error on checklist template API (P2)
- Historical journal entries show "Unknown" for some descriptions (P2)

## Feature Backlog
- (P0) Duplicate Route Refactor — 55 conflicting API endpoints (user holding until laptop ready)
- (P1) Unify P&L Systems — Deprecate old Auditor P&L
- (P1) Notification System — In-app bell + email alerts
- (P1) Trainer Contract Workflow — Freelance staff contracts per session
- (P1) Post-Training Evaluation — 3mo/6mo follow-up, auto-delete non-attendees
- (P1) Supervisor Portal Enhancement — Invoices, feedback, certificates
- (P1) Certificate Generation — PDF template-based with dynamic fields
- (P1) SaaS Monetization (Stripe)
- (P2) Client/Trainer Portals, Native App
- (P2) PWA Offline Data Caching for field staff
- (P2) Phase 2/3 Audit Fixes

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
