"""
Super Admin routes - Testing panel for quick data entry
Endpoints: 5 (excluding test submit which is in tests.py)
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone
from pydantic import BaseModel
import pytz

from core import db, get_current_user, get_malaysia_time
from models import User, Attendance, VehicleChecklist, CourseFeedback, VehicleDetails

router = APIRouter(prefix="/super-admin", tags=["super-admin"])

MALAYSIA_TZ = pytz.timezone("Asia/Kuala_Lumpur")


# Request Models
class SuperAdminClockIn(BaseModel):
    session_id: str
    participant_id: str
    clock_in: str


class SuperAdminClockOut(BaseModel):
    session_id: str
    participant_id: str
    clock_out: str


class SuperAdminVehicleDetails(BaseModel):
    session_id: str
    participant_id: str
    vehicle_model: str
    registration_number: str
    roadtax_expiry: str


class SuperAdminChecklistSubmit(BaseModel):
    session_id: str
    participant_id: str
    checklist_items: List[dict]


class SuperAdminFeedbackSubmit(BaseModel):
    session_id: str
    participant_id: str
    responses: List[dict]


@router.post("/attendance/clock-in")
async def super_admin_clock_in(data: SuperAdminClockIn, current_user: User = Depends(get_current_user)):
    """Super admin clock in for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can manage attendance")
    
    clock_in_dt = datetime.fromisoformat(data.clock_in.replace('Z', '+00:00'))
    clock_in_malaysia = clock_in_dt.astimezone(MALAYSIA_TZ)
    date_str = clock_in_malaysia.date().isoformat()
    time_str = clock_in_malaysia.strftime("%H:%M:%S")
    
    existing = await db.attendance.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    }, {"_id": 0})
    
    if existing:
        await db.attendance.update_one(
            {"id": existing['id']},
            {"$set": {"clock_in": time_str, "date": date_str}}
        )
    else:
        attendance_obj = Attendance(
            participant_id=data.participant_id,
            session_id=data.session_id,
            date=date_str,
            clock_in=time_str
        )
        doc = attendance_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.attendance.insert_one(doc)
    
    return {"message": "Attendance updated successfully"}


@router.post("/attendance/clock-out")
async def super_admin_clock_out(data: SuperAdminClockOut, current_user: User = Depends(get_current_user)):
    """Super admin clock out for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can manage attendance")
    
    clock_out_dt = datetime.fromisoformat(data.clock_out.replace('Z', '+00:00'))
    clock_out_malaysia = clock_out_dt.astimezone(MALAYSIA_TZ)
    time_str = clock_out_malaysia.strftime("%H:%M:%S")
    
    existing = await db.attendance.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    }, {"_id": 0})
    
    if existing:
        await db.attendance.update_one(
            {"id": existing['id']},
            {"$set": {"clock_out": time_str}}
        )
        return {"message": "Attendance updated successfully"}
    else:
        raise HTTPException(status_code=404, detail="No clock-in record found. Please clock in first.")


@router.post("/checklist/submit")
async def super_admin_checklist_submit(data: SuperAdminChecklistSubmit, current_user: User = Depends(get_current_user)):
    """Super admin submit checklist for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit checklists")
    
    session = await db.sessions.find_one({"id": data.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    checklist_obj = VehicleChecklist(
        participant_id=data.participant_id,
        session_id=data.session_id,
        interval="trainer_inspection",
        checklist_items=data.checklist_items,
        verified_by="super_admin",
        verified_at=datetime.now(timezone.utc),
        verification_status="completed"
    )
    
    doc = checklist_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    doc['verified_at'] = doc['verified_at'].isoformat()
    
    await db.vehicle_checklists.update_one(
        {"participant_id": data.participant_id, "session_id": data.session_id},
        {"$set": doc},
        upsert=True
    )
    
    await db.participant_access.update_one(
        {"participant_id": data.participant_id, "session_id": data.session_id},
        {"$set": {"checklist_completed": True}},
        upsert=True
    )
    
    return {"message": "Checklist submitted successfully"}


@router.post("/feedback/submit")
async def super_admin_feedback_submit(data: SuperAdminFeedbackSubmit, current_user: User = Depends(get_current_user)):
    """Super admin submit feedback for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit feedback")
    
    session = await db.sessions.find_one({"id": data.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    program_id = session.get('program_id')
    if not program_id:
        raise HTTPException(status_code=400, detail="Session has no program_id")
    
    feedback_obj = CourseFeedback(
        participant_id=data.participant_id,
        session_id=data.session_id,
        program_id=program_id,
        responses=data.responses
    )
    
    doc = feedback_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    existing = await db.course_feedback.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    })
    
    if existing:
        await db.course_feedback.update_one(
            {"participant_id": data.participant_id, "session_id": data.session_id},
            {"$set": {"program_id": program_id, "responses": data.responses, "submitted_at": doc['submitted_at']}}
        )
    else:
        await db.course_feedback.insert_one(doc)
    
    await db.participant_access.update_one(
        {"participant_id": data.participant_id, "session_id": data.session_id},
        {"$set": {"feedback_completed": True}},
        upsert=True
    )
    
    return {"message": "Feedback submitted successfully"}


@router.post("/vehicle-details")
async def super_admin_vehicle_details(data: SuperAdminVehicleDetails, current_user: User = Depends(get_current_user)):
    """Super admin submit vehicle details for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit vehicle details")
    
    existing = await db.vehicle_details.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    })
    
    if existing:
        await db.vehicle_details.update_one(
            {"participant_id": data.participant_id, "session_id": data.session_id},
            {"$set": {
                "vehicle_model": data.vehicle_model,
                "registration_number": data.registration_number,
                "roadtax_expiry": data.roadtax_expiry
            }}
        )
        return {"message": "Vehicle details updated successfully"}
    else:
        vehicle_obj = VehicleDetails(
            participant_id=data.participant_id,
            session_id=data.session_id,
            vehicle_model=data.vehicle_model,
            registration_number=data.registration_number,
            roadtax_expiry=data.roadtax_expiry
        )
        
        doc = vehicle_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.vehicle_details.insert_one(doc)
        
        return {"message": "Vehicle details saved successfully"}
