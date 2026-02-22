"""
Marketing Module routes - Client management, quotations, and PDF generation
Endpoints: 26
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import uuid
import csv

from core import db, get_current_user, get_malaysia_time
from models import User
from utils.email_notifications import (
    notify_new_lead,
    notify_lead_stage_change,
    notify_quotation_for_approval,
    notify_discount_request,
    notify_quotation_sent,
    notify_lead_won,
    notify_lead_lost,
    notify_quotation_accepted,
    notify_quotation_declined,
    notify_quotation_rejected
)

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
        # Normalize created_at to string for sorting
        if isinstance(q.get("created_at"), datetime):
            q["created_at"] = q["created_at"].isoformat()
    
    quotations.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
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
    
    # Generate quotation number: QUO/MDDRC/YYYY/MM/XXXXX
    now = get_malaysia_time()
    year = now.year
    month = now.month
    
    # Count quotations in current month (shared sequence across all marketing users)
    month_prefix = f"QUO/MDDRC/{year}/{str(month).zfill(2)}/"
    # Escape slashes for regex
    escaped_prefix = month_prefix.replace('/', r'\/')
    regex_pattern = f"^{escaped_prefix}" + r"\d{5}$"
    count = await db.quotations.count_documents({
        "quotation_number": {"$regex": regex_pattern}
    })
    quotation_number = f"{month_prefix}{str(count + 1).zfill(5)}"
    
    # Calculate valid_until date
    validity_days = quotation_data.get("validity_days", 30)
    valid_until = (now + timedelta(days=validity_days)).strftime("%Y-%m-%d")
    
    quotation = {
        "id": str(uuid.uuid4()),
        "quotation_number": quotation_number,
        "revision_number": 0,  # Track revision count
        "client_id": quotation_data.get("client_id"),
        "programme_id": quotation_data.get("programme_id"),
        "programme_name": quotation_data.get("programme_name"),
        "pricing_type": quotation_data.get("pricing_type", "per_pax"),
        "num_participants": quotation_data.get("num_participants", 1),
        "rate_per_pax": quotation_data.get("rate_per_pax", 0),
        "group_price": quotation_data.get("group_price", 0),
        "items": quotation_data.get("items", []),
        "subtotal": quotation_data.get("subtotal", 0),
        "discount_percentage": quotation_data.get("discount_percentage", 0),
        "discount_amount": quotation_data.get("discount_amount", 0),
        "sst_percentage": quotation_data.get("sst_percentage", 0),
        "sst_amount": quotation_data.get("sst_amount", 0),
        "total_amount": quotation_data.get("total_amount", 0),
        "validity_days": validity_days,
        "valid_until": valid_until,
        "selected_items": quotation_data.get("selected_items", []),  # Inclusions/exclusions
        "description_items": quotation_data.get("description_items", []),  # Legacy
        "custom_description": quotation_data.get("custom_description"),
        "terms_conditions": quotation_data.get("terms_conditions"),
        "notes": quotation_data.get("notes"),
        "remarks": quotation_data.get("remarks"),
        "status": "draft",
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.quotations.insert_one(quotation)
    
    # Remove _id before returning (MongoDB adds it)
    quotation.pop("_id", None)
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
    
    # Recalculate valid_until if validity_days is updated
    if "validity_days" in update_fields:
        created_at_str = existing.get("created_at", get_malaysia_time().isoformat())
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except:
            created_at = get_malaysia_time()
        update_fields["valid_until"] = (created_at + timedelta(days=update_fields["validity_days"])).strftime("%Y-%m-%d")
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_fields})
    return {"message": "Quotation updated"}


@router.delete("/quotations/{quotation_id}")
async def delete_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Delete a quotation (only drafts can be deleted)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if existing.get("status") not in ["draft"]:
        raise HTTPException(status_code=400, detail="Only draft quotations can be deleted")
    
    await db.quotations.delete_one({"id": quotation_id})
    return {"message": "Quotation deleted"}



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
    
    # Notify admin for approval
    try:
        # Get client name
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        await notify_quotation_for_approval(quotation, client_name, current_user.full_name)
    except:
        pass
    
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
    
    rejection_reason = reason.get("reason") if reason else None
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "draft", "rejection_reason": rejection_reason}}
    )
    
    # Send email notification
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        await notify_quotation_rejected(quotation, client_name, current_user.full_name, rejection_reason or "")
    except:
        pass
    
    return {"message": "Quotation rejected, returned to draft"}


# Helper function to sync lead stage when quotation status changes
async def sync_lead_stage_from_quotation(quotation_id: str, new_status: str):
    """Called when quotation status changes to sync lead stage and value"""
    lead = await db.leads.find_one({"quotation_id": quotation_id}, {"_id": 0})
    if not lead:
        return
    
    # Get quotation to sync value
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    
    stage_map = {
        "sent": "quotation_sent",
        "accepted": "won",
        "declined": "lost"
    }
    
    new_stage = stage_map.get(new_status)
    update_data = {
        "updated_at": get_malaysia_time().isoformat()
    }
    
    if new_stage and lead.get("stage") != new_stage:
        update_data["stage"] = new_stage
        update_data["stage_changed_at"] = get_malaysia_time().isoformat()
    
    # Sync expected_value with quotation's total_amount
    if quotation and quotation.get("total_amount"):
        update_data["expected_value"] = quotation["total_amount"]
    
    if len(update_data) > 1:  # More than just updated_at
        await db.leads.update_one(
            {"quotation_id": quotation_id},
            {"$set": update_data}
        )


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
    
    # Sync lead stage
    await sync_lead_stage_from_quotation(quotation_id, "sent")
    
    # Send email notification
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        await notify_quotation_sent(quotation, client_name, current_user.full_name)
    except:
        pass
    
    return {"message": "Quotation marked as sent"}


@router.post("/quotations/{quotation_id}/client-response")
async def record_client_response(quotation_id: str, response_data: dict, current_user: User = Depends(get_current_user)):
    """Record client response (accepted/declined). If accepted, auto-creates a draft session."""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    response = response_data.get("response")  # accepted or declined
    if response not in ["accepted", "declined"]:
        raise HTTPException(status_code=400, detail="Response must be 'accepted' or 'declined'")
    
    now = get_malaysia_time()
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {
            "status": response,
            "client_response_at": now.isoformat(),
            "client_response_notes": response_data.get("notes"),
            "training_date": response_data.get("training_date"),
            "venue": response_data.get("venue")
        }}
    )
    
    # Sync lead stage
    await sync_lead_stage_from_quotation(quotation_id, response)
    
    result = {"message": f"Quotation marked as {response}"}
    
    # If accepted, create a draft session
    if response == "accepted":
        # Get client info
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        
        # Create or find company
        company_id = None
        company_name = client.get("company_name", "Unknown Company") if client else "Unknown Company"
        if client:
            existing_company = await db.companies.find_one(
                {"name": {"$regex": f"^{client['company_name']}$", "$options": "i"}},
                {"_id": 0}
            )
            if existing_company:
                company_id = existing_company.get("id")
            else:
                company_id = str(uuid.uuid4())
                await db.companies.insert_one({
                    "id": company_id,
                    "name": client["company_name"],
                    "address": client.get("company_address", ""),
                    "contact_person": client.get("contact_person", ""),
                    "contact_email": client.get("contact_email", ""),
                    "contact_phone": client.get("contact_phone", ""),
                    "created_at": now.isoformat()
                })
        
        # Get training date from response or quotation
        training_date = response_data.get("training_date") or quotation.get("training_date") or now.strftime("%Y-%m-%d")
        end_date = response_data.get("end_date") or training_date
        venue = response_data.get("venue") or quotation.get("venue") or ""
        
        # Create draft session
        session_id = str(uuid.uuid4())
        session_data = {
            "id": session_id,
            "name": f"{company_name} - {quotation.get('programme_name', 'Training')}",
            "program_id": quotation.get("programme_id", ""),
            "company_id": company_id or "",
            "location": venue,
            "start_date": training_date,
            "end_date": end_date,
            "expected_participants": quotation.get("num_participants", 0),
            "status": "draft",
            "completion_status": "ongoing",
            "supervisor_ids": [],
            "participant_ids": [],
            "trainer_assignments": [],
            "quotation_id": quotation_id,
            "marketing_user_id": quotation.get("created_by"),
            "created_at": now.isoformat()
        }
        
        await db.sessions.insert_one(session_data)
        result["session_id"] = session_id
        result["message"] = "Quotation accepted and draft session created"
        
        # Send email notification for accepted quotation
        try:
            await notify_quotation_accepted(quotation, company_name, current_user.full_name)
        except:
            pass
    else:
        # Quotation declined
        try:
            client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
            client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
            await notify_quotation_declined(quotation, client_name, current_user.full_name, response_data.get("notes", ""))
        except:
            pass
    
    return result



@router.post("/quotations/{quotation_id}/apply-discount")
async def apply_discount_to_quotation(quotation_id: str, discount_data: dict, current_user: User = Depends(get_current_user)):
    """Apply discount to a sent quotation (for negotiation) - creates revision number
    
    Validation Rules (Improvement 2 - Marketing & Finance Hardening):
    1. Discount cannot be negative
    2. Discount cannot exceed subtotal
    3. Percentage discount cannot exceed 100%
    4. Cannot apply discount if subtotal = 0
    5. Cannot modify discount if quotation is accepted
    6. Final total must not be negative
    7. SST rate must be valid (0% or 6%)
    """
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # VALIDATION 5: Cannot modify discount if quotation is accepted
    if quotation.get("status") == "accepted":
        raise HTTPException(status_code=400, detail="Cannot modify discount on accepted quotations")
    
    # Only allow discount on SENT quotations (negotiation phase - client has already seen it)
    if quotation.get("status") != "sent":
        raise HTTPException(status_code=400, detail="Discounts can only be applied to quotations that have been sent to the client")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate new totals with discount
    subtotal = quotation.get("subtotal", 0)
    
    # VALIDATION 4: Cannot apply discount if subtotal = 0
    if subtotal <= 0:
        raise HTTPException(status_code=400, detail="Cannot apply discount to quotation with zero or negative subtotal")
    
    discount_type = discount_data.get("discount_type", "percentage")  # percentage or fixed
    discount_value = float(discount_data.get("discount_value", 0))
    
    # VALIDATION 1: Discount cannot be negative
    if discount_value < 0:
        raise HTTPException(status_code=400, detail="Discount value cannot be negative")
    
    # VALIDATION 3: Percentage discount cannot exceed 100%
    if discount_type == "percentage" and discount_value > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100%")
    
    if discount_type == "percentage":
        discount_amount = subtotal * (discount_value / 100)
        discount_percentage = discount_value
    else:
        # VALIDATION 2: Fixed discount cannot exceed subtotal
        if discount_value > subtotal:
            raise HTTPException(status_code=400, detail="Fixed discount cannot exceed subtotal amount")
        discount_amount = discount_value
        discount_percentage = (discount_value / subtotal * 100) if subtotal > 0 else 0
    
    # Recalculate with discount
    discounted_subtotal = subtotal - discount_amount
    
    # VALIDATION 6: Final total must not be negative (sanity check after discount)
    if discounted_subtotal < 0:
        raise HTTPException(status_code=400, detail="Discount would result in negative subtotal")
    
    sst_percentage = quotation.get("sst_percentage", 0)
    
    # VALIDATION 7: SST rate must be valid (0% or 6% for Malaysia)
    if sst_percentage not in [0, 6]:
        raise HTTPException(status_code=400, detail="SST rate must be 0% or 6%")
    
    sst_amount = discounted_subtotal * (sst_percentage / 100)
    new_total = discounted_subtotal + sst_amount
    
    # Increment revision number and update quotation number with suffix
    current_revision = quotation.get("revision_number", 0)
    new_revision = current_revision + 1
    
    # Get base quotation number (without revision suffix)
    base_number = quotation.get("quotation_number", "")
    if "-" in base_number:
        base_number = base_number.split("-")[0]  # Remove existing revision suffix
    
    new_quotation_number = f"{base_number}-{str(new_revision).zfill(2)}"
    
    # Update quotation - set to pending_approval for admin review
    update_data = {
        "quotation_number": new_quotation_number,
        "revision_number": new_revision,
        "discount_percentage": round(discount_percentage, 2),
        "discount_amount": round(discount_amount, 2),
        "sst_amount": round(sst_amount, 2),
        "total_amount": round(new_total, 2),
        "discount_reason": discount_data.get("reason", ""),
        "status": "pending_approval",  # Discount requires admin approval
        "updated_at": get_malaysia_time().isoformat()
    }
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_data})
    
    # Send email notification for discount approval
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        updated_quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
        await notify_discount_request(
            updated_quotation, 
            client_name, 
            current_user.full_name, 
            discount_amount,
            discount_data.get("reason", "")
        )
    except:
        pass
    
    updated_quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    return {
        "message": f"Discount applied - Pending admin approval (Revision {new_revision})",
        "quotation": updated_quotation
    }


# Quotation PDF download is handled by the full implementation in server.py
# with rich text rendering support (bold, italic, highlight, colors, etc.)


# =====================================================
# DESCRIPTION ITEMS
# =====================================================

@router.get("/description-items")
async def get_description_items(current_user: User = Depends(get_current_user)):
    """Get all active description items (for marketers to select when creating quotations)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # All marketers can see all active description items
    items = await db.description_items.find({"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]}, {"_id": 0}).to_list(500)
    items.sort(key=lambda x: (x.get("category", ""), x.get("sort_order", 0)))
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
    """Create a description item (Admin only for inclusions/exclusions)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create description items")
    
    item = {
        "id": str(uuid.uuid4()),
        "name": item_data.get("name"),
        "description": item_data.get("description", ""),
        "category": item_data.get("category", "inclusion"),  # "inclusion" or "exclusion"
        "has_quantity": item_data.get("has_quantity", False),  # Whether to show quantity input
        "is_active": True,
        "sort_order": item_data.get("sort_order", 0),
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.description_items.insert_one(item)
    # Remove _id added by MongoDB before returning
    item.pop("_id", None)
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
    
    templates = await db.quotation_pdf_templates.find_one({"id": "quotation_pdf_templates"}, {"_id": 0})
    return templates or {"id": "quotation_pdf_templates", "cover_letter": "", "terms_conditions_pages": "", "primary_color": "#1a365d"}


@router.put("/pdf-templates")
async def update_pdf_templates(template_data: dict, current_user: User = Depends(get_current_user)):
    """Update PDF templates (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    template_data["id"] = "quotation_pdf_templates"
    await db.quotation_pdf_templates.update_one(
        {"id": "quotation_pdf_templates"},
        {"$set": template_data},
        upsert=True
    )
    return {"message": "Templates updated"}


# ==================== LEAD PIPELINE ====================

class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None  # referral, website, cold_call, event, other
    stage: str = "inquiry"  # inquiry, contacted, quotation_sent, negotiating, won, lost
    notes: Optional[str] = None
    expected_value: float = 0
    follow_up_date: Optional[str] = None  # ISO date string
    lost_reason: Optional[str] = None
    quotation_id: Optional[str] = None
    client_id: Optional[str] = None  # Link to client if converted
    created_by: str  # Marketing user ID
    created_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    updated_at: datetime = Field(default_factory=get_malaysia_time)
    stage_changed_at: datetime = Field(default_factory=get_malaysia_time)


class LeadCreate(BaseModel):
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    expected_value: float = 0
    follow_up_date: Optional[str] = None


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    stage: Optional[str] = None
    notes: Optional[str] = None
    expected_value: Optional[float] = None
    follow_up_date: Optional[str] = None
    lost_reason: Optional[str] = None
    quotation_id: Optional[str] = None
    client_id: Optional[str] = None


@router.get("/leads")
async def get_leads(
    stage: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leads - Marketing sees own, Admin sees all"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    
    # Marketing users only see their own leads
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    if stage:
        query["stage"] = stage
    
    leads = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return leads


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get single lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return lead


@router.post("/leads")
async def create_lead(lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    """Create new lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Check for duplicate company name for this user's leads
    existing = await db.leads.find_one({
        "company_name": {"$regex": f"^{lead_data.company_name.strip()}$", "$options": "i"},
        "created_by": current_user.id,
        "stage": {"$nin": ["won", "lost"]}  # Allow if previous lead was closed
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"You already have an active lead for '{lead_data.company_name}'. Please update the existing lead instead."
        )
    
    lead = Lead(
        company_name=lead_data.company_name.strip(),
        company_address=lead_data.company_address,
        contact_person=lead_data.contact_person,
        contact_email=lead_data.contact_email,
        contact_phone=lead_data.contact_phone,
        source=lead_data.source,
        notes=lead_data.notes,
        expected_value=lead_data.expected_value,
        follow_up_date=lead_data.follow_up_date,
        created_by=current_user.id,
        created_by_name=current_user.full_name
    )
    
    doc = lead.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    doc["stage_changed_at"] = doc["stage_changed_at"].isoformat()
    
    await db.leads.insert_one(doc)
    
    # Send email notification to admin
    try:
        await notify_new_lead(doc, current_user.full_name)
    except Exception as e:
        # Don't fail lead creation if email fails
        pass
    
    return lead


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, lead_data: LeadUpdate, current_user: User = Depends(get_current_user)):
    """Update lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = {k: v for k, v in lead_data.model_dump().items() if v is not None}
    update_data["updated_at"] = get_malaysia_time().isoformat()
    
    # Track stage changes and notify admin for key stages
    new_stage = update_data.get("stage")
    old_stage = lead.get("stage")
    if new_stage and new_stage != old_stage:
        update_data["stage_changed_at"] = get_malaysia_time().isoformat()
        # Notify admin for key stage changes
        if new_stage in ["contacted", "quotation_sent"]:
            try:
                await notify_lead_stage_change(lead, new_stage, current_user.full_name)
            except:
                pass
        elif new_stage == "won":
            try:
                # Get quotation for deal value
                quotation = None
                if lead.get("quotation_id"):
                    quotation = await db.quotations.find_one({"id": lead.get("quotation_id")}, {"_id": 0})
                await notify_lead_won(lead, quotation, current_user.full_name)
            except:
                pass
        elif new_stage == "lost":
            try:
                lost_reason = update_data.get("lost_reason", "") or lead_data.notes if hasattr(lead_data, 'notes') else ""
                await notify_lead_lost(lead, current_user.full_name, lost_reason)
            except:
                pass
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    # Sync client data if lead has a linked client and contact info changed
    if lead.get("client_id"):
        client_sync_fields = {}
        if "company_name" in update_data:
            client_sync_fields["company_name"] = update_data["company_name"]
        if "company_address" in update_data:
            client_sync_fields["company_address"] = update_data["company_address"]
        if "contact_person" in update_data:
            client_sync_fields["contact_person"] = update_data["contact_person"]
        if "contact_email" in update_data:
            client_sync_fields["contact_email"] = update_data["contact_email"]
        if "contact_phone" in update_data:
            client_sync_fields["contact_phone"] = update_data["contact_phone"]
        
        if client_sync_fields:
            client_sync_fields["updated_at"] = get_malaysia_time().isoformat()
            await db.marketing_clients.update_one(
                {"id": lead["client_id"]},
                {"$set": client_sync_fields}
            )
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return updated_lead


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Delete lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.leads.delete_one({"id": lead_id})
    return {"message": "Lead deleted"}


@router.post("/leads/{lead_id}/revive")
async def revive_lead(lead_id: str, revive_data: dict, current_user: User = Depends(get_current_user)):
    """Revive a lost lead for future follow-up"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.get("stage") != "lost":
        raise HTTPException(status_code=400, detail="Only lost leads can be revived")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    update_data = {
        "stage": "inquiry",  # Reset to inquiry
        "follow_up_date": revive_data.get("follow_up_date"),
        "notes": f"{lead.get('notes', '')}\n\n[Revived on {now.strftime('%d/%m/%Y')}] {revive_data.get('reason', '')}".strip(),
        "lost_reason": None,  # Clear lost reason
        "stage_changed_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return {"message": "Lead revived successfully", "lead": updated_lead}


@router.post("/leads/{lead_id}/mark-won")
async def mark_lead_won_and_create_session(lead_id: str, win_data: dict, current_user: User = Depends(get_current_user)):
    """Mark lead as won and optionally create draft session"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    now = get_malaysia_time()
    
    # Update lead to won
    lead_update = {
        "stage": "won",
        "stage_changed_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.leads.update_one({"id": lead_id}, {"$set": lead_update})
    
    result = {"message": "Lead marked as won"}
    
    # Create draft session if training date provided
    training_date = win_data.get("training_date")
    if training_date:
        # Get client and quotation info
        client = None
        if lead.get("client_id"):
            client = await db.marketing_clients.find_one({"id": lead["client_id"]}, {"_id": 0})
        
        quotation = None
        if lead.get("quotation_id"):
            quotation = await db.quotations.find_one({"id": lead["quotation_id"]}, {"_id": 0})
        
        # Create or find company
        company_id = None
        if client:
            # Check if company exists
            existing_company = await db.companies.find_one(
                {"name": {"$regex": f"^{client['company_name']}$", "$options": "i"}},
                {"_id": 0}
            )
            if existing_company:
                company_id = existing_company.get("id")
            else:
                # Create company
                company_id = str(uuid.uuid4())
                await db.companies.insert_one({
                    "id": company_id,
                    "name": client["company_name"],
                    "address": client.get("company_address", ""),
                    "contact_person": client.get("contact_person", ""),
                    "contact_email": client.get("contact_email", ""),
                    "contact_phone": client.get("contact_phone", ""),
                    "created_at": now.isoformat()
                })
        
        # Get programme info
        programme_id = quotation.get("programme_id") if quotation else None
        programme_name = quotation.get("programme_name") if quotation else "Training Programme"
        
        # Create draft session
        session_id = str(uuid.uuid4())
        end_date = win_data.get("end_date") or training_date
        num_participants = win_data.get("num_participants", 0)
        
        session_data = {
            "id": session_id,
            "name": f"{client['company_name'] if client else lead['company_name']} - {programme_name}",
            "program_id": programme_id or "",
            "company_id": company_id or "",
            "location": win_data.get("venue", quotation.get("venue", "") if quotation else ""),
            "start_date": training_date,
            "end_date": end_date,
            "expected_participants": num_participants,
            "status": "draft",  # Draft status for admin review
            "completion_status": "ongoing",
            "supervisor_ids": [],
            "participant_ids": [],
            "trainer_assignments": [],
            "grant_id": win_data.get("grant_id", ""),
            "lead_id": lead_id,
            "quotation_id": lead.get("quotation_id"),
            "marketing_user_id": lead.get("created_by"),
            "created_at": now.isoformat()
        }
        
        await db.sessions.insert_one(session_data)
        result["session_id"] = session_id
        result["message"] = "Lead marked as won and draft session created"
    
    return result



@router.put("/leads/{lead_id}/stage")
async def update_lead_stage(lead_id: str, stage: str, current_user: User = Depends(get_current_user)):
    """Quick update lead stage (for drag-drop)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    valid_stages = ["inquiry", "contacted", "quotation_sent", "negotiating", "won", "lost"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "stage": stage,
            "updated_at": get_malaysia_time().isoformat(),
            "stage_changed_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": f"Lead moved to {stage}"}


@router.post("/leads/{lead_id}/convert-to-client")
async def convert_lead_to_client(lead_id: str, current_user: User = Depends(get_current_user)):
    """Convert a lead to a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if already converted
    if lead.get("client_id"):
        raise HTTPException(status_code=400, detail="Lead already converted to client")
    
    # Create client from lead
    client = MarketingClient(
        company_name=lead["company_name"],
        contact_person=lead.get("contact_person"),
        contact_email=lead.get("contact_email"),
        contact_phone=lead.get("contact_phone"),
        notes=f"Converted from lead. Original notes: {lead.get('notes', '')}",
        created_by=current_user.id
    )
    
    doc = client.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.marketing_clients.insert_one(doc)
    
    # Update lead with client_id and mark as won
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "client_id": client.id,
            "stage": "won",
            "updated_at": get_malaysia_time().isoformat(),
            "stage_changed_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Lead converted to client", "client_id": client.id}


# ==================== FOLLOW-UP REMINDERS ====================

@router.get("/leads/reminders/pending")
async def get_pending_reminders(current_user: User = Depends(get_current_user)):
    """Get leads with overdue or upcoming follow-ups"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    today = get_malaysia_time().strftime("%Y-%m-%d")
    
    query = {
        "follow_up_date": {"$ne": None, "$lte": today},
        "stage": {"$nin": ["won", "lost"]}  # Only active leads
    }
    
    # Marketing users only see their own
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    overdue = await db.leads.find(query, {"_id": 0}).sort("follow_up_date", 1).to_list(100)
    
    # Also get upcoming (next 7 days)
    from datetime import timedelta
    next_week = (get_malaysia_time() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    upcoming_query = {
        "follow_up_date": {"$gt": today, "$lte": next_week},
        "stage": {"$nin": ["won", "lost"]}
    }
    if current_user.role not in ["admin", "super_admin"]:
        upcoming_query["created_by"] = current_user.id
    
    upcoming = await db.leads.find(upcoming_query, {"_id": 0}).sort("follow_up_date", 1).to_list(100)
    
    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "overdue_count": len(overdue),
        "upcoming_count": len(upcoming)
    }


# ==================== QUICK STATS ====================

@router.get("/stats/pipeline")
async def get_pipeline_stats(current_user: User = Depends(get_current_user)):
    """Get lead pipeline statistics - Marketing sees own, Admin sees all"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    # Get all leads for this user
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    
    # Count by stage
    stage_counts = {
        "inquiry": 0,
        "contacted": 0,
        "quotation_sent": 0,
        "negotiating": 0,
        "won": 0,
        "lost": 0
    }
    
    total_value = 0
    won_value = 0
    won_count = 0
    total_days_to_close = 0
    
    for lead in leads:
        stage = lead.get("stage", "inquiry")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        total_value += lead.get("expected_value", 0)
        
        if stage == "won":
            won_value += lead.get("expected_value", 0)
            won_count += 1
            # Calculate days to close
            if lead.get("created_at") and lead.get("stage_changed_at"):
                try:
                    created = datetime.fromisoformat(lead["created_at"].replace("Z", "+00:00")) if isinstance(lead["created_at"], str) else lead["created_at"]
                    closed = datetime.fromisoformat(lead["stage_changed_at"].replace("Z", "+00:00")) if isinstance(lead["stage_changed_at"], str) else lead["stage_changed_at"]
                    days = (closed - created).days
                    total_days_to_close += max(days, 0)
                except:
                    pass
    
    total_leads = len(leads)
    closed_leads = stage_counts["won"] + stage_counts["lost"]
    
    # Calculate conversion rate
    conversion_rate = round((won_count / closed_leads * 100), 1) if closed_leads > 0 else 0
    
    # Average deal size
    avg_deal_size = round(won_value / won_count, 2) if won_count > 0 else 0
    
    # Average days to close
    avg_days_to_close = round(total_days_to_close / won_count, 1) if won_count > 0 else 0
    
    return {
        "stage_counts": stage_counts,
        "total_leads": total_leads,
        "total_pipeline_value": total_value,
        "won_value": won_value,
        "conversion_rate": conversion_rate,
        "avg_deal_size": avg_deal_size,
        "avg_days_to_close": avg_days_to_close,
        "active_leads": total_leads - closed_leads
    }


@router.get("/stats/by-source")
async def get_stats_by_source(current_user: User = Depends(get_current_user)):
    """Get lead stats grouped by source"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    
    source_stats = {}
    for lead in leads:
        source = lead.get("source") or "unknown"
        if source not in source_stats:
            source_stats[source] = {"total": 0, "won": 0, "value": 0}
        source_stats[source]["total"] += 1
        if lead.get("stage") == "won":
            source_stats[source]["won"] += 1
            source_stats[source]["value"] += lead.get("expected_value", 0)
    
    return source_stats


@router.get("/stats/by-user")
async def get_stats_by_user(current_user: User = Depends(get_current_user)):
    """Get lead stats by marketing user (Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    leads = await db.leads.find({}, {"_id": 0}).to_list(1000)
    
    user_stats = {}
    for lead in leads:
        user_id = lead.get("created_by", "unknown")
        user_name = lead.get("created_by_name", "Unknown")
        
        if user_id not in user_stats:
            user_stats[user_id] = {
                "user_name": user_name,
                "total": 0,
                "won": 0,
                "lost": 0,
                "active": 0,
                "total_value": 0,
                "won_value": 0
            }
        
        user_stats[user_id]["total"] += 1
        user_stats[user_id]["total_value"] += lead.get("expected_value", 0)
        
        stage = lead.get("stage")
        if stage == "won":
            user_stats[user_id]["won"] += 1
            user_stats[user_id]["won_value"] += lead.get("expected_value", 0)
        elif stage == "lost":
            user_stats[user_id]["lost"] += 1
        else:
            user_stats[user_id]["active"] += 1
    
    return user_stats


# ==================== LEAD TO QUOTATION ====================

@router.post("/leads/{lead_id}/create-quotation")
async def create_quotation_from_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Create a quotation from a lead - auto-creates client if needed"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Get the lead
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if lead already has a quotation
    if lead.get("quotation_id"):
        existing_quotation = await db.quotations.find_one({"id": lead["quotation_id"]}, {"_id": 0})
        if existing_quotation:
            return {
                "message": "Lead already has a quotation",
                "quotation_id": lead["quotation_id"],
                "client_id": lead.get("client_id"),
                "already_exists": True
            }
    
    # Check if client already exists (by company name for this marketing user)
    client_id = lead.get("client_id")
    if not client_id:
        existing_client = await db.marketing_clients.find_one({
            "company_name": lead["company_name"],
            "created_by": current_user.id
        }, {"_id": 0})
        
        if existing_client:
            client_id = existing_client["id"]
        else:
            # Auto-create client from lead data
            new_client = MarketingClient(
                company_name=lead["company_name"],
                company_address=lead.get("company_address"),
                contact_person=lead.get("contact_person"),
                contact_email=lead.get("contact_email"),
                contact_phone=lead.get("contact_phone"),
                notes=f"Auto-created from lead. Source: {lead.get('source', 'N/A')}",
                created_by=current_user.id
            )
            
            doc = new_client.model_dump()
            doc["created_at"] = doc["created_at"].isoformat()
            await db.marketing_clients.insert_one(doc)
            client_id = new_client.id
    
    # Update lead with client_id
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "client_id": client_id,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    # Return client data for quotation form pre-fill
    client = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    
    return {
        "message": "Client ready for quotation",
        "client_id": client_id,
        "client": client,
        "lead_id": lead_id,
        "already_exists": False
    }


@router.put("/leads/{lead_id}/link-quotation")
async def link_quotation_to_lead(lead_id: str, quotation_id: str, current_user: User = Depends(get_current_user)):
    """Link a quotation to a lead and update stage"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify quotation exists
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Update lead with quotation link and sync value
    update_data = {
        "quotation_id": quotation_id,
        "updated_at": get_malaysia_time().isoformat()
    }
    
    # Sync expected_value with quotation's total_amount
    if quotation.get("total_amount"):
        update_data["expected_value"] = quotation["total_amount"]
    
    # Auto-update stage based on quotation status
    quotation_status = quotation.get("status", "draft")
    if quotation_status in ["sent", "accepted", "declined"]:
        if quotation_status == "accepted":
            update_data["stage"] = "won"
        elif quotation_status == "declined":
            update_data["stage"] = "lost"
        else:
            update_data["stage"] = "quotation_sent"
        update_data["stage_changed_at"] = get_malaysia_time().isoformat()
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    return {"message": "Quotation linked to lead", "stage": update_data.get("stage")}



