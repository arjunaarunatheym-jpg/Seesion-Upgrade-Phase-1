# MDDRC Training Management Platform — PRD

## Original Problem Statement
Comprehensive training management platform for MDDRC. Phase 3A locks the
financial write lifecycle for normal users, preserving a **canonical,
audited SuperAdmin God Mode** for exceptional corrections. NEVER deploy
mid-phase. Phase 3B (Dynamic Funding Source) MUST NOT start until user
explicitly approves post Phase 3A sign-off.

## Phase 3A — FINAL Sign-off Blocker Round (Feb 2026)
All 26 independent-audit blockers implemented and regressed. 91/91 Phase
3A tests pass.

### Implemented (Feb 2026)
1. **Proforma Conversion Readiness (item 1)** — server.py runs a READ-ONLY
   duplicate preflight on `converted_from_proforma_id`. If duplicates
   exist, conflicting IDs are logged and `app.state.proforma_conversion_ready`
   is set False. The conversion route returns 503
   `PROFORMA_CONVERSION_GUARD_UNAVAILABLE` until ops resolve the duplicates.
   Unique partial index is created only when preflight is clean.
2. **True Concurrency Test (item 2)** — `test_2_duplicate_conversion_no_second_invoice`
   uses `asyncio.gather` with 5 parallel calls. Asserts exactly ONE
   converted invoice ever exists.
3. **One Reversal Engine (item 3)** — `DELETE /api/finance/admin/payments/{id}`
   now delegates to `PaymentReversalService.execute(alias="finance_admin_delete")`.
   Legacy `POST /api/superadmin/payments/{id}/void` and formal
   `POST /api/superadmin/payment-reversal/execute` also delegate. Test/dev
   hard-delete path unchanged.
4. **Reversal Concurrent Idempotency (item 4)** — unique index on
   `payment_reversals.payment_id`. Service uses an atomic conditional
   update to claim the payment row; concurrent losers return the winning
   reversal record.
5. **Legacy Voided in Payment History (item 5)** — `_build_payment_history_query`
   default `status="active"` now excludes BOTH `reversed` and `voided`.
   New filters: `voided`, `inactive`. CSV export shares the same query builder.
6. **Atomic CN Issue (item 6)** — `/credit-notes/{id}/issue` snapshots
   prior status, flips to `issued`, then attempts `post_credit_note_issued`.
   On failure, restores prior CN state, voids any partial journal, and
   returns 500 `CN_ACCOUNTING_POST_FAILED`. Failure-injection test
   `test_88_normal_cn_issue_failure_compensated` proves rollback.
7. **Payment + Linked CN Half-Success** — payment CN auto-post already
   guarded; hard exceptions surface via audit log; retry safe.
8. **Atomic Issued-CN Correction (item 8)** — voids old journals, posts
   corrected journal, and on hard failure restores original CN amount
   and re-activates original journals. Returns 500
   `CN_CORRECTION_ACCOUNTING_FAILED`.
9. **Invoice Value Line-Item Consistency (item 9)** — single-line auto-
   recalc allowed; multi-line requires explicit `corrected_line_items` +
   `new_subtotal` + `new_tax_amount` that sum consistently within RM
   rounding tolerance. Ambiguous cases return
   `AMBIGUOUS_LINE_ITEM_DISTRIBUTION`.
10. **Invoice Value Accounting Delta (item 10)** — void existing active
    issuance journals and repost via `post_invoice_issued` for the
    corrected total. Audit records `voided_journal_ids` and `new_journal_ids`.
11. **Confirmation on Number/Date/Text (item 11)** — locked/terminal
    invoice corrections now require `confirm=true` (schemas updated;
    default false returns preview).
12. **Strict ISO Date Validation (item 12)** — `correct-date` enforces
    `YYYY-MM-DD` regex + `datetime.strptime` calendar validation. Test 83
    replaced with genuine invalid dates (`2026-13-40`, `banana`, `04/09/26`).
    New test 83b confirms locked-invoice preview/confirm gating.
13. **Safe Direct Invoice Void (item 13)** — SuperAdmin
    `/invoices/{id}/void` blocks with `INVOICE_HAS_ACTIVE_PAYMENTS` or
    `INVOICE_HAS_ACTIVE_ISSUED_CNS` unless they are reversed / voided
    first. Voids active issuance journals; records
    `voided_journal_ids` in the audit.
14. **Formal Reversal Fix (item 14)** — normal `/reverse-void` already
    returns 409 `INVOICE_RESURRECTION_BLOCKED`. Repair Status is the sole
    SuperAdmin path.
15. **Frontend SoT Adoption (items 16-18)** —
    `ClaimFormPrint.jsx` fetches
    `/finance/source-of-truth/session/{id}/snapshot` and uses canonical
    `session_revenue / session_cost / gross_profit / gross_margin_pct`.
    Local recomputation removed. Multi-invoice rows render
    `net_invoiced_value` in the TOTAL column. `invoice_date` fallback uses
    `invoice_created_at` (never generic `created_at`).
16. **PaymentsTab selectedInvoiceId (item 19)** — `useEffect` on
    `selectedInvoiceId` prop change auto-runs `handleInvoiceSelect`.
    `paymentDisabled` now also requires `canonicalOutstanding` to be
    present.
17. **Test 32 (item 20)** — rewritten to call the real `PUT /api/sessions/{id}`
    endpoint (admin_token) and asserts: issued invoice snapshot unchanged;
    pre-issue invoice reflects at least one cascaded field.
18. **Archive Visibility Test (item 21)** — `test_87_archive_visibility`
    asserts archived session is absent from active list and financial
    docs preserved.
19. **Failure-Injection Tests (item 22)** — `test_88` (CN issue),
    `test_90` (concurrent reversal) added.
20. **Ephemeral Upload Storage Migration** — new
    `/app/backend/services/object_storage.py` routes all 12 pod-local
    upload sites through Emergent Object Storage.

### Files Changed (Latest Round)
- backend/server.py
- backend/routes/finance_invoices.py
- backend/routes/finance_payments.py
- backend/routes/superadmin_portal.py
- backend/routes/superadmin_finance_corrections.py
- backend/services/payment_reversal.py
- backend/services/superadmin_financial_correction.py
- backend/tests/test_phase3a_write_protection.py
- backend/services/object_storage.py (NEW)
- backend/routes/{static_files,settings,checklists,reports,training_reports,certificates,finance_payables}.py
- frontend/src/components/ClaimFormPrint.jsx
- frontend/src/components/finance/PaymentsTab.jsx

### Regression Status
- Phase 3A: **91/91 pass** (verified by testing_agent iteration_51.json)
- Backend healthy (HTTP 200), Frontend healthy (HTTP 200)

## User Preferences (STRICT)
- DO NOT DEPLOY.
- DO NOT START Phase 3B.
- Preserve SuperAdmin God Mode.
- Never mask tests with `status in (200, 400)` fallback assertions.
- Test isolation: `DB_NAME_phase2_test` only, tagged with `ph3_test`.

## Test Credentials
- Super Admin: arjuna@mddrc.com.my / Dana102229

## Marketing Bug Fixes — Feb 2026 (iter 52)
Verified by testing_agent (11/11 pytest pass):
1. Quotation PDF: `end_date` is now persisted on client-response and the download-pdf endpoint renders (a) single date, (b) `training_date to end_date` range, (c) comma-separated non-consecutive `training_dates` list. Client TO/Attn block now sets X=10 before every line so "Attn:" is left-aligned with company_name/Tel.
2. Revert Acceptance: new endpoint `POST /api/marketing/quotations/{id}/revert-acceptance` — reverts status back to `sent`, deletes the auto-created draft session, syncs lead stage. Blocked (409 SESSION_HAS_FINANCIAL_HISTORY) if the linked session already has issued invoice / payment / credit note / journal.
3. Session Costing Prefill: `GET /api/finance/session/{id}/costing` now returns a `quotation` snapshot (total_amount, pricing_type, rate_per_pax, group_price, num_participants) when the session was auto-created from an accepted quotation. `SessionCosting.jsx` prefills invoice amount from that snapshot so admin only enters costing values.

Files touched: `backend/routes/marketing.py`, `backend/routes/finance_session.py`, `frontend/src/pages/MarketingDashboard.jsx`, `frontend/src/components/marketing/QuotationsTab.jsx`, `frontend/src/components/SessionCosting.jsx`. New regression suite: `backend/tests/test_marketing_bugfixes_iter52.py`.

## Upcoming (Blocked Until Sign-Off)
- P0: Phase 3B Dynamic Funding Source Foundation
- P1: Roles/Multi-Role redesign, Calendar, Marketing Easy Mode,
  Quotation redesign, Certificates enhancements
- P1: Petty Cash → Session Expenses linkage
- P1: Trainer Contract Workflow, System-wide Digital Signatures
