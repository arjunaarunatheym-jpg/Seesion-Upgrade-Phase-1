# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for MDDRC. Manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python), Database: MongoDB, Auth: JWT + bcrypt

## Current Status (Mar 2026)

### EPF Band-Based Calculation + Dynamic Statutory Recalc + Input Fix — COMPLETE (Mar 23, 2026)
- **EPF Calculation Fixed**: Now uses official band-based lookup (Jadual Ketiga) with 1001 salary bands (RM20 increments up to RM20,000). All EPF amounts are whole RM (no cents). Employer rate: 13% (≤RM5,000) / 12% (>RM5,000). 
- **Dynamic Statutory Recalculation**: When variable earnings (commission, bonus, overtime, etc.) change in Generate/Edit Payslip dialogs, EPF/SOCSO/EIS auto-recalculate via backend API (400ms debounce). Statutory fields remain manually editable.
- **Gross Salary Preview**: Blue box shows estimated gross in Generate Payslip dialog.
- **"0" Input Bug Fixed**: Number inputs now allow clearing to empty before typing. Uses nv()/np()/n0() helpers.
- **New endpoint**: POST /api/hr/statutory/calculate — returns all 6 statutory amounts for a given gross salary.
- Testing: 100% backend + frontend (iteration_32)

### Enhanced HR Payroll Fields — COMPLETE (Mar 22, 2026)
**Income Fields**: Basic Salary, Fixed Allowance (NEW), Housing Allowance, Transport Allowance, Commission (variable/monthly), Incentives (variable), Bonus (variable), Annual Leave Pay (variable), Overtime
**Deduction Fields**: EPF, SOCSO, EIS/SIP, CP39/PCB Tax (NEW), CP38 (NEW), Loan (NEW), Mid-Month Advance (NEW), Salary Adjustment (NEW), Unpaid Leave (NEW)
- Fixed allowance is stored on staff record (monthly fixed); all others are variable per payslip
- Generate Payslip, Edit Payslip, View Payslip, and PayslipPrint all updated
- Testing: 100% backend + frontend (iteration_31)

### Manual Staff-User Link — COMPLETE (Mar 22, 2026)
- "Link user" button replaces "Not linked" badge, opens dropdown to select user
- POST /api/hr/staff/{id}/link-user/{user_id} and DELETE /api/hr/staff/{id}/unlink-user

### Dashboard KPIs + Role Protection — COMPLETE (Mar 22, 2026)
- 8 KPI cards on Admin Dashboard, role guards on 15+ endpoints

### Quick Wins — COMPLETE (Mar 22, 2026)
- DB Indexing (25 indexes), PWA v2, Loading/Empty States

### Previous: Balance Sheet, Backfill, Mobile Responsive, Payroll Portal

## Known Issues
- Pre-existing 500 error on checklist template API (P2)

## Feature Backlog
- (P0) Duplicate Route Refactor (user holding until laptop ready)
- (P1) Unify P&L Systems
- (P1) Notification System — in-app bell + email alerts
- (P1) Trainer Contract Workflow — freelance staff only, per session
- (P1) Post-Training Evaluation — programme-specific questionnaires, 3mo/6mo follow-up
- (P1) Supervisor Portal Enhancement — invoices, feedback, certificates
- (P1) Certificate Generation — PDF template with dynamic fields
- (P1) SaaS Monetization (Stripe)
- (P2) Client/Trainer Portals, Native App, PWA Offline

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
