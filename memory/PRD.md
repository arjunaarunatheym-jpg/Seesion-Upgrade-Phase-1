# MDDRC Training Management System — PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC).

## Core Requirements
- Strict financial data integrity
- Role-based UX (Admin, Coordinator, Trainer, Finance, Participant, SuperAdmin, AssistantAdmin)
- PDF/DOCX document generation (html2pdf.js + html-docx-js-typescript)
- Digital signature uploads across all roles
- Automated e-certificate generation via drag-and-drop visual designer
- Bulk and single participant management

## Tech Stack
- **Backend**: FastAPI + MongoDB (38+ routers)
- **Frontend**: React + Shadcn/UI + Tailwind
- **Document Generation**: html2pdf.js (PDF), html-docx-js-typescript (Word), FPDF (server-side)

## What's Been Implemented

### Session Management
- Full CRUD, participant assignment (bulk + single), trainer/coordinator assignment
- Protected field stripping on session updates
- Coordinator query includes both active + draft sessions

### Participant Management (April 2026)
- Admin + Coordinator: Bulk Upload + Add Participant (single) buttons per session card
- Coordinator "My Sessions": Sessions grouped by month/year

### Participant Portal — Active vs Past Sessions (April 2026)
- Overview + Details tabs: Only active sessions shown; past sessions collapsed
- Certificates tab: Shows ALL sessions
- Tab order: Overview, My Details, Tests, Checklists, Certs, Settings
- Participant session filtering: Backend filters by participant_ids (fixed data leak bug)

### Trainer Checklist — Self-Select & Swipe-Through (April 2026)
- **Self-Select Flow**: Trainers see ALL session participants with search bar
- **Swipe-Through UI**: Prev/Next navigation with progress bar

### Document Generation
- Quotation PDF/Word with digital signatures (marketer + approver)
- Invoice, Receipt, Credit Note, Payslip, Pay Advice, Claim Form, Indemnity Form printing

### Certificate Designer
- Drag-and-drop visual editor (CertificateDesigner.jsx)

### Digital Signatures
- DigitalSignatureManager across all role dashboards
- Signature embedding in Quotation PDF/Word

### Payment Reversal System (April 18, 2026)
- Super Admin only, 3-step formal flow, full audit trail
- Reverses payment, voids linked credit notes + journal entries, reverts invoice status

### Ad-Hoc Invoice System (April 20, 2026) — NEW
- **Standalone invoices** not tied to training sessions (Finance + Admin access)
- **Same INV numbering sequence** as session invoices
- **Custom billing entity**: company name, address, reg no, contact person, email, phone
- **Flexible line items**: multiple rows with description, qty, unit price, auto-calculated amount
- **Flexible SST %**: optional, configurable percentage (0% default, ready for future SST)
- **Optional references**: link to existing session/invoice + free-text reference field
- **Discount & rounding** support
- **"Ad-Hoc" badge** in invoice list + reference text shown in session column
- Use case: Billing shortfalls to different company entities, venue rental, consulting fees

### Bug Fixes (April 20, 2026)
- Quotation PDF: Address text wrapping (cell_safe → multi_cell_safe) for long addresses
- Quotation PDF: Digital signature embedding (marketer/approver queries now include digital_signature field)
- Quotation dialog: Added "Download Word" button alongside PDF download
- Trainer checklist: State reset on participant navigation
- Feedback submission: responses type dict → Any
- Coordinator checklist visibility: queries now hit vehicle_checklists collection

### God Mode Safeguard & Duplicate Journal Audit (Feb 2026)
- **God Mode downgrade blocked**: `PUT /api/superadmin/invoices/{id}` now rejects status downgrades that would corrupt journals (paid/issued/partially_paid → draft/voided/issued). Users are told to use the formal Reversal flow.
- **Duplicate Journal Audit UI**: Super Admin → Reversals tab has a "Duplicate Journal Cleanup" card with two actions:
  1. Diagnose (read-only) — lists all invoices/payments that have more than one active issuance journal.
  2. Repair — voids all later duplicate journals per source (keeps earliest as authoritative), fully audited with reason.
- Backend endpoints: `GET /superadmin/audit/duplicate-invoice-journals`, `POST /superadmin/audit/repair-duplicate-journals`

### Payables Excel Export Upgrade (Feb 2026)
- Added **Summary** sheet as the first tab of `payables_{year}_{month}.xlsx`, grouped by payee (A-Z), with per-person subtotals and Grand Total. Each summary row includes the linked Invoice Number.
- Added an **Invoice #** column (col A) to the four existing detail sheets (Trainer Fees, Coordinator Fees, Marketing Commission, Administration Fees).
- Invoice lookup: `session_id` → `invoices.invoice_number` (voided invoices excluded). Sessions with multiple invoices join numbers with " / "; sessions with none show "— No Invoice —".
- No changes to financial calculations, statuses, or DB records.
- File: `/app/backend/routes/finance_payables.py::export_payables_excel`.

### Full Payment History — Phase 1 (Feb 2026)
- **New Finance tab** `Payment History` (data-testid=`payment-history-tab`) — server-side searchable, filterable, sorted, paginated read-only ledger. Complements (does NOT replace) the existing Recent Payments widget.
- **Backend**: `GET /api/finance/payments/history` (query: q, date_from, date_to, payment_method, funding_source, status, sort, page, page_size). Response envelope: `{ items, page, page_size, total, total_pages, sort, filters }`. Search matches receipt/reference/HRDCorp invoice #, plus invoice/company/programme via join. Sorts: newest/oldest/highest/lowest. Default page_size=25, max=100.
- **CSV export**: `GET /api/finance/payments/history/export` (hard-capped at 5000 rows).
- **Detail view**: `GET /api/finance/payments/{id}/detail` returns payment, invoice, session, programme, recorder — read-only.
- **Recent Payments** widget now has a "View All Payments" button (data-testid=`view-all-payments-btn`) that switches to the Payment History tab.
- **Indexes** (added via `/app/backend/add_payment_history_indexes.py`): payment_date_created_desc, payment_amount, payment_method, payment_type, payment_status, payment_invoice_id, payment_receipt_number, payment_reference_number, invoice_number_idx, invoice_company_name_idx, invoice_bill_to_name_idx.
- **Financial logic**: NOT modified. Read-only guarantee asserted by pytest.
- **Tests**: 18 tests in `/app/backend/tests/test_payment_history.py` — all passing (default sort, pagination, page-size, >100 records access, search by invoice/receipt/company, date/method/funding filters, empty state, auth 403/401, recent-payments regression, existing-payments-unchanged, payment detail, sort highest, status=reversed).
- **Frontend**: `/app/frontend/src/components/finance/PaymentHistoryTab.jsx` (search debounced 400 ms; filters, sort, page-size, pagination controls; detail dialog; CSV export; empty/loading/error states).

## P0 — In Progress / Pending
- System-wide digital signature audit & implementation (Receipts, Payslips, Pay Advice, EA Forms, Claim Forms, Credit Notes)
- File & Media Storage (Emergent Object Storage) — deferred by user; will pick up when requested

## P1 — Upcoming
- Payment History polish (default status filter to 'All' if user prefers) + Phase 2 (payment integrity / reversal rules moved into the history page)
- Email integration (Resend) + WhatsApp link integration
- Trainer Contract Workflow
- Session P&L / Profitability view (revenue vs expenses per session)

## P2 — Future/Backlog
- Post-Training Evaluation System (3/6 month feedback)
- Multi-tenancy & SaaS (Stripe)
- Supervisor Portal / Client Self-Service Portal
- Native Mobile App (Capacitor)

## Refactoring Backlog
- Break down `sessions_new.py` (~2300+ lines) into smaller route modules
- Delete CertificateAdjuster.jsx (dead code)
- Extract HTML generators from MarketingDashboard.jsx (~1700 lines) to utils
- Mobile responsiveness audit on older Admin/Coordinator tables

## Phase 3A Remediation — 2026-02 (STOPPED for independent review)
- Consolidated Phase 3A source-audit remediation completed (41 items).
- Added canonical SuperAdmin auth helper (`services/superadmin_auth.py`) used
  by BOTH legacy portal and new correction endpoints (Section A).
- Added canonical Payment Reversal engine (`services/payment_reversal.py`)
  delegated by legacy /payments/{id}/void, formal /payment-reversal/execute,
  and preview. Idempotent, source_payment_id scoped, SoT-derived status.
- FinancialWriteGuard now treats `status` as a locked lifecycle field;
  Credit Notes may be created ONLY against issued/partially_paid/paid.
- FinancialSourceOfTruth: legacy voided payments treated non-active
  (excluded from paid + outstanding). Added invoice_date/created_at/
  tax_amount/subtotal to invoice snapshot for display.
- All old finance bypass endpoints (edit-paid, backdate, override,
  edit-number, renumber, revert-status, reverse-void) reject
  locked/terminal invoices with concrete 409 codes.
- Terminal invoices are never resurrected by value correction.
- Session archive writes canonical `is_archived` + `completion_status`
  = 'archived' + archive_reason/archived_at/archived_by (legacy `archived`
  mirrored).
- Superadmin session cascade only rewrites pre-issue invoices.
- Payment UI: unsafe fallback to invoice.total_amount removed; button
  disabled while loading/failed/fully-settled/over-outstanding.
- Fixed masking tests 16 / 34 / 48. Added new endpoint-level tests 69–85.
- Regression: Phase 3A 85/85 · Phase 2 SoT 44/44 · Phase 1 History 26/26.
- NO deployment. NO Phase 3B work started. NO bulk historical rewrite.
- Review bundle: `/app/memory/PHASE_3A_REMEDIATION_REVIEW_BUNDLE.txt`.

