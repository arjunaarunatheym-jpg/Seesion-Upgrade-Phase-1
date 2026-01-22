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
async def get_past_training(current_user: User = Depends(get_current_user)):
    """Get completed/archived training sessions"""
    query = {
        "$or": [
            {"completion_status": "completed"},
            {"completion_status": "archived"},
            {"is_archived": True}
        ]
    }
    
    if current_user.role == "coordinator":
        query["coordinator_id"] = current_user.id
    elif current_user.role == "participant":
        query["participant_ids"] = current_user.id
    
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
