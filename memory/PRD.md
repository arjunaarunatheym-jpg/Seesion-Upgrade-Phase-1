# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC). Manages training sessions, participants, invoicing, HR/payroll, marketing, and compliance.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind
- **Backend**: FastAPI (39 modular route files under /app/backend/routes/)
- **Database**: MongoDB
- **PDF**: Client-side html2pdf.js + Backend FPDF + LibreOffice headless (.docx→PDF)
- **DOCX**: html-docx-js-typescript for Word exports, python-docx for certificate template processing

## What's Been Implemented (Full List)
- Full backend modularization (server.py monolith -> 39 route files)
- Session management with start/end dates, cert validity
- Invoice lifecycle with line_items auto-sync on override
- Marketing dashboard with 10s polling
- 2-decimal currency formatting (fmtRM)
- HR module, payroll, EA forms
- P&L / General Ledger / Balance Sheet reports
- Certificate management + public verification
- Data Management tab (SuperAdmin)
- Trainer/Coordinator/Supervisor Dashboards
- Journal Sync Engine + Auto-posting
- PDF Download Refactor (all window.print → html2pdf.js)
- Digital Signature Manager (all 8 role dashboards)
- Vehicle Rental / Add-on Item Pricing in Quotations
- **Certificate Auto-generation Engine** (2026-04-06)
- **Certificate Adjuster Tool** (2026-04-06)

## Completed This Session (2026-04-06)

### Certificate Auto-generation Engine (P0) - DONE
- User uploads custom `.docx` certificate template with `{{PLACEHOLDER}}` markers
- System replaces 11 placeholders (name, IC, company, title, dates, venue, cert number, etc.)
- Intelligent font size auto-fitting: configurable per-field font size, max lines, auto-shrink toggle
- LibreOffice headless converts .docx → PDF, trims to single page
- Certificate number format: `MDDRC/COA/YYYY/MM/XXXXX`
- Eligibility checks: attendance, post-test, feedback (with force override)
- Bulk generation for all eligible participants in a session

### Certificate Adjuster Tool (P0) - DONE
- Live preview panel for Admin & Coordinator dashboards
- Per-field controls: font size slider, max lines slider, auto-fit toggle
- Global controls: top margin %, paragraph spacing %
- Session & participant selection with live certificate preview
- Save settings as defaults for future certificates
- Generate single or bulk certificates with one click
- Force override for eligibility-bypass generation

### Key Endpoints Added
- `GET /api/certificates/font-settings` - Load saved font settings
- `PUT /api/certificates/font-settings` - Save font settings
- `POST /api/certificates/preview-pdf/{session_id}/{participant_id}` - Generate PNG preview
- `POST /api/certificates/generate-pdf/{session_id}/{participant_id}` - Generate real cert PDF
- `POST /api/certificates/generate-bulk-pdf/{session_id}` - Bulk generate for session

## Prioritized Backlog
### P1
- Email integration (Resend) — invoice/payment/cert notifications
- WhatsApp link integration — document sharing
- Trainer Contract Workflow — freelance staff contracts

### P2
- Post-Training Evaluation System (automated 3/6 month feedback)
- Multi-tenancy architecture & SaaS Monetization (Stripe)

### P3
- Supervisor Portal / Client Self-Service Portal
- Native Mobile App conversion (Capacitor)

## Refactoring Notes
- `MarketingDashboard.jsx` (~1700 lines) — extract HTML generators to `/utils`
- Certificate PDF cleanup: old test certs generated during development should be purged
