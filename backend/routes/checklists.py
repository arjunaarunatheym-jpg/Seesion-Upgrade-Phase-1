"""
Checklists routes - Checklist templates, submissions, and vehicle details
Endpoints: 15+
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime
import uuid
import shutil
from pathlib import Path

from core import db, get_current_user, get_malaysia_time, get_or_create_participant_access
from models import User

from pydantic import BaseModel, Field, ConfigDict

# Models
class ChecklistItem(BaseModel):
    name: str
    description: Optional[str] = None

class ChecklistTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program_id: str
    items: List[ChecklistItem] = []
    created_at: datetime = Field(default_factory=get_malaysia_time)

class ChecklistTemplateCreate(BaseModel):
    program_id: str
    items: List[ChecklistItem]

class ChecklistSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    trainer_id: str
    items: List[dict] = []
    photos: List[str] = []
    submitted_at: datetime = Field(default_factory=get_malaysia_time)
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

class ChecklistSubmit(BaseModel):
    session_id: str
    participant_id: str
    items: List[dict]
    photos: List[str] = []

class VehicleDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    vehicle_model: str
    registration_number: str
    roadtax_expiry: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class VehicleDetailsSubmit(BaseModel):
    session_id: str
    vehicle_model: str
    registration_number: str
    roadtax_expiry: Optional[str] = None

# Paths
STATIC_DIR = Path(__file__).parent.parent / "static"
CHECKLIST_PHOTOS_DIR = STATIC_DIR / "checklist_photos"
CHECKLIST_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(tags=["checklists"])


# Checklist Template Routes
@router.post("/checklist-templates", response_model=ChecklistTemplate)
async def create_checklist_template(template_data: ChecklistTemplateCreate, current_user: User = Depends(get_current_user)):
    """Create or update checklist template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can create checklist templates")
    
    existing = await db.checklist_templates.find_one({"program_id": template_data.program_id}, {"_id": 0})
    if existing:
        await db.checklist_templates.update_one(
            {"program_id": template_data.program_id},
            {"$set": {"items": [item.model_dump() for item in template_data.items]}}
        )
        existing['items'] = [item.model_dump() for item in template_data.items]
        if isinstance(existing.get('created_at'), str):
            existing['created_at'] = datetime.fromisoformat(existing['created_at'])
        return ChecklistTemplate(**existing)
    
    template_obj = ChecklistTemplate(
        program_id=template_data.program_id,
        items=template_data.items
    )
    doc = template_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.checklist_templates.insert_one(doc)
    return template_obj


@router.get("/checklist-templates", response_model=List[ChecklistTemplate])
async def get_all_checklist_templates(current_user: User = Depends(get_current_user)):
    """Get all checklist templates"""
    templates = await db.checklist_templates.find({}, {"_id": 0}).to_list(100)
    result = []
    for template in templates:
        if isinstance(template.get('created_at'), str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
        # Handle legacy data where items might be strings instead of ChecklistItem objects
        if template.get('items'):
            normalized_items = []
            for item in template['items']:
                if isinstance(item, str):
                    normalized_items.append({"name": item, "description": None})
                elif isinstance(item, dict):
                    normalized_items.append(item)
            template['items'] = normalized_items
        result.append(ChecklistTemplate(**template))
    return result


@router.get("/checklist-templates/program/{program_id}", response_model=ChecklistTemplate)
async def get_checklist_template(program_id: str, current_user: User = Depends(get_current_user)):
    """Get checklist template for a program"""
    template = await db.checklist_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        return ChecklistTemplate(program_id=program_id, items=[])
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    # Handle legacy data where items might be strings instead of ChecklistItem objects
    if template.get('items'):
        normalized_items = []
        for item in template['items']:
            if isinstance(item, str):
                normalized_items.append({"name": item, "description": None})
            elif isinstance(item, dict):
                normalized_items.append(item)
        template['items'] = normalized_items
    return ChecklistTemplate(**template)


@router.get("/checklists/templates/program/{program_id}", response_model=ChecklistTemplate)
async def get_checklist_template_alias(program_id: str, current_user: User = Depends(get_current_user)):
    """Alias endpoint for backward compatibility - trainers use this"""
    template = await db.checklist_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        return ChecklistTemplate(program_id=program_id, items=[])
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    # Handle legacy data where items might be strings instead of ChecklistItem objects
    if template.get('items'):
        normalized_items = []
        for item in template['items']:
            if isinstance(item, str):
                normalized_items.append({"name": item, "description": None})
            elif isinstance(item, dict):
                normalized_items.append(item)
        template['items'] = normalized_items
    return ChecklistTemplate(**template)


@router.get("/checklists/templates", response_model=List[ChecklistTemplate])
async def get_all_checklist_templates_alias(current_user: User = Depends(get_current_user)):
    """Alias endpoint for /checklist-templates"""
    templates = await db.checklist_templates.find({}, {"_id": 0}).to_list(100)
    result = []
    for t in templates:
        if isinstance(t.get('created_at'), str):
            t['created_at'] = datetime.fromisoformat(t['created_at'])
        # Handle legacy data where items might be strings instead of ChecklistItem objects
        if t.get('items'):
            normalized_items = []
            for item in t['items']:
                if isinstance(item, str):
                    normalized_items.append({"name": item, "description": None})
                elif isinstance(item, dict):
                    normalized_items.append(item)
            t['items'] = normalized_items
        result.append(ChecklistTemplate(**t))
    return result


@router.put("/checklist-templates/{template_id}", response_model=ChecklistTemplate)
async def update_checklist_template(template_id: str, template_data: ChecklistTemplateCreate, current_user: User = Depends(get_current_user)):
    """Update a checklist template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can update checklist templates")
    
    existing = await db.checklist_templates.find_one({"id": template_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    items_data = [item.model_dump() for item in template_data.items]
    await db.checklist_templates.update_one(
        {"id": template_id},
        {"$set": {"items": items_data, "program_id": template_data.program_id}}
    )
    
    existing['items'] = items_data
    existing['program_id'] = template_data.program_id
    if isinstance(existing.get('created_at'), str):
        existing['created_at'] = datetime.fromisoformat(existing['created_at'])
    
    return ChecklistTemplate(**existing)


@router.delete("/checklist-templates/{template_id}/items/{item_index}")
async def delete_checklist_item(template_id: str, item_index: int, current_user: User = Depends(get_current_user)):
    """Delete a specific item from a checklist template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete checklist items")
    
    template = await db.checklist_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if item_index < 0 or item_index >= len(template.get("items", [])):
        raise HTTPException(status_code=400, detail="Invalid item index")
    
    items = template.get("items", [])
    items.pop(item_index)
    
    await db.checklist_templates.update_one({"id": template_id}, {"$set": {"items": items}})
    return {"message": "Checklist item deleted successfully"}


@router.delete("/checklist-templates/{template_id}")
async def delete_checklist_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Delete a checklist template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete checklist templates")
    
    result = await db.checklist_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}


@router.post("/checklist-templates/bulk-upload")
async def bulk_upload_checklist_items(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Bulk upload checklist items from Excel file"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        import pandas as pd
        import io
        
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        df.columns = df.columns.str.strip()
        
        # Group by program
        programs_items = {}
        for idx, row in df.iterrows():
            program_name = str(row.get('Program Name', '')).strip()
            item_name = str(row.get('Item Name', '')).strip()
            
            if not program_name or not item_name:
                continue
            
            if program_name not in programs_items:
                programs_items[program_name] = []
            programs_items[program_name].append({"name": item_name})
        
        results = []
        for program_name, items in programs_items.items():
            program = await db.programs.find_one({"name": program_name}, {"_id": 0})
            if not program:
                results.append({"program": program_name, "status": "not_found"})
                continue
            
            existing = await db.checklist_templates.find_one({"program_id": program["id"]}, {"_id": 0})
            if existing:
                await db.checklist_templates.update_one(
                    {"program_id": program["id"]},
                    {"$set": {"items": items}}
                )
            else:
                await db.checklist_templates.insert_one({
                    "id": str(uuid.uuid4()),
                    "program_id": program["id"],
                    "items": items,
                    "created_at": get_malaysia_time().isoformat()
                })
            results.append({"program": program_name, "status": "success", "items_count": len(items)})
        
        return {"message": "Bulk upload complete", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


# Checklist Submission Routes
@router.post("/checklists/submit")
async def submit_checklist(checklist_data: ChecklistSubmit, current_user: User = Depends(get_current_user)):
    """Submit checklist for a participant (trainer only)"""
    if current_user.role not in ["trainer", "admin"]:
        raise HTTPException(status_code=403, detail="Only trainers can submit checklists")
    
    existing = await db.checklist_submissions.find_one({
        "participant_id": checklist_data.participant_id,
        "session_id": checklist_data.session_id
    }, {"_id": 0})
    
    if existing:
        await db.checklist_submissions.update_one(
            {"participant_id": checklist_data.participant_id, "session_id": checklist_data.session_id},
            {"$set": {
                "items": checklist_data.items,
                "photos": checklist_data.photos,
                "trainer_id": current_user.id,
                "submitted_at": get_malaysia_time().isoformat()
            }}
        )
    else:
        submission = ChecklistSubmission(
            participant_id=checklist_data.participant_id,
            session_id=checklist_data.session_id,
            trainer_id=current_user.id,
            items=checklist_data.items,
            photos=checklist_data.photos
        )
        doc = submission.model_dump()
        doc['submitted_at'] = doc['submitted_at'].isoformat()
        await db.checklist_submissions.insert_one(doc)
    
    await db.participant_access.update_one(
        {"participant_id": checklist_data.participant_id, "session_id": checklist_data.session_id},
        {"$set": {"checklist_submitted": True, "checklist_completed": True}},
        upsert=True
    )
    
    return {"message": "Checklist submitted successfully"}


@router.get("/checklists/session/{session_id}")
async def get_session_checklists(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all checklist submissions for a session"""
    checklists = await db.checklist_submissions.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    for c in checklists:
        if isinstance(c.get('submitted_at'), str):
            c['submitted_at'] = datetime.fromisoformat(c['submitted_at'])
    return checklists


@router.get("/checklists/pending")
async def get_pending_checklists(current_user: User = Depends(get_current_user)):
    """Get pending checklist submissions for coordinator"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can view pending checklists")
    
    checklists = await db.checklist_submissions.find({"verified": False}, {"_id": 0}).to_list(1000)
    return checklists


@router.get("/checklists/participant/{participant_id}")
async def get_participant_checklists(participant_id: str, current_user: User = Depends(get_current_user)):
    """Get checklist submissions for a participant"""
    checklists = await db.checklist_submissions.find({"participant_id": participant_id}, {"_id": 0}).to_list(100)
    for c in checklists:
        if isinstance(c.get('submitted_at'), str):
            c['submitted_at'] = datetime.fromisoformat(c['submitted_at'])
    return checklists


@router.post("/checklists/verify")
async def verify_checklist(submission_id: str, current_user: User = Depends(get_current_user)):
    """Verify a checklist submission"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can verify checklists")
    
    await db.checklist_submissions.update_one(
        {"id": submission_id},
        {"$set": {
            "verified": True,
            "verified_by": current_user.id,
            "verified_at": get_malaysia_time().isoformat()
        }}
    )
    return {"message": "Checklist verified successfully"}


@router.post("/checklist-photos/upload")
async def upload_checklist_photo(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    participant_id: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a photo for checklist"""
    if current_user.role not in ["trainer", "admin"]:
        raise HTTPException(status_code=403, detail="Only trainers can upload photos")
    
    file_ext = file.filename.split(".")[-1]
    filename = f"{session_id}_{participant_id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = CHECKLIST_PHOTOS_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    photo_url = f"/api/static/checklist-photos/{filename}"
    return {"photo_url": photo_url}


# Vehicle Details Routes
@router.post("/vehicle-details/submit", response_model=VehicleDetails)
async def submit_vehicle_details(vehicle_data: VehicleDetailsSubmit, current_user: User = Depends(get_current_user)):
    """Submit vehicle details"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can submit vehicle details")
    
    existing = await db.vehicle_details.find_one({
        "participant_id": current_user.id,
        "session_id": vehicle_data.session_id
    }, {"_id": 0})
    
    if existing:
        await db.vehicle_details.update_one(
            {"participant_id": current_user.id, "session_id": vehicle_data.session_id},
            {"$set": {
                "vehicle_model": vehicle_data.vehicle_model,
                "registration_number": vehicle_data.registration_number,
                "roadtax_expiry": vehicle_data.roadtax_expiry
            }}
        )
        existing.update(vehicle_data.model_dump())
        if isinstance(existing.get('created_at'), str):
            existing['created_at'] = datetime.fromisoformat(existing['created_at'])
        return VehicleDetails(**existing)
    
    vehicle_obj = VehicleDetails(
        participant_id=current_user.id,
        session_id=vehicle_data.session_id,
        vehicle_model=vehicle_data.vehicle_model,
        registration_number=vehicle_data.registration_number,
        roadtax_expiry=vehicle_data.roadtax_expiry
    )
    
    doc = vehicle_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.vehicle_details.insert_one(doc)
    
    return vehicle_obj


@router.get("/vehicle-details/{session_id}/{participant_id}")
async def get_vehicle_details(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    """Get vehicle details for a participant"""
    details = await db.vehicle_details.find_one({
        "participant_id": participant_id,
        "session_id": session_id
    }, {"_id": 0})
    
    if details and isinstance(details.get('created_at'), str):
        details['created_at'] = datetime.fromisoformat(details['created_at'])
    
    return details


@router.get("/vehicle-checklists/{session_id}/{participant_id}")
async def get_vehicle_checklists(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    """Get vehicle checklist for a participant"""
    checklists = await db.checklist_submissions.find({
        "participant_id": participant_id,
        "session_id": session_id
    }, {"_id": 0}).to_list(10)
    
    for c in checklists:
        if isinstance(c.get('submitted_at'), str):
            c['submitted_at'] = datetime.fromisoformat(c['submitted_at'])
    
    return checklists



# Trainer Checklist Models (different from template ChecklistItem)
class TrainerChecklistItem(BaseModel):
    item: str
    status: str  # "good", "needs_repair", "na"
    comments: Optional[str] = None
    photo_url: Optional[str] = None


class TrainerChecklistSubmit(BaseModel):
    participant_id: str
    session_id: str
    items: List[TrainerChecklistItem]
    chief_trainer_comments: Optional[str] = None


@router.post("/trainer-checklist/submit")
async def submit_trainer_checklist(checklist_data: TrainerChecklistSubmit, current_user: User = Depends(get_current_user)):
    """Submit a trainer's vehicle inspection checklist"""
    if current_user.role not in ["trainer", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only trainers can submit vehicle checklists")

    session = await db.sessions.find_one({"id": checklist_data.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    participant = await db.users.find_one({"id": checklist_data.participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    checklist_id = str(uuid.uuid4())
    now = get_malaysia_time()

    checklist_doc = {
        "id": checklist_id,
        "session_id": checklist_data.session_id,
        "participant_id": checklist_data.participant_id,
        "participant_name": participant.get("full_name", ""),
        "trainer_id": current_user.id,
        "trainer_name": current_user.full_name,
        "interval": "trainer_inspection",
        "checklist_items": [item.model_dump() for item in checklist_data.items],
        "chief_trainer_comments": checklist_data.chief_trainer_comments,
        "status": "completed",
        "submitted_at": now.isoformat(),
        "created_at": now.isoformat()
    }

    await db.vehicle_checklists.insert_one(checklist_doc)

    access = await get_or_create_participant_access(
        checklist_data.participant_id,
        checklist_data.session_id,
        session.get("program_id")
    )
    if access:
        await db.participant_access.update_one(
            {"id": access["id"]},
            {"$set": {"trainer_checklist_submitted": True, "updated_at": now.isoformat()}}
        )

    return {"message": "Trainer checklist submitted successfully", "checklist_id": checklist_id}


@router.get("/trainer-checklist/{session_id}/assigned-participants")
async def get_trainer_assigned_participants(session_id: str, current_user: User = Depends(get_current_user)):
    """Get participants assigned to the current trainer for a session"""
    if current_user.role not in ["trainer", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only trainers can view their assigned participants")

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    trainer_assignments = session.get("trainer_assignments", [])
    trainer_assignment = None
    for ta in trainer_assignments:
        if ta.get("trainer_id") == current_user.id:
            trainer_assignment = ta
            break

    if not trainer_assignment and current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="You are not assigned to this session")

    if trainer_assignment and trainer_assignment.get("participant_ids"):
        participant_ids = trainer_assignment.get("participant_ids", [])
    else:
        participant_ids = session.get("participant_ids", [])

    participants = []
    for pid in participant_ids:
        p = await db.users.find_one({"id": pid}, {"_id": 0})
        if p:
            existing_checklist = await db.vehicle_checklists.find_one({
                "session_id": session_id,
                "participant_id": pid,
                "trainer_id": current_user.id,
                "interval": "trainer_inspection"
            }, {"_id": 0})

            participants.append({
                "id": p["id"],
                "full_name": p.get("full_name", ""),
                "id_number": p.get("id_number", ""),
                "checklist_submitted": existing_checklist is not None,
                "checklist_id": existing_checklist.get("id") if existing_checklist else None
            })

    return {
        "session_id": session_id,
        "trainer_role": trainer_assignment.get("role") if trainer_assignment else "admin",
        "participants": participants
    }
