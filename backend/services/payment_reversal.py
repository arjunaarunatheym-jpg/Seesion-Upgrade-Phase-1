"""Canonical Payment Reversal Service (Phase 3A Section J).

Single reversal engine used by:
    - Finance production payment DELETE (auto-reverses in production mode).
    - Legacy SuperAdmin ``/payments/{id}/void`` (delegated alias).
    - SuperAdmin formal ``/payment-reversal/execute`` (audited preview/execute).

Design guarantees:
    - Never mutates ``amount_paid`` on invoices via raw arithmetic. Invoice
      status is derived from a fresh :class:`FinancialSourceOfTruth` snapshot
      after the payment is marked reversed and any explicitly-linked CN is
      voided.
    - Idempotent: retrying a reversal for the same payment returns the prior
      reversal record instead of creating a duplicate.
    - Legacy inactive statuses (``reversed`` and ``voided``) are treated as
      non-active by :class:`FinancialSourceOfTruth`; this service preserves
      those rows and never rewrites them.
    - Only credit notes with ``source_payment_id == payment.id`` are
      auto-voided. Legacy CNs on the same invoice are surfaced as
      ``manual_review_credit_notes`` — never automatically voided.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.financial_source_of_truth import FinancialSourceOfTruth


NON_ACTIVE_PAYMENT_STATUSES = frozenset({"reversed", "voided"})


class PaymentReversalService:
    def __init__(self, db):
        self.db = db
        self.sot = FinancialSourceOfTruth(db)

    # ------------------------------------------------------------------ #
    # PREVIEW
    # ------------------------------------------------------------------ #
    async def preview(self, payment_id: str) -> Dict[str, Any]:
        payment = await self.db.payments.find_one({"id": payment_id}, {"_id": 0})
        if not payment:
            return {"error": "PAYMENT_NOT_FOUND"}
        invoice = None
        if payment.get("invoice_id"):
            invoice = await self.db.invoices.find_one({"id": payment["invoice_id"]}, {"_id": 0})

        auto_affected: List[Dict[str, Any]] = []
        manual_review: List[Dict[str, Any]] = []
        if invoice:
            cns = await self.db.credit_notes.find(
                {"invoice_id": invoice["id"], "status": {"$nin": list(NON_ACTIVE_PAYMENT_STATUSES)}},
                {"_id": 0},
            ).to_list(200)
            for cn in cns:
                bucket = auto_affected if cn.get("source_payment_id") == payment_id else manual_review
                bucket.append({
                    "id": cn.get("id"),
                    "cn_number": cn.get("cn_number"),
                    "amount": cn.get("amount"),
                    "status": cn.get("status"),
                    "source_payment_id": cn.get("source_payment_id"),
                })

        auto_journals: List[Dict[str, Any]] = []
        # Payment journal entries
        payment_journals = await self.db.journal_entries.find(
            {"source_id": payment_id, "source_module": "payment",
             "status": {"$ne": "voided"}},
            {"_id": 0, "id": 1, "journal_no": 1, "description": 1,
             "total_debit": 1, "status": 1},
        ).to_list(20)
        auto_journals.extend(payment_journals)
        # Journals for auto-affected CNs
        for cn in auto_affected:
            cn_journals = await self.db.journal_entries.find(
                {"source_id": cn["id"], "source_module": "credit_note",
                 "status": {"$ne": "voided"}},
                {"_id": 0, "id": 1, "journal_no": 1, "description": 1,
                 "total_debit": 1, "status": 1},
            ).to_list(20)
            auto_journals.extend(cn_journals)

        # Compute the after-reversal SoT status
        new_status: Optional[str] = None
        if invoice:
            # Simulate: exclude the current payment, include no CN removals yet
            simulated_payments = await self.db.payments.find(
                {"invoice_id": invoice["id"], "id": {"$ne": payment_id},
                 "status": {"$nin": list(NON_ACTIVE_PAYMENT_STATUSES)}},
                {"_id": 0},
            ).to_list(500)
            simulated_cns = await self.db.credit_notes.find(
                {"invoice_id": invoice["id"]}, {"_id": 0},
            ).to_list(500)
            # Also simulate the auto-void of the linked CN(s)
            auto_ids = {c["id"] for c in auto_affected}
            simulated_cns = [
                {**c, "status": "voided"} if c["id"] in auto_ids else c
                for c in simulated_cns
            ]
            snap = self.sot._compute_invoice_snapshot(invoice, simulated_payments, simulated_cns)
            new_status = self._derive_invoice_status(invoice, snap)

        return {
            "payment": {
                "id": payment.get("id"),
                "amount": payment.get("amount", 0),
                "receipt_number": payment.get("receipt_number"),
                "status": payment.get("status", "active"),
                "payment_date": payment.get("payment_date"),
                "payment_method": payment.get("payment_method"),
            },
            "invoice": {
                "id": invoice.get("id"),
                "invoice_number": invoice.get("invoice_number"),
                "company_name": invoice.get("company_name") or invoice.get("bill_to_name"),
                "current_status": invoice.get("status"),
                "new_status_after_reversal": new_status,
            } if invoice else None,
            "auto_affected_credit_notes": auto_affected,
            "manual_review_credit_notes": manual_review,
            "auto_affected_journal_entries": auto_journals,
            "summary": {
                "auto_credit_notes": len(auto_affected),
                "manual_review_credit_notes": len(manual_review),
                "journals_to_void": len(auto_journals),
            },
        }

    # ------------------------------------------------------------------ #
    # EXECUTE
    # ------------------------------------------------------------------ #
    async def execute(
        self,
        payment_id: str,
        *,
        reason: str,
        user: Any,
        alias: str = "canonical",
    ) -> Dict[str, Any]:
        """Reverse a payment. Idempotent based on payment_reversals.status.

        MINI PHASE 1 (E) — strict order:
            1. Validate payment.
            2. Reserve in-progress reversal record.
            3. Void linked CNs (source_payment_id == payment.id). Preserve
               unrelated / manual CNs.
            4. Void the payment journal and journals of the linked CNs.
            5. Atomic-claim flip payment.status = "reversed".
            6. Confirm the flip actually landed.
            7. ONLY AFTER payment.status is reversed: take a fresh
               FinancialSourceOfTruth snapshot and derive the invoice status.
            8. Update invoice.status.
            9. Update session.invoice_status = EXACTLY the same status.
           10. ONLY AFTER 7-9 succeed: mark payment_reversals.status = "completed".
        """
        payment = await self.db.payments.find_one({"id": payment_id}, {"_id": 0})
        if not payment:
            return {"error": "PAYMENT_NOT_FOUND"}

        # ---- STRICT IDEMPOTENCY (Section E) ----------------------------
        # payment.status == "reversed" BY ITSELF is not enough to claim
        # completion. The source of truth for "completed" is the matching
        # payment_reversals record.
        if payment.get("status") == "reversed":
            existing = await self.db.payment_reversals.find_one(
                {"payment_id": payment_id}, {"_id": 0},
            )
            existing_status = (existing or {}).get("status")
            if existing_status == "completed":
                return {
                    "message": "Payment already reversed",
                    "idempotent": True,
                    "reversal": existing,
                    "payment_id": payment_id,
                }
            if existing_status == "in_progress":
                return {
                    "message": "Reversal already in progress",
                    "code": "REVERSAL_IN_PROGRESS",
                    "payment_id": payment_id,
                    "idempotent": True,
                }
            if existing_status == "recovery_required":
                return {
                    "message": "Prior reversal attempt requires ops recovery",
                    "code": "REVERSAL_RECOVERY_REQUIRED",
                    "payment_id": payment_id,
                    "idempotent": True,
                }
            # Payment is 'reversed' but there is NO completed reversal
            # record — do NOT claim completed.
            return {
                "message": (
                    "Payment status is 'reversed' but no completed reversal "
                    "record exists; ops recovery required."
                ),
                "code": "REVERSAL_RECOVERY_REQUIRED",
                "payment_id": payment_id,
                "idempotent": True,
            }

        now = datetime.now(timezone.utc)
        reversal_id = str(uuid.uuid4())
        actions_taken: List[str] = []

        # ---- 1. Reserve in-progress reversal record --------------------
        # Unique index on payment_id makes concurrent losers observe the
        # existing record.
        try:
            await self.db.payment_reversals.insert_one({
                "id": reversal_id,
                "payment_id": payment_id,
                "status": "in_progress",
                "reason": reason,
                "alias": alias,
                "reversed_by": getattr(user, "id", None),
                "reversed_by_name": getattr(user, "full_name", None),
                "reversed_at": now.isoformat(),
            })
        except Exception:
            existing = await self.db.payment_reversals.find_one(
                {"payment_id": payment_id}, {"_id": 0},
            )
            existing_status = (existing or {}).get("status")
            if existing_status == "completed":
                return {
                    "message": "Payment already reversed (concurrent completed)",
                    "idempotent": True,
                    "reversal": existing,
                    "payment_id": payment_id,
                }
            return {
                "message": (
                    "Reversal already in progress or awaiting recovery"
                    if existing_status != "recovery_required"
                    else "Prior reversal attempt requires ops recovery"
                ),
                "code": (
                    "REVERSAL_IN_PROGRESS"
                    if existing_status != "recovery_required"
                    else "REVERSAL_RECOVERY_REQUIRED"
                ),
                "payment_id": payment_id,
                "idempotent": True,
            }

        invoice: Optional[Dict[str, Any]] = None
        if payment.get("invoice_id"):
            invoice = await self.db.invoices.find_one(
                {"id": payment["invoice_id"]}, {"_id": 0},
            )

        # ---- 2. Void EXPLICITLY LINKED CNs; preserve manual CNs --------
        voided_credit_notes: List[str] = []
        manual_review: List[Dict[str, Any]] = []
        if invoice:
            cns_on_invoice = await self.db.credit_notes.find(
                {"invoice_id": invoice["id"], "status": {"$ne": "voided"}},
                {"_id": 0},
            ).to_list(500)
            for cn in cns_on_invoice:
                if cn.get("source_payment_id") != payment_id:
                    manual_review.append({
                        "id": cn.get("id"),
                        "cn_number": cn.get("cn_number"),
                        "amount": cn.get("amount"),
                        "status": cn.get("status"),
                        "source_payment_id": cn.get("source_payment_id"),
                    })
                    continue
                await self.db.credit_notes.update_one(
                    {"id": cn["id"]},
                    {"$set": {
                        "status": "voided",
                        "voided_by": getattr(user, "id", None),
                        "voided_at": now.isoformat(),
                        "void_reason": f"Payment reversal: {reason}",
                        "reversal_id": reversal_id,
                        "updated_at": now.isoformat(),
                    }},
                )
                voided_credit_notes.append(cn["id"])
                actions_taken.append(
                    f"Credit Note {cn.get('cn_number')} voided "
                    f"(RM {float(cn.get('amount') or 0):,.2f})"
                )

        # ---- 3. Void related journal entries (idempotent) --------------
        voided_journals: List[str] = []
        payment_journals = await self.db.journal_entries.find(
            {"source_id": payment_id, "source_module": "payment",
             "status": {"$ne": "voided"}},
            {"_id": 0},
        ).to_list(20)
        for je in payment_journals:
            await self.db.journal_entries.update_one(
                {"id": je["id"], "status": {"$ne": "voided"}},
                {"$set": {
                    "status": "voided",
                    "voided_by": getattr(user, "id", None),
                    "voided_by_name": getattr(user, "full_name", None),
                    "voided_at": now.isoformat(),
                    "void_reason": f"Payment reversal: {reason}",
                    "reversal_id": reversal_id,
                    "updated_at": now.isoformat(),
                }},
            )
            voided_journals.append(je["id"])
        for cn_id in voided_credit_notes:
            cn_journals = await self.db.journal_entries.find(
                {"source_id": cn_id, "source_module": "credit_note",
                 "status": {"$ne": "voided"}},
                {"_id": 0},
            ).to_list(20)
            for je in cn_journals:
                await self.db.journal_entries.update_one(
                    {"id": je["id"], "status": {"$ne": "voided"}},
                    {"$set": {
                        "status": "voided",
                        "voided_by": getattr(user, "id", None),
                        "voided_by_name": getattr(user, "full_name", None),
                        "voided_at": now.isoformat(),
                        "void_reason": f"Payment reversal: {reason}",
                        "reversal_id": reversal_id,
                        "updated_at": now.isoformat(),
                    }},
                )
                voided_journals.append(je["id"])

        # ---- 4. Atomic claim: flip payment.status = "reversed" ---------
        # MUST occur BEFORE the fresh SoT snapshot below (Section E strict
        # order). If this update lands 0 rows, someone else finished ahead
        # of us — do NOT claim success.
        claim = await self.db.payments.update_one(
            {"id": payment_id, "status": {"$nin": list(NON_ACTIVE_PAYMENT_STATUSES)}},
            {"$set": {
                "status": "reversed",
                "reversed_by": getattr(user, "id", None),
                "reversed_by_name": getattr(user, "full_name", None),
                "reversed_at": now.isoformat(),
                "reversal_reason": reason,
                "reversal_id": reversal_id,
                "reversal_alias": alias,
                "updated_at": now.isoformat(),
            }},
        )
        if claim.modified_count != 1:
            existing = await self.db.payment_reversals.find_one(
                {"payment_id": payment_id, "status": "completed"}, {"_id": 0},
            )
            if existing:
                return {
                    "message": "Payment already reversed (peer completed)",
                    "idempotent": True,
                    "reversal": existing,
                    "payment_id": payment_id,
                }
            await self.db.payment_reversals.update_one(
                {"id": reversal_id},
                {"$set": {"status": "recovery_required",
                          "note": "payment flip did not modify a row"}},
            )
            return {
                "message": "Payment reversal requires ops recovery",
                "code": "REVERSAL_RECOVERY_REQUIRED",
                "payment_id": payment_id,
                "reversal_id": reversal_id,
                "idempotent": False,
            }
        actions_taken.append(
            f"Payment RM {float(payment.get('amount') or 0):,.2f} reversed"
        )

        # ---- 5. POST-FLIP: fresh SoT snapshot + invoice/session sync ---
        # If any part of the reconciliation fails, DO NOT mark the reversal
        # completed. Mark payment_reversals.status = "recovery_required"
        # and return a controlled non-success. Payment is already reversed
        # so we do not un-reverse it.
        new_status: Optional[str] = None
        try:
            if invoice:
                fresh = await self.sot.get_invoice_snapshot(invoice["id"])
                if fresh is None:
                    raise Exception("SOT_SNAPSHOT_UNAVAILABLE")
                new_status = self._derive_invoice_status(invoice, fresh)
                if new_status and new_status != invoice.get("status"):
                    await self.db.invoices.update_one(
                        {"id": invoice["id"]},
                        {"$set": {"status": new_status,
                                  "updated_at": now.isoformat()}},
                    )
                    actions_taken.append(
                        f"Invoice {invoice.get('invoice_number')} status: "
                        f"{invoice.get('status')} → {new_status}"
                    )
                final_status = new_status or invoice.get("status")
                if final_status:
                    # session.invoice_status MUST match invoice.status exactly.
                    await self.db.sessions.update_one(
                        {"invoice_id": invoice["id"]},
                        {"$set": {"invoice_status": final_status}},
                    )
        except Exception as e:
            await self.db.payment_reversals.update_one(
                {"id": reversal_id},
                {"$set": {"status": "recovery_required",
                          "note": f"post-flip SoT reconciliation failed: {e}"}},
            )
            return {
                "message": (
                    "Payment reversed but final Source-of-Truth reconciliation "
                    "failed; ops recovery required."
                ),
                "code": "REVERSAL_RECOVERY_REQUIRED",
                "payment_id": payment_id,
                "reversal_id": reversal_id,
                "idempotent": False,
                "error": str(e),
            }

        # ---- 6. Finalize: mark payment_reversals completed -------------
        company_name = (
            invoice.get("company_name") or invoice.get("bill_to_name") or "Unknown"
        ) if invoice else "Unknown"
        reversal_record = {
            "id": reversal_id,
            "payment_id": payment_id,
            "payment_amount": payment.get("amount", 0),
            "receipt_number": payment.get("receipt_number"),
            "invoice_id": payment.get("invoice_id"),
            "invoice_number": invoice.get("invoice_number") if invoice else None,
            "company_name": company_name,
            "voided_credit_notes": voided_credit_notes,
            "voided_journal_entries": voided_journals,
            "manual_review_credit_notes": manual_review,
            "reason": reason,
            "alias": alias,
            "actions_taken": actions_taken,
            "reversed_by": getattr(user, "id", None),
            "reversed_by_name": getattr(user, "full_name", None),
            "reversed_at": now.isoformat(),
        }
        await self.db.payment_reversals.update_one(
            {"id": reversal_id},
            {"$set": {**reversal_record, "status": "completed"}},
        )
        reversal_record.pop("_id", None)
        return {
            "message": "Payment reversed successfully",
            "reversal_id": reversal_id,
            "idempotent": False,
            "actions_taken": actions_taken,
            "unlinked_credit_notes_needing_review": manual_review,
            "summary": {
                "payment_reversed": f"RM {float(payment.get('amount') or 0):,.2f}",
                "credit_notes_voided": len(voided_credit_notes),
                "credit_notes_needing_manual_review": len(manual_review),
                "journals_voided": len(voided_journals),
                "invoice_status": new_status or (invoice.get("status") if invoice else "N/A"),
            },
        }

    # ------------------------------------------------------------------ #
    # Helper: derive canonical invoice status from a fresh SoT snapshot
    # ------------------------------------------------------------------ #
    @staticmethod
    def _derive_invoice_status(invoice: Dict[str, Any], snap: Dict[str, Any]) -> str:
        """Map SoT canonical values → invoice.status.

        Preserves terminal statuses (voided/cancelled/deleted/converted).
        Only issued/partially_paid/paid participate in the mapping.
        """
        cur = (invoice.get("status") or "").lower()
        if cur in {"voided", "cancelled", "deleted", "converted"}:
            return cur
        paid = float(snap.get("paid_amount") or 0)
        outstanding = float(snap.get("outstanding_amount") or 0)
        net = float(snap.get("net_invoiced_value") or 0)
        if paid <= 0:
            return "issued"
        if outstanding <= 0.005 and paid > 0:
            return "paid"
        if 0 < paid < net:
            return "partially_paid"
        return "issued"
