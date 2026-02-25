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

## API Endpoints (Key)
- `/api/auth/login` - User authentication
- `/api/finance/invoices` - Invoice CRUD operations
- `/api/finance/session/{session_id}/additional-invoice` - Create linked invoices
- `/api/marketing/quotations/{id}/download-pdf` - PDF generation with rich text
- `/api/settings/indemnity-sections` - Admin-managed indemnity content
- `/api/settings/feedback-questions` - GET/POST feedback questions (Admin)
- `/api/sessions/{session_id}/export-feedback-excel` - Export feedback as Excel
- `/api/marketing/leads` - Lead CRUD (Marketing sees own, Admin sees all)
- `/api/marketing/leads/{id}/stage` - Quick stage update
- `/api/marketing/leads/{id}/convert-to-client` - Convert lead to client
- `/api/marketing/leads/reminders/pending` - Get overdue and upcoming follow-ups
- `/api/marketing/stats/pipeline` - Pipeline statistics
- `/api/marketing/stats/by-source` - Stats grouped by lead source
- `/api/marketing/stats/by-user` - Stats by marketing user (Admin only)
- `/api/superadmin/dashboard` - Super Admin dashboard stats
- `/api/superadmin/users` - User management (list, update, role change)
- `/api/superadmin/sessions` - Session management with status fixes
- `/api/superadmin/invoices` - Invoice management with void capability
- `/api/superadmin/audit-log` - View all super admin actions
- `/api/superadmin/export/{collection}` - CSV export for any collection

## Current Status (Feb 2026)

### Recently Completed (Feb 22, 2026)
- ✅ **Super Admin Portal** - Comprehensive system administration dashboard
  - Access: `/superadmin` route for arjuna@mddrc.com.my or super_admin role users
  - Dashboard tab: System statistics (users, sessions, invoices, quotations counts)
  - Users tab: Full CRUD - list, search, change roles, toggle active, reset passwords
  - Sessions tab: List all sessions with status filter, fix completion status
  - Invoices tab: List all invoices with status filter, void functionality
  - Quotations tab: List all quotations
  - Audit Log tab: View all super admin actions with timestamps, performers, reasons
  - Settings tab: View company and accounting settings
  - Export tab: CSV export for 8 collections (users, sessions, invoices, payments, quotations, companies, programs, journal_entries)
  - Access control: Backend 403 for unauthorized users, frontend route guard redirects
  - Audit logging: All modifications logged with reason, before/after values

### Recently Fixed (Feb 19, 2026)
- ✅ **Edit Session Dialog - Trainer Assignments**: Added missing trainer assignment UI to Edit Session dialog for draft sessions
- ✅ **Payables Excel Export**: Fixed download not triggering - file now downloads correctly as `payables_YYYY_MM.xlsx`

### Completed
- ✅ Full frontend refactoring (all dashboard components modularized)
- ✅ Multi-invoice per session feature
- ✅ Additional invoice PDF with venue/session details (VERIFIED)
- ✅ Enhanced participant profile verification (mandatory email/phone)
- ✅ Indemnity form wizard implementation
- ✅ API rate limiting increased (500 req/min)
- ✅ Rich-text quotation PDF templates (bold, italic, highlight, colors)
- ✅ Admin UI for Indemnity Form sections management
- ✅ Rich-text formatting toolbar for PDF templates editor
- ✅ Trainer session filtering (current/future vs past training)
- ✅ Session creation without participants (optional)
- ✅ Invoice number reuse for deleted auto-draft invoices
- ✅ Coordinator Dashboard reporting workflow consolidation (Jan 30, 2026)
  - Reports tab shows pending and submitted reports
  - Clicking pending report navigates to Analytics tab with session loaded
- ✅ Participant Feedback System (Soalan Maklum Balas) - Feb 5, 2026
  - Admin UI in Settings to add/edit/delete/reorder feedback questions
  - Questions organized by category: A. KUALITI KURSUS, B. PENYEDIA LATIHAN, C. TRAINER, D. UMUM
  - Rating (1-5) and Text question types
  - Default 19 questions in Bahasa Malaysia
  - Participant feedback form with 1-5 number buttons (not stars)
  - Form organized by category with Bahasa Malaysia instructions
  - Feedback mandatory before certificate download
- ✅ Excel Feedback Export - Feb 5, 2026
- ✅ Marketing Portal Phase 2 - Lead Pipeline (Feb 5, 2026)
  - Lead Pipeline with 6 stages: Inquiry → Contacted → Quotation Sent → Negotiating → Won → Lost
  - Pipeline (Kanban) and List views
  - Lead card with company, contact, expected value, follow-up date
  - Quick stage change via dropdown
  - Convert Lead to Client action
  - Data isolation: Marketing sees own leads, Admin sees all
  - Quick Stats Dashboard: Total leads, active, conversion rate, avg deal size, avg days to close, won value
  - Follow-up Reminders: Overdue alert and upcoming this week
  - Pipeline Breakdown badges by stage
  - **Lead → Quotation Flow:** "Quote" button auto-creates client from lead data
  - Quotation form pre-fills with client, links quotation to lead
  - Stage auto-syncs when quotation status changes (sent → quotation_sent, accepted → won, declined → lost)
  - **Admin Marketing Leads Overview:** New tab showing all marketing staff performance
  - Expandable staff rows to view their leads
  - Compare active, won, lost, conversion rate, won value by staff

### In Progress
- None

### Recently Completed (Feb 25, 2026)
- ✅ **Certificate Template Designer** (P1) — Fully functional
  - Pre-built Templates tab: Classic Gold, Modern Minimal, Corporate Blue
  - Custom Designer with drag-and-drop positioning
  - Elements: Logo, Text, Signature, Line with full property editing
  - Background color and border style customization
  - Live preview with placeholder substitution
  - Save/Load/Delete templates via API
  - Image upload for logos and signatures
  - Available placeholders: {Participant Name}, {Program Name}, {Date}, {Certificate Number}, {Company Name}
  - Backend: CRUD endpoints in routes/settings.py, asset upload endpoint
  - Testing: 9/9 backend, all UI tests passed

### Recently Fixed (Feb 25, 2026)
- ✅ **Session-to-Invoice Full Cascade Update** (P0)
  - Fixed: Editing session dates now cascades to ALL related invoices (training_dates field)
  - Fixed: Editing session venue/location now cascades to ALL related invoices
  - Fixed: Editing session programme now cascades to ALL related invoices
  - Fixed: Company name cascade still works for invoices, quotations, leads
  - Fixed in `routes/sessions_new.py` (the active PUT handler) and `server.py` backup
  - Covers multi-invoice sessions (additional invoices under same session_id)
- ✅ **nginx-app-proxy stability** - Recreated missing config file

### Recently Fixed (Feb 23, 2026)
- ✅ **Session Company Name Cascade Update** (P0)
  - Fixed: Editing company_name in Super Admin Portal now cascades to related records
  - Changes propagate to: invoices (company_name, bill_to_name), leads (company_name), quotations (client_name)
  - GET /superadmin/sessions now enriches company_name from company_id if not stored on session
  - PUT /superadmin/sessions now returns `cascaded_to` array showing which related records were updated

### Recently Fixed (Feb 2026)
- ✅ Admin Quotations Tab UI Improvements (Feb 19, 2026)
  - Quotations: Filter by Year + Month dropdowns (default: current year)
  - Clients: Alphabetical grouping (A-D, E-H, I-L, M-P, Q-T, U-Z)
  - Shows count of filtered results

- ✅ Won Quotation → Draft Session (Feb 19, 2026)
  - Auto-creates draft session when quotation is marked "Accepted"
  - Session appears in Admin Sessions tab with status "draft"
  - Fixed 3 existing won leads that were missing sessions

- ✅ Inclusions & Exclusions System (Feb 19, 2026)
  - Admin can create/manage "Inclusion" and "Exclusion" items via Quotations tab
  - Items have: name, category (inclusion/exclusion), has_quantity flag
  - Marketing users can select items with optional quantities when creating quotations
  - Two-column UI: Green (Inclusions) and Red (Exclusions) in Admin
  - Checkbox selection with quantity input in Marketing quotation form
  - PDF generation updated to show Inclusions and Exclusions sections

- ✅ PDF Logo Positioning Fix (Feb 19, 2026)
  - Fixed logo alignment in quotation PDF header
  - Logo now aligns with company name text (raised by 2mm)

- ✅ Marketing Commission Calculation Bug Fix (Feb 16, 2026)
  - Fixed: Historical commission amounts were incorrect (e.g., RM 69 instead of RM 1,149)
  - Root cause: Code used `find_one` for invoices, only considering first invoice per session
  - Fix: Changed to `find()` to sum ALL invoices for each session
  - Added `/api/finance/recalculate-commissions` admin endpoint for historical data correction
  - Recalculated Vighnesh's January 2026 commission: RM 69 → RM 1,149

### Recently Fixed (Dec 2025)
- ✅ Quotation Amount Bug Fix (Dec 16, 2025)
  - Fixed: Quotations were saving with RM 0.00 regardless of entered amount
  - Root cause: Frontend was not calculating/sending subtotal, sst_amount, total_amount to backend
  - Fix: Added calculation logic in handleSaveQuotation before API call
- ✅ Quotation Delete Endpoint (Dec 16, 2025)
  - Added DELETE /api/marketing/quotations/{id} endpoint
  - Only draft quotations can be deleted
- ✅ Data Cleanup (Dec 16, 2025)
  - Removed all duplicate/broken draft quotations (Vinda Malaysia, Taj Curry House, etc.)

### Upcoming (P1)
- "Won Lead → Draft Session" UI dialog completion
- Collapsible UI tables (Payables, Users, Invoices)
- Payables Excel export verification
- PDF bugs: `valid_until` date, "System Administrator" name (investigate stale data)
- Google Drive Feedback Integration
- WYSIWYG PDF Template Editor

### Backlog (P2)
- Backend cleanup (remove redundant server.py code)
- Billing party deletion fix
- Dummy participant re-add fix
- Invoice undo/replace buttons fix
- Period exists error fix
- Invoice CSV export sorting
- Post-Training Evaluation System
- Marketing Portal Phase 2
- Accountant P&L view with YoY analysis

## Architecture
```
/app/
├── backend/
│   ├── routes/          # Modular API routes
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
