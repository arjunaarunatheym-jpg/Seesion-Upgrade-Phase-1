"""
Finance Session routes - Session costing, invoices, expenses, marketing
Endpoints: 12
- GET /finance/session/{session_id}/costing
- POST /finance/session/{session_id}/invoice
- POST /finance/session/{session_id}/additional-invoice
- POST /finance/session/{session_id}/trainer-fees
- POST /finance/session/{session_id}/coordinator-fee
- POST /finance/session/{session_id}/expenses
- DELETE /finance/session/{session_id}/expense/{expense_id}
- POST /finance/session/{session_id}/marketing
- POST /finance/session/{session_id}/calculate-profit
- GET /finance/session/{session_id}/payables-report
- GET /finance/pdf-layout-preview
- POST /finance/session/{session_id}/credit-note
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from typing import List, Optional
from datetime import datetime
import uuid
import os

from core import db, get_current_user, get_malaysia_time, pwd_context, ROOT_DIR
from models import User, CompanySettings

router = APIRouter(prefix="/finance", tags=["finance_session"])


async def _generate_invoice_number():
    """Generate a sequential invoice number - delegates to finance_invoices logic"""
    from routes.finance_invoices import generate_invoice_number
    return await generate_invoice_number()


@router.get("/session/{session_id}/costing")
async def get_session_costing(session_id: str, current_user: User = Depends(get_current_user)):
    """Get complete costing breakdown for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # PHASE 3A Section Q: use canonical status set. Legacy 'partial' is
    # obsolete — canonical is 'partially_paid'. Keep 'partial' for
    # backward-compat reads of very old records if any still exist.
    ELIGIBLE_STATUSES = ["issued", "partial", "partially_paid", "paid"]
    invoices = await db.invoices.find({
        "session_id": session_id,
        "status": {"$in": ELIGIBLE_STATUSES}
    }, {"_id": 0}).to_list(100)

    invoice_total = sum(float(inv.get("total_amount", 0)) for inv in invoices)
    tax_amount = sum(float(inv.get("tax_amount", 0)) for inv in invoices)
    invoice_count = len(invoices)

    trainer_fees = await db.trainer_fees.find({"session_id": session_id}, {"_id": 0}).to_list(100)

    for fee in trainer_fees:
        if not fee.get("trainer_name") or fee.get("trainer_name") == "Unknown Trainer":
            if fee.get("trainer_id"):
                trainer = await db.users.find_one({"id": fee.get("trainer_id")}, {"_id": 0, "full_name": 1})
                fee["trainer_name"] = trainer.get("full_name") if trainer else "Unknown Trainer"

    session_trainer_ids = [ta.get("trainer_id") for ta in session.get("trainer_assignments", [])]
    existing_fee_trainer_ids = [f.get("trainer_id") for f in trainer_fees]
    new_trainer_ids = [tid for tid in session_trainer_ids if tid not in existing_fee_trainer_ids]

    for ta in session.get("trainer_assignments", []):
        if ta.get("trainer_id") in new_trainer_ids:
            trainer = await db.users.find_one({"id": ta.get("trainer_id")}, {"_id": 0, "full_name": 1})
            trainer_fees.append({
                "trainer_id": ta.get("trainer_id"),
                "trainer_name": trainer.get("full_name") if trainer else "Unknown Trainer",
                "role": ta.get("role", "regular"),
                "fee_amount": 0,
                "remark": "",
                "status": "pending"
            })

    trainer_fees = [f for f in trainer_fees if f.get("trainer_id") in session_trainer_ids]
    trainer_fees_total = sum(f.get("fee_amount", 0) for f in trainer_fees)

    coord_fee = await db.coordinator_fees.find_one({"session_id": session_id}, {"_id": 0})
    coordinator_fee_total = coord_fee.get("total_fee", 0) if coord_fee else 0

    expenses = await db.session_expenses.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    cash_expenses_estimated = sum(e.get("estimated_amount", 0) for e in expenses)
    cash_expenses_actual = sum(e.get("actual_amount", 0) for e in expenses)

    marketing = await db.marketing_commissions.find_one({"session_id": session_id, "type": {"$ne": "admin_fee"}}, {"_id": 0})

    gross_revenue = invoice_total - tax_amount
    cash_expenses_used = cash_expenses_actual
    total_expenses_before_marketing = trainer_fees_total + coordinator_fee_total + cash_expenses_used
    profit_before_marketing = gross_revenue - total_expenses_before_marketing

    marketing_amount = 0.0
    if marketing:
        if marketing.get("commission_type") == "percentage":
            marketing_amount = profit_before_marketing * (marketing.get("commission_rate", 0) / 100)
        else:
            marketing_amount = marketing.get("fixed_amount") or 0.0

    total_expenses = total_expenses_before_marketing + marketing_amount
    final_profit = gross_revenue - total_expenses
    profit_percentage = (final_profit / gross_revenue * 100) if gross_revenue > 0 else 0

    company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})

    trainer_count = len(session.get("trainer_assignments", []))
    coordinator_count = 1 if session.get("coordinator_id") else 0
    total_headcount = len(session.get("participant_ids", [])) + trainer_count + coordinator_count

    return {
        "session_id": session_id,
        "session_name": session.get("name"),
        "company_name": company.get("name") if company else None,
        "training_dates": f"{session.get('start_date')} to {session.get('end_date')}",
        "pax": len(session.get("participant_ids", [])),
        "trainer_count": trainer_count,
        "coordinator_count": coordinator_count,
        "total_headcount": total_headcount,
        "invoice_total": invoice_total,
        "invoice_count": invoice_count,
        "less_tax": tax_amount,
        "gross_revenue": gross_revenue,
        "trainer_fees": trainer_fees,
        "trainer_fees_total": trainer_fees_total,
        "coordinator_fee": coord_fee,
        "coordinator_fee_total": coordinator_fee_total,
        "expenses": expenses,
        "cash_expenses_estimated": cash_expenses_estimated,
        "cash_expenses_actual": cash_expenses_actual,
        "marketing": marketing,
        "marketing_commission": marketing_amount,
        "total_expenses": total_expenses,
        "profit": final_profit,
        "profit_percentage": round(profit_percentage, 2)
    }


@router.post("/session/{session_id}/invoice")
async def save_session_invoice(session_id: str, invoice_data: dict, current_user: User = Depends(get_current_user)):
    """Save or update invoice for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # PHASE 3A (Section 12): use canonical resolver instead of arbitrary
    # find_one({"session_id": ...}). Session Costing must NEVER modify
    # converted proformas or issued/partially_paid/paid invoices.
    from services.financial_write_guard import (
        FinancialWriteGuard, FinancialSafetyError, FinancialAmbiguityError,
    )
    guard = FinancialWriteGuard(db)
    explicit_invoice_id = invoice_data.get("invoice_id")
    existing = None
    try:
        if session.get("invoice_id") or explicit_invoice_id:
            existing = await guard.resolve_session_primary_invoice(
                session_id, explicit_invoice_id=explicit_invoice_id,
            )
        else:
            # Legacy compatibility: allow single-eligible resolution but never
            # arbitrary find_one on multiple.
            candidates = await db.invoices.find(
                {"session_id": session_id, "document_type": {"$ne": "proforma"},
                 "status": {"$in": ["draft", "auto_draft", "finance_review", "approved"]}},
                {"_id": 0},
            ).to_list(10)
            if len(candidates) == 1:
                existing = candidates[0]
            elif len(candidates) > 1:
                raise FinancialAmbiguityError(
                    "Session has multiple pre-issue invoices; supply invoice_id.",
                    candidates=[{"id": c["id"], "invoice_number": c.get("invoice_number")} for c in candidates],
                )
    except FinancialAmbiguityError as e:
        raise HTTPException(status_code=e.http_status,
                            detail={"code": e.code, "message": e.message, "candidates": e.candidates})
    except FinancialSafetyError as e:
        raise HTTPException(status_code=e.http_status, detail={"code": e.code, "message": e.message})

    now = get_malaysia_time()

    if existing:
        # Block mutation of locked / terminal invoices.
        locked = (existing.get("status") or "").lower() in {
            "issued", "partially_paid", "paid", "voided", "cancelled", "deleted", "converted",
        }
        if locked:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "INVOICE_LOCKED",
                    "message": (
                        f"Invoice {existing.get('id')} is in status {existing.get('status')!r} — "
                        "Session Costing cannot rewrite issued/paid/terminal invoices. "
                        "Use the SuperAdmin controlled correction endpoints if a "
                        "genuine data entry correction is required."
                    ),
                    "invoice_id": existing.get("id"),
                    "invoice_status": existing.get("status"),
                },
            )
        update_dict = {
            "pricing_type": invoice_data.get("pricing_type", "lumpsum"),
            "line_items": invoice_data.get("line_items", []),
            "subtotal": invoice_data.get("subtotal", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "total_amount": invoice_data.get("total_amount", 0),
            "updated_at": now.isoformat()
        }
        await db.invoices.update_one({"id": existing["id"]}, {"$set": update_dict})
        # Recompute admin fee since subtotal may have changed
        try:
            from routes.admin_fee import apply_admin_fee_to_session
            await apply_admin_fee_to_session(session_id, current_user.id)
        except Exception as _e:
            print(f"[save_session_invoice/update] admin_fee hook failed: {_e}")
        return {"message": "Invoice updated", "invoice_id": existing["id"]}
    else:
        # Determine document type: "invoice" (default) or "proforma"
        document_type = (invoice_data.get("document_type") or "invoice").lower()
        if document_type not in ("invoice", "proforma"):
            raise HTTPException(status_code=400, detail="document_type must be 'invoice' or 'proforma'")
        if document_type == "proforma":
            from routes.finance_invoices import generate_proforma_number
            invoice_number = await generate_proforma_number()
        else:
            invoice_number = await _generate_invoice_number()
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})

        # Enrich with programme / training dates / venue so PDF prints them
        programme_name = None
        if session.get("program_id"):
            prog = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0, "name": 1})
            programme_name = prog.get("name") if prog else None

        training_dates_str = None
        td = session.get("training_dates")
        if td and isinstance(td, list) and len(td) > 1:
            training_dates_str = ", ".join(td)
        elif session.get("start_date"):
            if session.get("end_date") and session.get("end_date") != session.get("start_date"):
                training_dates_str = f"{session['start_date']} — {session['end_date']}"
            else:
                training_dates_str = session["start_date"]

        venue = session.get("location")
        if not venue and session.get("quotation_id"):
            quo = await db.quotations.find_one({"id": session["quotation_id"]}, {"_id": 0, "venue": 1})
            venue = quo.get("venue") if quo else None

        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "document_type": document_type,
            "session_id": session_id,
            "company_id": session.get("company_id"),
            "company_name": company.get("name") if company else None,
            "session_name": session.get("name"),
            "programme_name": programme_name,
            "training_dates": training_dates_str,
            "venue": venue,
            "pricing_type": invoice_data.get("pricing_type", "lumpsum"),
            "line_items": invoice_data.get("line_items", []),
            "subtotal": invoice_data.get("subtotal", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "total_amount": invoice_data.get("total_amount", 0),
            "status": "draft",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": current_user.id
        }
        await db.invoices.insert_one(invoice)
        return {"message": f"{'Proforma i' if document_type == 'proforma' else 'I'}nvoice created", "invoice_id": invoice["id"], "invoice_number": invoice_number, "document_type": document_type}


@router.post("/session/{session_id}/additional-invoice")
async def save_additional_invoice(session_id: str, invoice_data: dict, current_user: User = Depends(get_current_user)):
    """Create or update additional invoice for multi-company sessions"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    company_id = invoice_data.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID required")

    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    now = get_malaysia_time()
    invoice_id = invoice_data.get("invoice_id")

    # PHASE 3A Section P: additional-invoice writes must respect the invoice
    # lifecycle just like save_session_invoice. Never arbitrarily pick a
    # find_one({"session_id", "company_id"}) result and mutate it — that can
    # rewrite a locked issued/paid invoice.
    from services.financial_write_guard import FinancialWriteGuard
    guard = FinancialWriteGuard(db)
    PRE_ISSUE = ("draft", "auto_draft", "finance_review", "approved")

    if invoice_id:
        target = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not target:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if target.get("session_id") != session_id:
            raise HTTPException(status_code=400, detail="Invoice does not belong to this session")
        if target.get("company_id") != company_id:
            raise HTTPException(status_code=400, detail="Invoice belongs to a different company")
        # Route through the canonical write guard for locked-field protection.
        proposed = {
            "company_id": company_id,
            "company_name": company.get("name"),
            "total_amount": invoice_data.get("total_amount", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
        }
        try:
            guard.assert_invoice_editable(target, proposed)
        except Exception:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "INVOICE_LOCKED",
                    "message": (
                        f"Invoice {invoice_id} is in status "
                        f"{target.get('status')!r} — the additional-invoice endpoint "
                        "cannot rewrite locked financial documents. Use "
                        "/api/superadmin/finance/invoices/{id}/correct-value for "
                        "controlled corrections."
                    ),
                    "invoice_id": invoice_id,
                    "invoice_status": target.get("status"),
                },
            )
        update_dict = {**proposed, "updated_at": now.isoformat()}
        await db.invoices.update_one({"id": invoice_id}, {"$set": update_dict})
        return {"message": "Additional invoice updated", "invoice_id": invoice_id}
    else:
        # No explicit invoice_id — search ONLY for a safe pre-issue candidate.
        pre_issue_candidates = await db.invoices.find(
            {"session_id": session_id, "company_id": company_id,
             "status": {"$in": list(PRE_ISSUE)}},
            {"_id": 0},
        ).to_list(10)
        locked_candidates = await db.invoices.find(
            {"session_id": session_id, "company_id": company_id,
             "status": {"$nin": list(PRE_ISSUE) + ["deleted"]}},
            {"_id": 0, "id": 1, "invoice_number": 1, "status": 1, "total_amount": 1},
        ).to_list(10)

        if len(pre_issue_candidates) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "AMBIGUOUS_SESSION_INVOICE_SELECTION",
                    "message": "Multiple pre-issue additional invoices exist; supply invoice_id explicitly.",
                    "candidates": [
                        {"id": c["id"], "invoice_number": c.get("invoice_number"),
                         "status": c.get("status")}
                        for c in pre_issue_candidates
                    ],
                },
            )
        if len(pre_issue_candidates) == 1:
            existing = pre_issue_candidates[0]
            update_dict = {
                "total_amount": invoice_data.get("total_amount", 0),
                "tax_rate": invoice_data.get("tax_rate", 0),
                "tax_amount": invoice_data.get("tax_amount", 0),
                "updated_at": now.isoformat()
            }
            await db.invoices.update_one({"id": existing["id"]}, {"$set": update_dict})
            return {"message": "Additional invoice updated", "invoice_id": existing["id"]}

        # No pre-issue candidate but locked ones exist → refuse to touch them.
        if locked_candidates:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ONLY_LOCKED_CANDIDATES",
                    "message": (
                        "Only issued/paid/terminal additional invoices exist "
                        "for this company on this session — they cannot be "
                        "mutated. Create a new draft or use SuperAdmin "
                        "controlled correction endpoints."
                    ),
                    "candidates": locked_candidates,
                },
            )

        reuse_number = invoice_data.get("reuse_invoice_number")
        if reuse_number:
            deleted_record = await db.deleted_invoice_numbers.find_one({
                "invoice_number": reuse_number,
                "is_available": True
            })
            if deleted_record:
                invoice_number = reuse_number
                await db.deleted_invoice_numbers.update_one(
                    {"invoice_number": reuse_number},
                    {"$set": {"is_available": False, "reused_at": now.isoformat(), "reused_session_id": session_id}}
                )
            else:
                invoice_number = await _generate_invoice_number()
        else:
            invoice_number = await _generate_invoice_number()

        program_name = ""
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session.get("program_id")}, {"_id": 0, "name": 1})
            program_name = program.get("name", "") if program else ""

        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "session_id": session_id,
            "company_id": company_id,
            "company_name": company.get("name"),
            "bill_to_name": company.get("name"),
            "bill_to_address": f"{company.get('address_line1', '')} {company.get('address_line2', '')}".strip(),
            "bill_to_reg_no": company.get("registration_no", ""),
            "session_name": session.get("name"),
            "programme_name": program_name,
            "venue": session.get("location", ""),
            "training_dates": f"{session.get('start_date', '')} - {session.get('end_date', '')}",
            "pricing_type": "lumpsum",
            "line_items": [{"description": "Training Course Fee", "quantity": 1, "unit_price": invoice_data.get("total_amount", 0), "amount": invoice_data.get("total_amount", 0)}],
            "subtotal": invoice_data.get("total_amount", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "total_amount": invoice_data.get("total_amount", 0),
            "status": "auto_draft",
            "is_additional": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": current_user.id
        }
        await db.invoices.insert_one(invoice)
        return {"message": "Additional invoice created", "invoice_id": invoice["id"], "invoice_number": invoice_number}


@router.post("/session/{session_id}/trainer-fees")
async def save_trainer_fees(session_id: str, fees: List[dict], current_user: User = Depends(get_current_user)):
    """Save trainer fees for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.trainer_fees.delete_many({"session_id": session_id})

    for fee in fees:
        trainer = await db.users.find_one({"id": fee.get("trainer_id")}, {"_id": 0, "full_name": 1})
        fee_record = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "trainer_id": fee.get("trainer_id"),
            "trainer_name": trainer.get("full_name") if trainer else fee.get("trainer_name"),
            "role": fee.get("role", "trainer"),
            "fee_amount": float(fee.get("fee_amount", 0)),
            "remark": fee.get("remark"),
            "status": "pending",
            "created_at": get_malaysia_time().isoformat()
        }
        await db.trainer_fees.insert_one(fee_record)

    return {"message": f"Saved {len(fees)} trainer fees"}


@router.post("/session/{session_id}/coordinator-fee")
async def save_coordinator_fee(session_id: str, fee_data: dict, current_user: User = Depends(get_current_user)):
    """Save coordinator fee for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    coordinator_id = fee_data.get("coordinator_id") or session.get("coordinator_id")
    if not coordinator_id:
        raise HTTPException(status_code=400, detail="No coordinator assigned")

    coordinator = await db.users.find_one({"id": coordinator_id}, {"_id": 0, "full_name": 1})

    num_days = fee_data.get("num_days", 1)
    daily_rate = fee_data.get("daily_rate", 50.0)
    total_fee = num_days * daily_rate

    existing_fee = await db.coordinator_fees.find_one({"session_id": session_id}, {"_id": 0, "id": 1})
    fee_id = existing_fee.get("id") if existing_fee and existing_fee.get("id") else str(uuid.uuid4())

    await db.coordinator_fees.update_one(
        {"session_id": session_id},
        {"$set": {
            "id": fee_id,
            "coordinator_id": coordinator_id,
            "coordinator_name": coordinator.get("full_name") if coordinator else None,
            "num_days": num_days,
            "daily_rate": daily_rate,
            "total_fee": total_fee,
            "status": "pending",
            "created_at": get_malaysia_time().isoformat()
        }},
        upsert=True
    )

    return {"message": "Coordinator fee saved", "total_fee": total_fee}


@router.post("/session/{session_id}/expenses")
async def save_session_expenses(session_id: str, expenses: List[dict], current_user: User = Depends(get_current_user)):
    """Save expenses for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    for expense in expenses:
        expense_id = expense.get("id")

        if expense_id:
            await db.session_expenses.update_one(
                {"id": expense_id},
                {"$set": {
                    "category": expense.get("category"),
                    "description": expense.get("description"),
                    "expense_type": expense.get("expense_type", "fixed"),
                    "percentage_rate": float(expense.get("percentage_rate", 0)),
                    "estimated_amount": float(expense.get("estimated_amount", 0)),
                    "actual_amount": float(expense.get("actual_amount", 0)),
                    "quantity": int(expense.get("quantity", 1)),
                    "unit_price": float(expense.get("unit_price", 0)),
                    "remark": expense.get("remark"),
                    "status": expense.get("status", "estimated"),
                    "updated_at": get_malaysia_time().isoformat()
                }}
            )
        else:
            expense_record = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "category": expense.get("category"),
                "description": expense.get("description"),
                "expense_type": expense.get("expense_type", "fixed"),
                "percentage_rate": float(expense.get("percentage_rate", 0)),
                "estimated_amount": float(expense.get("estimated_amount", 0)),
                "actual_amount": float(expense.get("actual_amount", 0)),
                "quantity": int(expense.get("quantity", 1)),
                "unit_price": float(expense.get("unit_price", 0)),
                "remark": expense.get("remark"),
                "status": expense.get("status", "estimated"),
                "created_at": get_malaysia_time().isoformat(),
                "updated_at": get_malaysia_time().isoformat()
            }
            await db.session_expenses.insert_one(expense_record)

    # Trigger Administration Fee auto-application (idempotent; no-op for sessions predating cutoff)
    try:
        from routes.admin_fee import apply_admin_fee_to_session
        await apply_admin_fee_to_session(session_id, current_user.id)
    except Exception as _e:
        print(f"[save_session_expenses] admin_fee hook failed: {_e}")

    return {"message": f"Saved {len(expenses)} expenses"}


@router.delete("/session/{session_id}/expense/{expense_id}")
async def delete_session_expense(session_id: str, expense_id: str, current_user: User = Depends(get_current_user)):
    """Delete a session expense"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.session_expenses.delete_one({"id": expense_id, "session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")

    return {"message": "Expense deleted"}


@router.post("/session/{session_id}/marketing")
async def save_marketing_commission(session_id: str, marketing_data: dict, current_user: User = Depends(get_current_user)):
    """Save or create marketing person and commission for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    marketing_user_id = marketing_data.get("marketing_user_id")

    if marketing_data.get("create_new") and not marketing_user_id:
        full_name = marketing_data.get("full_name")
        id_number = marketing_data.get("id_number")

        if not full_name or not id_number:
            raise HTTPException(status_code=400, detail="Name and ID number required for new marketing person")

        existing = await db.users.find_one({"id_number": id_number}, {"_id": 0})
        if existing:
            marketing_user_id = existing.get("id")
            if "marketing" not in (existing.get("additional_roles") or []):
                await db.users.update_one(
                    {"id": marketing_user_id},
                    {"$addToSet": {"additional_roles": "marketing"}}
                )
        else:
            email_safe = id_number.replace(" ", "").replace("-", "")
            new_user = {
                "id": str(uuid.uuid4()),
                "email": f"{email_safe}@marketing.mddrc.local",
                "full_name": full_name,
                "id_number": id_number,
                "role": "marketing",
                "additional_roles": [],
                "password": pwd_context.hash("mddrc1"),
                "created_at": get_malaysia_time().isoformat(),
                "is_active": True
            }
            await db.users.insert_one(new_user)
            marketing_user_id = new_user["id"]

    if not marketing_user_id:
        raise HTTPException(status_code=400, detail="Marketing user ID required")

    marketing_user = await db.users.find_one({"id": marketing_user_id}, {"_id": 0, "full_name": 1})

    costing = await get_session_costing(session_id, current_user)
    gross_revenue = costing.get("gross_revenue", 0)
    cash_expenses = costing.get("cash_expenses_actual", 0) or costing.get("cash_expenses_estimated", 0)
    total_expenses = costing.get("trainer_fees_total", 0) + costing.get("coordinator_fee_total", 0) + cash_expenses
    profit_before_marketing = gross_revenue - total_expenses

    commission_type = marketing_data.get("commission_type", "percentage")
    commission_rate = float(marketing_data.get("commission_rate", 0))
    fixed_amount = float(marketing_data.get("fixed_amount", 0))

    if commission_type == "percentage":
        calculated_amount = round(profit_before_marketing * commission_rate / 100, 2)
    else:
        calculated_amount = round(fixed_amount, 2)

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0, "start_date": 1, "invoice_id": 1})

    await db.marketing_commissions.update_one(
        {"session_id": session_id, "type": {"$ne": "admin_fee"}},
        {"$set": {
            "id": str(uuid.uuid4()),
            "type": "marketing",
            "marketing_user_id": marketing_user_id,
            "marketing_user_name": marketing_user.get("full_name") if marketing_user else None,
            "commission_type": commission_type,
            "commission_rate": commission_rate,
            "fixed_amount": fixed_amount,
            "calculated_amount": calculated_amount,
            "session_name": costing.get("session_name"),
            "company_name": costing.get("company_name"),
            "training_dates": costing.get("training_dates"),
            "session_start_date": session.get("start_date") if session else None,
            "invoice_id": session.get("invoice_id") if session else None,
            "status": "pending",
            "updated_at": get_malaysia_time().isoformat()
        }},
        upsert=True
    )

    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "marketing_user_id": marketing_user_id,
            "commission_type": marketing_data.get("commission_type", "percentage"),
            "commission_rate": float(marketing_data.get("commission_rate", 0)),
            "commission_fixed_amount": float(marketing_data.get("fixed_amount", 0))
        }}
    )

    return {"message": "Marketing commission saved", "marketing_user_id": marketing_user_id}


@router.post("/session/{session_id}/calculate-profit")
async def calculate_and_save_profit(session_id: str, current_user: User = Depends(get_current_user)):
    """Calculate and finalize profit for a session"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can finalize profit")

    costing = await get_session_costing(session_id, current_user)

    marketing = await db.marketing_commissions.find_one({"session_id": session_id, "type": {"$ne": "admin_fee"}}, {"_id": 0})
    if marketing:
        await db.marketing_commissions.update_one(
            {"session_id": session_id, "type": {"$ne": "admin_fee"}},
            {"$set": {
                "calculated_amount": costing["marketing_commission"],
                "status": "approved",
                "updated_at": get_malaysia_time().isoformat()
            }}
        )

    return {
        "message": "Profit calculated",
        "profit": costing["profit"],
        "profit_percentage": costing["profit_percentage"],
        "marketing_commission": costing["marketing_commission"]
    }


@router.get("/session/{session_id}/payables-report")
async def get_session_payables_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Get comprehensive payables report for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0})
    program = await db.programs.find_one({"id": session.get("program_id")}, {"_id": 0})
    participant_count = len(session.get("participant_ids", []))
    coordinator = await db.users.find_one({"id": session.get("coordinator_id")}, {"_id": 0, "full_name": 1})
    invoice = await db.invoices.find_one({"session_id": session_id}, {"_id": 0})
    trainer_fees = await db.trainer_fees.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    coordinator_fees = await db.coordinator_fees.find({"session_id": session_id}, {"_id": 0}).to_list(10)
    expenses = await db.session_expenses.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    marketing = await db.marketing_commissions.find({"session_id": session_id}, {"_id": 0}).to_list(10)

    total_trainer_fees = sum(t.get("fee_amount", 0) for t in trainer_fees)
    total_coordinator_fees = sum(c.get("total_fee", 0) for c in coordinator_fees)
    total_marketing = sum(m.get("commission_amount", 0) for m in marketing)
    total_expenses = sum(e.get("actual_amount") or e.get("amount", 0) for e in expenses)

    costing = await db.session_costing.find_one({"session_id": session_id}, {"_id": 0})

    return {
        "session": {
            "id": session_id,
            "name": session.get("name"),
            "start_date": session.get("start_date"),
            "end_date": session.get("end_date"),
            "venue": session.get("venue"),
            "num_days": session.get("num_days", 1)
        },
        "client": {
            "company_name": company.get("name") if company else session.get("company_name"),
            "contact_person": session.get("contact_person"),
            "contact_phone": session.get("contact_phone"),
            "contact_email": session.get("contact_email")
        },
        "program": {
            "name": program.get("name") if program else session.get("program_name"),
            "category": program.get("category") if program else ""
        },
        "participants": {
            "count": participant_count,
            "target": session.get("pax", 0)
        },
        "coordinator": {
            "name": coordinator.get("full_name") if coordinator else "",
            "id": session.get("coordinator_id")
        },
        "invoice": {
            "number": invoice.get("invoice_number") if invoice else "",
            "status": invoice.get("status") if invoice else "",
            "total_amount": invoice.get("total_amount", 0) if invoice else 0,
            "bill_to": invoice.get("bill_to_name") if invoice else ""
        },
        "payables": {
            "trainer_fees": trainer_fees,
            "coordinator_fees": coordinator_fees,
            "marketing_commissions": marketing,
            "expenses": expenses
        },
        "totals": {
            "trainer_fees": total_trainer_fees,
            "coordinator_fees": total_coordinator_fees,
            "marketing_commissions": total_marketing,
            "expenses": total_expenses,
            "total_payables": total_trainer_fees + total_coordinator_fees + total_marketing + total_expenses,
            "invoice_amount": invoice.get("total_amount", 0) if invoice else 0,
            "profit": (invoice.get("total_amount", 0) if invoice else 0) - (total_trainer_fees + total_coordinator_fees + total_marketing + total_expenses)
        },
        "costing": costing
    }


@router.get("/pdf-layout-preview")
async def get_pdf_layout_preview(current_user: User = Depends(get_current_user)):
    """Generate a preview PDF with current layout settings"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")

    company_settings = await db.company_settings.find_one({"id": "company_settings"}, {"_id": 0})
    if not company_settings:
        company_settings = {}

    primary_color_hex = company_settings.get("primary_color", "#1a365d")
    try:
        primary_color_rgb = tuple(int(primary_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        primary_color_rgb = (26, 54, 93)

    from routes.marketing import QuotationPDF
    pdf = QuotationPDF(company_settings, primary_color_rgb)
    pdf.add_page()

    pdf.set_font_safe('B', 12)
    pdf.ln(10)
    pdf.cell_safe(0, 8, "QUOTATION LAYOUT PREVIEW", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font_safe('', 10)
    pdf.multi_cell_safe(0, 5, "This is a preview of your PDF layout. Adjust the settings below to customize the header layout:\n\n" +
        f"- Logo X Position: {company_settings.get('logo_x', 10)}mm\n" +
        f"- Logo Y Position: {company_settings.get('logo_y', 8)}mm\n" +
        f"- Logo Width: {company_settings.get('logo_width', 35)}mm\n" +
        f"- Logo Height: {company_settings.get('logo_height', 0)}mm (0 = auto)\n" +
        f"- Header X Position: {company_settings.get('header_x', 50)}mm\n" +
        f"- Header Y Position: {company_settings.get('header_y', 8)}mm\n")

    pdf_output = pdf.output()

    return Response(
        content=bytes(pdf_output),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=layout_preview.pdf"}
    )

