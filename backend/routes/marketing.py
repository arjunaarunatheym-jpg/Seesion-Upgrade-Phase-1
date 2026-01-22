"""
Marketing Module routes - Client management, quotations, and PDF generation
Endpoints: 26
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime
from io import BytesIO, StringIO
import uuid
import csv

from core import db, get_current_user, get_malaysia_time
from models import User

from pydantic import BaseModel, Field, ConfigDict

# Marketing Models
class MarketingClient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class MarketingClientCreate(BaseModel):
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None

class DescriptionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    unit: Optional[str] = "pax"
    default_rate: float = 0
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class Quotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quotation_number: Optional[str] = None
    client_id: str
    programme_id: Optional[str] = None
    programme_name: Optional[str] = None
    items: List[dict] = []
    subtotal: float = 0
    discount_percentage: float = 0
    discount_amount: float = 0
    sst_percentage: float = 0
    sst_amount: float = 0
    total_amount: float = 0
    validity_days: int = 30
    terms_conditions: Optional[str] = None
    notes: Optional[str] = None
    status: str = "draft"  # draft, pending_approval, approved, sent, accepted, declined, expired
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    submitted_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    sent_at: Optional[str] = None
    client_response_at: Optional[str] = None
    client_response_notes: Optional[str] = None


router = APIRouter(prefix="/marketing", tags=["marketing"])


def check_marketing_access(user: User) -> bool:
    """Check if user has marketing access"""
    if user.role in ["admin", "super_admin"]:
        return True
    if user.role == "marketing":
        return True
    if "marketing" in (user.additional_roles or []):
        return True
    return False


# =====================================================
# CLIENTS
# =====================================================

@router.get("/clients")
async def get_marketing_clients(current_user: User = Depends(get_current_user)):
    """Get clients - marketers see only their own, admin sees all"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    clients = await db.marketing_clients.find(query, {"_id": 0}).to_list(1000)
    
    if current_user.role in ["admin", "super_admin"]:
        user_ids = list(set(c.get("created_by") for c in clients if c.get("created_by")))
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "full_name": 1}).to_list(100)
        user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
        for c in clients:
            c["marketer_name"] = user_map.get(c.get("created_by"), "Unknown")
    
    return clients


@router.get("/clients/all")
async def get_all_clients_admin(current_user: User = Depends(get_current_user)):
    """Admin only - Get all clients with marketer info"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    clients = await db.marketing_clients.find({}, {"_id": 0}).to_list(1000)
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u["full_name"] for u in users}
    
    for client in clients:
        client["marketer_name"] = user_map.get(client.get("created_by", ""), "Unknown")
    
    return clients


@router.post("/clients")
async def create_marketing_client(client_data: MarketingClientCreate, current_user: User = Depends(get_current_user)):
    """Create a new client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({
        "company_name": {"$regex": f"^{client_data.company_name}$", "$options": "i"},
        "created_by": current_user.id
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a client with this company name")
    
    client = MarketingClient(**client_data.model_dump(), created_by=current_user.id)
    doc = client.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    
    await db.marketing_clients.insert_one(doc)
    return {"message": "Client created successfully", "client": doc}


@router.put("/clients/{client_id}")
async def update_marketing_client(client_id: str, client_data: dict, current_user: User = Depends(get_current_user)):
    """Update a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own clients")
    
    update_fields = {k: v for k, v in client_data.items() if k not in ["id", "created_by", "created_at"]}
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    
    await db.marketing_clients.update_one({"id": client_id}, {"$set": update_fields})
    return {"message": "Client updated successfully"}


@router.delete("/clients/{client_id}")
async def delete_marketing_client(client_id: str, current_user: User = Depends(get_current_user)):
    """Delete a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own clients")
    
    quotation_count = await db.quotations.count_documents({"client_id": client_id})
    if quotation_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete client with {quotation_count} quotation(s)")
    
    await db.marketing_clients.delete_one({"id": client_id})
    return {"message": "Client deleted successfully"}


@router.get("/clients/export")
async def export_all_clients(current_user: User = Depends(get_current_user)):
    """Admin only - Export all clients as CSV"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    clients = await db.marketing_clients.find({}, {"_id": 0}).to_list(1000)
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u["full_name"] for u in users}
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Company Name", "Contact Person", "Email", "Phone", "Address", "Marketer", "Created Date"])
    
    for client in clients:
        marketer_name = user_map.get(client.get("created_by", ""), "Unknown")
        created_at = client.get("created_at", "")
        if isinstance(created_at, datetime):
            created_at = created_at.strftime("%Y-%m-%d")
        
        writer.writerow([
            client.get("company_name", ""),
            client.get("contact_person", ""),
            client.get("contact_email", ""),
            client.get("contact_phone", ""),
            client.get("company_address", "").replace("\n", ", "),
            marketer_name,
            created_at
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="marketing_clients_{datetime.now().strftime("%Y%m%d")}.csv"'}
    )


# =====================================================
# QUOTATIONS
# =====================================================

@router.get("/quotations")
async def get_quotations(status: str = None, current_user: User = Depends(get_current_user)):
    """Get quotations"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    if status:
        query["status"] = status
    
    quotations = await db.quotations.find(query, {"_id": 0}).to_list(1000)
    
    client_ids = list(set(q.get("client_id") for q in quotations if q.get("client_id")))
    clients = await db.marketing_clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(100)
    client_map = {c["id"]: c for c in clients}
    
    user_ids = list(set(q.get("created_by") for q in quotations if q.get("created_by")))
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "full_name": 1}).to_list(100)
    user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
    
    for q in quotations:
        client = client_map.get(q.get("client_id"), {})
        q["client_name"] = client.get("company_name", "Unknown")
        q["contact_person"] = client.get("contact_person", "")
        q["marketer_name"] = user_map.get(q.get("created_by"), "Unknown")
    
    quotations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return quotations


@router.get("/quotations/{quotation_id}")
async def get_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Get a single quotation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Enrich with client info
    client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
    if client:
        quotation["client"] = client
    
    return quotation


@router.post("/quotations")
async def create_quotation(quotation_data: dict, current_user: User = Depends(get_current_user)):
    """Create a new quotation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Generate quotation number
    year = datetime.now().year
    count = await db.quotations.count_documents({"quotation_number": {"$regex": f"^Q{year}"}})
    quotation_number = f"Q{year}{str(count + 1).zfill(4)}"
    
    quotation = {
        "id": str(uuid.uuid4()),
        "quotation_number": quotation_number,
        "client_id": quotation_data.get("client_id"),
        "programme_id": quotation_data.get("programme_id"),
        "programme_name": quotation_data.get("programme_name"),
        "items": quotation_data.get("items", []),
        "subtotal": quotation_data.get("subtotal", 0),
        "discount_percentage": quotation_data.get("discount_percentage", 0),
        "discount_amount": quotation_data.get("discount_amount", 0),
        "sst_percentage": quotation_data.get("sst_percentage", 0),
        "sst_amount": quotation_data.get("sst_amount", 0),
        "total_amount": quotation_data.get("total_amount", 0),
        "validity_days": quotation_data.get("validity_days", 30),
        "terms_conditions": quotation_data.get("terms_conditions"),
        "notes": quotation_data.get("notes"),
        "status": "draft",
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.quotations.insert_one(quotation)
    return {"message": "Quotation created", "quotation": quotation}


@router.put("/quotations/{quotation_id}")
async def update_quotation(quotation_id: str, quotation_data: dict, current_user: User = Depends(get_current_user)):
    """Update a quotation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if existing.get("status") not in ["draft", "pending_approval"]:
        raise HTTPException(status_code=400, detail="Cannot edit quotation in this status")
    
    update_fields = {k: v for k, v in quotation_data.items() if k not in ["id", "created_by", "created_at", "quotation_number"]}
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_fields})
    return {"message": "Quotation updated"}


@router.post("/quotations/{quotation_id}/submit")
async def submit_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Submit quotation for approval"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft quotations can be submitted")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "pending_approval", "submitted_at": get_malaysia_time().isoformat()}}
    )
    return {"message": "Quotation submitted for approval"}


@router.post("/quotations/{quotation_id}/approve")
async def approve_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Approve a quotation (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admin can approve")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Quotation is not pending approval")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "approved", "approved_at": get_malaysia_time().isoformat(), "approved_by": current_user.id}}
    )
    return {"message": "Quotation approved"}


@router.post("/quotations/{quotation_id}/reject")
async def reject_quotation(quotation_id: str, reason: dict = None, current_user: User = Depends(get_current_user)):
    """Reject a quotation (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admin can reject")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "draft", "rejection_reason": reason.get("reason") if reason else None}}
    )
    return {"message": "Quotation rejected, returned to draft"}


@router.post("/quotations/{quotation_id}/mark-sent")
async def mark_quotation_sent(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Mark quotation as sent to client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved quotations can be marked as sent")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "sent", "sent_at": get_malaysia_time().isoformat()}}
    )
    return {"message": "Quotation marked as sent"}


@router.post("/quotations/{quotation_id}/client-response")
async def record_client_response(quotation_id: str, response_data: dict, current_user: User = Depends(get_current_user)):
    """Record client response (accepted/declined)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    response = response_data.get("response")  # accepted or declined
    if response not in ["accepted", "declined"]:
        raise HTTPException(status_code=400, detail="Response must be 'accepted' or 'declined'")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {
            "status": response,
            "client_response_at": get_malaysia_time().isoformat(),
            "client_response_notes": response_data.get("notes")
        }}
    )
    return {"message": f"Quotation marked as {response}"}


@router.get("/quotations/{quotation_id}/download-pdf")
async def download_quotation_pdf(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Download quotation as PDF"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Simple PDF generation (placeholder - would use proper PDF library)
    pdf_content = f"Quotation {quotation.get('quotation_number')}\n\nTotal: RM {quotation.get('total_amount', 0):.2f}".encode()
    
    return StreamingResponse(
        BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="quotation_{quotation.get("quotation_number", quotation_id)}.pdf"'}
    )


# =====================================================
# DESCRIPTION ITEMS
# =====================================================

@router.get("/description-items")
async def get_description_items(current_user: User = Depends(get_current_user)):
    """Get description items for current user"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    items = await db.description_items.find(query, {"_id": 0}).to_list(500)
    return items


@router.get("/description-items/all")
async def get_all_description_items(current_user: User = Depends(get_current_user)):
    """Get all description items (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    items = await db.description_items.find({}, {"_id": 0}).to_list(500)
    return items


@router.post("/description-items")
async def create_description_item(item_data: dict, current_user: User = Depends(get_current_user)):
    """Create a description item"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    item = {
        "id": str(uuid.uuid4()),
        "name": item_data.get("name"),
        "description": item_data.get("description"),
        "unit": item_data.get("unit", "pax"),
        "default_rate": item_data.get("default_rate", 0),
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.description_items.insert_one(item)
    return {"message": "Item created", "item": item}


@router.put("/description-items/{item_id}")
async def update_description_item(item_id: str, item_data: dict, current_user: User = Depends(get_current_user)):
    """Update a description item"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.description_items.find_one({"id": item_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_fields = {k: v for k, v in item_data.items() if k not in ["id", "created_by", "created_at"]}
    await db.description_items.update_one({"id": item_id}, {"$set": update_fields})
    return {"message": "Item updated"}


@router.delete("/description-items/{item_id}")
async def delete_description_item(item_id: str, current_user: User = Depends(get_current_user)):
    """Delete a description item"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    await db.description_items.delete_one({"id": item_id})
    return {"message": "Item deleted"}


# =====================================================
# STATS & HELPERS
# =====================================================

@router.get("/stats")
async def get_marketing_stats(current_user: User = Depends(get_current_user)):
    """Get marketing stats"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    client_query = {}
    if current_user.role not in ["admin", "super_admin"]:
        client_query["created_by"] = current_user.id
    
    client_count = await db.marketing_clients.count_documents(client_query)
    total_quotations = await db.quotations.count_documents(query)
    pending = await db.quotations.count_documents({**query, "status": "pending_approval"})
    approved = await db.quotations.count_documents({**query, "status": "approved"})
    sent = await db.quotations.count_documents({**query, "status": "sent"})
    accepted = await db.quotations.count_documents({**query, "status": "accepted"})
    declined = await db.quotations.count_documents({**query, "status": "declined"})
    
    accepted_quotations = await db.quotations.find({**query, "status": "accepted"}, {"_id": 0, "total_amount": 1}).to_list(1000)
    total_accepted_value = sum(q.get("total_amount", 0) for q in accepted_quotations)
    
    return {
        "clients": client_count,
        "total_quotations": total_quotations,
        "pending_approval": pending,
        "approved": approved,
        "sent": sent,
        "accepted": accepted,
        "declined": declined,
        "total_accepted_value": total_accepted_value
    }


@router.get("/programmes")
async def get_programmes_for_quotation(current_user: User = Depends(get_current_user)):
    """Get programmes list for quotation creation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1, "category": 1, "description": 1}).to_list(100)
    return programmes


@router.get("/default-terms")
async def get_default_terms(current_user: User = Depends(get_current_user)):
    """Get default terms and conditions"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    settings = await db.company_settings.find_one({}, {"_id": 0})
    default_terms = """1. This quotation is valid for 30 days from the date of issue.
2. A 50% deposit is required upon confirmation.
3. Full payment must be made before the training date.
4. Cancellation within 7 days of training will incur a 50% cancellation fee.
5. Prices are subject to SST where applicable."""
    
    return {"terms": settings.get("quotation_terms", default_terms) if settings else default_terms}


@router.get("/pdf-templates")
async def get_pdf_templates(current_user: User = Depends(get_current_user)):
    """Get PDF templates configuration"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    templates = await db.pdf_templates.find_one({"id": "quotation_template"}, {"_id": 0})
    return templates or {"id": "quotation_template", "header": "", "footer": ""}


@router.put("/pdf-templates")
async def update_pdf_templates(template_data: dict, current_user: User = Depends(get_current_user)):
    """Update PDF templates (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await db.pdf_templates.update_one(
        {"id": "quotation_template"},
        {"$set": template_data},
        upsert=True
    )
    return {"message": "Templates updated"}
