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


@router.get("")
async def get_sessions(
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get sessions filtered by user role - main sessions endpoint"""
    from datetime import date as dt_date
    current_date_str = dt_date.today().isoformat()
    
    if current_user.role == "admin":
        # Admin sees all non-completed, non-archived sessions
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
    elif current_user.role == "trainer":
        # Trainer sees sessions they're assigned to (current/future, non-completed)
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},
                {"end_date": {"$gte": current_date_str}},
                {
                    "$or": [
                        {"completed_by_coordinator": {"$exists": False}},
                        {"completed_by_coordinator": False},
                        {"completion_status": {"$exists": False}},
                        {"completion_status": "ongoing"}
                    ]
                },
                {
                    "$or": [
                        {"trainer_assignments.trainer_id": current_user.id},
                        {"assistant_coordinator_ids": current_user.id}
                    ]
                }
            ]
        }
    elif current_user.role == "coordinator":
        # Coordinator sees sessions they're assigned to as coordinator OR assistant coordinator
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},
                {"status": "active"},
                {
                    "$or": [
                        {"completion_status": {"$exists": False}},
                        {"completion_status": "ongoing"},
                        {"completion_status": {"$nin": ["completed", "archived"]}}
                    ]
                },
                {
                    "$or": [
                        {"coordinator_id": current_user.id},
                        {"assistant_coordinator_ids": current_user.id}
                    ]
                }
            ]
        }
    elif current_user.role == "assistant_admin":
        # Assistant admin sees all non-completed sessions
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
    else:
        # Default: show all non-completed, non-archived sessions
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},
                {"status": "active"},
                {
                    "$or": [
                        {"completion_status": {"$exists": False}},
                        {"completion_status": "ongoing"},
                        {"completion_status": {"$nin": ["completed", "archived"]}}
                    ]
                }
            ]
        }
    
    # Add search filters
    if company_id:
        query["$and"].append({"company_id": company_id})
    if program_id:
        query["$and"].append({"program_id": program_id})
    if start_date:
        query["$and"].append({"start_date": {"$gte": start_date}})
    if end_date:
        query["$and"].append({"end_date": {"$lte": end_date}})
    
    sessions = await db.sessions.find(query, {"_id": 0}).sort("start_date", -1).to_list(1000)
    
    # Enrich with company_name and program_name
    for session in sessions:
        if not session.get("company_name") and session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0, "name": 1})
            if company:
                session["company_name"] = company.get("name")
        
        if not session.get("program_name") and session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0, "name": 1})
            if program:
                session["program_name"] = program.get("name")
        
        # Convert datetime objects to strings for JSON serialization
        if isinstance(session.get("created_at"), datetime):
            session["created_at"] = session["created_at"].isoformat()
    
    return sessions



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
    """Update session details with cascade to invoices"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if current_user.role == "coordinator":
        if session.get("coordinator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update sessions assigned to you")
    elif current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can update sessions")
    
    # Capture old values before update
    old_start_date = session.get("start_date")
    old_end_date = session.get("end_date")
    old_company_name = session.get("company_name")
    old_location = session.get("location")
    old_program_id = session.get("program_id")
    
    # Check if participant_ids changed (new participants added)
    old_participant_ids = set(session.get("participant_ids", []))
    new_participant_ids = set(session_data.get("participant_ids", []))
    
    result = await db.sessions.update_one(
        {"id": session_id},
        {"$set": session_data}
    )
    
    # Cascade company_name update to related invoices and quotations
    new_company_name = session_data.get("company_name")
    if new_company_name and new_company_name != old_company_name:
        await db.invoices.update_many(
            {"session_id": session_id},
            {"$set": {"company_name": new_company_name, "bill_to_name": new_company_name}}
        )
        if session.get("quotation_id"):
            await db.quotations.update_one(
                {"id": session.get("quotation_id")},
                {"$set": {"client_name": new_company_name, "company_name": new_company_name}}
            )
        if session.get("lead_id"):
            await db.leads.update_one(
                {"id": session.get("lead_id")},
                {"$set": {"company_name": new_company_name}}
            )
    
    # Cascade date changes to related invoices
    new_start_date = session_data.get("start_date")
    new_end_date = session_data.get("end_date")
    if (new_start_date and new_start_date != old_start_date) or (new_end_date and new_end_date != old_end_date):
        final_start = new_start_date or old_start_date
        final_end = new_end_date or old_end_date
        if final_start and final_end:
            new_training_dates = f"{final_start} to {final_end}"
            await db.invoices.update_many(
                {"session_id": session_id},
                {"$set": {"training_dates": new_training_dates}}
            )
    
    # Cascade venue/location changes to related invoices
    new_location = session_data.get("location")
    if new_location and new_location != old_location:
        await db.invoices.update_many(
            {"session_id": session_id},
            {"$set": {"venue": new_location}}
        )
    
    # Cascade programme changes to related invoices
    new_program_id = session_data.get("program_id")
    if new_program_id and new_program_id != old_program_id:
        programme = await db.programs.find_one({"id": new_program_id}, {"_id": 0})
        if programme:
            await db.invoices.update_many(
                {"session_id": session_id},
                {"$set": {"programme_name": programme.get("name")}}
            )
    
    updated_session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    return updated_session


@router.delete("/{session_id}")
async def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    """Delete session and all related data, saving auto-draft invoice numbers for reuse"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete sessions")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check for auto-draft invoices and save their numbers for reuse
    invoices = await db.invoices.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    saved_invoice_numbers = []
    
    for invoice in invoices:
        # Only save numbers from auto-draft/draft invoices (never issued)
        if invoice.get("status") in ["auto_draft", "draft"]:
            invoice_number = invoice.get("invoice_number")
            if invoice_number:
                # Save to deleted_invoice_numbers collection for reuse
                await db.deleted_invoice_numbers.insert_one({
                    "invoice_number": invoice_number,
                    "original_session_id": session_id,
                    "original_session_name": session.get("name"),
                    "original_company_id": session.get("company_id"),
                    "deleted_at": get_malaysia_time().isoformat(),
                    "deleted_by": current_user.id,
                    "is_available": True
                })
                saved_invoice_numbers.append(invoice_number)
    
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
        "records_deleted": total_deleted,
        "invoice_numbers_saved_for_reuse": saved_invoice_numbers
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


# ============================================================
# Admin Session Complete + Excel Import/Export
# ============================================================

@router.post("/{session_id}/admin-complete")
async def admin_mark_session_complete(session_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin marks session as completed (bypasses coordinator workflow)"""
    if current_user.role not in ["admin", "super_admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can force-complete sessions")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    reason = data.get("reason", "Admin override")
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "completion_status": "completed",
            "completed_by_coordinator": True,
            "completed_date": get_malaysia_time().isoformat(),
            "admin_completed": True,
            "admin_complete_reason": reason,
            "admin_completed_by": current_user.id,
            "is_archived": True
        }}
    )
    
    return {
        "message": f"Session marked as completed by admin",
        "session_id": session_id,
        "reason": reason
    }


@router.post("/{session_id}/admin-revert-complete")
async def admin_revert_session_complete(session_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin reverts a completed session back to ongoing"""
    if current_user.role not in ["admin", "super_admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can revert session completion")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    reason = data.get("reason", "Admin revert")
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "completion_status": "ongoing",
            "completed_by_coordinator": False,
            "is_archived": False,
            "revert_reason": reason,
            "reverted_by": current_user.id,
            "reverted_at": get_malaysia_time().isoformat()
        },
        "$unset": {
            "completed_date": "",
            "admin_completed": "",
            "admin_complete_reason": "",
            "admin_completed_by": ""
        }}
    )
    
    return {"message": "Session reverted to ongoing", "session_id": session_id}


@router.get("/{session_id}/export-template")
async def export_session_template(session_id: str, current_user: User = Depends(get_current_user)):
    """Export Excel template pre-populated with session participants"""
    if current_user.role not in ["admin", "super_admin", "assistant_admin", "coordinator", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    from fastapi.responses import StreamingResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from io import BytesIO
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get participants
    participant_ids = session.get("participant_ids", [])
    participants = []
    for pid in participant_ids:
        user = await db.users.find_one({"id": pid}, {"_id": 0, "id": 1, "name": 1, "ic_number": 1, "email": 1, "phone": 1})
        if user:
            participants.append(user)
    
    # Get existing data
    existing_attendance = await db.attendance.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    existing_tests = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    
    att_map = {}
    for a in existing_attendance:
        key = a.get("participant_id")
        if key not in att_map:
            att_map[key] = []
        att_map[key].append(a)
    
    test_map = {}
    for t in existing_tests:
        key = (t.get("participant_id"), t.get("test_type"))
        test_map[key] = t
    
    # Get session dates for attendance columns
    start = session.get("start_date", "")
    end = session.get("end_date", start)
    
    wb = Workbook()
    
    # === Sheet 1: Test Scores ===
    ws1 = wb.active
    ws1.title = "Test Scores"
    
    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # Info rows
    ws1.merge_cells('A1:F1')
    ws1['A1'] = f"Session: {session.get('company_name', 'N/A')} - {session.get('program_name', 'N/A')}"
    ws1['A1'].font = Font(bold=True, size=14)
    ws1.merge_cells('A2:F2')
    ws1['A2'] = f"Dates: {start} to {end} | Session ID: {session_id}"
    ws1['A2'].font = Font(size=11, italic=True)
    
    headers = ["No", "Participant Name", "IC Number", "Pre-Test Score (%)", "Post-Test Score (%)", "Remarks"]
    for col, h in enumerate(headers, 1):
        cell = ws1.cell(row=4, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
    
    for i, p in enumerate(participants, 1):
        row = i + 4
        ws1.cell(row=row, column=1, value=i).border = thin_border
        ws1.cell(row=row, column=2, value=p.get("name", "")).border = thin_border
        ws1.cell(row=row, column=3, value=p.get("ic_number", "")).border = thin_border
        
        pre = test_map.get((p["id"], "pre"))
        post = test_map.get((p["id"], "post"))
        pre_cell = ws1.cell(row=row, column=4, value=pre.get("score") if pre else None)
        pre_cell.border = thin_border
        post_cell = ws1.cell(row=row, column=5, value=post.get("score") if post else None)
        post_cell.border = thin_border
        ws1.cell(row=row, column=6, value="").border = thin_border
    
    ws1.column_dimensions['A'].width = 6
    ws1.column_dimensions['B'].width = 30
    ws1.column_dimensions['C'].width = 18
    ws1.column_dimensions['D'].width = 20
    ws1.column_dimensions['E'].width = 20
    ws1.column_dimensions['F'].width = 25
    
    # === Sheet 2: Attendance ===
    ws2 = wb.create_sheet("Attendance")
    ws2.merge_cells('A1:F1')
    ws2['A1'] = f"Attendance Record - {session.get('company_name', 'N/A')}"
    ws2['A1'].font = Font(bold=True, size=14)
    ws2.merge_cells('A2:F2')
    ws2['A2'] = f"Enter 'P' for Present, 'A' for Absent, 'L' for Late"
    ws2['A2'].font = Font(size=11, italic=True, color="666666")
    
    att_headers = ["No", "Participant Name", "IC Number"]
    # Generate day columns
    from datetime import date as dt_date, timedelta
    day_dates = []
    if start:
        try:
            s_date = dt_date.fromisoformat(start)
            e_date = dt_date.fromisoformat(end) if end else s_date
            current = s_date
            while current <= e_date:
                day_dates.append(current.isoformat())
                att_headers.append(f"Day {len(day_dates)} ({current.strftime('%d/%m')})")
                current += timedelta(days=1)
        except:
            att_headers.append("Day 1")
            day_dates.append(start)
    
    for col, h in enumerate(att_headers, 1):
        cell = ws2.cell(row=4, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
    
    for i, p in enumerate(participants, 1):
        row = i + 4
        ws2.cell(row=row, column=1, value=i).border = thin_border
        ws2.cell(row=row, column=2, value=p.get("name", "")).border = thin_border
        ws2.cell(row=row, column=3, value=p.get("ic_number", "")).border = thin_border
        
        p_att = att_map.get(p["id"], [])
        for d_idx, d_date in enumerate(day_dates):
            day_att = next((a for a in p_att if a.get("date") == d_date), None)
            val = "P" if day_att and day_att.get("clock_in") else ""
            ws2.cell(row=row, column=4 + d_idx, value=val).border = thin_border
    
    ws2.column_dimensions['A'].width = 6
    ws2.column_dimensions['B'].width = 30
    ws2.column_dimensions['C'].width = 18
    for d_idx in range(len(day_dates)):
        ws2.column_dimensions[chr(68 + d_idx)].width = 16
    
    # === Sheet 3: Instructions ===
    ws3 = wb.create_sheet("Instructions")
    instructions = [
        ("MDDRC Session Data Import Template", Font(bold=True, size=16)),
        ("", None),
        ("Sheet 1: Test Scores", Font(bold=True, size=12)),
        ("- Fill in Pre-Test Score and Post-Test Score as percentages (0-100)", None),
        ("- Do NOT modify the IC Number column - it's used for matching", None),
        ("- Leave blank if no score available", None),
        ("", None),
        ("Sheet 2: Attendance", Font(bold=True, size=12)),
        ("- Enter 'P' for Present, 'A' for Absent, 'L' for Late", None),
        ("- Each Day column corresponds to the session date shown in the header", None),
        ("- Leave blank if no data", None),
        ("", None),
        ("IMPORTANT:", Font(bold=True, size=12, color="FF0000")),
        ("- Do NOT add/remove rows or change the order of participants", None),
        ("- Do NOT modify IC Numbers - they are used to match participants", None),
        ("- Save as .xlsx format before uploading", None),
    ]
    for i, (text, font) in enumerate(instructions, 1):
        cell = ws3.cell(row=i, column=1, value=text)
        if font:
            cell.font = font
    ws3.column_dimensions['A'].width = 70
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    company = (session.get("company_name") or "session").replace(" ", "_")[:30]
    filename = f"MDDRC_Template_{company}_{start}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/{session_id}/import-data")
async def import_session_data(session_id: str, file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Import session data (test scores, attendance) from Excel"""
    if current_user.role not in ["admin", "super_admin", "assistant_admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    from openpyxl import load_workbook
    from io import BytesIO
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    content = await file.read()
    wb = load_workbook(BytesIO(content), read_only=True)
    
    results = {"test_scores_imported": 0, "attendance_imported": 0, "errors": [], "skipped": []}
    
    # Build participant lookup by IC number
    participant_ids = session.get("participant_ids", [])
    ic_to_participant = {}
    for pid in participant_ids:
        user = await db.users.find_one({"id": pid}, {"_id": 0, "id": 1, "name": 1, "ic_number": 1})
        if user and user.get("ic_number"):
            ic_to_participant[str(user["ic_number"]).strip()] = user
    
    # === Process Test Scores (Sheet 1) ===
    if "Test Scores" in wb.sheetnames:
        ws = wb["Test Scores"]
        for row in ws.iter_rows(min_row=5, values_only=False):
            try:
                ic = str(row[2].value or "").strip()
                if not ic or ic not in ic_to_participant:
                    continue
                
                participant = ic_to_participant[ic]
                pid = participant["id"]
                pre_score = row[3].value
                post_score = row[4].value
                
                # Import pre-test score
                if pre_score is not None and str(pre_score).strip() != "":
                    score_val = float(pre_score)
                    existing = await db.test_results.find_one({"session_id": session_id, "participant_id": pid, "test_type": "pre"})
                    if existing:
                        await db.test_results.update_one(
                            {"session_id": session_id, "participant_id": pid, "test_type": "pre"},
                            {"$set": {"score": score_val, "passed": score_val >= 50, "imported": True, "imported_at": get_malaysia_time().isoformat()}}
                        )
                    else:
                        await db.test_results.insert_one({
                            "id": str(uuid.uuid4()),
                            "test_id": f"import-pre-{session_id}",
                            "participant_id": pid,
                            "session_id": session_id,
                            "test_type": "pre",
                            "answers": [],
                            "score": score_val,
                            "total_questions": 0,
                            "correct_answers": 0,
                            "passed": score_val >= 50,
                            "imported": True,
                            "imported_at": get_malaysia_time().isoformat(),
                            "submitted_at": get_malaysia_time().isoformat()
                        })
                    results["test_scores_imported"] += 1
                
                # Import post-test score
                if post_score is not None and str(post_score).strip() != "":
                    score_val = float(post_score)
                    existing = await db.test_results.find_one({"session_id": session_id, "participant_id": pid, "test_type": "post"})
                    if existing:
                        await db.test_results.update_one(
                            {"session_id": session_id, "participant_id": pid, "test_type": "post"},
                            {"$set": {"score": score_val, "passed": score_val >= 50, "imported": True, "imported_at": get_malaysia_time().isoformat()}}
                        )
                    else:
                        await db.test_results.insert_one({
                            "id": str(uuid.uuid4()),
                            "test_id": f"import-post-{session_id}",
                            "participant_id": pid,
                            "session_id": session_id,
                            "test_type": "post",
                            "answers": [],
                            "score": score_val,
                            "total_questions": 0,
                            "correct_answers": 0,
                            "passed": score_val >= 50,
                            "imported": True,
                            "imported_at": get_malaysia_time().isoformat(),
                            "submitted_at": get_malaysia_time().isoformat()
                        })
                    results["test_scores_imported"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Row error: {str(e)}")
    
    # === Process Attendance (Sheet 2) ===
    if "Attendance" in wb.sheetnames:
        ws = wb["Attendance"]
        
        # Parse day dates from headers
        day_dates = []
        header_row = list(ws.iter_rows(min_row=4, max_row=4, values_only=True))[0]
        from datetime import date as dt_date, timedelta
        start = session.get("start_date", "")
        end = session.get("end_date", start)
        if start:
            try:
                s_date = dt_date.fromisoformat(start)
                e_date = dt_date.fromisoformat(end) if end else s_date
                current = s_date
                while current <= e_date:
                    day_dates.append(current.isoformat())
                    current += timedelta(days=1)
            except:
                day_dates = [start]
        
        for row in ws.iter_rows(min_row=5, values_only=False):
            try:
                ic = str(row[2].value or "").strip()
                if not ic or ic not in ic_to_participant:
                    continue
                
                participant = ic_to_participant[ic]
                pid = participant["id"]
                
                for d_idx, d_date in enumerate(day_dates):
                    col_idx = 3 + d_idx
                    if col_idx >= len(row):
                        break
                    val = str(row[col_idx].value or "").strip().upper()
                    
                    if val in ["P", "PRESENT", "L", "LATE"]:
                        existing = await db.attendance.find_one({"session_id": session_id, "participant_id": pid, "date": d_date})
                        clock_in = "09:00:00" if val != "L" else "09:30:00"
                        if existing:
                            await db.attendance.update_one(
                                {"session_id": session_id, "participant_id": pid, "date": d_date},
                                {"$set": {"clock_in": clock_in, "imported": True}}
                            )
                        else:
                            await db.attendance.insert_one({
                                "id": str(uuid.uuid4()),
                                "participant_id": pid,
                                "session_id": session_id,
                                "date": d_date,
                                "clock_in": clock_in,
                                "clock_out": None,
                                "imported": True,
                                "created_at": get_malaysia_time().isoformat()
                            })
                        results["attendance_imported"] += 1
                    elif val in ["A", "ABSENT"]:
                        # Mark as absent by removing any existing attendance
                        await db.attendance.delete_one({"session_id": session_id, "participant_id": pid, "date": d_date})
                        
            except Exception as e:
                results["errors"].append(f"Attendance row error: {str(e)}")
    
    wb.close()
    return results
