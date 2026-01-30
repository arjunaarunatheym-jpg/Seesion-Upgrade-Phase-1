"""
Sessions routes - Training session management
This is a PARTIAL extraction - complex endpoints remain in server.py for now.
Endpoints extracted: Core session CRUD and participant management
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from core import db, get_current_user, get_malaysia_time, find_or_create_user, get_or_create_participant_access
from models import User, Session, SessionCreate

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/calendar")
async def get_calendar_sessions(current_user: User = Depends(get_current_user)):
    """Get all sessions for calendar view"""
    query = {"is_archived": {"$ne": True}}
    
    if current_user.role == "coordinator":
        query["coordinator_id"] = current_user.id
    elif current_user.role == "trainer":
        query["$or"] = [
            {"trainer_assignments.trainer_id": current_user.id},
            {"assistant_coordinator_ids": current_user.id}
        ]
    elif current_user.role == "participant":
        query["participant_ids"] = current_user.id
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with names
    for session in sessions:
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
        
        if session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
        
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name", "Unknown") if program else "Unknown"
    
    return sessions


@router.get("/past-training")
async def get_past_training(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get completed/archived training sessions with optional month/year filter"""
    current_date = get_malaysia_time().date()
    current_date_str = current_date.isoformat()
    
    if current_user.role == "trainer":
        # For trainers: Show sessions where:
        # 1. Trainer is assigned, AND
        # 2. Either completed by coordinator OR end_date has passed
        query = {
            "$and": [
                # Trainer must be assigned
                {
                    "$or": [
                        {"trainer_assignments.trainer_id": current_user.id},
                        {"assistant_coordinator_ids": current_user.id}
                    ]
                },
                # Either completed OR end_date has passed
                {
                    "$or": [
                        {"completed_by_coordinator": True},
                        {"completion_status": "completed"},
                        {"completion_status": "archived"},
                        {"is_archived": True},
                        {"end_date": {"$lt": current_date_str}}  # Past sessions
                    ]
                }
            ]
        }
    elif current_user.role == "coordinator":
        query = {
            "$and": [
                {"coordinator_id": current_user.id},
                {
                    "$or": [
                        {"completion_status": "completed"},
                        {"completion_status": "archived"},
                        {"is_archived": True}
                    ]
                }
            ]
        }
    elif current_user.role == "participant":
        query = {
            "$and": [
                {"participant_ids": current_user.id},
                {
                    "$or": [
                        {"completion_status": "completed"},
                        {"completion_status": "archived"},
                        {"is_archived": True}
                    ]
                }
            ]
        }
    else:
        # Admin/assistant_admin see all completed sessions
        query = {
            "$or": [
                {"completion_status": "completed"},
                {"completion_status": "archived"},
                {"is_archived": True}
            ]
        }
    
    # Add month/year filter if provided
    if month and year:
        start_of_month = f"{year}-{month:02d}-01"
        if month == 12:
            end_of_month = f"{year+1}-01-01"
        else:
            end_of_month = f"{year}-{month+1:02d}-01"
        
        date_filter = {
            "end_date": {
                "$gte": start_of_month,
                "$lt": end_of_month
            }
        }
        
        if "$and" in query:
            query["$and"].append(date_filter)
        else:
            query = {"$and": [query, date_filter]}
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    for session in sessions:
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
        
        if session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
        
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name", "Unknown") if program else "Unknown"
    
    return sessions


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific session by ID"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if isinstance(session.get('created_at'), str):
        session['created_at'] = datetime.fromisoformat(session['created_at'])
    
    return Session(**session)


@router.get("/{session_id}/participants")
async def get_session_participants(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all participants for a session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    participants = []
    
    for pid in participant_ids:
        user = await db.users.find_one({"id": pid}, {"_id": 0, "password": 0})
        if user:
            if isinstance(user.get('created_at'), str):
                user['created_at'] = datetime.fromisoformat(user['created_at'])
            participants.append(user)
    
    return participants


@router.get("/{session_id}/participants/enriched")
async def get_enriched_participants(session_id: str, current_user: User = Depends(get_current_user)):
    """Get participants with all their related data (attendance, test results, etc.) - OPTIMIZED"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    if not participant_ids:
        return []
    
    # Bulk fetch all data
    users = await db.users.find({"id": {"$in": participant_ids}}, {"_id": 0, "password": 0}).to_list(1000)
    attendances = await db.attendance.find({"session_id": session_id, "participant_id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
    accesses = await db.participant_access.find({"session_id": session_id, "participant_id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
    test_results = await db.test_results.find({"session_id": session_id, "participant_id": {"$in": participant_ids}}, {"_id": 0}).to_list(2000)
    checklists = await db.checklist_submissions.find({"session_id": session_id, "participant_id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
    feedbacks = await db.course_feedback.find({"session_id": session_id, "participant_id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
    
    # Create lookup maps
    user_map = {u['id']: u for u in users}
    attendance_map = {a['participant_id']: a for a in attendances}
    access_map = {a['participant_id']: a for a in accesses}
    checklist_map = {c['participant_id']: c for c in checklists}
    feedback_map = {f['participant_id']: f for f in feedbacks}
    
    # Group test results by participant
    test_results_map = {}
    for tr in test_results:
        pid = tr['participant_id']
        if pid not in test_results_map:
            test_results_map[pid] = []
        test_results_map[pid].append(tr)
    
    # Build enriched data
    enriched = []
    for pid in participant_ids:
        user = user_map.get(pid, {})
        if not user:
            continue
        
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
        
        enriched.append({
            "user": user,
            "attendance": attendance_map.get(pid),
            "access": access_map.get(pid),
            "test_results": test_results_map.get(pid, []),
            "checklist": checklist_map.get(pid),
            "feedback": feedback_map.get(pid)
        })
    
    return enriched


@router.get("/{session_id}/status")
async def get_session_status(session_id: str, current_user: User = Depends(get_current_user)):
    """Get session completion status"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    total_participants = len(participant_ids)
    
    # Count completions
    attendance_complete = await db.attendance.count_documents({
        "session_id": session_id,
        "clock_in": {"$exists": True, "$ne": None}
    })
    
    pre_test_complete = await db.test_results.count_documents({
        "session_id": session_id,
        "test_type": {"$in": ["pre", "pre_test"]}
    })
    
    post_test_complete = await db.test_results.count_documents({
        "session_id": session_id,
        "test_type": {"$in": ["post", "post_test"]}
    })
    
    checklist_complete = await db.checklist_submissions.count_documents({
        "session_id": session_id
    })
    
    feedback_complete = await db.course_feedback.count_documents({
        "session_id": session_id
    })
    
    return {
        "session_id": session_id,
        "total_participants": total_participants,
        "attendance_complete": attendance_complete,
        "pre_test_complete": pre_test_complete,
        "post_test_complete": post_test_complete,
        "checklist_complete": checklist_complete,
        "feedback_complete": feedback_complete,
        "completion_status": session.get("completion_status", "ongoing"),
        "completed_by_coordinator": session.get("completed_by_coordinator", False)
    }


@router.get("/{session_id}/completion-checklist")
async def get_completion_checklist(session_id: str, current_user: User = Depends(get_current_user)):
    """Get completion checklist for session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    
    checklist = {
        "all_attendance_recorded": False,
        "all_pre_tests_completed": False,
        "all_post_tests_completed": False,
        "all_checklists_submitted": False,
        "all_feedback_submitted": False,
        "coordinator_feedback_submitted": False,
        "chief_trainer_feedback_submitted": False
    }
    
    if participant_ids:
        total = len(participant_ids)
        
        attendance_count = await db.attendance.count_documents({
            "session_id": session_id,
            "clock_in": {"$exists": True, "$ne": None}
        })
        checklist["all_attendance_recorded"] = attendance_count >= total
        
        pre_test_count = await db.test_results.count_documents({
            "session_id": session_id,
            "test_type": {"$in": ["pre", "pre_test"]}
        })
        checklist["all_pre_tests_completed"] = pre_test_count >= total
        
        post_test_count = await db.test_results.count_documents({
            "session_id": session_id,
            "test_type": {"$in": ["post", "post_test"]}
        })
        checklist["all_post_tests_completed"] = post_test_count >= total
        
        checklist_count = await db.checklist_submissions.count_documents({
            "session_id": session_id
        })
        checklist["all_checklists_submitted"] = checklist_count >= total
        
        feedback_count = await db.course_feedback.count_documents({
            "session_id": session_id
        })
        checklist["all_feedback_submitted"] = feedback_count >= total
    
    coord_feedback = await db.coordinator_feedback.find_one({"session_id": session_id})
    checklist["coordinator_feedback_submitted"] = coord_feedback is not None
    
    trainer_feedback = await db.chief_trainer_feedback.find_one({"session_id": session_id})
    checklist["chief_trainer_feedback_submitted"] = trainer_feedback is not None
    
    return checklist


@router.get("/{session_id}/results-summary")
async def get_results_summary(session_id: str, current_user: User = Depends(get_current_user)):
    """Get summary of test results for a session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    
    # Get all test results
    results = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(2000)
    
    # Calculate stats
    pre_scores = [r['score'] for r in results if r.get('test_type') in ['pre', 'pre_test']]
    post_scores = [r['score'] for r in results if r.get('test_type') in ['post', 'post_test']]
    
    return {
        "total_participants": len(participant_ids),
        "pre_test": {
            "completed": len(pre_scores),
            "average_score": sum(pre_scores) / len(pre_scores) if pre_scores else 0,
            "passed": sum(1 for r in results if r.get('test_type') in ['pre', 'pre_test'] and r.get('passed', False))
        },
        "post_test": {
            "completed": len(post_scores),
            "average_score": sum(post_scores) / len(post_scores) if post_scores else 0,
            "passed": sum(1 for r in results if r.get('test_type') in ['post', 'post_test'] and r.get('passed', False))
        }
    }


@router.post("/{session_id}/release-pre-test")
async def release_pre_test(session_id: str, current_user: User = Depends(get_current_user)):
    """Release pre-test for all participants"""
    if current_user.role not in ["coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    for pid in session.get("participant_ids", []):
        await get_or_create_participant_access(pid, session_id)
        await db.participant_access.update_one(
            {"participant_id": pid, "session_id": session_id},
            {"$set": {"can_access_pre_test": True}}
        )
    
    return {"message": "Pre-test released for all participants"}


@router.post("/{session_id}/release-post-test")
async def release_post_test(session_id: str, current_user: User = Depends(get_current_user)):
    """Release post-test for all participants"""
    if current_user.role not in ["coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    for pid in session.get("participant_ids", []):
        await get_or_create_participant_access(pid, session_id)
        await db.participant_access.update_one(
            {"participant_id": pid, "session_id": session_id},
            {"$set": {"can_access_post_test": True}}
        )
    
    return {"message": "Post-test released for all participants"}


@router.post("/{session_id}/release-feedback")
async def release_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    """Release feedback for all participants"""
    if current_user.role not in ["coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    for pid in session.get("participant_ids", []):
        await get_or_create_participant_access(pid, session_id)
        await db.participant_access.update_one(
            {"participant_id": pid, "session_id": session_id},
            {"$set": {"can_access_feedback": True}}
        )
    
    return {"message": "Feedback released for all participants"}


@router.get("/{session_id}/participants/attendance")
async def get_participants_attendance(session_id: str, current_user: User = Depends(get_current_user)):
    """Get attendance for all participants in a session"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    
    result = []
    for pid in participant_ids:
        user = await db.users.find_one({"id": pid}, {"_id": 0, "password": 0})
        attendance = await db.attendance.find_one({"participant_id": pid, "session_id": session_id}, {"_id": 0})
        
        if user:
            result.append({
                "participant": user,
                "attendance": attendance
            })
    
    return result


@router.get("/{session_id}/tests/available")
async def get_available_tests(session_id: str, current_user: User = Depends(get_current_user)):
    """Get available tests for a participant in a session"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can access this")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    access = await get_or_create_participant_access(current_user.id, session_id)
    tests = await db.tests.find({"program_id": session['program_id']}, {"_id": 0}).to_list(10)
    
    import random
    available_tests = []
    for test in tests:
        if isinstance(test.get('created_at'), str):
            test['created_at'] = datetime.fromisoformat(test['created_at'])
        
        test_type = test['test_type']
        can_access = False
        is_completed = False
        
        if test_type in ["pre", "pre_test"]:
            can_access = access.can_access_pre_test
            is_completed = access.pre_test_completed
        elif test_type in ["post", "post_test"]:
            can_access = access.can_access_post_test
            is_completed = access.post_test_completed
        
        if can_access and not is_completed:
            test_copy = test.copy()
            questions = test['questions'].copy()
            
            if test_type == "post":
                random.shuffle(questions)
            
            test_copy['questions'] = [
                {'question': q['question'], 'options': q['options']}
                for q in questions
            ]
            available_tests.append(test_copy)
    
    return available_tests


# ==================== STAGE 6b: Additional Session Endpoints ====================

@router.get("/{session_id}/indemnity-records")
async def get_session_indemnity_records(session_id: str, current_user: User = Depends(get_current_user)):
    """Get indemnity acceptance records for all participants in a session"""
    if current_user.role not in ["admin", "coordinator", "assistant_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    participants = await db.users.find(
        {"id": {"$in": participant_ids}},
        {
            "_id": 0,
            "id": 1,
            "full_name": 1,
            "id_number": 1,
            "email": 1,
            "phone_number": 1,
            "profile_verified": 1,
            "indemnity_accepted": 1,
            "indemnity_accepted_at": 1,
            "indemnity_signature": 1,
            "indemnity_signed_name": 1,
            "indemnity_signed_ic": 1,
            "indemnity_signed_date": 1,
            "emergency_contact_name": 1,
            "emergency_contact_relationship": 1,
            "emergency_contact_phone": 1
        }
    ).to_list(1000)
    
    return {
        "session_id": session_id,
        "session_name": session.get("name"),
        "company_name": session.get("company_name"),
        "training_date": f"{session.get('start_date')} to {session.get('end_date')}",
        "location": session.get("location"),
        "total_participants": len(participants),
        "indemnity_records": participants
    }


@router.get("/{session_id}/indemnity-records/export")
async def export_session_indemnity_records(session_id: str, current_user: User = Depends(get_current_user)):
    """Export indemnity records as Excel file"""
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    import openpyxl
    
    if current_user.role not in ["admin", "coordinator", "assistant_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get("participant_ids", [])
    participants = await db.users.find({"id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Indemnity Records"
    
    headers = ["No", "Full Name", "IC Number", "Indemnity Accepted", "Signed Name", "Signed IC", "Signed Date", "Accepted At"]
    ws.append(headers)
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
    
    for idx, p in enumerate(participants, 1):
        ws.append([
            idx,
            p.get("full_name", ""),
            p.get("id_number", ""),
            "Yes" if p.get("indemnity_accepted") else "No",
            p.get("indemnity_signed_name", ""),
            p.get("indemnity_signed_ic", ""),
            p.get("indemnity_signed_date", ""),
            p.get("indemnity_accepted_at", "")
        ])
    
    for column in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 40)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    session_name = session.get("name", "Session").replace(" ", "_")
    filename = f"Indemnity_Records_{session_name}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.put("/{session_id}/toggle-status")
async def toggle_session_status(session_id: str, current_user: User = Depends(get_current_user)):
    """Toggle session between active and inactive (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change session status")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    new_status = "inactive" if session.get("status", "active") == "active" else "active"
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"status": new_status}}
    )
    
    return {"message": f"Session marked as {new_status}", "status": new_status}


@router.post("/{session_id}/participants")
async def add_participants_to_session(
    session_id: str,
    participant_ids: dict,
    current_user: User = Depends(get_current_user)
):
    """Add participants to a session by IC number or user ID"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can add participants")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    ids_to_add = participant_ids.get("participant_ids", [])
    if not ids_to_add:
        raise HTTPException(status_code=400, detail="No participant IDs provided")
    
    added_ids = []
    for identifier in ids_to_add:
        user = await db.users.find_one(
            {"$or": [{"id_number": identifier}, {"id": identifier}]},
            {"_id": 0, "id": 1}
        )
        if user:
            added_ids.append(user["id"])
        else:
            raise HTTPException(status_code=404, detail=f"User not found: {identifier}")
    
    current_participants = session.get("participant_ids", [])
    newly_added = []
    for user_id in added_ids:
        if user_id not in current_participants:
            current_participants.append(user_id)
            newly_added.append(user_id)
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"participant_ids": current_participants}}
    )
    
    for user_id in newly_added:
        await get_or_create_participant_access(user_id, session_id)
    
    return {
        "message": f"Successfully added {len(added_ids)} participant(s)",
        "added_count": len(added_ids)
    }


@router.put("/{session_id}")
async def update_session(session_id: str, session_data: dict, current_user: User = Depends(get_current_user)):
    """Update session details"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if current_user.role == "coordinator":
        if session.get("coordinator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update sessions assigned to you")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins and coordinators can update sessions")
    
    result = await db.sessions.update_one(
        {"id": session_id},
        {"$set": session_data}
    )
    
    updated_session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    return updated_session


@router.delete("/{session_id}")
async def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    """Delete session and all related data"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete sessions")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    total_deleted = 0
    
    result = await db.sessions.delete_one({"id": session_id})
    total_deleted += result.deleted_count
    
    related_collections = [
        "test_results", "course_feedback", "attendance", "attendance_records",
        "participant_attendance", "vehicle_checklists", "vehicle_details",
        "certificates", "participant_access", "training_reports",
        "chief_trainer_feedback", "coordinator_feedback",
        "trainer_fees", "coordinator_fees", "session_expenses",
        "invoices", "credit_notes", "marketing_commissions",
    ]
    
    for collection_name in related_collections:
        result = await db[collection_name].delete_many({"session_id": session_id})
        total_deleted += result.deleted_count
    
    return {
        "message": "Session and all related data deleted successfully",
        "session_name": session.get("name"),
        "records_deleted": total_deleted
    }


@router.delete("/bulk/delete-all")
async def delete_all_sessions(current_user: User = Depends(get_current_user)):
    """Delete ALL sessions and related data - for testing/cleanup purposes"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete all sessions")
    
    all_sessions = await db.sessions.find({}, {"_id": 0, "id": 1}).to_list(1000)
    session_ids = [s["id"] for s in all_sessions]
    
    if not session_ids:
        return {"message": "No sessions to delete", "sessions_deleted": 0, "total_records_deleted": 0}
    
    total_deleted = 0
    
    collections_to_clean = [
        "sessions", "test_results", "course_feedback", "attendance",
        "attendance_records", "participant_attendance", "vehicle_checklists",
        "vehicle_details", "certificates", "participant_access",
        "training_reports", "chief_trainer_feedback", "coordinator_feedback",
    ]
    
    for collection_name in collections_to_clean:
        result = await db[collection_name].delete_many({})
        total_deleted += result.deleted_count
    
    return {
        "message": "All sessions and related data deleted successfully",
        "sessions_deleted": len(session_ids),
        "total_records_deleted": total_deleted
    }


@router.post("/{session_id}/participants/{participant_id}/attendance")
async def mark_participant_attendance(
    session_id: str,
    participant_id: str,
    status: str,
    current_user: User = Depends(get_current_user)
):
    """Mark participant as present or absent for a session"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can mark attendance")
    
    if status not in ["present", "absent"]:
        raise HTTPException(status_code=400, detail="Status must be 'present' or 'absent'")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if participant_id not in session.get("participant_ids", []):
        raise HTTPException(status_code=400, detail="Participant not enrolled in this session")
    
    await db.participant_attendance.update_one(
        {"session_id": session_id, "participant_id": participant_id},
        {"$set": {"status": status, "marked_by": current_user.id, "marked_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    
    return {"message": f"Participant marked as {status}", "status": status}


@router.post("/{session_id}/mark-completed")
async def mark_session_completed(session_id: str, current_user: User = Depends(get_current_user)):
    """Mark session as completed by coordinator - archives session and pushes report to supervisors"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can mark sessions as completed")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    if not training_report or not training_report.get("final_pdf_filename"):
        raise HTTPException(
            status_code=400,
            detail="Training report must be uploaded before marking session as completed. Please upload the final PDF report first."
        )
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "completion_status": "completed",
            "completed_by_coordinator": True,
            "completed_date": get_malaysia_time().isoformat(),
            "report_available_to_supervisors": True
        }}
    )
    
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {"available_to_supervisors": True, "pushed_to_supervisors_at": get_malaysia_time().isoformat()}}
    )
    
    return {
        "message": "Session marked as completed successfully. Report is now available to supervisors.",
        "session_archived": True,
        "report_pushed_to_supervisors": True
    }
