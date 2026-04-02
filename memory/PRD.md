# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC). Manages training sessions, participants, invoicing, HR/payroll, marketing, and compliance.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind
- **Backend**: FastAPI (38 modular route files under /app/backend/routes/)
- **Database**: MongoDB
- **PDF**: Client-side HTML-to-print (printInvoice.js)

## What's Been Implemented
- Full backend modularization (server.py monolith → 38 route files)
- Session management with start_date and end_date
- Invoice lifecycle (create, issue, void, backdate, override, edit-paid, delete)
- Marketing dashboard with 10s polling for quotation approvals
- 2-decimal currency formatting (fmtRM) across costing dashboards
- HR module, payroll, EA forms
- Profit & Loss / General Ledger reports
- Certificate management
- Data Management tab (SuperAdmin)
- Checklist templates (fixed 500 error)

## Completed This Session (2026-04-02)
- **P0 FIX**: Invoice PDF line items mismatch on override — Root cause: `override_invoice_validation` endpoint updated `total_amount` but not `subtotal`/`line_items`. Fixed by adding line_items recalculation to the override endpoint.
- **DB Repair**: Synced Sapura Offshore (INV/0002) and Sapura Drilling (INV/0003) invoices.
- **Belt-and-suspenders**: Frontend `InvoicesTab.jsx` now re-fetches invoice from API before printing PDF.
- **P1 Verified**: Session End Date already fully implemented (frontend + backend).

## Prioritized Backlog
### P0
- (none currently)

### P1
- Certificate auto-generation and Email notifications
- Trainer Contract Workflow (freelance staff)
- Post-Training Evaluation System (automated 3/6 month feedback)

### P2
- Balance Sheet report and SST Summary report

### Future
- Multi-tenancy architecture
- Supervisor Portal / Client Self-Service Portal
- SaaS Monetization (Stripe Integration)
- Native Mobile App conversion (Capacitor)
