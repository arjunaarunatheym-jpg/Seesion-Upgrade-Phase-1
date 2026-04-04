"""
Finance Petty Cash & Manual Entries routes
Stage F6: ~14 endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
import uuid

from core import db, get_current_user, get_malaysia_time
from models import User

try:
    from routes.accounting import create_auto_journal_entry
except ImportError:
    create_auto_journal_entry = None

router = APIRouter(prefix="/finance", tags=["finance-petty-cash"])


# ============ MODELS ============
class ManualIncomeEntry(BaseModel):
    description: str
    amount: float
    category: str = "Other Income"
    date: str  # YYYY-MM-DD
    notes: Optional[str] = None


class ManualExpenseEntry(BaseModel):
    description: str
    amount: float
    category: str
    date: str  # YYYY-MM-DD
    notes: Optional[str] = None


class PettyCashSetup(BaseModel):
    float_amount: float
    custodian_id: Optional[str] = None
    custodian_name: Optional[str] = None
    approval_threshold: float = 100.0


class PettyCashTransaction(BaseModel):
    type: str
    amount: float
    description: str
    category: Optional[str] = None
    receipt_url: Optional[str] = None
    date: str
    notes: Optional[str] = None


class PettyCashReconciliation(BaseModel):
    physical_count: float
    notes: Optional[str] = None


# ============ MANUAL INCOME ENDPOINTS ============
@router.post("/manual-income")
async def add_manual_income(entry: ManualIncomeEntry, current_user: User = Depends(get_current_user)):
    """Add a one-off manual income entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = {
        "id": str(uuid.uuid4()),
        "description": entry.description,
        "amount": entry.amount,
        "category": entry.category,
        "date": entry.date,
        "notes": entry.notes,
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    await db.manual_income.insert_one(record)
    # Auto-post journal entry
    if create_auto_journal_entry:
        try:
            await create_auto_journal_entry(
                entry_date=entry.date, description=f"Manual Income: {entry.description}",
                source_module="manual_income", source_id=record["id"], source_reference=f"MI-{record['id'][:8]}",
                lines=[
                    {"account_code": "1000", "debit": round(entry.amount, 2), "credit": 0, "memo": "Cash received"},
                    {"account_code": "4100", "debit": 0, "credit": round(entry.amount, 2), "memo": entry.description},
                ],
                created_by_id=current_user.id, created_by_name=current_user.full_name, skip_date_check=True
            )
        except Exception:
            pass  # Non-blocking — backfill will catch it
    return {"message": "Income entry added", "id": record["id"]}


@router.get("/manual-income")
async def get_manual_income(year: int = None, current_user: User = Depends(get_current_user)):
    """Get manual income entries"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        query["date"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    
    entries = await db.manual_income.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return entries


@router.delete("/manual-income/{entry_id}")
async def delete_manual_income(entry_id: str, current_user: User = Depends(get_current_user)):
    """Delete a manual income entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.manual_income.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Entry deleted"}


# ============ MANUAL EXPENSE ENDPOINTS ============
@router.post("/manual-expense")
async def add_manual_expense(entry: ManualExpenseEntry, current_user: User = Depends(get_current_user)):
    """Add a one-off manual expense entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = {
        "id": str(uuid.uuid4()),
        "description": entry.description,
        "amount": entry.amount,
        "category": entry.category,
        "date": entry.date,
        "notes": entry.notes,
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    await db.manual_expenses.insert_one(record)
    # Auto-post journal entry
    if create_auto_journal_entry:
        try:
            await create_auto_journal_entry(
                entry_date=entry.date, description=f"Manual Expense: {entry.description}",
                source_module="manual_expense", source_id=record["id"], source_reference=f"ME-{record['id'][:8]}",
                lines=[
                    {"account_code": "6999", "debit": round(entry.amount, 2), "credit": 0, "memo": entry.description},
                    {"account_code": "1000", "debit": 0, "credit": round(entry.amount, 2), "memo": "Cash paid"},
                ],
                created_by_id=current_user.id, created_by_name=current_user.full_name, skip_date_check=True
            )
        except Exception:
            pass
    return {"message": "Expense entry added", "id": record["id"]}


@router.get("/manual-expenses")
async def get_manual_expenses(year: int = None, current_user: User = Depends(get_current_user)):
    """Get manual expense entries"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        query["date"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    
    entries = await db.manual_expenses.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return entries


@router.delete("/manual-expense/{entry_id}")
async def delete_manual_expense(entry_id: str, current_user: User = Depends(get_current_user)):
    """Delete a manual expense entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.manual_expenses.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Entry deleted"}


# ============ PETTY CASH ENDPOINTS ============
@router.get("/petty-cash/settings")
async def get_petty_cash_settings(current_user: User = Depends(get_current_user)):
    """Get petty cash settings"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.petty_cash_settings.find_one({}, {"_id": 0})
    if not settings:
        settings = {
            "float_amount": 500.0,
            "current_balance": 500.0,
            "custodian_id": None,
            "custodian_name": None,
            "approval_threshold": 100.0,
            "last_reconciliation": None
        }
    return settings


@router.post("/petty-cash/setup")
async def setup_petty_cash(setup: PettyCashSetup, current_user: User = Depends(get_current_user)):
    """Setup or update petty cash settings"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = await db.petty_cash_settings.find_one({})
    
    settings = {
        "float_amount": setup.float_amount,
        "current_balance": setup.float_amount if not existing else existing.get("current_balance", setup.float_amount),
        "custodian_id": setup.custodian_id,
        "custodian_name": setup.custodian_name,
        "approval_threshold": setup.approval_threshold,
        "updated_at": get_malaysia_time().isoformat(),
        "updated_by": current_user.id
    }
    
    if existing:
        await db.petty_cash_settings.update_one({}, {"$set": settings})
    else:
        settings["created_at"] = get_malaysia_time().isoformat()
        settings["last_reconciliation"] = None
        await db.petty_cash_settings.insert_one(settings)
    
    return {"message": "Petty cash settings updated", "settings": {k: v for k, v in settings.items() if k != "_id"}}


@router.post("/petty-cash/transaction")
async def add_petty_cash_transaction(txn: PettyCashTransaction, current_user: User = Depends(get_current_user)):
    """Add a petty cash transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.petty_cash_settings.find_one({})
    if not settings:
        raise HTTPException(status_code=400, detail="Petty cash not set up")
    
    current_balance = settings.get("current_balance", 0)
    
    if txn.type == "expense":
        if txn.amount > current_balance:
            raise HTTPException(status_code=400, detail=f"Insufficient balance. Current: RM {current_balance:.2f}")
        new_balance = current_balance - txn.amount
    elif txn.type == "topup":
        new_balance = current_balance + txn.amount
    else:
        raise HTTPException(status_code=400, detail="Invalid type")
    
    requires_approval = txn.type == "expense" and txn.amount > settings.get("approval_threshold", 100)
    
    transaction = {
        "id": str(uuid.uuid4()),
        "type": txn.type,
        "amount": txn.amount,
        "description": txn.description,
        "category": txn.category or "Miscellaneous",
        "receipt_url": txn.receipt_url,
        "date": txn.date,
        "notes": txn.notes,
        "balance_before": current_balance,
        "balance_after": new_balance,
        "status": "pending" if requires_approval else "approved",
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": get_malaysia_time().isoformat(),
        "approved_by": None if requires_approval else current_user.id,
        "approved_at": None if requires_approval else get_malaysia_time().isoformat()
    }
    
    await db.petty_cash_transactions.insert_one(transaction)
    
    if not requires_approval:
        await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": new_balance}})
        # Auto-post journal entry for approved petty cash
        if create_auto_journal_entry:
            try:
                if txn.type == "expense":
                    lines = [
                        {"account_code": "6600", "debit": round(txn.amount, 2), "credit": 0, "memo": txn.description},
                        {"account_code": "1010", "debit": 0, "credit": round(txn.amount, 2), "memo": "Petty Cash"},
                    ]
                else:  # topup
                    lines = [
                        {"account_code": "1010", "debit": round(txn.amount, 2), "credit": 0, "memo": "Petty Cash Top-up"},
                        {"account_code": "1000", "debit": 0, "credit": round(txn.amount, 2), "memo": "Cash at Bank"},
                    ]
                await create_auto_journal_entry(
                    entry_date=txn.date, description=f"Petty Cash {txn.type}: {txn.description}",
                    source_module="petty_cash", source_id=transaction["id"], source_reference=f"PC-{transaction['id'][:8]}",
                    lines=lines,
                    created_by_id=current_user.id, created_by_name=current_user.full_name, skip_date_check=True
                )
            except Exception:
                pass
    
    return {
        "message": "Transaction added" + (" (pending approval)" if requires_approval else ""),
        "transaction_id": transaction["id"],
        "new_balance": new_balance if not requires_approval else current_balance,
        "requires_approval": requires_approval
    }


@router.get("/petty-cash/transactions")
async def get_petty_cash_transactions(
    year: int = None,
    month: int = None,
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get petty cash transactions"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        if month:
            start = f"{year}-{month:02d}-01"
            end = f"{year}-{month:02d}-31"
        query["date"] = {"$gte": start, "$lte": end}
    if status:
        query["status"] = status
    
    transactions = await db.petty_cash_transactions.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return transactions


@router.post("/petty-cash/approve/{transaction_id}")
async def approve_petty_cash_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Approve a pending transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    txn = await db.petty_cash_transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if txn.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Not pending")
    
    await db.petty_cash_transactions.update_one(
        {"id": transaction_id},
        {"$set": {"status": "approved", "approved_by": current_user.id, "approved_at": get_malaysia_time().isoformat()}}
    )
    
    settings = await db.petty_cash_settings.find_one({})
    new_balance = settings.get("current_balance", 0)
    if txn.get("type") == "expense":
        new_balance -= txn.get("amount", 0)
    elif txn.get("type") == "topup":
        new_balance += txn.get("amount", 0)
    
    await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": new_balance}})
    return {"message": "Approved", "new_balance": new_balance}


@router.post("/petty-cash/reject/{transaction_id}")
async def reject_petty_cash_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Reject a pending transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    txn = await db.petty_cash_transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if txn.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Not pending")
    
    await db.petty_cash_transactions.update_one(
        {"id": transaction_id},
        {"$set": {"status": "rejected", "rejected_by": current_user.id, "rejected_at": get_malaysia_time().isoformat()}}
    )
    return {"message": "Rejected"}


@router.delete("/petty-cash/transaction/{transaction_id}")
async def delete_petty_cash_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Delete a transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    txn = await db.petty_cash_transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    
    if txn.get("status") == "approved":
        settings = await db.petty_cash_settings.find_one({})
        current_balance = settings.get("current_balance", 0)
        if txn.get("type") == "expense":
            new_balance = current_balance + txn.get("amount", 0)
        elif txn.get("type") == "topup":
            new_balance = current_balance - txn.get("amount", 0)
        else:
            new_balance = current_balance
        await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": new_balance}})
    
    await db.petty_cash_transactions.delete_one({"id": transaction_id})
    return {"message": "Deleted"}


@router.post("/petty-cash/reconcile")
async def reconcile_petty_cash(recon: PettyCashReconciliation, current_user: User = Depends(get_current_user)):
    """Reconcile petty cash"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.petty_cash_settings.find_one({})
    if not settings:
        raise HTTPException(status_code=400, detail="Not set up")
    
    system_balance = settings.get("current_balance", 0)
    variance = recon.physical_count - system_balance
    
    reconciliation = {
        "id": str(uuid.uuid4()),
        "date": get_malaysia_time().isoformat()[:10],
        "system_balance": system_balance,
        "physical_count": recon.physical_count,
        "variance": variance,
        "notes": recon.notes,
        "reconciled_by": current_user.id,
        "reconciled_by_name": current_user.full_name,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.petty_cash_reconciliations.insert_one(reconciliation)
    await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": recon.physical_count, "last_reconciliation": reconciliation["date"]}})
    
    if abs(variance) > 0.01:
        adjustment = {
            "id": str(uuid.uuid4()),
            "type": "adjustment",
            "amount": abs(variance),
            "description": f"Reconciliation adjustment",
            "category": "Adjustment",
            "date": get_malaysia_time().isoformat()[:10],
            "notes": recon.notes,
            "balance_before": system_balance,
            "balance_after": recon.physical_count,
            "status": "approved",
            "created_by": current_user.id,
            "created_by_name": current_user.full_name,
            "created_at": get_malaysia_time().isoformat(),
            "approved_by": current_user.id,
            "approved_at": get_malaysia_time().isoformat()
        }
        await db.petty_cash_transactions.insert_one(adjustment)
    
    return {"message": "Complete", "system_balance": system_balance, "physical_count": recon.physical_count, "variance": variance, "new_balance": recon.physical_count}


@router.get("/petty-cash/reconciliations")
async def get_reconciliation_history(current_user: User = Depends(get_current_user)):
    """Get reconciliation history"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    reconciliations = await db.petty_cash_reconciliations.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return reconciliations


@router.get("/petty-cash/summary")
async def get_petty_cash_summary(year: int = None, current_user: User = Depends(get_current_user)):
    """Get petty cash summary"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    query = {"date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}, "type": "expense", "status": "approved"}
    transactions = await db.petty_cash_transactions.find(query, {"_id": 0}).to_list(10000)
    
    by_category = {}
    for txn in transactions:
        cat = txn.get("category", "Miscellaneous")
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += txn.get("amount", 0)
    
    by_month = {}
    for txn in transactions:
        try:
            m = int(txn.get("date", "")[5:7])
            if m not in by_month:
                by_month[m] = 0
            by_month[m] += txn.get("amount", 0)
        except:
            pass
    
    settings = await db.petty_cash_settings.find_one({}, {"_id": 0})
    
    return {
        "year": year,
        "current_balance": settings.get("current_balance", 0) if settings else 0,
        "float_amount": settings.get("float_amount", 0) if settings else 0,
        "by_category": by_category,
        "by_month": by_month,
        "total_expenses": sum(c["total"] for c in by_category.values())
    }
