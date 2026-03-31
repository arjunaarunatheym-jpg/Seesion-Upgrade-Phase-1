# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for MDDRC. Manages training sessions, participants, invoicing, and coordination across multiple user roles.

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python), Database: MongoDB, Auth: JWT + bcrypt

## Current Status (Mar 2026)

### App Hardening — Testing, Security, Backup, Business Settings — COMPLETE (Mar 28, 2026)
- **Automated Test Suite**: 23 pytest tests covering Auth, Health, Settings, Companies, Programs, Sessions, Invoices, HR/Payroll, Statutory Calculations, Finance Reports, AR Aging, KPIs, Backup, Leads, Users. All pass.
- **System Health Check**: GET /api/health (public) + GET /api/health/detailed (admin) — tests DB, collections, statutory rates, settings, admin user, invoice counter
- **Data Backup/Export**: Full backup (all collections as single JSON), individual collection export (JSON or CSV), collection inventory with record counts. In Admin Settings page.
- **Password Strength**: Min 8 chars, must include number + letter
- **Business Settings**: SST rate, Company Reg No, SST Reg No, Bank details, Document prefixes (INV/QUO/CN), EPF/SOCSO/EIS employer numbers, Payment terms — all configurable in Admin Settings without code changes

### Financial Reporting Overhaul — COMPLETE (Mar 28, 2026)
- **Unified P&L**: Journal-based "P&L Statement" is now default tab. Old "CEO P&L" renamed to "P&L by Programme" (secondary)
- **AR Aging Report**: New "Receivables Aging" tab with 3 views (Summary bar chart, By Invoice with tables, By Company matrix), CSV export, 90+ day overdue alert
- **Yearly Segregation**: Verified all reports correctly filter by year parameter (2025 vs 2026)
- **YoY Comparison**: Confirmed working — compares two years side by side with variance % and trend indicators
- Backend: New GET /api/finance/ar-aging endpoint
- Frontend: New ARAgingTab.jsx, reordered ProfitLossLedger tabs

### Company Combobox for Session Invoices — COMPLETE (Mar 28, 2026)
- **Searchable + auto-create**: Replaced static Select dropdown with CompanyCombobox in "Additional Invoices (Other Companies)" section of Session Costing
- Type to search existing companies, or type a new name and click "Create [name]" to auto-create company record
- Auto-refreshes company list after creation — no need to leave and create company separately

### Clickable KPI Cards with Drill-Down — COMPLETE (Mar 27, 2026)
- **Admin Dashboard**: All 8 KPI cards clickable with drill-down detail lists
- **Admin Finance Tab**: All 4 finance cards clickable with drill-down
- **Finance Dashboard (/finance)**: All 4 cards (Total Invoices, Collected, Outstanding, Payables) clickable with drill-down
- Backend endpoint: GET /api/admin/kpi-drilldown/{kpi_type}
- Shared component: KpiDrilldown.jsx with type-specific list renderers

### Mobile Dialog Scroll Fix — COMPLETE (Mar 26, 2026)
- **Global fix**: Added `max-h-[90vh] overflow-y-auto` to base `DialogContent` component
- All dialogs (Leads, Payslips, Staff, Sessions, etc.) now scrollable on mobile with buttons always reachable

### EPF Band-Based Calculation + Dynamic Statutory Recalc + Input Fix — COMPLETE (Mar 23, 2026)
- **EPF Calculation Fixed**: Band-based lookup (Jadual Ketiga) with 1001 salary bands. Whole RM amounts (no cents). Employer rate: 13% (≤RM5,000) / 12% (>RM5,000).
- **Age-Aware Statutory**: Age 60+ → EPF employee 0%, employer 4%. SOCSO employee 0. Age 57+ → EIS 0.
- **Dynamic Recalculation**: Variable earnings changes auto-update statutory (400ms debounce).
- **Gross Preview**: Blue box shows estimated gross in Generate Payslip dialog.
- **Mobile Scroll Fix**: Dialog uses flex layout with fixed buttons at bottom.
- **"0" Input Bug Fixed**: Number inputs allow clearing to empty.
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
