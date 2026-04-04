# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC). Manages training sessions, participants, invoicing, HR/payroll, marketing, and compliance.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind
- **Backend**: FastAPI (39 modular route files under /app/backend/routes/)
- **Database**: MongoDB
- **PDF**: Client-side html2pdf.js (all window.open/print patterns replaced)
- **DOCX**: html-docx-js-typescript for Word exports

## What's Been Implemented
- Full backend modularization (server.py monolith -> 39 route files)
- Session management with start_date, end_date, cert_show_validity, cert_validity_months
- Invoice lifecycle with line_items auto-sync on override
- Marketing dashboard with 10s polling
- 2-decimal currency formatting (fmtRM)
- HR module, payroll, EA forms
- Profit & Loss / General Ledger reports
- Certificate management
- Data Management tab (SuperAdmin)
- Programme Certificate Title & Subtitle fields
- Public Certificate Verification page (/verify)
- Participant Photo Upload in Verification Dialog
- Trainer Dashboard UX Improvements (Today's Session, Participant Photos, Session Notes)
- Coordinator & Supervisor Dashboard creation/UX pass
- Receipt Number Fix (auto-generated RCP/YYYY/MM/0001)
- Balance Sheet UI in Finance Dashboard
- Journal Sync Engine Fix (deferred revenue, CEO/Auditor P&L alignment)
- Auto-posting for Petty Cash, Manual Income/Expenses
- 10-Role Audit Report & Finance Explainer PDFs

## Completed This Session (2026-04-04)
- **PDF Download Refactor (P0)**: Replaced ALL window.open/document.write/window.print patterns with html2pdf.js across:
  - FinanceDashboard.jsx (Receipt, Invoice, Credit Note, Payables Report)
  - PayablesTab.jsx (Payables print button)
  - ClaimFormPrint.jsx, IndemnityFormPrint.jsx, PayslipPrint.jsx, PayAdvicePrint.jsx, DocumentPreview.jsx (removed orphaned printWindow.close() references)
- **Digital Signature Manager (P0)**: Per-user signature upload/save feature added to ALL role dashboards:
  - Admin: Settings area
  - Marketing: My Payroll tab
  - Coordinator: My Payroll tab
  - Trainer: My Payroll tab
  - Supervisor: Dedicated Signature tab
  - SuperAdmin: Dedicated Signature tab
  - AssistantAdmin: My Earnings area
  - Finance: Settings area
- **User Model Updated**: Added `profile_photo` and `digital_signature` optional fields to Pydantic User model so they return correctly from `/api/auth/me`
- **Word DOCX Export**: Quotation DOCX download via `generateWord` in MarketingDashboard (uses html-docx-js-typescript)

## Prioritized Backlog
### P0
- Certificate auto-generation from PDF template (waiting for user's template upload)

### P1
- Email integration (Resend) — invoice issued, payment received, cert ready
- WhatsApp integration (cert ready, payment reminders)
- Trainer Contract Workflow (freelance staff)
- Post-Training Evaluation System (3/6 month feedback)

### P2
- Balance Sheet report and SST Summary report
- Client self-service portal

### Future
- Multi-tenancy architecture
- Supervisor Portal
- SaaS Monetization (Stripe)
- Native Mobile App (Capacitor)

## Key Technical Notes
- Session model: `cert_show_validity` (bool), `cert_validity_months` (int, default 24)
- Programme model: `certificate_title` (str), `certificate_subtitle` (str)
- IC formatting: `format_ic_number()` in certificate_verify.py
- Verify endpoints are PUBLIC (no auth required)
- printInvoice.js has auto-heal: if line_items don't match total_amount, recalculates before rendering
- Digital signature stored as base64 in users collection, returned via User model
- html2pdf.js for all PDF downloads; html-docx-js-typescript for DOCX
- downloadPdf() and downloadPdfLandscape() in utils/htmlToPdf.js
