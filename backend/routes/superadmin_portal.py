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

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


# ============ ACCESS CONTROL ============

def check_super_admin(user: User):
    """Check if user has super admin access"""
    # Allow specific email OR super_admin role
    allowed_emails = ["arjuna@mddrc.com.my"]
    if user.email in allowed_emails or user.role == "super_admin":
        return True
    return False


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
    return {"sessions": sessions, "count": len(sessions)}


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    update_data: dict,
    reason: str = Query(..., min_length=5),
    current_user: User = Depends(get_current_user)
):
    """Update session details"""
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
    
    await db.sessions.update_one({"id": session_id}, {"$set": update_fields})
    
    await log_super_admin_action(
        action="session_updated",
        entity_type="session",
        entity_id=session_id,
        performed_by=current_user,
        before_value=before_value,
        after_value=update_fields,
        reason=reason
    )
    
    return {"message": "Session updated", "updated_fields": list(update_fields.keys())}


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
        except:
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
    
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    before_value = {k: invoice.get(k) for k in update_fields.keys() if k != "updated_at"}
    
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
    """Void a payment"""
    if not check_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.get("status") == "voided":
        raise HTTPException(status_code=400, detail="Payment already voided")
    
    await db.payments.update_one({"id": payment_id}, {"$set": {
        "status": "voided",
        "voided_by": current_user.id,
        "voided_at": get_malaysia_time().isoformat(),
        "void_reason": reason
    }})
    
    # Update invoice amount_paid if needed
    if payment.get("invoice_id"):
        invoice = await db.invoices.find_one({"id": payment["invoice_id"]}, {"_id": 0})
        if invoice:
            new_amount_paid = (invoice.get("amount_paid", 0) or 0) - payment.get("amount", 0)
            new_status = "issued" if new_amount_paid < invoice.get("total_amount", 0) else invoice.get("status")
            await db.invoices.update_one({"id": payment["invoice_id"]}, {"$set": {
                "amount_paid": max(0, new_amount_paid),
                "status": new_status
            }})
    
    await log_super_admin_action(
        action="payment_voided",
        entity_type="payment",
        entity_id=payment_id,
        performed_by=current_user,
        before_value={"amount": payment.get("amount")},
        after_value={"status": "voided"},
        reason=reason
    )
    
    return {"message": "Payment voided"}


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
