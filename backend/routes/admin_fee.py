"""
Administration Fee management.

A configurable percentage fee (default 4%) auto-applied to sessions with start_date >= effective_from.
The fee is:
- Recorded as a session_expense (category="Administration Fee", auto_generated=true)
- Recorded as a marketing_commissions entry (type="admin_fee") payable to the configured recipient

Endpoints:
- GET    /api/admin-fee/config
- PUT    /api/admin-fee/config              (admin only)
- GET    /api/admin-fee/recipients          (list marketing-eligible users)
- POST   /api/admin-fee/sessions/{id}/recompute  (force recompute for one session)
- POST   /api/admin-fee/sessions/{id}/override   (per-session override)
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
import uuid

from core import db, get_current_user, get_malaysia_time
from models import User

router = APIRouter(prefix="/admin-fee", tags=["admin-fee"])

DEFAULT_PERCENTAGE = 4.0
DEFAULT_EFFECTIVE_FROM = "2026-05-01"
SETTINGS_KEY = "admin_fee_config"


class AdminFeeConfig(BaseModel):
    enabled: bool = True
    percentage: float = DEFAULT_PERCENTAGE
    recipient_id: Optional[str] = None
    recipient_name: Optional[str] = None
    effective_from: str = DEFAULT_EFFECTIVE_FROM  # YYYY-MM-DD


class AdminFeeOverride(BaseModel):
    percentage: Optional[float] = None  # null clears override
    enabled: Optional[bool] = None      # null clears override; False explicitly disables for this session


async def _load_config() -> dict:
    """Load config; bootstrap with defaults pointing to Vighnesh Arunatheym if found."""
    cfg = await db.settings.find_one({"key": SETTINGS_KEY}, {"_id": 0})
    if cfg:
        return cfg
    # Bootstrap: default recipient = Vighnesh (marketing)
    vighnesh = await db.users.find_one(
        {"role": "marketing", "full_name": {"$regex": "vighnesh", "$options": "i"}},
        {"_id": 0, "id": 1, "full_name": 1},
    )
    cfg = {
        "key": SETTINGS_KEY,
        "enabled": True,
        "percentage": DEFAULT_PERCENTAGE,
        "recipient_id": vighnesh.get("id") if vighnesh else None,
        "recipient_name": vighnesh.get("full_name") if vighnesh else None,
        "effective_from": DEFAULT_EFFECTIVE_FROM,
        "created_at": get_malaysia_time().isoformat(),
    }
    await db.settings.insert_one(cfg)
    cfg.pop("_id", None)
    return cfg


@router.get("/config")
async def get_admin_fee_config(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await _load_config()
    return cfg


@router.put("/config")
async def update_admin_fee_config(body: AdminFeeConfig, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin only")

    recipient_name = body.recipient_name
    if body.recipient_id:
        rec = await db.users.find_one({"id": body.recipient_id}, {"_id": 0, "full_name": 1})
        if not rec:
            raise HTTPException(status_code=404, detail="Recipient user not found")
        recipient_name = rec.get("full_name")

    update = {
        "enabled": bool(body.enabled),
        "percentage": float(body.percentage),
        "recipient_id": body.recipient_id,
        "recipient_name": recipient_name,
        "effective_from": body.effective_from,
        "updated_at": get_malaysia_time().isoformat(),
        "updated_by": current_user.id,
    }
    await db.settings.update_one(
        {"key": SETTINGS_KEY},
        {"$set": update, "$setOnInsert": {"key": SETTINGS_KEY, "created_at": get_malaysia_time().isoformat()}},
        upsert=True,
    )
    cfg = await db.settings.find_one({"key": SETTINGS_KEY}, {"_id": 0})
    return {"message": "Administration fee configuration updated", "config": cfg}


@router.get("/recipients")
async def list_recipients(current_user: User = Depends(get_current_user)):
    """Users who can receive admin fee payouts (anyone with marketing role)."""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    users = await db.users.find(
        {"$or": [{"role": "marketing"}, {"additional_roles": "marketing"}]},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1},
    ).sort("full_name", 1).to_list(200)
    return {"recipients": users}


def _is_eligible_session(session: dict, effective_from: str) -> bool:
    """A session is eligible if its start_date (YYYY-MM-DD) >= effective_from."""
    sd = (session or {}).get("start_date") or ""
    if not sd:
        return False
    return sd >= effective_from


async def _compute_subtotal_for_admin_fee(session_id: str) -> float:
    """Subtotal = training fee + add-on items (excludes SST, excludes other expenses).
    Matches user's choice 1b (subtotal including add-ons)."""
    invoice = await db.invoices.find_one({"session_id": session_id}, {"_id": 0, "items": 1, "subtotal": 1})
    if invoice and invoice.get("subtotal"):
        return float(invoice.get("subtotal") or 0)
    # Fallback: derive from quotation linked to the session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0, "quotation_id": 1})
    if session and session.get("quotation_id"):
        quo = await db.quotations.find_one({"id": session["quotation_id"]}, {"_id": 0})
        if quo:
            training_fee = (
                float(quo.get("group_price") or 0)
                if (quo.get("pricing_type") == "per_group")
                else float(quo.get("rate_per_pax") or 0) * int(quo.get("num_participants") or 0)
            )
            addons = 0.0
            for si in (quo.get("selected_items") or []):
                if (si.get("unit_price") or 0) > 0:
                    addons += float(si.get("unit_price") or 0) * int(si.get("quantity") or 1)
            return round(training_fee + addons, 2)
    return 0.0


async def apply_admin_fee_to_session(session_id: str, current_user_id: str = "system") -> dict:
    """Idempotently create/update the auto Administration Fee expense and the marketing payable for a session.
    Returns a dict with status info; never raises."""
    try:
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            return {"applied": False, "reason": "session_not_found"}

        cfg = await _load_config()
        if not cfg.get("enabled"):
            await _remove_admin_fee_for_session(session_id)
            return {"applied": False, "reason": "feature_disabled"}

        if not _is_eligible_session(session, cfg.get("effective_from", DEFAULT_EFFECTIVE_FROM)):
            await _remove_admin_fee_for_session(session_id)
            return {"applied": False, "reason": "session_predates_cutoff"}

        # Per-session override
        override_pct = session.get("admin_fee_percentage_override")
        override_enabled = session.get("admin_fee_enabled_override")
        if override_enabled is False:
            await _remove_admin_fee_for_session(session_id)
            return {"applied": False, "reason": "overridden_off"}

        pct = float(override_pct) if (override_pct is not None) else float(cfg.get("percentage", DEFAULT_PERCENTAGE))
        recipient_id = cfg.get("recipient_id")
        recipient_name = cfg.get("recipient_name") or "Administration Fee Recipient"

        subtotal = await _compute_subtotal_for_admin_fee(session_id)
        amount = round(subtotal * pct / 100, 2)

        # --- Upsert session_expense (auto-generated) ---
        existing_exp = await db.session_expenses.find_one(
            {"session_id": session_id, "auto_generated": True, "category": "admin_fee"},
            {"_id": 0, "id": 1},
        )
        expense_doc = {
            "session_id": session_id,
            "category": "admin_fee",
            "description": f"Administration Fee ({pct}%) - {recipient_name}",
            "expense_type": "percentage",
            "percentage_rate": pct,
            "estimated_amount": amount,
            "actual_amount": amount,
            "quantity": 1,
            "unit_price": amount,
            "remark": f"Auto-generated administration fee on subtotal RM {subtotal:,.2f}",
            "status": "estimated",
            "auto_generated": True,
            "linked_recipient_id": recipient_id,
            "linked_recipient_name": recipient_name,
            "updated_at": get_malaysia_time().isoformat(),
        }
        if existing_exp:
            await db.session_expenses.update_one(
                {"id": existing_exp["id"]},
                {"$set": expense_doc},
            )
        else:
            expense_doc.update({
                "id": str(uuid.uuid4()),
                "created_at": get_malaysia_time().isoformat(),
            })
            await db.session_expenses.insert_one(expense_doc)

        # --- Upsert marketing_commissions payable (type=admin_fee) ---
        if recipient_id:
            existing_cm = await db.marketing_commissions.find_one(
                {"session_id": session_id, "type": "admin_fee"},
                {"_id": 0, "id": 1, "status": 1},
            )
            cm_doc = {
                "session_id": session_id,
                "type": "admin_fee",
                "marketing_user_id": recipient_id,
                "marketing_user_name": recipient_name,
                "commission_type": "percentage",
                "commission_rate": pct,
                "fixed_amount": 0.0,
                "calculated_amount": amount,
                "session_name": session.get("session_name") or session.get("title"),
                "company_name": session.get("company_name"),
                "session_start_date": session.get("start_date"),
                "updated_at": get_malaysia_time().isoformat(),
            }
            if existing_cm:
                # Don't downgrade a paid status back to pending
                if existing_cm.get("status") != "paid":
                    await db.marketing_commissions.update_one(
                        {"id": existing_cm["id"]},
                        {"$set": {**cm_doc, "status": "pending"}},
                    )
                else:
                    await db.marketing_commissions.update_one(
                        {"id": existing_cm["id"]},
                        {"$set": cm_doc},
                    )
            else:
                cm_doc.update({
                    "id": str(uuid.uuid4()),
                    "status": "pending",
                    "created_at": get_malaysia_time().isoformat(),
                })
                await db.marketing_commissions.insert_one(cm_doc)

        return {
            "applied": True,
            "amount": amount,
            "percentage": pct,
            "subtotal": subtotal,
            "recipient_id": recipient_id,
            "recipient_name": recipient_name,
        }
    except Exception as e:
        print(f"[admin_fee] apply_admin_fee_to_session({session_id}) failed: {e}")
        return {"applied": False, "reason": "error", "detail": str(e)}


async def _remove_admin_fee_for_session(session_id: str) -> None:
    """Used when a session becomes ineligible (cutoff change, feature disabled, per-session override off)."""
    await db.session_expenses.delete_many(
        {"session_id": session_id, "auto_generated": True, "category": "admin_fee"}
    )
    # Only delete pending commissions; paid stays for audit
    await db.marketing_commissions.delete_many(
        {"session_id": session_id, "type": "admin_fee", "status": {"$ne": "paid"}}
    )


@router.post("/sessions/{session_id}/recompute")
async def recompute_for_session(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await apply_admin_fee_to_session(session_id, current_user.id)
    return result


@router.post("/sessions/{session_id}/override")
async def override_for_session(session_id: str, body: AdminFeeOverride, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Admin/Finance only")
    update = {}
    if body.percentage is None:
        update["admin_fee_percentage_override"] = None
    else:
        update["admin_fee_percentage_override"] = float(body.percentage)
    if body.enabled is None:
        update["admin_fee_enabled_override"] = None
    else:
        update["admin_fee_enabled_override"] = bool(body.enabled)
    await db.sessions.update_one({"id": session_id}, {"$set": update})
    result = await apply_admin_fee_to_session(session_id, current_user.id)
    return {"message": "Override saved and admin fee recomputed", "result": result}


# ============ PAYOUT ENDPOINTS ============
def _is_finance_or_admin(user: User) -> bool:
    return user.role in ["admin", "super_admin", "finance"]


@router.get("/payouts")
async def list_payouts(
    status: Optional[str] = None,
    recipient_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List admin fee payouts.
    - Finance/Admin: sees all (can filter by recipient_id).
    - Marketing user (or any non-finance): forced to their own records only.
    """
    query: dict = {"type": "admin_fee"}
    if _is_finance_or_admin(current_user):
        if recipient_id:
            query["marketing_user_id"] = recipient_id
    else:
        query["marketing_user_id"] = current_user.id
    if status:
        query["status"] = status
    if start_date or end_date:
        q = {}
        if start_date:
            q["$gte"] = start_date
        if end_date:
            q["$lte"] = end_date
        query["session_start_date"] = q

    records = await db.marketing_commissions.find(query, {"_id": 0}).sort("session_start_date", -1).to_list(2000)
    total = sum(float(r.get("calculated_amount") or 0) for r in records)
    pending_count = sum(1 for r in records if r.get("status") == "pending")
    paid_count = sum(1 for r in records if r.get("status") == "paid")
    return {
        "records": records,
        "summary": {
            "total_records": len(records),
            "total_amount": round(total, 2),
            "pending_count": pending_count,
            "paid_count": paid_count,
        },
    }


@router.get("/payouts/summary")
async def payout_summary(current_user: User = Depends(get_current_user)):
    """Quick summary for dashboard widgets.
    - Finance/Admin: across all recipients.
    - Marketing user: for self only.
    """
    query: dict = {"type": "admin_fee"}
    is_admin_view = _is_finance_or_admin(current_user)
    if not is_admin_view:
        query["marketing_user_id"] = current_user.id

    records = await db.marketing_commissions.find(query, {"_id": 0}).to_list(5000)
    pending = [r for r in records if r.get("status") == "pending"]
    paid = [r for r in records if r.get("status") == "paid"]

    pending_amount = round(sum(float(r.get("calculated_amount") or 0) for r in pending), 2)
    paid_amount = round(sum(float(r.get("calculated_amount") or 0) for r in paid), 2)

    # By month buckets
    from collections import defaultdict
    by_month: dict = defaultdict(lambda: {"count": 0, "amount": 0.0, "pending_amount": 0.0})
    for r in records:
        sd = r.get("session_start_date") or ""
        key = sd[:7] if len(sd) >= 7 else "unknown"
        amt = float(r.get("calculated_amount") or 0)
        by_month[key]["count"] += 1
        by_month[key]["amount"] += amt
        if r.get("status") == "pending":
            by_month[key]["pending_amount"] += amt
    by_month_list = [{"month": k, **v, "amount": round(v["amount"], 2), "pending_amount": round(v["pending_amount"], 2)} for k, v in sorted(by_month.items(), reverse=True)]

    # By recipient (admin view only)
    by_recipient = []
    if is_admin_view:
        recs: dict = defaultdict(lambda: {"recipient_id": None, "recipient_name": None, "pending_amount": 0.0, "pending_count": 0, "total_amount": 0.0})
        for r in records:
            rid = r.get("marketing_user_id") or "unknown"
            recs[rid]["recipient_id"] = rid
            recs[rid]["recipient_name"] = r.get("marketing_user_name")
            amt = float(r.get("calculated_amount") or 0)
            recs[rid]["total_amount"] += amt
            if r.get("status") == "pending":
                recs[rid]["pending_amount"] += amt
                recs[rid]["pending_count"] += 1
        by_recipient = [
            {**v, "pending_amount": round(v["pending_amount"], 2), "total_amount": round(v["total_amount"], 2)}
            for v in recs.values()
        ]
        by_recipient.sort(key=lambda x: x["pending_amount"], reverse=True)

    return {
        "is_admin_view": is_admin_view,
        "pending_amount": pending_amount,
        "pending_count": len(pending),
        "paid_amount": paid_amount,
        "paid_count": len(paid),
        "by_month": by_month_list,
        "by_recipient": by_recipient,
    }


class BulkPayRequest(BaseModel):
    record_ids: list[str]
    payment_reference: Optional[str] = None
    paid_date: Optional[str] = None
    notes: Optional[str] = None


@router.post("/payouts/bulk-pay")
async def bulk_mark_paid(body: BulkPayRequest, current_user: User = Depends(get_current_user)):
    if not _is_finance_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only Finance/Admin can pay payouts")
    if not body.record_ids:
        raise HTTPException(status_code=400, detail="No records selected")

    paid_date = body.paid_date or get_malaysia_time().strftime("%Y-%m-%d")
    batch_ref = body.payment_reference or f"ADMFEE-{get_malaysia_time().strftime('%Y%m%d%H%M%S')}"

    # Only mark records that are currently pending admin_fee
    records = await db.marketing_commissions.find(
        {"id": {"$in": body.record_ids}, "type": "admin_fee", "status": "pending"},
        {"_id": 0},
    ).to_list(len(body.record_ids))

    if not records:
        raise HTTPException(status_code=404, detail="No matching pending records found")

    result = await db.marketing_commissions.update_many(
        {"id": {"$in": [r["id"] for r in records]}},
        {"$set": {
            "status": "paid",
            "paid_date": paid_date,
            "paid_by": current_user.id,
            "payment_reference": batch_ref,
            "payment_notes": body.notes,
            "updated_at": get_malaysia_time().isoformat(),
        }},
    )
    total_amount = round(sum(float(r.get("calculated_amount") or 0) for r in records), 2)
    return {
        "message": f"Marked {result.modified_count} payouts as paid",
        "modified_count": result.modified_count,
        "total_amount": total_amount,
        "payment_reference": batch_ref,
        "paid_date": paid_date,
    }


@router.post("/payouts/{record_id}/mark-paid")
async def mark_one_paid(record_id: str, current_user: User = Depends(get_current_user)):
    if not _is_finance_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Only Finance/Admin can pay payouts")
    record = await db.marketing_commissions.find_one(
        {"id": record_id, "type": "admin_fee"}, {"_id": 0}
    )
    if not record:
        raise HTTPException(status_code=404, detail="Payout not found")
    if record.get("status") == "paid":
        return {"message": "Already paid", "record": record}
    await db.marketing_commissions.update_one(
        {"id": record_id},
        {"$set": {
            "status": "paid",
            "paid_date": get_malaysia_time().strftime("%Y-%m-%d"),
            "paid_by": current_user.id,
            "updated_at": get_malaysia_time().isoformat(),
        }},
    )
    return {"message": "Marked as paid"}
