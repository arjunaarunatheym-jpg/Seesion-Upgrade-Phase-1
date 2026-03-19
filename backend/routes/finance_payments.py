"""
Finance Payments & Credit Notes routes
Stage F3: ~18 endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import uuid
import pytz

from core import db, get_current_user, get_malaysia_time
from models import User
from utils.email_notifications import notify_payment_received as notify_payment_received_email

# Import accounting auto-posting functions (Phase 2)
from routes.accounting import post_payment_received, post_credit_note_issued

router = APIRouter(prefix="/finance", tags=["finance-payments"])

MALAYSIA_TZ = pytz.timezone("Asia/Kuala_Lumpur")


# ============ MODELS ============
class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float
    payment_date: str
    payment_method: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    create_credit_note: Optional[bool] = False
    deduction_percentage: Optional[float] = None
    deduction_amount: Optional[float] = None
    deduction_reason: Optional[str] = None


class BackdateCreditNoteRequest(BaseModel):
    new_date: str
    reason: str


class EditCreditNoteRequest(BaseModel):
    company_name: Optional[str] = None
    reason: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    percentage: Optional[float] = None
    edit_reason: str


class DeletePaymentRequest(BaseModel):
    reason: str


# ============ HELPER FUNCTIONS ============
async def generate_credit_note_number():
    """Generate unique credit note number: CN/MDDRC/YYYY/MM/0001"""
    now = get_malaysia_time()
    year = now.year
    month = now.month
    prefix = f"CN/MDDRC/{year}/{month:02d}/"
    
    last_cn = await db.credit_notes.find_one(
        {"cn_number": {"$regex": f"^CN/MDDRC/{year}/{month:02d}/"}},
        sort=[("cn_number", -1)]
    )
    
    if last_cn:
        last_num = int(last_cn["cn_number"].split("/")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"{prefix}{new_num:04d}"


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


# ============ PAYMENT ENDPOINTS ============
@router.get("/payments")
async def get_payments(current_user: User = Depends(get_current_user)):
    """Get all payments"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    payments = await db.payments.find({}, {"_id": 0}).sort("payment_date", -1).to_list(100)
    
    for payment in payments:
        if payment.get("invoice_id"):
            invoice = await db.invoices.find_one({"id": payment["invoice_id"]}, {"_id": 0, "invoice_number": 1, "company_name": 1})
            if invoice:
                payment["invoice_number"] = invoice.get("invoice_number")
                payment["company_name"] = invoice.get("company_name")
    
    return payments


@router.post("/payments")
async def record_payment(payment_data: PaymentCreate, current_user: User = Depends(get_current_user)):
    """Record payment"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can record payments")
    
    invoice = await db.invoices.find_one({"id": payment_data.invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") not in ["issued", "paid"]:
        raise HTTPException(status_code=400, detail="Can only record payments for issued invoices")
    
    payment = {
        "id": str(uuid.uuid4()),
        "invoice_id": payment_data.invoice_id,
        "amount": payment_data.amount,
        "payment_date": payment_data.payment_date,
        "payment_method": payment_data.payment_method,
        "reference_number": payment_data.reference_number,
        "notes": payment_data.notes,
        "recorded_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.payments.insert_one(payment)
    payment.pop("_id", None)
    
    # ============ CREATE CREDIT NOTE IF REQUESTED ============
    credit_note_created = None
    if payment_data.create_credit_note and (payment_data.deduction_percentage or payment_data.deduction_amount):
        try:
            if payment_data.deduction_amount and payment_data.deduction_amount > 0:
                deduction_amount = payment_data.deduction_amount
                deduction_percentage = (deduction_amount / invoice.get("total_amount", 1)) * 100
            elif payment_data.deduction_percentage and payment_data.deduction_percentage > 0:
                deduction_percentage = payment_data.deduction_percentage
                deduction_amount = (invoice.get("total_amount", 0) * deduction_percentage) / 100
            else:
                deduction_amount = 0
                deduction_percentage = 0
            
            if deduction_amount > 0:
                now = get_malaysia_time()
                year = now.year
                month = now.month
                last_cn = await db.credit_notes.find_one(
                    {"cn_number": {"$regex": f"^CN/MDDRC/{year}/{month:02d}/"}},
                    sort=[("cn_number", -1)]
                )
                if last_cn:
                    last_num = int(last_cn["cn_number"].split("/")[-1])
                    cn_number = f"CN/MDDRC/{year}/{month:02d}/{str(last_num + 1).zfill(4)}"
                else:
                    cn_number = f"CN/MDDRC/{year}/{month:02d}/0001"
                
                credit_note = {
                    "id": str(uuid.uuid4()),
                    "cn_number": cn_number,
                    "invoice_id": payment_data.invoice_id,
                    "invoice_number": invoice.get("invoice_number"),
                    "session_id": invoice.get("session_id"),
                    "session_name": invoice.get("session_name") or invoice.get("programme_name"),
                    "company_id": invoice.get("company_id"),
                    "company_name": invoice.get("bill_to_name") or invoice.get("company_name"),
                    "bill_to_name": invoice.get("bill_to_name"),
                    "bill_to_address": invoice.get("bill_to_address"),
                    "reason": payment_data.deduction_reason or "HRDCorp Levy Deduction",
                    "description": f"{deduction_percentage:.1f}% deduction",
                    "base_amount": invoice.get("total_amount", 0),
                    "percentage": deduction_percentage,
                    "amount": round(deduction_amount, 2),
                    "status": "draft",
                    "created_by": current_user.id,
                    "created_at": get_malaysia_time().isoformat(),
                    "cn_date": payment_data.payment_date
                }
                
                await db.credit_notes.insert_one(credit_note)
                credit_note.pop("_id", None)
                credit_note_created = credit_note
                
                await log_finance_action("credit_note", credit_note["id"], "created", current_user.id, after_value=credit_note)
                
                # Auto-post credit note to journal
                try:
                    await post_credit_note_issued(
                        credit_note=credit_note,
                        invoice=invoice,
                        user_id=current_user.id,
                        user_name=current_user.full_name
                    )
                except Exception as e:
                    print(f"Credit note accounting auto-post error: {str(e)}")
        except Exception as e:
            print(f"Error creating credit note: {e}")
    # ============ END CREDIT NOTE ============
    
    all_payments = await db.payments.find({"invoice_id": payment_data.invoice_id}, {"_id": 0}).to_list(100)
    total_paid = sum(p.get("amount", 0) for p in all_payments)
    
    if total_paid >= invoice.get("total_amount", 0):
        await db.invoices.update_one({"id": payment_data.invoice_id}, {"$set": {"status": "paid", "updated_at": get_malaysia_time().isoformat()}})
        await db.sessions.update_one({"invoice_id": payment_data.invoice_id}, {"$set": {"invoice_status": "paid"}})
    
    await log_finance_action("payment", payment["id"], "created", current_user.id, after_value=payment)
    
    # ============ ACCOUNTING AUTO-POST (Phase 2) ============
    # Create journal entry for payment received
    try:
        accounting_result = await post_payment_received(
            payment=payment,
            invoice=invoice,
            user_id=current_user.id,
            user_name=current_user.full_name
        )
        if accounting_result.get("error"):
            print(f"Accounting auto-post warning: {accounting_result.get('error')}")
    except Exception as e:
        print(f"Accounting auto-post error: {str(e)}")
    # ============ END ACCOUNTING AUTO-POST ============
    
    # ============ EMAIL NOTIFICATION ============
    try:
        await notify_payment_received_email(payment, invoice)
    except Exception as e:
        print(f"Payment notification error: {str(e)}")
    # ============ END EMAIL NOTIFICATION ============
    
    result = {**payment}
    if credit_note_created:
        result["credit_note"] = credit_note_created
    return result


@router.get("/payments/{payment_id}/receipt")
async def get_receipt_data(payment_id: str, current_user: User = Depends(get_current_user)):
    """Get receipt data for printing"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    invoice = await db.invoices.find_one({"id": payment.get("invoice_id")}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    settings = await db.company_settings.find_one({"id": "company_settings"}, {"_id": 0})
    if not settings:
        settings = {"company_name": "MDDRC SDN BHD"}
    
    receipt_count = await db.payments.count_documents({})
    year = get_malaysia_time().year
    month = get_malaysia_time().month
    receipt_number = f"RCP/{year}/{month:02d}/{receipt_count:04d}"
    
    return {
        "receipt_number": receipt_number,
        "payment": payment,
        "invoice": invoice,
        "company_settings": settings
    }


@router.get("/admin/payments")
async def get_admin_payments(
    invoice_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all payments for admin management"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can access")
    
    query = {}
    if invoice_id:
        query["invoice_id"] = invoice_id
    
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    for payment in payments:
        invoice = await db.invoices.find_one({"id": payment.get("invoice_id")}, {"_id": 0})
        if invoice:
            payment["invoice_number"] = invoice.get("invoice_number")
            payment["company_name"] = invoice.get("company_name")
    
    return payments


@router.delete("/admin/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    request: DeletePaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Delete a payment record"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can delete payments")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    invoice = await db.invoices.find_one({"id": payment.get("invoice_id")}, {"_id": 0})
    company_name = invoice.get("company_name", "Unknown") if invoice else "Unknown"
    
    record_ref = f"{company_name} - RM {payment.get('amount', 0):,.2f} ({payment.get('payment_method', 'Unknown')})"
    
    await create_audit_trail_entry(
        action="Payment Deleted",
        record_reference=record_ref,
        entity_type="payment",
        entity_id=payment_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="deleted",
        from_value=f"RM {payment.get('amount', 0):,.2f}",
        to_value="Deleted"
    )
    
    await db.payments.delete_one({"id": payment_id})
    
    if invoice and invoice.get("status") == "paid":
        remaining_payments = await db.payments.count_documents({"invoice_id": invoice["id"]})
        if remaining_payments == 0:
            await db.invoices.update_one(
                {"id": invoice["id"]},
                {"$set": {"status": "issued", "updated_at": get_malaysia_time().isoformat()}}
            )
    
    return {"message": "Payment deleted successfully"}


# ============ CREDIT NOTE ENDPOINTS ============
@router.get("/credit-notes")
async def get_credit_notes(current_user: User = Depends(get_current_user)):
    """Get all credit notes"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    credit_notes = await db.credit_notes.find({}, {"_id": 0}).to_list(1000)
    return credit_notes


@router.post("/credit-notes")
async def create_credit_note(cn_data: dict, current_user: User = Depends(get_current_user)):
    """Create a credit note (e.g., for HRDCorp 4% deduction)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    invoice_id = cn_data.get("invoice_id")
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0}) if invoice_id else None
    
    now = get_malaysia_time()
    cn_number = await generate_credit_note_number()
    
    credit_note = {
        "id": str(uuid.uuid4()),
        "cn_number": cn_number,
        "invoice_id": invoice_id,
        "invoice_number": invoice.get("invoice_number") if invoice else None,
        "session_id": cn_data.get("session_id"),
        "company_id": cn_data.get("company_id") or (invoice.get("company_id") if invoice else None),
        "company_name": cn_data.get("company_name") or (invoice.get("company_name") if invoice else None),
        "reason": cn_data.get("reason", "HRDCorp Levy Deduction"),
        "description": cn_data.get("description", "4% HRDCorp levy deducted from payment"),
        "amount": float(cn_data.get("amount", 0)),
        "percentage": float(cn_data.get("percentage", 4)),
        "status": "draft",
        "created_by": current_user.id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.insert_one(credit_note)
    await log_finance_action("credit_note", credit_note["id"], "created", current_user.id, after_value=credit_note)
    
    return {"message": "Credit note created", "cn_number": cn_number, "id": credit_note["id"]}


@router.get("/credit-notes/{cn_id}")
async def get_credit_note(cn_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific credit note"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    return credit_note


@router.put("/credit-notes/{cn_id}")
async def update_credit_note(cn_id: str, update_data: dict, current_user: User = Depends(get_current_user)):
    """Update a credit note"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can update credit notes")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") == "approved":
        raise HTTPException(status_code=400, detail="Cannot modify approved credit note")
    
    allowed_fields = ["reason", "description", "amount", "percentage", "status"]
    update_dict = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}
    update_dict["updated_at"] = get_malaysia_time().isoformat()
    
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    await log_finance_action("credit_note", cn_id, "updated", current_user.id, credit_note, update_dict)
    
    return await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})


@router.post("/credit-notes/{cn_id}/approve")
async def approve_credit_note(cn_id: str, current_user: User = Depends(get_current_user)):
    """Approve a credit note"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can approve credit notes")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft credit notes can be approved")
    
    now = get_malaysia_time()
    update_dict = {
        "status": "approved",
        "approved_by": current_user.id,
        "approved_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    await log_finance_action("credit_note", cn_id, "approved", current_user.id, credit_note, update_dict)
    
    return {"message": "Credit note approved", "cn_number": credit_note.get("cn_number")}


@router.post("/credit-notes/{cn_id}/issue")
async def issue_credit_note(cn_id: str, current_user: User = Depends(get_current_user)):
    """Issue a credit note"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can issue credit notes")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") not in ["draft", "approved"]:
        raise HTTPException(status_code=400, detail="Credit note must be draft or approved to be issued")
    
    now = get_malaysia_time()
    update_dict = {
        "status": "issued",
        "issued_by": current_user.id,
        "issued_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    await log_finance_action("credit_note", cn_id, "issued", current_user.id, credit_note, update_dict)
    
    # ============ ACCOUNTING AUTO-POST (Phase 2) ============
    # Create journal entry for credit note issued
    try:
        updated_cn = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
        accounting_result = await post_credit_note_issued(
            credit_note=updated_cn,
            user_id=current_user.id,
            user_name=current_user.full_name
        )
        if accounting_result.get("error"):
            print(f"Accounting auto-post warning: {accounting_result.get('error')}")
    except Exception as e:
        print(f"Accounting auto-post error: {str(e)}")
    # ============ END ACCOUNTING AUTO-POST ============
    
    return {"message": "Credit note issued", "cn_number": credit_note.get("cn_number")}


@router.post("/session/{session_id}/credit-note")
async def create_session_credit_note(session_id: str, cn_data: dict, current_user: User = Depends(get_current_user)):
    """Create a credit note for a session (typically for HRDCorp deduction)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    invoice = await db.invoices.find_one({"session_id": session_id}, {"_id": 0})
    company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
    
    percentage = float(cn_data.get("percentage", 4))
    base_amount = float(cn_data.get("base_amount", invoice.get("total_amount", 0) if invoice else 0))
    cn_amount = float(cn_data.get("amount", 0)) or (base_amount * percentage / 100)
    
    now = get_malaysia_time()
    cn_number = await generate_credit_note_number()
    
    credit_note = {
        "id": str(uuid.uuid4()),
        "cn_number": cn_number,
        "invoice_id": invoice.get("id") if invoice else None,
        "invoice_number": invoice.get("invoice_number") if invoice else None,
        "session_id": session_id,
        "session_name": session.get("name"),
        "company_id": session.get("company_id"),
        "company_name": company.get("name") if company else None,
        "reason": cn_data.get("reason", "HRDCorp Levy Deduction"),
        "description": cn_data.get("description", f"{percentage}% HRDCorp levy deducted from payment"),
        "base_amount": base_amount,
        "percentage": percentage,
        "amount": cn_amount,
        "status": "draft",
        "created_by": current_user.id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.insert_one(credit_note)
    await log_finance_action("credit_note", credit_note["id"], "created", current_user.id, after_value=credit_note)
    
    return {"message": "Credit note created", "cn_number": cn_number, "id": credit_note["id"], "amount": cn_amount}


# ============ ADMIN CREDIT NOTE ENDPOINTS ============
@router.put("/admin/credit-notes/{cn_id}/backdate")
async def backdate_credit_note(
    cn_id: str,
    request: BackdateCreditNoteRequest,
    current_user: User = Depends(get_current_user)
):
    """Backdate a credit note"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can backdate credit notes")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    company_name = credit_note.get("company_name", "Unknown")
    amount = credit_note.get("amount", 0)
    record_ref = f"{credit_note.get('cn_number')} - {company_name} - RM {amount:,.2f}"
    
    old_created_at = credit_note.get("created_at")
    if isinstance(old_created_at, datetime):
        old_date = old_created_at.strftime("%Y-%m-%d")
    elif isinstance(old_created_at, str):
        old_date = old_created_at[:10]
    else:
        old_date = "Unknown"
    
    try:
        new_datetime = datetime.strptime(request.new_date, "%Y-%m-%d")
        new_datetime = new_datetime.replace(tzinfo=MALAYSIA_TZ)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    await create_audit_trail_entry(
        action="Credit Note Backdated",
        record_reference=record_ref,
        entity_type="credit_note",
        entity_id=cn_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="created_at",
        from_value=old_date,
        to_value=request.new_date
    )
    
    await db.credit_notes.update_one(
        {"id": cn_id},
        {"$set": {
            "created_at": new_datetime.isoformat(),
            "cn_date": request.new_date,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Credit note backdated successfully", "old_date": old_date, "new_date": request.new_date}


@router.put("/admin/credit-notes/{cn_id}/edit")
async def edit_credit_note_admin(
    cn_id: str,
    request: EditCreditNoteRequest,
    current_user: User = Depends(get_current_user)
):
    """Edit credit note details with audit trail"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can edit credit notes")
    
    if not request.edit_reason or len(request.edit_reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Edit reason is required (minimum 5 characters)")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    record_ref = f"{credit_note.get('cn_number')} - {credit_note.get('company_name', 'Unknown')}"
    
    update_dict = {"updated_at": get_malaysia_time().isoformat()}
    changes = []
    
    if request.company_name is not None and request.company_name != credit_note.get("company_name"):
        changes.append(("company_name", credit_note.get("company_name"), request.company_name))
        update_dict["company_name"] = request.company_name
    
    if request.reason is not None and request.reason != credit_note.get("reason"):
        changes.append(("reason", credit_note.get("reason"), request.reason))
        update_dict["reason"] = request.reason
    
    if request.description is not None and request.description != credit_note.get("description"):
        changes.append(("description", credit_note.get("description"), request.description))
        update_dict["description"] = request.description
    
    if request.amount is not None and request.amount != credit_note.get("amount"):
        changes.append(("amount", str(credit_note.get("amount")), str(request.amount)))
        update_dict["amount"] = request.amount
    
    if request.percentage is not None and request.percentage != credit_note.get("percentage"):
        changes.append(("percentage", str(credit_note.get("percentage")), str(request.percentage)))
        update_dict["percentage"] = request.percentage
    
    if not changes:
        return {"message": "No changes detected"}
    
    for field, from_val, to_val in changes:
        await create_audit_trail_entry(
            action="Credit Note Edited",
            record_reference=record_ref,
            entity_type="credit_note",
            entity_id=cn_id,
            changed_by=current_user,
            reason=request.edit_reason,
            field_changed=field,
            from_value=str(from_val) if from_val else "",
            to_value=str(to_val) if to_val else ""
        )
    
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    
    return {"message": "Credit note updated successfully", "changes": len(changes)}


@router.put("/admin/credit-notes/{cn_id}/void")
async def void_credit_note(
    cn_id: str,
    reason: str = "",
    current_user: User = Depends(get_current_user)
):
    """Void a credit note"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can void credit notes")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") == "voided":
        raise HTTPException(status_code=400, detail="Credit note is already voided")
    
    record_ref = f"{credit_note.get('cn_number')} - {credit_note.get('company_name', 'Unknown')}"
    
    await create_audit_trail_entry(
        action="Credit Note Voided",
        record_reference=record_ref,
        entity_type="credit_note",
        entity_id=cn_id,
        changed_by=current_user,
        reason=reason,
        field_changed="status",
        from_value=credit_note.get("status"),
        to_value="voided"
    )
    
    await db.credit_notes.update_one(
        {"id": cn_id},
        {"$set": {
            "status": "voided",
            "voided_by": current_user.id,
            "voided_at": get_malaysia_time().isoformat(),
            "void_reason": reason,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Credit note voided successfully"}


@router.put("/admin/credit-notes/{cn_id}/number")
async def edit_credit_note_number(
    cn_id: str,
    year: int,
    month: int,
    sequence: int,
    reason: str = "",
    current_user: User = Depends(get_current_user)
):
    """Edit credit note number"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can edit credit note numbers")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    old_number = credit_note.get("cn_number")
    new_number = f"CN/MDDRC/{year}/{str(month).zfill(2)}/{str(sequence).zfill(4)}"
    
    existing = await db.credit_notes.find_one({"cn_number": new_number, "id": {"$ne": cn_id}}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail=f"Credit note number {new_number} already exists")
    
    record_ref = f"{old_number} → {new_number}"
    
    await create_audit_trail_entry(
        action="Credit Note Number Changed",
        record_reference=record_ref,
        entity_type="credit_note",
        entity_id=cn_id,
        changed_by=current_user,
        reason=reason,
        field_changed="cn_number",
        from_value=old_number,
        to_value=new_number
    )
    
    await db.credit_notes.update_one(
        {"id": cn_id},
        {"$set": {
            "cn_number": new_number,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Credit note number updated successfully", "old_number": old_number, "new_number": new_number}
