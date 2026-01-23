"""
Supervisor routes - PIC Supervisor functionality
Endpoints: 2
"""
from fastapi import APIRouter, HTTPException, Depends

from core import db, get_current_user
from models import User

router = APIRouter(prefix="/supervisor", tags=["supervisor"])


@router.get("/sessions")
async def get_supervisor_sessions(current_user: User = Depends(get_current_user)):
    """Get sessions for supervisor"""
    if current_user.role != "pic_supervisor":
        raise HTTPException(status_code=403, detail="Only supervisors can access this")
    
    sessions = await db.sessions.find({
        "supervisor_ids": current_user.id
    }, {"_id": 0}).to_list(100)
    
    return sessions


@router.get("/attendance/{session_id}")
async def get_supervisor_session_attendance(session_id: str, current_user: User = Depends(get_current_user)):
    """Get attendance for session (Supervisor)"""
    if current_user.role != "pic_supervisor":
        raise HTTPException(status_code=403, detail="Only supervisors can access this")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or current_user.id not in session.get('supervisor_ids', []):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    attendance = await db.attendance.find({
        "session_id": session_id
    }, {"_id": 0}).to_list(100)
    
    for record in attendance:
        participant = await db.users.find_one({"id": record['participant_id']}, {"_id": 0, "password": 0})
        if participant:
            record['participant_name'] = participant.get('full_name', 'Unknown')
            record['participant_email'] = participant.get('email', '')
        else:
            record['participant_name'] = f"Participant {record['participant_id']}"
            record['participant_email'] = ''
    
    return attendance
