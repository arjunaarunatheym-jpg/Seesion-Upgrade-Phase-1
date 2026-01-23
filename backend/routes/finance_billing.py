"""
Finance Billing Parties routes
Stage F1: 4 endpoints
"""
from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user
from models import User, BillingParty

router = APIRouter(prefix="/finance", tags=["finance-billing"])


@router.post("/billing-parties")
async def create_billing_party(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new billing party / vendor"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    billing_party = BillingParty(
        name=data.get("name"),
        registration_no=data.get("registration_no"),
        address_line1=data.get("address_line1"),
        address_line2=data.get("address_line2"),
        city=data.get("city"),
        postcode=data.get("postcode"),
        state=data.get("state"),
        phone=data.get("phone"),
        email=data.get("email"),
        contact_person=data.get("contact_person")
    )
    doc = billing_party.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.billing_parties.insert_one(doc)
    doc.pop('_id', None)
    return {"message": "Billing party created", "billing_party": doc}


@router.get("/billing-parties")
async def get_billing_parties(current_user: User = Depends(get_current_user)):
    """Get all billing parties"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    parties = await db.billing_parties.find({"is_active": True}, {"_id": 0}).to_list(100)
    return parties


@router.put("/billing-parties/{party_id}")
async def update_billing_party(party_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a billing party"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_dict = {k: v for k, v in data.items() if v is not None and k != "id"}
    
    result = await db.billing_parties.update_one(
        {"id": party_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Billing party not found")
    
    return {"message": "Updated successfully"}


@router.delete("/billing-parties/{party_id}")
async def delete_billing_party(party_id: str, current_user: User = Depends(get_current_user)):
    """Soft delete a billing party"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.billing_parties.update_one(
        {"id": party_id},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "Deleted successfully"}
