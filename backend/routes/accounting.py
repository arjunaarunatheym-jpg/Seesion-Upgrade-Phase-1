"""
Accounting Engine - Phase 1: Foundation
Double-Entry Accounting System for MDDRC Training Management

Collections:
- chart_of_accounts: Chart of Accounts (COA)
- journal_entries: Double-entry journal entries
- accounting_periods: Fiscal period control
- accounting_settings: System configuration
- journal_entry_counters: Atomic journal numbering
- accounting_audit_log: Audit trail

Endpoints: ~25
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field, ConfigDict, validator
from pymongo import ReturnDocument
import uuid

from core import db, get_current_user, get_malaysia_time
from models import User


router = APIRouter(prefix="/accounting", tags=["accounting"])


# ============ PYDANTIC MODELS ============

class ChartOfAccountCreate(BaseModel):
    """Create a new account in Chart of Accounts"""
    account_code: str = Field(..., min_length=3, max_length=10)
    account_name: str = Field(..., min_length=2, max_length=100)
    account_type: str = Field(..., pattern="^(Asset|Liability|Equity|Income|Expense)$")
    account_category: str = Field(..., min_length=2, max_length=50)
    parent_code: Optional[str] = None
    description: Optional[str] = None
    normal_balance: str = Field(default="debit", pattern="^(debit|credit)$")


class ChartOfAccountUpdate(BaseModel):
    """Update an existing account"""
    account_name: Optional[str] = None
    account_category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class JournalLine(BaseModel):
    """Single line in a journal entry (debit or credit)"""
    account_code: str
    debit: float = 0.0
    credit: float = 0.0
    memo: Optional[str] = None
    
    @validator('debit', 'credit')
    def round_to_two_decimals(cls, v):
        return round(float(v), 2)


class JournalEntryCreate(BaseModel):
    """Create a manual journal entry"""
    date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$")
    description: str = Field(..., min_length=5, max_length=500)
    lines: List[JournalLine] = Field(..., min_items=2)
    
    @validator('lines')
    def validate_balanced(cls, v):
        total_debit = sum(line.debit for line in v)
        total_credit = sum(line.credit for line in v)
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(f"Journal entry must be balanced. Debit: {total_debit}, Credit: {total_credit}")
        return v


class PeriodCloseRequest(BaseModel):
    """Request to close an accounting period"""
    reason: Optional[str] = None


class PeriodReopenRequest(BaseModel):
    """Request to reopen a closed period"""
    reason: str = Field(..., min_length=10)


# ============ HELPER FUNCTIONS ============

def round_money(value: float) -> float:
    """Round money to 2 decimal places using banker's rounding"""
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


async def log_accounting_action(
    action: str,
    entity_type: str,
    entity_id: str,
    performed_by: User,
    before_value: dict = None,
    after_value: dict = None,
    reason: str = None
):
    """Log accounting actions for audit trail"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_value": before_value,
        "after_value": after_value,
        "performed_by": performed_by.id,
        "performed_by_name": performed_by.full_name,
        "reason": reason,
        "timestamp": get_malaysia_time().isoformat()
    }
    await db.accounting_audit_log.insert_one(log_entry)
    return log_entry


async def get_next_journal_number(entry_date: str) -> str:
    """
    Generate atomic, unique journal entry number.
    Format: JE-YYYY-MM-XXXX
    Resets monthly.
    """
    year = entry_date[:4]
    month = entry_date[5:7]
    counter_key = f"JE-{year}-{month}"
    
    result = await db.journal_entry_counters.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    
    sequence = result["seq"]
    return f"{counter_key}-{str(sequence).zfill(4)}"


async def check_period_open(entry_date: str) -> bool:
    """Check if the accounting period is open for the given date"""
    year = int(entry_date[:4])
    month = int(entry_date[5:7])
    
    period = await db.accounting_periods.find_one(
        {"year": year, "month": month},
        {"_id": 0}
    )
    
    # If no period record exists, assume open (will be created on first use)
    if not period:
        return True
    
    return period.get("status") == "open"


async def get_account_by_code(account_code: str) -> dict:
    """Get account details by code"""
    account = await db.chart_of_accounts.find_one(
        {"account_code": account_code, "is_active": True},
        {"_id": 0}
    )
    return account


async def validate_journal_accounts(lines: List[JournalLine]) -> List[dict]:
    """Validate all accounts exist and are active, return enriched lines"""
    enriched_lines = []
    for i, line in enumerate(lines):
        account = await get_account_by_code(line.account_code)
        if not account:
            raise HTTPException(
                status_code=400, 
                detail=f"Account {line.account_code} not found or inactive"
            )
        enriched_lines.append({
            "line_no": i + 1,
            "account_code": line.account_code,
            "account_name": account["account_name"],
            "account_type": account["account_type"],
            "debit": round_money(line.debit),
            "credit": round_money(line.credit),
            "memo": line.memo or ""
        })
    return enriched_lines


# ============ INITIALIZATION ============

async def initialize_accounting_system():
    """Initialize accounting system with default COA and settings"""
    
    # Check if already initialized
    existing = await db.chart_of_accounts.count_documents({})
    if existing > 0:
        return {"message": "Accounting system already initialized", "accounts": existing}
    
    # Default Chart of Accounts
    default_coa = [
        # ASSETS (1000-1999)
        {"account_code": "1000", "account_name": "Cash at Bank", "account_type": "Asset", "account_category": "Bank", "normal_balance": "debit", "is_system": True},
        {"account_code": "1001", "account_name": "Petty Cash", "account_type": "Asset", "account_category": "Bank", "normal_balance": "debit", "is_system": True},
        {"account_code": "1100", "account_name": "Accounts Receivable", "account_type": "Asset", "account_category": "AR", "normal_balance": "debit", "is_system": True},
        {"account_code": "1200", "account_name": "Prepaid Expenses", "account_type": "Asset", "account_category": "Current Asset", "normal_balance": "debit", "is_system": False},
        
        # LIABILITIES (2000-2999)
        {"account_code": "2100", "account_name": "Accounts Payable", "account_type": "Liability", "account_category": "AP", "normal_balance": "credit", "is_system": True},
        {"account_code": "2200", "account_name": "SST Payable", "account_type": "Liability", "account_category": "Tax Liability", "normal_balance": "credit", "is_system": True},
        {"account_code": "2300", "account_name": "Deferred Revenue", "account_type": "Liability", "account_category": "Deferred", "normal_balance": "credit", "is_system": True},
        {"account_code": "2400", "account_name": "EPF Payable", "account_type": "Liability", "account_category": "Payroll Liability", "normal_balance": "credit", "is_system": True},
        {"account_code": "2450", "account_name": "SOCSO Payable", "account_type": "Liability", "account_category": "Payroll Liability", "normal_balance": "credit", "is_system": True},
        {"account_code": "2460", "account_name": "EIS Payable", "account_type": "Liability", "account_category": "Payroll Liability", "normal_balance": "credit", "is_system": True},
        {"account_code": "2470", "account_name": "PCB Payable", "account_type": "Liability", "account_category": "Payroll Liability", "normal_balance": "credit", "is_system": True},
        {"account_code": "2500", "account_name": "Accrued Expenses", "account_type": "Liability", "account_category": "Current Liability", "normal_balance": "credit", "is_system": False},
        
        # EQUITY (3000-3999)
        {"account_code": "3000", "account_name": "Opening Balance Equity", "account_type": "Equity", "account_category": "Equity", "normal_balance": "credit", "is_system": True},
        {"account_code": "3100", "account_name": "Retained Earnings", "account_type": "Equity", "account_category": "Equity", "normal_balance": "credit", "is_system": True},
        
        # INCOME (4000-4999)
        {"account_code": "4000", "account_name": "Training Revenue", "account_type": "Income", "account_category": "Revenue", "normal_balance": "credit", "is_system": True},
        {"account_code": "4100", "account_name": "Other Income", "account_type": "Income", "account_category": "Revenue", "normal_balance": "credit", "is_system": False},
        
        # EXPENSES (5000-6999)
        {"account_code": "5000", "account_name": "Trainer Fees", "account_type": "Expense", "account_category": "Direct Cost", "normal_balance": "debit", "is_system": True},
        {"account_code": "5100", "account_name": "Coordinator Fees", "account_type": "Expense", "account_category": "Direct Cost", "normal_balance": "debit", "is_system": True},
        {"account_code": "5200", "account_name": "Marketing Commission", "account_type": "Expense", "account_category": "Direct Cost", "normal_balance": "debit", "is_system": True},
        {"account_code": "5300", "account_name": "Training Materials", "account_type": "Expense", "account_category": "Direct Cost", "normal_balance": "debit", "is_system": False},
        {"account_code": "5400", "account_name": "Venue & Logistics", "account_type": "Expense", "account_category": "Direct Cost", "normal_balance": "debit", "is_system": False},
        {"account_code": "5500", "account_name": "Transportation", "account_type": "Expense", "account_category": "Direct Cost", "normal_balance": "debit", "is_system": False},
        {"account_code": "6000", "account_name": "Salary & Wages", "account_type": "Expense", "account_category": "Operating Expense", "normal_balance": "debit", "is_system": True},
        {"account_code": "6100", "account_name": "EPF Employer Contribution", "account_type": "Expense", "account_category": "Operating Expense", "normal_balance": "debit", "is_system": True},
        {"account_code": "6200", "account_name": "SOCSO Employer Contribution", "account_type": "Expense", "account_category": "Operating Expense", "normal_balance": "debit", "is_system": True},
        {"account_code": "6300", "account_name": "EIS Employer Contribution", "account_type": "Expense", "account_category": "Operating Expense", "normal_balance": "debit", "is_system": True},
        {"account_code": "6400", "account_name": "Office Expenses", "account_type": "Expense", "account_category": "Operating Expense", "normal_balance": "debit", "is_system": False},
        {"account_code": "6500", "account_name": "Utilities", "account_type": "Expense", "account_category": "Operating Expense", "normal_balance": "debit", "is_system": False},
        {"account_code": "6600", "account_name": "Petty Cash Expenses", "account_type": "Expense", "account_category": "Operating Expense", "normal_balance": "debit", "is_system": False},
    ]
    
    now = get_malaysia_time().isoformat()
    for account in default_coa:
        account["id"] = str(uuid.uuid4())
        account["is_active"] = True
        account["description"] = ""
        account["parent_code"] = None
        account["created_by"] = "system"
        account["created_at"] = now
        account["updated_at"] = now
    
    await db.chart_of_accounts.insert_many(default_coa)
    
    # Create indexes
    await db.chart_of_accounts.create_index("account_code", unique=True)
    await db.chart_of_accounts.create_index("account_type")
    await db.chart_of_accounts.create_index("is_active")
    
    await db.journal_entries.create_index("journal_no", unique=True)
    await db.journal_entries.create_index("date")
    await db.journal_entries.create_index("source_module")
    await db.journal_entries.create_index("source_id")
    await db.journal_entries.create_index("status")
    await db.journal_entries.create_index([("date", 1), ("status", 1)])
    await db.journal_entries.create_index("lines.account_code")
    
    await db.accounting_periods.create_index([("year", 1), ("month", 1)], unique=True)
    await db.accounting_audit_log.create_index("timestamp")
    await db.accounting_audit_log.create_index("entity_type")
    
    # Default accounting settings
    settings = {
        "id": "accounting_settings",
        "fiscal_year_start_month": 1,
        "accounting_start_date": "2026-01-01",
        "default_currency": "MYR",
        "use_deferred_revenue": True,
        "auto_post_invoices": True,
        "auto_post_payments": True,
        "auto_post_expenses": True,
        "auto_post_payroll": True,
        "default_bank_account": "1000",
        "default_ar_account": "1100",
        "default_ap_account": "2100",
        "default_revenue_account": "4000",
        "default_deferred_revenue_account": "2300",
        "default_sst_account": "2200",
        "created_at": now,
        "updated_at": now
    }
    await db.accounting_settings.update_one(
        {"id": "accounting_settings"},
        {"$set": settings},
        upsert=True
    )
    
    # Create Jan and Feb 2026 periods as open
    for month in [1, 2]:
        period = {
            "id": str(uuid.uuid4()),
            "year": 2026,
            "month": month,
            "period_name": f"{'January' if month == 1 else 'February'} 2026",
            "status": "open",
            "closed_by": None,
            "closed_at": None,
            "created_at": now
        }
        await db.accounting_periods.update_one(
            {"year": 2026, "month": month},
            {"$setOnInsert": period},
            upsert=True
        )
    
    return {"message": "Accounting system initialized", "accounts": len(default_coa)}


# ============ CHART OF ACCOUNTS ENDPOINTS ============

@router.post("/initialize")
async def initialize_accounting(current_user: User = Depends(get_current_user)):
    """Initialize the accounting system with default COA and settings (Super Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Super Admin can initialize accounting")
    
    result = await initialize_accounting_system()
    
    await log_accounting_action(
        action="system_initialized",
        entity_type="system",
        entity_id="accounting",
        performed_by=current_user,
        after_value=result
    )
    
    return result


@router.get("/chart-of-accounts")
async def get_chart_of_accounts(
    account_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user)
):
    """Get all accounts in the Chart of Accounts"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if account_type:
        query["account_type"] = account_type
    if is_active is not None:
        query["is_active"] = is_active
    
    accounts = await db.chart_of_accounts.find(query, {"_id": 0}).sort("account_code", 1).to_list(500)
    
    # Group by account type for easier display
    grouped = {
        "Asset": [],
        "Liability": [],
        "Equity": [],
        "Income": [],
        "Expense": []
    }
    for account in accounts:
        acc_type = account.get("account_type", "Asset")
        if acc_type in grouped:
            grouped[acc_type].append(account)
    
    return {
        "accounts": accounts,
        "grouped": grouped,
        "total": len(accounts)
    }


@router.post("/chart-of-accounts")
async def create_account(
    account_data: ChartOfAccountCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new account in the Chart of Accounts (Super Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Super Admin can create accounts")
    
    # Check if account code already exists
    existing = await db.chart_of_accounts.find_one({"account_code": account_data.account_code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Account code {account_data.account_code} already exists")
    
    # Validate parent account if provided
    if account_data.parent_code:
        parent = await db.chart_of_accounts.find_one({"account_code": account_data.parent_code})
        if not parent:
            raise HTTPException(status_code=400, detail=f"Parent account {account_data.parent_code} not found")
    
    now = get_malaysia_time().isoformat()
    account = {
        "id": str(uuid.uuid4()),
        "account_code": account_data.account_code,
        "account_name": account_data.account_name,
        "account_type": account_data.account_type,
        "account_category": account_data.account_category,
        "parent_code": account_data.parent_code,
        "description": account_data.description or "",
        "normal_balance": account_data.normal_balance,
        "is_system": False,
        "is_active": True,
        "created_by": current_user.id,
        "created_at": now,
        "updated_at": now
    }
    
    await db.chart_of_accounts.insert_one(account)
    
    await log_accounting_action(
        action="account_created",
        entity_type="chart_of_accounts",
        entity_id=account["id"],
        performed_by=current_user,
        after_value={"account_code": account["account_code"], "account_name": account["account_name"]}
    )
    
    account.pop("_id", None)
    return {"message": "Account created", "account": account}


@router.put("/chart-of-accounts/{account_code}")
async def update_account(
    account_code: str,
    update_data: ChartOfAccountUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an account in the Chart of Accounts (Super Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Super Admin can update accounts")
    
    account = await db.chart_of_accounts.find_one({"account_code": account_code}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Cannot change type of system accounts
    if account.get("is_system") and update_data.is_active is False:
        # Check if account has been used in journal entries
        used = await db.journal_entries.find_one({"lines.account_code": account_code, "status": "posted"})
        if used:
            raise HTTPException(status_code=400, detail="Cannot deactivate system account that has been used")
    
    update_fields = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    
    before_value = {"account_name": account.get("account_name"), "is_active": account.get("is_active")}
    
    await db.chart_of_accounts.update_one(
        {"account_code": account_code},
        {"$set": update_fields}
    )
    
    await log_accounting_action(
        action="account_updated",
        entity_type="chart_of_accounts",
        entity_id=account["id"],
        performed_by=current_user,
        before_value=before_value,
        after_value=update_fields
    )
    
    updated = await db.chart_of_accounts.find_one({"account_code": account_code}, {"_id": 0})
    return {"message": "Account updated", "account": updated}


# ============ JOURNAL ENTRY ENDPOINTS ============

@router.get("/journal-entries")
async def get_journal_entries(
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = None,
    source_module: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get journal entries with optional filters"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    
    if year and month:
        # Filter by specific month
        start_date = f"{year}-{str(month).zfill(2)}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{str(month + 1).zfill(2)}-01"
        query["date"] = {"$gte": start_date, "$lt": end_date}
    elif year:
        # Filter by year
        query["date"] = {"$gte": f"{year}-01-01", "$lt": f"{year + 1}-01-01"}
    
    if status:
        query["status"] = status
    
    if source_module:
        query["source_module"] = source_module
    
    entries = await db.journal_entries.find(query, {"_id": 0}).sort("date", -1).to_list(limit)
    
    return {
        "entries": entries,
        "count": len(entries),
        "filters": {"year": year, "month": month, "status": status, "source_module": source_module}
    }


@router.get("/journal-entries/{journal_id}")
async def get_journal_entry(journal_id: str, current_user: User = Depends(get_current_user)):
    """Get a single journal entry by ID"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    entry = await db.journal_entries.find_one({"id": journal_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    return entry


@router.post("/journal-entries")
async def create_journal_entry(
    entry_data: JournalEntryCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a manual journal entry (draft status)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can create journal entries")
    
    # Check if period is open
    if not await check_period_open(entry_data.date):
        raise HTTPException(status_code=400, detail="Cannot create journal entry in a closed period")
    
    # Validate and enrich lines with account names
    enriched_lines = await validate_journal_accounts(entry_data.lines)
    
    # Calculate totals
    total_debit = round_money(sum(line["debit"] for line in enriched_lines))
    total_credit = round_money(sum(line["credit"] for line in enriched_lines))
    
    # Generate journal number
    journal_no = await get_next_journal_number(entry_data.date)
    
    now = get_malaysia_time().isoformat()
    journal_entry = {
        "id": str(uuid.uuid4()),
        "journal_no": journal_no,
        "date": entry_data.date,
        "description": entry_data.description,
        "source_module": "manual",
        "source_id": None,
        "source_reference": None,
        "status": "draft",
        "lines": enriched_lines,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "is_balanced": abs(total_debit - total_credit) < 0.01,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "posted_by": None,
        "posted_at": None,
        "voided_by": None,
        "voided_at": None,
        "void_reason": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.journal_entries.insert_one(journal_entry)
    
    await log_accounting_action(
        action="journal_created",
        entity_type="journal_entry",
        entity_id=journal_entry["id"],
        performed_by=current_user,
        after_value={"journal_no": journal_no, "total_debit": total_debit, "total_credit": total_credit}
    )
    
    journal_entry.pop("_id", None)
    return {"message": "Journal entry created (draft)", "journal_entry": journal_entry}


@router.post("/journal-entries/{journal_id}/post")
async def post_journal_entry(journal_id: str, current_user: User = Depends(get_current_user)):
    """Post a draft journal entry"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can post journal entries")
    
    entry = await db.journal_entries.find_one({"id": journal_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    if entry.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft entries can be posted")
    
    if not entry.get("is_balanced"):
        raise HTTPException(status_code=400, detail="Cannot post unbalanced journal entry")
    
    # Check if period is still open
    if not await check_period_open(entry["date"]):
        raise HTTPException(status_code=400, detail="Cannot post to a closed period")
    
    now = get_malaysia_time().isoformat()
    await db.journal_entries.update_one(
        {"id": journal_id},
        {"$set": {
            "status": "posted",
            "posted_by": current_user.id,
            "posted_by_name": current_user.full_name,
            "posted_at": now,
            "updated_at": now
        }}
    )
    
    await log_accounting_action(
        action="journal_posted",
        entity_type="journal_entry",
        entity_id=journal_id,
        performed_by=current_user,
        before_value={"status": "draft"},
        after_value={"status": "posted"}
    )
    
    return {"message": "Journal entry posted", "journal_no": entry["journal_no"]}


@router.post("/journal-entries/{journal_id}/void")
async def void_journal_entry(
    journal_id: str,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """Void a posted journal entry"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Super Admin can void journal entries")
    
    if not reason or len(reason) < 10:
        raise HTTPException(status_code=400, detail="Void reason must be at least 10 characters")
    
    entry = await db.journal_entries.find_one({"id": journal_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    if entry.get("status") != "posted":
        raise HTTPException(status_code=400, detail="Only posted entries can be voided")
    
    now = get_malaysia_time().isoformat()
    await db.journal_entries.update_one(
        {"id": journal_id},
        {"$set": {
            "status": "voided",
            "voided_by": current_user.id,
            "voided_by_name": current_user.full_name,
            "voided_at": now,
            "void_reason": reason,
            "updated_at": now
        }}
    )
    
    await log_accounting_action(
        action="journal_voided",
        entity_type="journal_entry",
        entity_id=journal_id,
        performed_by=current_user,
        before_value={"status": "posted"},
        after_value={"status": "voided"},
        reason=reason
    )
    
    return {"message": "Journal entry voided", "journal_no": entry["journal_no"]}


# ============ ACCOUNTING PERIODS ============

@router.get("/periods")
async def get_accounting_periods(
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all accounting periods"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        query["year"] = year
    
    periods = await db.accounting_periods.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    
    return {"periods": periods, "count": len(periods)}


@router.post("/periods/{year}/{month}/close")
async def close_period(
    year: int,
    month: int,
    request: PeriodCloseRequest,
    current_user: User = Depends(get_current_user)
):
    """Close an accounting period (Super Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Super Admin can close periods")
    
    period = await db.accounting_periods.find_one({"year": year, "month": month}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Period is already closed")
    
    # Check for unposted journal entries in this period
    start_date = f"{year}-{str(month).zfill(2)}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{str(month + 1).zfill(2)}-01"
    
    unposted = await db.journal_entries.count_documents({
        "date": {"$gte": start_date, "$lt": end_date},
        "status": "draft"
    })
    
    if unposted > 0:
        raise HTTPException(status_code=400, detail=f"Cannot close period with {unposted} unposted journal entries")
    
    now = get_malaysia_time().isoformat()
    await db.accounting_periods.update_one(
        {"year": year, "month": month},
        {"$set": {
            "status": "closed",
            "closed_by": current_user.id,
            "closed_by_name": current_user.full_name,
            "closed_at": now,
            "close_reason": request.reason
        }}
    )
    
    await log_accounting_action(
        action="period_closed",
        entity_type="accounting_period",
        entity_id=period["id"],
        performed_by=current_user,
        after_value={"year": year, "month": month, "status": "closed"},
        reason=request.reason
    )
    
    month_name = ["", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"][month]
    
    return {"message": f"Period {month_name} {year} closed"}


@router.post("/periods/{year}/{month}/reopen")
async def reopen_period(
    year: int,
    month: int,
    request: PeriodReopenRequest,
    current_user: User = Depends(get_current_user)
):
    """Reopen a closed period (Super Admin only, with reason)"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="Only Super Admin can reopen periods")
    
    period = await db.accounting_periods.find_one({"year": year, "month": month}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.get("status") == "open":
        raise HTTPException(status_code=400, detail="Period is already open")
    
    now = get_malaysia_time().isoformat()
    await db.accounting_periods.update_one(
        {"year": year, "month": month},
        {"$set": {
            "status": "open",
            "reopened_by": current_user.id,
            "reopened_by_name": current_user.full_name,
            "reopened_at": now,
            "reopen_reason": request.reason
        }}
    )
    
    await log_accounting_action(
        action="period_reopened",
        entity_type="accounting_period",
        entity_id=period["id"],
        performed_by=current_user,
        before_value={"status": "closed"},
        after_value={"status": "open"},
        reason=request.reason
    )
    
    month_name = ["", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"][month]
    
    return {"message": f"Period {month_name} {year} reopened", "reason": request.reason}


# ============ SETTINGS ============

@router.get("/settings")
async def get_accounting_settings(current_user: User = Depends(get_current_user)):
    """Get accounting settings"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.accounting_settings.find_one({"id": "accounting_settings"}, {"_id": 0})
    if not settings:
        return {"message": "Accounting system not initialized. Call /accounting/initialize first."}
    
    return settings


@router.put("/settings")
async def update_accounting_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update accounting settings (Super Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Super Admin can update settings")
    
    # Protected fields that cannot be changed
    protected = ["id", "accounting_start_date", "created_at"]
    update_fields = {k: v for k, v in settings_data.items() if k not in protected}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    update_fields["updated_by"] = current_user.id
    
    await db.accounting_settings.update_one(
        {"id": "accounting_settings"},
        {"$set": update_fields}
    )
    
    await log_accounting_action(
        action="settings_updated",
        entity_type="accounting_settings",
        entity_id="accounting_settings",
        performed_by=current_user,
        after_value=update_fields
    )
    
    return {"message": "Settings updated", "updated_fields": list(update_fields.keys())}


# ============ TRIAL BALANCE ============

@router.get("/trial-balance")
async def get_trial_balance(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user)
):
    """Generate Trial Balance for a specific month"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all posted journal entries up to end of specified month
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{str(month + 1).zfill(2)}-01"
    
    # Aggregate debits and credits by account
    pipeline = [
        {"$match": {"status": "posted", "date": {"$lt": end_date}}},
        {"$unwind": "$lines"},
        {"$group": {
            "_id": "$lines.account_code",
            "account_name": {"$first": "$lines.account_name"},
            "total_debit": {"$sum": "$lines.debit"},
            "total_credit": {"$sum": "$lines.credit"}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = await db.journal_entries.aggregate(pipeline).to_list(500)
    
    # Enrich with account details and calculate balances
    accounts = await db.chart_of_accounts.find({}, {"_id": 0}).to_list(500)
    account_map = {a["account_code"]: a for a in accounts}
    
    trial_balance = []
    total_debit = 0
    total_credit = 0
    
    for row in results:
        account_code = row["_id"]
        account = account_map.get(account_code, {})
        
        debit_total = round_money(row["total_debit"])
        credit_total = round_money(row["total_credit"])
        net_balance = debit_total - credit_total
        
        # Determine which column to show balance in based on normal balance
        normal_balance = account.get("normal_balance", "debit")
        if normal_balance == "debit":
            debit_balance = net_balance if net_balance >= 0 else 0
            credit_balance = abs(net_balance) if net_balance < 0 else 0
        else:
            credit_balance = abs(net_balance) if net_balance <= 0 else 0
            debit_balance = net_balance if net_balance > 0 else 0
        
        trial_balance.append({
            "account_code": account_code,
            "account_name": row["account_name"],
            "account_type": account.get("account_type", ""),
            "debit_balance": round_money(debit_balance),
            "credit_balance": round_money(credit_balance)
        })
        
        total_debit += debit_balance
        total_credit += credit_balance
    
    # Group by account type
    grouped = {"Asset": [], "Liability": [], "Equity": [], "Income": [], "Expense": []}
    for row in trial_balance:
        acc_type = row.get("account_type", "Asset")
        if acc_type in grouped:
            grouped[acc_type].append(row)
    
    month_name = ["", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"][month]
    
    return {
        "period": f"{month_name} {year}",
        "as_of_date": end_date,
        "trial_balance": trial_balance,
        "grouped": grouped,
        "totals": {
            "total_debit": round_money(total_debit),
            "total_credit": round_money(total_credit),
            "is_balanced": abs(total_debit - total_credit) < 0.01
        },
        "generated_at": get_malaysia_time().isoformat()
    }


# ============ GENERAL LEDGER ============

@router.get("/general-ledger/{account_code}")
async def get_general_ledger(
    account_code: str,
    year: int,
    month: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get General Ledger for a specific account"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify account exists
    account = await db.chart_of_accounts.find_one({"account_code": account_code}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Build date range
    if month:
        start_date = f"{year}-{str(month).zfill(2)}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{str(month + 1).zfill(2)}-01"
    else:
        start_date = f"{year}-01-01"
        end_date = f"{year + 1}-01-01"
    
    # Calculate opening balance (all entries before start_date)
    opening_pipeline = [
        {"$match": {"status": "posted", "date": {"$lt": start_date}}},
        {"$unwind": "$lines"},
        {"$match": {"lines.account_code": account_code}},
        {"$group": {
            "_id": None,
            "total_debit": {"$sum": "$lines.debit"},
            "total_credit": {"$sum": "$lines.credit"}
        }}
    ]
    
    opening_result = await db.journal_entries.aggregate(opening_pipeline).to_list(1)
    opening_debit = opening_result[0]["total_debit"] if opening_result else 0
    opening_credit = opening_result[0]["total_credit"] if opening_result else 0
    opening_balance = round_money(opening_debit - opening_credit)
    
    # Get transactions in the period
    entries = await db.journal_entries.find(
        {"status": "posted", "date": {"$gte": start_date, "$lt": end_date}, "lines.account_code": account_code},
        {"_id": 0}
    ).sort("date", 1).to_list(1000)
    
    # Build ledger with running balance
    ledger_entries = []
    running_balance = opening_balance
    
    for entry in entries:
        for line in entry.get("lines", []):
            if line["account_code"] == account_code:
                debit = round_money(line.get("debit", 0))
                credit = round_money(line.get("credit", 0))
                running_balance = round_money(running_balance + debit - credit)
                
                ledger_entries.append({
                    "date": entry["date"],
                    "journal_no": entry["journal_no"],
                    "description": entry["description"],
                    "memo": line.get("memo", ""),
                    "debit": debit,
                    "credit": credit,
                    "balance": running_balance
                })
    
    period_debit = round_money(sum(e["debit"] for e in ledger_entries))
    period_credit = round_money(sum(e["credit"] for e in ledger_entries))
    
    return {
        "account": account,
        "period": f"{year}" if not month else f"{year}-{str(month).zfill(2)}",
        "opening_balance": opening_balance,
        "entries": ledger_entries,
        "totals": {
            "period_debit": period_debit,
            "period_credit": period_credit,
            "closing_balance": running_balance
        },
        "generated_at": get_malaysia_time().isoformat()
    }


# ============ AUDIT LOG ============

@router.get("/audit-log")
async def get_accounting_audit_log(
    entity_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get accounting audit log"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Super Admin can view audit log")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    
    logs = await db.accounting_audit_log.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    return {"logs": logs, "count": len(logs)}
