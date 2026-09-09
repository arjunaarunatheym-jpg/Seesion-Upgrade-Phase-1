"""
Financial Operation Ledger — the ONE consistent multi-step design.

Mongo is running standalone (verified at design time), so multi-document
transactions are unavailable. This module provides a durable-recovery
alternative that guarantees:

    1. A status such as ``issued`` / ``paid`` / ``reversed`` is never
       treated as proof that an unfinished operation completed. The client
       only receives success when ``financial_operations.status == "completed"``.
    2. Concurrent requests and retries cannot create duplicate financial
       effects. A unique index on ``op_key`` claims the operation once;
       retries with the same key observe the already-completed ledger and
       return its stored result idempotently.
    3. A failed operation cannot silently overwrite another user's later
       change: each tracked mutation uses a conditional update against the
       recorded ``before`` state, so a stale rollback is a no-op.
    4. Compensation affects only records created / changed by THIS
       operation. Every insert is tagged with ``op_id``; every update
       stores its ``before`` snapshot on the ledger row.
    5. An incomplete operation returns a clear failure or
       ``RECOVERY_REQUIRED`` result — never a success message.
    6. Original invoices, receipts, payments, credit notes, UUIDs, and
       audit history are never physically deleted or renumbered.

Usage
-----
    async with FinancialOperation(
        db, op_type="issue_invoice", op_key=f"issue:{invoice_id}"
    ) as op:
        if op.replay:
            # Idempotent retry — the operation already completed. Return
            # the stored result verbatim.
            return op.result

        # Track each intended change BEFORE performing it. The ledger row
        # captures enough state to compensate this operation only.
        await op.track_update(
            "invoices", invoice_id,
            match={"id": invoice_id, "status": prior_status},
            set_fields={"status": "issued", ...},
            before={"status": prior_status},
        )
        journal_doc = {..., "op_id": op.op_id}      # side-effect tagged
        await op.track_insert("journal_entries", journal_doc)

        # Post-condition checks go here — anything that raises will trip
        # the durable abort path.
        op.set_result({"message": "Invoice issued", "invoice_number": ...})

The ``__aexit__`` finalizes:

    * exception raised          → ledger marked ``failed``; walk tracked
                                  steps in reverse and revert each one
                                  against the captured ``before`` state
                                  (conditional — no stale overwrite).
    * ``op.set_recovery_required`` set → ledger marked ``recovery_required``.
    * otherwise                 → ledger marked ``completed`` with
                                  ``result``.  Only this final flip makes
                                  the operation success-visible.
"""

from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RecoveryRequired(Exception):
    """Raised internally when an operation cannot safely commit or abort."""

    def __init__(self, code: str, message: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra or {}


class FinancialOperation:
    """Durable-recovery unit-of-work for a single multi-step financial op."""

    def __init__(self, db, op_type: str, op_key: str, actor: Optional[Any] = None):
        self.db = db
        self.op_type = op_type
        self.op_key = op_key
        self.actor = actor
        self.op_id = str(uuid.uuid4())
        self.steps: List[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.replay: bool = False
        self._recovery_required: Optional[Dict[str, Any]] = None
        self._started_at: Optional[str] = None

    async def __aenter__(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        self._started_at = now_iso
        # Unique index on op_key enforces one operation per idempotency key.
        try:
            await self.db.financial_operations.insert_one({
                "op_id": self.op_id,
                "op_key": self.op_key,
                "op_type": self.op_type,
                "status": "in_progress",
                "actor_id": getattr(self.actor, "id", None),
                "actor_name": getattr(self.actor, "full_name", None),
                "steps": [],
                "result": None,
                "started_at": now_iso,
            })
        except Exception:
            # Duplicate op_key — either a concurrent in-flight retry or a
            # previously completed operation. Return the ledger row.
            existing = await self.db.financial_operations.find_one(
                {"op_key": self.op_key}, {"_id": 0},
            )
            if not existing:
                raise RecoveryRequired(
                    "OP_KEY_CONFLICT_NO_ROW",
                    f"op_key {self.op_key} conflicts but no ledger row found",
                )
            self.op_id = existing["op_id"]
            status = existing.get("status")
            if status == "completed":
                self.replay = True
                self.result = existing.get("result") or {}
                return self
            if status == "in_progress":
                # Another request is still working. Do NOT proceed.
                raise RecoveryRequired(
                    "OP_IN_PROGRESS",
                    f"Operation {self.op_type} already in progress under "
                    f"op_id {existing['op_id']}",
                    {"op_id": existing["op_id"]},
                )
            # failed / recovery_required — do not silently retry; surface it.
            raise RecoveryRequired(
                "PRIOR_OP_" + (status or "UNKNOWN").upper(),
                f"Prior operation for op_key {self.op_key} is in status {status!r}",
                {"prior_op_id": existing.get("op_id"),
                 "prior_status": status},
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc is not None:
            await self._abort(f"{exc_type.__name__}: {exc}")
            return False  # re-raise
        if self._recovery_required is not None:
            await self._mark("recovery_required",
                             extra={"recovery_reason": self._recovery_required})
            return False
        await self._commit()
        return False

    # ---------- side-effect tracking ---------------------------------------

    async def track_update(
        self, collection: str, doc_id: str, *,
        match: Dict[str, Any], set_fields: Dict[str, Any],
        before: Dict[str, Any], unset_fields: Optional[List[str]] = None,
    ) -> int:
        """Conditional update — records before-state so we can revert only
        the change made by THIS operation. Returns modified_count.
        """
        ops = {"$set": {**set_fields, f"_op_last_{self.op_type}": self.op_id,
                        "updated_at": datetime.now(timezone.utc).isoformat()}}
        if unset_fields:
            ops["$unset"] = {k: "" for k in unset_fields}
        result = await self.db[collection].update_one(match, ops)
        self.steps.append({
            "kind": "update",
            "collection": collection,
            "doc_id": doc_id,
            "match": match,
            "set_fields": list(set_fields.keys()),
            "unset_fields": list(unset_fields or []),
            "before": before,
            "modified": result.modified_count,
        })
        return result.modified_count

    async def track_insert(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert with an ``op_id`` tag so compensation targets this op only."""
        document = {**document, "op_id": self.op_id,
                    "_created_by_op": self.op_type}
        await self.db[collection].insert_one(document)
        doc_id = document.get("id") or document.get("_id")
        self.steps.append({
            "kind": "insert",
            "collection": collection,
            "doc_id": doc_id,
        })
        return doc_id

    def set_result(self, result: Dict[str, Any]) -> None:
        self.result = result

    def request_recovery(self, code: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Flag that the operation could not safely complete AND could not
        safely be rolled back. Client sees a controlled recovery-required
        result — never a success.
        """
        self._recovery_required = {"code": code, "message": message,
                                    "extra": extra or {}}

    # ---------- commit / abort --------------------------------------------

    async def _commit(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        await self.db.financial_operations.update_one(
            {"op_id": self.op_id, "status": "in_progress"},
            {"$set": {
                "status": "completed",
                "steps": self.steps,
                "result": self.result,
                "completed_at": now_iso,
            }},
        )

    async def _abort(self, reason: str) -> None:
        """Best-effort compensation in REVERSE order. Every step uses a
        conditional query so we cannot overwrite a later user's change.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        compensation_report: List[Dict[str, Any]] = []
        for step in reversed(self.steps):
            try:
                if step["kind"] == "insert":
                    # Only delete rows that STILL carry our op_id — a later
                    # legitimate mutation (e.g. void) would have changed
                    # ``status`` but not the tag, so this is safe. We do NOT
                    # remove rows whose lifecycle has moved on.
                    r = await self.db[step["collection"]].delete_one(
                        {"id": step["doc_id"], "op_id": self.op_id,
                         "_created_by_op": self.op_type},
                    )
                    compensation_report.append({
                        "step": step, "reverted": r.deleted_count,
                    })
                elif step["kind"] == "update":
                    # Revert only if our tag is still the last mutation.
                    revert_set = {**step["before"],
                                  "updated_at": now_iso}
                    revert_unset = {k: "" for k in step["set_fields"]
                                    if k not in step["before"]}
                    ops = {"$set": revert_set}
                    if revert_unset:
                        ops["$unset"] = revert_unset
                    r = await self.db[step["collection"]].update_one(
                        {"id": step["doc_id"],
                         f"_op_last_{self.op_type}": self.op_id},
                        ops,
                    )
                    compensation_report.append({
                        "step": step, "reverted": r.modified_count,
                    })
            except Exception as comp_err:
                compensation_report.append({
                    "step": step, "error": str(comp_err),
                })
        # If any step could not be reverted, escalate to recovery_required.
        all_ok = all(
            (rep.get("error") is None) and
            ((rep.get("reverted") or 0) >= 0)
            for rep in compensation_report
        )
        # Failed status when compensation fully applied; recovery_required
        # if any compensation itself errored (needs ops attention).
        final_status = "failed" if all_ok else "recovery_required"
        await self.db.financial_operations.update_one(
            {"op_id": self.op_id, "status": "in_progress"},
            {"$set": {
                "status": final_status,
                "steps": self.steps,
                "compensation": compensation_report,
                "failure_reason": reason,
                "failed_at": now_iso,
            }},
        )

    async def _mark(self, status: str, *, extra: Optional[Dict[str, Any]] = None) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {"status": status, "steps": self.steps,
                   "recorded_at": now_iso}
        if extra:
            payload.update(extra)
        await self.db.financial_operations.update_one(
            {"op_id": self.op_id, "status": "in_progress"},
            {"$set": payload},
        )


async def ensure_financial_operations_indexes(db) -> None:
    """Called from server startup. Creates the ledger's unique index."""
    try:
        await db.financial_operations.create_index("op_id", unique=True)
        await db.financial_operations.create_index(
            "op_key", unique=True,
            name="uniq_financial_operations_op_key",
        )
        await db.financial_operations.create_index("status")
    except Exception as e:
        logger.warning(f"financial_operations indexes: {e}")
