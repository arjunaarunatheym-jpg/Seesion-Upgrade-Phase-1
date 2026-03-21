# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). The system manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Authentication: JWT + bcrypt (24h expiry)

## Current Status (Mar 2026)

### Mobile Responsive Overhaul — COMPLETE (Mar 21, 2026)
All pages made mobile-friendly:
- **Global CSS** (App.css): Table horizontal scroll, full-width dialogs, scrollable tab lists, compact badges, reduced padding
- **All 9 dashboard headers**: Stack vertically on mobile (flex-col sm:flex-row), smaller text, icon-only buttons
- **Tab navigation**: Horizontal scroll with hidden scrollbar, icon-only on mobile
- **Accounting Engine**: Header buttons wrap, sub-tabs scroll, Balance Sheet grid stacks single column
- **Tables**: Global overflow-x-auto for all tables on mobile
- Testing: 100% — All pages verified on mobile (390x844) and desktop (1920x800) (iteration_27)

Pages updated: AdminDashboard, FinanceDashboard, CoordinatorDashboard, CalendarDashboard, ParticipantDashboard, SupervisorDashboard_new, AssistantAdminDashboard, MarketingDashboard, AccountingTab

### Comprehensive Backfill System — COMPLETE (Mar 20, 2026)
- `POST /api/accounting/backfill` handles 10 transaction types with original dates
- `POST /api/accounting/backfill/reset-and-resync` voids old entries and re-syncs
- Testing: 100% (iteration_26)

### Balance Sheet UI Enhancement — COMPLETE
- Balanced badge, account codes, Print/Excel, data-testid coverage

### Production Audit Phase 1 — COMPLETE
- DB indexes, JWT 24h, ErrorBoundary, ProtectedRoute, CORS hardening

## Design Principles
1. **Always include backfill**: Future improvements with auto-posting must include backfill
2. **Mobile-first CSS**: Use sm:/md:/lg: breakpoints, flex-col sm:flex-row pattern, scrollbar-hide on tab lists

## Known Issues
- Pre-existing 500 error on checklist template API (P2)
- Historical journal entries show "Unknown" for some descriptions (P2)

## Feature Backlog
- (P0) Duplicate Route Refactor — 55 conflicting API endpoints
- (P1) Phase 2 Audit Fixes — Unify P&L, invoice state machine, consolidate collections
- (P1) Trainer Contract Workflow
- (P1) Post-Training Evaluation System
- (P1) Automated Certificate Generation
- (P1) SaaS Monetization (Stripe)
- (P2) Client/Trainer Portals, Native App

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
