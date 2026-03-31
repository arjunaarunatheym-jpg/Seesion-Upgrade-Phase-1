"""
Super Admin Data Management Routes
Admin can edit/delete any data with full audit logging
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from datetime import datetime

from models import CourseFeedback, User
from models.test import TestResult
from models.audit import AuditLog, AuditLogResponse
from services.auth_service import get_current_user
from utils import db
from utils.audit_helper import log_audit, get_audit_logs_for_resource

router = APIRouter(prefix="/admin/data-management", tags=["admin_data_management"])


# ============================================================================
# TEST RESULTS MANAGEMENT
# ============================================================================

@router.get("/test-results")
async def get_test_results_admin(
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all test results with filters (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this")
    
    query = {}
    
    # Apply filters
    if session_id:
        query["session_id"] = session_id
    
    # For company/program filtering, we need to join with sessions
    if company_id or program_id or start_date or end_date:
        # Get matching sessions first
        session_query = {}
        if company_id:
            session_query["company_id"] = company_id
        if program_id:
            session_query["program_id"] = program_id
        if start_date:
            session_query["start_date"] = {"$gte": start_date}
        if end_date:
            session_query["end_date"] = {"$lte": end_date}
        
        sessions = await db.sessions.find(session_query, {"_id": 0, "id": 1}).to_list(1000)
        session_ids = [s["id"] for s in sessions]
        query["session_id"] = {"$in": session_ids}
    
    results = await db.test_results.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with participant and session info
    for result in results:
        if isinstance(result.get('submitted_at'), str):
            result['submitted_at'] = datetime.fromisoformat(result['submitted_at'])
        
        # Get participant details
        participant = await db.users.find_one({"id": result["participant_id"]}, {"_id": 0})
        if participant:
            result["participant_name"] = participant.get("full_name", "Unknown")
            result["participant_ic"] = participant.get("id_number", "Unknown")
        
        # Get session details
        session = await db.sessions.find_one({"id": result["session_id"]}, {"_id": 0})
        if session:
            result["session_name"] = session.get("name", "Unknown")
            
            # Get company and program names
            if session.get("company_id"):
                company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
                result["company_name"] = company.get("name") if company else "Unknown"
            
            if session.get("program_id"):
                program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
                result["program_name"] = program.get("name") if program else "Unknown"
        
        # Get test details
        test = await db.tests.find_one({"id": result["test_id"]}, {"_id": 0})
        if test:
            result["test_title"] = test.get("title", "Unknown")
            result["test_type"] = test.get("test_type", "Unknown")
    
    return results


@router.put("/test-results/{result_id}")
async def update_test_result(
    result_id: str,
    score: Optional[float] = None,
    passed: Optional[bool] = None,
    answers: Optional[List[int]] = None,
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Update a test result (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit test results")
    
    # Get existing result
    existing = await db.test_results.find_one({"id": result_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    # Prepare updates
    updates = {}
    if score is not None:
        updates["score"] = score
    if passed is not None:
        updates["passed"] = passed
    if answers is not None:
        updates["answers"] = answers
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    # Update the record
    await db.test_results.update_one({"id": result_id}, {"$set": updates})
    
    # Get updated result
    updated = await db.test_results.find_one({"id": result_id}, {"_id": 0})
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="update",
        resource_type="test_result",
        resource_id=result_id,
        old_data=existing,
        new_data=updated,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Test result updated successfully", "result": updated}


@router.delete("/test-results/{result_id}")
async def delete_test_result(
    result_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Delete a test result (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete test results")
    
    # Get existing result for audit log
    existing = await db.test_results.find_one({"id": result_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    # Hard delete
    result = await db.test_results.delete_one({"id": result_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="delete",
        resource_type="test_result",
        resource_id=result_id,
        old_data=existing,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Test result deleted successfully"}


# ============================================================================
# FEEDBACK MANAGEMENT
# ============================================================================

@router.get("/feedback")
async def get_feedback_admin(
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all feedback with filters (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this")
    
    query = {}
    
    if session_id:
        query["session_id"] = session_id
    
    # For company/program filtering, join with sessions
    if company_id or program_id or start_date or end_date:
        session_query = {}
        if company_id:
            session_query["company_id"] = company_id
        if program_id:
            session_query["program_id"] = program_id
        if start_date:
            session_query["start_date"] = {"$gte": start_date}
        if end_date:
            session_query["end_date"] = {"$lte": end_date}
        
        sessions = await db.sessions.find(session_query, {"_id": 0, "id": 1}).to_list(1000)
        session_ids = [s["id"] for s in sessions]
        query["session_id"] = {"$in": session_ids}
    
    feedback_list = await db.course_feedback.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with participant and session info
    for feedback in feedback_list:
        if isinstance(feedback.get('submitted_at'), str):
            feedback['submitted_at'] = datetime.fromisoformat(feedback['submitted_at'])
        
        # Get participant details
        participant = await db.users.find_one({"id": feedback["participant_id"]}, {"_id": 0})
        if participant:
            feedback["participant_name"] = participant.get("full_name", "Unknown")
            feedback["participant_ic"] = participant.get("id_number", "Unknown")
        
        # Get session details
        session = await db.sessions.find_one({"id": feedback["session_id"]}, {"_id": 0})
        if session:
            feedback["session_name"] = session.get("name", "Unknown")
            
            if session.get("company_id"):
                company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
                feedback["company_name"] = company.get("name") if company else "Unknown"
            
            if session.get("program_id"):
                program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
                feedback["program_name"] = program.get("name") if program else "Unknown"
    
    return feedback_list


@router.put("/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    responses: List[dict],
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Update feedback responses (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit feedback")
    
    # Get existing feedback
    existing = await db.course_feedback.find_one({"id": feedback_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Update the record
    await db.course_feedback.update_one(
        {"id": feedback_id},
        {"$set": {"responses": responses}}
    )
    
    # Get updated feedback
    updated = await db.course_feedback.find_one({"id": feedback_id}, {"_id": 0})
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="update",
        resource_type="feedback",
        resource_id=feedback_id,
        old_data=existing,
        new_data=updated,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Feedback updated successfully", "feedback": updated}


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Delete feedback (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete feedback")
    
    # Get existing feedback for audit log
    existing = await db.course_feedback.find_one({"id": feedback_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Hard delete
    result = await db.course_feedback.delete_one({"id": feedback_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="delete",
        resource_type="feedback",
        resource_id=feedback_id,
        old_data=existing,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Feedback deleted successfully"}


# ============================================================================
# ATTENDANCE MANAGEMENT
# ============================================================================

@router.get("/attendance")
async def get_attendance_admin(
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all attendance records with filters (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this")
    
    query = {}
    
    if session_id:
        query["session_id"] = session_id
    
    # For company/program filtering, join with sessions
    if company_id or program_id or start_date or end_date:
        session_query = {}
        if company_id:
            session_query["company_id"] = company_id
        if program_id:
            session_query["program_id"] = program_id
        if start_date:
            session_query["start_date"] = {"$gte": start_date}
        if end_date:
            session_query["end_date"] = {"$lte": end_date}
        
        sessions = await db.sessions.find(session_query, {"_id": 0, "id": 1}).to_list(1000)
        session_ids = [s["id"] for s in sessions]
        query["session_id"] = {"$in": session_ids}
    
    attendance_list = await db.attendance.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with participant and session info
    for attendance in attendance_list:
        # Handle clock_in datetime conversion
        if attendance.get('clock_in'):
            if isinstance(attendance['clock_in'], str):
                try:
                    attendance['clock_in'] = datetime.fromisoformat(attendance['clock_in'])
                except:
                    pass
        
        # Handle clock_out datetime conversion
        if attendance.get('clock_out'):
            if isinstance(attendance['clock_out'], str):
                try:
                    attendance['clock_out'] = datetime.fromisoformat(attendance['clock_out'])
                except:
                    pass
        
        # Get participant details
        if attendance.get("participant_id"):
            participant = await db.users.find_one({"id": attendance["participant_id"]}, {"_id": 0})
            if participant:
                attendance["participant_name"] = participant.get("full_name", "Unknown")
                attendance["participant_ic"] = participant.get("id_number", "Unknown")
        
        # Get session details
        if attendance.get("session_id"):
            session = await db.sessions.find_one({"id": attendance["session_id"]}, {"_id": 0})
            if session:
                attendance["session_name"] = session.get("name", "Unknown")
                
                if session.get("company_id"):
                    company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
                    attendance["company_name"] = company.get("name") if company else "Unknown"
                
                if session.get("program_id"):
                    program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
                    attendance["program_name"] = program.get("name") if program else "Unknown"
    
    return attendance_list


@router.put("/attendance/{attendance_id}")
async def update_attendance(
    attendance_id: str,
    clock_in: Optional[str] = None,
    clock_out: Optional[str] = None,
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Update attendance record (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit attendance")
    
    # Get existing attendance
    existing = await db.attendance.find_one({"id": attendance_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Prepare updates
    updates = {}
    if clock_in:
        updates["clock_in"] = clock_in
    if clock_out:
        updates["clock_out"] = clock_out
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    # Update the record
    await db.attendance.update_one({"id": attendance_id}, {"$set": updates})
    
    # Get updated attendance
    updated = await db.attendance.find_one({"id": attendance_id}, {"_id": 0})
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="update",
        resource_type="attendance",
        resource_id=attendance_id,
        old_data=existing,
        new_data=updated,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Attendance updated successfully", "attendance": updated}


@router.delete("/attendance/{attendance_id}")
async def delete_attendance(
    attendance_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Delete attendance record (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete attendance")
    
    # Get existing attendance for audit log
    existing = await db.attendance.find_one({"id": attendance_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Hard delete
    result = await db.attendance.delete_one({"id": attendance_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="delete",
        resource_type="attendance",
        resource_id=attendance_id,
        old_data=existing,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Attendance deleted successfully"}


# ============================================================================
# VEHICLE CHECKLIST MANAGEMENT
# ============================================================================

@router.get("/checklists")
async def get_checklists_admin(
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all vehicle checklists with filters (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this")
    
    query = {}
    
    if session_id:
        query["session_id"] = session_id
    
    # For company/program filtering, join with sessions
    if company_id or program_id or start_date or end_date:
        session_query = {}
        if company_id:
            session_query["company_id"] = company_id
        if program_id:
            session_query["program_id"] = program_id
        if start_date:
            session_query["start_date"] = {"$gte": start_date}
        if end_date:
            session_query["end_date"] = {"$lte": end_date}
        
        sessions = await db.sessions.find(session_query, {"_id": 0, "id": 1}).to_list(1000)
        session_ids = [s["id"] for s in sessions]
        query["session_id"] = {"$in": session_ids}
    
    checklists = await db.vehicle_checklists.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with participant and session info
    for checklist in checklists:
        if isinstance(checklist.get('created_at'), str):
            checklist['created_at'] = datetime.fromisoformat(checklist['created_at'])
        
        # Get participant details
        if checklist.get("participant_id"):
            participant = await db.users.find_one({"id": checklist["participant_id"]}, {"_id": 0})
            if participant:
                checklist["participant_name"] = participant.get("full_name", "Unknown")
                checklist["participant_ic"] = participant.get("id_number", "Unknown")
        
        # Get trainer details
        if checklist.get("trainer_id"):
            trainer = await db.users.find_one({"id": checklist["trainer_id"]}, {"_id": 0})
            if trainer:
                checklist["trainer_name"] = trainer.get("full_name", "Unknown")
        
        # Get session details
        session = await db.sessions.find_one({"id": checklist["session_id"]}, {"_id": 0})
        if session:
            checklist["session_name"] = session.get("name", "Unknown")
            
            if session.get("company_id"):
                company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
                checklist["company_name"] = company.get("name") if company else "Unknown"
            
            if session.get("program_id"):
                program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
                checklist["program_name"] = program.get("name") if program else "Unknown"
    
    return checklists


@router.put("/checklists/{checklist_id}")
async def update_checklist(
    checklist_id: str,
    items: List[dict],
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Update vehicle checklist items (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit checklists")
    
    # Get existing checklist
    existing = await db.vehicle_checklists.find_one({"id": checklist_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist not found")
    
    # Update the record
    await db.vehicle_checklists.update_one(
        {"id": checklist_id},
        {"$set": {"items": items}}
    )
    
    # Get updated checklist
    updated = await db.vehicle_checklists.find_one({"id": checklist_id}, {"_id": 0})
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="update",
        resource_type="checklist",
        resource_id=checklist_id,
        old_data=existing,
        new_data=updated,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Checklist updated successfully", "checklist": updated}


@router.delete("/checklists/{checklist_id}")
async def delete_checklist(
    checklist_id: str,
    request: Request = None,
    current_user: User = Depends(get_current_user)
):
    """Delete vehicle checklist (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete checklists")
    
    # Get existing checklist for audit log
    existing = await db.vehicle_checklists.find_one({"id": checklist_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Checklist not found")
    
    # Hard delete
    result = await db.vehicle_checklists.delete_one({"id": checklist_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Checklist not found")
    
    # Log the audit trail
    await log_audit(
        user_id=current_user.id,
        user_email=current_user.email,
        action="delete",
        resource_type="checklist",
        resource_id=checklist_id,
        old_data=existing,
        ip_address=request.client.host if request else None
    )
    
    return {"message": "Checklist deleted successfully"}


# ============================================================================
# AUDIT LOG VIEWING
# ============================================================================

@router.get("/audit-logs/{resource_type}/{resource_id}", response_model=List[AuditLogResponse])
async def get_audit_logs(
    resource_type: str,
    resource_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get audit logs for a specific resource (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")
    
    logs = await get_audit_logs_for_resource(resource_type, resource_id)
    
    # Format response
    response = []
    for log in logs:
        changes_summary = None
        if log.get("action") == "update" and log.get("old_data") and log.get("new_data"):
            # Generate a summary of what changed
            old = log["old_data"]
            new = log["new_data"]
            changes = []
            for key in new.keys():
                if key in old and old[key] != new[key]:
                    changes.append(f"{key}: {old[key]} → {new[key]}")
            changes_summary = ", ".join(changes) if changes else "No changes detected"
        
        response.append(AuditLogResponse(
            id=log["id"],
            user_email=log["user_email"],
            action=log["action"],
            resource_type=log["resource_type"],
            resource_id=log["resource_id"],
            timestamp=log["timestamp"],
            changes_summary=changes_summary
        ))
    
    return response
