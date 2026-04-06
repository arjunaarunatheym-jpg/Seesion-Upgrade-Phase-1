# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC). Manages training sessions, participants, invoicing, HR/payroll, marketing, and compliance.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind
- **Backend**: FastAPI (39 modular route files under /app/backend/routes/)
- **Database**: MongoDB
- **PDF**: Client-side html2pdf.js + Backend FPDF for quotation PDFs
- **DOCX**: html-docx-js-typescript for Word exports

## What's Been Implemented
- Full backend modularization (server.py monolith -> 39 route files)
- Session management with start_date, end_date, cert_show_validity, cert_validity_months
- Invoice lifecycle with line_items auto-sync on override
- Marketing dashboard with 10s polling
- 2-decimal currency formatting (fmtRM)
- HR module, payroll, EA forms
- Profit & Loss / General Ledger / Balance Sheet reports
- Certificate management + public verification page
- Data Management tab (SuperAdmin)
- Programme Certificate Title & Subtitle fields
- Participant Photo Upload in Verification Dialog
- Trainer/Coordinator/Supervisor Dashboard UX
- Receipt Number Fix (auto-generated RCP/YYYY/MM/0001)
- Journal Sync Engine Fix (deferred revenue, CEO/Auditor P&L alignment)
- Auto-posting for Petty Cash, Manual Income/Expenses
- 10-Role Audit Report & Finance Explainer PDFs

## Completed This Session (2026-04-06)

### 1. PDF Download Refactor (P0) - DONE
Replaced ALL `window.open/document.write/window.print` patterns with `html2pdf.js` across:
- FinanceDashboard.jsx (Receipt, Invoice, Credit Note, Payables Report)
- PayablesTab.jsx (Payables print button)
- ClaimFormPrint.jsx, IndemnityFormPrint.jsx, PayslipPrint.jsx, PayAdvicePrint.jsx, DocumentPreview.jsx

### 2. Digital Signature Manager (P0) - DONE
Per-user signature upload/save deployed to ALL 8 role dashboards:
- Admin (Settings), Marketing (My Payroll), Coordinator (My Payroll), Trainer (My Payroll)
- Supervisor (Signature tab), SuperAdmin (Signature tab), AssistantAdmin (My Earnings), Finance (Settings)
- User model updated with `profile_photo` and `digital_signature` fields

### 3. Vehicle Rental / Add-on Item Pricing (P0) - DONE
Added unit pricing support for quotation description items:
- **Backend**: `description_items` now support `has_pricing` (bool) + `default_unit_price` (float)
- **Admin UI**: QuotationsTab dialog has "Has unit pricing" checkbox + default price input
- **Quotation Form**: Priced items show Qty + RM/unit inputs with live inline total calculation
- **Subtotal**: Training Fee + Add-on Items total + SST = Grand Total
- **PDF**: Priced items render as separate table rows in FPDF quotation PDF
- **Word DOCX**: Priced items included as separate rows in Word export
- **Frontend PDF**: generatePDF includes priced items as separate rows
- **Session**: On quotation acceptance, `addon_line_items` stored on session
- **Invoice**: SessionCosting includes addon_line_items as separate invoice line_items

## Prioritized Backlog
### P0
- Certificate auto-generation from PDF template (blocked on user's template upload)

### P1
- Email integration (Resend) — invoice issued, payment received, cert ready
- WhatsApp integration
- Trainer Contract Workflow (freelance staff)
- Post-Training Evaluation System (3/6 month feedback)

### P2
- SST Summary report
- Client self-service portal

### Future
- Multi-tenancy architecture
- SaaS Monetization (Stripe)
- Native Mobile App (Capacitor)

## Key Technical Notes
- `description_items` collection: `{id, name, category, has_quantity, has_pricing, default_unit_price}`
- `selected_items` in quotations: `[{item_id, quantity, unit_price}]`
- `addon_line_items` on sessions: `[{description, quantity, unit_price, amount}]`
- Invoice line_items include both training fee and addon items
- Digital signature stored as base64 in users collection
- html2pdf.js for all PDF downloads; html-docx-js-typescript for DOCX
- downloadPdf() and downloadPdfLandscape() in utils/htmlToPdf.js
- printInvoice.js has auto-heal: if line_items don't match total_amount, recalculates before rendering
