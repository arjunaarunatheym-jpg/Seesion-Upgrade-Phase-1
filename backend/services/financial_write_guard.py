"""Financial Write Guard (Phase 3A)
==========================================================================
Centralized WRITE-side domain validation for MDDRC financial operations.
Reuses the Phase 2 `FinancialSourceOfTruth` for all read-side calculations
(net invoiced value, canonical outstanding, credit-note aggregation, etc.).
It NEVER duplicates those rules — it composes them.

This module is intentionally small and focused. It exposes:
- InvoiceLifecycleState                 canonical status buckets
- CreditNoteLifecycleState              canonical CN status buckets
- FinancialSafetyError                  raised when a write is unsafe
- FinancialAmbiguityError               raised for AMBIGUOUS_SESSION_INVOICE_SELECTION
- FinancialImmutabilityError            raised when a locked field is edited
- FinancialWriteGuard                   service class
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, Iterable, List, Optional

from services.financial_source_of_truth import (
    FinancialSourceOfTruth,
    ACTIVE_CN_STATUSES,
    EXCLUDED_INVOICE_STATUSES,
    INFORMATIONAL_INVOICE_STATUSES,
    KNOWN_INVOICE_STATUSES,
    PROFORMA_DOC_TYPE,
    REVENUE_ELIGIBLE_INVOICE_STATUSES,
)


# =============================================================================
# Canonical write-side buckets
# =============================================================================
class InvoiceLifecycleState:
    """Grouping of invoice statuses for write-guard purposes."""
    PRE_ISSUE = INFORMATIONAL_INVOICE_STATUSES  # draft, auto_draft
    LOCKED_ACTIVE = REVENUE_ELIGIBLE_INVOICE_STATUSES  # issued, partially_paid, paid
    TERMINAL = EXCLUDED_INVOICE_STATUSES  # voided, cancelled, deleted, converted

    #: Financial fields that MUST NOT be edited once the invoice is
    #: LOCKED_ACTIVE or TERMINAL. Phase 3A Section B: ``status`` is a
    #: material lifecycle field — arbitrary status mutation via a generic
    #: PUT is prohibited. SuperAdmin lifecycle repair uses the dedicated
    #: controlled workflows.
    LOCKED_FIELDS = frozenset({
        "status",
        "total_amount",
        "subtotal",
        "tax_amount",
        "tax_rate",
        "invoice_number",
        "invoice_date",
        "due_date",
        "issue_date",
        "bill_to_name",
        "bill_to_address",
        "bill_to_email",
        "company_id",
        "company_name",
        "programme_name",
        "session_name",
        "line_items",
        "invoice_lines",
        "document_type",
        "converted_from_proforma_id",
        "funding_source_id",
        "funding_source_code",
    })


class CreditNoteLifecycleState:
    """Canonical CN lifecycle (Phase 3A).

    NOTE: This intentionally changes the Phase 2 rule.
    ONLY status == "issued" reduces canonical net invoiced value.
    """
    DRAFT = "draft"
    APPROVED = "approved"
    ISSUED = "issued"
    VOIDED = "voided"

    ACTIVE_STATUSES = frozenset({ISSUED})            # reduces canonical net
    PENDING_STATUSES = frozenset({DRAFT, APPROVED})  # editable, no AR effect
    INACTIVE_STATUSES = frozenset({VOIDED})
    KNOWN_STATUSES = ACTIVE_STATUSES | PENDING_STATUSES | INACTIVE_STATUSES


# =============================================================================
# Errors
# =============================================================================
class FinancialSafetyError(Exception):
    """Raised when a write is unsafe (e.g. payment against Proforma)."""
    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class FinancialAmbiguityError(FinancialSafetyError):
    """Multiple invoices match a session-only request — caller must pick one."""
    def __init__(self, message: str, candidates: List[Dict[str, Any]]):
        super().__init__("AMBIGUOUS_SESSION_INVOICE_SELECTION", message, http_status=409)
        self.candidates = candidates


class FinancialImmutabilityError(FinancialSafetyError):
    """A locked financial field was edited on a locked/terminal invoice."""
    def __init__(self, invoice_id: str, status: str, fields: Iterable[str]):
        flist = sorted(set(fields))
        super().__init__(
            code="INVOICE_LOCKED",
            message=(
                f"Invoice {invoice_id} is in status {status!r}; the following "
                f"financial fields are locked and cannot be edited: {flist}. "
                f"Use void/cancel + replacement or a Credit Note instead."
            ),
            http_status=409,
        )
        self.fields = flist


# =============================================================================
# Money helpers
# =============================================================================
def is_production_mode() -> bool:
    """True unless the environment is explicitly a test/dev environment.

    Precedence:
    - APP_ENV=production forces True (even against a test DB).
    - APP_ENV in {test, dev, development, local} → False.
    - Otherwise, DB_NAME containing '_test' / '_phase2_test' → False.
    - Fallback: True.
    """
    env = (os.environ.get("APP_ENV") or "").lower()
    if env == "production":
        return True
    if env in {"test", "dev", "development", "local"}:
        return False
    db_name = (os.environ.get("DB_NAME") or "").lower()
    if "_test" in db_name or "_phase2_test" in db_name:
        return False
    return True


def validate_money(amount: Any, *, allow_zero: bool = False,
                   allow_negative: bool = False, field: str = "amount") -> float:
    """Reject NaN / non-numeric / zero / negative, round to 2dp."""
    try:
        v = float(amount)
    except (TypeError, ValueError):
        raise FinancialSafetyError(
            "INVALID_AMOUNT", f"{field} must be a number.", http_status=400,
        )
    if math.isnan(v) or math.isinf(v):
        raise FinancialSafetyError(
            "INVALID_AMOUNT", f"{field} must be a finite number.", http_status=400,
        )
    if not allow_zero and v == 0:
        raise FinancialSafetyError(
            "ZERO_AMOUNT_NOT_ALLOWED", f"{field} must be greater than zero.",
            http_status=400,
        )
    if not allow_negative and v < 0:
        raise FinancialSafetyError(
            "NEGATIVE_AMOUNT_NOT_ALLOWED", f"{field} cannot be negative.",
            http_status=400,
        )
    return round(v, 2)


# =============================================================================
# Guard service
# =============================================================================
class FinancialWriteGuard:
    """Composes read-side canonical rules (via FinancialSourceOfTruth) with
    write-side domain validation. All checks raise FinancialSafetyError on
    failure — callers translate to HTTPException.
    """

    #: Collections whose presence indicates the session has financial history.
    FINANCIAL_HISTORY_COLLECTIONS = (
        "invoices", "payments", "credit_notes", "journal_entries",
    )

    def __init__(self, db):
        self.db = db
        self.sot = FinancialSourceOfTruth(db)

    # -------------------------------------------------------------------------
    # Session → Invoice resolver
    # -------------------------------------------------------------------------
    async def resolve_session_primary_invoice(
        self,
        session_id: str,
        explicit_invoice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return the canonical primary invoice for a session write.

        Priority:
          1. explicit_invoice_id if provided — must belong to session.
          2. session.invoice_id if set — must exist, belong to session, be
             a real invoice (not proforma).
          3. If session has exactly one eligible (non-proforma, non-terminal)
             invoice, use it.
          4. Otherwise raise FinancialAmbiguityError with the candidate list.

        Never uses find_one({"session_id": ...}) as authoritative.
        """
        session = await self.db.sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            raise FinancialSafetyError(
                "SESSION_NOT_FOUND", f"Session {session_id} not found.", http_status=404,
            )

        if explicit_invoice_id:
            inv = await self.db.invoices.find_one({"id": explicit_invoice_id}, {"_id": 0})
            if not inv:
                raise FinancialSafetyError(
                    "INVOICE_NOT_FOUND", f"Invoice {explicit_invoice_id} not found.",
                    http_status=404,
                )
            if inv.get("session_id") != session_id:
                raise FinancialSafetyError(
                    "INVOICE_SESSION_MISMATCH",
                    f"Invoice {explicit_invoice_id} does not belong to session {session_id}.",
                    http_status=400,
                )
            if inv.get("document_type") == PROFORMA_DOC_TYPE:
                raise FinancialSafetyError(
                    "INVOICE_IS_PROFORMA",
                    "Requested document is a Proforma, not a real invoice.",
                    http_status=400,
                )
            return inv

        primary_id = session.get("invoice_id")
        if primary_id:
            inv = await self.db.invoices.find_one({"id": primary_id}, {"_id": 0})
            if inv and inv.get("session_id") == session_id and inv.get("document_type") != PROFORMA_DOC_TYPE:
                return inv
            # session.invoice_id is stale — fall through to candidate search.

        # Search for real, non-terminal invoices in this session.
        candidates_cursor = self.db.invoices.find(
            {"session_id": session_id, "document_type": {"$ne": PROFORMA_DOC_TYPE}},
            {"_id": 0},
        )
        candidates = [
            c async for c in candidates_cursor
            if (c.get("status") or "").lower() not in EXCLUDED_INVOICE_STATUSES
        ]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise FinancialSafetyError(
                "NO_ELIGIBLE_INVOICE",
                f"Session {session_id} has no eligible invoice for this operation.",
                http_status=404,
            )
        raise FinancialAmbiguityError(
            f"Session {session_id} has {len(candidates)} eligible invoices; "
            "an explicit invoice_id is required.",
            candidates=[
                {"id": c.get("id"), "invoice_number": c.get("invoice_number"),
                 "status": c.get("status"), "total_amount": c.get("total_amount")}
                for c in candidates
            ],
        )

    # -------------------------------------------------------------------------
    # Invoice write-side checks
    # -------------------------------------------------------------------------
    def _invoice_locked_status(self, inv: Dict[str, Any]) -> Optional[str]:
        status = (inv.get("status") or "").lower()
        if status in InvoiceLifecycleState.LOCKED_ACTIVE:
            return status
        if status in InvoiceLifecycleState.TERMINAL:
            return status
        return None

    def assert_invoice_editable(
        self,
        invoice: Dict[str, Any],
        proposed_updates: Dict[str, Any],
    ) -> None:
        """Reject edits to LOCKED financial fields on locked/terminal invoices.
        Non-financial metadata (updated_at, audit fields) is always allowed.
        """
        locked_status = self._invoice_locked_status(invoice)
        if not locked_status:
            return  # Pre-issue drafts — normal edits allowed.
        touched = InvoiceLifecycleState.LOCKED_FIELDS & set(proposed_updates.keys())
        if touched:
            raise FinancialImmutabilityError(
                invoice_id=invoice.get("id", "?"),
                status=locked_status,
                fields=touched,
            )

    async def validate_payment_recordable(
        self,
        invoice_id: str,
        amount: float,
    ) -> Dict[str, Any]:
        """All Section I checks in one call.

        Returns the loaded invoice for the caller (avoids double read).
        """
        # Money validation first (no I/O required).
        _ = validate_money(amount, field="payment amount")

        inv = await self.db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not inv:
            raise FinancialSafetyError(
                "INVOICE_NOT_FOUND", f"Invoice {invoice_id} not found.", http_status=404,
            )
        if inv.get("document_type") == PROFORMA_DOC_TYPE:
            raise FinancialSafetyError(
                "PAYMENT_AGAINST_PROFORMA",
                "Payments cannot be recorded against a Proforma. Convert it to a real invoice first.",
                http_status=400,
            )
        status = (inv.get("status") or "").lower()
        if status in InvoiceLifecycleState.TERMINAL:
            raise FinancialSafetyError(
                "PAYMENT_AGAINST_TERMINAL_INVOICE",
                f"Cannot record payment against invoice in status {status!r}.",
                http_status=400,
            )
        if status not in InvoiceLifecycleState.LOCKED_ACTIVE:
            raise FinancialSafetyError(
                "PAYMENT_AGAINST_NON_ISSUED_INVOICE",
                f"Invoice must be issued/partially_paid/paid to receive payment (got {status!r}).",
                http_status=400,
            )

        # Canonical outstanding via Phase 2 SoT (single source of truth).
        snap = await self.sot.get_invoice_snapshot(invoice_id)
        if snap is None:
            raise FinancialSafetyError(
                "INVOICE_NOT_FOUND", f"Invoice {invoice_id} not found.", http_status=404,
            )
        outstanding = float(snap.get("outstanding_amount") or 0)
        if outstanding <= 0:
            raise FinancialSafetyError(
                "INVOICE_FULLY_SETTLED",
                "Invoice has zero canonical outstanding — no further payment can be recorded.",
                http_status=400,
            )
        if float(amount) - outstanding > 0.01:  # >1sen over
            raise FinancialSafetyError(
                "PAYMENT_EXCEEDS_OUTSTANDING",
                f"Payment RM{float(amount):.2f} exceeds canonical outstanding RM{outstanding:.2f}.",
                http_status=400,
            )
        return inv

    async def validate_credit_note_creation(
        self,
        invoice_id: Optional[str],
    ) -> Dict[str, Any]:
        """Phase 3A Section F: normal Credit Note creation is allowed ONLY
        against a real invoice whose status is issued / partially_paid / paid.

        Rejects: draft, auto_draft, finance_review, approved, proforma,
        converted, cancelled, voided, deleted, missing invoice.
        """
        if not invoice_id:
            raise FinancialSafetyError(
                "CN_INVOICE_REQUIRED", "invoice_id is required to create a Credit Note.",
                http_status=400,
            )
        inv = await self.db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not inv:
            raise FinancialSafetyError(
                "CN_INVOICE_NOT_FOUND", f"Invoice {invoice_id} not found.", http_status=404,
            )
        if inv.get("document_type") == PROFORMA_DOC_TYPE:
            raise FinancialSafetyError(
                "CN_AGAINST_PROFORMA", "Credit Notes cannot be created against a Proforma.",
                http_status=400,
            )
        status = (inv.get("status") or "").lower()
        if status in InvoiceLifecycleState.TERMINAL:
            raise FinancialSafetyError(
                "CN_AGAINST_TERMINAL_INVOICE",
                f"Credit Notes cannot be created against a {status!r} invoice.",
                http_status=400,
            )
        if status not in InvoiceLifecycleState.LOCKED_ACTIVE:
            # Pre-issue (draft/auto_draft/finance_review/approved) is REJECTED
            # — CNs are only meaningful against a real financial document.
            raise FinancialSafetyError(
                "CN_AGAINST_NON_ISSUED_INVOICE",
                f"Credit Notes can only be created against issued invoices "
                f"(got {status!r}).",
                http_status=400,
            )
        return inv

    def assert_credit_note_editable(self, cn: Dict[str, Any]) -> None:
        """Draft is fully editable. Approved is limited. Issued/voided locked."""
        status = (cn.get("status") or "").lower()
        if status in (CreditNoteLifecycleState.ISSUED, CreditNoteLifecycleState.VOIDED):
            raise FinancialSafetyError(
                "CN_LOCKED",
                f"Credit Note is in status {status!r}; amount/invoice link cannot be edited.",
                http_status=409,
            )

    # -------------------------------------------------------------------------
    # Proforma idempotency helper (Section C)
    # -------------------------------------------------------------------------
    async def find_existing_conversion(self, proforma_id: str) -> Optional[Dict[str, Any]]:
        """Return the invoice this proforma has ALREADY been converted to,
        if any. Idempotency guarantee: if this returns a doc, the conversion
        endpoint must return that doc instead of creating a new invoice."""
        existing = await self.db.invoices.find_one(
            {"converted_from_proforma_id": proforma_id}, {"_id": 0},
        )
        return existing

    # -------------------------------------------------------------------------
    # Session deletion / archive safety (Section U)
    # -------------------------------------------------------------------------
    async def session_has_financial_history(self, session_id: str) -> Dict[str, Any]:
        """Return a summary of any financially significant records.

        A session is 'financially significant' if it has ANY of:
        - invoice with status in (issued/partially_paid/paid/cancelled/voided/deleted)
        - any payment (including reversed)
        - any credit note (issued/voided/draft/approved — any status)
        - any journal entry
        """
        # Only proforma+auto_draft+draft invoices are considered "safe drafts".
        # Every other invoice (including terminal) is historical evidence.
        safe_invoice_statuses = ("draft", "auto_draft")
        hist_invoices = await self.db.invoices.count_documents({
            "session_id": session_id,
            "$or": [
                {"status": {"$nin": safe_invoice_statuses}},
                # Even auto_draft/draft REAL invoices that are converted to are still history
            ],
        })
        payments = await self.db.payments.count_documents({
            "invoice_id": {"$in": [
                i["id"] async for i in self.db.invoices.find(
                    {"session_id": session_id}, {"_id": 0, "id": 1},
                )
            ]},
        })
        credit_notes = await self.db.credit_notes.count_documents({"session_id": session_id})
        journals = await self.db.journal_entries.count_documents({"session_id": session_id})
        total = hist_invoices + payments + credit_notes + journals
        return {
            "has_history": total > 0,
            "historical_invoice_count": hist_invoices,
            "payment_count": payments,
            "credit_note_count": credit_notes,
            "journal_entry_count": journals,
        }
