"""
Reports Legacy routes - Old report format endpoints (kept for backward compatibility)
These are NOT used by the current frontend (which uses /training-reports/).
Endpoints: 4
- POST /reports/generate
- GET /reports/session/{session_id}
- PUT /reports/{report_id}
- POST /reports/{report_id}/publish
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

from core import db, get_current_user, get_malaysia_time
from models import User

router = APIRouter(prefix="/reports", tags=["reports_legacy"])


class ReportGenerateRequest(BaseModel):
    session_id: str


class ReportUpdateRequest(BaseModel):
    content: str


@router.post("/generate")
async def generate_report(request: ReportGenerateRequest, current_user: User = Depends(get_current_user)):
    """Generate a training report for a session (legacy)"""
    if current_user.role not in ["coordinator", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    session = await db.sessions.find_one({"id": request.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    existing = await db.reports.find_one({"session_id": request.session_id}, {"_id": 0})
    if existing:
        return existing

    program = await db.programs.find_one({"id": session.get("program_id")}, {"_id": 0})
    company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0})
    participants = await db.users.find(
        {"id": {"$in": session.get("participant_ids", [])}}, {"_id": 0}
    ).to_list(None)

    now = get_malaysia_time()
    report = {
        "id": str(uuid.uuid4()),
        "session_id": request.session_id,
        "program_id": session.get("program_id"),
        "company_id": session.get("company_id"),
        "generated_by": current_user.id,
        "session_name": session.get("name"),
        "program_name": program.get("name") if program else "",
        "company_name": company.get("name") if company else "",
        "participant_count": len(participants),
        "content": f"Training Report for {session.get('name', 'Session')}",
        "status": "draft",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    await db.reports.insert_one(report)
    report.pop("_id", None)
    return report


@router.get("/session/{session_id}")
async def get_session_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Get the report for a specific session (legacy)"""
    report = await db.reports.find_one({"session_id": session_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this session")
    return report


@router.put("/{report_id}")
async def update_report(report_id: str, request: ReportUpdateRequest, current_user: User = Depends(get_current_user)):
    """Update a report's content (legacy)"""
    if current_user.role not in ["coordinator", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    existing = await db.reports.find_one({"id": report_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.reports.update_one(
        {"id": report_id},
        {"$set": {
            "content": request.content,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    return {"message": "Report updated successfully"}


@router.post("/{report_id}/publish")
async def publish_report(report_id: str, current_user: User = Depends(get_current_user)):
    """Publish a report (legacy)"""
    if current_user.role not in ["coordinator", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    existing = await db.reports.find_one({"id": report_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.reports.update_one(
        {"id": report_id},
        {"$set": {
            "status": "published",
            "published_at": get_malaysia_time().isoformat(),
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    return {"message": "Report published successfully"}
