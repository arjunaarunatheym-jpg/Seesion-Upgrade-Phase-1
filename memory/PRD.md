# MDDRC Training Management System — PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC). Features include session management, participant tracking, financial management (invoices, quotations, receipts), HR (payroll, payslips, claims), marketing (leads, quotations), certificate generation, and role-based dashboards.

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
- **Certificate Designer**: Visual drag-and-drop over PNG template (CertificateDesigner.jsx)

## What's Been Implemented

### Session Management
- Full CRUD for training sessions
- Participant assignment (bulk upload Excel + single add)
- Trainer assignment with chief/regular roles
- Coordinator and assistant coordinator assignment
- Session status management (active/draft/completed/archived)
- Protected field stripping on session updates (prevents accidental status changes)
- Coordinator query includes both active + draft sessions

### Participant Management (April 2026)
- **Admin SessionsTab**: Bulk Upload + Add Participant (single) buttons per session card
- **Coordinator Dashboard**: Bulk Participants + Add Participant buttons per session card
- **Coordinator "My Sessions"**: Sessions grouped by month/year with section headers

### Document Generation
- Quotation PDF/Word with digital signatures (marketer + approver)
- Invoice generation
- Receipt generation
- Credit note generation
- Payslip and Pay Advice printing
- Claim form printing
- Indemnity form printing

### Certificate Designer
- Drag-and-drop visual editor (CertificateDesigner.jsx)
- Backend generates PNG from uploaded .docx template
- Admin and Coordinator access via "Cert Generator" tab

### Digital Signatures
- DigitalSignatureManager across all role dashboards
- Signature embedding in Quotation PDF/Word (marketer + approver)
- User model supports profile_photo + digital_signature (base64)

### Financial Management
- Quotation pricing with add-on items (has_pricing, default_unit_price)
- Description items with unit pricing
- Costing management per session

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
- Delete CertificateAdjuster.jsx (dead code)
- Extract HTML generators from MarketingDashboard.jsx (~1700 lines) to utils
