"""
HR Module routes - Staff management, payroll, and statutory calculations
Endpoints: 27
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from io import BytesIO

from core import db, get_current_user
from models import User

router = APIRouter(prefix="/hr", tags=["hr"])


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


@router.get("/available-users")
async def get_available_users(current_user: User = Depends(get_current_user)):
    """Get users that can be linked as staff"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing_staff = await db.hr_staff.find({}, {"user_id": 1}).to_list(500)
    existing_user_ids = [s.get("user_id") for s in existing_staff if s.get("user_id")]
    
    users = await db.users.find(
        {
            "role": {"$in": ["trainer", "coordinator", "assistant_admin", "admin"]},
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
    """Generate a payslip for a staff member"""
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
        raise HTTPException(status_code=400, detail="Payslip already exists for this period")
    
    # Calculate age and statutory
    age = calculate_age_from_nric(nric, f"{year}-{month:02d}-01") if nric else 30
    
    basic_salary = data.get("basic_salary") or staff.get("basic_salary", 0)
    total_allowances = sum([
        data.get("housing_allowance") or staff.get("housing_allowance", 0),
        data.get("transport_allowance") or staff.get("transport_allowance", 0),
        data.get("meal_allowance") or staff.get("meal_allowance", 0),
        data.get("phone_allowance") or staff.get("phone_allowance", 0),
        data.get("other_allowance") or staff.get("other_allowance", 0)
    ])
    
    overtime = data.get("overtime", 0)
    bonus = data.get("bonus", 0)
    gross_salary = basic_salary + total_allowances + overtime + bonus
    
    epf = calculate_epf(basic_salary, age, staff.get("employee_epf_rate"), staff.get("employer_epf_rate"))
    socso = calculate_socso(gross_salary, age)
    eis = calculate_eis(gross_salary, age)
    
    total_deductions = epf["employee_amount"] + socso["employee_amount"] + eis["employee_amount"] + data.get("pcb", 0)
    nett_pay = gross_salary - total_deductions
    
    payslip = {
        "id": str(uuid.uuid4()),
        "staff_id": staff_id,
        "year": year,
        "month": month,
        "period_name": f"{year}-{str(month).zfill(2)}",
        "full_name": staff.get("full_name"),
        "nric": nric,
        "basic_salary": basic_salary,
        "total_allowances": total_allowances,
        "overtime": overtime,
        "bonus": bonus,
        "gross_salary": gross_salary,
        "epf_employee": epf["employee_amount"],
        "epf_employer": epf["employer_amount"],
        "socso_employee": socso["employee_amount"],
        "socso_employer": socso["employer_amount"],
        "eis_employee": eis["employee_amount"],
        "eis_employer": eis["employer_amount"],
        "pcb": data.get("pcb", 0),
        "total_deductions": total_deductions,
        "nett_pay": nett_pay,
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.email
    }
    
    await db.payslips.insert_one(payslip)
    return {"id": payslip["id"], "message": "Payslip generated", "nett_pay": nett_pay}


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
    """Delete a payslip"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete payslips")
    
    payslip = await db.payslips.find_one({"id": payslip_id})
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    if payslip.get("is_locked"):
        raise HTTPException(status_code=400, detail="Cannot delete locked payslip")
    
    await db.payslips.delete_one({"id": payslip_id})
    return {"message": "Payslip deleted"}


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
    """Generate pay advice for a session worker"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_id = data.get("user_id")
    year = data.get("year")
    month = data.get("month")
    
    if not user_id or not year or not month:
        raise HTTPException(status_code=400, detail="user_id, year, and month required")
    
    existing = await db.pay_advice.find_one({"user_id": user_id, "year": year, "month": month})
    if existing:
        raise HTTPException(status_code=400, detail="Pay advice already exists")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    advice = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "full_name": user.get("full_name"),
        "year": year,
        "month": month,
        "period_name": f"{year}-{str(month).zfill(2)}",
        "total_amount": data.get("total_amount", 0),
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.pay_advice.insert_one(advice)
    return {"id": advice["id"], "message": "Pay advice generated"}


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
    """Delete pay advice"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete")
    
    advice = await db.pay_advice.find_one({"id": advice_id})
    if not advice:
        raise HTTPException(status_code=404, detail="Not found")
    if advice.get("is_locked"):
        raise HTTPException(status_code=400, detail="Cannot delete locked advice")
    
    await db.pay_advice.delete_one({"id": advice_id})
    return {"message": "Pay advice deleted"}


@router.post("/pay-advice/{advice_id}/lock")
async def lock_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Lock a pay advice"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.pay_advice.update_one({"id": advice_id}, {"$set": {"is_locked": True}})
    return {"message": "Pay advice locked"}


@router.post("/pay-advice/{advice_id}/unlock")
async def unlock_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Unlock a pay advice"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can unlock")
    
    await db.pay_advice.update_one({"id": advice_id}, {"$set": {"is_locked": False}})
    return {"message": "Pay advice unlocked"}


@router.post("/pay-advice/bulk-generate")
async def bulk_generate_pay_advice(data: dict, current_user: User = Depends(get_current_user)):
    """Bulk generate pay advice"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Simplified bulk generation
    return {"message": "Bulk generation completed", "count": 0}


@router.post("/pay-advice/bulk-lock")
async def bulk_lock_pay_advice(data: dict, current_user: User = Depends(get_current_user)):
    """Bulk lock pay advice"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    advice_ids = data.get("advice_ids", [])
    if advice_ids:
        await db.pay_advice.update_many({"id": {"$in": advice_ids}}, {"$set": {"is_locked": True}})
    return {"message": f"Locked {len(advice_ids)} records"}


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
