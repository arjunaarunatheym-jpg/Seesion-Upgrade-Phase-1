# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC). Manages training sessions, participants, invoicing, HR/payroll, marketing, and compliance.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind
- **Backend**: FastAPI (39 modular route files under /app/backend/routes/)
- **Database**: MongoDB
- **PDF**: Client-side HTML-to-print (printInvoice.js)

## What's Been Implemented
- Full backend modularization (server.py monolith → 39 route files)
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
- Session creation endpoint restored in sessions_new.py

## Completed This Session (2026-04-02)
- **P0 FIX**: Invoice PDF line items mismatch — fixed override endpoint + printInvoice auto-heal
- **Certificate Title/Subtitle**: Added to Programme model and UI (create/edit forms)
- **Session Validity Settings**: cert_show_validity toggle + cert_validity_months dropdown on session create/edit
- **Public Verification Page**: /verify route with cert number search + IC number search
- **Backend verification route**: /api/verify/certificate/{num} and /api/verify/search-ic/{ic}
- **Session creation endpoint**: Restored POST /sessions in sessions_new.py (was orphaned in old sessions.py)
- **.gitignore fix**: Removed *.env blocking that prevented deployment

## Prioritized Backlog
### P0
- Certificate auto-generation from PDF template (waiting for user's template upload)
- QR code generation on certificates (ready to implement when template arrives)

### P1
- Email integration (invoice issued, payment received, cert ready)
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
- IC formatting: `format_ic_number()` in certificate_verify.py (861125385720 → 861125-38-5720)
- Verify endpoints are PUBLIC (no auth required)
- printInvoice.js has auto-heal: if line_items don't match total_amount, recalculates before rendering
