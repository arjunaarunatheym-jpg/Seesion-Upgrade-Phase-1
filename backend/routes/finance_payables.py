"""
Finance Payables, Session Costing, Income & Company Settings routes
Stage F4: ~22 endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid
import os

from core import db, get_current_user, get_malaysia_time
from models import User, CompanySettings

router = APIRouter(prefix="/finance", tags=["finance-payables"])


# ============ MODELS ============
class PayablesPeriodCreate(BaseModel):
    year: int
    month: int


# ============ HELPER FUNCTIONS ============
async def log_finance_action(entity_type: str, entity_id: str, action: str, 
                             changed_by: str, before_value: dict = None, 
                             after_value: dict = None, reason: str = None):
    log_entry = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "before_value": before_value,
        "after_value": after_value,
        "changed_by": changed_by,
        "reason": reason,
        "timestamp": get_malaysia_time().isoformat()
    }
    await db.finance_audit_log.insert_one(log_entry)


async def create_audit_trail_entry(
    action: str, record_reference: str, entity_type: str, entity_id: str,
    changed_by: User, reason: str, field_changed: str = None,
    from_value: str = None, to_value: str = None
):
    entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "record_reference": record_reference,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field_changed": field_changed,
        "from_value": from_value,
        "to_value": to_value,
        "changed_by_name": changed_by.full_name,
        "changed_by_email": changed_by.email,
        "reason": reason,
        "timestamp": get_malaysia_time().isoformat()
    }
    await db.audit_trail.insert_one(entry)
    return entry


# ============ COMPANY SETTINGS ============
@router.get("/company-settings")
async def get_company_settings(current_user: User = Depends(get_current_user)):
    """Get company settings for invoices/receipts"""
    has_marketing = "marketing" in (current_user.additional_roles or []) or current_user.role == "marketing"
    if current_user.role not in ["admin", "super_admin", "finance"] and not has_marketing:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.company_settings.find_one({"id": "company_settings"}, {"_id": 0})
    if not settings:
        settings = CompanySettings().model_dump()
        await db.company_settings.insert_one(settings)
    
    return settings


@router.put("/company-settings")
async def update_company_settings(settings_data: dict, current_user: User = Depends(get_current_user)):
    """Update company settings"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can update settings")
    
    settings_data["updated_at"] = get_malaysia_time().isoformat()
    settings_data["updated_by"] = current_user.id
    settings_data["id"] = "company_settings"
    
    await db.company_settings.update_one(
        {"id": "company_settings"},
        {"$set": settings_data},
        upsert=True
    )
    
    return {"message": "Settings updated successfully"}


@router.post("/company-settings/upload-logo")
async def upload_company_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload company logo for document headers"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can upload logo")
    
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only image files (PNG, JPG, JPEG, GIF, WEBP) are allowed")
    
    content = await file.read()
    
    upload_dir = "uploads/company"
    os.makedirs(upload_dir, exist_ok=True)
    
    timestamp = get_malaysia_time().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"company_logo_{timestamp}{file_ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    logo_url = f"/api/uploads/company/{safe_filename}"
    
    await db.company_settings.update_one(
        {"id": "company_settings"},
        {"$set": {
            "logo_url": logo_url,
            "logo_filename": file.filename,
            "updated_at": get_malaysia_time().isoformat(),
            "updated_by": current_user.id
        }},
        upsert=True
    )
    
    return {"message": "Logo uploaded successfully", "url": logo_url, "filename": file.filename}


@router.post("/company-settings/upload-indemnity-form")
async def upload_indemnity_form(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload custom indemnity form PDF"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can upload indemnity form")
    
    if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX files are allowed")
    
    content = await file.read()
    
    upload_dir = "uploads/company"
    os.makedirs(upload_dir, exist_ok=True)
    
    timestamp = get_malaysia_time().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1].lower()
    safe_filename = f"indemnity_form_{timestamp}{file_ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    form_url = f"/api/uploads/company/{safe_filename}"
    
    await db.company_settings.update_one(
        {"id": "company_settings"},
        {"$set": {
            "indemnity_form_url": form_url,
            "indemnity_form_filename": file.filename,
            "updated_at": get_malaysia_time().isoformat(),
            "updated_by": current_user.id
        }},
        upsert=True
    )
    
    return {"message": "Indemnity form uploaded successfully", "url": form_url, "filename": file.filename}


# ============ INCOME ENDPOINTS ============
@router.get("/income/trainer/{trainer_id}")
async def get_trainer_income(trainer_id: str, current_user: User = Depends(get_current_user)):
    """Get trainer income from all sessions"""
    if current_user.role == "trainer" and current_user.id != trainer_id:
        raise HTTPException(status_code=403, detail="Can only view your own income")
    
    if current_user.role not in ["admin", "super_admin", "finance", "trainer"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    records = await db.trainer_fees.find({"trainer_id": trainer_id}, {"_id": 0}).to_list(1000)
    
    valid_records = []
    for record in records:
        session = await db.sessions.find_one({"id": record.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "end_date": 1, "company_id": 1})
        if session:
            record["session_name"] = session.get("name")
            record["training_dates"] = f"{session.get('start_date')} to {session.get('end_date')}"
            record["start_date"] = session.get("start_date")
            if session.get("company_id"):
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
                record["company_name"] = company.get("name") if company else None
            record["amount"] = record.get("fee_amount", 0)
            valid_records.append(record)
        else:
            await db.trainer_fees.delete_one({"id": record.get("id")})
    
    total = sum(r.get("fee_amount", 0) for r in valid_records)
    paid = sum(r.get("fee_amount", 0) for r in valid_records if r.get("status") == "paid")
    
    return {"records": valid_records, "summary": {"total_income": total, "paid_income": paid, "pending_income": total - paid}}


@router.get("/income/coordinator/{coordinator_id}")
async def get_coordinator_income(coordinator_id: str, current_user: User = Depends(get_current_user)):
    """Get coordinator income from all sessions"""
    if current_user.role == "coordinator" and current_user.id != coordinator_id:
        if "coordinator" not in (current_user.additional_roles or []):
            raise HTTPException(status_code=403, detail="Can only view your own income")
    
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        if "coordinator" not in (current_user.additional_roles or []):
            raise HTTPException(status_code=403, detail="Access denied")
    
    records = await db.coordinator_fees.find({"coordinator_id": coordinator_id}, {"_id": 0}).to_list(1000)
    
    valid_records = []
    for record in records:
        session = await db.sessions.find_one({"id": record.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "end_date": 1, "company_id": 1})
        if session:
            record["session_name"] = session.get("name")
            record["training_dates"] = f"{session.get('start_date')} to {session.get('end_date')}"
            record["start_date"] = session.get("start_date")
            company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
            record["company_name"] = company.get("name") if company else None
            record["amount"] = record.get("total_fee", 0)
            valid_records.append(record)
        else:
            await db.coordinator_fees.delete_one({"id": record.get("id")})
    
    total = sum(r.get("total_fee", 0) for r in valid_records)
    paid = sum(r.get("total_fee", 0) for r in valid_records if r.get("status") == "paid")
    
    return {"records": valid_records, "summary": {"total_fees": total, "paid_fees": paid, "pending_fees": total - paid}}


@router.get("/income/marketing/{marketing_id}")
async def get_marketing_income(marketing_id: str, current_user: User = Depends(get_current_user)):
    """Get marketing income"""
    is_marketing = current_user.role == "marketing" or "marketing" in (current_user.additional_roles or [])
    
    if is_marketing and current_user.id != marketing_id:
        raise HTTPException(status_code=403, detail="Can only view your own income")
    
    if current_user.role not in ["admin", "super_admin", "finance", "marketing"]:
        if "marketing" not in (current_user.additional_roles or []):
            raise HTTPException(status_code=403, detail="Access denied")
    
    records = await db.marketing_commissions.find({"marketing_user_id": marketing_id}, {"_id": 0}).to_list(1000)
    
    valid_records = []
    for record in records:
        session = await db.sessions.find_one({"id": record.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "end_date": 1, "company_id": 1})
        if session:
            record["session_name"] = session.get("name")
            record["training_dates"] = f"{session.get('start_date')} to {session.get('end_date')}"
            record["start_date"] = session.get("start_date")
            company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
            record["company_name"] = company.get("name") if company else None
            valid_records.append(record)
        else:
            await db.marketing_commissions.delete_one({"id": record.get("id")})
    
    total = sum(r.get("calculated_amount", 0) for r in valid_records)
    paid = sum(r.get("calculated_amount", 0) for r in valid_records if r.get("status") == "paid")
    
    return {"records": valid_records, "summary": {"total_commission": total, "paid_commission": paid, "pending_commission": total - paid}}


# ============ MARK PAID ENDPOINTS ============
@router.post("/income/trainer/{record_id}/mark-paid")
async def mark_trainer_paid(record_id: str, current_user: User = Depends(get_current_user)):
    """Mark trainer income as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.trainer_income.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.trainer_income.update_one({"id": record_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id}})
    await log_finance_action("trainer_income", record_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Marked as paid"}


@router.post("/income/coordinator/{record_id}/mark-paid")
async def mark_coordinator_paid(record_id: str, current_user: User = Depends(get_current_user)):
    """Mark coordinator fee as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.coordinator_fees.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.coordinator_fees.update_one({"id": record_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id}})
    await log_finance_action("coordinator_fee", record_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Marked as paid"}


@router.post("/income/commission/{record_id}/mark-paid")
async def mark_commission_paid(record_id: str, current_user: User = Depends(get_current_user)):
    """Mark commission as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.marketing_commissions.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.marketing_commissions.update_one({"id": record_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}})
    await log_finance_action("marketing_commission", record_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Marked as paid"}


@router.post("/trainer-fees/{fee_id}/mark-paid")
async def mark_trainer_fee_paid(fee_id: str, current_user: User = Depends(get_current_user)):
    """Mark trainer fee as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.trainer_fees.find_one({"id": fee_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Fee record not found")
    
    await db.trainer_fees.update_one({"id": fee_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}})
    await log_finance_action("trainer_fee", fee_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Trainer fee marked as paid"}


@router.post("/coordinator-fees/{fee_id}/mark-paid")
async def mark_coordinator_fee_paid(fee_id: str, current_user: User = Depends(get_current_user)):
    """Mark coordinator fee as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.coordinator_fees.find_one({"id": fee_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Fee record not found")
    
    await db.coordinator_fees.update_one({"id": fee_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}})
    await log_finance_action("coordinator_fee", fee_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Coordinator fee marked as paid"}


# ============ PAYABLES MARK-PAID ENDPOINTS (Used by PayablesTab) ============
@router.post("/payables/trainer/{fee_id}/mark-paid")
async def mark_trainer_payable_paid(fee_id: str, current_user: User = Depends(get_current_user)):
    """Mark trainer fee as paid (payables endpoint)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.trainer_fees.find_one({"id": fee_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Fee record not found")
    
    await db.trainer_fees.update_one(
        {"id": fee_id}, 
        {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}}
    )
    await log_finance_action("trainer_fee", fee_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Trainer fee marked as paid"}


@router.post("/payables/coordinator/{fee_id}/mark-paid")
async def mark_coordinator_payable_paid(fee_id: str, current_user: User = Depends(get_current_user)):
    """Mark coordinator fee as paid (payables endpoint)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.coordinator_fees.find_one({"id": fee_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Fee record not found")
    
    await db.coordinator_fees.update_one(
        {"id": fee_id}, 
        {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}}
    )
    await log_finance_action("coordinator_fee", fee_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Coordinator fee marked as paid"}


@router.post("/payables/marketing/{record_id}/mark-paid")
async def mark_marketing_payable_paid(record_id: str, current_user: User = Depends(get_current_user)):
    """Mark marketing commission as paid (payables endpoint)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.marketing_commissions.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Commission record not found")
    
    await db.marketing_commissions.update_one(
        {"id": record_id}, 
        {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}}
    )
    await log_finance_action("marketing_commission", record_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Marketing commission marked as paid"}


# ============ PAYABLES PERIOD MANAGEMENT ============
@router.get("/payables/periods")
async def get_payables_periods(current_user: User = Depends(get_current_user)):
    """Get all payables periods with open/closed status"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    periods = await db.payables_periods.find({}, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return periods


@router.post("/payables/periods")
async def create_payables_period(period: PayablesPeriodCreate, current_user: User = Depends(get_current_user)):
    """Create a new payables period (opens it)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = await db.payables_periods.find_one({"year": period.year, "month": period.month}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Period already exists")
    
    now = get_malaysia_time()
    new_period = {
        "id": str(uuid.uuid4()),
        "year": period.year,
        "month": period.month,
        "status": "open",
        "opened_at": now.isoformat(),
        "opened_by": current_user.id,
        "created_at": now.isoformat()
    }
    
    await db.payables_periods.insert_one({**new_period, "_id": new_period["id"]})
    return new_period


@router.post("/payables/periods/{period_id}/close")
async def close_payables_period(period_id: str, current_user: User = Depends(get_current_user)):
    """Close a payables period - no more changes allowed after closing"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    period = await db.payables_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Period is already closed")
    
    now = get_malaysia_time()
    await db.payables_periods.update_one(
        {"id": period_id},
        {"$set": {"status": "closed", "closed_at": now.isoformat(), "closed_by": current_user.id, "updated_at": now.isoformat()}}
    )
    
    return {"message": "Period closed successfully"}


@router.post("/payables/periods/{period_id}/reopen")
async def reopen_payables_period(period_id: str, reason: str = "", current_user: User = Depends(get_current_user)):
    """Reopen a closed payables period - requires admin and reason"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can reopen periods")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    period = await db.payables_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.get("status") == "open":
        raise HTTPException(status_code=400, detail="Period is already open")
    
    now = get_malaysia_time()
    await db.payables_periods.update_one(
        {"id": period_id},
        {"$set": {"status": "open", "reopened_at": now.isoformat(), "reopened_by": current_user.id, "reopen_reason": reason, "updated_at": now.isoformat()}}
    )
    
    await create_audit_trail_entry(
        action="Payables Period Reopened",
        record_reference=f"{period['year']}-{str(period['month']).zfill(2)}",
        entity_type="payables_period",
        entity_id=period_id,
        changed_by=current_user,
        reason=reason,
        field_changed="status",
        from_value="closed",
        to_value="open"
    )
    
    return {"message": "Period reopened successfully"}


@router.get("/payables/period-status")
async def get_period_status(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Check if a specific period is open or closed"""
    period = await db.payables_periods.find_one({"year": year, "month": month}, {"_id": 0})
    if not period:
        return {"status": "open", "exists": False}
    return {"status": period.get("status", "open"), "exists": True, "period": period}


# ============ PAYABLES LIST ENDPOINTS ============
@router.get("/payables/trainer-fees")
async def get_pending_trainer_fees(current_user: User = Depends(get_current_user)):
    """Get all trainer fees (pending and paid)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "name": 1, "start_date": 1, "company_id": 1}).to_list(1000)
    session_map = {s["id"]: {"name": s["name"], "start_date": s.get("start_date"), "company_id": s.get("company_id")} for s in sessions}
    
    # Get companies for lookup
    companies = await db.companies.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
    company_map = {c["id"]: c["name"] for c in companies}
    
    fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(1000)
    
    result = []
    for fee in fees:
        if fee.get("session_id") not in session_map:
            await db.trainer_fees.delete_one({"id": fee.get("id")})
            continue
            
        session_info = session_map.get(fee.get("session_id"), {})
        trainer = await db.users.find_one({"id": fee.get("trainer_id")}, {"_id": 0, "full_name": 1})
        fee["trainer_name"] = trainer.get("full_name") if trainer else "Unknown"
        fee["session_name"] = session_info.get("name", "Unknown Session")
        fee["session_start_date"] = session_info.get("start_date")
        fee["company_name"] = company_map.get(session_info.get("company_id"), "Unknown Company")
        result.append(fee)
    
    return result


@router.get("/payables/coordinator-fees")
async def get_pending_coordinator_fees(current_user: User = Depends(get_current_user)):
    """Get all coordinator fees"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "name": 1, "start_date": 1, "company_id": 1}).to_list(1000)
    session_map = {s["id"]: {"name": s["name"], "start_date": s.get("start_date"), "company_id": s.get("company_id")} for s in sessions}
    
    # Get companies for lookup
    companies = await db.companies.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
    company_map = {c["id"]: c["name"] for c in companies}
    
    fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(1000)
    
    result = []
    for fee in fees:
        if fee.get("session_id") not in session_map:
            await db.coordinator_fees.delete_one({"id": fee.get("id")})
            continue
        
        session_info = session_map.get(fee.get("session_id"), {})
        coordinator = await db.users.find_one({"id": fee.get("coordinator_id")}, {"_id": 0, "full_name": 1})
        fee["coordinator_name"] = coordinator.get("full_name") if coordinator else "Unknown"
        fee["session_name"] = session_info.get("name", "Unknown Session")
        fee["session_start_date"] = session_info.get("start_date")
        fee["company_name"] = company_map.get(session_info.get("company_id"), "Unknown Company")
        result.append(fee)
    
    return result


@router.get("/payables/marketing-commissions")
async def get_pending_marketing_commissions(current_user: User = Depends(get_current_user)):
    """Get all marketing commissions - calculated on-the-fly to match Profit Summary"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "name": 1, "start_date": 1}).to_list(1000)
    session_map = {s["id"]: {"name": s["name"], "start_date": s.get("start_date")} for s in sessions}
    
    comms = await db.marketing_commissions.find({}, {"_id": 0}).to_list(1000)
    
    result = []
    for comm in comms:
        session_id = comm.get("session_id")
        if session_id not in session_map:
            await db.marketing_commissions.delete_one({"id": comm.get("id")})
            continue
        
        # FIX: Get ALL invoices for the session, not just one
        invoices = await db.invoices.find({"session_id": session_id}, {"_id": 0, "total_amount": 1, "tax_amount": 1}).to_list(100)
        invoice_total = sum(inv.get("total_amount", 0) for inv in invoices)
        tax_amount = sum(inv.get("tax_amount", 0) for inv in invoices)
        gross_revenue = invoice_total - tax_amount
        
        trainer_fees = await db.trainer_fees.find({"session_id": session_id}, {"_id": 0, "fee_amount": 1}).to_list(100)
        trainer_fees_total = sum(f.get("fee_amount", 0) for f in trainer_fees)
        
        # FIX: Get ALL coordinator fees, not just one
        coord_fees = await db.coordinator_fees.find({"session_id": session_id}, {"_id": 0, "total_fee": 1}).to_list(100)
        coordinator_fee_total = sum(cf.get("total_fee", 0) for cf in coord_fees)
        
        expenses = await db.session_expenses.find({"session_id": session_id}, {"_id": 0, "actual_amount": 1, "estimated_amount": 1}).to_list(100)
        cash_expenses_actual = sum(e.get("actual_amount", 0) for e in expenses)
        cash_expenses_estimated = sum(e.get("estimated_amount", 0) for e in expenses)
        cash_expenses = cash_expenses_actual if cash_expenses_actual > 0 else cash_expenses_estimated
        
        total_expenses_before_marketing = trainer_fees_total + coordinator_fee_total + cash_expenses
        profit_before_marketing = gross_revenue - total_expenses_before_marketing
        
        if comm.get("commission_type") == "percentage":
            calculated_amount = profit_before_marketing * (comm.get("commission_rate", 0) / 100)
        else:
            calculated_amount = comm.get("fixed_amount") or 0.0
        
        # Always update if there's a discrepancy
        if abs(calculated_amount - (comm.get("calculated_amount") or 0)) > 0.01:
            await db.marketing_commissions.update_one(
                {"id": comm.get("id")},
                {"$set": {"calculated_amount": calculated_amount, "updated_at": get_malaysia_time().isoformat()}}
            )
        
        user = await db.users.find_one({"id": comm.get("marketing_user_id")}, {"_id": 0, "full_name": 1})
        comm["marketing_user_name"] = user.get("full_name") if user else "Unknown"
        comm["session_name"] = session_map.get(session_id, {}).get("name", "Unknown Session")
        comm["session_start_date"] = session_map.get(session_id, {}).get("start_date")
        comm["calculated_amount"] = calculated_amount
        result.append(comm)
    
    return result


class RecalculateCommissionsRequest(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None
    session_id: Optional[str] = None


@router.post("/recalculate-commissions")
async def recalculate_marketing_commissions(
    request: RecalculateCommissionsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Admin endpoint to recalculate and fix historical marketing commission data.
    Can filter by year/month or specific session_id.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can recalculate commissions")
    
    # Build query for commissions to recalculate
    query = {}
    if request.session_id:
        query["session_id"] = request.session_id
    
    comms = await db.marketing_commissions.find(query, {"_id": 0}).to_list(1000)
    
    updated_records = []
    skipped_records = []
    
    for comm in comms:
        session_id = comm.get("session_id")
        
        # Check session exists
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0, "name": 1, "start_date": 1})
        if not session:
            skipped_records.append({"id": comm.get("id"), "reason": "Session not found"})
            continue
        
        # Filter by year/month if specified
        if request.year or request.month:
            start_date = session.get("start_date", "")
            if start_date:
                try:
                    date_parts = start_date.split("-")
                    session_year = int(date_parts[0])
                    session_month = int(date_parts[1])
                    
                    if request.year and session_year != request.year:
                        continue
                    if request.month and session_month != request.month:
                        continue
                except:
                    pass
        
        # Calculate correct commission based on ALL invoices
        invoices = await db.invoices.find({"session_id": session_id}, {"_id": 0, "total_amount": 1, "tax_amount": 1}).to_list(100)
        invoice_total = sum(inv.get("total_amount", 0) for inv in invoices)
        tax_amount = sum(inv.get("tax_amount", 0) for inv in invoices)
        gross_revenue = invoice_total - tax_amount
        
        trainer_fees = await db.trainer_fees.find({"session_id": session_id}, {"_id": 0, "fee_amount": 1}).to_list(100)
        trainer_fees_total = sum(f.get("fee_amount", 0) for f in trainer_fees)
        
        coord_fees = await db.coordinator_fees.find({"session_id": session_id}, {"_id": 0, "total_fee": 1}).to_list(100)
        coordinator_fee_total = sum(cf.get("total_fee", 0) for cf in coord_fees)
        
        expenses = await db.session_expenses.find({"session_id": session_id}, {"_id": 0, "actual_amount": 1, "estimated_amount": 1}).to_list(100)
        cash_expenses_actual = sum(e.get("actual_amount", 0) for e in expenses)
        cash_expenses_estimated = sum(e.get("estimated_amount", 0) for e in expenses)
        cash_expenses = cash_expenses_actual if cash_expenses_actual > 0 else cash_expenses_estimated
        
        total_expenses_before_marketing = trainer_fees_total + coordinator_fee_total + cash_expenses
        profit_before_marketing = gross_revenue - total_expenses_before_marketing
        
        if comm.get("commission_type") == "percentage":
            new_amount = profit_before_marketing * (comm.get("commission_rate", 0) / 100)
        else:
            new_amount = comm.get("fixed_amount") or 0.0
        
        old_amount = comm.get("calculated_amount", 0)
        
        # Update the record
        await db.marketing_commissions.update_one(
            {"id": comm.get("id")},
            {"$set": {
                "calculated_amount": new_amount,
                "updated_at": get_malaysia_time().isoformat(),
                "recalculated_by": current_user.id,
                "recalculated_at": get_malaysia_time().isoformat()
            }}
        )
        
        # Log the change
        await log_finance_action(
            "marketing_commission",
            comm.get("id"),
            "recalculated",
            current_user.id,
            {"calculated_amount": old_amount},
            {"calculated_amount": new_amount},
            f"Recalculated commission: {len(invoices)} invoices, gross={gross_revenue}, profit={profit_before_marketing}"
        )
        
        updated_records.append({
            "id": comm.get("id"),
            "session_name": session.get("name"),
            "old_amount": old_amount,
            "new_amount": new_amount,
            "difference": new_amount - old_amount,
            "invoices_count": len(invoices),
            "gross_revenue": gross_revenue,
            "profit_before_marketing": profit_before_marketing
        })
    
    return {
        "message": f"Recalculated {len(updated_records)} commission records",
        "updated": updated_records,
        "skipped": skipped_records
    }


# ============ EXPENSE CATEGORIES ============
@router.get("/expense-categories")
async def get_expense_categories(current_user: User = Depends(get_current_user)):
    """Get list of expense categories with their calculation types and rates"""
    return [
        {"id": "fnb", "name": "F&B", "type": "per_pax", "rate": 25, "description": "RM 25 per pax (auto-calculated)"},
        {"id": "hrdc_levy", "name": "HRDCorp Levy", "type": "percentage", "rate": 4, "description": "4% of invoice"},
        {"id": "wear_tear", "name": "Wear and Tear", "type": "percentage", "rate": 2, "description": "2% of invoice"},
        {"id": "printing", "name": "Printing", "type": "percentage", "rate": 1, "description": "1% of invoice"},
        {"id": "accommodation", "name": "Accommodation", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "allowance", "name": "Allowance", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "petrol", "name": "Petrol", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "toll", "name": "Toll / Touch N Go", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "sst", "name": "SST", "type": "percentage", "rate": 0, "description": "Custom percentage"},
        {"id": "muafakat", "name": "Muafakat", "type": "percentage", "rate": 0, "description": "Custom percentage"},
        {"id": "other", "name": "Other Expenses", "type": "fixed", "rate": 0, "description": "Fixed amount"}
    ]


# ============ MARKETING USERS ============
@router.get("/marketing-users")
async def get_marketing_users(current_user: User = Depends(get_current_user)):
    """Get list of users who can be assigned as marketing (all staff members)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    marketing_users = await db.users.find(
        {"role": {"$in": ["marketing", "coordinator", "trainer", "assistant_admin"]}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1, "additional_roles": 1, "id_number": 1}
    ).to_list(100)
    
    return marketing_users


# ============ FINANCE DASHBOARD ============
@router.get("/dashboard")
async def get_finance_dashboard(year: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get finance dashboard with optional year filter"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    def get_date_year(date_val):
        if not date_val:
            return None
        if isinstance(date_val, str):
            try:
                return datetime.fromisoformat(date_val.replace('Z', '+00:00')).year
            except:
                try:
                    return int(date_val[:4])
                except:
                    return None
        elif hasattr(date_val, 'year'):
            return date_val.year
        return None
    
    all_invoices_raw = await db.invoices.find({}, {"_id": 0}).to_list(5000)
    
    if year:
        invoices_for_year = [inv for inv in all_invoices_raw if get_date_year(inv.get("invoice_date") or inv.get("created_at")) == year]
    else:
        invoices_for_year = all_invoices_raw
    
    total_invoices = len(invoices_for_year)
    draft_invoices = len([inv for inv in invoices_for_year if inv.get("status") in ["auto_draft", "finance_review"]])
    approved_invoices = len([inv for inv in invoices_for_year if inv.get("status") == "approved"])
    issued_invoices = len([inv for inv in invoices_for_year if inv.get("status") == "issued"])
    paid_invoices = len([inv for inv in invoices_for_year if inv.get("status") == "paid"])
    
    financial_invoices = [inv for inv in invoices_for_year if inv.get("status") in ["issued", "paid"]]
    total_issued_amount = sum(inv.get("total_amount", 0) for inv in financial_invoices)
    total_collected = sum(inv.get("total_amount", 0) for inv in financial_invoices if inv.get("status") == "paid")
    
    pending_trainer_all = await db.trainer_fees.find({"status": {"$ne": "paid"}}, {"_id": 0, "fee_amount": 1, "created_at": 1, "session_start_date": 1}).to_list(1000)
    pending_coord_all = await db.coordinator_fees.find({"status": {"$ne": "paid"}}, {"_id": 0, "total_fee": 1, "created_at": 1, "session_start_date": 1}).to_list(1000)
    pending_comm_all = await db.marketing_commissions.find({"status": {"$in": ["pending", "approved"]}}, {"_id": 0, "calculated_amount": 1, "created_at": 1, "session_start_date": 1}).to_list(1000)
    
    if year:
        pending_trainer = [r for r in pending_trainer_all if get_date_year(r.get("session_start_date") or r.get("created_at")) == year]
        pending_coord = [r for r in pending_coord_all if get_date_year(r.get("session_start_date") or r.get("created_at")) == year]
        pending_comm = [r for r in pending_comm_all if get_date_year(r.get("session_start_date") or r.get("created_at")) == year]
    else:
        pending_trainer = pending_trainer_all
        pending_coord = pending_coord_all
        pending_comm = pending_comm_all
    
    total_pending = sum(r.get("fee_amount", 0) for r in pending_trainer) + sum(r.get("total_fee", 0) for r in pending_coord) + sum(r.get("calculated_amount", 0) for r in pending_comm)
    
    available_years = set()
    for inv in all_invoices_raw:
        inv_year = get_date_year(inv.get("invoice_date") or inv.get("created_at"))
        if inv_year:
            available_years.add(inv_year)
    
    return {
        "invoices": {"total": total_invoices, "draft": draft_invoices, "approved": approved_invoices, "issued": issued_invoices, "paid": paid_invoices},
        "financials": {"total_issued": total_issued_amount, "total_collected": total_collected, "outstanding_receivables": total_issued_amount - total_collected},
        "payables": {"pending_total": total_pending},
        "available_years": sorted(list(available_years), reverse=True),
        "selected_year": year
    }


# ============ AUDIT LOG ============
@router.get("/audit-log")
async def get_audit_log(entity_type: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 100, current_user: User = Depends(get_current_user)):
    """Get audit log"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    
    logs = await db.finance_audit_log.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    result = []
    for log in logs:
        user = await db.users.find_one({"id": log.get("changed_by")}, {"_id": 0, "full_name": 1})
        log_dict = {
            "id": log.get("id"),
            "entity_type": log.get("entity_type"),
            "entity_id": log.get("entity_id"),
            "action": log.get("action"),
            "changed_by": log.get("changed_by"),
            "changed_by_name": user.get("full_name") if user else "Unknown",
            "timestamp": log.get("timestamp"),
            "before_value": str(log.get("before_value", "")) if log.get("before_value") else None,
            "after_value": str(log.get("after_value", "")) if log.get("after_value") else None,
            "remark": log.get("remark")
        }
        result.append(log_dict)
    
    return result
