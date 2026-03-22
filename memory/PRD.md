# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). Manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Authentication: JWT + bcrypt (24h expiry)

## Current Status (Mar 2026)

### Manual Staff-User Link Fix — COMPLETE (Mar 22, 2026)
**Problem**: Staff members (like Abdul Malek) showed "Not linked" on HR & Payroll because the auto-link only matched by exact name/IC. If names differ slightly, the link fails.
**Fix**: 
- Added `POST /api/hr/staff/{staff_id}/link-user/{user_id}` endpoint for manual linking
- Added `DELETE /api/hr/staff/{staff_id}/unlink-user` endpoint for unlinking
- Replaced static "Not linked" badge with clickable "Link user" button → opens dropdown to select user
- "Linked" badge shows green, hover turns red for unlinking
- Auto-link button still available for batch operations
- Testing: Backend endpoints verified, UI screenshot confirmed

### Dashboard Analytics/KPIs + Backend Role Protection — COMPLETE (Mar 22, 2026)
- Dashboard KPIs: 8 business metrics on Admin Dashboard
- Role guards added to 15 endpoints across 6 route files
- Testing: 100% (iteration_30)

### Quick Wins Batch — COMPLETE (Mar 22, 2026)
- Database Indexing: 25 new indexes across 19 collections
- PWA Enhancements: Service worker v2
- Loading States & Empty States: Skeleton loaders + empty states

### Previous Completions
- Balance Sheet UI, Backfill System, Reset & Re-sync
- Full mobile responsive overhaul
- Payroll portal fixes & status indicators

## Known Issues
- Pre-existing 500 error on checklist template API (P2)

## Feature Backlog
- (P0) Duplicate Route Refactor — 55 endpoints (user holding until laptop ready)
- (P1) Unify P&L Systems
- (P1) Notification System
- (P1) Trainer Contract Workflow (freelance only)
- (P1) Post-Training Evaluation (3mo/6mo, programme-specific questionnaires)
- (P1) Supervisor Portal Enhancement
- (P1) Certificate Generation (PDF template)
- (P1) SaaS Monetization (Stripe)
- (P2) Client/Trainer Portals, Native App, PWA Offline

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
