"""
HR Module routes - Staff management, payroll, and statutory calculations
Endpoints: 27
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
from io import BytesIO

from core import db, get_current_user, get_malaysia_time
from models import User

router = APIRouter(prefix="/hr", tags=["hr"])


@router.get("/pay-advice/debug/{year}/{month}")
async def debug_pay_advice(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Debug endpoint: show exactly what bulk-generate would find for a given payment month."""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    training_month = month - 1
    training_year = year
    if training_month < 1:
        training_month = 12
        training_year = year - 1
    
    # Find sessions in training month
    all_sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "name": 1, "start_date": 1}).to_list(1000)
    matched_sessions = []
    parse_errors = []
    
    for s in all_sessions:
        sd = s.get("start_date")
        if not sd:
            continue
        try:
            if isinstance(sd, str):
                # Try multiple date formats
                sdt = None
                for fmt in [None, "%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        if fmt is None:
                            sdt = datetime.fromisoformat(sd.replace('Z', '+00:00'))
                        else:
                            sdt = datetime.strptime(sd, fmt)
                        break
                    except:
                        pass
                if sdt and sdt.year == training_year and sdt.month == training_month:
                    matched_sessions.append({"id": s["id"], "name": s.get("name"), "start_date": sd})
                elif not sdt:
                    parse_errors.append({"session": s.get("name"), "start_date": sd, "error": "Could not parse date"})
            else:
                if sd.year == training_year and sd.month == training_month:
                    matched_sessions.append({"id": s["id"], "name": s.get("name"), "start_date": str(sd)})
        except Exception as e:
            parse_errors.append({"session": s.get("name"), "start_date": str(sd), "error": str(e)})
    
    session_ids = [s["id"] for s in matched_sessions]
    
    # Find workers
    trainer_ids = set()
    coord_ids = set()
    mkt_ids = set()
    
    if session_ids:
        for tf in await db.trainer_fees.find({"session_id": {"$in": session_ids}}, {"_id": 0, "trainer_id": 1, "session_id": 1, "fee_amount": 1}).to_list(500):
            trainer_ids.add(tf.get("trainer_id"))
        for cf in await db.coordinator_fees.find({"session_id": {"$in": session_ids}}, {"_id": 0, "coordinator_id": 1, "session_id": 1, "total_fee": 1}).to_list(500):
            coord_ids.add(cf.get("coordinator_id"))
        for mc in await db.marketing_commissions.find({"session_id": {"$in": session_ids}}, {"_id": 0, "marketing_user_id": 1, "session_id": 1}).to_list(500):
            mkt_ids.add(mc.get("marketing_user_id"))
    
    # Check existing pay advice
    existing_count = await db.pay_advice.count_documents({"year": year, "month": month})
    existing_training = await db.pay_advice.count_documents({"training_year": training_year, "training_month": training_month})
    
    return {
        "payment_month": f"{year}-{str(month).zfill(2)}",
        "training_month": f"{training_year}-{str(training_month).zfill(2)}",
        "sessions_found": len(matched_sessions),
        "sessions": matched_sessions,
        "workers": {
            "trainers": len(trainer_ids),
            "coordinators": len(coord_ids),
            "marketers": len(mkt_ids),
            "total_unique": len(trainer_ids | coord_ids | mkt_ids)
        },
        "existing_pay_advice": {
            "by_payment_month": existing_count,
            "by_training_month": existing_training
        },
        "date_parse_errors": parse_errors,
        "all_session_dates": [{"name": s.get("name", "?"), "start_date": s.get("start_date")} for s in all_sessions[:20]]
    }




# =====================================================
# HELPER FUNCTIONS
# =====================================================

def calculate_age_from_nric(nric: str, reference_date: str = None) -> int:
    """Calculate age from Malaysian NRIC (first 6 digits = YYMMDD)"""
    if not nric or len(nric) < 6:
        return 30
    try:
        yy = int(nric[:2])
        mm = int(nric[2:4])
        dd = int(nric[4:6])
        current_year = datetime.now().year
        current_yy = current_year % 100
        if yy > current_yy + 5:
            year = 1900 + yy
        else:
            year = 2000 + yy
        dob = datetime(year, mm, dd)
        ref = datetime.fromisoformat(reference_date) if reference_date else datetime.now()
        age = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
        return max(18, min(age, 100))
    except:
        return 30


def calculate_age(date_of_birth: str, reference_date: str = None) -> int:
    """Calculate age from date of birth"""
    if not date_of_birth:
        return 30
    try:
        dob = datetime.fromisoformat(date_of_birth.replace('Z', '+00:00'))
        ref = datetime.fromisoformat(reference_date) if reference_date else datetime.now()
        return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
    except:
        return 30


def calculate_epf(basic_salary: float, age: int, custom_employee_rate: float = None, custom_employer_rate: float = None):
    """Calculate EPF contributions"""
    if age >= 60:
        employer_rate = 4.0
        employee_rate = 0.0
    else:
        employer_rate = custom_employer_rate if custom_employer_rate else (13.0 if basic_salary <= 5000 else 12.0)
        employee_rate = custom_employee_rate if custom_employee_rate else 11.0
    
    return {
        "employee_rate": employee_rate,
        "employer_rate": employer_rate,
        "employee_amount": round(basic_salary * employee_rate / 100, 2),
        "employer_amount": round(basic_salary * employer_rate / 100, 2)
    }


def calculate_socso(wages: float, age: int):
    """Calculate SOCSO contributions"""
    capped_wages = min(wages, 6000)
    if age >= 60:
        employer_rate, employee_rate = 1.25, 0.0
    else:
        employer_rate, employee_rate = 1.75, 0.5
    
    return {
        "employee_rate": employee_rate,
        "employer_rate": employer_rate,
        "employee_amount": round(capped_wages * employee_rate / 100, 2),
        "employer_amount": round(capped_wages * employer_rate / 100, 2),
        "capped_wages": capped_wages
    }


def calculate_eis(wages: float, age: int):
    """Calculate EIS contributions"""
    if age >= 60:
        return {"employee_rate": 0.0, "employer_rate": 0.0, "employee_amount": 0.0, "employer_amount": 0.0, "capped_wages": 0}
    
    capped_wages = min(wages, 6000)
    return {
        "employee_rate": 0.2,
        "employer_rate": 0.2,
        "employee_amount": round(capped_wages * 0.2 / 100, 2),
        "employer_amount": round(capped_wages * 0.2 / 100, 2),
        "capped_wages": capped_wages
    }


# =====================================================
# STAFF MANAGEMENT
# =====================================================

@router.get("/staff")
async def get_staff(current_user: User = Depends(get_current_user)):
    """Get all staff records with user details"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    staff_records = await db.hr_staff.find({}, {"_id": 0}).to_list(500)
    
    for staff in staff_records:
        if staff.get("user_id"):
            user = await db.users.find_one({"id": staff["user_id"]}, {"_id": 0, "full_name": 1, "email": 1, "id_number": 1})
            if user:
                staff["full_name"] = user.get("full_name") or staff.get("full_name")
                staff["email"] = user.get("email")
                if not staff.get("nric"):
                    staff["nric"] = user.get("id_number", "")
    
    return staff_records


@router.post("/staff")
async def create_staff(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new staff record"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can manage staff")
    
    staff_id = str(uuid.uuid4())
    
    full_name = None
    if data.get("user_id"):
        user = await db.users.find_one({"id": data["user_id"]}, {"_id": 0, "full_name": 1})
        full_name = user.get("full_name") if user else None
    
    staff_record = {
        "id": staff_id,
        "user_id": data.get("user_id"),
        "employee_id": data.get("employee_id"),
        "full_name": full_name or data.get("full_name", ""),
        "nric": data.get("nric", ""),
        "designation": data.get("designation", ""),
        "department": data.get("department", ""),
        "date_joined": data.get("date_joined"),
        "date_of_birth": data.get("date_of_birth"),
        "bank_name": data.get("bank_name", ""),
        "bank_account": data.get("bank_account", ""),
        "basic_salary": float(data.get("basic_salary", 0)),
        "housing_allowance": float(data.get("housing_allowance", 0)),
        "transport_allowance": float(data.get("transport_allowance", 0)),
        "meal_allowance": float(data.get("meal_allowance", 0)),
        "phone_allowance": float(data.get("phone_allowance", 0)),
        "other_allowance": float(data.get("other_allowance", 0)),
        "epf_number": data.get("epf_number", ""),
        "socso_number": data.get("socso_number", ""),
        "tax_number": data.get("tax_number", ""),
        "employee_epf_rate": float(data.get("employee_epf_rate", 11)),
        "employer_epf_rate": float(data.get("employer_epf_rate", 13)),
        "is_active": data.get("is_active", True),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_staff.insert_one(staff_record)
    return {"id": staff_id, "message": "Staff created successfully"}


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a staff record"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can manage staff")
    
    existing = await db.hr_staff.find_one({"id": staff_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    update_data = {
        "user_id": data.get("user_id", existing.get("user_id")),
        "full_name": data.get("full_name", existing.get("full_name", "")),
        "employee_id": data.get("employee_id", existing.get("employee_id")),
        "nric": data.get("nric", existing.get("nric", "")),
        "designation": data.get("designation", existing.get("designation")),
        "department": data.get("department", existing.get("department")),
        "date_joined": data.get("date_joined", existing.get("date_joined")),
        "date_of_birth": data.get("date_of_birth", existing.get("date_of_birth")),
        "bank_name": data.get("bank_name", existing.get("bank_name")),
        "bank_account": data.get("bank_account", existing.get("bank_account")),
        "basic_salary": float(data.get("basic_salary", existing.get("basic_salary", 0))),
        "housing_allowance": float(data.get("housing_allowance", existing.get("housing_allowance", 0))),
        "transport_allowance": float(data.get("transport_allowance", existing.get("transport_allowance", 0))),
        "meal_allowance": float(data.get("meal_allowance", existing.get("meal_allowance", 0))),
        "phone_allowance": float(data.get("phone_allowance", existing.get("phone_allowance", 0))),
        "other_allowance": float(data.get("other_allowance", existing.get("other_allowance", 0))),
        "epf_number": data.get("epf_number", existing.get("epf_number")),
        "socso_number": data.get("socso_number", existing.get("socso_number")),
        "tax_number": data.get("tax_number", existing.get("tax_number")),
        "employee_epf_rate": float(data.get("employee_epf_rate", existing.get("employee_epf_rate", 11))),
        "employer_epf_rate": float(data.get("employer_epf_rate", existing.get("employer_epf_rate", 13))),
        "is_active": data.get("is_active", existing.get("is_active", True)),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_staff.update_one({"id": staff_id}, {"$set": update_data})
    return {"message": "Staff updated successfully"}


@router.delete("/staff/{staff_id}")
async def delete_staff(staff_id: str, current_user: User = Depends(get_current_user)):
    """Delete a staff record"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can manage staff")
    
    result = await db.hr_staff.delete_one({"id": staff_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    return {"message": "Staff deleted successfully"}


@router.get("/payroll-status")
async def get_payroll_status(
    year: int = None,
    month: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get payroll status showing which staff have payslips for a given month"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = datetime.now(timezone.utc)
    if not year:
        year = now.year
    if not month:
        month = now.month
    
    # Get all active staff
    staff_list = await db.hr_staff.find(
        {"is_active": True}, {"_id": 0}
    ).to_list(500)
    
    # Get payslips for this period
    payslips = await db.payslips.find(
        {"year": year, "month": month}, {"_id": 0, "staff_id": 1, "net_salary": 1, "gross_salary": 1}
    ).to_list(500)
    
    paid_staff_ids = {p["staff_id"]: p for p in payslips}
    
    status = []
    for s in staff_list:
        payslip = paid_staff_ids.get(s["id"])
        status.append({
            "staff_id": s["id"],
            "full_name": s.get("full_name", ""),
            "designation": s.get("designation", ""),
            "department": s.get("department", ""),
            "basic_salary": s.get("basic_salary", 0),
            "user_id": s.get("user_id"),
            "has_payslip": payslip is not None,
            "net_salary": payslip.get("net_salary", 0) if payslip else None,
            "gross_salary": payslip.get("gross_salary", 0) if payslip else None,
        })
    
    paid_count = sum(1 for s in status if s["has_payslip"])
    
    return {
        "year": year,
        "month": month,
        "total_staff": len(status),
        "paid_count": paid_count,
        "unpaid_count": len(status) - paid_count,
        "staff": status
    }


@router.post("/staff/auto-link-users")
async def auto_link_staff_to_users(current_user: User = Depends(get_current_user)):
    """Auto-link hr_staff records to user accounts by matching name or email"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can manage staff")
    
    # Get all unlinked staff
    unlinked_staff = await db.hr_staff.find(
        {"$or": [{"user_id": None}, {"user_id": {"$exists": False}}]},
        {"_id": 0}
    ).to_list(500)
    
    if not unlinked_staff:
        return {"message": "All staff are already linked", "linked": 0}
    
    # Get all users that could be staff
    all_users = await db.users.find(
        {"role": {"$in": ["trainer", "coordinator", "marketing", "assistant_admin", "admin", "finance"]}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1, "id_number": 1}
    ).to_list(500)
    
    linked = 0
    for staff in unlinked_staff:
        staff_name = (staff.get("full_name") or "").strip().lower()
        staff_nric = (staff.get("nric") or "").strip()
        
        for user in all_users:
            user_name = (user.get("full_name") or "").strip().lower()
            user_ic = (user.get("id_number") or "").strip()
            
            # Match by name (case-insensitive) or NRIC/IC number
            if (staff_name and user_name and staff_name == user_name) or \
               (staff_nric and user_ic and staff_nric == user_ic):
                await db.hr_staff.update_one(
                    {"id": staff["id"]},
                    {"$set": {"user_id": user["id"], "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                linked += 1
                break
    
    return {"message": f"Linked {linked} staff to user accounts", "linked": linked, "total_unlinked": len(unlinked_staff)}


@router.post("/staff/{staff_id}/link-user/{user_id}")
async def manual_link_staff_to_user(staff_id: str, user_id: str, current_user: User = Depends(get_current_user)):
    """Manually link an hr_staff record to a user account"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can link staff")

    staff = await db.hr_staff.find_one({"id": staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "full_name": 1, "email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.hr_staff.update_one(
        {"id": staff_id},
        {"$set": {"user_id": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    return {"message": f"Linked {staff.get('full_name')} to user {user.get('full_name')}", "staff_id": staff_id, "user_id": user_id}


@router.delete("/staff/{staff_id}/unlink-user")
async def unlink_staff_from_user(staff_id: str, current_user: User = Depends(get_current_user)):
    """Unlink an hr_staff record from its user account"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can unlink staff")

    result = await db.hr_staff.update_one(
        {"id": staff_id},
        {"$set": {"user_id": None, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")

    return {"message": "User unlinked successfully", "staff_id": staff_id}


@router.get("/available-users")
async def get_available_users(current_user: User = Depends(get_current_user)):
    """Get users that can be linked as staff"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing_staff = await db.hr_staff.find({}, {"user_id": 1}).to_list(500)
    existing_user_ids = [s.get("user_id") for s in existing_staff if s.get("user_id")]
    
    users = await db.users.find(
        {
            "role": {"$in": ["trainer", "coordinator", "marketing", "assistant_admin", "admin", "finance"]},
            "id": {"$nin": existing_user_ids}
        },
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1, "id_number": 1}
    ).to_list(200)
    
    return users


# =====================================================
# PAYROLL PERIODS
# =====================================================

@router.get("/payroll-periods")
async def get_payroll_periods(year: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get all payroll periods"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {"year": year} if year else {}
    periods = await db.payroll_periods.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return periods


@router.post("/payroll-periods")
async def create_payroll_period(data: dict, current_user: User = Depends(get_current_user)):
    """Create or open a payroll period"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can manage payroll periods")
    
    year, month = data.get("year"), data.get("month")
    if not year or not month:
        raise HTTPException(status_code=400, detail="Year and month required")
    
    existing = await db.payroll_periods.find_one({"year": year, "month": month})
    if existing:
        raise HTTPException(status_code=400, detail="Payroll period already exists")
    
    period = {
        "id": str(uuid.uuid4()),
        "year": year,
        "month": month,
        "period_name": f"{year}-{str(month).zfill(2)}",
        "status": "open",
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "opened_by": current_user.email,
        "closed_at": None,
        "closed_by": None
    }
    
    await db.payroll_periods.insert_one(period)
    return {"id": period["id"], "message": "Payroll period created"}


@router.put("/payroll-periods/{period_id}/close")
async def close_payroll_period(period_id: str, current_user: User = Depends(get_current_user)):
    """Close a payroll period"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can close payroll periods")
    
    period = await db.payroll_periods.find_one({"id": period_id})
    if not period:
        raise HTTPException(status_code=404, detail="Payroll period not found")
    
    if period.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Period already closed")
    
    await db.payroll_periods.update_one(
        {"id": period_id},
        {"$set": {"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat(), "closed_by": current_user.email}}
    )
    
    await db.payslips.update_many({"period_id": period_id}, {"$set": {"is_locked": True}})
    return {"message": "Payroll period closed successfully"}


# =====================================================
# STATUTORY RATES
# =====================================================

@router.get("/statutory-rates")
async def get_statutory_rates(rate_type: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get uploaded statutory rates"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {"rate_type": rate_type} if rate_type else {}
    rates = await db.statutory_rates.find(query, {"_id": 0}).sort("min_wages", 1).to_list(500)
    return rates


@router.post("/statutory-rates/upload")
async def upload_statutory_rates(file: UploadFile = File(...), rate_type: str = Form(...), current_user: User = Depends(get_current_user)):
    """Upload Excel file with statutory contribution rates"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can upload statutory rates")
    
    if rate_type not in ["epf", "socso", "eis"]:
        raise HTTPException(status_code=400, detail="Invalid rate type")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        import pandas as pd
        from io import BytesIO
        
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        await db.statutory_rates.delete_many({"rate_type": rate_type})
        
        records = []
        for _, row in df.iterrows():
            records.append({
                "id": str(uuid.uuid4()),
                "rate_type": rate_type,
                "min_wages": float(row.iloc[0]),
                "max_wages": float(row.iloc[1]),
                "employee_amount": float(row.iloc[2]),
                "employer_amount": float(row.iloc[3]),
                "total": float(row.iloc[4]) if len(row) > 4 else float(row.iloc[2]) + float(row.iloc[3]),
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "uploaded_by": current_user.email
            })
        
        if records:
            await db.statutory_rates.insert_many(records)
        
        return {"message": f"Uploaded {len(records)} {rate_type.upper()} rates successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@router.get("/statutory-rates/templates/{rate_type}")
async def download_statutory_template(rate_type: str, current_user: User = Depends(get_current_user)):
    """Download Excel template for statutory rates"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Admin or Finance access required")
    if rate_type not in ["epf", "socso", "eis"]:
        raise HTTPException(status_code=400, detail="Invalid rate type")
    
    import openpyxl
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{rate_type.upper()} Rates"
    
    headers = ["Min Wages (RM)", "Max Wages (RM)", "Employee Amount (RM)", "Employer Amount (RM)", "Total (RM)"]
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={rate_type}_rates_template.xlsx"}
    )


# =====================================================
# PAYSLIPS
# =====================================================

@router.get("/payslips")
async def get_payslips(staff_id: Optional[str] = None, period_id: Optional[str] = None, year: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get payslips with optional filters"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if staff_id: query["staff_id"] = staff_id
    if period_id: query["period_id"] = period_id
    if year: query["year"] = year
    
    payslips = await db.payslips.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(500)
    return payslips


@router.post("/payslips/generate")
async def generate_payslip(data: dict, current_user: User = Depends(get_current_user)):
    """Generate a payslip for a staff member with full details, YTD, and journal posting"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    staff_id = data.get("staff_id")
    year = data.get("year")
    month = data.get("month")
    
    staff = await db.hr_staff.find_one({"id": staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get NRIC
    nric = staff.get("nric", "")
    if not nric and staff.get("user_id"):
        user = await db.users.find_one({"id": staff["user_id"]}, {"_id": 0, "id_number": 1})
        nric = user.get("id_number", "") if user else ""
    
    # Check existing
    existing = await db.payslips.find_one({"staff_id": staff_id, "year": year, "month": month})
    if existing:
        raise HTTPException(status_code=400, detail="Payslip already exists for this period. Delete it first to regenerate.")
    
    # Check if payroll period is closed
    period = await db.payroll_periods.find_one({"year": year, "month": month}, {"_id": 0})
    if period and period.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Cannot generate payslip for closed period")
    
    # Calculate age
    age = calculate_age_from_nric(nric, f"{year}-{month:02d}-01") if nric else 30
    
    # Earnings - use provided values or fall back to staff defaults
    basic_salary = data.get("basic_salary") if data.get("basic_salary") is not None else staff.get("basic_salary", 0)
    fixed_allowance = data.get("fixed_allowance") if data.get("fixed_allowance") is not None else staff.get("fixed_allowance", 0)
    housing_allowance = data.get("housing_allowance") if data.get("housing_allowance") is not None else staff.get("housing_allowance", 0)
    transport_allowance = data.get("transport_allowance") if data.get("transport_allowance") is not None else staff.get("transport_allowance", 0)
    meal_allowance = data.get("meal_allowance") if data.get("meal_allowance") is not None else staff.get("meal_allowance", 0)
    phone_allowance = data.get("phone_allowance") if data.get("phone_allowance") is not None else staff.get("phone_allowance", 0)
    other_allowance = data.get("other_allowance") if data.get("other_allowance") is not None else staff.get("other_allowance", 0)
    total_allowances = fixed_allowance + housing_allowance + transport_allowance + meal_allowance + phone_allowance + other_allowance
    
    overtime = data.get("overtime", 0)
    bonus = data.get("bonus", 0)
    commission = data.get("commission", 0)
    incentives = data.get("incentives", 0)
    annual_leave_pay = data.get("annual_leave_pay", 0)
    other_earnings = data.get("other_earnings", 0)
    
    gross_salary = basic_salary + total_allowances + overtime + bonus + commission + incentives + annual_leave_pay + other_earnings
    
    # Statutory calculations
    epf = calculate_epf(basic_salary, age, staff.get("employee_epf_rate"), staff.get("employer_epf_rate"))
    socso = calculate_socso(gross_salary, age)
    eis = calculate_eis(gross_salary, age)
    
    # Allow overriding auto-calculated values
    epf_employee = data.get("epf_employee") if data.get("epf_employee") is not None else epf["employee_amount"]
    epf_employer = data.get("epf_employer") if data.get("epf_employer") is not None else epf["employer_amount"]
    socso_employee = data.get("socso_employee") if data.get("socso_employee") is not None else socso["employee_amount"]
    socso_employer = data.get("socso_employer") if data.get("socso_employer") is not None else socso["employer_amount"]
    eis_employee = data.get("eis_employee") if data.get("eis_employee") is not None else eis["employee_amount"]
    eis_employer = data.get("eis_employer") if data.get("eis_employer") is not None else eis["employer_amount"]
    
    pcb = data.get("pcb", 0)
    cp38 = data.get("cp38", 0)
    loan_deduction = data.get("loan_deduction", 0)
    mid_month_advance = data.get("mid_month_advance", 0)
    salary_adjustment = data.get("salary_adjustment", 0)
    unpaid_leave = data.get("unpaid_leave", 0)
    other_deductions = data.get("other_deductions", 0)
    
    total_deductions = round(epf_employee + socso_employee + eis_employee + pcb + cp38 + loan_deduction + mid_month_advance + salary_adjustment + unpaid_leave + other_deductions, 2)
    nett_pay = round(gross_salary - total_deductions, 2)
    
    # YTD calculation
    ytd_data = await db.payslips.aggregate([
        {"$match": {"staff_id": staff_id, "year": year, "month": {"$lt": month}}},
        {"$group": {
            "_id": None,
            "ytd_gross": {"$sum": "$gross_salary"},
            "ytd_epf_employee": {"$sum": "$epf_employee"},
            "ytd_epf_employer": {"$sum": "$epf_employer"},
            "ytd_socso_employee": {"$sum": "$socso_employee"},
            "ytd_socso_employer": {"$sum": "$socso_employer"},
            "ytd_eis_employee": {"$sum": "$eis_employee"},
            "ytd_eis_employer": {"$sum": "$eis_employer"},
            "ytd_pcb": {"$sum": "$pcb"},
            "ytd_nett": {"$sum": "$nett_pay"}
        }}
    ]).to_list(1)
    ytd = ytd_data[0] if ytd_data else {}
    
    payslip = {
        "id": str(uuid.uuid4()),
        "staff_id": staff_id,
        "period_id": period["id"] if period else None,
        "year": year,
        "month": month,
        "period_name": f"{year}-{str(month).zfill(2)}",
        
        # Staff info snapshot
        "employee_id": staff.get("employee_id"),
        "full_name": staff.get("full_name"),
        "nric": nric,
        "designation": staff.get("designation"),
        "department": staff.get("department"),
        "epf_number": staff.get("epf_number"),
        "socso_number": staff.get("socso_number"),
        "tax_number": staff.get("tax_number"),
        "bank_name": staff.get("bank_name"),
        "bank_account": staff.get("bank_account"),
        "age": age,
        
        # Earnings
        "basic_salary": basic_salary,
        "fixed_allowance": fixed_allowance,
        "housing_allowance": housing_allowance,
        "transport_allowance": transport_allowance,
        "meal_allowance": meal_allowance,
        "phone_allowance": phone_allowance,
        "other_allowance": other_allowance,
        "total_allowances": total_allowances,
        "overtime": overtime,
        "bonus": bonus,
        "commission": commission,
        "incentives": incentives,
        "annual_leave_pay": annual_leave_pay,
        "other_earnings": other_earnings,
        "gross_salary": gross_salary,
        
        # Deductions
        "epf_employee": epf_employee,
        "epf_employer": epf_employer,
        "epf_employee_rate": epf["employee_rate"],
        "epf_employer_rate": epf["employer_rate"],
        "socso_employee": socso_employee,
        "socso_employer": socso_employer,
        "eis_employee": eis_employee,
        "eis_employer": eis_employer,
        "pcb": pcb,
        "cp38": cp38,
        "loan_deduction": loan_deduction,
        "mid_month_advance": mid_month_advance,
        "salary_adjustment": salary_adjustment,
        "unpaid_leave": unpaid_leave,
        "other_deductions": other_deductions,
        "total_deductions": total_deductions,
        
        "nett_pay": nett_pay,
        
        # YTD (including current month)
        "ytd_gross": round(ytd.get("ytd_gross", 0) + gross_salary, 2),
        "ytd_epf_employee": round(ytd.get("ytd_epf_employee", 0) + epf_employee, 2),
        "ytd_epf_employer": round(ytd.get("ytd_epf_employer", 0) + epf_employer, 2),
        "ytd_socso_employee": round(ytd.get("ytd_socso_employee", 0) + socso_employee, 2),
        "ytd_socso_employer": round(ytd.get("ytd_socso_employer", 0) + socso_employer, 2),
        "ytd_eis_employee": round(ytd.get("ytd_eis_employee", 0) + eis_employee, 2),
        "ytd_eis_employer": round(ytd.get("ytd_eis_employer", 0) + eis_employer, 2),
        "ytd_pcb": round(ytd.get("ytd_pcb", 0) + pcb, 2),
        "ytd_nett": round(ytd.get("ytd_nett", 0) + nett_pay, 2),
        
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.email
    }
    
    await db.payslips.insert_one(payslip)
    
    # Post payroll journal entry
    try:
        from routes.accounting import post_payroll
        await post_payroll(payslip, user_id=current_user.id, user_name=current_user.full_name)
    except Exception as e:
        import logging
        logging.warning(f"Failed to post payroll journal entry: {e}")
    
    return {"id": payslip["id"], "message": "Payslip generated successfully", "nett_pay": nett_pay}


@router.get("/payslips/{payslip_id}")
async def get_payslip(payslip_id: str, current_user: User = Depends(get_current_user)):
    """Get a single payslip"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    payslip = await db.payslips.find_one({"id": payslip_id}, {"_id": 0})
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    return payslip


@router.delete("/payslips/{payslip_id}")
async def delete_payslip(payslip_id: str, current_user: User = Depends(get_current_user)):
    """Delete a payslip and void its associated journal entry"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete payslips")
    
    payslip = await db.payslips.find_one({"id": payslip_id})
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    if payslip.get("is_locked"):
        raise HTTPException(status_code=400, detail="Cannot delete locked payslip. Period is closed.")
    
    # Void associated journal entry
    try:
        journal = await db.journal_entries.find_one({
            "source_module": "payroll",
            "source_id": payslip_id,
            "status": {"$ne": "voided"}
        })
        if journal:
            now = datetime.now(timezone.utc).isoformat()
            await db.journal_entries.update_one(
                {"id": journal["id"]},
                {"$set": {
                    "status": "voided",
                    "voided_by": current_user.id,
                    "voided_by_name": current_user.full_name,
                    "voided_at": now,
                    "void_reason": f"Payslip deleted by {current_user.full_name}"
                }}
            )
    except Exception as e:
        import logging
        logging.warning(f"Failed to void payroll journal entry: {e}")
    
    await db.payslips.delete_one({"id": payslip_id})
    return {"message": "Payslip and associated journal entry deleted"}


@router.put("/payslips/{payslip_id}")
async def update_payslip(payslip_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a payslip - edit amounts, refresh staff info, recalculate, and re-post journal"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can edit payslips")
    
    payslip = await db.payslips.find_one({"id": payslip_id}, {"_id": 0})
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    if payslip.get("is_locked"):
        raise HTTPException(status_code=400, detail="Cannot edit locked payslip. Period is closed.")
    
    # If refresh_staff_info requested, pull latest from hr_staff
    if data.get("refresh_staff_info"):
        staff = await db.hr_staff.find_one({"id": payslip["staff_id"]}, {"_id": 0})
        if staff:
            payslip["designation"] = staff.get("designation", "")
            payslip["department"] = staff.get("department", "")
            payslip["epf_number"] = staff.get("epf_number", "")
            payslip["socso_number"] = staff.get("socso_number", "")
            payslip["tax_number"] = staff.get("tax_number", "")
            payslip["bank_name"] = staff.get("bank_name", "")
            payslip["bank_account"] = staff.get("bank_account", "")
            payslip["full_name"] = staff.get("full_name", payslip.get("full_name", ""))
            nric = staff.get("nric", "")
            if not nric and staff.get("user_id"):
                user = await db.users.find_one({"id": staff["user_id"]}, {"_id": 0, "id_number": 1})
                nric = user.get("id_number", "") if user else ""
            payslip["nric"] = nric or payslip.get("nric", "")
    
    # Update editable fields
    editable_fields = [
        "basic_salary", "fixed_allowance", "housing_allowance", "transport_allowance", "meal_allowance",
        "phone_allowance", "other_allowance", "overtime", "bonus", "commission",
        "incentives", "annual_leave_pay", "other_earnings", "epf_employee", "epf_employer", "socso_employee",
        "socso_employer", "eis_employee", "eis_employer", "pcb", "cp38",
        "loan_deduction", "mid_month_advance", "salary_adjustment", "unpaid_leave", "other_deductions"
    ]
    for field in editable_fields:
        if field in data and data[field] is not None:
            payslip[field] = float(data[field])
    
    # Recalculate derived values
    basic = float(payslip.get("basic_salary", 0))
    total_allowances = sum(float(payslip.get(f, 0)) for f in [
        "fixed_allowance", "housing_allowance", "transport_allowance", "meal_allowance",
        "phone_allowance", "other_allowance"
    ])
    overtime_val = float(payslip.get("overtime", 0))
    bonus_val = float(payslip.get("bonus", 0))
    commission_val = float(payslip.get("commission", 0))
    incentives_val = float(payslip.get("incentives", 0))
    annual_leave_val = float(payslip.get("annual_leave_pay", 0))
    other_earnings_val = float(payslip.get("other_earnings", 0))
    
    gross_salary = round(basic + total_allowances + overtime_val + bonus_val + commission_val + incentives_val + annual_leave_val + other_earnings_val, 2)
    
    total_deductions = round(sum(float(payslip.get(f, 0)) for f in [
        "epf_employee", "socso_employee", "eis_employee", "pcb", "cp38",
        "loan_deduction", "mid_month_advance", "salary_adjustment", "unpaid_leave", "other_deductions"
    ]), 2)
    
    nett_pay = round(gross_salary - total_deductions, 2)
    
    payslip["total_allowances"] = round(total_allowances, 2)
    payslip["gross_salary"] = gross_salary
    payslip["total_deductions"] = total_deductions
    payslip["nett_pay"] = nett_pay
    
    # Recalculate YTD
    year = payslip.get("year")
    month = payslip.get("month")
    ytd_data = await db.payslips.aggregate([
        {"$match": {"staff_id": payslip["staff_id"], "year": year, "month": {"$lt": month}, "id": {"$ne": payslip_id}}},
        {"$group": {
            "_id": None,
            "ytd_gross": {"$sum": "$gross_salary"},
            "ytd_epf_employee": {"$sum": "$epf_employee"},
            "ytd_epf_employer": {"$sum": "$epf_employer"},
            "ytd_pcb": {"$sum": "$pcb"},
            "ytd_nett": {"$sum": "$nett_pay"}
        }}
    ]).to_list(1)
    ytd = ytd_data[0] if ytd_data else {}
    payslip["ytd_gross"] = round(ytd.get("ytd_gross", 0) + gross_salary, 2)
    payslip["ytd_epf_employee"] = round(ytd.get("ytd_epf_employee", 0) + float(payslip.get("epf_employee", 0)), 2)
    payslip["ytd_epf_employer"] = round(ytd.get("ytd_epf_employer", 0) + float(payslip.get("epf_employer", 0)), 2)
    payslip["ytd_pcb"] = round(ytd.get("ytd_pcb", 0) + float(payslip.get("pcb", 0)), 2)
    payslip["ytd_nett"] = round(ytd.get("ytd_nett", 0) + nett_pay, 2)
    
    payslip["updated_at"] = datetime.now(timezone.utc).isoformat()
    payslip["updated_by"] = current_user.email
    
    # Update in DB
    await db.payslips.update_one({"id": payslip_id}, {"$set": payslip})
    
    # Void old journal entry and create new one
    try:
        from routes.accounting import post_payroll
        old_journal = await db.journal_entries.find_one({
            "source_module": "payroll",
            "source_id": payslip_id,
            "status": {"$ne": "voided"}
        })
        if old_journal:
            now = datetime.now(timezone.utc).isoformat()
            await db.journal_entries.update_one(
                {"id": old_journal["id"]},
                {"$set": {
                    "status": "voided",
                    "voided_by": current_user.id,
                    "voided_by_name": current_user.full_name,
                    "voided_at": now,
                    "void_reason": f"Payslip edited by {current_user.full_name}"
                }}
            )
        await post_payroll(payslip, user_id=current_user.id, user_name=current_user.full_name)
    except Exception as e:
        import logging
        logging.warning(f"Failed to update payroll journal entry: {e}")
    
    return {"message": "Payslip updated successfully", "nett_pay": nett_pay}



# =====================================================
# PAY ADVICE
# =====================================================

@router.get("/pay-advice")
async def get_pay_advice_list(period_id: Optional[str] = None, year: Optional[int] = None, month: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get all pay advice records"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if period_id: query["period_id"] = period_id
    if year: query["year"] = year
    if month: query["month"] = month
    
    advice_list = await db.pay_advice.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return advice_list


@router.post("/pay-advice/generate")
async def generate_pay_advice(data: dict, current_user: User = Depends(get_current_user)):
    """Generate pay advice for a session worker.
    year/month = PAYMENT month (what the user selected in UI).
    Training month = payment month - 1."""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_id = data.get("user_id")
    year = data.get("year")    # payment year
    month = data.get("month")  # payment month
    
    if not user_id or not year or not month:
        raise HTTPException(status_code=400, detail="user_id, year, and month are required")
    
    # Payment month is what the user selected; training month is one month before
    payment_year = year
    payment_month = month
    training_month = month - 1
    training_year = year
    if training_month < 1:
        training_month = 12
        training_year = year - 1
    
    # Check if pay advice already exists
    existing = await db.pay_advice.find_one(
        {"user_id": user_id, "year": payment_year, "month": payment_month},
        {"_id": 0}
    )
    if not existing:
        existing = await db.pay_advice.find_one(
            {"user_id": user_id, "training_year": training_year, "training_month": training_month},
            {"_id": 0}
        )
    if existing:
        raise HTTPException(status_code=400, detail="Pay advice already exists for this period. Delete it first to regenerate.")
    
    # Get user details
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check period
    period = await db.payables_periods.find_one({"year": training_year, "month": training_month})
    
    # Build session details from fee records in the TRAINING month
    session_details = []
    total_amount = 0
    
    # Get session IDs for the training month
    all_sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "start_date": 1}).to_list(1000)
    training_session_ids = []
    for s in all_sessions:
        sd = s.get("start_date")
        if sd:
            try:
                if isinstance(sd, str):
                    sdt = datetime.fromisoformat(sd.replace('Z', '+00:00'))
                else:
                    sdt = sd
                if sdt.year == training_year and sdt.month == training_month:
                    training_session_ids.append(s["id"])
            except:
                pass
    
    # 1. Trainer fees
    trainer_fees = await db.trainer_fees.find({"trainer_id": user_id, "session_id": {"$in": training_session_ids}}, {"_id": 0}).to_list(500)
    for fee in trainer_fees:
        session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        session_details.append({
            "session_id": fee.get("session_id"),
            "session_name": session.get("name"),
            "company_name": company.get("name") if company else "Unknown",
            "session_date": session.get("start_date"),
            "role": fee.get("trainer_role", "Trainer"),
            "amount": fee.get("fee_amount", 0),
            "status": fee.get("status", "pending"),
            "remark": fee.get("remark", "")
        })
        total_amount += fee.get("fee_amount", 0)
    
    # 2. Coordinator fees
    coord_fees = await db.coordinator_fees.find({"coordinator_id": user_id, "session_id": {"$in": training_session_ids}}, {"_id": 0}).to_list(500)
    for fee in coord_fees:
        session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        session_details.append({
            "session_id": fee.get("session_id"),
            "session_name": session.get("name"),
            "company_name": company.get("name") if company else "Unknown",
            "session_date": session.get("start_date"),
            "role": "Coordinator",
            "amount": fee.get("total_fee", 0),
            "status": fee.get("status", "pending"),
            "remark": f"{fee.get('num_days', 1)} day(s) @ RM{fee.get('daily_rate', 50)}/day"
        })
        total_amount += fee.get("total_fee", 0)
    
    # 3. Marketing commissions
    mkt_comm = await db.marketing_commissions.find({"marketing_user_id": user_id, "session_id": {"$in": training_session_ids}}, {"_id": 0}).to_list(500)
    for comm in mkt_comm:
        session = await db.sessions.find_one({"id": comm.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        session_details.append({
            "session_id": comm.get("session_id"),
            "session_name": session.get("name"),
            "company_name": company.get("name") if company else "Unknown",
            "session_date": session.get("start_date"),
            "role": "Marketing",
            "amount": comm.get("calculated_amount", 0),
            "status": comm.get("status", "pending"),
            "remark": f"{comm.get('commission_type', 'Commission')} @ {comm.get('commission_percentage', 0)}%"
        })
        total_amount += comm.get("calculated_amount", 0)
    
    if not session_details:
        raise HTTPException(status_code=400, detail=f"No session work found for this user in training month {training_month}/{training_year}")
    
    # Sort by session date
    session_details.sort(key=lambda x: x.get("session_date", ""))
    
    # Create pay advice with PAYMENT month
    now = get_malaysia_time()
    pay_advice = {
        "id": str(uuid.uuid4()),
        "advice_number": f"PA/MDDRC/{payment_year}/{str(payment_month).zfill(2)}/{str(uuid.uuid4())[:4].upper()}",
        "user_id": user_id,
        "period_id": period["id"] if period else None,
        "training_year": training_year,
        "training_month": training_month,
        "year": payment_year,
        "month": payment_month,
        "period_name": f"{datetime(payment_year, payment_month, 1).strftime('%B %Y')}",
        "training_period_name": f"{datetime(training_year, training_month, 1).strftime('%B %Y')}",
        "full_name": user.get("full_name"),
        "id_number": user.get("id_number"),
        "email": user.get("email"),
        "phone": user.get("phone_number"),
        "bank_name": user.get("bank_name"),
        "bank_account": user.get("bank_account"),
        "session_details": session_details,
        "total_sessions": len(session_details),
        "gross_amount": total_amount,
        "deductions": 0,
        "nett_amount": total_amount,
        "is_locked": False,
        "created_at": now.isoformat(),
        "created_by": current_user.id,
        "created_by_name": current_user.full_name or current_user.email
    }
    
    await db.pay_advice.insert_one({**pay_advice, "_id": pay_advice["id"]})
    return {"id": pay_advice["id"], "message": "Pay advice generated successfully", "total_sessions": len(session_details), "total_amount": total_amount}


@router.get("/pay-advice/{advice_id}")
async def get_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Get a single pay advice"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    advice = await db.pay_advice.find_one({"id": advice_id}, {"_id": 0})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    return advice


@router.delete("/pay-advice/{advice_id}")
async def delete_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Delete pay advice (only if not locked)"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can delete pay advice")
    
    advice = await db.pay_advice.find_one({"id": advice_id})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    if advice.get("is_locked"):
        raise HTTPException(status_code=400, detail="Cannot delete locked pay advice. Period is closed.")
    
    await db.pay_advice.delete_one({"id": advice_id})
    return {"message": "Pay advice deleted"}


@router.post("/pay-advice/{advice_id}/lock")
async def lock_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Lock a pay advice (finalize it so staff can view)"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can lock pay advice")
    
    advice = await db.pay_advice.find_one({"id": advice_id}, {"_id": 0})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    if advice.get("is_locked"):
        raise HTTPException(status_code=400, detail="Pay advice is already locked")
    
    now = get_malaysia_time()
    await db.pay_advice.update_one(
        {"id": advice_id},
        {"$set": {
            "is_locked": True,
            "locked_at": now.isoformat(),
            "locked_by": current_user.id,
            "locked_by_name": current_user.full_name or current_user.email
        }}
    )
    return {"message": "Pay advice locked successfully"}


@router.post("/pay-advice/{advice_id}/unlock")
async def unlock_pay_advice(advice_id: str, reason: str = "", current_user: User = Depends(get_current_user)):
    """Unlock a pay advice (requires admin and reason)"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can unlock pay advice")
    
    advice = await db.pay_advice.find_one({"id": advice_id}, {"_id": 0})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    if not advice.get("is_locked"):
        raise HTTPException(status_code=400, detail="Pay advice is not locked")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason must be at least 5 characters")
    
    now = get_malaysia_time()
    await db.pay_advice.update_one(
        {"id": advice_id},
        {"$set": {
            "is_locked": False,
            "unlocked_at": now.isoformat(),
            "unlocked_by": current_user.id,
            "unlock_reason": reason
        }}
    )
    return {"message": "Pay advice unlocked successfully"}


@router.post("/pay-advice/bulk-generate")
async def bulk_generate_pay_advice(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Bulk generate pay advice for all session workers.
    year/month = PAYMENT month (what the user selected in UI).
    Training month = payment month - 1 (sessions that happened the previous month)."""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Payment month is what the user selected; training month is one month before
    payment_year = year
    payment_month = month
    
    # Calculate training month (month - 1)
    training_month = month - 1
    training_year = year
    if training_month < 1:
        training_month = 12
        training_year = year - 1
    
    # Get all sessions in the TRAINING month
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "start_date": 1}).to_list(1000)
    session_ids = []
    for s in sessions:
        sd = s.get("start_date")
        if sd:
            try:
                sdt = None
                if isinstance(sd, str):
                    # Try multiple date formats
                    for fmt in [None, "%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y"]:
                        try:
                            if fmt is None:
                                sdt = datetime.fromisoformat(sd.replace('Z', '+00:00'))
                            else:
                                sdt = datetime.strptime(sd, fmt)
                            break
                        except:
                            pass
                else:
                    sdt = sd
                if sdt and sdt.year == training_year and sdt.month == training_month:
                    session_ids.append(s["id"])
            except:
                pass
    
    if not session_ids:
        return {"message": f"No sessions found for training month {training_month}/{training_year}", "generated": 0, "skipped": 0}
    
    # Find unique users who worked in these sessions
    user_ids = set()
    
    trainer_fees = await db.trainer_fees.find({"session_id": {"$in": session_ids}}, {"_id": 0, "trainer_id": 1}).to_list(1000)
    for tf in trainer_fees:
        if tf.get("trainer_id"):
            user_ids.add(tf["trainer_id"])
    
    coord_fees = await db.coordinator_fees.find({"session_id": {"$in": session_ids}}, {"_id": 0, "coordinator_id": 1}).to_list(1000)
    for cf in coord_fees:
        if cf.get("coordinator_id"):
            user_ids.add(cf["coordinator_id"])
    
    mkt_comm = await db.marketing_commissions.find({"session_id": {"$in": session_ids}}, {"_id": 0, "marketing_user_id": 1}).to_list(1000)
    for mc in mkt_comm:
        if mc.get("marketing_user_id"):
            user_ids.add(mc["marketing_user_id"])
    
    generated = 0
    skipped = 0
    errors = []
    
    for user_id in user_ids:
        try:
            # Check if already exists (by payment month OR training month)
            existing = await db.pay_advice.find_one({"user_id": user_id, "year": payment_year, "month": payment_month})
            if not existing:
                existing = await db.pay_advice.find_one({"user_id": user_id, "training_year": training_year, "training_month": training_month})
            if existing:
                skipped += 1
                continue
            
            user = await db.users.find_one({"id": user_id}, {"_id": 0})
            if not user:
                continue
            
            session_details = []
            total_amount = 0
            
            # Trainer fees
            for fee in await db.trainer_fees.find({"trainer_id": user_id, "session_id": {"$in": session_ids}}, {"_id": 0}).to_list(100):
                session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1}) if session else None
                session_details.append({
                    "session_id": fee.get("session_id"),
                    "session_name": session.get("name") if session else "Unknown",
                    "company_name": company.get("name") if company else "Unknown",
                    "session_date": session.get("start_date") if session else None,
                    "role": fee.get("trainer_role", "Trainer"),
                    "amount": fee.get("fee_amount", 0),
                    "status": fee.get("status", "pending")
                })
                total_amount += fee.get("fee_amount", 0)
            
            # Coordinator fees
            for fee in await db.coordinator_fees.find({"coordinator_id": user_id, "session_id": {"$in": session_ids}}, {"_id": 0}).to_list(100):
                session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1}) if session else None
                session_details.append({
                    "session_id": fee.get("session_id"),
                    "session_name": session.get("name") if session else "Unknown",
                    "company_name": company.get("name") if company else "Unknown",
                    "session_date": session.get("start_date") if session else None,
                    "role": "Coordinator",
                    "amount": fee.get("total_fee", 0),
                    "status": fee.get("status", "pending")
                })
                total_amount += fee.get("total_fee", 0)
            
            # Marketing commissions
            for comm in await db.marketing_commissions.find({"marketing_user_id": user_id, "session_id": {"$in": session_ids}}, {"_id": 0}).to_list(100):
                session = await db.sessions.find_one({"id": comm.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1}) if session else None
                session_details.append({
                    "session_id": comm.get("session_id"),
                    "session_name": session.get("name") if session else "Unknown",
                    "company_name": company.get("name") if company else "Unknown",
                    "session_date": session.get("start_date") if session else None,
                    "role": "Marketing",
                    "amount": comm.get("calculated_amount", 0),
                    "status": comm.get("status", "pending")
                })
                total_amount += comm.get("calculated_amount", 0)
            
            if not session_details:
                continue
            
            now = get_malaysia_time()
            period = await db.payables_periods.find_one({"year": training_year, "month": training_month})
            pay_advice = {
                "id": str(uuid.uuid4()),
                "advice_number": f"PA/MDDRC/{payment_year}/{str(payment_month).zfill(2)}/{str(uuid.uuid4())[:4].upper()}",
                "user_id": user_id,
                "period_id": period["id"] if period else None,
                "training_year": training_year,
                "training_month": training_month,
                "year": payment_year,
                "month": payment_month,
                "period_name": f"{datetime(payment_year, payment_month, 1).strftime('%B %Y')}",
                "training_period_name": f"{datetime(training_year, training_month, 1).strftime('%B %Y')}",
                "full_name": user.get("full_name"),
                "id_number": user.get("id_number"),
                "email": user.get("email"),
                "phone": user.get("phone_number"),
                "bank_name": user.get("bank_name"),
                "bank_account": user.get("bank_account"),
                "session_details": session_details,
                "total_sessions": len(session_details),
                "gross_amount": total_amount,
                "deductions": 0,
                "nett_amount": total_amount,
                "is_locked": False,
                "created_at": now.isoformat(),
                "created_by": current_user.id
            }
            
            await db.pay_advice.insert_one({**pay_advice, "_id": pay_advice["id"]})
            generated += 1
        except Exception as e:
            errors.append(f"{user_id}: {str(e)}")
    
    return {
        "message": f"Bulk generation complete (training: {training_month}/{training_year}, payment: {payment_month}/{payment_year})",
        "generated": generated,
        "skipped": skipped,
        "total_workers": len(user_ids),
        "errors": errors[:5] if errors else []
    }


@router.post("/pay-advice/bulk-lock")
async def bulk_lock_pay_advice(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Bulk lock all pay advice for a period"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    result = await db.pay_advice.update_many(
        {"year": year, "month": month, "is_locked": False},
        {"$set": {
            "is_locked": True,
            "locked_at": now.isoformat(),
            "locked_by": current_user.id
        }}
    )
    return {"message": f"Locked {result.modified_count} pay advice records"}


# =====================================================
# MY PAYSLIPS / PAY ADVICE (Self-service)
# =====================================================

@router.get("/my-payslips")
async def get_my_payslips(current_user: User = Depends(get_current_user)):
    """Get current user's payslips"""
    staff = await db.hr_staff.find_one({"user_id": current_user.id}, {"_id": 0})
    if not staff:
        return []
    
    payslips = await db.payslips.find({"staff_id": staff["id"]}, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return payslips


@router.get("/my-pay-advice")
async def get_my_pay_advice(current_user: User = Depends(get_current_user)):
    """Get current user's pay advice"""
    advice_list = await db.pay_advice.find({"user_id": current_user.id}, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return advice_list


# =====================================================
# EA FORM
# =====================================================

@router.get("/ea-form/{staff_id}/{year}")
async def get_ea_form(staff_id: str, year: int, current_user: User = Depends(get_current_user)):
    """Get EA Form data for a staff member"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    staff = await db.hr_staff.find_one({"id": staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    payslips = await db.payslips.find({"staff_id": staff_id, "year": year}, {"_id": 0}).to_list(12)
    
    totals = {
        "gross_salary": sum(p.get("gross_salary", 0) for p in payslips),
        "epf_employee": sum(p.get("epf_employee", 0) for p in payslips),
        "pcb": sum(p.get("pcb", 0) for p in payslips)
    }
    
    return {"staff": staff, "year": year, "payslips": payslips, "totals": totals}


@router.get("/my-ea-form/{year}")
async def get_my_ea_form(year: int, current_user: User = Depends(get_current_user)):
    """Get current user's EA Form"""
    staff = await db.hr_staff.find_one({"user_id": current_user.id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff record not found")
    
    payslips = await db.payslips.find({"staff_id": staff["id"], "year": year}, {"_id": 0}).to_list(12)
    
    totals = {
        "gross_salary": sum(p.get("gross_salary", 0) for p in payslips),
        "epf_employee": sum(p.get("epf_employee", 0) for p in payslips),
        "pcb": sum(p.get("pcb", 0) for p in payslips)
    }
    
    return {"staff": staff, "year": year, "payslips": payslips, "totals": totals}
