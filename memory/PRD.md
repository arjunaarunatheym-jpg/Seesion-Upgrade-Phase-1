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

## Current Status (Feb 2026)

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
- ✅ Excel Feedback Export - Feb 5, 2026
  - Export button in Coordinator Analytics tab
  - Generates XLSX with 4 sheets: Session Info, Participants & Test Results, Feedback Responses, Summary
  - Includes pre/post test scores, feedback ratings, and averages

### In Progress
- None

### Upcoming (P1)
- Google Drive Feedback Integration (feedback URL per session, certificate release mechanism TBD)
- Remove picture upload from reporting (reduce storage)
- Custom Pre/Post Test Results format (blocked on user sample)

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
