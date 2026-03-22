# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). Manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Authentication: JWT + bcrypt (24h expiry)

## Current Status (Mar 2026)

### Payroll Portal & Status Indicators — COMPLETE (Mar 22, 2026)
**Root cause**: hr_staff records had no `user_id` link to user accounts, so staff portals couldn't find payslips.

**What was built**:
- `GET /api/hr/payroll-status` — Returns paid/unpaid counts per month for all staff
- `POST /api/hr/staff/auto-link-users` — Auto-matches hr_staff to users by name or IC number
- **My Payroll tab** added to Coordinator, Marketing, and Trainer dashboards
- **Payroll status summary** in HRModule: "March 2026 Payroll: X Paid, Y Unpaid"
- **Per-staff badges**: Green "Paid" / Orange "Unpaid" on each staff card
- **"Not linked" badge** for staff without user_id connection
- **Auto-link Users button** in HR module to fix linkage
- Testing: 100% — Backend 14/14, Frontend all flows (iteration_28)

### Mobile Responsive Overhaul — COMPLETE (Mar 21, 2026)
- All 9 dashboard pages made mobile-friendly
- Global CSS: table scroll, full-width dialogs, scrollable tabs, compact badges
- Headers stack vertically on mobile, tabs icon-only with horizontal scroll
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

## Known Issues
- Pre-existing 500 error on checklist template API (P2)
- Historical journal entries show "Unknown" for some descriptions (P2)

## Feature Backlog
- (P0) Duplicate Route Refactor — 55 conflicting API endpoints
- (P1) Phase 2 Audit Fixes — Unify P&L, invoice state machine
- (P1) Trainer Contract Workflow
- (P1) Post-Training Evaluation System
- (P1) Automated Certificate Generation
- (P1) SaaS Monetization (Stripe)
- (P2) Client/Trainer Portals, Native App

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
