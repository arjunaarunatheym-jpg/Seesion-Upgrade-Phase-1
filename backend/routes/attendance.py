"""
Attendance routes - Clock in/out management
Endpoints: 4
- POST /attendance/clock-in
- POST /attendance/clock-out
- GET /attendance/session/{session_id}
- GET /attendance/{session_id}/{participant_id}
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import logging

from core import db, get_current_user, get_malaysia_time, get_malaysia_date, get_malaysia_time_str
from models import User, Attendance, AttendanceClockIn, AttendanceClockOut

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/clock-in")
async def clock_in(attendance_data: AttendanceClockIn, current_user: User = Depends(get_current_user)):
    """Clock in for a training session (participants only)"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can clock in")
    
    today = get_malaysia_date().isoformat()
    now = get_malaysia_time_str()
    
    # Check if any attendance record exists for this participant/session
    existing_any = await db.attendance.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id
    }, {"_id": 0})
    
    if existing_any and existing_any.get('clock_in'):
        raise HTTPException(status_code=400, detail="Already clocked in for this session")
    
    # Check for today's record
    existing_today = await db.attendance.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id,
        "date": today
    }, {"_id": 0})
    
    if existing_today:
        await db.attendance.update_one(
            {"id": existing_today['id']},
            {"$set": {"clock_in": now}}
        )
        return {"message": "Clocked in successfully", "time": now}
    
    if existing_any:
        await db.attendance.update_one(
            {"id": existing_any['id']},
            {"$set": {"clock_in": now, "date": today}}
        )
        return {"message": "Clocked in successfully", "time": now}
    
    # Create new record
    attendance_obj = Attendance(
        participant_id=current_user.id,
        session_id=attendance_data.session_id,
        date=today,
        clock_in=now
    )
    
    doc = attendance_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.attendance.insert_one(doc)
    
    return {"message": "Clocked in successfully", "time": now}


@router.post("/clock-out")
async def clock_out(attendance_data: AttendanceClockOut, current_user: User = Depends(get_current_user)):
    """Clock out from a training session (participants only)"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can clock out")
    
    # Check if clock out has been released
    access = await db.participant_access.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id
    }, {"_id": 0})
    
    if not access or not access.get("can_clock_out"):
        raise HTTPException(status_code=403, detail="Clock out not yet released by coordinator")
    
    now = get_malaysia_time_str()
    
    existing = await db.attendance.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id
    }, {"_id": 0})
    
    if not existing or not existing.get('clock_in'):
        raise HTTPException(status_code=400, detail="Please clock in first")
    
    if existing.get('clock_out'):
        raise HTTPException(status_code=400, detail="Already clocked out for this session")
    
    await db.attendance.update_one(
        {"id": existing['id']},
        {"$set": {"clock_out": now}}
    )
    
    return {"message": "Clocked out successfully", "time": now}


@router.get("/session/{session_id}")
async def get_session_attendance(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all attendance records for a session"""
    if current_user.role not in ["pic_supervisor", "coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logging.info(f"Querying attendance for session_id: {session_id}")
    attendance_records = await db.attendance.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    logging.info(f"Found {len(attendance_records)} attendance records")
    
    participant_map = {}
    if attendance_records:
        participant_ids = list(set([r['participant_id'] for r in attendance_records]))
        logging.info(f"Looking up {len(participant_ids)} unique participants")
        
        if participant_ids:
            participants = await db.users.find({"id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
            participant_map = {p['id']: p for p in participants}
            logging.info(f"Found {len(participants)} participant records")
    
    for record in attendance_records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        participant = participant_map.get(record['participant_id'])
        if participant:
            record['participant_name'] = participant.get('full_name', 'Unknown')
            record['participant_email'] = participant.get('email', '')
        else:
            record['participant_name'] = f"Participant {record['participant_id']}"
            record['participant_email'] = ''
            logging.warning(f"Could not find participant info for ID: {record['participant_id']}")
    
    return attendance_records


@router.get("/{session_id}/{participant_id}")
async def get_attendance(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    """Get attendance records for a specific participant in a session"""
    attendance_records = await db.attendance.find({
        "participant_id": participant_id,
        "session_id": session_id
    }, {"_id": 0}).to_list(100)
    
    for record in attendance_records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
    
    return attendance_records
