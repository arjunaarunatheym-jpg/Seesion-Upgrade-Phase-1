# MDDRC Training Management System - PRD

## Original Problem Statement
Build a comprehensive training management platform for Malaysian Defensive Driving and Riding Centre Sdn Bhd (MDDRC). The system manages training sessions, participants, invoicing, and coordination across multiple user roles.

## User Personas
- **System Administrator**: Manages programs, users, companies, settings
- **Coordinator**: Manages training sessions, participants, attendance
- **Finance**: Handles invoicing, payments, P&L, payables
- **Marketing**: Manages clients, quotations, commissions
- **Trainer**: Conducts training, provides feedback
- **Participant**: Attends training, completes tests, feedback

## Core Features Implemented
1. **Authentication & Authorization** - JWT-based login with role-based access
2. **Training Session Management** - Create, schedule, manage training sessions
3. **Participant Management** - Registration, attendance tracking, certificates
4. **Invoice System** - Auto-generation, approval workflow, PDF generation
5. **Multi-Invoice per Session** - Link multiple invoices from different companies to a single session
6. **Finance Portal** - Full accounting, P&L ledger, payables, credit notes
7. **Quotation System** - Marketing quotations with admin approval workflow
8. **Indemnity Form** - Multi-step wizard with digital signature capture

## Tech Stack
- Frontend: React 18 + Tailwind CSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- PDF Generation: fpdf2
- Authentication: JWT + bcrypt
- Email: Resend API

## API Endpoints (Key)
- `/api/auth/login` - User authentication
- `/api/finance/invoices` - Invoice CRUD operations
- `/api/finance/session/{session_id}/additional-invoice` - Create linked invoices
- `/api/marketing/quotations/{id}/download-pdf` - PDF generation with rich text
- `/api/settings/indemnity-sections` - Admin-managed indemnity content
- `/api/settings/feedback-questions` - GET/POST feedback questions (Admin)
- `/api/sessions/{session_id}/export-template` - Download Excel template
- `/api/sessions/{session_id}/import-data` - Import Excel data
- `/api/marketing/leads` - Lead CRUD
- `/api/notifications/settings` - Email notification settings CRUD
- `/api/notifications/broadcast` - Send broadcast emails
- `/api/notifications/broadcast-history` - Broadcast history
- `/api/notifications/recipients` - Deduplicated staff recipients
- `/api/notifications/events` - Available notification events
- `/api/superadmin/dashboard` - Super Admin dashboard stats

## Current Status (Mar 2026)

### Recently Completed (Mar 16, 2026)
- ✅ **Calendar View for All Staff** — Calendar now shows ALL sessions to all staff roles (admin, coordinator, trainer, marketing, finance). No role-based filtering. Marketing and finance users can now access `/calendar`.
- ✅ **Marketing "My Sessions" Tab** — New tab in Marketing Portal showing sessions from the marketer's deals. Read-only view with current/past toggle, company names, programme, dates, venue, coordinators, trainers, and invoice status.
- ✅ **Smart Email Dispatcher** (P0) — Complete contextual email routing system with 14 event-specific notification functions
  - Core `send_smart_notification()` function with TO/CC/REPLY-TO support
  - 14 event-specific notification functions with hardcoded routing rules:
    - Quotation for Approval → TO: Admin | REPLY-TO: Marketer
    - Quotation Approved → TO: Marketer | CC: Admin
    - Quotation Rejected → TO: Marketer
    - Quotation Sent to Client → TO: Client | CC: Admin | REPLY-TO: Marketer
    - Quotation Accepted → TO: Admin | CC: Finance
    - Quotation Declined → TO: Admin
    - Discount Request → TO: Admin | REPLY-TO: Marketer
    - Invoice Issued → TO: Client contact | CC: Admin + Finance
    - Payment Received → TO: Admin + Finance
    - Session Completed → TO: Admin | CC: Coordinator + Trainers
    - New Lead → TO: Admin
    - Lead Stage Change → TO: Admin
    - Lead Won → TO: Admin | CC: Finance
    - Lead Lost → TO: Admin
  - All email triggers wired into marketing, finance, and session routes
  - Tested: 23/23 backend tests passed (iteration_19)

- ✅ **Email & Notifications System** — Full notification management
  - Notification Rules: 10 configurable events with per-event toggle, role/staff/custom email recipients
  - Broadcast/Greetings: Send emails to groups with attachment support
  - Broadcast History: View sent broadcasts with recipient counts
  - Resend integration (domain verification needed for external emails)

- ✅ **Auto-Lead for Returning Clients**
- ✅ **Revenue Recognition Fix** — Cash-basis (payment received)
- ✅ **Marketing Pipeline Month/Year Grouping**
- ✅ **Excel Import/Export Refinement** — 5-sheet template, raw marks, feedback
- ✅ **Coordinator Session Visibility Bug Fix**
- ✅ **Admin Session Mark Complete**
- ✅ **Invoice Revert Status**
- ✅ **Credit Notes Month/Year Grouping**
- ✅ **Certificate Template Designer**
- ✅ **Super Admin Portal**

### Upcoming (P1)
- Trainer Contract Workflow — Generate & email freelance contract for trainers
- `server.py` refactoring — Move remaining endpoints to modular route files
- SaaS Monetization — Stripe integration for tiered subscription plans
- Post-Training Evaluation System — Automated evaluation forms
- Automated Certificate Generation Workflow
- Native App Conversion — Capacitor with push notifications & camera
- Privacy Policy Page — `/privacy-policy`
- Collapsible UI tables (Payables, Users, Invoices)

### Backlog (P2)
- Journal entry "Unknown" descriptions fix
- PDF data integrity fixes (valid_until date, names)
- Payables Excel export verification
- Client Portal for customers
- Trainer Portal for trainers
- Enhanced Data Management tables with search/pagination
- WYSIWYG PDF Template Editor
- Collapsible table UI in Admin Dashboard (P3)

## Architecture
```
/app/
├── backend/
│   ├── routes/          # Modular API routes
│   │   ├── marketing.py        # Quotation + lead notifications wired
│   │   ├── finance_invoices.py # Invoice issued notification wired
│   │   ├── finance_payments.py # Payment received notification wired
│   │   ├── sessions_new.py     # Session completed notification wired
│   │   └── notifications.py    # Notification settings + broadcast
│   ├── utils/
│   │   └── email_notifications.py  # Smart email dispatcher (14 functions)
│   ├── models/          # Pydantic models
│   └── server.py        # Main FastAPI app
└── frontend/
    └── src/
        ├── components/  # UI components
        ├── pages/       # Dashboard pages
        └── utils/       # Print utilities
```

## Test Credentials
- Admin: arjuna@mddrc.com.my / Dana102229
- Coordinator: malek@mddrc.com.my / mddrc1
