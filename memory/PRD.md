# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). The system manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Authentication: JWT + bcrypt (24h expiry)

## Current Status (Mar 2026)

### Comprehensive Backfill System — COMPLETE (Mar 20, 2026)
**Root cause fix**: Historical transactions created before the Accounting Engine had no journal entries.

**What was built**:
- `POST /api/accounting/backfill` handles **10 transaction types**: invoices, payments, credit notes, trainer fees, coordinator fees, session expenses, marketing commissions, manual income, manual expenses, petty cash
- Uses **original transaction dates** (no longer forces pre-start dates to accounting start date)
- Auto-opens accounting periods as needed
- Idempotent: safe to re-run
- Paid invoices always post to Training Revenue (4000), not Deferred Revenue
- COA mapping: trainer→5000, coordinator→5100, marketing→5200, session expenses→5300-5700 by category, manual income→4100, manual expenses→6999, petty cash→6600

**Date fix**: Dec 2025 invoices now correctly appear in 2025 P&L (not 2026).

**Testing**: 100% — Backend 15/15, Frontend all flows (iteration_26)

### Balance Sheet UI Enhancement — COMPLETE
- Balanced/Unbalanced badge, account codes, period label, Print/Excel buttons
- Testing: 100% (iteration_24)

### Production Audit Phase 1 — COMPLETE
- DB indexes, JWT 24h, ErrorBoundary, ProtectedRoute, CORS hardening

### Previous Session Completions
- Payroll System Overhaul (edit, delete with void, journal auto-posting)
- Finance Reporting (Auditor P&L, CEO P&L, YoY, Print COA, Trial Balance)
- Credit Note & Payment Flow Fix, Export Fixes

## Design Principle
**Always include backfill**: Any future improvement that adds auto-posting or new data processing must include a backfill mechanism for existing data.

## Known Issues
- Pre-existing 500 error on checklist template API (P2)
- Historical journal entries show "Unknown" for some descriptions (P2)
- P&L Ledger page (old system) uses different data source than Accounting Engine P&L (part of P&L unification task)

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
