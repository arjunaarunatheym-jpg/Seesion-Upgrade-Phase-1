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

## P0 — In Progress / Pending
- System-wide digital signature audit & implementation (Receipts, Payslips, Pay Advice, EA Forms, Claim Forms, Credit Notes)

## P1 — Upcoming
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
