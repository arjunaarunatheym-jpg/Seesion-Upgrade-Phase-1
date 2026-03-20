# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). The system manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Authentication: JWT + bcrypt (24h expiry)

## Current Status (Mar 2026)

### Balance Sheet UI Enhancement — COMPLETE
- Balanced/Unbalanced badge, account codes, period label, Print button
- Excel export working, data-testid coverage
- Testing: 100% (iteration_24)

### Backfill / Sync Historical Transactions — COMPLETE (Mar 20, 2026)
- **Root cause**: Invoices/payments created before Accounting Engine had no journal entries → Revenue showed RM 0
- Built `POST /api/accounting/backfill` endpoint that retroactively creates journal entries for all existing invoices, payments, and credit notes
- Handles pre-accounting-start-date transactions by posting with accounting start date
- Paid invoices correctly mapped to Training Revenue (4000), not Deferred Revenue (2300)
- Idempotent: safe to re-run, duplicates skipped automatically
- Frontend: "Sync Historical Transactions" button with result summary in Accounting Engine header
- After backfill: Revenue RM 27,840, Expenses RM 3,103.65, Net Profit RM 24,736.35
- Balance Sheet: Assets RM 25,455.90 = Liabilities + Equity RM 25,455.90 (Balanced)
- Testing: 100% — Backend 14/14, Frontend all flows verified (iteration_25)

### Production Audit Phase 1 — COMPLETE
- DB indexes, JWT 24h expiry, ErrorBoundary, ProtectedRoute, CORS hardening

### Previous Session Completions
- Payroll System Overhaul (edit, delete with void, journal auto-posting)
- 3-Phase Finance Reporting (Auditor P&L, CEO P&L, YoY, Print COA)
- Credit Note & Payment Flow Fix, Export Fixes

## Design Principle: Always Include Backfill
Per user request: any future improvement that adds auto-posting or new data processing must include a backfill mechanism for existing data.

## Known Issues
- Pre-existing 500 error on checklist template API (P2)
- Historical journal entries show "Unknown" for some descriptions (P2)
- P&L Ledger page (old system) still shows RM 0 — uses different data source than Accounting Engine P&L (P1, part of P&L unification)

## Feature Backlog
- (P0) Duplicate Route Refactor — 55 conflicting API endpoints
- (P1) Phase 2 Audit Fixes — Unify P&L, invoice state machine, consolidate collections
- (P1) Trainer Contract Workflow
- (P1) Post-Training Evaluation System
- (P1) Automated Certificate Generation
- (P1) SaaS Monetization (Stripe)
- (P2) Client/Trainer Portals
- (P2) Native App (Capacitor)

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
