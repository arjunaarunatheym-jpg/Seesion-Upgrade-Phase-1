"""
Participant Access routes - Control what participants can access
Endpoints: 4
- POST /participant-access/update
- GET /participant-access/{session_id}
- GET /participant-access/session/{session_id}
- POST /participant-access/session/{session_id}/toggle
"""
from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user, get_or_create_participant_access
from models import User, UpdateParticipantAccess

router = APIRouter(prefix="/participant-access", tags=["participant-access"])


@router.post("/update")
async def update_participant_access(access_data: UpdateParticipantAccess, current_user: User = Depends(get_current_user)):
    """Update access for a single participant"""
    # Allow admins and coordinators
    if current_user.role == "coordinator":
        session = await db.sessions.find_one({"id": access_data.session_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.get("coordinator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only manage access for sessions assigned to you")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins and coordinators can update access")
    
    await get_or_create_participant_access(access_data.participant_id, access_data.session_id)
    
    update_fields = {}
    if access_data.can_access_pre_test is not None:
        update_fields['can_access_pre_test'] = access_data.can_access_pre_test
    if access_data.can_access_post_test is not None:
        update_fields['can_access_post_test'] = access_data.can_access_post_test
    if access_data.can_access_checklist is not None:
        update_fields['can_access_checklist'] = access_data.can_access_checklist
    if access_data.can_access_feedback is not None:
        update_fields['can_access_feedback'] = access_data.can_access_feedback
    
    await db.participant_access.update_one(
        {"participant_id": access_data.participant_id, "session_id": access_data.session_id},
        {"$set": update_fields}
    )
    
    return {"message": "Access updated successfully"}


@router.get("/{session_id}")
async def get_my_access(session_id: str, current_user: User = Depends(get_current_user)):
    """Get current user's access for a session (participants)"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can check access")
    
    access = await get_or_create_participant_access(current_user.id, session_id)
    return access


@router.get("/session/{session_id}")
async def get_session_access(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all participant access records for a session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check permissions
    can_access = False
    if current_user.role in ["coordinator", "admin", "assistant_admin"]:
        can_access = True
    elif current_user.role == "trainer":
        trainer_ids = [t.get("trainer_id") for t in session.get("trainer_assignments", [])]
        assistant_coord_ids = session.get("assistant_coordinator_ids", [])
        if current_user.id in trainer_ids or current_user.id in assistant_coord_ids:
            can_access = True
    
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    access_records = await db.participant_access.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    return access_records


@router.post("/session/{session_id}/toggle")
async def toggle_session_access(session_id: str, access_data: dict, current_user: User = Depends(get_current_user)):
    """Toggle access for all participants in a session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check permissions
    can_access = False
    if current_user.role in ["coordinator", "admin", "assistant_admin"]:
        can_access = True
    elif current_user.role == "trainer":
        trainer_ids = [t.get("trainer_id") for t in session.get("trainer_assignments", [])]
        assistant_coord_ids = session.get("assistant_coordinator_ids", [])
        if current_user.id in trainer_ids or current_user.id in assistant_coord_ids:
            can_access = True
    
    if not can_access:
        raise HTTPException(status_code=403, detail="You don't have permission to control access for this session")
    
    access_type = access_data.get("access_type")
    enabled = access_data.get("enabled", False)
    
    field_mapping = {
        "pre_test": "can_access_pre_test",
        "post_test": "can_access_post_test",
        "feedback": "can_access_feedback",
        "checklist": "can_access_checklist",
        "clock_out": "can_clock_out"
    }
    
    if access_type not in field_mapping:
        raise HTTPException(status_code=400, detail="Invalid access type")
    
    field_name = field_mapping[access_type]
    participant_ids = session.get("participant_ids", [])
    
    for participant_id in participant_ids:
        await get_or_create_participant_access(participant_id, session_id)
        await db.participant_access.update_one(
            {"participant_id": participant_id, "session_id": session_id},
            {"$set": {field_name: enabled}}
        )
    
    status_text = "enabled" if enabled else "disabled"
    return {"message": f"{access_type} access {status_text} for {len(participant_ids)} participants"}
