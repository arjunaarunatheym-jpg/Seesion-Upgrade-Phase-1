# 🔧 STAGED REFACTORING PLAN - BACKEND & FRONTEND

## 📊 CURRENT STATE SUMMARY

### Backend: `server.py` (17,072 lines)
| Section | Lines | Endpoints | Description |
|---------|-------|-----------|-------------|
| Security Config | 1-200 | 0 | Middleware, rate limiting |
| Models | 306-1293 | 0 | Pydantic models |
| Helper Functions | 1294-1453 | 0 | Utilities |
| Auth Routes | 1461-1664 | 6 | Login, register, password |
| Companies & Programs | 1665-1862 | 8 | Basic CRUD |
| Users | 1863-2059 | 7 | User management |
| Sessions | 2060-3462 | 25 | Core session logic |
| Tests | 3583-4678 | 11 | Assessment system |
| Super Admin | 4423-4634 | 5 | Quick testing panel |
| Checklists | 4698-4825, 6790-6922 | 15 | Vehicle checklists |
| Attendance | 4881-5077 | 4 | Clock in/out |
| Training Reports | 5078-6591 | 12 | AI reports, DOCX |
| Trainer Checklist | 6592-6789 | 2 | Trainer features |
| Feedback | 6924-7226 | 12 | Course feedback |
| Certificates | 7227-7877 | 10 | Cert generation |
| Settings | 7252-7332 | 4 | App settings |
| Supervisor | 8170-8212 | 2 | Supervisor endpoints |
| Finance | 8213-15059 | 95 | Invoices, P&L, etc. |
| Petty Cash | 15060-15373 | 10 | Cash management |
| Security Admin | 15374-15450 | 4 | IP blocking |
| Marketing | 15451-16942 | 26 | Quotations, clients |

### Frontend: Large Components
| File | Lines | Priority |
|------|-------|----------|
| AdminDashboard.jsx | 5,688 | 🔴 Critical |
| FinanceDashboard.jsx | 4,419 | 🔴 Critical |
| CoordinatorDashboard.jsx | 3,034 | 🟠 High |
| DataManagement.jsx | 2,020 | 🟠 High |
| HRModule.jsx | 1,578 | 🟡 Medium |
| ProfitLossLedger.jsx | 1,486 | 🟡 Medium |
| ParticipantDashboard.jsx | 1,534 | 🟡 Medium |
| MarketingDashboard.jsx | 1,230 | 🟡 Medium |
| SuperAdminPanel.jsx | 1,217 | 🟡 Medium |
| TrainerDashboard.jsx | 1,176 | 🟢 Lower |

---

## 🎯 BACKEND REFACTORING STAGES

### STAGE 1: Foundation & Simple Routes (Low Risk)
**Goal**: Set up structure, extract simplest routes first

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Settings | 4 | 80 | 🟢 Very Low |
| Programs | 4 | 50 | 🟢 Very Low |
| Companies | 4 | 60 | 🟢 Very Low |
| **Total** | **12** | **~190** | |

#### Checklist - Stage 1:
- [ ] Create `/app/backend/routes/` structure (if not exists)
- [ ] Create `routes/settings.py` with exact same endpoints
- [ ] Create `routes/programs.py` with exact same endpoints  
- [ ] Create `routes/companies.py` with exact same endpoints
- [ ] Register routers in server.py
- [ ] Run API contract test - all must pass
- [ ] Test via curl: GET /api/settings, GET /api/programs, GET /api/companies
- [ ] Comment out old code in server.py
- [ ] Run API contract test again
- [ ] Delete commented code
- [ ] Git commit: "Stage 1: Settings, Programs, Companies extracted"

---

### STAGE 2: User Management & Auth (Low Risk)
**Goal**: Extract user-related functionality

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Auth | 6 | 200 | 🟢 Low |
| Users | 7 | 150 | 🟢 Low |
| **Total** | **13** | **~350** | |

#### Checklist - Stage 2:
- [ ] Create `routes/auth.py` - login, register, password reset
- [ ] Create `routes/users.py` - CRUD, profile, export
- [ ] Move `get_current_user` dependency to `services/auth_service.py`
- [ ] Register routers
- [ ] Run API contract test
- [ ] Test: POST /api/auth/login, GET /api/users
- [ ] Comment out old code
- [ ] Verify login still works in browser
- [ ] Delete old code
- [ ] Git commit: "Stage 2: Auth, Users extracted"

---

### STAGE 3: Attendance & Participant Access (Low Risk)
**Goal**: Extract simple session-related features

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Attendance | 4 | 200 | 🟢 Low |
| Participant Access | 4 | 100 | 🟢 Low |
| **Total** | **8** | **~300** | |

#### Checklist - Stage 3:
- [ ] Create `routes/attendance.py`
- [ ] Create `routes/participant_access.py`
- [ ] Register routers
- [ ] Run API contract test
- [ ] Test: POST /api/attendance/clock-in, GET /api/participant-access/session/{id}
- [ ] Comment out old code
- [ ] Test attendance in SuperAdmin panel
- [ ] Delete old code
- [ ] Git commit: "Stage 3: Attendance, Participant Access extracted"

---

### STAGE 4: Tests & Feedback (Medium Risk)
**Goal**: Extract assessment-related features

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Tests | 11 | 400 | 🟡 Medium |
| Feedback | 12 | 300 | 🟡 Medium |
| **Total** | **23** | **~700** | |

#### Checklist - Stage 4:
- [ ] Create `routes/tests.py` - test CRUD, submit, results
- [ ] Create `routes/feedback.py` - feedback templates, submit
- [ ] Register routers
- [ ] Run API contract test
- [ ] Test: Submit a test, submit feedback
- [ ] Comment out old code
- [ ] Full test: Complete a test flow in participant dashboard
- [ ] Delete old code
- [ ] Git commit: "Stage 4: Tests, Feedback extracted"

---

### STAGE 5: Checklists & Certificates (Medium Risk)
**Goal**: Extract document-related features

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Checklists | 15 | 400 | 🟡 Medium |
| Certificates | 10 | 650 | 🟡 Medium |
| **Total** | **25** | **~1050** | |

#### Checklist - Stage 5:
- [ ] Create `routes/checklists.py` - templates, submit, verify
- [ ] Create `routes/certificates.py` - generate, download, preview
- [ ] Handle static file serving for certificates
- [ ] Register routers
- [ ] Run API contract test
- [ ] Test: Download a certificate, submit checklist
- [ ] Comment out old code
- [ ] Full test: Generate certificate in admin panel
- [ ] Delete old code
- [ ] Git commit: "Stage 5: Checklists, Certificates extracted"

---

### STAGE 6: Sessions & Reports (Medium-High Risk)
**Goal**: Extract core session management

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Sessions | 25 | 1400 | 🟠 Higher |
| Training Reports | 12 | 1500 | 🟠 Higher |
| **Total** | **37** | **~2900** | |

#### Checklist - Stage 6:
- [ ] Create `routes/sessions.py` - CRUD, participants, status
- [ ] Create `routes/training_reports.py` - AI report, DOCX generation
- [ ] Move report generation helpers to `services/report_service.py`
- [ ] Register routers
- [ ] Run API contract test
- [ ] Test: Create session, add participant, generate report
- [ ] Comment out old code
- [ ] Full test: Complete session workflow
- [ ] Delete old code
- [ ] Git commit: "Stage 6: Sessions, Training Reports extracted"

---

### STAGE 7: HR Module (Medium Risk)
**Goal**: Extract HR/Payroll functionality

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| HR | 27 | 800 | 🟡 Medium |

#### Checklist - Stage 7:
- [ ] Create `routes/hr.py` - staff, payslips, pay advice, EA forms
- [ ] Register router
- [ ] Run API contract test
- [ ] Test: Generate payslip, view pay advice
- [ ] Comment out old code
- [ ] Full test: HR workflow in finance dashboard
- [ ] Delete old code
- [ ] Git commit: "Stage 7: HR Module extracted"

---

### STAGE 8: Marketing Module (Medium Risk)
**Goal**: Extract marketing/quotation functionality

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Marketing | 26 | 1500 | 🟡 Medium |

#### Checklist - Stage 8:
- [ ] Create `routes/marketing.py` - clients, quotations, PDF generation
- [ ] Move PDF generation to `services/pdf_service.py`
- [ ] Register router
- [ ] Run API contract test
- [ ] Test: Create quotation, download PDF
- [ ] Comment out old code
- [ ] Full test: Complete quotation workflow
- [ ] Delete old code
- [ ] Git commit: "Stage 8: Marketing Module extracted"

---

### STAGE 9: Finance Module - Part 1 (High Risk)
**Goal**: Extract core finance features

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Finance Core | 40 | 2000 | 🔴 High |
| (Invoices, Payments, Credit Notes) | | | |

#### Checklist - Stage 9:
- [ ] Create `routes/finance/invoices.py`
- [ ] Create `routes/finance/payments.py`
- [ ] Create `routes/finance/credit_notes.py`
- [ ] Create `routes/finance/__init__.py` to combine
- [ ] Register router
- [ ] Run API contract test
- [ ] Test: Create invoice, record payment
- [ ] Comment out old code
- [ ] Full test: Invoice workflow
- [ ] Delete old code
- [ ] Git commit: "Stage 9: Finance Core extracted"

---

### STAGE 10: Finance Module - Part 2 (High Risk)
**Goal**: Extract remaining finance features

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Finance Advanced | 55 | 3500 | 🔴 High |
| (P&L, Payables, Costing, Petty Cash) | | | |

#### Checklist - Stage 10:
- [ ] Create `routes/finance/profit_loss.py`
- [ ] Create `routes/finance/payables.py`
- [ ] Create `routes/finance/session_costing.py`
- [ ] Create `routes/finance/petty_cash.py`
- [ ] Register all finance routers
- [ ] Run API contract test
- [ ] Test: View P&L, session costing
- [ ] Comment out old code
- [ ] Full test: Complete finance workflows
- [ ] Delete old code
- [ ] Git commit: "Stage 10: Finance Advanced extracted"

---

### STAGE 11: Cleanup & Utilities (Low Risk)
**Goal**: Extract remaining items, clean up server.py

| Module | Endpoints | Lines ~| Risk |
|--------|-----------|--------|------|
| Supervisor | 2 | 50 | 🟢 Low |
| Super Admin | 5 | 200 | 🟢 Low |
| Security Admin | 4 | 80 | 🟢 Low |
| Templates | 6 | 100 | 🟢 Low |
| Static Files | 7 | 50 | 🟢 Low |
| **Total** | **24** | **~480** | |

#### Checklist - Stage 11:
- [ ] Create `routes/supervisor.py`
- [ ] Create `routes/super_admin.py`
- [ ] Create `routes/security.py`
- [ ] Create `routes/templates.py`
- [ ] Create `routes/static_files.py`
- [ ] Register all routers
- [ ] Run API contract test
- [ ] Comment out old code
- [ ] Final cleanup of server.py
- [ ] Delete all old route code
- [ ] Git commit: "Stage 11: Backend refactoring complete"

---

### STAGE 12: Final Backend Cleanup
**Goal**: server.py should only have ~300 lines

#### Final server.py Structure:
```python
# server.py (~300 lines)
from fastapi import FastAPI
from routes import (
    auth, users, companies, programs, sessions,
    tests, feedback, checklists, certificates,
    attendance, participant_access, training_reports,
    hr, marketing, finance, supervisor, super_admin,
    security, templates, static_files, settings
)

app = FastAPI()

# Middleware
# CORS
# Database connection
# Router registration
# Startup/shutdown events
```

#### Checklist - Stage 12:
- [ ] Move models to `/app/backend/models/`
- [ ] Move security config to `/app/backend/core/security.py`
- [ ] Move helper functions to `/app/backend/utils/`
- [ ] server.py is now ~300 lines
- [ ] Full regression test
- [ ] Git commit: "Backend refactoring 100% complete"

---

## 🎯 FRONTEND REFACTORING STAGES

### STAGE F1: AdminDashboard.jsx Decomposition
**Current**: 5,688 lines → **Target**: <500 lines main + sub-components

#### Sub-components to extract:
| Component | Description | Lines ~|
|-----------|-------------|--------|
| CompanyManagement.jsx | Company CRUD | 400 |
| ProgramManagement.jsx | Program CRUD | 300 |
| SessionManagement.jsx | Session CRUD | 600 |
| UserManagement.jsx | User CRUD | 500 |
| StaffManagement.jsx | Staff roles | 400 |
| ChecklistTemplates.jsx | Checklist config | 300 |
| FeedbackTemplates.jsx | Feedback config | 300 |
| TestTemplates.jsx | Test config | 300 |
| CertificateRepository.jsx | Cert management | 400 |
| FinanceSummary.jsx | Finance overview | 300 |
| MarketingQuotations.jsx | Quotation UI | 500 |
| MarketingClients.jsx | Client management | 400 |

#### Checklist - Stage F1:
- [ ] Create `/app/frontend/src/components/admin/` folder
- [ ] Extract CompanyManagement.jsx
- [ ] Extract ProgramManagement.jsx
- [ ] Extract SessionManagement.jsx
- [ ] Test: Admin dashboard still loads
- [ ] Extract UserManagement.jsx
- [ ] Extract StaffManagement.jsx
- [ ] Test: User management still works
- [ ] Extract remaining components
- [ ] Final test: All tabs work
- [ ] Git commit: "Stage F1: AdminDashboard decomposed"

---

### STAGE F2: FinanceDashboard.jsx Decomposition
**Current**: 4,419 lines → **Target**: <400 lines main + sub-components

#### Sub-components to extract:
| Component | Description | Lines ~|
|-----------|-------------|--------|
| InvoiceList.jsx | Invoice table | 400 |
| InvoiceForm.jsx | Create/edit invoice | 300 |
| PaymentList.jsx | Payment records | 300 |
| CreditNoteList.jsx | Credit notes | 300 |
| FinanceReports.jsx | P&L, ledger | 400 |
| PayablesList.jsx | Trainer/coord fees | 400 |
| SessionCostingPanel.jsx | Costing UI | 300 |
| BillingParties.jsx | Vendor management | 200 |

#### Checklist - Stage F2:
- [ ] Create `/app/frontend/src/components/finance/` folder
- [ ] Extract InvoiceList.jsx
- [ ] Extract InvoiceForm.jsx
- [ ] Test: Invoice tab works
- [ ] Extract remaining components
- [ ] Final test: All finance features work
- [ ] Git commit: "Stage F2: FinanceDashboard decomposed"

---

### STAGE F3: CoordinatorDashboard.jsx Decomposition
**Current**: 3,034 lines → **Target**: <400 lines main + sub-components

#### Checklist - Stage F3:
- [ ] Analyze component structure
- [ ] Extract session management pieces
- [ ] Extract participant management pieces
- [ ] Test: Coordinator features work
- [ ] Git commit: "Stage F3: CoordinatorDashboard decomposed"

---

### STAGE F4: Remaining Large Components
**Target**: All components under 800 lines

#### Components to decompose:
- DataManagement.jsx (2,020 lines)
- HRModule.jsx (1,578 lines)
- ProfitLossLedger.jsx (1,486 lines)
- ParticipantDashboard.jsx (1,534 lines)

#### Checklist - Stage F4:
- [ ] Extract DataManagement sub-components
- [ ] Extract HRModule sub-components
- [ ] Extract ProfitLossLedger sub-components
- [ ] Extract ParticipantDashboard sub-components
- [ ] Final test: All dashboards work
- [ ] Git commit: "Stage F4: Frontend refactoring complete"

---

## 📈 PROGRESS TRACKER

### Backend Progress
| Stage | Status | Endpoints | Verified |
|-------|--------|-----------|----------|
| Stage 1 | ⬜ Pending | 12 | ⬜ |
| Stage 2 | ⬜ Pending | 13 | ⬜ |
| Stage 3 | ⬜ Pending | 8 | ⬜ |
| Stage 4 | ⬜ Pending | 23 | ⬜ |
| Stage 5 | ⬜ Pending | 25 | ⬜ |
| Stage 6 | ⬜ Pending | 37 | ⬜ |
| Stage 7 | ⬜ Pending | 27 | ⬜ |
| Stage 8 | ⬜ Pending | 26 | ⬜ |
| Stage 9 | ⬜ Pending | 40 | ⬜ |
| Stage 10 | ⬜ Pending | 55 | ⬜ |
| Stage 11 | ⬜ Pending | 24 | ⬜ |
| Stage 12 | ⬜ Pending | 0 | ⬜ |

### Frontend Progress
| Stage | Status | Component | Verified |
|-------|--------|-----------|----------|
| Stage F1 | ⬜ Pending | AdminDashboard | ⬜ |
| Stage F2 | ⬜ Pending | FinanceDashboard | ⬜ |
| Stage F3 | ⬜ Pending | CoordinatorDashboard | ⬜ |
| Stage F4 | ⬜ Pending | Remaining | ⬜ |

---

## 🛡️ GOLDEN RULES

1. **NEVER change endpoint URLs** - `/api/sessions` stays `/api/sessions`
2. **NEVER change request/response format** - Same JSON in, same JSON out
3. **NEVER change database operations** - Same queries, same collections
4. **Test BEFORE and AFTER each stage** - Use API contract test
5. **Commit after EACH stage** - Easy rollback if needed
6. **One stage at a time** - Don't batch stages together
