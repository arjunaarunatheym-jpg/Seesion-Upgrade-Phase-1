"""
Companies routes - Company management
Endpoints: 4
- POST /companies
- GET /companies
- PUT /companies/{company_id}
- DELETE /companies/{company_id}
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime

from core import db, get_current_user
from models import User, Company, CompanyCreate, CompanyUpdate

router = APIRouter(tags=["companies"])


@router.post("/companies", response_model=Company)
async def create_company(company_data: CompanyCreate, current_user: User = Depends(get_current_user)):
    """Create a new company (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create companies")
    
    company_obj = Company(
        name=company_data.name,
        registration_no=company_data.registration_no,
        address_line1=company_data.address_line1,
        address_line2=company_data.address_line2,
        city=company_data.city,
        postcode=company_data.postcode,
        state=company_data.state,
        phone=company_data.phone,
        email=company_data.email,
        contact_person=company_data.contact_person
    )
    doc = company_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.companies.insert_one(doc)
    return company_obj


@router.get("/companies", response_model=List[Company])
async def get_companies(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all companies with optional search"""
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    companies = await db.companies.find(query, {"_id": 0}).to_list(1000)
    for company in companies:
        if isinstance(company.get('created_at'), str):
            company['created_at'] = datetime.fromisoformat(company['created_at'])
    return companies


@router.put("/companies/{company_id}", response_model=Company)
async def update_company(company_id: str, company_data: CompanyUpdate, current_user: User = Depends(get_current_user)):
    """Update a company (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can update companies")
    
    update_dict = {k: v for k, v in company_data.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.companies.update_one(
        {"id": company_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company_doc = await db.companies.find_one({"id": company_id}, {"_id": 0})
    return company_doc


@router.delete("/companies/{company_id}")
async def delete_company(company_id: str, current_user: User = Depends(get_current_user)):
    """Delete a company (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete companies")
    
    result = await db.companies.delete_one({"id": company_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"message": "Company deleted successfully"}
