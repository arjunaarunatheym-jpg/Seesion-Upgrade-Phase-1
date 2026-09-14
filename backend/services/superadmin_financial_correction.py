"""SuperAdmin Financial Correction Service (Phase 3A — controlled God Mode)
=========================================================================
Provides CONTROLLED, AUDITED, IMPACT-AWARE correction of already-locked
invoices and credit notes for the SuperAdmin role only.

Design rules:
- Every correction operation preserves the internal UUID.
- Every correction operation preserves all relationships (payments, credit
  notes, journals, session, receipts).
- Every correction operation writes a rich before/after audit record.
- Every correction operation composes with the Phase 2 canonical
  ``FinancialSourceOfTruth`` for impact preview.
- Every correction operation is READ-ONLY UNTIL confirm=True.
- Never physically deletes historical financial evidence.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.financial_source_of_truth import (
    FinancialSourceOfTruth,
    EXCLUDED_INVOICE_STATUSES,
)
from services.financial_write_guard import (
    CreditNoteLifecycleState,
    FinancialSafetyError,
    validate_money,
)


# =============================================================================
# Public constants
# =============================================================================
#: High-impact invoice fields that must NOT be silently changed via the
#: generic superadmin update endpoint on a locked invoice. Corrections to
#: these fields must go through dedicated controlled endpoints.
HIGH_IMPACT_INVOICE_FIELDS = frozenset({
    "status",
    "total_amount", "subtotal", "tax_amount", "tax_rate",
    "invoice_number", "invoice_date", "issue_date", "due_date",
    "line_items", "invoice_lines",
    "company_id", "company_name",
    "bill_to_name", "bill_to_address", "bill_to_email",
    "programme_name", "session_name",
    "document_type", "converted_from_proforma_id",
    "funding_source_id", "funding_source_code",
})

CORRECTION_TYPES = ("data_entry_correction", "commercial_adjustment", "exceptional_override")

CorrectionAudit = Dict[str, Any]


# =============================================================================
# Service
# =============================================================================
class SuperAdminFinancialCorrection:
    def __init__(self, db):
        self.db = db
        self.sot = FinancialSourceOfTruth(db)

    # -------------------------------------------------------------------------
    # Shared helpers
    # -------------------------------------------------------------------------
    async def _load_invoice(self, invoice_id: str) -> Dict[str, Any]:
        inv = await self.db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not inv:
            raise FinancialSafetyError(
                "INVOICE_NOT_FOUND", f"Invoice {invoice_id} not found.", http_status=404,
            )
        return inv

    async def _write_audit(self, entity_type: str, entity_id: str, action: str,
                           user: Any, reason: str, before: Any, after: Any,
                           extra: Optional[Dict[str, Any]] = None) -> None:
        rec = {
            "id": f"god_{entity_type}_{entity_id}_{int(datetime.now(timezone.utc).timestamp()*1000)}",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "reason": reason,
            "before_value": before,
            "after_value": after,
            "performed_by": getattr(user, "id", None),
            "performed_by_name": getattr(user, "full_name", None),
            "performed_by_email": getattr(user, "email", None),
            "performed_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            rec.update(extra)
        await self.db.superadmin_god_mode_audit.insert_one(rec)

    # -------------------------------------------------------------------------
    # 1. Correct invoice NUMBER
    # -------------------------------------------------------------------------
    async def correct_invoice_number(
        self, invoice_id: str, new_number: str, reason: str, user: Any,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        if not new_number or not str(new_number).strip():
            raise FinancialSafetyError("MISSING_NEW_NUMBER", "new invoice_number is required.", 400)
        if not reason or len(reason.strip()) < 5:
            raise FinancialSafetyError("MISSING_REASON", "Reason is required (min 5 chars).", 400)

        inv = await self._load_invoice(invoice_id)
        new_number = new_number.strip()
        old_number = inv.get("invoice_number")
        if new_number == old_number:
            return {"message": "No change — invoice number is already the requested value.",
                    "invoice_id": invoice_id, "invoice_number": new_number}

        # Uniqueness check
        clash = await self.db.invoices.find_one(
            {"invoice_number": new_number, "id": {"$ne": invoice_id}},
            {"_id": 0, "id": 1, "status": 1},
        )
        if clash:
            raise FinancialSafetyError(
                "DUPLICATE_INVOICE_NUMBER",
                f"Invoice number {new_number!r} is already used by invoice {clash.get('id')}.",
                409,
            )

        # Section 11: locked/terminal invoices need explicit confirm=True.
        status = (inv.get("status") or "").lower()
        if status in {"issued", "partially_paid", "paid", "voided", "cancelled",
                      "converted", "deleted"} and not confirm:
            return {
                "message": "PREVIEW ONLY — pass confirm=true to execute.",
                "invoice_id": invoice_id,
                "current_invoice_number": old_number,
                "proposed_invoice_number": new_number,
                "invoice_status": status,
            }

        now = datetime.now(timezone.utc).isoformat()
        await self.db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {
                "invoice_number": new_number,
                "number_corrected_by": getattr(user, "id", None),
                "number_corrected_at": now,
                "number_correction_reason": reason,
                "updated_at": now,
            }}
        )
        # Denormalized copies on children (best-effort, does NOT touch amounts).
        await self.db.payments.update_many(
            {"invoice_id": invoice_id},
            {"$set": {"invoice_number": new_number}},
        )
        await self.db.credit_notes.update_many(
            {"invoice_id": invoice_id},
            {"$set": {"invoice_number": new_number}},
        )
        await self._write_audit(
            "invoice", invoice_id, "number_corrected", user, reason,
            before={"invoice_number": old_number},
            after={"invoice_number": new_number},
        )
        return {
            "message": "Invoice number corrected. UUID, payments, credit notes, and journals preserved.",
            "invoice_id": invoice_id,
            "before_invoice_number": old_number,
            "after_invoice_number": new_number,
        }

    # -------------------------------------------------------------------------
    # 2. Impact preview for VALUE correction (Section 25)
    # -------------------------------------------------------------------------
    async def preview_value_correction(
        self, invoice_id: str, new_total_amount: float,
    ) -> Dict[str, Any]:
        inv = await self._load_invoice(invoice_id)
        new_total = validate_money(new_total_amount, field="new total_amount")

        # BEFORE snapshot via Phase 2 SoT.
        before = await self.sot.get_invoice_snapshot(invoice_id)

        # AFTER simulation: reuse SoT rules without writing. We reload the
        # invoice with a proposed override, then compute using the internal
        # helper (which does not mutate the DB doc — it just reads it).
        simulated_inv = {**inv, "total_amount": new_total}
        payments = await self.db.payments.find(
            {"invoice_id": invoice_id}, {"_id": 0},
        ).to_list(500)
        cns = await self.db.credit_notes.find(
            {"invoice_id": invoice_id}, {"_id": 0},
        ).to_list(500)
        after = self.sot._compute_invoice_snapshot(simulated_inv, payments, cns)

        return {
            "invoice_id": invoice_id,
            "before": {
                "document_face_value": before["document_face_value"],
                "credit_note_total": before["credit_note_total"],
                "net_invoiced_value": before["net_invoiced_value"],
                "paid_amount": before["paid_amount"],
                "outstanding_amount": before["outstanding_amount"],
                "payment_status": before["payment_status"],
            } if before else None,
            "after": {
                "document_face_value": after["document_face_value"],
                "credit_note_total": after["credit_note_total"],
                "net_invoiced_value": after["net_invoiced_value"],
                "paid_amount": after["paid_amount"],
                "outstanding_amount": after["outstanding_amount"],
                "payment_status": after["payment_status"],
                "integrity_warnings": [w.get("code") for w in after.get("integrity_warnings", [])],
            },
            "affected_payments": len(payments),
            "affected_credit_notes": len(cns),
        }

    # -------------------------------------------------------------------------
    # 3. Execute VALUE correction
    # -------------------------------------------------------------------------
    async def correct_invoice_value(
        self, invoice_id: str, new_total_amount: float, reason: str,
        correction_type: str, user: Any, confirm: bool = False,
        new_subtotal: Optional[float] = None,
        new_tax_amount: Optional[float] = None,
        corrected_line_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if correction_type not in CORRECTION_TYPES:
            raise FinancialSafetyError(
                "INVALID_CORRECTION_TYPE",
                f"correction_type must be one of {CORRECTION_TYPES}.", 400,
            )
        if not reason or len(reason.strip()) < 5:
            raise FinancialSafetyError("MISSING_REASON", "Reason is required (min 5 chars).", 400)
        new_total = validate_money(new_total_amount, field="new total_amount")

        inv = await self._load_invoice(invoice_id)
        old_total = float(inv.get("total_amount") or 0)
        if abs(new_total - old_total) < 0.001:
            return {"message": "No change — invoice value is already the requested amount.",
                    "invoice_id": invoice_id, "total_amount": new_total}

        # ---- Section 9: LINE-ITEM CONSISTENCY --------------------------------
        # Determine subtotal / tax / lines that keep the invoice internally
        # consistent. If the caller supplied an explicit breakdown, validate
        # it; otherwise ONLY auto-recalc when the invoice has zero or one
        # monetary line (simple case).
        existing_lines = inv.get("line_items") or inv.get("invoice_lines") or []

        if corrected_line_items is not None or new_subtotal is not None or new_tax_amount is not None:
            if new_subtotal is None or new_tax_amount is None or corrected_line_items is None:
                raise FinancialSafetyError(
                    "INCOMPLETE_LINE_ITEM_BREAKDOWN",
                    ("When supplying a corrected breakdown you must provide "
                     "new_subtotal, new_tax_amount, and corrected_line_items."),
                    400,
                )
            new_subtotal_v = validate_money(new_subtotal, field="new_subtotal")
            new_tax_v = validate_money(new_tax_amount, field="new_tax_amount")
            line_sum = round(sum(float(li.get("amount") or 0) for li in corrected_line_items), 2)
            if abs(line_sum - new_subtotal_v) > 0.01:
                raise FinancialSafetyError(
                    "LINE_ITEMS_SUBTOTAL_MISMATCH",
                    f"sum(line amounts) {line_sum} != subtotal {new_subtotal_v}.",
                    400,
                )
            if abs((new_subtotal_v + new_tax_v) - new_total) > 0.01:
                raise FinancialSafetyError(
                    "SUBTOTAL_TAX_TOTAL_MISMATCH",
                    f"subtotal + tax {new_subtotal_v + new_tax_v} != total {new_total}.",
                    400,
                )
            subtotal, tax_amount, new_lines = new_subtotal_v, new_tax_v, corrected_line_items
        else:
            # Auto-recalc allowed only when 0 or 1 existing line.
            if len(existing_lines) > 1:
                raise FinancialSafetyError(
                    "AMBIGUOUS_LINE_ITEM_DISTRIBUTION",
                    ("Invoice has multiple line items; supply "
                     "corrected_line_items + new_subtotal + new_tax_amount to "
                     "correct value safely."),
                    400,
                )
            tax_rate = float(inv.get("tax_rate") or 0)
            subtotal = round(new_total / (1 + tax_rate / 100), 2) if tax_rate else round(new_total, 2)
            tax_amount = round(new_total - subtotal, 2)
            if existing_lines:
                new_lines = [{**existing_lines[0], "amount": subtotal}]
            else:
                new_lines = existing_lines

        # Preview computed for the audit record + response.
        preview = await self.preview_value_correction(invoice_id, new_total)
        if not confirm:
            return {"message": "PREVIEW ONLY — pass confirm=true to execute.",
                    "computed_subtotal": subtotal, "computed_tax_amount": tax_amount,
                    **preview}

        now = datetime.now(timezone.utc).isoformat()
        # ---- Section 10 (FINAL): atomic accounting correction ----------
        # If the correction touches accounting (issued/partially_paid/paid),
        # void the old journals, post the corrected journal, and ONLY THEN
        # apply the amount change to the invoice. If accounting fails at any
        # point, restore the previous state and return a controlled
        # INVOICE_VALUE_CORRECTION_ACCOUNTING_FAILED.
        cur_status_l = (inv.get("status") or "").lower()
        accounting_effect: Dict[str, Any] = {"applied": False}
        voided_journal_snapshot: List[Dict[str, Any]] = []
        if cur_status_l in {"issued", "partially_paid", "paid"}:
            old_journals = await self.db.journal_entries.find(
                {"source_id": invoice_id, "source_module": "invoice",
                 "status": {"$ne": "voided"}},
                {"_id": 0},
            ).to_list(20)
            voided_journal_snapshot = list(old_journals)
            voided_ids: List[str] = []
            for je in old_journals:
                await self.db.journal_entries.update_one(
                    {"id": je["id"], "status": {"$ne": "voided"}},
                    {"$set": {
                        "status": "voided",
                        "voided_by": getattr(user, "id", None),
                        "voided_at": now,
                        "void_reason": f"Invoice value correction: {reason}",
                        "updated_at": now,
                    }},
                )
                voided_ids.append(je["id"])
            # Try posting corrected issuance journal.
            new_journal_ids: List[str] = []
            repost_error: Optional[str] = None
            try:
                from routes.accounting import post_invoice_issued  # type: ignore
                corrected_inv = {**inv, "total_amount": new_total,
                                 "subtotal": subtotal, "tax_amount": tax_amount,
                                 "line_items": new_lines}
                repost = await post_invoice_issued(
                    invoice=corrected_inv,
                    user_id=getattr(user, "id", None),
                    user_name=getattr(user, "full_name", None),
                )
                if isinstance(repost, dict):
                    if repost.get("error"):
                        repost_error = repost.get("error")
                    elif not repost.get("journal_entry"):
                        repost_error = "ACCOUNTING_RETURNED_NO_JOURNAL"
                    else:
                        # Section G CLOSEOUT: only tag as new when NOT a
                        # duplicate. is_duplicate means the existing journal
                        # is pre-existing history, not our creation.
                        if not repost.get("is_duplicate"):
                            je = repost["journal_entry"]
                            j_id = je.get("id") if isinstance(je, dict) else None
                            if j_id:
                                new_journal_ids.append(j_id)
            except ImportError:
                if voided_journal_snapshot:
                    repost_error = "ACCOUNTING_LAYER_UNAVAILABLE"
            except Exception as e:
                repost_error = str(e)

            if repost_error:
                # ROLL BACK — re-activate the old journals and DO NOT save
                # the new total on the invoice.
                for je in voided_journal_snapshot:
                    await self.db.journal_entries.update_one(
                        {"id": je["id"]},
                        {"$set": {"status": je.get("status", "posted"),
                                  "updated_at": now},
                         "$unset": {"voided_by": "", "voided_at": "",
                                    "void_reason": ""}},
                    )
                await self._write_audit(
                    "invoice", invoice_id, "value_correction_rolled_back",
                    user, reason,
                    before={"total_amount": old_total, "status": inv.get("status")},
                    after={"error": repost_error},
                    extra={"restored_journal_ids": voided_ids},
                )
                raise FinancialSafetyError(
                    "INVOICE_VALUE_CORRECTION_ACCOUNTING_FAILED",
                    ("Invoice value correction accounting failed; invoice "
                     "amount and journals have been restored. Error: "
                     + repost_error),
                    500,
                )
            accounting_effect = {
                "applied": True,
                "voided_journal_ids": voided_ids,
                "new_journal_ids": new_journal_ids,
            }
        await self.db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {
                "total_amount": new_total,
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "line_items": new_lines,
                "value_corrected_by": getattr(user, "id", None),
                "value_corrected_at": now,
                "value_correction_reason": reason,
                "value_correction_type": correction_type,
                "value_correction_before": old_total,
                "updated_at": now,
            }}
        )
        # Section C: verify the invoice update actually landed. If not,
        # roll back the accounting effects created by THIS operation and
        # return recovery-required — do NOT report success.
        _post_update_inv = await self.db.invoices.find_one(
            {"id": invoice_id}, {"_id": 0, "total_amount": 1},
        )
        if not _post_update_inv or abs(float(_post_update_inv.get("total_amount") or 0) - new_total) > 0.01:
            # Void the new journals we just created (this operation only).
            for jid in accounting_effect.get("new_journal_ids", []) or []:
                await self.db.journal_entries.update_one(
                    {"id": jid},
                    {"$set": {"status": "voided", "voided_at": now,
                              "void_reason": "Invoice update did not persist"}},
                )
            # Re-activate the old journals we voided.
            for je in voided_journal_snapshot or []:
                await self.db.journal_entries.update_one(
                    {"id": je["id"]},
                    {"$set": {"status": je.get("status", "posted"),
                              "updated_at": now},
                     "$unset": {"voided_by": "", "voided_at": "",
                                "void_reason": ""}},
                )
            raise FinancialSafetyError(
                "INVOICE_VALUE_CORRECTION_RECOVERY_REQUIRED",
                ("Invoice value update did not persist; new journals voided "
                 "and prior journals restored. Retry after investigation."),
                500,
            )
        # Recompute canonical status from fresh snapshot.
        # Phase 3A Section V: TERMINAL statuses (voided/cancelled/deleted/
        # converted) MUST NOT be silently resurrected by a value correction.
        snap = await self.sot.get_invoice_snapshot(invoice_id)
        new_status_candidate = None
        cur_status = (inv.get("status") or "").lower()
        TERMINAL = {"voided", "cancelled", "deleted", "converted"}
        if cur_status in TERMINAL:
            # Preserve terminal status. Reason recorded in audit; if the
            # SuperAdmin genuinely needs to revive the invoice, they must
            # use a dedicated Repair Status workflow.
            new_status_candidate = cur_status
        elif snap and cur_status in ("issued", "partially_paid", "paid"):
            outstanding = float(snap["outstanding_amount"])
            paid = float(snap["paid_amount"])
            net = float(snap["net_invoiced_value"])
            if outstanding <= 0.005 and paid > 0:
                new_status_candidate = "paid"
            elif 0 < paid < net:
                new_status_candidate = "partially_paid"
            elif paid == 0:
                new_status_candidate = "issued"
        if new_status_candidate and new_status_candidate != inv.get("status"):
            await self.db.invoices.update_one(
                {"id": invoice_id},
                {"$set": {"status": new_status_candidate, "updated_at": now}}
            )

        await self._write_audit(
            "invoice", invoice_id, "value_corrected", user, reason,
            before={"total_amount": old_total, "status": inv.get("status")},
            after={"total_amount": new_total, "status": new_status_candidate or inv.get("status")},
            extra={"correction_type": correction_type, "preview": preview,
                   "accounting_effect": accounting_effect},
        )
        return {
            "message": "Invoice value corrected.",
            "invoice_id": invoice_id,
            "before_total_amount": old_total,
            "after_total_amount": new_total,
            "correction_type": correction_type,
            "status_after": new_status_candidate or inv.get("status"),
            "accounting_effect": accounting_effect,
            "preview": preview,
        }

    # -------------------------------------------------------------------------
    # 4. Correct DATE
    # -------------------------------------------------------------------------
    async def correct_invoice_date(
        self, invoice_id: str, new_invoice_date: str, reason: str, user: Any,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        if not new_invoice_date:
            raise FinancialSafetyError("MISSING_NEW_DATE", "new_invoice_date is required.", 400)
        if not reason or len(reason.strip()) < 5:
            raise FinancialSafetyError("MISSING_REASON", "Reason is required (min 5 chars).", 400)
        # ---- Section 12: strict ISO YYYY-MM-DD calendar validation --------
        import re as _re
        if not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", new_invoice_date.strip()):
            raise FinancialSafetyError(
                "INVALID_DATE_FORMAT",
                "new_invoice_date must be an ISO calendar date YYYY-MM-DD.",
                400,
            )
        try:
            datetime.strptime(new_invoice_date.strip(), "%Y-%m-%d")
        except ValueError:
            raise FinancialSafetyError(
                "INVALID_DATE_CALENDAR",
                f"new_invoice_date {new_invoice_date!r} is not a valid calendar date.",
                400,
            )

        inv = await self._load_invoice(invoice_id)
        old_date = inv.get("invoice_date")
        status = (inv.get("status") or "").lower()
        if status in {"issued", "partially_paid", "paid", "voided", "cancelled",
                      "converted", "deleted"} and not confirm:
            return {
                "message": "PREVIEW ONLY — pass confirm=true to execute.",
                "invoice_id": invoice_id,
                "current_invoice_date": old_date,
                "proposed_invoice_date": new_invoice_date.strip(),
                "invoice_status": status,
            }
        now = datetime.now(timezone.utc).isoformat()
        await self.db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {
                "invoice_date": new_invoice_date,
                "date_corrected_by": getattr(user, "id", None),
                "date_corrected_at": now,
                "date_correction_reason": reason,
                "updated_at": now,
                # NOTE: created_at is deliberately NOT touched.
            }}
        )
        await self._write_audit(
            "invoice", invoice_id, "date_corrected", user, reason,
            before={"invoice_date": old_date},
            after={"invoice_date": new_invoice_date},
        )
        return {"invoice_id": invoice_id, "before_invoice_date": old_date,
                "after_invoice_date": new_invoice_date}

    # -------------------------------------------------------------------------
    # 5. Correct TEXT / bill-to
    # -------------------------------------------------------------------------
    async def correct_invoice_text(
        self, invoice_id: str, updates: Dict[str, Any], reason: str, user: Any,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        if not reason or len(reason.strip()) < 5:
            raise FinancialSafetyError("MISSING_REASON", "Reason is required (min 5 chars).", 400)
        # Text-only fields — money is REJECTED here.
        allowed = {"company_name", "bill_to_name", "bill_to_address", "bill_to_email",
                   "programme_name", "session_name", "description", "po_number",
                   "line_items_text_note"}
        clean = {k: v for k, v in (updates or {}).items() if k in allowed}
        rejected = [k for k in (updates or {}) if k not in allowed]
        if rejected:
            raise FinancialSafetyError(
                "MONEY_FIELDS_NOT_ALLOWED",
                f"Use /correct-value for monetary fields. Rejected: {rejected}.", 400,
            )
        if not clean:
            raise FinancialSafetyError("NOTHING_TO_UPDATE", "No text fields provided.", 400)

        inv = await self._load_invoice(invoice_id)
        status = (inv.get("status") or "").lower()
        if status in {"issued", "partially_paid", "paid", "voided", "cancelled",
                      "converted", "deleted"} and not confirm:
            return {
                "message": "PREVIEW ONLY — pass confirm=true to execute.",
                "invoice_id": invoice_id,
                "current": {k: inv.get(k) for k in clean},
                "proposed": clean,
                "invoice_status": status,
            }
        before = {k: inv.get(k) for k in clean}
        now = datetime.now(timezone.utc).isoformat()
        clean["text_corrected_by"] = getattr(user, "id", None)
        clean["text_corrected_at"] = now
        clean["text_correction_reason"] = reason
        clean["updated_at"] = now
        await self.db.invoices.update_one({"id": invoice_id}, {"$set": clean})
        await self._write_audit(
            "invoice", invoice_id, "text_corrected", user, reason,
            before=before, after={k: v for k, v in clean.items() if k in allowed},
        )
        return {"invoice_id": invoice_id, "before": before, "after": clean}

    # -------------------------------------------------------------------------
    # 6. Correct ISSUED Credit Note
    # -------------------------------------------------------------------------
    async def correct_issued_credit_note(
        self, cn_id: str, updates: Dict[str, Any], reason: str, user: Any,
        confirm: bool = False,
    ) -> Dict[str, Any]:
        if not reason or len(reason.strip()) < 5:
            raise FinancialSafetyError("MISSING_REASON", "Reason is required (min 5 chars).", 400)
        cn = await self.db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
        if not cn:
            raise FinancialSafetyError("CN_NOT_FOUND", f"Credit Note {cn_id} not found.", 404)
        if (cn.get("status") or "").lower() != "issued":
            raise FinancialSafetyError(
                "CN_NOT_ISSUED",
                "This correction endpoint only applies to ISSUED credit notes. "
                "Draft/approved CNs use the normal edit path.", 400,
            )
        allowed = {"cn_number", "cn_date", "amount", "reason", "description"}
        clean = {k: v for k, v in (updates or {}).items() if k in allowed}
        if not clean:
            raise FinancialSafetyError("NOTHING_TO_UPDATE", "No allowed fields provided.", 400)
        if "amount" in clean:
            clean["amount"] = validate_money(clean["amount"], field="new amount")

        # Impact preview: recompute the invoice snapshot with new CN amount.
        preview = None
        if cn.get("invoice_id"):
            payments = await self.db.payments.find(
                {"invoice_id": cn["invoice_id"]}, {"_id": 0},
            ).to_list(500)
            cns = await self.db.credit_notes.find(
                {"invoice_id": cn["invoice_id"]}, {"_id": 0},
            ).to_list(500)
            simulated_cns = [{**c, **clean} if c["id"] == cn_id else c for c in cns]
            inv = await self.db.invoices.find_one({"id": cn["invoice_id"]}, {"_id": 0})
            if inv:
                after_snap = self.sot._compute_invoice_snapshot(inv, payments, simulated_cns)
                before_snap = await self.sot.get_invoice_snapshot(cn["invoice_id"])
                preview = {
                    "before_net_invoiced_value": before_snap["net_invoiced_value"] if before_snap else None,
                    "after_net_invoiced_value": after_snap["net_invoiced_value"],
                    "before_outstanding_amount": before_snap["outstanding_amount"] if before_snap else None,
                    "after_outstanding_amount": after_snap["outstanding_amount"],
                }

        if not confirm:
            return {"message": "PREVIEW ONLY — pass confirm=true to execute.",
                    "cn_id": cn_id, "updates": clean, "preview": preview}

        before = {k: cn.get(k) for k in clean}
        now = datetime.now(timezone.utc).isoformat()
        clean["issued_cn_corrected_by"] = getattr(user, "id", None)
        clean["issued_cn_corrected_at"] = now
        clean["issued_cn_correction_reason"] = reason
        clean["updated_at"] = now
        await self.db.credit_notes.update_one({"id": cn_id}, {"$set": clean})

        # If amount changed, reconcile linked journal entries by voiding and
        # re-posting via existing post_credit_note_issued. Section 8:
        # this operation is ATOMIC — if the repost fails, restore the CN
        # amount + re-activate the previous journals so the final state is
        # economically identical to BEFORE.
        if "amount" in clean and clean.get("amount") != before.get("amount"):
            # Snapshot active journals before any mutation for compensation.
            active_journals = await self.db.journal_entries.find(
                {"source_id": cn_id, "source_module": "credit_note",
                 "status": {"$ne": "voided"}},
                {"_id": 0},
            ).to_list(20)
            active_journal_ids = [je["id"] for je in active_journals]
            # Mark old journals as voided (idempotent).
            await self.db.journal_entries.update_many(
                {"source_id": cn_id, "source_module": "credit_note",
                 "status": {"$ne": "voided"}},
                {"$set": {
                    "status": "voided",
                    "voided_by": getattr(user, "id", None),
                    "voided_at": now,
                    "void_reason": f"CN amount corrected: {reason}",
                    "updated_at": now,
                }},
            )
            # Phase 3A FINAL Section 5: BOTH raised exceptions AND returned
            # {"error": ...} accounting failures are treated as HARD failures.
            # If accounting is truly not available (ImportError), we still
            # roll back the CN amount change because the accounting effect
            # cannot be verified consistent.
            new_journal_id: Optional[str] = None
            repost_error: Optional[str] = None
            hard_failure = False
            try:
                from routes.accounting import post_credit_note_issued  # type: ignore
                new_cn = await self.db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
                repost = await post_credit_note_issued(
                    credit_note=new_cn,
                    user_id=getattr(user, "id", None),
                    user_name=getattr(user, "full_name", None),
                )
                # Section G CLOSEOUT: use `journal_entry`, not `journal_id`.
                # `is_duplicate=True` means the existing journal is NOT ours;
                # do NOT track/void it as compensation.
                if isinstance(repost, dict):
                    if repost.get("error"):
                        repost_error = repost.get("error")
                        hard_failure = True
                    elif not repost.get("journal_entry"):
                        repost_error = "ACCOUNTING_RETURNED_NO_JOURNAL"
                        hard_failure = True
                    else:
                        if not repost.get("is_duplicate"):
                            je = repost["journal_entry"]
                            new_journal_id = je.get("id") if isinstance(je, dict) else None
            except ImportError:
                if active_journal_ids:
                    repost_error = "ACCOUNTING_LAYER_UNAVAILABLE"
                    hard_failure = True
            except Exception as e:
                repost_error = str(e)
                hard_failure = True

            if hard_failure:
                # COMPENSATE: void the new journal if one was created, and
                # re-activate the old journals; restore the CN doc.
                if new_journal_id:
                    await self.db.journal_entries.update_one(
                        {"id": new_journal_id},
                        {"$set": {"status": "voided", "voided_at": now,
                                  "void_reason": f"CN correction failed: {repost_error}"}},
                    )
                await self.db.credit_notes.update_one(
                    {"id": cn_id},
                    {"$set": {**{k: cn.get(k) for k in clean.keys()},
                              "updated_at": now}}
                )
                for jid in active_journal_ids:
                    await self.db.journal_entries.update_one(
                        {"id": jid},
                        {"$set": {"status": "posted", "updated_at": now},
                         "$unset": {"voided_by": "", "voided_at": "",
                                    "void_reason": ""}},
                    )
                await self._write_audit(
                    "credit_note", cn_id, "issued_cn_correction_rolled_back",
                    user, reason,
                    before=before, after={"error": repost_error},
                    extra={"restored_journal_ids": active_journal_ids},
                )
                raise FinancialSafetyError(
                    "CN_CORRECTION_ACCOUNTING_FAILED",
                    ("Journal repost failed; original CN amount and journals "
                     "have been restored. Error: " + repost_error),
                    500,
                )
            # Success — keep the new journal id for audit.
            _repost_new_journal_id = new_journal_id

        await self._write_audit(
            "credit_note", cn_id, "issued_cn_corrected", user, reason,
            before=before, after=clean, extra={"preview": preview},
        )
        return {"cn_id": cn_id, "before": before, "after": clean, "preview": preview}


# =============================================================================
# High-impact-field guard for the generic superadmin update endpoint.
# =============================================================================
def high_impact_touched(invoice: Dict[str, Any], updates: Dict[str, Any]) -> List[str]:
    """Return the list of HIGH_IMPACT_INVOICE_FIELDS present in ``updates``
    that would materially change the LOCKED invoice, so callers can reject
    them and redirect SuperAdmin to the controlled endpoints."""
    status = (invoice.get("status") or "").lower()
    if status not in EXCLUDED_INVOICE_STATUSES and status not in {"issued", "partially_paid", "paid"}:
        return []
    return sorted(set(updates.keys()) & HIGH_IMPACT_INVOICE_FIELDS)
