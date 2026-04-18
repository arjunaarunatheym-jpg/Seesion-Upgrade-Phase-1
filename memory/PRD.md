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
- **Self-Select Flow**: Trainers see ALL session participants with search bar. They "Claim" participants to inspect, other trainers see who's claimed/taken.
- **Stats Bar**: Total / Mine / Available / Done filter buttons
- **Claim/Unclaim API**: `POST/DELETE /trainer-checklist/{session_id}/claim/{participant_id}`
- **Swipe-Through UI**: After claiming, trainer sees one participant at a time. Prev/Next navigation with progress bar. Auto-advances to next participant after submission.
- Backend: `assigned-participants` endpoint shows all participants with claim status and checklist submission status

### Document Generation
- Quotation PDF/Word with digital signatures (marketer + approver)
- Invoice, Receipt, Credit Note, Payslip, Pay Advice, Claim Form, Indemnity Form printing

### Certificate Designer
- Drag-and-drop visual editor (CertificateDesigner.jsx)

### Digital Signatures
- DigitalSignatureManager across all role dashboards
- Signature embedding in Quotation PDF/Word

### Test Results Review
- Backend enriches test results with questions from original test for review

### Payment Reversal System (April 18, 2026) — NEW
- **Super Admin only** access (role check + specific email whitelist)
- **3-Step Formal Flow**: 
  1. Select payment → Preview impact (affected credit notes, journal entries, invoice status change)
  2. Enter mandatory reason (min 10 characters)
  3. Confirm & execute
- **Full reversal actions**: Payment status → "reversed", credit notes → "voided", journal entries → "voided", invoice status reverted
- **Comprehensive audit trail**: Logged to super_admin_audit_log, finance_audit_log, and audit_trail collections
- **Reversal History tab**: Shows all past reversals with date, company, amount, reason
- **Finance portal indicators**: REVERSED badge on payments, VOIDED badge on credit notes
- **Entity audit trail API**: `GET /api/superadmin/audit-trail/{entity_type}/{entity_id}`

### Bug Fixes (April 14, 2026)
- Fixed: Trainer checklist "No checklist items available" — state reset on navigation + stale closure prevention
- Fixed: Feedback submission 422 error — `FeedbackSubmit.responses` changed from `dict` to `Any`
- Fixed: Coordinator visibility of checklists — endpoints now query `vehicle_checklists` collection
- Fixed: `/vehicle-checklists/` endpoint now checks `vehicle_checklists` collection first

## P0 — In Progress / Pending
- System-wide digital signature audit & implementation (Invoices, Receipts, Payslips, Pay Advice, EA Forms, Claim Forms, Credit Notes)

## P1 — Upcoming
- Email integration (Resend) + WhatsApp link integration
- Trainer Contract Workflow

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
