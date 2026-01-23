"""
Finance Reports routes - P&L, Subledgers, Chart of Accounts, General Ledger
Stage F5: ~12 endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core import db, get_current_user, get_malaysia_time
from models import User

router = APIRouter(prefix="/finance", tags=["finance-reports"])


# Chart of Accounts - Static configuration
CHART_OF_ACCOUNTS = {
    # Assets (1xxx)
    "1001": {"name": "Cash at Bank", "type": "Asset"},
    "1002": {"name": "Petty Cash", "type": "Asset"},
    "1100": {"name": "Accounts Receivable", "type": "Asset"},
    
    # Liabilities (2xxx)
    "2001": {"name": "Accounts Payable", "type": "Liability"},
    "2100": {"name": "Trainer Payable", "type": "Liability"},
    "2101": {"name": "Coordinator Payable", "type": "Liability"},
    "2102": {"name": "Marketing Commission Payable", "type": "Liability"},
    "2200": {"name": "EPF Payable", "type": "Liability"},
    "2201": {"name": "SOCSO Payable", "type": "Liability"},
    "2202": {"name": "EIS Payable", "type": "Liability"},
    "2210": {"name": "Salary Payable", "type": "Liability"},
    
    # Income (4xxx)
    "4000": {"name": "Training Income - General", "type": "Income"},
    "4001": {"name": "Training Income - Cars", "type": "Income"},
    "4002": {"name": "Training Income - Motorcycles", "type": "Income"},
    "4003": {"name": "Training Income - Heavy Vehicles", "type": "Income"},
    "4004": {"name": "Training Income - Bus", "type": "Income"},
    "4100": {"name": "Other Income", "type": "Income"},
    
    # Expenses (5xxx)
    "5001": {"name": "Trainer Fees", "type": "Expense"},
    "5002": {"name": "Coordinator Fees", "type": "Expense"},
    "5003": {"name": "Marketing Commission", "type": "Expense"},
    "5100": {"name": "Staff Salaries", "type": "Expense"},
    "5101": {"name": "EPF - Employer", "type": "Expense"},
    "5102": {"name": "SOCSO - Employer", "type": "Expense"},
    "5103": {"name": "EIS - Employer", "type": "Expense"},
    "5200": {"name": "F&B Expenses", "type": "Expense"},
    "5201": {"name": "Venue Expenses", "type": "Expense"},
    "5202": {"name": "HRDCorp Levy", "type": "Expense"},
    "5300": {"name": "Petty Cash Expenses", "type": "Expense"},
    "5400": {"name": "Other Expenses", "type": "Expense"},
}


@router.get("/profit-loss")
async def get_profit_loss_report(
    year: int = None,
    month: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get Profit/Loss report - monthly breakdown and YTD
    
    IMPORTANT: All session-related expenses (trainer fees, coordinator fees, 
    marketing commissions, session expenses) are attributed to the month based 
    on the SESSION'S START DATE, not the record's created_at date.
    """
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get sessions for the year to map expenses to correct months
    sessions = await db.sessions.find({
        "start_date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0, "id": 1, "start_date": 1, "invoice_id": 1}).to_list(10000)
    
    session_date_map = {}
    invoice_session_map = {}
    for s in sessions:
        session_date_map[s.get("id")] = s.get("start_date", "")
        if s.get("invoice_id"):
            invoice_session_map[s.get("invoice_id")] = s.get("id")
    
    # Get all data sources
    invoices = await db.invoices.find({}, {"_id": 0}).to_list(10000)
    manual_income = await db.manual_income.find({"date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0}).to_list(1000)
    payslips = await db.hr_payslips.find({"year": year}, {"_id": 0}).to_list(1000)
    pay_advice = await db.hr_pay_advices.find({"year": year}, {"_id": 0}).to_list(1000)
    all_trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    all_coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    all_session_expenses = await db.session_expenses.find({}, {"_id": 0}).to_list(10000)
    all_marketing_commissions = await db.marketing_commissions.find({"status": {"$in": ["pending", "approved", "paid"]}}, {"_id": 0}).to_list(10000)
    petty_cash = await db.petty_cash_transactions.find({"date": {"$gte": start_date, "$lte": end_date}, "type": "expense", "status": "approved"}, {"_id": 0}).to_list(1000)
    manual_expenses = await db.manual_expenses.find({"date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0}).to_list(1000)
    
    # Build monthly breakdown
    monthly_data = {}
    for m in range(1, 13):
        monthly_data[m] = {
            "month": m,
            "month_name": ["", "January", "February", "March", "April", "May", "June", 
                          "July", "August", "September", "October", "November", "December"][m],
            "income": {"invoices": 0, "manual": 0, "total": 0},
            "expenses": {"payroll": 0, "session_workers": 0, "marketing_commissions": 0, 
                        "session_expenses": 0, "petty_cash": 0, "manual": 0, "total": 0},
            "net_profit": 0
        }
    
    # Process invoices (income)
    for inv in invoices:
        try:
            if inv.get("status") not in ["approved", "paid"]:
                continue
            amount = float(inv.get("total_amount") or inv.get("amount") or 0)
            inv_id = inv.get("id")
            
            session_id = invoice_session_map.get(inv_id)
            if session_id and session_id in session_date_map:
                session_date = session_date_map[session_id]
                if session_date.startswith(str(year)):
                    inv_month = int(session_date[5:7])
                    monthly_data[inv_month]["income"]["invoices"] += amount
            else:
                inv_date = inv.get("created_at", "")[:10]
                if inv_date.startswith(str(year)):
                    inv_month = int(inv_date[5:7]) if len(inv_date) >= 7 else 1
                    monthly_data[inv_month]["income"]["invoices"] += amount
        except:
            pass
    
    # Process manual income
    for inc in manual_income:
        try:
            inc_month = int(inc.get("date", "")[5:7])
            monthly_data[inc_month]["income"]["manual"] += float(inc.get("amount", 0))
        except:
            pass
    
    # Process payroll
    for ps in payslips:
        try:
            ps_month = ps.get("month", 1)
            gross = float(ps.get("gross_salary", 0))
            epf_er = float(ps.get("epf_employer", 0))
            socso_er = float(ps.get("socso_employer", 0))
            eis_er = float(ps.get("eis_employer", 0))
            monthly_data[ps_month]["expenses"]["payroll"] += gross + epf_er + socso_er + eis_er
        except:
            pass
    
    # Process pay advice
    for pa in pay_advice:
        try:
            pa_month = pa.get("month", 1)
            monthly_data[pa_month]["expenses"]["session_workers"] += float(pa.get("amount", 0))
        except:
            pass
    
    # Process trainer fees
    for tf in all_trainer_fees:
        try:
            session_id = tf.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            tf_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            monthly_data[tf_month]["expenses"]["session_workers"] += float(tf.get("fee_amount") or 0)
        except:
            pass
    
    # Process coordinator fees
    for cf in all_coordinator_fees:
        try:
            session_id = cf.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            cf_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            monthly_data[cf_month]["expenses"]["session_workers"] += float(cf.get("total_fee") or 0)
        except:
            pass
    
    # Process session expenses
    for exp in all_session_expenses:
        try:
            session_id = exp.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            exp_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            amount = float(exp.get("actual_amount") or exp.get("estimated_amount") or exp.get("amount") or 0)
            monthly_data[exp_month]["expenses"]["session_expenses"] += amount
        except:
            pass
    
    # Process marketing commissions
    for mc in all_marketing_commissions:
        try:
            session_id = mc.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            mc_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            monthly_data[mc_month]["expenses"]["marketing_commissions"] += float(mc.get("calculated_amount") or 0)
        except:
            pass
    
    # Process petty cash
    for pc in petty_cash:
        try:
            pc_month = int(pc.get("date", "")[5:7])
            monthly_data[pc_month]["expenses"]["petty_cash"] += float(pc.get("amount", 0))
        except:
            pass
    
    # Process manual expenses
    for exp in manual_expenses:
        try:
            exp_month = int(exp.get("date", "")[5:7])
            monthly_data[exp_month]["expenses"]["manual"] += float(exp.get("amount", 0))
        except:
            pass
    
    # Calculate totals
    ytd_income = 0
    ytd_expenses = 0
    
    for m in range(1, 13):
        md = monthly_data[m]
        md["income"]["total"] = md["income"]["invoices"] + md["income"]["manual"]
        md["expenses"]["total"] = sum([md["expenses"]["payroll"], md["expenses"]["session_workers"],
                                       md["expenses"]["marketing_commissions"], md["expenses"]["session_expenses"],
                                       md["expenses"]["petty_cash"], md["expenses"]["manual"]])
        md["net_profit"] = md["income"]["total"] - md["expenses"]["total"]
        ytd_income += md["income"]["total"]
        ytd_expenses += md["expenses"]["total"]
    
    return {
        "year": year,
        "monthly_breakdown": list(monthly_data.values()),
        "ytd_summary": {
            "total_income": ytd_income,
            "total_expenses": ytd_expenses,
            "net_profit": ytd_income - ytd_expenses,
            "profit_margin": round((ytd_income - ytd_expenses) / ytd_income * 100, 2) if ytd_income > 0 else 0
        },
        "expense_breakdown": {
            "payroll": sum(md["expenses"]["payroll"] for md in monthly_data.values()),
            "session_workers": sum(md["expenses"]["session_workers"] for md in monthly_data.values()),
            "marketing_commissions": sum(md["expenses"]["marketing_commissions"] for md in monthly_data.values()),
            "session_expenses": sum(md["expenses"]["session_expenses"] for md in monthly_data.values()),
            "petty_cash": sum(md["expenses"]["petty_cash"] for md in monthly_data.values()),
            "manual": sum(md["expenses"]["manual"] for md in monthly_data.values())
        }
    }


@router.get("/profit-loss/by-programme")
async def get_profit_loss_by_programme(
    year: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get Profit/Loss report broken down by programme (dynamic)."""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1, "category": 1}).to_list(100)
    programme_map = {p["id"]: p for p in programmes}
    
    sessions = await db.sessions.find({"start_date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0}).to_list(10000)
    
    session_to_programme = {}
    invoice_to_session = {}
    
    for s in sessions:
        sid = s.get("id")
        session_to_programme[sid] = s.get("program_id")
        if s.get("invoice_id"):
            invoice_to_session[s.get("invoice_id")] = sid
    
    programme_data = {}
    for prog in programmes:
        programme_data[prog["id"]] = {
            "programme_id": prog["id"],
            "programme_name": prog.get("name", "Unknown"),
            "category": prog.get("category", ""),
            "income": 0,
            "expenses": {"trainer_fees": 0, "coordinator_fees": 0, "marketing_commissions": 0, "session_expenses": 0, "total": 0},
            "gross_profit": 0,
            "gross_margin_pct": 0,
            "session_count": 0
        }
    
    programme_data["_other"] = {
        "programme_id": "_other",
        "programme_name": "Other / Unassigned",
        "category": "Other",
        "income": 0,
        "expenses": {"trainer_fees": 0, "coordinator_fees": 0, "marketing_commissions": 0, "session_expenses": 0, "total": 0},
        "gross_profit": 0,
        "gross_margin_pct": 0,
        "session_count": 0
    }
    
    for s in sessions:
        prog_id = s.get("program_id") or "_other"
        if prog_id in programme_data:
            programme_data[prog_id]["session_count"] += 1
    
    invoices = await db.invoices.find({"status": {"$in": ["approved", "issued", "paid"]}}, {"_id": 0}).to_list(10000)
    
    for inv in invoices:
        try:
            amount = float(inv.get("total_amount") or inv.get("amount") or 0)
            inv_id = inv.get("id")
            session_id = invoice_to_session.get(inv_id)
            prog_id = session_to_programme.get(session_id, "_other") if session_id else "_other"
            
            if session_id and session_id in session_to_programme:
                if prog_id in programme_data:
                    programme_data[prog_id]["income"] += amount
                else:
                    programme_data["_other"]["income"] += amount
            else:
                inv_date = inv.get("created_at", "")[:10]
                if inv_date.startswith(str(year)):
                    programme_data["_other"]["income"] += amount
        except:
            pass
    
    trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    for tf in trainer_fees:
        try:
            session_id = tf.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                programme_data[prog_id]["expenses"]["trainer_fees"] += float(tf.get("fee_amount") or 0)
        except:
            pass
    
    coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    for cf in coordinator_fees:
        try:
            session_id = cf.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                programme_data[prog_id]["expenses"]["coordinator_fees"] += float(cf.get("total_fee") or 0)
        except:
            pass
    
    marketing_comms = await db.marketing_commissions.find({"status": {"$in": ["pending", "approved", "paid"]}}, {"_id": 0}).to_list(10000)
    for mc in marketing_comms:
        try:
            session_id = mc.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                programme_data[prog_id]["expenses"]["marketing_commissions"] += float(mc.get("calculated_amount") or 0)
        except:
            pass
    
    session_expenses = await db.session_expenses.find({}, {"_id": 0}).to_list(10000)
    for exp in session_expenses:
        try:
            session_id = exp.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                amount = float(exp.get("actual_amount") or exp.get("estimated_amount") or exp.get("amount") or 0)
                programme_data[prog_id]["expenses"]["session_expenses"] += amount
        except:
            pass
    
    total_income = 0
    total_direct_expenses = 0
    
    for prog_id, data in programme_data.items():
        data["expenses"]["total"] = sum([data["expenses"]["trainer_fees"], data["expenses"]["coordinator_fees"],
                                         data["expenses"]["marketing_commissions"], data["expenses"]["session_expenses"]])
        data["gross_profit"] = data["income"] - data["expenses"]["total"]
        data["gross_margin_pct"] = round((data["gross_profit"] / data["income"] * 100), 2) if data["income"] > 0 else 0
        total_income += data["income"]
        total_direct_expenses += data["expenses"]["total"]
    
    payslips = await db.hr_payslips.find({"year": year}, {"_id": 0}).to_list(1000)
    overhead_payroll = sum(float(ps.get("gross_salary", 0)) + float(ps.get("epf_employer", 0)) + 
                          float(ps.get("socso_employer", 0)) + float(ps.get("eis_employer", 0)) for ps in payslips)
    
    petty_cash = await db.petty_cash_transactions.find({"date": {"$gte": start_date, "$lte": end_date}, "type": "expense", "status": "approved"}, {"_id": 0}).to_list(1000)
    overhead_petty_cash = sum(float(pc.get("amount", 0)) for pc in petty_cash)
    
    manual_expenses = await db.manual_expenses.find({"date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0}).to_list(1000)
    overhead_manual = sum(float(exp.get("amount", 0)) for exp in manual_expenses)
    
    manual_income = await db.manual_income.find({"date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0}).to_list(1000)
    other_income = sum(float(inc.get("amount", 0)) for inc in manual_income)
    
    total_overhead = overhead_payroll + overhead_petty_cash + overhead_manual
    total_expenses = total_direct_expenses + total_overhead
    net_profit = total_income + other_income - total_expenses
    
    active_programmes = [data for data in programme_data.values() if data["income"] > 0 or data["expenses"]["total"] > 0]
    active_programmes.sort(key=lambda x: x["income"], reverse=True)
    
    return {
        "year": year,
        "programmes": active_programmes,
        "summary": {
            "total_programme_income": total_income,
            "other_income": other_income,
            "total_income": total_income + other_income,
            "total_direct_costs": total_direct_expenses,
            "gross_profit": total_income - total_direct_expenses,
            "gross_margin_pct": round((total_income - total_direct_expenses) / total_income * 100, 2) if total_income > 0 else 0,
            "overhead": {"payroll": overhead_payroll, "petty_cash": overhead_petty_cash, "manual": overhead_manual, "total": total_overhead},
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "net_margin_pct": round(net_profit / (total_income + other_income) * 100, 2) if (total_income + other_income) > 0 else 0
        }
    }


@router.get("/subledger/trainers")
async def get_trainer_subledger(year: int = None, current_user: User = Depends(get_current_user)):
    """Get Trainer & Coordinator Sub-ledger - aggregated by person"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    sessions = await db.sessions.find({"start_date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0, "id": 1, "start_date": 1, "program_id": 1}).to_list(10000)
    session_ids = {s["id"] for s in sessions}
    session_map = {s["id"]: s for s in sessions}
    
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    programme_map = {p["id"]: p.get("name", "Unknown") for p in programmes}
    
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
    
    trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    
    trainer_data = {}
    for tf in trainer_fees:
        session_id = tf.get("session_id")
        if session_id not in session_ids:
            continue
        trainer_id = tf.get("trainer_id")
        if not trainer_id:
            continue
        
        if trainer_id not in trainer_data:
            trainer_data[trainer_id] = {"user_id": trainer_id, "name": user_map.get(trainer_id, tf.get("trainer_name", "Unknown")),
                                        "role": "Trainer", "total_earned": 0, "total_paid": 0, "balance": 0, "sessions": []}
        
        session = session_map.get(session_id, {})
        amount = float(tf.get("fee_amount") or 0)
        is_paid = tf.get("status") == "paid"
        
        trainer_data[trainer_id]["total_earned"] += amount
        if is_paid:
            trainer_data[trainer_id]["total_paid"] += amount
        
        trainer_data[trainer_id]["sessions"].append({
            "session_id": session_id, "date": session.get("start_date", ""),
            "programme": programme_map.get(session.get("program_id"), "Unknown"),
            "amount": amount, "status": tf.get("status", "pending")
        })
    
    coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    
    coordinator_data = {}
    for cf in coordinator_fees:
        session_id = cf.get("session_id")
        if session_id not in session_ids:
            continue
        coord_id = cf.get("coordinator_id")
        if not coord_id:
            continue
        
        if coord_id not in coordinator_data:
            coordinator_data[coord_id] = {"user_id": coord_id, "name": user_map.get(coord_id, cf.get("coordinator_name", "Unknown")),
                                          "role": "Coordinator", "total_earned": 0, "total_paid": 0, "balance": 0, "sessions": []}
        
        session = session_map.get(session_id, {})
        amount = float(cf.get("total_fee") or 0)
        is_paid = cf.get("status") == "paid"
        
        coordinator_data[coord_id]["total_earned"] += amount
        if is_paid:
            coordinator_data[coord_id]["total_paid"] += amount
        
        coordinator_data[coord_id]["sessions"].append({
            "session_id": session_id, "date": session.get("start_date", ""),
            "programme": programme_map.get(session.get("program_id"), "Unknown"),
            "amount": amount, "status": cf.get("status", "pending")
        })
    
    for data in trainer_data.values():
        data["balance"] = data["total_earned"] - data["total_paid"]
        data["sessions"].sort(key=lambda x: x["date"], reverse=True)
    
    for data in coordinator_data.values():
        data["balance"] = data["total_earned"] - data["total_paid"]
        data["sessions"].sort(key=lambda x: x["date"], reverse=True)
    
    trainers = sorted(trainer_data.values(), key=lambda x: x["total_earned"], reverse=True)
    coordinators = sorted(coordinator_data.values(), key=lambda x: x["total_earned"], reverse=True)
    
    return {
        "year": year, "trainers": trainers, "coordinators": coordinators,
        "totals": {
            "trainer_earned": sum(t["total_earned"] for t in trainers),
            "trainer_paid": sum(t["total_paid"] for t in trainers),
            "trainer_balance": sum(t["balance"] for t in trainers),
            "coordinator_earned": sum(c["total_earned"] for c in coordinators),
            "coordinator_paid": sum(c["total_paid"] for c in coordinators),
            "coordinator_balance": sum(c["balance"] for c in coordinators)
        }
    }


@router.get("/subledger/marketing")
async def get_marketing_subledger(year: int = None, current_user: User = Depends(get_current_user)):
    """Get Marketing Commission Sub-ledger - aggregated by marketer"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    sessions = await db.sessions.find({"start_date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0, "id": 1, "start_date": 1, "program_id": 1, "company_name": 1}).to_list(10000)
    session_ids = {s["id"] for s in sessions}
    session_map = {s["id"]: s for s in sessions}
    
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    programme_map = {p["id"]: p.get("name", "Unknown") for p in programmes}
    
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
    
    commissions = await db.marketing_commissions.find({}, {"_id": 0}).to_list(10000)
    
    marketer_data = {}
    for mc in commissions:
        session_id = mc.get("session_id")
        if session_id not in session_ids:
            continue
        marketer_id = mc.get("marketing_user_id") or mc.get("user_id")
        if not marketer_id:
            continue
        
        if marketer_id not in marketer_data:
            marketer_data[marketer_id] = {"user_id": marketer_id, "name": user_map.get(marketer_id, mc.get("marketer_name", "Unknown")),
                                          "total_commission": 0, "total_paid": 0, "balance": 0, "clients": []}
        
        session = session_map.get(session_id, {})
        amount = float(mc.get("calculated_amount") or 0)
        is_paid = mc.get("status") == "paid"
        
        marketer_data[marketer_id]["total_commission"] += amount
        if is_paid:
            marketer_data[marketer_id]["total_paid"] += amount
        
        marketer_data[marketer_id]["clients"].append({
            "session_id": session_id, "date": session.get("start_date", ""),
            "client": session.get("company_name", "Unknown"),
            "programme": programme_map.get(session.get("program_id"), "Unknown"),
            "commission_rate": mc.get("commission_rate", 0), "amount": amount, "status": mc.get("status", "pending")
        })
    
    for data in marketer_data.values():
        data["balance"] = data["total_commission"] - data["total_paid"]
        data["clients"].sort(key=lambda x: x["date"], reverse=True)
    
    marketers = sorted(marketer_data.values(), key=lambda x: x["total_commission"], reverse=True)
    
    return {
        "year": year, "marketers": marketers,
        "totals": {"total_commission": sum(m["total_commission"] for m in marketers),
                   "total_paid": sum(m["total_paid"] for m in marketers),
                   "total_balance": sum(m["balance"] for m in marketers)}
    }


@router.get("/subledger/payroll")
async def get_payroll_subledger(year: int = None, current_user: User = Depends(get_current_user)):
    """Get Staff Payroll Register - aggregated by employee"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    payslips = await db.hr_payslips.find({"year": year}, {"_id": 0}).to_list(1000)
    staff = await db.hr_staff.find({}, {"_id": 0}).to_list(1000)
    staff_map = {s["id"]: s for s in staff}
    
    employee_data = {}
    for ps in payslips:
        staff_id = ps.get("staff_id")
        if not staff_id:
            continue
        
        if staff_id not in employee_data:
            staff_info = staff_map.get(staff_id, {})
            employee_data[staff_id] = {
                "staff_id": staff_id, "name": ps.get("full_name") or staff_info.get("full_name", "Unknown"),
                "employee_id": staff_info.get("employee_id", ""), "designation": staff_info.get("designation", ""),
                "total_gross": 0, "total_epf": 0, "total_socso": 0, "total_eis": 0, "total_net": 0, "months": []
            }
        
        employee_data[staff_id]["total_gross"] += float(ps.get("gross_salary", 0))
        employee_data[staff_id]["total_epf"] += float(ps.get("epf_employee", 0))
        employee_data[staff_id]["total_socso"] += float(ps.get("socso_employee", 0))
        employee_data[staff_id]["total_eis"] += float(ps.get("eis_employee", 0))
        employee_data[staff_id]["total_net"] += float(ps.get("nett_pay", 0))
        
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        employee_data[staff_id]["months"].append({
            "month": ps.get("month"), "month_name": month_names[ps.get("month", 1)],
            "gross": float(ps.get("gross_salary", 0)), "epf": float(ps.get("epf_employee", 0)),
            "socso": float(ps.get("socso_employee", 0)), "eis": float(ps.get("eis_employee", 0)),
            "net": float(ps.get("nett_pay", 0))
        })
    
    for data in employee_data.values():
        data["months"].sort(key=lambda x: x["month"])
    
    employees = sorted(employee_data.values(), key=lambda x: x["name"])
    
    return {
        "year": year, "employees": employees,
        "totals": {"total_gross": sum(e["total_gross"] for e in employees),
                   "total_epf": sum(e["total_epf"] for e in employees),
                   "total_socso": sum(e["total_socso"] for e in employees),
                   "total_eis": sum(e["total_eis"] for e in employees),
                   "total_net": sum(e["total_net"] for e in employees)}
    }


@router.get("/chart-of-accounts")
async def get_chart_of_accounts(current_user: User = Depends(get_current_user)):
    """Get the Chart of Accounts"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    accounts = []
    for code, info in sorted(CHART_OF_ACCOUNTS.items()):
        accounts.append({"code": code, "name": info["name"], "type": info["type"]})
    return accounts


@router.get("/general-ledger")
async def get_general_ledger(year: int = None, month: int = None, current_user: User = Depends(get_current_user)):
    """Get General Ledger with double-entry transactions."""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    if month:
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    else:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
    
    gl_entries = []
    entry_id = 1
    
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    programme_map = {p["id"]: p.get("name", "Unknown") for p in programmes}
    
    sessions = await db.sessions.find({"start_date": {"$gte": start_date, "$lte": end_date}}, {"_id": 0}).to_list(10000)
    session_map = {s.get("id"): s for s in sessions}
    session_ids = set(session_map.keys())
    
    # 1. INVOICES - DR Accounts Receivable, CR Training Income
    invoices = await db.invoices.find({"status": {"$in": ["approved", "issued", "paid"]}}, {"_id": 0}).to_list(10000)
    
    for inv in invoices:
        try:
            session_id = None
            session = None
            
            for s in sessions:
                if s.get("invoice_id") == inv.get("id"):
                    session_id = s.get("id")
                    session = s
                    break
            
            if not session:
                inv_date = inv.get("created_at", "")[:10]
                if not (inv_date >= start_date and inv_date <= end_date):
                    continue
            
            amount = float(inv.get("total_amount") or inv.get("amount") or 0)
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date") if session else inv.get("created_at", "")[:10]
            ref = inv.get("invoice_number", f"INV-{inv.get('id', '')[:8]}")
            programme = programme_map.get(session.get("program_id"), "General") if session else "General"
            
            income_account = "4000"
            prog_name = programme.lower() if programme else ""
            if "car" in prog_name:
                income_account = "4001"
            elif "motorcycle" in prog_name or "motor" in prog_name:
                income_account = "4002"
            elif "heavy" in prog_name or "truck" in prog_name:
                income_account = "4003"
            elif "bus" in prog_name:
                income_account = "4004"
            
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": ref,
                              "description": f"Invoice issued - {inv.get('company_name', 'Customer')}",
                              "account_code": "1100", "account_name": CHART_OF_ACCOUNTS["1100"]["name"],
                              "debit": amount, "credit": 0, "tags": {"session_id": session_id, "programme": programme}})
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": ref,
                              "description": f"Invoice issued - {inv.get('company_name', 'Customer')}",
                              "account_code": income_account, "account_name": CHART_OF_ACCOUNTS[income_account]["name"],
                              "debit": 0, "credit": amount, "tags": {"session_id": session_id, "programme": programme}})
            entry_id += 1
        except:
            pass
    
    # 2. PAYMENTS RECEIVED - DR Bank, CR Accounts Receivable
    payments = await db.payments.find({}, {"_id": 0}).to_list(10000)
    for pmt in payments:
        try:
            pmt_date = pmt.get("payment_date", pmt.get("created_at", ""))[:10]
            if not (pmt_date >= start_date and pmt_date <= end_date):
                continue
            amount = float(pmt.get("amount", 0))
            if amount <= 0:
                continue
            ref = pmt.get("reference", f"PMT-{pmt.get('id', '')[:8]}")
            
            gl_entries.append({"entry_id": entry_id, "date": pmt_date, "reference": ref,
                              "description": f"Payment received - {pmt.get('payment_method', 'Bank')}",
                              "account_code": "1001", "account_name": CHART_OF_ACCOUNTS["1001"]["name"],
                              "debit": amount, "credit": 0, "tags": {}})
            gl_entries.append({"entry_id": entry_id, "date": pmt_date, "reference": ref,
                              "description": f"Payment received - {pmt.get('payment_method', 'Bank')}",
                              "account_code": "1100", "account_name": CHART_OF_ACCOUNTS["1100"]["name"],
                              "debit": 0, "credit": amount, "tags": {}})
            entry_id += 1
        except:
            pass
    
    # 3. TRAINER FEES - DR Trainer Fees Expense, CR Trainer Payable
    trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    for tf in trainer_fees:
        try:
            session_id = tf.get("session_id")
            if session_id not in session_ids:
                continue
            session = session_map.get(session_id, {})
            amount = float(tf.get("fee_amount", 0))
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date", tf.get("created_at", "")[:10])
            programme = programme_map.get(session.get("program_id"), "Unknown")
            
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": f"TF-{session_id[:8]}",
                              "description": f"Trainer fee accrual - {tf.get('trainer_name', 'Trainer')}",
                              "account_code": "5001", "account_name": CHART_OF_ACCOUNTS["5001"]["name"],
                              "debit": amount, "credit": 0, "tags": {"session_id": session_id, "programme": programme}})
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": f"TF-{session_id[:8]}",
                              "description": f"Trainer fee accrual - {tf.get('trainer_name', 'Trainer')}",
                              "account_code": "2100", "account_name": CHART_OF_ACCOUNTS["2100"]["name"],
                              "debit": 0, "credit": amount, "tags": {"session_id": session_id, "programme": programme}})
            entry_id += 1
        except:
            pass
    
    # 4. COORDINATOR FEES
    coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    for cf in coordinator_fees:
        try:
            session_id = cf.get("session_id")
            if session_id not in session_ids:
                continue
            session = session_map.get(session_id, {})
            amount = float(cf.get("total_fee", 0))
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date", cf.get("created_at", "")[:10])
            programme = programme_map.get(session.get("program_id"), "Unknown")
            
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": f"CF-{session_id[:8]}",
                              "description": f"Coordinator fee accrual - {cf.get('coordinator_name', 'Coordinator')}",
                              "account_code": "5002", "account_name": CHART_OF_ACCOUNTS["5002"]["name"],
                              "debit": amount, "credit": 0, "tags": {"session_id": session_id, "programme": programme}})
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": f"CF-{session_id[:8]}",
                              "description": f"Coordinator fee accrual - {cf.get('coordinator_name', 'Coordinator')}",
                              "account_code": "2101", "account_name": CHART_OF_ACCOUNTS["2101"]["name"],
                              "debit": 0, "credit": amount, "tags": {"session_id": session_id, "programme": programme}})
            entry_id += 1
        except:
            pass
    
    # 5. MARKETING COMMISSIONS
    marketing_comms = await db.marketing_commissions.find({"status": {"$in": ["approved", "paid"]}}, {"_id": 0}).to_list(10000)
    for mc in marketing_comms:
        try:
            session_id = mc.get("session_id")
            if session_id not in session_ids:
                continue
            session = session_map.get(session_id, {})
            amount = float(mc.get("calculated_amount", 0))
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date", mc.get("created_at", "")[:10])
            programme = programme_map.get(session.get("program_id"), "Unknown")
            
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": f"MC-{session_id[:8]}",
                              "description": f"Marketing commission - {mc.get('marketer_name', 'Marketer')}",
                              "account_code": "5003", "account_name": CHART_OF_ACCOUNTS["5003"]["name"],
                              "debit": amount, "credit": 0, "tags": {"session_id": session_id, "programme": programme}})
            gl_entries.append({"entry_id": entry_id, "date": trans_date, "reference": f"MC-{session_id[:8]}",
                              "description": f"Marketing commission - {mc.get('marketer_name', 'Marketer')}",
                              "account_code": "2102", "account_name": CHART_OF_ACCOUNTS["2102"]["name"],
                              "debit": 0, "credit": amount, "tags": {"session_id": session_id, "programme": programme}})
            entry_id += 1
        except:
            pass
    
    # Sort by date
    gl_entries.sort(key=lambda x: x["date"])
    
    # Summary by account
    account_summary = {}
    for entry in gl_entries:
        code = entry["account_code"]
        if code not in account_summary:
            account_summary[code] = {"account_code": code, "account_name": entry["account_name"], "total_debit": 0, "total_credit": 0}
        account_summary[code]["total_debit"] += entry["debit"]
        account_summary[code]["total_credit"] += entry["credit"]
    
    return {
        "year": year, "month": month,
        "entries": gl_entries,
        "account_summary": sorted(account_summary.values(), key=lambda x: x["account_code"]),
        "totals": {"total_debit": sum(e["debit"] for e in gl_entries), "total_credit": sum(e["credit"] for e in gl_entries)}
    }
