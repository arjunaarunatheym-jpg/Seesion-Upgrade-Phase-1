# Training Management Platform - Product Requirements Document

## Overview
A comprehensive training management platform for MDDRC (Malaysian Defensive Driving and Riding Centre) with multiple user roles and integrated finance management.

## Core User Personas
- **Admin/Super Admin**: Full system access, user management, session management, finance oversight
- **Finance**: Invoice, payment, expense management, HR & Payroll
- **Trainer**: Training delivery, checklist management, participant tracking
- **Coordinator**: Session coordination, participant management, attendance tracking
- **Participant**: Training completion, indemnity acceptance, check-in/out
- **Supervisor**: Company representative, view training reports

## Tech Stack
- **Frontend**: React + Vite + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB

---

## MEGA E2E TESTING RESULTS (January 3, 2026)

### Test Session Created
- **Program**: Bus Defensive Training
- **Company**: RapidKL
- **Session ID**: d664b79d-91a1-4968-bd72-de82611cdb1f
- **Participants**: 15 total (13 present, 2 absent)
- **Invoice**: INV/MDDRC/2026/01/0002 (RM 15,000 - PAID)

### Phase 1-4 Test Results Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Admin Login | ✅ WORKING | arjuna@mddrc.com.my |
| Program Creation | ✅ WORKING | Bus Defensive Training created |
| Session Creation | ✅ WORKING | With full costing |
| Participant Upload | ✅ WORKING | 15 participants (3 individual, 12 bulk) |
| Pre/Post Test Questions | ✅ WORKING | 40 questions each, 90% pass mark |
| Participant Indemnity | ✅ WORKING | 13/15 signed |
| Participant Clock-in | ✅ WORKING | 13/15 clocked in |
| Coordinator Attendance | ✅ WORKING | 13 present, 2 absent |
| Pre-Test Release | ✅ WORKING | 3 pass, 10 fail |
| Trainer Checklists | ✅ WORKING | 3 trainers, 13 participants |
| Post-Test Release | ✅ WORKING | 12 pass, 1 fail |
| Feedback Submission | ✅ WORKING | 13/13 submitted |
| Chief Trainer Feedback | ✅ WORKING | Submitted |
| Coordinator Feedback | ✅ WORKING | Submitted |
| Invoice Creation | ✅ WORKING | Draft → Issued → Paid |
| **Payment Recording** | ✅ FIXED | Was broken, now working |
| P&L Ledger | ✅ WORKING | Shows RM 20,000 income |
| Petty Cash | ✅ WORKING | RM 359.50 balance |
| HR Payroll APIs | ✅ WORKING | Staff, Payslips, Pay Advice |
| Report Generation | ⚠️ FIXED | LlmChat API updated |
| Pre/Post Test Display | ✅ FIXED | Was showing 0/15, now correct |

### Bugs Fixed During Testing
1. **Payment Recording**: MongoDB ObjectId serialization error - FIXED
2. **Pre/Post Test Count Display**: Coordinator dashboard showing 0/15 - FIXED  
3. **Report Generation**: LlmChat initialization missing args - FIXED
4. **Test Type Mismatch**: API expected 'pre'/'post' but stored 'pre_test'/'post_test' - FIXED

---

## What's Been Implemented

### January 3, 2026 - Security & Stability Improvements

#### Security Features Implemented
- **Rate Limiting**: 100 requests per 60 seconds per IP
- **Login Lockout**: 5 failed attempts = 5 minute lockout
- **Malicious Input Detection**: XSS, SQL injection, MongoDB injection patterns blocked
- **Input Sanitization**: HTML escaping, null byte removal, length limits
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, etc.
- **File Upload Security**: Extension validation, magic byte verification, size limits (10MB max)
- **Dangerous File Blocking**: .exe, .bat, .sh, .ps1, etc. automatically blocked
- **IP Blocking**: Admin can manually block/unblock IPs
- **Security Audit**: Admin dashboard shows rate-limited, blocked, and locked-out IPs

#### Security Endpoints
- `GET /api/health` - Health check with DB status
- `GET /api/security/status` - Security metrics (admin only)
- `POST /api/security/block-ip` - Block IP (admin only)
- `POST /api/security/unblock-ip` - Unblock IP (admin only)
- `GET /api/security/audit-log` - Security event log (admin only)

### January 3, 2026 - P0, P1, P2, P3 Features Complete

#### My Payroll Tab for All Roles (P0 - COMPLETED)
- **Admin Dashboard**: Added MyPayroll tab with data-testid="my-payroll-tab", blue gradient styling
- **Assistant Admin Dashboard**: Already had MyPayroll tab, verified working
- **Trainer Dashboard**: Payroll tab visible under income section
- **Coordinator Dashboard**: MyPayroll tab visible
- All staff can now access their Payslips, Pay Advice, and EA Form at any time

#### Live Document Preview (P1 - COMPLETED)
- **New `DocumentPreview.jsx` Component**: Full-page document preview with:
  - Dark overlay background
  - Zoom controls (50% - 200%)
  - Fullscreen toggle
  - Print and Download buttons
  - Keyboard shortcuts (Esc to close, Ctrl+P to print)
  - Mobile zoom controls
- **Enhanced `PayslipPrint.jsx`**: Added "Full Preview" button that opens DocumentPreview

#### Page Crash Fixes (P3 - COMPLETED)
- **`ResultsSummary.jsx`**: Added null-safe checks for participants array, session data
- **`TrainerChiefFeedback.jsx`**: Added null-safe checks for sessions and feedback template
- Both pages now load without crashing even with empty/null data

#### Profit/Loss Ledger (P2 - NEW)
- **Monthly P&L Comparison**: All 12 months displayed with Income, Expenses, Net Profit, Status
- **YTD Summary Cards**: Total Income, Total Expenses, Net Profit, Profit Margin %
- **Income Sources**: Invoices (auto-aggregated) + Manual one-off entries
- **Expense Tracking**: Payroll, Session Workers, Session Expenses, Petty Cash, Manual entries
- **Expense Breakdown**: Visual category breakdown with percentages and progress bars
- Backend APIs: `/finance/profit-loss`, `/finance/manual-income`, `/finance/manual-expenses`

#### Petty Cash Module (P2 - NEW)
- **Float Management**: Set initial float amount, current balance tracking
- **Expense Recording**: Date, description, amount, category, notes
- **Category Tracking**: Office Supplies, Transport, Refreshments, Postage, Printing, etc.
- **Approval Workflow**: Auto-approve under threshold (default RM 100), manual approval for larger expenses
- **Reconciliation**: Compare physical count with system balance, variance tracking, adjustment transactions
- **Audit Trail**: Full transaction history with who created/approved
- Backend APIs: `/finance/petty-cash/*` (settings, transaction, approve, reject, reconcile, summary)

#### EA Forms Generation (P0)
- **EA Forms Tab** in HR Module: Admin can select staff member and year to generate annual remuneration statement
- Displays: Employee Particulars, Annual Gross Income, Annual Deductions (Employee), Employer Contributions, Monthly Breakdown
- **Printable EA Form** with bilingual format (English/Malay) following Malaysian tax form standards
- Backend API: `/hr/ea-form/{staff_id}/{year}`

#### Self-Service Payroll Portal (P0)
- **MyPayroll Component** for staff to view their own payroll documents
- Integrated into: TrainerDashboard, CoordinatorDashboard, MarketingDashboard
- Features: Payslips tab, Pay Advice tab, EA Form tab (self-service)
- Backend APIs: `/hr/my-payslips`, `/hr/my-pay-advice`, `/hr/my-ea-form/{year}`

#### Statutory Rates Upload (P1)
- Complete Excel upload functionality for EPF, SOCSO, EIS rate tables
- Download template functionality for each rate type
- Rate type selector with visual display of uploaded records

#### Mobile-Friendly UI (P2)
- Responsive TabsList components across all dashboards
- Flex-wrap enabled for tabs on smaller viewports
- Improved spacing and sizing for mobile devices

### January 2, 2026 - HR & Payroll System Complete
- **HR Module with Full Payroll Features**:
  - **Staff Management**: Add/Edit staff with salary, allowances, bank details, NRIC, statutory info
  - **Payroll Period Management**: Open/Close monthly periods (closed = read-only)
  - **Payslip Generation**: 
    - Auto-calculates EPF, SOCSO, EIS with **age-based rules from NRIC**
    - **Editable statutory values** - can override auto-calculated amounts
    - YTD (Year-to-date) tracking
    - Printable payslip with company branding
  - **Pay Advice**: For session workers (trainers/coordinators) with printable output

- **NRIC-Based Age Calculation**:
  - First 6 digits of NRIC = YYMMDD (date of birth)
  - System auto-detects if 60+ and adjusts rates accordingly

- **Statutory Calculation Rules**:
  - **EPF**: 11% employee / 13% employer (below 60); 0% / 4% (60+)
  - **SOCSO**: 0.5% employee / 1.75% employer (below 60); 0% / 1.25% employer only (60+)
  - **EIS**: 0.2% each (below 60); 0% (60+)
  - Wage ceiling: RM6,000 for SOCSO/EIS

- **Period Close Feature**: Once closed, payslips become read-only (is_locked = true)

- **Claim Form UI Improvements**
  - Fixed header layout (single company name, centered with logo)
  - Improved spacing throughout the form
  - Better table formatting and visual hierarchy

### January 2, 2026 - P0 Features Complete
- **Course Registration Form (Claim Form)**: Printable document from Session Costing
  - Component: `frontend/src/components/ClaimFormPrint.jsx`
  
- **Individual Indemnity Form Printing**
  - Component: `frontend/src/components/IndemnityFormPrint.jsx`

### Previous Session Completions
- Super Admin Finance Tab (Data tab with invoice/payment management, audit trail)
- Bulk User Deletion on Users tab
- Score Calculator in Super Admin panel
- Excel Templates download
- Dynamic Trainer Checklist filtering
- Document Styling & Custom Fields
- Session Month Filter

---

## Prioritized Backlog

### P0 - Critical
- [x] ~~Course Registration Form (Claim Form)~~ - DONE
- [x] ~~Individual Indemnity Form Printing~~ - DONE
- [x] ~~EA Forms Generation~~ - DONE (Jan 3, 2026)
- [x] ~~Self-Service Payroll Portal~~ - DONE (Jan 3, 2026)
- [x] **My Payroll Tab for All Roles** - DONE (Jan 3, 2026) - Added to Admin, Assistant Admin, Coordinator, Trainer dashboards

### P1 - High Priority
- [x] HR Module - Staff Management - DONE
- [x] **Payslip Generation** - DONE (with statutory deductions, YTD tracking)
- [x] **Pay Advice** - DONE (for session workers)
- [x] EPF/SOCSO/EIS Excel upload for statutory rate tables - DONE
- [x] **Live Document Previews** - DONE (Jan 3, 2026) - Full-page preview with zoom, print, download

### P2 - Medium Priority
- [x] Mobile-friendly UI - DONE (responsive tabs across all dashboards)
- [x] **Profit/Loss Ledger** - DONE (Jan 3, 2026) - Monthly comparison, YTD, manual entries
- [x] **Petty Cash Module** - DONE (Jan 3, 2026) - Float, expenses, approvals, reconciliation
- [ ] Password protection for Data tab

### P3 - Bug Fixes/Refactoring
- [x] **Fix `ResultsSummary.jsx` page crash** - DONE (Jan 3, 2026) - Null-safe checks added
- [x] **Fix `TrainerChiefFeedback.jsx` page crash** - DONE (Jan 3, 2026) - Null-safe checks added
- [x] **Fix P&L Ledger Double-Counting Bug** - DONE (Jan 3, 2026) - Fixed critical bug in `/api/finance/profit-loss` that was:
  - Double-counting trainer and coordinator fees (duplicate processing loops)
  - Using `created_at` instead of session's `start_date` for month attribution
  - Now correctly attributes expenses to the session's execution month (Dec 2025 vs Jan 2026)
- [ ] Code refactoring (split large files: server.py, HRModule.jsx)
- [ ] Conditional F&B Expense Logic

---

## Key Files Reference
- `backend/server.py` - Main FastAPI server (HR APIs, P&L, Petty Cash - 12000+ lines)
- `frontend/src/pages/FinanceDashboard.jsx` - Finance interface with HR, P&L, Petty Cash tabs
- `frontend/src/components/HRModule.jsx` - HR module with Staff, Payroll, EA Forms
- `frontend/src/components/ProfitLossLedger.jsx` - P&L monthly overview and manual entries
- `frontend/src/components/PettyCash.jsx` - Petty cash management with approvals
- `frontend/src/components/MyPayroll.jsx` - Self-service payroll portal
- `frontend/src/components/PayslipPrint.jsx` - Payslip print component
- `frontend/src/components/PayAdvicePrint.jsx` - Pay advice print component
- `frontend/src/components/ClaimFormPrint.jsx` - Claim form print
- `frontend/src/components/IndemnityFormPrint.jsx` - Indemnity print

---

## HR Module Database Schema (hr_staff collection)
```json
{
  "id": "uuid",
  "user_id": "optional - link to users collection",
  "employee_id": "EMP001",
  "full_name": "string",
  "designation": "string",
  "department": "string",
  "date_joined": "date",
  "bank_name": "string",
  "bank_account": "string",
  "basic_salary": 2700.00,
  "housing_allowance": 0,
  "transport_allowance": 0,
  "meal_allowance": 0,
  "phone_allowance": 0,
  "other_allowance": 0,
  "epf_number": "string",
  "socso_number": "string",
  "tax_number": "string",
  "employee_epf_rate": 11,
  "employer_epf_rate": 13,
  "is_active": true
}
```

---

## Test Credentials
- **Admin**: arjuna@mddrc.com.my / Dana102229
- **Finance**: munirah@sdc.com.my / mddrc1

---

## January 11, 2026 - Finance Dashboard Year Filter & Credit Note Workflow

### Year-by-Year Filter for Finance Dashboard (P1 - COMPLETED)
- **Problem**: Finance Dashboard showed all invoices/data regardless of year; user couldn't filter by financial year
- **Solution**: 
  - Added `Financial Year` dropdown selector in Finance Dashboard
  - Backend `/api/finance/dashboard` and `/api/finance/invoices` endpoints now accept `?year=YYYY` parameter
  - Dashboard cards (Total Invoices, Collected, Outstanding, Payables) filter by selected year
  - Invoices tab also filters by selected year
  - Year selector always shows current year ± 2 years (e.g., 2024, 2025, 2026) plus any years with data
  - "Showing data for YYYY" indicator displays selected year
- **Files Modified**: `backend/server.py`, `frontend/src/pages/FinanceDashboard.jsx`

### Credit Note Workflow Enhancement (P1 - COMPLETED)
- **Problem**: Credit Notes were created as "draft" and never issued; no print/download functionality
- **Solution**:
  - Added status workflow: Draft → Approved → Issued (same as Invoices)
  - New API endpoints:
    - `POST /api/finance/credit-notes/{cn_id}/approve` - Approve a draft CN
    - `POST /api/finance/credit-notes/{cn_id}/issue` - Issue a CN (can skip approve)
  - Credit Notes tab now shows:
    - Date column
    - Status badges (Draft=Yellow, Approved=Blue, Issued=Green)
    - Actions column with:
      - Approve button (for draft CNs)
      - Issue button (for draft/approved CNs)
      - Print button (opens print preview)
      - Download button (opens print for PDF save)
  - **Auto-Issue on Payment**: When recording a payment with CN checkbox, the Credit Note is now automatically issued
  - **Print Preview**: Professional Credit Note document with:
    - Company header with logo and custom fields
    - Red-themed styling (contrasting with Invoice blue)
    - CN details (number, date, invoice reference)
    - Reason/description section
    - Amount displayed prominently
    - Status badge
    - Footer with company info
- **Files Modified**: `backend/server.py`, `frontend/src/pages/FinanceDashboard.jsx`


### Credit Note Management in Data Tab (P1 - COMPLETED)
- **Problem**: Credit Notes had no editing capabilities like Invoices; no backdate, void, or audit trail
- **Solution**:
  - Added new **Credit Notes** tab in Data Management (between Invoices and Payments)
  - Backend endpoints added:
    - `PUT /api/finance/admin/credit-notes/{cn_id}/backdate` - Change CN date with reason
    - `PUT /api/finance/admin/credit-notes/{cn_id}/edit` - Edit details with reason
    - `PUT /api/finance/admin/credit-notes/{cn_id}/void` - Void CN with reason
    - `PUT /api/finance/admin/credit-notes/{cn_id}/number` - Change CN number with reason
  - All changes logged to Audit Trail with:
    - Action type (Backdated, Edited, Voided, Number Changed)
    - Record reference (CN number, company, amount)
    - Field changed with old → new values
    - User who made the change
    - Mandatory reason
    - Timestamp
  - Frontend features:
    - Search by CN number, company, invoice
    - Filter by status (All, Draft, Approved, Issued, Voided)
    - Action buttons: Edit Number (#), Backdate (📅), Edit Details (✏️), Void (🚫)
    - Modal dialogs for each action with mandatory reason field
- **Files Modified**: `backend/server.py`, `frontend/src/components/DataManagement.jsx`


### Recent Payments Auto-Load Fix (P1 - COMPLETED)
- **Problem**: Recording a payment didn't show in "Recent Payments" section until manual refresh
- **Solution**: 
  - Added `GET /api/finance/payments` endpoint to fetch all payments with invoice info
  - Added useEffect to auto-load payments when Payments tab is activated
- **Files Modified**: `backend/server.py`, `frontend/src/pages/FinanceDashboard.jsx`

### Admin Finance Tab Year Filter (P1 - COMPLETED)
- **Problem**: Admin Dashboard's Finance tab showed all-time invoices without year filtering
- **Solution**:
  - Added `financeYear` state and year selector dropdown
  - Created `loadFinanceSummaryByYear()` function that calls `/api/finance/dashboard?year=YYYY`
  - Dashboard cards now filter by selected year
  - Year selector shows current year ± 2 years
- **Files Modified**: `frontend/src/pages/AdminDashboard.jsx`

### Payables Print Feature (P1 - COMPLETED)
- **Problem**: No way to print payables report for accounting purposes
- **Solution**:
  - Added Print button to Payables tab header
  - Created `handlePrintPayables()` function that generates professional printout with:
    - Company header with logo
    - Summary cards (Trainer Fees, Coordinator Fees, Marketing Commission, Total)
    - Detailed table with Name, Role, Session, Amount columns
    - Category subtotals (color-coded by type)
    - Grand total row
    - Signature areas (Prepared By, Approved By)
    - Footer with report date and payment policy
- **Files Modified**: `frontend/src/pages/FinanceDashboard.jsx`

### Staff Portal Payables Verification (VERIFIED)
- Trainers can view their pending income via `/api/finance/income/trainer/{id}`
- Coordinators can view via `/api/finance/income/coordinator/{id}`
- Marketing can view via `/api/finance/income/marketing/{id}`
- All endpoints return correct amounts matching the Payables tab


### Payables Excel Export & Period Management (P1 - COMPLETED)
- **Problem**: No way to export payables to Excel format; no period closing to prevent changes
- **Solution**:

**1. Excel Export Feature**
  - Added `GET /api/finance/payables/export-excel?year=YYYY&month=MM` endpoint
  - Returns data grouped by staff name with session details
  - Columns: NAME, INVOICE NUMBER, TRAINING DATE, POSITION, COMPANY, DETAILS, PRICE
  - Includes subtotals per person and grand total
  - Exports as CSV file (opens in Excel)
  - Data comes from same endpoints trainers/coordinators/marketing see in their portals

**2. Period Management (Open/Close)**
  - Added `payables_periods` collection to track period status
  - Endpoints:
    - `GET /api/finance/payables/periods` - List all periods
    - `POST /api/finance/payables/periods` - Create/open period
    - `POST /api/finance/payables/periods/{id}/close` - Close period
    - `POST /api/finance/payables/periods/{id}/reopen` - Reopen (admin only, requires reason)
    - `GET /api/finance/payables/period-status?year=&month=` - Check period status
  - When period is CLOSED:
    - Red "CLOSED" badge displayed
    - Warning banner shown
    - Mark as Paid buttons are disabled
    - Admin can reopen with mandatory reason (logged to audit trail)

**3. Frontend UI Updates**
  - Month/Year selector dropdowns
  - OPEN/CLOSED status badge
  - Close Period button (red, only when open)
  - Reopen button (green, only when closed, admin only)
  - Excel export button (green)
  - Period status banner when closed

- **Files Modified**: `backend/server.py`, `frontend/src/pages/FinanceDashboard.jsx`



---

## January 11, 2026 - P0 Bug Fix & P&L Enhancement

### P0: Re-open Period Dialog Fix (COMPLETED)
- **Problem**: The "Reopen" button for locked Pay Advice periods used `window.prompt()` which:
  - Doesn't work on mobile browsers
  - Is a poor UX (native browser dialog)
  - Was inconsistent with the rest of the app's modal dialogs
- **Solution**:
  - Replaced `window.prompt()` in `HRModule.jsx` with a proper Shadcn `Dialog` component
  - Added state: `unlockPayAdviceDialog` with `{open, id, reason}`
  - Created `confirmUnlockPayAdvice()` handler that validates reason (min 5 chars) before API call
  - Dialog includes: title, description, textarea for reason, Cancel/Unlock buttons
  - Same pattern already used in `FinanceDashboard.jsx` for Payables period reopen
- **Files Modified**: `frontend/src/components/HRModule.jsx`

### P&L Enhancement: CEO P&L View & Sub-ledger Reports (COMPLETED)
- **Problem**: User wanted programme-level P&L breakdown matching their Excel template with:
  - Dynamic income/expense breakdown by programme
  - Sub-ledger views for Trainers, Marketing, Payroll
  - CEO-style insight view with margins

- **Solution - Backend Endpoints Added**:
  - `GET /api/finance/profit-loss/by-programme?year=YYYY` - Programme-level P&L with:
    - Revenue per programme (linked via sessions → invoices)
    - Direct costs per programme (trainer fees, coordinator fees, marketing, session expenses)
    - Gross profit and margin % per programme
    - Overhead costs (payroll, petty cash, manual) shown separately
    - Summary with net profit and net margin %
  
  - `GET /api/finance/subledger/trainers?year=YYYY` - Trainer & Coordinator Sub-ledger:
    - Aggregated by person (earned, paid, balance)
    - Session-level detail with dates, programme, amounts, status
  
  - `GET /api/finance/subledger/marketing?year=YYYY` - Marketing Commission Sub-ledger:
    - Aggregated by marketer
    - Client/campaign detail with commission rates
  
  - `GET /api/finance/subledger/payroll?year=YYYY` - Staff Payroll Register:
    - Aggregated by employee
    - Monthly breakdown with gross, EPF, SOCSO, EIS, net

- **Solution - Frontend (ProfitLossLedger.jsx)**:
  - **New Tabs Added**:
    - "CEO P&L" - Programme breakdown table with expandable rows for cost detail
    - "Trainers" - Trainer & Coordinator sub-ledger with expandable session detail
    - "Marketing" - Marketing commission sub-ledger with client detail
    - "Payroll" - Staff payroll register with monthly breakdown
  - **Features**:
    - Expandable rows (click to see detail)
    - Color-coded margins (green >30%, yellow 15-30%, red <15%)
    - Summary cards showing totals and overhead breakdown
    - Year selector (dynamic data loading)

- **Files Modified**: 
  - `backend/server.py` - Added 4 new endpoints
  - `frontend/src/components/ProfitLossLedger.jsx` - Complete rewrite with new tabs

### Key Architecture Notes
- **No new database collections** - All new endpoints aggregate existing data from:
  - `db.programs` - Programme definitions
  - `db.sessions` - Sessions with `program_id` field
  - `db.invoices` - Invoice amounts
  - `db.trainer_fees`, `db.coordinator_fees`, `db.marketing_commissions` - Direct costs
  - `db.session_expenses` - F&B, venue costs
  - `db.hr_payslips` - Payroll data
  - `db.petty_cash_transactions`, `db.manual_expenses` - Overhead

- **Dynamic Programme Support**: New programmes automatically appear in CEO P&L when sessions are created with that `program_id`



### General Ledger View (P1 - COMPLETED)
- **Problem**: User wanted a proper General Ledger with double-entry (DR/CR) format matching their Excel template
- **Solution**:

**1. Chart of Accounts (Static Config)**
  - Asset accounts (1xxx): Cash at Bank, Petty Cash, Accounts Receivable
  - Liability accounts (2xxx): AP, Trainer/Coordinator/Marketing Payable, EPF/SOCSO/EIS Payable, Salary Payable
  - Income accounts (4xxx): Training Income by programme type (Cars, Motorcycles, Heavy Vehicles, Bus), Other Income
  - Expense accounts (5xxx): Trainer/Coordinator Fees, Marketing Commission, Staff Salaries, Employer Contributions, F&B, Venue, HRDCorp Levy, Petty Cash, Other

**2. General Ledger Endpoint** (`GET /api/finance/general-ledger?year=YYYY&month=MM`)
  - Generates double-entry journal entries from all financial transactions:
    - Invoices: DR Accounts Receivable, CR Training Income (by programme)
    - Payments: DR Bank, CR Accounts Receivable  
    - Trainer Fees: DR Trainer Fees Expense, CR Trainer Payable
    - Coordinator Fees: DR Coordinator Fees Expense, CR Coordinator Payable
    - Marketing Commission: DR Marketing Expense, CR Marketing Payable
    - Payroll: DR Salaries + Employer Contributions, CR EPF/SOCSO/EIS/Salary Payable
    - Session Expenses: DR F&B/Venue/HRDCorp, CR Accounts Payable
    - Petty Cash: DR Petty Cash Expenses, CR Petty Cash
    - Manual Income/Expenses: Appropriate DR/CR entries
  - Returns: Journal entries + Trial Balance (aggregated by account)
  - Verifies debits = credits (balanced check)

**3. Frontend Tab** (ProfitLossLedger.jsx - "General Ledger" tab)
  - Month selector dropdown (filter by specific month or all months)
  - Print button - Opens professional printout with:
    - Journal entries table (Entry #, Date, Reference, Account Code, Account Name, Description, Debit, Credit)
    - Totals row with balanced/unbalanced indicator
    - Trial Balance table
  - Download CSV button - Exports full GL data to CSV (opens in Excel)
  - Journal entries table with color-coded Debit (red) and Credit (green)
  - Trial Balance section with account types badges (Asset=blue, Liability=purple, Income=green, Expense=red)
  - Net balance shown as DR or CR

- **Files Modified**: `backend/server.py`, `frontend/src/components/ProfitLossLedger.jsx`

---

## P0/P1 Features - January 16, 2026

### P0: Billing Parties / Vendors Feature ✅ COMPLETE

**Purpose**: Allow invoicing to alternative billing entities (e.g., HRDC, sponsors) instead of the company receiving training.

**Implementation**:
1. **Backend API Endpoints** (`server.py` lines 1609-1673):
   - `POST /api/finance/billing-parties` - Create billing party
   - `GET /api/finance/billing-parties` - List active billing parties
   - `PUT /api/finance/billing-parties/{id}` - Update billing party
   - `DELETE /api/finance/billing-parties/{id}` - Soft delete (is_active=False)

2. **BillingParty Model Fields**:
   - id, name, registration_no, address_line1, address_line2
   - city, postcode, state, country, phone, email, contact_person
   - is_active, created_at

3. **Frontend UI** (`FinanceDashboard.jsx`):
   - Settings tab: "Billing Parties / Vendors" section
   - Add/Edit/Delete billing parties via modal
   - Invoice Edit modal: "Quick Fill" dropdown to apply billing party details to Bill To fields

### P1: Company Registration & Address Fields ✅ COMPLETE

**Purpose**: Capture detailed company information for auto-populating invoices.

**Implementation**:
1. **Company Model Updated** (`server.py`):
   - Added: registration_no, address_line1, address_line2, city, postcode, state
   - Added: phone, email, contact_person

2. **Frontend UI** (`AdminDashboard.jsx`):
   - Create Company form: All new fields with grid layout
   - Edit Company form: All new fields with scrollable modal
   - Company list: Shows registration number if available

**Test Results**: 
- Backend: 10/10 API tests passed
- Frontend: All UI features working
- Test file: `/app/tests/test_billing_parties_companies.py`


---

## MARKETING PORTAL - PHASE 1 ✅ COMPLETE (January 19, 2026)

### Overview
A full-featured quotation management system for the marketing team, allowing them to create quotations, get admin approval, and generate professional PDF packages.

### Features Implemented

#### 1. Client Management ✅
- Create and manage marketing clients
- Store company details, contact person, phone, email, address
- Client list with search functionality

#### 2. Quotation Creation ✅
- Create quotations with unique numbering format: `QOU/MDDRC/YYYY/MM/0001`
- Select programme, set pricing (per pax or per group)
- Add description items (admin-managed templates)
- Custom remarks and terms

#### 3. Quotation Workflow ✅
- Status flow: Draft → Pending Approval → Approved/Rejected → Sent → Accepted/Declined
- Admin approval queue in Admin Dashboard > Quotations tab
- Marketer can edit rejected quotations

#### 4. Accept Quotation with Training Details ✅ NEW
- When marking quotation as "Accepted", dialog opens requiring:
  - Training Date (date picker)
  - Venue / Location (text input)
- Training details saved to quotation and shown in PDF

#### 5. Multi-Page PDF Generation ✅ UPDATED
- **Uniform Header/Footer**: Same style as invoices across all pages
- **Text Wrapping**: Description column properly wraps long programme names
  
- **Page 1: Cover Letter**
  - Company header with logo
  - Recipient details (client name, address)
  - Custom content from admin template
  - Signature block
  
- **Page 2: Quotation Details**
  - Quotation number, date, validity in info box
  - Client info box
  - Training details (date/venue) if accepted
  - Pricing table with text-wrapped description
  - Description items (properly wrapped)
  - SST if applicable
  - Total amount
  - Prepared/Approved signatures
  
- **Pages 3-5: Terms & Conditions**
  - Admin-customizable content via rich text editor
  - Paginated automatically based on content length
  
- **Page 6: Registration Form** ✅ NEW (replaces Attendance List)
  - Account Manager & Order Details box
  - Tick boxes: New Registration, Company, Individual
  - Course Information section (auto-populated)
  - Participant's Particulars table (Full Name, Corporate Email, Tel/Mobile, IC/Passport, Fees, Signature)
  - PDPA Consent section
  - Authorized Signatory & Company Stamp section

#### 6. Admin PDF Templates Management ✅ UPDATED
  - Custom content from admin template
  - Paginated automatically

- **Page 7: Attendance/Participants List**
  - Programme, client, date, venue
  - Table columns: No, Full Name, IC Number, Company Name, Citizen, Signature
  - Rows based on num_participants (min 10)
  - Continues to next page if needed

#### 6. Admin PDF Templates Management ✅ NEW
- Located in Admin Dashboard > Quotations tab
- "PDF Document Templates" card with Edit button
- Cover Letter template with placeholders:
  - `{{programme_name}}`
  - `{{company_name}}`
  - `{{contact_person}}`
  - `{{quotation_number}}`
- Terms & Conditions template (multi-page support)

### Technical Implementation

#### Backend (`server.py`)
- `QuotationPDF` class with Unicode font support (DejaVu)
- `sanitize_text_for_pdf()` for character handling
- Endpoints:
  - `GET /api/marketing/quotations/{id}/download-pdf` - Generate PDF
  - `GET /api/marketing/pdf-templates` - Get templates
  - `PUT /api/marketing/pdf-templates` - Update templates
  - Updated: `POST /api/marketing/quotations/{id}/client-response` - Now requires training_date and venue for "accepted"

#### Frontend
- `MarketingDashboard.jsx`: Accept dialog, PDF download button, training details display
- `AdminDashboard.jsx`: PDF templates management section

### Test Results (Iteration 11)
- Backend: 100% (12/12 tests passed)
- Frontend: 100% (all features working)
- Test file: `/app/tests/test_quotation_pdf.py`

### Access
- Marketing Users: Users with `additional_roles: ["marketing"]`
- Credentials: `malek@mddrc.com.my` / `mddrc1` or `chandra@mddrc.com.my` / `mddrc1`
- Access via: Dashboard → Marketing button

---

## UPCOMING TASKS (P1 Priority)

### Marketing Portal Phase 2
1. Extended quotation statuses (Negotiating, Revised, Expired, Converted)
2. One-click conversion: Accepted quotation → Training session
3. CSV/Excel export functionality
4. Performance reports for marketers

### Finance
1. Formal Accountant P&L view
2. Year-over-Year (YoY) analysis

### System
1. Backend refactoring (`server.py` → separate router files)
2. Frontend refactoring (break down AdminDashboard.jsx, MarketingDashboard.jsx)

---

## BACKLOG (P2 Priority)

1. Post-Training Evaluation System
2. Billing party deletion verification
3. Invoice "Undo" and "Replace" button verification
4. Re-adding dummy participant verification

