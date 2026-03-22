# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). Manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Authentication: JWT + bcrypt (24h expiry)

## Current Status (Mar 2026)

### Quick Wins Batch — COMPLETE (Mar 22, 2026)
**What was built**:
- **Database Indexing**: 25 new indexes added to 19 collections (attendance_records, audit_trail, chief_trainer_feedback, coordinator_feedback, finance_audit_log, manual_expenses, manual_income, marketing_clients, participant_attendance, petty_cash_transactions, vehicle_checklists, vehicle_details, tests, broadcast_history, feedback_templates, certificate_templates, marketing_audit_log, super_admin_audit_log)
- **PWA Enhancements**: Service worker upgraded to v2 with cache-first for static assets, stale-while-revalidate for read-only API data, improved offline page
- **Loading States & Empty States**: Skeleton loaders added to Finance, Coordinator, Supervisor, Marketing dashboards. Empty state components with icons and descriptions added to all major list views (sessions, invoices, attendance)
- Testing: 100% — Backend 11/11, Frontend all flows (iteration_29)

### Payroll Portal & Status Indicators — COMPLETE (Mar 22, 2026)
- Auto-link hr_staff to users, payroll status badges, My Payroll tabs
- Testing: 100% (iteration_28)

### Mobile Responsive Overhaul — COMPLETE (Mar 21, 2026)
- All 9 dashboard pages made mobile-friendly
- Testing: 100% (iteration_27)

### Comprehensive Backfill System — COMPLETE (Mar 20, 2026)
- 10 transaction types, original dates, Reset & Re-sync button
- Testing: 100% (iteration_26)

### Balance Sheet UI — COMPLETE
- Balanced badge, account codes, Print/Excel

### Production Audit Phase 1 — COMPLETE
- DB indexes, JWT 24h, ErrorBoundary, ProtectedRoute

## Design Principles
1. **Always include backfill**: Future auto-posting improvements must include backfill
2. **Mobile-first CSS**: Use sm:/md:/lg: breakpoints
3. **Staff-user linking**: Always link hr_staff to users for portal access
4. **Loading patterns**: Use skeleton loaders during data fetch, empty states when no data

## Known Issues
- Pre-existing 500 error on checklist template API (P2)
- Historical journal entries show "Unknown" for some descriptions (P2)

## Feature Backlog
- (P0) Duplicate Route Refactor — 55 conflicting API endpoints (user wants to hold until laptop ready)
- (P1) Unify P&L Systems — Deprecate old Auditor P&L
- (P1) Backend Role Protection — 20+ unprotected endpoints
- (P1) Dashboard Analytics/KPIs — At-a-glance business metrics
- (P1) Trainer Contract Workflow — Freelance staff contracts per session
- (P1) Post-Training Evaluation System — 3mo/6mo follow-up, auto-delete non-attendees
- (P1) Supervisor Portal Enhancement — Invoices, feedback, certificates for company trainees
- (P1) Certificate Generation — PDF template-based with dynamic fields
- (P1) Notification System — In-app bell + email notifications
- (P1) SaaS Monetization (Stripe)
- (P2) Client/Trainer Portals, Native App
- (P2) PWA Offline Data Caching for field staff
- (P2) Phase 2/3 Audit Fixes

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
