"""
Session management routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from datetime import datetime
import pandas as pd
import io

from models import Session, SessionCreate, ParticipantAccess, UpdateParticipantAccess
from services.auth_service import get_current_user
from services.participant_service import find_or_create_user, get_or_create_participant_access
from utils import db, get_malaysia_time

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=List[Session])
async def get_sessions(
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get sessions based on user role and filters"""
    current_date = get_malaysia_time().date()
    
    # Role-based filtering
    if current_user.role in ["trainer", "assistant_admin"]:
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},
                {"end_date": {"$gte": current_date.isoformat()}},
                {"status": "active"}
            ]
        }
    else:
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},
                {
                    "$or": [
                        {"completion_status": {"$exists": False}},
                        {"completion_status": "ongoing"},
                        {"completion_status": {"$nin": ["completed", "archived"]}}
                    ]
                }
            ]
        }
    
    # Apply filters
    if company_id:
        query["$and"].append({"company_id": company_id})
    if program_id:
        query["$and"].append({"program_id": program_id})
    if start_date:
        query["$and"].append({"start_date": {"$gte": start_date}})
    if end_date:
        query["$and"].append({"end_date": {"$lte": end_date}})
    
    # Role-specific filters
    if current_user.role not in ["admin", "trainer"]:
        query["$and"].append({"status": "active"})
    
    if current_user.role == "participant":
        query["$and"].append({"participant_ids": current_user.id})
        sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    elif current_user.role == "supervisor":
        query["$and"].append({"supervisor_ids": current_user.id})
        sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    elif current_user.role == "coordinator":
        query["$and"].append({"coordinator_id": current_user.id})
        sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    else:
        sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with company and program data
    for session in sessions:
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
        
        # Only lookup company_name if not already stored on session (allows overrides)
        if not session.get("company_name") and session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
        elif not session.get("company_name"):
            session["company_name"] = "Unknown"
        
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name", "Unknown") if program else "Unknown"
        else:
            session["program_name"] = "Unknown"
    
    # Apply text search filter
    if search:
        search_lower = search.lower()
        sessions = [
            s for s in sessions
            if search_lower in s.get("name", "").lower()
            or search_lower in s.get("company_name", "").lower()
            or search_lower in s.get("program_name", "").lower()
            or search_lower in s.get("location", "").lower()
        ]
    
    return sessions


@router.post("")
async def create_session(session_data: SessionCreate, current_user = Depends(get_current_user)):
    """Create a new training session"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can create sessions")
    
    from models import Session
    from uuid import uuid4
    
    # Create or link participants
    participant_ids = []
    for p_data in session_data.participants:
        result = await find_or_create_user(
            p_data.model_dump(),
            "participant",
            session_data.company_id
        )
        participant_ids.append(result["user_id"])
    
    # Add existing participants
    participant_ids.extend(session_data.participant_ids)
    
    # Create or link supervisors
    supervisor_ids = []
    for s_data in session_data.supervisors:
        result = await find_or_create_user(
            s_data.model_dump(),
            "supervisor",
            session_data.company_id
        )
        supervisor_ids.append(result["user_id"])
    
    supervisor_ids.extend(session_data.supervisor_ids)
    
    session_obj = Session(
        name=session_data.name,
        program_id=session_data.program_id,
        company_id=session_data.company_id,
        location=session_data.location,
        start_date=session_data.start_date,
        end_date=session_data.end_date,
        supervisor_ids=supervisor_ids,
        participant_ids=participant_ids,
        trainer_assignments=session_data.trainer_assignments,
        coordinator_id=session_data.coordinator_id
    )
    
    doc = session_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.sessions.insert_one(doc)
    
    # Create participant access records
    for participant_id in participant_ids:
        await get_or_create_participant_access(participant_id, session_obj.id)
    
    return {"message": "Session created", "session_id": session_obj.id}


@router.get("/calendar")
async def get_calendar(current_user = Depends(get_current_user)):
    """Get sessions for calendar view (shows all sessions from past year to next year)"""
    if current_user.role not in ["admin", "coordinator", "assistant_admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get all sessions from 1 year ago to 1 year in future
    current_date = get_malaysia_time().date()
    one_year_ago = current_date.replace(year=current_date.year - 1)
    one_year_from_now = current_date.replace(year=current_date.year + 1)
    
    query = {
        "start_date": {
            "$gte": one_year_ago.isoformat(),
            "$lte": one_year_from_now.isoformat()
        }
    }
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with company and program data for calendar display
    for session in sessions:
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
        
        # Only lookup company_name if not already stored on session (allows overrides)
        if not session.get("company_name") and session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
        elif not session.get("company_name"):
            session["company_name"] = "Unknown"
        
        # Get program info
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name", "Unknown") if program else "Unknown"
        else:
            session["program_name"] = "Unknown"
        
        # Add participant count
        session["participant_count"] = len(session.get("participant_ids", []))
    
    return sessions


@router.get("/past-training")
async def get_past_training(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    """Get past training sessions"""
    query = {"completion_status": "completed"}
    
    if month and year:
        start_of_month = f"{year}-{month:02d}-01"
        if month == 12:
            end_of_month = f"{year+1}-01-01"
        else:
            end_of_month = f"{year}-{month+1:02d}-01"
        
        query["$and"] = [
            {"start_date": {"$gte": start_of_month}},
            {"start_date": {"$lt": end_of_month}}
        ]
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich - only lookup company_name if not already stored on session
    for session in sessions:
        if not session.get("company_name") and session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name") if company else "Unknown"
        elif not session.get("company_name"):
            session["company_name"] = "Unknown"
        
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name") if program else "Unknown"
        else:
            session["program_name"] = "Unknown"
    
    return sessions


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str, current_user = Depends(get_current_user)):
    """Get a specific session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Only enrich company_name if not already stored on session (allows overrides)
    if not session.get("company_name") and session.get("company_id"):
        company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
        session["company_name"] = company.get("name") if company else "Unknown"
    
    if session.get("program_id"):
        program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
        session["program_name"] = program.get("name") if program else "Unknown"
    
    return Session(**session)


@router.post("/{session_id}/mark-completed")
async def mark_session_completed(session_id: str, current_user = Depends(get_current_user)):
    """Mark session as completed"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators or admins can mark sessions as completed")
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "completion_status": "completed",
            "completed_by_coordinator": True,
            "completed_date": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Session marked as completed"}





@router.post("/{session_id}/participants")
async def add_participants_to_session(
    session_id: str,
    participant_ids: dict,
    current_user = Depends(get_current_user)
):
    """Add existing participants to a session by IC number or user ID"""
    if current_user.role not in ["admin", "assistant_admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins, assistant admins, and coordinators can add participants")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # participant_ids is a list of IC numbers or user IDs
    ids_to_add = participant_ids.get("participant_ids", [])
    if not ids_to_add:
        raise HTTPException(status_code=400, detail="No participant IDs provided")
    
    # Find users by IC number or user ID
    added_ids = []
    for identifier in ids_to_add:
        # Try to find by IC number first, then by user ID
        user = await db.users.find_one(
            {"$or": [{"id_number": identifier}, {"id": identifier}]},
            {"_id": 0, "id": 1}
        )
        if user:
            added_ids.append(user["id"])
        else:
            raise HTTPException(status_code=404, detail=f"User not found: {identifier}")
    
    # Get current participant list
    current_participants = session.get("participant_ids", [])
    
    # Add new participants (avoid duplicates)
    newly_added = []
    for user_id in added_ids:
        if user_id not in current_participants:
            current_participants.append(user_id)
            newly_added.append(user_id)
    
    # Update session
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"participant_ids": current_participants}}
    )
    
    # Create participant_access records for newly added participants
    for user_id in newly_added:
        await get_or_create_participant_access(user_id, session_id)
    
    return {
        "message": f"Successfully added {len(newly_added)} participant(s)",
        "added_count": len(newly_added)
    }

@router.post("/{session_id}/participants/bulk-upload")
async def bulk_upload_participants(
    session_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Bulk upload participants from Excel file"""
    if current_user.role not in ["admin", "assistant_admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Read Excel file
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
    
    # Process data
    participants_added = []
    for _, row in df.iterrows():
        # Flexible column names
        name_col = next((col for col in df.columns if 'name' in col.lower()), None)
        ic_col = next((col for col in df.columns if 'ic' in col.lower() or 'number' in col.lower()), None)
        
        if not name_col or not ic_col:
            raise HTTPException(status_code=400, detail="Excel must contain 'Name' and 'IC Number' columns")
        
        full_name = str(row[name_col]).strip().upper()
        ic_number = str(row[ic_col]).strip().replace('-', '').upper()
        
        # Create or find user
        result = await find_or_create_user(
            {"full_name": full_name, "id_number": ic_number},
            "participant",
            session["company_id"]
        )
        
        user_id = result["user_id"]
        
        # Add to session
        if user_id not in session.get("participant_ids", []):
            await db.sessions.update_one(
                {"id": session_id},
                {"$addToSet": {"participant_ids": user_id}}
            )
            participants_added.append(user_id)
        
        # Create access record
        await get_or_create_participant_access(user_id, session_id)
    
    return {
        "message": "Participants uploaded successfully",
        "count": len(participants_added),
        "total_uploaded": len(participants_added)
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str, current_user = Depends(get_current_user)):
    """Delete a session"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete sessions")
    
    result = await db.sessions.delete_one({"id": session_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Also delete related participant_access records
    await db.participant_access.delete_many({"session_id": session_id})
    
    return {"message": "Session deleted successfully"}


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    updates: dict,
    current_user = Depends(get_current_user)
):
    """Update a session"""
    if current_user.role not in ["admin", "assistant_admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins, assistant admins, and coordinators can update sessions")
    
    # Remove protected fields
    updates.pop("id", None)
    
    result = await db.sessions.update_one({"id": session_id}, {"$set": updates})
    
    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session updated successfully"}


@router.post("/{session_id}/release-pre-test")
async def release_pre_test(session_id: str, current_user = Depends(get_current_user)):
    """Release pre-test for all participants in session"""
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update all participant_access records for this session
    result = await db.participant_access.update_many(
        {"session_id": session_id},
        {"$set": {"pre_test_released": True}}
    )
    
    return {"message": f"Pre-test released for {result.modified_count} participants"}


@router.post("/{session_id}/release-post-test")
async def release_post_test(session_id: str, current_user = Depends(get_current_user)):
    """Release post-test for all participants in session"""
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = await db.participant_access.update_many(
        {"session_id": session_id},
        {"$set": {"post_test_released": True}}
    )
    
    return {"message": f"Post-test released for {result.modified_count} participants"}


@router.post("/{session_id}/release-feedback")
async def release_feedback(session_id: str, current_user = Depends(get_current_user)):
    """Release feedback form for all participants in session"""
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = await db.participant_access.update_many(
        {"session_id": session_id},
        {"$set": {"feedback_released": True}}
    )
    
    return {"message": f"Feedback released for {result.modified_count} participants"}


@router.post("/{session_id}/release-certificate")
async def release_certificate(session_id: str, current_user = Depends(get_current_user)):
    """Release certificates for all participants in session"""
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    result = await db.participant_access.update_many(
        {"session_id": session_id},
        {"$set": {"certificate_released": True}}
    )
    
    return {"message": f"Certificates released for {result.modified_count} participants"}


@router.get("/{session_id}/participants", response_model=List)
async def get_session_participants(session_id: str, current_user = Depends(get_current_user)):
    """Get all participants in a session with their details"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participants = []
    for participant_id in session.get("participant_ids", []):
        user = await db.users.find_one({"id": participant_id}, {"_id": 0, "password": 0})
        if user:
            # Get participant access info
            access = await db.participant_access.find_one(
                {"participant_id": participant_id, "session_id": session_id},
                {"_id": 0}
            )
            user["access_info"] = access if access else {}
            
            # Get test results
            pre_test = await db.test_results.find_one(
                {"participant_id": participant_id, "session_id": session_id},
                {"_id": 0},
                sort=[("submitted_at", -1)]
            )
            user["pre_test_score"] = pre_test.get("score") if pre_test else None
            
            participants.append(user)
    
    return participants


@router.get("/{session_id}/results-summary")
async def get_session_results_summary(session_id: str, current_user = Depends(get_current_user)):
    """Get comprehensive results summary for a session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all test results for this session
    test_results = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    
    # Get all feedback
    feedback = await db.course_feedback.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    
    # Get all checklists
    checklists = await db.vehicle_checklists.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    
    # Get all attendance
    attendance = await db.attendance.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    
    # Get participant details
    participants = []
    for p_id in session.get("participant_ids", []):
        user = await db.users.find_one({"id": p_id}, {"_id": 0, "password": 0})
        if user:
            # Get participant access
            access = await db.participant_access.find_one(
                {"participant_id": p_id, "session_id": session_id},
                {"_id": 0}
            )
            
            user["access"] = access if access else {}
            user["test_results"] = [r for r in test_results if r.get("participant_id") == p_id]
            user["attendance_count"] = len([a for a in attendance if a.get("participant_id") == p_id])
            user["checklist_completed"] = any(c.get("participant_id") == p_id for c in checklists)
            user["feedback_submitted"] = any(f.get("participant_id") == p_id for f in feedback)
            
            participants.append(user)
    
    session["participants"] = participants
    session["test_results"] = test_results
    session["feedback"] = feedback
    session["checklists"] = checklists
    session["attendance"] = attendance
    
    return session


@router.get("/{session_id}/status")
async def get_session_status(session_id: str, current_user = Depends(get_current_user)):
    """Get session status with counts"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_count = len(session.get("participant_ids", []))
    
    # Count test submissions
    pre_tests = await db.test_results.count_documents({"session_id": session_id})
    
    # Count feedback submissions
    feedback_count = await db.course_feedback.count_documents({"session_id": session_id})
    
    # Count checklists
    checklist_count = await db.vehicle_checklists.count_documents({"session_id": session_id})
    
    return {
        "session_id": session_id,
        "participant_count": participant_count,
        "pre_test_count": pre_tests,
        "feedback_count": feedback_count,
        "checklist_count": checklist_count,
        "completion_status": session.get("completion_status", "ongoing")
    }


@router.put("/{session_id}/toggle-status")
async def toggle_session_status(session_id: str, current_user = Depends(get_current_user)):
    """Toggle session active/inactive status"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can toggle session status")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    new_status = "inactive" if session.get("status") == "active" else "active"
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"status": new_status}}
    )
    
    return {"message": f"Session status changed to {new_status}", "status": new_status}


@router.get("/{session_id}/completion-checklist")
async def get_completion_checklist(session_id: str, current_user = Depends(get_current_user)):
    """Get completion checklist for coordinator to verify before marking complete"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_count = len(session.get("participant_ids", []))
    
    # Check various completion criteria
    pre_tests = await db.test_results.count_documents({"session_id": session_id})
    feedback = await db.course_feedback.count_documents({"session_id": session_id})
    checklists = await db.vehicle_checklists.count_documents({"session_id": session_id})
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    return {
        "participant_count": participant_count,
        "pre_test_submissions": pre_tests,
        "feedback_submissions": feedback,
        "checklist_submissions": checklists,
        "training_report_generated": report is not None,
        "training_report_status": report.get("status") if report else None,
        "all_requirements_met": (
            pre_tests >= participant_count and
            feedback >= participant_count and
            report is not None and
            report.get("status") == "submitted"
        )
    }



@router.get("/{session_id}/assigned-participants")
async def get_assigned_participants(session_id: str, current_user = Depends(get_current_user)):
    """Get participants assigned to current trainer (auto-distributed equally)"""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all trainers in session
    trainer_assignments = session.get('trainer_assignments', [])
    trainers = [t['trainer_id'] for t in trainer_assignments]
    
    if not trainers:
        return []
    
    # Auto-assign participants to trainers
    participant_ids = session.get('participant_ids', [])
    total_participants = len(participant_ids)
    total_trainers = len(trainers)
    
    if total_trainers == 0 or total_participants == 0:
        return []
    
    # Find current trainer and their role
    current_trainer_assignment = None
    current_trainer_index = -1
    for idx, assignment in enumerate(trainer_assignments):
        if assignment['trainer_id'] == current_user.id:
            current_trainer_assignment = assignment
            current_trainer_index = idx
            break
    
    if current_trainer_assignment is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this session")
    
    is_chief = current_trainer_assignment.get('role') == 'chief'
    
    # Count how many chiefs and regulars
    chief_assignments = [t for t in trainer_assignments if t.get('role') == 'chief']
    regular_assignments = [t for t in trainer_assignments if t.get('role') != 'chief']
    chief_count = len(chief_assignments)
    regular_count = len(regular_assignments)
    
    # Check if equal distribution is possible
    if total_participants % total_trainers == 0:
        # EQUAL DISTRIBUTION: Divide equally among all trainers
        participants_per_trainer = total_participants // total_trainers
        start_index = current_trainer_index * participants_per_trainer
        assigned_count = participants_per_trainer
    else:
        # UNEQUAL DISTRIBUTION: Chief gets fewer participants
        base_count = total_participants // total_trainers
        remainder = total_participants % total_trainers
        
        # Chiefs get base_count each (floor division)
        # Regular trainers get base_count + share of remainder
        participants_for_chiefs = chief_count * base_count
        participants_for_regulars = total_participants - participants_for_chiefs
        
        if is_chief:
            # Find which chief trainer this is
            chief_index = 0
            for t in chief_assignments:
                if t['trainer_id'] == current_user.id:
                    break
                chief_index += 1
            
            start_index = chief_index * base_count
            assigned_count = base_count
        else:
            # Regular trainers share the remaining participants
            if regular_count > 0:
                # Find which regular trainer this is (0-indexed among regulars)
                regular_index = 0
                for t in regular_assignments:
                    if t['trainer_id'] == current_user.id:
                        break
                    regular_index += 1
                
                # Distribute participants_for_regulars among regular trainers
                regulars_base = participants_for_regulars // regular_count
                regulars_remainder = participants_for_regulars % regular_count
                
                start_index = participants_for_chiefs + (regular_index * regulars_base) + min(regular_index, regulars_remainder)
                assigned_count = regulars_base + (1 if regular_index < regulars_remainder else 0)
            else:
                # No regular trainers (shouldn't happen but handle it)
                start_index = current_trainer_index * base_count
                assigned_count = base_count
    
    end_index = start_index + assigned_count
    assigned_participant_ids = participant_ids[start_index:end_index]
    
    # Get participant details
    participants = await db.users.find(
        {"id": {"$in": assigned_participant_ids}},
        {"_id": 0, "password": 0, "hashed_password": 0}
    ).to_list(100)
    
    return participants

@router.get("/{session_id}/tests/available")
async def get_available_tests(session_id: str, current_user = Depends(get_current_user)):
    """Get available tests for participant in a session"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can access this")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get participant access
    access = await get_or_create_participant_access(current_user.id, session_id)
    
    # Get tests for the session's program
    tests = await db.tests.find({"program_id": session['program_id']}, {"_id": 0}).to_list(10)
    
    available_tests = []
    for test in tests:
        if isinstance(test.get('created_at'), str):
            test['created_at'] = datetime.fromisoformat(test['created_at'])
        
        test_type = test.get('test_type', 'general')
        can_access = False
        is_completed = False
        
        if test_type == "pre":
            can_access = getattr(access, 'can_access_pre_test', False)
            is_completed = getattr(access, 'pre_test_completed', False)
        elif test_type == "post":
            can_access = getattr(access, 'can_access_post_test', False)
            is_completed = getattr(access, 'post_test_completed', False)
        
        if can_access and not is_completed:
            # Don't send correct answers to participant
            test_copy = test.copy()
            questions = test.get('questions', [])
            
            # Shuffle post-test questions and track indices
            if test_type == "post":
                import random
                import time
                # Seed random with timestamp + participant ID for unique shuffle per participant
                random.seed(time.time() + hash(current_user.id))
                # Create list of (index, question) tuples
                indexed_questions = list(enumerate(questions))
                random.shuffle(indexed_questions)
                
                # Extract shuffled questions and their original indices
                question_indices = [idx for idx, q in indexed_questions]
                questions = [q for idx, q in indexed_questions]
                
                test_copy['question_indices'] = question_indices
            
            test_copy['questions'] = [
                {
                    'question': q['question'],
                    'options': q['options']
                }
                for q in questions
            ]
            available_tests.append(test_copy)
    
    return available_tests




@router.post("/{session_id}/participants/{participant_id}/attendance")
async def mark_participant_attendance(
    session_id: str,
    participant_id: str,
    status: str,  # "present" or "absent" - passed as query parameter
    current_user = Depends(get_current_user)
):
    """Mark participant as present or absent for a session"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can mark attendance")
    
    if status not in ["present", "absent"]:
        raise HTTPException(status_code=400, detail="Status must be 'present' or 'absent'")
    
    # Check if session exists
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if participant is in this session
    if participant_id not in session.get("participant_ids", []):
        raise HTTPException(status_code=400, detail="Participant not enrolled in this session")
    
    # Update or create attendance record
    await db.participant_attendance.update_one(
        {
            "session_id": session_id,
            "participant_id": participant_id
        },
        {
            "$set": {
                "status": status,
                "marked_by": current_user.id,
                "marked_at": get_malaysia_time().isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "message": f"Participant marked as {status}",
        "status": status
    }


@router.get("/{session_id}/participants/attendance")
async def get_session_attendance_status(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get attendance status for all participants in a session"""
    if current_user.role not in ["coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get all attendance records for this session
    attendance_records = await db.participant_attendance.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Return as dictionary with participant_id as key
    attendance_dict = {record["participant_id"]: record["status"] for record in attendance_records}
    
    return attendance_dict

