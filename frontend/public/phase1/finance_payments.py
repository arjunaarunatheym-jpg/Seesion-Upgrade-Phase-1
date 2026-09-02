"""
Finance Payments & Credit Notes routes
Stage F3: ~18 endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import csv
import io
import math
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
    receipt_url: Optional[str] = None  # Optional proof-of-payment image (base64 data URL)
    # NEW: Payment type & HRDCorp fields
    payment_type: Optional[str] = "self_pay"  # "self_pay" | "hrdcorp" | "partial" | "other"
    hrdcorp_service_fee: Optional[float] = None
    hrdcorp_invoice_number: Optional[str] = None
    hrdcorp_invoice_date: Optional[str] = None
    hrdcorp_invoice_url: Optional[str] = None  # base64 data URL
    # Legacy CN flow (kept for backward compatibility)
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
async def generate_receipt_number():
    """Generate unique receipt number: RCP/YYYY/MM/0001"""
    now = get_malaysia_time()
    year = now.year
    month = now.month
    prefix = f"RCP/{year}/{month:02d}/"

    last_receipt = await db.payments.find_one(
        {"receipt_number": {"$regex": f"^RCP/{year}/{month:02d}/"}},
        sort=[("receipt_number", -1)]
    )

    if last_receipt and last_receipt.get("receipt_number"):
        last_num = int(last_receipt["receipt_number"].split("/")[-1])
        new_num = last_num + 1
    else:
        new_num = 1

    return f"{prefix}{new_num:04d}"


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
    """Get all payments. Strips multi-MB base64 fields from list response — clients
    must call /payments/{id}/proof or /payments/{id}/hrdcorp-invoice to view them."""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Project away the heavy base64 blobs from list responses
    payments = await db.payments.find(
        {},
        {"_id": 0, "receipt_url": 0, "hrdcorp_invoice_url": 0}
    ).sort("payment_date", -1).to_list(100)
    
    for payment in payments:
        # Add boolean indicators so the UI can show "view proof" / "view HRDCorp invoice" buttons
        # We need a separate exists-check because find() with projection 0 means we never saw the field.
        payment["has_receipt"] = False
        payment["has_hrdcorp_invoice"] = False
        if payment.get("invoice_id"):
            invoice = await db.invoices.find_one({"id": payment["invoice_id"]}, {"_id": 0, "invoice_number": 1, "company_name": 1})
            if invoice:
                payment["invoice_number"] = invoice.get("invoice_number")
                payment["company_name"] = invoice.get("company_name")

    # Single bulk query for which payments have which attachments
    payment_ids = [p["id"] for p in payments if p.get("id")]
    if payment_ids:
        with_receipt = await db.payments.find(
            {"id": {"$in": payment_ids}, "receipt_url": {"$exists": True, "$nin": [None, ""]}},
            {"_id": 0, "id": 1}
        ).to_list(len(payment_ids))
        with_hrd_inv = await db.payments.find(
            {"id": {"$in": payment_ids}, "hrdcorp_invoice_url": {"$exists": True, "$nin": [None, ""]}},
            {"_id": 0, "id": 1}
        ).to_list(len(payment_ids))
        receipt_set = {p["id"] for p in with_receipt}
        hrd_set = {p["id"] for p in with_hrd_inv}
        for p in payments:
            p["has_receipt"] = p["id"] in receipt_set
            p["has_hrdcorp_invoice"] = p["id"] in hrd_set
    
    return payments


# ============ PAYMENT HISTORY (Phase 1) ============
# Server-side searchable / filterable / paginated read-only history view.
# Existing GET /payments is preserved for the "Recent Payments" dashboard widget.
PAYMENT_HISTORY_MAX_PAGE_SIZE = 100
PAYMENT_HISTORY_ALLOWED_SORTS = {
    "newest": [("payment_date", -1), ("created_at", -1)],
    "oldest": [("payment_date", 1), ("created_at", 1)],
    "highest": [("amount", -1), ("payment_date", -1)],
    "lowest": [("amount", 1), ("payment_date", -1)],
}

# CSV formula-injection sanitization.
# Spreadsheet apps (Excel / Google Sheets / LibreOffice) may interpret a cell
# beginning with '=', '+', '-' or '@' as a formula. When exporting user- or
# DB-derived TEXTUAL values, prefix such values with a single apostrophe so the
# cell is treated as literal text. Numeric values are returned unchanged so
# legitimate amounts remain numeric in the CSV.
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@")


def _csv_safe_text(value):
    """Sanitize a textual CSV cell against formula injection.
    Numeric (int/float) values pass through unchanged.
    None -> empty string.
    A leading whitespace + dangerous character is neutralized with a leading apostrophe.
    Applied ONLY at CSV export time — the underlying DB record is never mutated.
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    s = str(value)
    stripped = s.lstrip()
    if stripped and stripped[0] in _CSV_INJECTION_PREFIXES:
        return "'" + s
    return s


def _escape_regex(s: str) -> str:
    """Escape user input for use in a MongoDB regex query."""
    import re
    return re.escape(s or "")


async def _build_payment_history_query(
    q: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    payment_method: Optional[str],
    funding_source: Optional[str],
    status: Optional[str],
) -> dict:
    """Build the Mongo query for payment history (server-side filtering)."""
    query: dict = {}

    # Date range filter (payment_date is stored as ISO date string 'YYYY-MM-DD')
    date_filter: dict = {}
    if date_from:
        date_filter["$gte"] = date_from
    if date_to:
        date_filter["$lte"] = date_to
    if date_filter:
        query["payment_date"] = date_filter

    if payment_method and payment_method != "all":
        query["payment_method"] = payment_method

    if funding_source and funding_source != "all":
        query["payment_type"] = funding_source

    # Status: 'active' (default in UI) => exclude reversed; 'reversed' => only reversed; 'all' => everything
    if status == "reversed":
        query["status"] = "reversed"
    elif status == "active" or not status:
        query["status"] = {"$ne": "reversed"}
    # 'all' -> no status filter

    # Search: match receipt_number OR reference_number OR resolve invoice/company via a pre-lookup
    if q and q.strip():
        term = q.strip()
        pattern = _escape_regex(term)
        or_clauses = [
            {"receipt_number": {"$regex": pattern, "$options": "i"}},
            {"reference_number": {"$regex": pattern, "$options": "i"}},
            {"hrdcorp_invoice_number": {"$regex": pattern, "$options": "i"}},
        ]

        # Resolve matching invoices by invoice_number OR company/bill-to name and add invoice_id filter
        matching_invoices = await db.invoices.find(
            {
                "$or": [
                    {"invoice_number": {"$regex": pattern, "$options": "i"}},
                    {"company_name": {"$regex": pattern, "$options": "i"}},
                    {"bill_to_name": {"$regex": pattern, "$options": "i"}},
                    {"session_name": {"$regex": pattern, "$options": "i"}},
                    {"programme_name": {"$regex": pattern, "$options": "i"}},
                ]
            },
            {"_id": 0, "id": 1},
        ).to_list(2000)
        invoice_ids = [inv["id"] for inv in matching_invoices if inv.get("id")]
        if invoice_ids:
            or_clauses.append({"invoice_id": {"$in": invoice_ids}})

        query["$or"] = or_clauses

    return query


async def _enrich_payments_with_invoice(payments: list) -> list:
    """Attach invoice_number, company_name and session/programme info to each payment."""
    invoice_ids = list({p.get("invoice_id") for p in payments if p.get("invoice_id")})
    invoice_map: dict = {}
    session_map: dict = {}

    if invoice_ids:
        invoices = await db.invoices.find(
            {"id": {"$in": invoice_ids}},
            {
                "_id": 0,
                "id": 1,
                "invoice_number": 1,
                "company_name": 1,
                "bill_to_name": 1,
                "session_id": 1,
                "session_name": 1,
                "programme_name": 1,
                "total_amount": 1,
            },
        ).to_list(len(invoice_ids))
        invoice_map = {inv["id"]: inv for inv in invoices if inv.get("id")}

        session_ids = list({inv.get("session_id") for inv in invoices if inv.get("session_id")})
        if session_ids:
            sessions = await db.sessions.find(
                {"id": {"$in": session_ids}},
                {"_id": 0, "id": 1, "program_id": 1, "funding_source": 1, "start_date": 1},
            ).to_list(len(session_ids))
            session_map = {s["id"]: s for s in sessions if s.get("id")}

            program_ids = list({s.get("program_id") for s in sessions if s.get("program_id")})
            if program_ids:
                programs = await db.programs.find(
                    {"id": {"$in": program_ids}}, {"_id": 0, "id": 1, "name": 1}
                ).to_list(len(program_ids))
                program_map = {p["id"]: p.get("name") for p in programs if p.get("id")}
                for s in session_map.values():
                    s["program_name"] = program_map.get(s.get("program_id"))

    # Presence flags for attachments (avoid ever streaming base64 blobs to the list view)
    payment_ids = [p["id"] for p in payments if p.get("id")]
    receipt_set = set()
    hrd_set = set()
    if payment_ids:
        with_receipt = await db.payments.find(
            {"id": {"$in": payment_ids}, "receipt_url": {"$exists": True, "$nin": [None, ""]}},
            {"_id": 0, "id": 1},
        ).to_list(len(payment_ids))
        with_hrd_inv = await db.payments.find(
            {"id": {"$in": payment_ids}, "hrdcorp_invoice_url": {"$exists": True, "$nin": [None, ""]}},
            {"_id": 0, "id": 1},
        ).to_list(len(payment_ids))
        receipt_set = {p["id"] for p in with_receipt}
        hrd_set = {p["id"] for p in with_hrd_inv}

    for p in payments:
        inv = invoice_map.get(p.get("invoice_id")) or {}
        p["invoice_number"] = inv.get("invoice_number")
        p["company_name"] = inv.get("bill_to_name") or inv.get("company_name")
        p["session_id"] = inv.get("session_id")
        p["session_name"] = inv.get("session_name") or inv.get("programme_name")
        sess = session_map.get(inv.get("session_id")) if inv.get("session_id") else None
        if sess:
            p["programme_name"] = sess.get("program_name") or p.get("session_name")
            p["session_funding_source"] = sess.get("funding_source")
        p["has_receipt"] = p.get("id") in receipt_set
        p["has_hrdcorp_invoice"] = p.get("id") in hrd_set
    return payments


@router.get("/payments/history")
async def get_payment_history(
    q: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    payment_method: Optional[str] = None,
    funding_source: Optional[str] = None,
    status: Optional[str] = "active",
    sort: str = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=PAYMENT_HISTORY_MAX_PAGE_SIZE),
    current_user: User = Depends(get_current_user),
):
    """Server-side paginated, searchable, filterable payment history.
    READ-ONLY — does not modify any payment/invoice data.
    """
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")

    sort_spec = PAYMENT_HISTORY_ALLOWED_SORTS.get(sort, PAYMENT_HISTORY_ALLOWED_SORTS["newest"])
    query = await _build_payment_history_query(
        q=q,
        date_from=date_from,
        date_to=date_to,
        payment_method=payment_method,
        funding_source=funding_source,
        status=status,
    )

    total = await db.payments.count_documents(query)
    total_pages = max(1, math.ceil(total / page_size)) if total else 0
    skip = (page - 1) * page_size

    projection = {"_id": 0, "receipt_url": 0, "hrdcorp_invoice_url": 0}
    cursor = db.payments.find(query, projection).sort(sort_spec).skip(skip).limit(page_size)
    items = await cursor.to_list(page_size)
    items = await _enrich_payments_with_invoice(items)

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "sort": sort,
        "filters": {
            "q": q,
            "date_from": date_from,
            "date_to": date_to,
            "payment_method": payment_method,
            "funding_source": funding_source,
            "status": status,
        },
    }


@router.get("/payments/history/export")
async def export_payment_history_csv(
    q: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    payment_method: Optional[str] = None,
    funding_source: Optional[str] = None,
    status: Optional[str] = "active",
    sort: str = "newest",
    current_user: User = Depends(get_current_user),
):
    """Export the currently filtered payment history as CSV. READ-ONLY."""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")

    sort_spec = PAYMENT_HISTORY_ALLOWED_SORTS.get(sort, PAYMENT_HISTORY_ALLOWED_SORTS["newest"])
    query = await _build_payment_history_query(
        q=q,
        date_from=date_from,
        date_to=date_to,
        payment_method=payment_method,
        funding_source=funding_source,
        status=status,
    )

    # Hard cap to avoid huge exports; UI recommends narrowing filters for very large sets.
    EXPORT_LIMIT = 5000
    projection = {"_id": 0, "receipt_url": 0, "hrdcorp_invoice_url": 0}
    items = await db.payments.find(query, projection).sort(sort_spec).limit(EXPORT_LIMIT).to_list(EXPORT_LIMIT)
    items = await _enrich_payments_with_invoice(items)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Payment Date", "Receipt Number", "Client / Company", "Invoice Number",
        "Session / Programme", "Funding Source", "Payment Method",
        "Reference Number", "Amount (RM)", "Status",
    ])
    for p in items:
        # Sanitize every textual field against CSV formula injection.
        # Numeric amount stays numeric; DB records are never mutated.
        writer.writerow([
            _csv_safe_text(p.get("payment_date") or ""),
            _csv_safe_text(p.get("receipt_number") or ""),
            _csv_safe_text(p.get("company_name") or ""),
            _csv_safe_text(p.get("invoice_number") or ""),
            _csv_safe_text(p.get("programme_name") or p.get("session_name") or ""),
            _csv_safe_text(p.get("payment_type") or ""),
            _csv_safe_text(p.get("payment_method") or ""),
            _csv_safe_text(p.get("reference_number") or ""),
            p.get("amount") or 0,
            _csv_safe_text(p.get("status") or "active"),
        ])

    buffer.seek(0)
    filename = f"payment-history-{get_malaysia_time().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/payments/{payment_id}/detail")
async def get_payment_detail(payment_id: str, current_user: User = Depends(get_current_user)):
    """Read-only detail view for a single payment (Payment History)."""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")

    payment = await db.payments.find_one(
        {"id": payment_id},
        {"_id": 0, "receipt_url": 0, "hrdcorp_invoice_url": 0},
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    invoice = None
    session = None
    program = None
    if payment.get("invoice_id"):
        invoice = await db.invoices.find_one({"id": payment["invoice_id"]}, {"_id": 0})
        if invoice and invoice.get("session_id"):
            session = await db.sessions.find_one({"id": invoice["session_id"]}, {"_id": 0})
            if session and session.get("program_id"):
                program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0, "id": 1, "name": 1})

    recorded_by_name = None
    if payment.get("recorded_by"):
        recorder = await db.users.find_one({"id": payment["recorded_by"]}, {"_id": 0, "full_name": 1, "email": 1})
        if recorder:
            recorded_by_name = recorder.get("full_name") or recorder.get("email")

    payment["has_receipt"] = bool(
        await db.payments.find_one(
            {"id": payment_id, "receipt_url": {"$exists": True, "$nin": [None, ""]}},
            {"_id": 0, "id": 1},
        )
    )
    payment["has_hrdcorp_invoice"] = bool(
        await db.payments.find_one(
            {"id": payment_id, "hrdcorp_invoice_url": {"$exists": True, "$nin": [None, ""]}},
            {"_id": 0, "id": 1},
        )
    )

    return {
        "payment": payment,
        "invoice": invoice,
        "session": session,
        "program": program,
        "recorded_by_name": recorded_by_name,
    }
# ============ END PAYMENT HISTORY ============


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

    # Proformas cannot receive payments — must be converted to a real invoice first
    if invoice.get("document_type") == "proforma":
        raise HTTPException(
            status_code=400,
            detail="Payments cannot be recorded against a Proforma Invoice. Convert it to a real tax invoice first."
        )

    # ============ PAYMENT TYPE VALIDATION ============
    payment_type = (payment_data.payment_type or "self_pay").lower()
    if payment_type not in ["self_pay", "hrdcorp", "partial", "other"]:
        raise HTTPException(status_code=400, detail=f"Invalid payment_type: {payment_type}")

    hrdcorp_fee = float(payment_data.hrdcorp_service_fee or 0)
    if payment_type == "hrdcorp":
        if hrdcorp_fee <= 0:
            raise HTTPException(status_code=400, detail="HRDCorp service fee is required for HRDCorp payments")
        invoice_total = float(invoice.get("total_amount", 0))
        cn_deduction = 0.0
        if payment_data.create_credit_note:
            if payment_data.deduction_amount is not None:
                cn_deduction = float(payment_data.deduction_amount or 0)
            elif payment_data.deduction_percentage is not None:
                cn_deduction = round(invoice_total * float(payment_data.deduction_percentage or 0) / 100, 2)
        expected_sum = round(payment_data.amount + hrdcorp_fee + cn_deduction, 2)
        if abs(expected_sum - invoice_total) > 0.01:
            # Provide guidance based on scenario
            gap = round(invoice_total - payment_data.amount - hrdcorp_fee, 2)
            if gap > 0.01 and not payment_data.create_credit_note:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"HRDCorp partial grant detected: Received ({payment_data.amount}) + Fee ({hrdcorp_fee}) = {round(payment_data.amount + hrdcorp_fee, 2)} "
                        f"is RM {gap:.2f} short of Invoice ({invoice_total}). "
                        f"Please tick 'Create Credit Note' with amount RM {gap:.2f} to write off the shortfall."
                    )
                )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"HRDCorp: Received ({payment_data.amount}) + Fee ({hrdcorp_fee}) + CN ({cn_deduction}) = {expected_sum} "
                    f"must equal Invoice Amount ({invoice_total})"
                )
            )
        if not payment_data.hrdcorp_invoice_number:
            raise HTTPException(status_code=400, detail="HRDCorp invoice number is required")
    # ============ END VALIDATION ============
    
    payment = {
        "id": str(uuid.uuid4()),
        "invoice_id": payment_data.invoice_id,
        "amount": payment_data.amount,
        "payment_date": payment_data.payment_date,
        "payment_method": payment_data.payment_method,
        "reference_number": payment_data.reference_number,
        "notes": payment_data.notes,
        "receipt_url": payment_data.receipt_url,
        "payment_type": payment_type,
        "hrdcorp_service_fee": hrdcorp_fee if payment_type == "hrdcorp" else None,
        "hrdcorp_invoice_number": payment_data.hrdcorp_invoice_number if payment_type == "hrdcorp" else None,
        "hrdcorp_invoice_date": payment_data.hrdcorp_invoice_date if payment_type == "hrdcorp" else None,
        "hrdcorp_invoice_url": payment_data.hrdcorp_invoice_url if payment_type == "hrdcorp" else None,
        "receipt_number": await generate_receipt_number(),
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
    # Status calculation: sum cash received + HRDCorp service fees absorbed (treat as settled)
    total_paid = sum(
        (p.get("amount", 0) or 0) + (p.get("hrdcorp_service_fee", 0) or 0)
        for p in all_payments
        if p.get("status") != "reversed"
    )
    
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
            user_name=current_user.full_name,
            hrdcorp_fee_amount=(hrdcorp_fee if payment_type == "hrdcorp" else 0)
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
    
    # Use stored receipt number, fallback to generated one for legacy payments
    receipt_number = payment.get("receipt_number")
    if not receipt_number:
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


@router.get("/payments/{payment_id}/proof")
async def get_payment_proof(payment_id: str, current_user: User = Depends(get_current_user)):
    """Return the uploaded proof-of-payment image (base64 data URL) for a payment, if any."""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0, "receipt_url": 1})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"receipt_url": payment.get("receipt_url") or ""}


@router.get("/payments/{payment_id}/hrdcorp-invoice")
async def get_payment_hrdcorp_invoice(payment_id: str, current_user: User = Depends(get_current_user)):
    """Return the uploaded HRDCorp invoice document for a payment, if any."""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0, "hrdcorp_invoice_url": 1, "hrdcorp_invoice_number": 1, "hrdcorp_invoice_date": 1})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "hrdcorp_invoice_url": payment.get("hrdcorp_invoice_url") or "",
        "hrdcorp_invoice_number": payment.get("hrdcorp_invoice_number") or "",
        "hrdcorp_invoice_date": payment.get("hrdcorp_invoice_date") or ""
    }


@router.get("/reports/hrdcorp-deductions")
async def hrdcorp_deductions_report(
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Combined historical + new HRDCorp deductions report.
    - Pre-cutover era: Credit Notes whose reason mentions HRDCorp/Levy
    - Post-cutover era: Payments with payment_type=hrdcorp
    No data is migrated — this is a read-only join."""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    legacy_query = {"reason": {"$regex": "hrdcorp|levy", "$options": "i"}}
    new_query = {"payment_type": "hrdcorp"}
    if year:
        date_prefix = f"{year}-"
        legacy_query["cn_date"] = {"$regex": f"^{date_prefix}"}
        new_query["payment_date"] = {"$regex": f"^{date_prefix}"}
    
    legacy_cns = await db.credit_notes.find(legacy_query, {"_id": 0}).to_list(2000)
    new_payments = await db.payments.find(new_query, {"_id": 0, "receipt_url": 0, "hrdcorp_invoice_url": 0}).to_list(2000)
    
    legacy_rows = []
    for cn in legacy_cns:
        legacy_rows.append({
            "source": "credit_note",
            "date": cn.get("cn_date") or (cn.get("created_at") or "")[:10],
            "reference": cn.get("cn_number"),
            "invoice_number": cn.get("invoice_number"),
            "company_name": cn.get("company_name") or cn.get("bill_to_name"),
            "amount": cn.get("amount", 0),
            "description": cn.get("reason"),
            "mechanism": "Legacy CN-based deduction"
        })
    
    new_rows = []
    for p in new_payments:
        invoice = None
        if p.get("invoice_id"):
            invoice = await db.invoices.find_one({"id": p["invoice_id"]}, {"_id": 0, "invoice_number": 1, "company_name": 1, "bill_to_name": 1})
        new_rows.append({
            "source": "payment",
            "date": p.get("payment_date"),
            "reference": p.get("receipt_number"),
            "invoice_number": invoice.get("invoice_number") if invoice else None,
            "company_name": (invoice.get("company_name") or invoice.get("bill_to_name")) if invoice else None,
            "amount": p.get("hrdcorp_service_fee", 0),
            "hrdcorp_invoice_number": p.get("hrdcorp_invoice_number"),
            "hrdcorp_invoice_date": p.get("hrdcorp_invoice_date"),
            "description": "HRDCorp Service Charge (Expense)",
            "mechanism": "Post-cutover expense booking"
        })
    
    legacy_total = round(sum(r["amount"] for r in legacy_rows), 2)
    new_total = round(sum(r["amount"] for r in new_rows), 2)
    
    return {
        "year": year,
        "legacy_cn_based": {
            "rows": legacy_rows,
            "count": len(legacy_rows),
            "total": legacy_total
        },
        "new_expense_based": {
            "rows": new_rows,
            "count": len(new_rows),
            "total": new_total
        },
        "grand_total": round(legacy_total + new_total, 2)
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
    """Create a credit note manually (e.g., for HRDCorp 4% deduction) - also handles retroactive creation"""
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
        "session_id": cn_data.get("session_id") or (invoice.get("session_id") if invoice else None),
        "session_name": cn_data.get("session_name") or (invoice.get("session_name") or invoice.get("programme_name") if invoice else None),
        "company_id": cn_data.get("company_id") or (invoice.get("company_id") if invoice else None),
        "company_name": cn_data.get("company_name") or (invoice.get("company_name") if invoice else None),
        "bill_to_name": cn_data.get("bill_to_name") or (invoice.get("bill_to_name") if invoice else None),
        "bill_to_address": cn_data.get("bill_to_address") or (invoice.get("bill_to_address") if invoice else None),
        "reason": cn_data.get("reason", "HRDCorp Levy Deduction"),
        "description": cn_data.get("description") or f"{cn_data.get('percentage', 4)}% deduction",
        "base_amount": float(invoice.get("total_amount", 0)) if invoice else 0,
        "amount": float(cn_data.get("amount", 0)),
        "percentage": float(cn_data.get("percentage", 4)),
        "status": "draft",
        "created_by": current_user.id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "cn_date": cn_data.get("cn_date") or now.strftime("%Y-%m-%d")
    }
    
    await db.credit_notes.insert_one(credit_note)
    credit_note.pop("_id", None)
    await log_finance_action("credit_note", credit_note["id"], "created", current_user.id, after_value=credit_note)
    
    # Auto-post to journal
    try:
        await post_credit_note_issued(
            credit_note=credit_note,
            invoice=invoice,
            user_id=current_user.id,
            user_name=current_user.full_name
        )
    except Exception as e:
        print(f"Credit note journal auto-post error: {str(e)}")
    
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
