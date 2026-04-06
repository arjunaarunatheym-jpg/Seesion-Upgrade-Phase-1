# MDDRC Training Management System - PRD

## Original Problem Statement
Comprehensive training management platform for Malaysian Defensive Driving and Riding Centre (MDDRC). Manages training sessions, participants, invoicing, HR/payroll, marketing, and compliance.

## Architecture
- **Frontend**: React + Shadcn/UI + Tailwind
- **Backend**: FastAPI (39 modular route files under /app/backend/routes/)
- **Database**: MongoDB
- **PDF**: Client-side html2pdf.js + Backend FPDF for quotation PDFs
- **DOCX**: html-docx-js-typescript for Word exports

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

## Completed This Session (2026-04-06)

### Vehicle Rental Pricing Bug Fix (P0) - DONE
**Problem**: When adding priced items (vehicle rental) to quotation, the PDF showed the training fee REDUCED by the vehicle amount instead of ADDING it on top.
- Example: Training RM 6,000 + Vehicles 5×RM 150 = RM 750 → System showed training as RM 5,250 and total RM 6,000 (wrong). Should show training RM 6,000 + vehicles RM 750 = total RM 6,750.

**Root causes fixed**:
1. **Backend create quotation** (`marketing.py` line ~707): `subtotal = group_price` didn't include addon items. Fixed to `subtotal = group_price + addon_total`.
2. **Backend PDF generation** (`marketing.py` line ~2615): Training row amount was `subtotal - priced_items` (subtracting). Fixed to use raw `group_price` or `rate_per_pax × participants` directly.
3. **Frontend PDF/DOCX generators** (`MarketingDashboard.jsx`): Same subtraction logic. Fixed to compute training fee from raw fields and add vehicle on top.

**Verified**: PDF now correctly shows:
- Bus Defensive Training: RM 6,000.00
- Training Vehicles (5 units): RM 750.00
- Subtotal: RM 6,750.00 ✓

## Prioritized Backlog
### P0
- Certificate auto-generation from PDF template (blocked on user's template upload)

### P1
- Email integration (Resend) — invoice/payment/cert notifications
- Trainer Contract Workflow (freelance staff)
- Post-Training Evaluation System (3/6 month feedback)

### P2
- SST Summary report, Client self-service portal

### Future
- Multi-tenancy, SaaS Monetization (Stripe), Native Mobile App (Capacitor)

## Key Technical Notes
- `description_items`: `{id, name, category, has_quantity, has_pricing, default_unit_price}`
- `selected_items` in quotations: `[{item_id, quantity, unit_price}]`
- Backend recalculates subtotal on create: `training_fee + sum(addon_items)`
- PDF generation uses raw pricing fields (`group_price`, `rate_per_pax × num_participants`) for the training row, never subtracts addons from subtotal
- `addon_line_items` on sessions: `[{description, quantity, unit_price, amount}]` — flows to invoice line_items
