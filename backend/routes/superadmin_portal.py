"""
Super Admin Portal - Comprehensive System Administration
Full CRUD control over all system data with audit logging

Features:
- Dashboard with system stats
- User & Role Management
- Master Data Control (Companies, Programs, Trainers)
- Session Management
- Financial Override (Invoices, Payments, Credit Notes)
- Marketing Data (Clients, Quotations, Leads)
- Accounting Adjustments
- Audit Log Viewer
- System Settings
- Data Export
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from io import BytesIO
import uuid
import csv

from core import db, get_current_user, get_malaysia_time
from models import User
from services.superadmin_auth import is_super_admin

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


# ============ ACCESS CONTROL ============

def check_super_admin(user: User):
    """Phase 3A Section A: single canonical SuperAdmin authority check.

    Delegates to :func:`services.superadmin_auth.is_super_admin` so the
    legacy portal endpoints and the new controlled correction endpoints
    can never diverge. The rule is:

    - role == 'super_admin' allowed
    - user.email in APPROVED_GOD_MODE_EMAILS allowed (approved owner override)
    - everyone else denied
    """
    return is_super_admin(user)


# ============ AUDIT LOGGING ============

async def log_super_admin_action(
    action: str,
    entity_type: str,
    entity_id: str,
    performed_by: User,
    before_value: dict = None,
    after_value: dict = None,
    reason: str = None
):
    """Log all super admin actions for audit trail"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_value": before_value,
        "after_value": after_value,
        "performed_by_id": performed_by.id,
        "performed_by_email": performed_by.email,
        "performed_by_name": performed_by.full_name,
        "reason": reason,
        "ip_address": None,  # Can be added from request context
        "timestamp": get_malaysia_time().isoformat()
    }
    await db.super_admin_audit_log.insert_one(log_entry)
    return log_entry


# ============ DASHBOARD ============

@router.get("/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get system overview statistics"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    # Get counts from all major collections
    stats = {
        "users": {
            "total": await db.users.count_documents({}),
            "by_role": {}
        },
        "sessions": {
            "total": await db.sessions.count_documents({}),
            "ongoing": await db.sessions.count_documents({"completion_status": "ongoing"}),
            "completed": await db.sessions.count_documents({"completion_status": "completed"})
        },
        "invoices": {
            "total": await db.invoices.count_documents({}),
            "draft": await db.invoices.count_documents({"status": "auto_draft"}),
            "issued": await db.invoices.count_documents({"status": "issued"}),
            "paid": await db.invoices.count_documents({"status": "paid"})
        },
        "quotations": {
            "total": await db.quotations.count_documents({}),
            "draft": await db.quotations.count_documents({"status": "draft"}),
            "sent": await db.quotations.count_documents({"status": "sent"}),
            "accepted": await db.quotations.count_documents({"status": "accepted"})
        },
        "companies": await db.companies.count_documents({}),
        "programs": await db.programs.count_documents({}),
        "payments": await db.payments.count_documents({}),
        "credit_notes": await db.credit_notes.count_documents({}),
        "journal_entries": await db.journal_entries.count_documents({"status": "posted"})
    }
    
    # Get user counts by role
    pipeline = [
        {"$group": {"_id": "$role", "count": {"$sum": 1}}}
    ]
    role_counts = await db.users.aggregate(pipeline).to_list(20)
    stats["users"]["by_role"] = {r["_id"]: r["count"] for r in role_counts}
    
    # Recent activity
    recent_invoices = await db.invoices.find({}, {"_id": 0, "invoice_number": 1, "status": 1, "created_at": 1}).sort("created_at", -1).to_list(5)
    recent_payments = await db.payments.find({}, {"_id": 0, "id": 1, "amount": 1, "created_at": 1}).sort("created_at", -1).to_list(5)
    
    stats["recent_activity"] = {
        "invoices": recent_invoices,
        "payments": recent_payments
    }
    
    return stats


# ============ USER MANAGEMENT ============

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    additional_roles: Optional[List[str]] = None
    is_active: Optional[bool] = None
    department: Optional[str] = None


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "admin"
    department: Optional[str] = None


@router.get("/users")
async def get_all_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all users with optional filters"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if role:
        query["role"] = role
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).sort("created_at", -1).to_list(limit)
    return {"users": users, "count": len(users)}


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Get single user details"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update user details (requires reason)"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_fields = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    
    # Store before value for audit
    before_value = {k: user.get(k) for k in update_fields.keys() if k != "updated_at"}
    
    await db.users.update_one({"id": user_id}, {"$set": update_fields})
    
    await log_super_admin_action(
        action="user_updated",
        entity_type="user",
        entity_id=user_id,
        performed_by=current_user,
        before_value=before_value,
        after_value=update_fields,
        reason=reason
    )
    
    return {"message": "User updated", "updated_fields": list(update_fields.keys())}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    new_password: str = Query(..., min_length=6),
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Reset user password"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    import bcrypt
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    await db.users.update_one({"id": user_id}, {"$set": {"hashed_password": hashed, "updated_at": get_malaysia_time().isoformat()}})
    
    await log_super_admin_action(
        action="password_reset",
        entity_type="user",
        entity_id=user_id,
        performed_by=current_user,
        after_value={"email": user["email"]},
        reason=reason
    )
    
    return {"message": f"Password reset for {user['email']}"}


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Toggle user active status"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_status = not user.get("is_active", True)
    await db.users.update_one({"id": user_id}, {"$set": {"is_active": new_status, "updated_at": get_malaysia_time().isoformat()}})
    
    await log_super_admin_action(
        action="user_status_changed",
        entity_type="user",
        entity_id=user_id,
        performed_by=current_user,
        before_value={"is_active": user.get("is_active", True)},
        after_value={"is_active": new_status},
        reason=reason
    )
    
    return {"message": f"User {'activated' if new_status else 'deactivated'}", "is_active": new_status}


# ============ SESSIONS MANAGEMENT ============

@router.get("/sessions")
async def get_all_sessions(
    status: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all sessions with filters"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if status:
        query["completion_status"] = status
    if year:
        query["start_date"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    
    sessions = await db.sessions.find(query, {"_id": 0}).sort("start_date", -1).to_list(limit)
    
    # Enrich with company_name if not present on session document
    for session in sessions:
        if not session.get("company_name") and session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0, "name": 1})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
    
    return {"sessions": sessions, "count": len(sessions)}


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    update_data: dict,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update session details with cascade to invoices and leads"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Don't allow updating certain protected fields directly
    protected = ["id", "created_at", "invoice_id"]
    update_fields = {k: v for k, v in update_data.items() if k not in protected and v is not None}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    before_value = {k: session.get(k) for k in update_fields.keys() if k != "updated_at"}
    
    # Update the session
    await db.sessions.update_one({"id": session_id}, {"$set": update_fields})
    
    # CASCADE: If company_name is being updated, propagate to related records
    # PHASE 3A (Section O): only pre-issue invoices participate in cascade.
    # Issued / partially_paid / paid / terminal invoices are locked historical
    # documents — a session edit MUST NOT rewrite their snapshot. If the
    # issued invoice snapshot is genuinely wrong, SuperAdmin must use the
    # dedicated /superadmin/finance/invoices/{id}/correct-text controlled
    # endpoint (audited, before/after preserved).
    cascaded_updates = []
    if "company_name" in update_fields:
        new_company_name = update_fields["company_name"]

        # 1. Only pre-issue invoices — never rewrite locked/terminal.
        PRE_ISSUE = ["draft", "auto_draft", "finance_review", "approved"]
        invoice_result = await db.invoices.update_many(
            {"session_id": session_id, "status": {"$in": PRE_ISSUE}},
            {"$set": {"company_name": new_company_name, "bill_to_name": new_company_name}}
        )
        if invoice_result.modified_count > 0:
            cascaded_updates.append(f"{invoice_result.modified_count} pre-issue invoice(s)")

        # Report how many locked invoices were skipped so the SuperAdmin can
        # correct them individually via the controlled endpoints.
        locked_skipped = await db.invoices.count_documents({
            "session_id": session_id,
            "status": {"$nin": PRE_ISSUE + ["deleted"]},
        })
        if locked_skipped > 0:
            cascaded_updates.append(
                f"{locked_skipped} locked/terminal invoice(s) NOT rewritten — "
                "use /superadmin/finance/invoices/{id}/correct-text to correct each"
            )
        
        # 2. Update the original lead record if lead_id exists
        lead_id = session.get("lead_id")
        if lead_id:
            lead_result = await db.leads.update_one(
                {"id": lead_id},
                {"$set": {"company_name": new_company_name}}
            )
            if lead_result.modified_count > 0:
                cascaded_updates.append("1 lead")
        
        # 3. Update quotations linked to this session
        quotation_result = await db.quotations.update_many(
            {"session_id": session_id},
            {"$set": {"client_name": new_company_name}}
        )
        if quotation_result.modified_count > 0:
            cascaded_updates.append(f"{quotation_result.modified_count} quotation(s)")
    
    await log_super_admin_action(
        action="session_updated",
        entity_type="session",
        entity_id=session_id,
        performed_by=current_user,
        before_value=before_value,
        after_value=update_fields,
        reason=reason + (f" [Cascaded to: {', '.join(cascaded_updates)}]" if cascaded_updates else "")
    )
    
    return {
        "message": "Session updated", 
        "updated_fields": list(update_fields.keys()),
        "cascaded_to": cascaded_updates
    }


@router.post("/sessions/{session_id}/fix-status")
async def fix_session_status(
    session_id: str,
    new_status: str = Query(..., pattern="^(ongoing|completed|archived)$"),
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Fix session completion status"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    old_status = session.get("completion_status", "ongoing")
    await db.sessions.update_one({"id": session_id}, {"$set": {"completion_status": new_status, "updated_at": get_malaysia_time().isoformat()}})
    
    await log_super_admin_action(
        action="session_status_fixed",
        entity_type="session",
        entity_id=session_id,
        performed_by=current_user,
        before_value={"completion_status": old_status},
        after_value={"completion_status": new_status},
        reason=reason
    )
    
    # If marking as completed, trigger revenue recognition
    if new_status == "completed" and old_status != "completed":
        try:
            from routes.accounting import post_session_completed_revenue
            await post_session_completed_revenue(session_id, current_user.id, current_user.full_name)
        except Exception:
            pass
    
    return {"message": f"Session status changed from {old_status} to {new_status}"}


# ============ INVOICES MANAGEMENT ============

@router.get("/invoices")
async def get_all_invoices(
    status: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all invoices with filters"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    if year:
        query["created_at"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"invoices": invoices, "count": len(invoices)}


@router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    update_data: dict,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update invoice details (use with caution)"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Protected fields
    protected = ["id", "created_at", "invoice_number"]
    update_fields = {k: v for k, v in update_data.items() if k not in protected and v is not None}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # SAFEGUARD: Prevent status downgrades that would corrupt accounting journals.
    # Once an invoice is issued/paid, journals have been posted. Flipping it back
    # to draft and re-issuing creates DUPLICATE journal entries. Force the user
    # into the formal Reversal flow instead.
    new_status = update_fields.get("status")
    current_status = invoice.get("status")
    if new_status and new_status != current_status:
        BLOCKED_DOWNGRADES = {
            ("paid", "draft"), ("paid", "issued"), ("paid", "voided"),
            ("issued", "draft"),
            ("partially_paid", "draft"), ("partially_paid", "issued"), ("partially_paid", "voided"),
        }
        if (current_status, new_status) in BLOCKED_DOWNGRADES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot downgrade invoice status from '{current_status}' to '{new_status}'. "
                    "This would create duplicate accounting journals when re-issued. "
                    "Please use the formal Invoice Reversal flow (Super Admin → Reversals → Invoices tab) instead."
                )
            )
    
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    before_value = {k: invoice.get(k) for k in update_fields.keys() if k != "updated_at"}

    # ---- Phase 3A: reject high-impact changes on locked invoices ----------
    # SuperAdmin can still correct these — but ONLY through the controlled
    # dedicated endpoints (correct-number/value/date/text) so that impact
    # preview, before/after audit, and relationship preservation are applied.
    # Section S: `status` is now a HIGH_IMPACT field — arbitrary lifecycle
    # mutation via the generic PUT is prohibited on locked invoices; the
    # dedicated void/reversal/repair endpoints must be used instead.
    from services.superadmin_financial_correction import (
        high_impact_touched, HIGH_IMPACT_INVOICE_FIELDS,
    )
    touched = high_impact_touched(invoice, update_fields)
    if touched:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "USE_CONTROLLED_CORRECTION_ENDPOINT",
                "message": (
                    "Locked invoice has high-impact fields in this request. "
                    f"Use the dedicated SuperAdmin correction endpoints for {touched}. "
                    "For lifecycle changes use /invoices/{id}/void or "
                    "/payment-reversal/execute; for material data use "
                    "/api/superadmin/finance/invoices/{id}/correct-* endpoints."
                ),
                "fields": touched,
                "invoice_status": invoice.get("status"),
            },
        )

    await db.invoices.update_one({"id": invoice_id}, {"$set": update_fields})
    
    await log_super_admin_action(
        action="invoice_updated",
        entity_type="invoice",
        entity_id=invoice_id,
        performed_by=current_user,
        before_value=before_value,
        after_value=update_fields,
        reason=reason
    )
    
    return {"message": "Invoice updated", "invoice_number": invoice.get("invoice_number")}


@router.post("/invoices/{invoice_id}/void")
async def void_invoice(
    invoice_id: str,
    reason: str = Query(..., min_length=10),
    current_user: User = Depends(get_current_user)
):
    """Void an invoice"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") == "voided":
        raise HTTPException(status_code=400, detail="Invoice already voided")
    
    old_status = invoice.get("status")
    await db.invoices.update_one({"id": invoice_id}, {"$set": {
        "status": "voided",
        "voided_by": current_user.id,
        "voided_at": get_malaysia_time().isoformat(),
        "void_reason": reason
    }})
    
    await log_super_admin_action(
        action="invoice_voided",
        entity_type="invoice",
        entity_id=invoice_id,
        performed_by=current_user,
        before_value={"status": old_status},
        after_value={"status": "voided"},
        reason=reason
    )
    
    return {"message": f"Invoice {invoice.get('invoice_number')} voided"}


# ============ PAYMENTS MANAGEMENT ============

@router.get("/payments")
async def get_all_payments(
    year: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all payments"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if year:
        query["created_at"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"payments": payments, "count": len(payments)}


@router.post("/payments/{payment_id}/void")
async def void_payment(
    payment_id: str,
    reason: str = Query(..., min_length=10),
    current_user: User = Depends(get_current_user)
):
    """Phase 3A Section J/K: legacy alias — delegates to the canonical
    payment reversal engine. The payment is reversed (status='reversed'),
    NOT set to 'voided' — legacy voided rows are preserved on disk but new
    reversals use the canonical status.
    """
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")

    from services.payment_reversal import PaymentReversalService
    svc = PaymentReversalService(db)
    result = await svc.execute(payment_id, reason=reason, user=current_user, alias="legacy_void")
    if result.get("error") == "PAYMENT_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Payment not found")
    return result


# ============ QUOTATIONS MANAGEMENT ============

@router.get("/quotations")
async def get_all_quotations(
    status: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all quotations"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    
    quotations = await db.quotations.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"quotations": quotations, "count": len(quotations)}


@router.put("/quotations/{quotation_id}")
async def update_quotation(
    quotation_id: str,
    update_data: dict,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update quotation"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    protected = ["id", "created_at", "quotation_number"]
    update_fields = {k: v for k, v in update_data.items() if k not in protected and v is not None}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    before_value = {k: quotation.get(k) for k in update_fields.keys() if k != "updated_at"}
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_fields})
    
    await log_super_admin_action(
        action="quotation_updated",
        entity_type="quotation",
        entity_id=quotation_id,
        performed_by=current_user,
        before_value=before_value,
        after_value=update_fields,
        reason=reason
    )
    
    return {"message": "Quotation updated"}


@router.delete("/quotations/{quotation_id}")
async def delete_quotation(
    quotation_id: str,
    reason: str = Query(..., min_length=10),
    current_user: User = Depends(get_current_user)
):
    """Delete a quotation (soft delete)"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Soft delete
    await db.quotations.update_one({"id": quotation_id}, {"$set": {
        "is_deleted": True,
        "deleted_by": current_user.id,
        "deleted_at": get_malaysia_time().isoformat(),
        "delete_reason": reason
    }})
    
    await log_super_admin_action(
        action="quotation_deleted",
        entity_type="quotation",
        entity_id=quotation_id,
        performed_by=current_user,
        before_value={"quotation_number": quotation.get("quotation_number")},
        reason=reason
    )
    
    return {"message": f"Quotation {quotation.get('quotation_number')} deleted"}


# ============ COMPANIES MANAGEMENT ============

@router.get("/companies")
async def get_all_companies(
    search: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all companies"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    companies = await db.companies.find(query, {"_id": 0}).sort("name", 1).to_list(limit)
    return {"companies": companies, "count": len(companies)}


@router.put("/companies/{company_id}")
async def update_company(
    company_id: str,
    update_data: dict,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update company details"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    update_fields = {k: v for k, v in update_data.items() if k != "id" and v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    before_value = {k: company.get(k) for k in update_fields.keys()}
    await db.companies.update_one({"id": company_id}, {"$set": update_fields})
    
    await log_super_admin_action(
        action="company_updated",
        entity_type="company",
        entity_id=company_id,
        performed_by=current_user,
        before_value=before_value,
        after_value=update_fields,
        reason=reason
    )
    
    return {"message": "Company updated"}


# ============ ACCOUNTING ADJUSTMENTS ============

@router.get("/journal-entries")
async def get_journal_entries_admin(
    year: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all journal entries"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if year:
        query["date"] = {"$gte": f"{year}-01-01", "$lt": f"{year + 1}-01-01"}
    if status:
        query["status"] = status
    
    entries = await db.journal_entries.find(query, {"_id": 0}).sort("date", -1).to_list(limit)
    return {"entries": entries, "count": len(entries)}


@router.post("/journal-entries/{journal_id}/void")
async def void_journal_entry_admin(
    journal_id: str,
    reason: str = Query(..., min_length=10),
    current_user: User = Depends(get_current_user)
):
    """Void a journal entry"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    entry = await db.journal_entries.find_one({"id": journal_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    if entry.get("status") == "voided":
        raise HTTPException(status_code=400, detail="Already voided")
    
    await db.journal_entries.update_one({"id": journal_id}, {"$set": {
        "status": "voided",
        "voided_by": current_user.id,
        "voided_by_name": current_user.full_name,
        "voided_at": get_malaysia_time().isoformat(),
        "void_reason": reason
    }})
    
    await log_super_admin_action(
        action="journal_voided",
        entity_type="journal_entry",
        entity_id=journal_id,
        performed_by=current_user,
        before_value={"journal_no": entry.get("journal_no"), "status": entry.get("status")},
        after_value={"status": "voided"},
        reason=reason
    )
    
    return {"message": f"Journal entry {entry.get('journal_no')} voided"}


@router.put("/journal-entries/{journal_id}")
async def update_journal_entry_description(
    journal_id: str,
    update_data: dict,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update journal entry description (to fix Unknown values)"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    entry = await db.journal_entries.find_one({"id": journal_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    # Only allow description update
    new_description = update_data.get("description")
    if not new_description:
        raise HTTPException(status_code=400, detail="Description is required")
    
    old_description = entry.get("description", "")
    
    await db.journal_entries.update_one({"id": journal_id}, {"$set": {
        "description": new_description,
        "updated_at": get_malaysia_time().isoformat()
    }})
    
    await log_super_admin_action(
        action="journal_description_updated",
        entity_type="journal_entry",
        entity_id=journal_id,
        performed_by=current_user,
        before_value={"description": old_description},
        after_value={"description": new_description},
        reason=reason
    )
    
    return {"message": f"Journal entry {entry.get('journal_no')} description updated"}


# ============ AUDIT LOG ============

@router.get("/audit-log")
async def get_audit_log(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get super admin audit log"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    
    logs = await db.super_admin_audit_log.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"logs": logs, "count": len(logs)}


# ============ DATA EXPORT ============

@router.get("/export/{collection}")
async def export_collection(
    collection: str,
    format: str = "csv",
    current_user: User = Depends(get_current_user)
):
    """Export collection data to CSV"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    allowed_collections = ["users", "sessions", "invoices", "payments", "quotations", "companies", "programs", "journal_entries"]
    if collection not in allowed_collections:
        raise HTTPException(status_code=400, detail=f"Collection not allowed. Allowed: {allowed_collections}")
    
    coll = db[collection]
    data = await coll.find({}, {"_id": 0, "hashed_password": 0}).to_list(10000)
    
    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    
    # Create CSV
    output = BytesIO()
    
    if data:
        # Get all unique keys
        all_keys = set()
        for doc in data:
            all_keys.update(doc.keys())
        headers = sorted(list(all_keys))
        
        # Write CSV
        import io
        text_output = io.StringIO()
        writer = csv.DictWriter(text_output, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for doc in data:
            # Convert non-string values
            row = {k: str(v) if not isinstance(v, (str, int, float, type(None))) else v for k, v in doc.items()}
            writer.writerow(row)
        
        output = BytesIO(text_output.getvalue().encode('utf-8'))
    
    await log_super_admin_action(
        action="data_exported",
        entity_type=collection,
        entity_id="export",
        performed_by=current_user,
        after_value={"collection": collection, "record_count": len(data)}
    )
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={collection}_{get_malaysia_time().strftime('%Y%m%d')}.csv"}
    )


# ============ SYSTEM SETTINGS ============

@router.get("/settings")
async def get_system_settings(current_user: User = Depends(get_current_user)):
    """Get all system settings"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    settings = {
        "company_settings": await db.company_settings.find_one({}, {"_id": 0}),
        "accounting_settings": await db.accounting_settings.find_one({"id": "accounting_settings"}, {"_id": 0}),
        "billing_parties": await db.billing_parties.find({}, {"_id": 0}).to_list(10)
    }
    return settings


@router.put("/settings/{setting_type}")
async def update_system_settings(
    setting_type: str,
    update_data: dict,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update system settings"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    collection_map = {
        "company": db.company_settings,
        "accounting": db.accounting_settings
    }
    
    if setting_type not in collection_map:
        raise HTTPException(status_code=400, detail="Invalid setting type")
    
    coll = collection_map[setting_type]
    
    if setting_type == "accounting":
        before = await coll.find_one({"id": "accounting_settings"}, {"_id": 0})
        await coll.update_one({"id": "accounting_settings"}, {"$set": update_data}, upsert=True)
    else:
        before = await coll.find_one({}, {"_id": 0})
        if before:
            await coll.update_one({}, {"$set": update_data})
        else:
            await coll.insert_one(update_data)
    
    await log_super_admin_action(
        action="settings_updated",
        entity_type=f"{setting_type}_settings",
        entity_id=setting_type,
        performed_by=current_user,
        before_value=before,
        after_value=update_data,
        reason=reason
    )
    
    return {"message": f"{setting_type.title()} settings updated"}


# ============ BULK OPERATIONS ============

@router.post("/bulk/sessions/update-status")
async def bulk_update_session_status(
    session_ids: List[str],
    new_status: str = Query(..., pattern="^(ongoing|completed|archived)$"),
    reason: str = Query(..., min_length=10),
    current_user: User = Depends(get_current_user)
):
    """Bulk update session status"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    result = await db.sessions.update_many(
        {"id": {"$in": session_ids}},
        {"$set": {"completion_status": new_status, "updated_at": get_malaysia_time().isoformat()}}
    )
    
    await log_super_admin_action(
        action="bulk_session_status_update",
        entity_type="session",
        entity_id=",".join(session_ids[:5]) + ("..." if len(session_ids) > 5 else ""),
        performed_by=current_user,
        after_value={"new_status": new_status, "count": result.modified_count},
        reason=reason
    )
    
    return {"message": f"Updated {result.modified_count} sessions to {new_status}"}


# ============ CREATE SUPER ADMIN USER ============

@router.post("/create-super-admin")
async def create_super_admin_user(
    email: str = Query(...),
    current_user: User = Depends(get_current_user)
):
    """Elevate existing user to super_admin role"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_role = user.get("role")
    await db.users.update_one({"email": email}, {"$set": {"role": "super_admin"}})
    
    await log_super_admin_action(
        action="user_elevated_to_super_admin",
        entity_type="user",
        entity_id=user["id"],
        performed_by=current_user,
        before_value={"role": old_role},
        after_value={"role": "super_admin"},
        reason="Elevated to Super Admin"
    )
    
    return {"message": f"{email} is now a Super Admin"}



# ============ PAYMENT REVERSAL ============

class PaymentReversalRequest(BaseModel):
    payment_id: str
    reason: str = Field(..., min_length=10, description="Mandatory reason for reversal")
    confirm: bool = False


@router.get("/payment-reversal/preview/{payment_id}")
async def preview_payment_reversal(
    payment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Phase 3A Section L: preview via the canonical reversal service.
    Returns auto_affected_credit_notes (source_payment_id linked) separately
    from manual_review_credit_notes (same invoice, not linked)."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    from services.payment_reversal import PaymentReversalService
    result = await PaymentReversalService(db).preview(payment_id)
    if result.get("error") == "PAYMENT_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Payment not found")
    return result

    from services.payment_reversal import PaymentReversalService
    result = await PaymentReversalService(db).preview(payment_id)
    if result.get("error") == "PAYMENT_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Payment not found")
    return result


@router.post("/payment-reversal/execute")
async def execute_payment_reversal(
    request: PaymentReversalRequest,
    current_user: User = Depends(get_current_user)
):
    """Phase 3A Section J/M/N: audited execute delegating to the canonical
    reversal engine. Idempotent — retrying returns the prior record."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Please confirm the reversal by setting confirm=true")

    from services.payment_reversal import PaymentReversalService
    from routes.finance_payments import create_audit_trail_entry

    svc = PaymentReversalService(db)
    result = await svc.execute(
        request.payment_id, reason=request.reason, user=current_user, alias="formal_execute",
    )
    if result.get("error") == "PAYMENT_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Payment not found")
    # Best-effort dual-audit (keep prior finance audit trail entries).
    if not result.get("idempotent"):
        payment = await db.payments.find_one({"id": request.payment_id}, {"_id": 0})
        invoice = await db.invoices.find_one(
            {"id": payment.get("invoice_id")}, {"_id": 0}
        ) if payment and payment.get("invoice_id") else None
        company_name = (invoice.get("company_name") or invoice.get("bill_to_name") or "Unknown") if invoice else "Unknown"
        await log_super_admin_action(
            action="payment_reversed",
            entity_type="payment",
            entity_id=request.payment_id,
            performed_by=current_user,
            before_value={"status": "active", "amount": payment.get("amount") if payment else None},
            after_value={"status": "reversed"},
            reason=request.reason,
        )
        try:
            await create_audit_trail_entry(
                action="Payment Reversed (Super Admin)",
                record_reference=f"{company_name} - RM {float(payment.get('amount') or 0):,.2f}",
                entity_type="payment",
                entity_id=request.payment_id,
                changed_by=current_user,
                reason=request.reason,
                field_changed="status",
                from_value="active",
                to_value="reversed",
            )
        except Exception:
            pass
    return result


@router.get("/payment-reversals")
async def get_payment_reversals(
    current_user: User = Depends(get_current_user)
):
    """Get all payment reversal records"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")

    reversals = await db.payment_reversals.find({}, {"_id": 0}).sort("reversed_at", -1).to_list(500)
    return reversals


@router.get("/payment-reversal/{reversal_id}")
async def get_payment_reversal(
    reversal_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific payment reversal record with full details"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")

    reversal = await db.payment_reversals.find_one({"id": reversal_id}, {"_id": 0})
    if not reversal:
        raise HTTPException(status_code=404, detail="Reversal record not found")
    return reversal


@router.get("/payments-for-reversal")
async def get_payments_for_reversal(
    current_user: User = Depends(get_current_user)
):
    """Get all active (non-reversed) payments for reversal selection"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")

    payments = await db.payments.find(
        {"status": {"$nin": ["reversed", "voided"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    # Enrich with invoice data
    for p in payments:
        if p.get("invoice_id"):
            invoice = await db.invoices.find_one({"id": p["invoice_id"]}, {"_id": 0, "invoice_number": 1, "company_name": 1, "bill_to_name": 1})
            if invoice:
                p["invoice_number"] = invoice.get("invoice_number")
                p["company_name"] = invoice.get("company_name") or invoice.get("bill_to_name")
    return payments


# ============ AUDIT TRAIL FOR ENTITY ============

@router.get("/audit-trail/{entity_type}/{entity_id}")
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get audit trail for a specific entity (payment, credit_note, invoice, etc.)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Search across multiple audit collections
    results = []

    # Super admin audit log
    sa_logs = await db.super_admin_audit_log.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    for log in sa_logs:
        log["source"] = "super_admin"
    results.extend(sa_logs)

    # Finance audit log
    fa_logs = await db.finance_audit_log.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    for log in fa_logs:
        log["source"] = "finance"
    results.extend(fa_logs)

    # General audit trail
    at_logs = await db.audit_trail.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    for log in at_logs:
        log["source"] = "audit_trail"
    results.extend(at_logs)

    # Sort all by timestamp descending
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return results


# ============ QUOTATION REVERSAL ============
# Reverses an "accepted" quotation back to "sent" (or original status). 
# If a draft session was auto-created from this quotation, it gets deleted
# ONLY if the session has no participants, no invoice, and no payments.

class QuotationReversalRequest(BaseModel):
    quotation_id: str
    reason: str = Field(..., min_length=10)
    confirm: bool = False


@router.get("/quotations-for-reversal")
async def get_quotations_for_reversal(current_user: User = Depends(get_current_user)):
    """Get accepted quotations eligible for reversal (i.e. not yet invoiced/paid)."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    quotations = await db.quotations.find(
        {"status": "accepted"},
        {"_id": 0}
    ).sort("client_response_at", -1).to_list(500)
    # Enrich with session linkage indicator
    for q in quotations:
        session = await db.sessions.find_one({"quotation_id": q["id"]}, {"_id": 0, "id": 1, "name": 1, "status": 1, "invoice_id": 1})
        q["linked_session"] = session
    return quotations


@router.get("/quotation-reversal/preview/{quotation_id}")
async def preview_quotation_reversal(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Preview what will be affected by reversing an accepted quotation."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")

    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.get("status") != "accepted":
        raise HTTPException(status_code=400, detail=f"Only accepted quotations can be reversed (current: {quotation.get('status')})")

    # Find linked session
    session = await db.sessions.find_one({"quotation_id": quotation_id}, {"_id": 0})
    blockers = []
    session_info = None
    if session:
        invoice_for_session = await db.invoices.find_one({"session_id": session["id"]}, {"_id": 0, "id": 1, "invoice_number": 1, "status": 1})
        if invoice_for_session and invoice_for_session.get("status") != "voided":
            blockers.append(f"Invoice {invoice_for_session.get('invoice_number')} exists for the linked session — void/reverse the invoice first.")
        participants = len(session.get("participant_ids") or [])
        if participants > 0:
            blockers.append(f"Linked session has {participants} participant(s) — remove them first.")
        session_info = {
            "id": session.get("id"),
            "name": session.get("name"),
            "status": session.get("status"),
            "participants": participants,
            "will_be_deleted": not bool(blockers)
        }

    return {
        "quotation": {
            "id": quotation["id"],
            "quotation_number": quotation.get("quotation_number"),
            "client_name": quotation.get("client_name"),
            "programme_name": quotation.get("programme_name"),
            "total_amount": quotation.get("total_amount", 0),
            "status": quotation.get("status"),
            "client_response_at": quotation.get("client_response_at"),
            "training_date": quotation.get("training_date")
        },
        "linked_session": session_info,
        "blockers": blockers,
        "can_reverse": len(blockers) == 0,
        "summary": {
            "new_quotation_status": "sent",
            "session_action": "delete" if (session and not blockers) else ("skip" if not session else "blocked")
        }
    }


@router.post("/quotation-reversal/execute")
async def execute_quotation_reversal(request: QuotationReversalRequest, current_user: User = Depends(get_current_user)):
    """Reverse an accepted quotation back to 'sent' status and delete its draft session (if safe)."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Please confirm the reversal by setting confirm=true")

    quotation = await db.quotations.find_one({"id": request.quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.get("status") != "accepted":
        raise HTTPException(status_code=400, detail=f"Only accepted quotations can be reversed (current: {quotation.get('status')})")

    now = get_malaysia_time()
    reversal_id = str(uuid.uuid4())
    actions_taken = []
    deleted_session_id = None

    # Block if linked session has invoice/participants
    session = await db.sessions.find_one({"quotation_id": request.quotation_id}, {"_id": 0})
    if session:
        invoice_for_session = await db.invoices.find_one({"session_id": session["id"], "status": {"$ne": "voided"}}, {"_id": 0, "invoice_number": 1})
        if invoice_for_session:
            raise HTTPException(status_code=400, detail=f"Invoice {invoice_for_session.get('invoice_number')} exists for the linked session — void/reverse the invoice first.")
        if (session.get("participant_ids") or []):
            raise HTTPException(status_code=400, detail="Linked session has participants — remove them first.")

    # 1. Revert quotation status to "sent"
    old_status = quotation.get("status")
    await db.quotations.update_one(
        {"id": request.quotation_id},
        {"$set": {
            "status": "sent",
            "reversed_by": current_user.id,
            "reversed_by_name": current_user.full_name,
            "reversed_at": now.isoformat(),
            "reversal_reason": request.reason,
            "reversal_id": reversal_id,
            "client_response_at": None,
            "training_date": None,
            "training_dates": None,
            "updated_at": now.isoformat()
        }}
    )
    actions_taken.append(f"Quotation {quotation.get('quotation_number')} status: {old_status} → sent")

    # 2. Delete draft session (if exists and safe)
    if session:
        await db.sessions.delete_one({"id": session["id"]})
        deleted_session_id = session["id"]
        actions_taken.append(f"Draft session '{session.get('name')}' deleted")

    # 3. Sync lead stage (if linked)
    try:
        lead = await db.marketing_leads.find_one({"quotation_id": request.quotation_id}, {"_id": 0, "id": 1, "stage": 1})
        if lead and lead.get("stage") == "won":
            await db.marketing_leads.update_one({"id": lead["id"]}, {"$set": {"stage": "quotation_sent", "updated_at": now.isoformat()}})
            actions_taken.append("Lead reverted to 'quotation_sent'")
    except Exception as e:
        print(f"[quotation_reversal] lead sync warning: {e}")

    # 4. Audit log
    await log_super_admin_action(
        action="quotation_reversed",
        entity_type="quotation",
        entity_id=request.quotation_id,
        performed_by=current_user,
        before_value={"status": old_status},
        after_value={"status": "sent"},
        reason=request.reason
    )

    # 5. Store reversal record
    reversal_record = {
        "id": reversal_id,
        "quotation_id": request.quotation_id,
        "quotation_number": quotation.get("quotation_number"),
        "client_name": quotation.get("client_name"),
        "total_amount": quotation.get("total_amount", 0),
        "deleted_session_id": deleted_session_id,
        "actions_taken": actions_taken,
        "reason": request.reason,
        "reversed_by": current_user.id,
        "reversed_by_name": current_user.full_name,
        "reversed_at": now.isoformat()
    }
    await db.quotation_reversals.insert_one(reversal_record)
    reversal_record.pop("_id", None)

    return {
        "message": "Quotation reversed successfully",
        "reversal_id": reversal_id,
        "actions_taken": actions_taken
    }


@router.get("/quotation-reversals")
async def get_quotation_reversals(current_user: User = Depends(get_current_user)):
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    reversals = await db.quotation_reversals.find({}, {"_id": 0}).sort("reversed_at", -1).to_list(500)
    return reversals


# ============ INVOICE REVERSAL ============
# Reverts an issued invoice back to "draft" status.
# Cannot reverse if there are active (non-reversed) payments against it.
# Voids the journal entry created at issuance.

class InvoiceReversalRequest(BaseModel):
    invoice_id: str
    reason: str = Field(..., min_length=10)
    confirm: bool = False


@router.get("/invoices-for-reversal")
async def get_invoices_for_reversal(current_user: User = Depends(get_current_user)):
    """Get issued invoices eligible for reversal (i.e. no active payments)."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    invoices = await db.invoices.find(
        {"status": {"$in": ["issued", "paid"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    # Enrich with active-payment count
    for inv in invoices:
        active_payments = await db.payments.count_documents({"invoice_id": inv["id"], "status": {"$ne": "reversed"}})
        inv["active_payment_count"] = active_payments
    return invoices


@router.get("/invoice-reversal/preview/{invoice_id}")
async def preview_invoice_reversal(invoice_id: str, current_user: User = Depends(get_current_user)):
    """Preview what will be affected by reversing an issued invoice."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")

    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("status") not in ["issued", "paid"]:
        raise HTTPException(status_code=400, detail=f"Only issued/paid invoices can be reversed (current: {invoice.get('status')})")

    # Find active payments
    active_payments = await db.payments.find(
        {"invoice_id": invoice_id, "status": {"$ne": "reversed"}},
        {"_id": 0, "id": 1, "receipt_number": 1, "amount": 1, "payment_date": 1}
    ).to_list(100)

    # Find journal entries to void
    linked_journals = await db.journal_entries.find(
        {"source_id": invoice_id, "source_module": "invoice", "status": {"$ne": "voided"}},
        {"_id": 0, "id": 1, "journal_no": 1, "description": 1, "total_debit": 1}
    ).to_list(20)

    blockers = []
    if active_payments:
        blockers.append(f"{len(active_payments)} active payment(s) exist against this invoice. Reverse the payments first.")

    return {
        "invoice": {
            "id": invoice["id"],
            "invoice_number": invoice.get("invoice_number"),
            "company_name": invoice.get("company_name") or invoice.get("bill_to_name"),
            "total_amount": invoice.get("total_amount", 0),
            "status": invoice.get("status"),
            "invoice_date": invoice.get("invoice_date") or invoice.get("created_at")
        },
        "active_payments": active_payments,
        "linked_journals": linked_journals,
        "blockers": blockers,
        "can_reverse": len(blockers) == 0,
        "summary": {
            "new_invoice_status": "draft",
            "journals_to_void": len(linked_journals)
        }
    }


@router.post("/invoice-reversal/execute")
async def execute_invoice_reversal(request: InvoiceReversalRequest, current_user: User = Depends(get_current_user)):
    """Reverse an issued invoice back to 'draft' (voids journals; blocked if active payments exist)."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Please confirm the reversal by setting confirm=true")

    invoice = await db.invoices.find_one({"id": request.invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("status") not in ["issued", "paid"]:
        raise HTTPException(status_code=400, detail=f"Only issued/paid invoices can be reversed (current: {invoice.get('status')})")

    # Block if active payments exist
    active_payments = await db.payments.count_documents({"invoice_id": request.invoice_id, "status": {"$ne": "reversed"}})
    if active_payments > 0:
        raise HTTPException(status_code=400, detail=f"{active_payments} active payment(s) exist for this invoice. Reverse the payments first.")

    now = get_malaysia_time()
    reversal_id = str(uuid.uuid4())
    actions_taken = []

    # 1. Revert invoice status to draft
    old_status = invoice.get("status")
    await db.invoices.update_one(
        {"id": request.invoice_id},
        {"$set": {
            "status": "draft",
            "reversed_by": current_user.id,
            "reversed_by_name": current_user.full_name,
            "reversed_at": now.isoformat(),
            "reversal_reason": request.reason,
            "reversal_id": reversal_id,
            "updated_at": now.isoformat()
        }}
    )
    actions_taken.append(f"Invoice {invoice.get('invoice_number')} status: {old_status} → draft")

    # 2. Sync linked session.invoice_status
    if invoice.get("session_id"):
        await db.sessions.update_one(
            {"id": invoice["session_id"]},
            {"$set": {"invoice_status": "draft"}}
        )

    # 3. Void linked journal entries
    linked_journals = await db.journal_entries.find(
        {"source_id": request.invoice_id, "source_module": "invoice", "status": {"$ne": "voided"}},
        {"_id": 0}
    ).to_list(20)
    voided_journals = []
    for je in linked_journals:
        await db.journal_entries.update_one(
            {"id": je["id"]},
            {"$set": {
                "status": "voided",
                "voided_by": current_user.id,
                "voided_by_name": current_user.full_name,
                "voided_at": now.isoformat(),
                "void_reason": f"Invoice reversal: {request.reason}",
                "reversal_id": reversal_id,
                "updated_at": now.isoformat()
            }}
        )
        voided_journals.append(je["id"])
        actions_taken.append(f"Journal {je.get('journal_no')} voided")

    # 4. Audit log
    await log_super_admin_action(
        action="invoice_reversed",
        entity_type="invoice",
        entity_id=request.invoice_id,
        performed_by=current_user,
        before_value={"status": old_status},
        after_value={"status": "draft"},
        reason=request.reason
    )

    # 5. Store reversal record
    reversal_record = {
        "id": reversal_id,
        "invoice_id": request.invoice_id,
        "invoice_number": invoice.get("invoice_number"),
        "company_name": invoice.get("company_name") or invoice.get("bill_to_name"),
        "total_amount": invoice.get("total_amount", 0),
        "previous_status": old_status,
        "voided_journal_entries": voided_journals,
        "actions_taken": actions_taken,
        "reason": request.reason,
        "reversed_by": current_user.id,
        "reversed_by_name": current_user.full_name,
        "reversed_at": now.isoformat()
    }
    await db.invoice_reversals.insert_one(reversal_record)
    reversal_record.pop("_id", None)

    return {
        "message": "Invoice reversed successfully",
        "reversal_id": reversal_id,
        "actions_taken": actions_taken
    }


@router.get("/invoice-reversals")
async def get_invoice_reversals(current_user: User = Depends(get_current_user)):
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    reversals = await db.invoice_reversals.find({}, {"_id": 0}).sort("reversed_at", -1).to_list(500)
    return reversals


# ============ DUPLICATE JOURNAL AUDIT & REPAIR ============
# Fixes the God Mode loophole: if super admin flipped a paid/issued invoice back
# to draft and then re-issued, the invoice now has multiple active journal entries.

@router.get("/audit/duplicate-invoice-journals")
async def audit_duplicate_invoice_journals(current_user: User = Depends(get_current_user)):
    """READ-ONLY: List every invoice that has more than one active (non-voided)
    issuance journal entry. Also flags duplicate payment journals per invoice."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")

    pipeline = [
        {"$match": {"source_module": "invoice", "status": {"$ne": "voided"}}},
        {"$group": {
            "_id": "$source_id",
            "count": {"$sum": 1},
            "journals": {"$push": {"id": "$id", "journal_no": "$journal_no", "entry_date": "$entry_date", "total_debit": "$total_debit", "description": "$description"}}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicates = await db.journal_entries.aggregate(pipeline).to_list(500)

    results = []
    for grp in duplicates:
        inv_id = grp["_id"]
        inv = await db.invoices.find_one({"id": inv_id}, {"_id": 0, "id": 1, "invoice_number": 1, "company_name": 1, "status": 1, "total_amount": 1})
        # Sort journals by entry_date ascending so the earliest = original
        journals = sorted(grp["journals"], key=lambda j: j.get("entry_date") or "")
        results.append({
            "invoice_id": inv_id,
            "invoice_number": inv.get("invoice_number") if inv else "(deleted)",
            "company_name": inv.get("company_name") if inv else "-",
            "current_status": inv.get("status") if inv else None,
            "total_amount": inv.get("total_amount") if inv else 0,
            "active_journal_count": grp["count"],
            "original_journal": journals[0],
            "duplicate_journals": journals[1:],
            "would_void_count": len(journals) - 1,
        })

    # Also flag duplicate payment journals per invoice (payments with same invoice_id, both active)
    payment_pipeline = [
        {"$match": {"source_module": "payment", "status": {"$ne": "voided"}}},
        {"$group": {"_id": "$source_id", "count": {"$sum": 1}, "journals": {"$push": {"id": "$id", "journal_no": "$journal_no", "entry_date": "$entry_date"}}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    pmt_dupes = await db.journal_entries.aggregate(payment_pipeline).to_list(500)

    return {
        "invoices_with_duplicate_journals": len(results),
        "details": results,
        "payments_with_duplicate_journals": len(pmt_dupes),
        "payment_duplicates": pmt_dupes,
        "note": "Run POST /superadmin/audit/repair-duplicate-journals with confirm=true to void ALL duplicate journals (keeps the earliest original for each invoice)."
    }


class RepairDupsRequest(BaseModel):
    confirm: bool = False
    reason: str = Field(..., min_length=10)


@router.post("/audit/repair-duplicate-journals")
async def repair_duplicate_journals(request: RepairDupsRequest, current_user: User = Depends(get_current_user)):
    """Void all DUPLICATE (later) journal entries per invoice, keeping the earliest as the authoritative one.
    Fixes the God Mode loophole (paid → draft flip → re-issue → double journals)."""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to run the repair")

    now = get_malaysia_time().isoformat()
    voided = []

    for src_module in ["invoice", "payment"]:
        pipeline = [
            {"$match": {"source_module": src_module, "status": {"$ne": "voided"}}},
            {"$group": {"_id": "$source_id", "count": {"$sum": 1}, "journals": {"$push": {"id": "$id", "entry_date": "$entry_date"}}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        dupes = await db.journal_entries.aggregate(pipeline).to_list(1000)
        for grp in dupes:
            journals = sorted(grp["journals"], key=lambda j: j.get("entry_date") or "")
            for je in journals[1:]:
                await db.journal_entries.update_one(
                    {"id": je["id"]},
                    {"$set": {
                        "status": "voided",
                        "voided_by": current_user.id,
                        "voided_by_name": current_user.full_name,
                        "voided_at": now,
                        "void_reason": f"Auto-repair duplicate journal: {request.reason}",
                        "updated_at": now,
                    }}
                )
                voided.append({"source_module": src_module, "source_id": grp["_id"], "journal_id": je["id"]})

    return {
        "message": f"Voided {len(voided)} duplicate journal entries (earliest journal per source kept as authoritative).",
        "voided": voided,
    }
