"""
Training Reports routes - Training completion reports and AI generation
Endpoints: 12
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
import uuid
import shutil

from core import db, get_current_user, get_malaysia_time
from models import User

from pydantic import BaseModel, Field, ConfigDict

# Paths
STATIC_DIR = Path(__file__).parent.parent / "static"
REPORT_DIR = STATIC_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PDF_DIR = STATIC_DIR / "reports_pdf"
REPORT_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Models
class TrainingReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    coordinator_id: Optional[str] = None
    status: str = "draft"
    content: Optional[dict] = None
    ai_generated_content: Optional[str] = None
    docx_url: Optional[str] = None
    pdf_url: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class TrainingReportCreate(BaseModel):
    session_id: str
    status: str = "draft"
    content: Optional[dict] = None

router = APIRouter(prefix="/training-reports", tags=["training-reports"])


@router.post("", response_model=TrainingReport)
async def create_training_report(report_data: TrainingReportCreate, current_user: User = Depends(get_current_user)):
    """Create or update training completion report"""
    if current_user.role != "coordinator" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only coordinators can create training reports")
    
    existing = await db.training_reports.find_one({"session_id": report_data.session_id}, {"_id": 0})
    
    if existing:
        update_data = report_data.model_dump()
        if update_data['status'] == 'submitted':
            update_data['submitted_at'] = get_malaysia_time().isoformat()
        
        await db.training_reports.update_one(
            {"session_id": report_data.session_id},
            {"$set": update_data}
        )
        
        updated = await db.training_reports.find_one({"session_id": report_data.session_id}, {"_id": 0})
        if isinstance(updated.get('created_at'), str):
            updated['created_at'] = datetime.fromisoformat(updated['created_at'])
        if isinstance(updated.get('submitted_at'), str):
            updated['submitted_at'] = datetime.fromisoformat(updated['submitted_at'])
        return TrainingReport(**updated)
    
    report_obj = TrainingReport(
        **report_data.model_dump(),
        coordinator_id=current_user.id
    )
    
    if report_data.status == 'submitted':
        report_obj.submitted_at = datetime.now(timezone.utc)
    
    doc = report_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('submitted_at'):
        doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    await db.training_reports.insert_one(doc)
    return report_obj


@router.get("/{session_id}")
async def get_training_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Get training report for a session"""
    if current_user.role not in ["admin", "super_admin", "coordinator", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    if not report:
        raise HTTPException(status_code=404, detail="Training report not found")
    
    if isinstance(report.get('created_at'), str):
        report['created_at'] = datetime.fromisoformat(report['created_at'])
    if isinstance(report.get('submitted_at'), str) and report.get('submitted_at'):
        report['submitted_at'] = datetime.fromisoformat(report['submitted_at'])
    
    return report


@router.get("/coordinator/{coordinator_id}")
async def get_coordinator_reports(coordinator_id: str, current_user: User = Depends(get_current_user)):
    """Get all training reports for a coordinator"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    reports = await db.training_reports.find({"coordinator_id": coordinator_id}, {"_id": 0}).to_list(100)
    
    for report in reports:
        if isinstance(report.get('created_at'), str):
            report['created_at'] = datetime.fromisoformat(report['created_at'])
        if isinstance(report.get('submitted_at'), str) and report.get('submitted_at'):
            report['submitted_at'] = datetime.fromisoformat(report['submitted_at'])
    
    return reports


@router.get("/admin/all")
async def get_all_training_reports(
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all training reports with filters - Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    query = {"status": "submitted"}
    if status:
        query["status"] = status
    
    reports = await db.training_reports.find(query, {"_id": 0}).to_list(1000)
    
    enriched_reports = []
    for report in reports:
        session = await db.sessions.find_one({"id": report['session_id']}, {"_id": 0})
        if not session:
            continue
        
        coordinator = await db.users.find_one({"id": report.get('coordinator_id')}, {"_id": 0})
        company = await db.companies.find_one({"id": session.get('company_id')}, {"_id": 0})
        program = await db.programs.find_one({"id": session.get('program_id')}, {"_id": 0})
        
        if company_id and session.get('company_id') != company_id:
            continue
        if program_id and session.get('program_id') != program_id:
            continue
        if start_date and session.get('start_date', '') < start_date:
            continue
        if end_date and session.get('end_date', '') > end_date:
            continue
        
        enriched = {
            **report,
            "session_name": session.get('name', 'Unknown'),
            "session_start_date": session.get('start_date'),
            "session_end_date": session.get('end_date'),
            "session_location": session.get('location'),
            "coordinator_name": coordinator.get('full_name') if coordinator else 'Unknown',
            "company_name": company.get('name') if company else 'Unknown',
            "program_name": program.get('name') if program else 'Unknown',
            "participant_count": len(session.get('participant_ids', []))
        }
        
        if search:
            search_lower = search.lower()
            searchable = f"{enriched['session_name']} {enriched['coordinator_name']} {enriched['company_name']} {enriched['program_name']}".lower()
            if search_lower not in searchable:
                continue
        
        enriched_reports.append(enriched)
    
    enriched_reports.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
    return {"total": len(enriched_reports), "reports": enriched_reports}


@router.get("/supervisor/sessions")
async def get_supervisor_sessions(current_user: User = Depends(get_current_user)):
    """Get sessions for supervisor to view reports"""
    if current_user.role not in ["supervisor", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if current_user.role == "supervisor":
        query["supervisor_ids"] = current_user.id
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(100)
    
    result = []
    for session in sessions:
        report = await db.training_reports.find_one({"session_id": session["id"]}, {"_id": 0})
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0})
        
        result.append({
            "session": session,
            "company_name": company.get("name") if company else "Unknown",
            "has_report": bool(report),
            "report_status": report.get("status") if report else None
        })
    
    return result


@router.post("/{session_id}/generate-ai-report")
async def generate_ai_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Generate AI training report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can generate reports")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    program = await db.programs.find_one({"id": session['program_id']}, {"_id": 0})
    company = await db.companies.find_one({"id": session['company_id']}, {"_id": 0})
    
    # Get participant results
    participant_ids = session.get('participant_ids', [])
    test_results = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    feedback = await db.course_feedback.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    
    # Calculate statistics
    pre_scores = [r['score'] for r in test_results if r.get('test_type') in ['pre', 'pre_test']]
    post_scores = [r['score'] for r in test_results if r.get('test_type') in ['post', 'post_test']]
    
    avg_pre = sum(pre_scores) / len(pre_scores) if pre_scores else 0
    avg_post = sum(post_scores) / len(post_scores) if post_scores else 0
    improvement = avg_post - avg_pre
    
    # Simple AI-generated content (placeholder - would use LLM in production)
    ai_content = f"""
Training Report Summary

Program: {program.get('name', 'Unknown') if program else 'Unknown'}
Company: {company.get('name', 'Unknown') if company else 'Unknown'}
Location: {session.get('location', 'N/A')}
Dates: {session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')}

Participants: {len(participant_ids)}
Pre-Test Average: {avg_pre:.1f}%
Post-Test Average: {avg_post:.1f}%
Improvement: {improvement:+.1f}%

Feedback Submissions: {len(feedback)}

This report was automatically generated.
"""
    
    # Save to database
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {"ai_generated_content": ai_content, "updated_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    
    return {"message": "AI report generated", "content": ai_content}


@router.post("/{session_id}/generate-docx")
async def generate_docx(session_id: str, current_user: User = Depends(get_current_user)):
    """Generate DOCX report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can generate reports")
    
    # Placeholder - would generate actual DOCX
    return {"message": "DOCX generation not implemented in modular version", "session_id": session_id}


@router.get("/{session_id}/download-docx")
async def download_docx(session_id: str, current_user: User = Depends(get_current_user)):
    """Download DOCX report"""
    if current_user.role not in ["admin", "super_admin", "coordinator", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    if not report or not report.get("docx_url"):
        raise HTTPException(status_code=404, detail="DOCX report not found")
    
    filename = report["docx_url"].split('/')[-1]
    file_path = REPORT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=f"report_{session_id}.docx")


@router.post("/{session_id}/upload-edited-docx")
async def upload_edited_docx(session_id: str, file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload edited DOCX report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can upload reports")
    
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only DOCX files are accepted")
    
    filename = f"{session_id}_edited_{uuid.uuid4().hex[:8]}.docx"
    file_path = REPORT_DIR / filename
    
    with open(file_path, "wb") as buffer:  # noqa: ephemeral-upload-storage
        shutil.copyfileobj(file.file, buffer)
    
    docx_url = f"/api/static/reports/{filename}"
    
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {"docx_url": docx_url, "updated_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    
    return {"message": "DOCX uploaded", "docx_url": docx_url}


@router.post("/{session_id}/upload-final-pdf")
async def upload_final_pdf(session_id: str, file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload final PDF report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can upload reports")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    filename = f"{session_id}_final_{uuid.uuid4().hex[:8]}.pdf"
    file_path = REPORT_PDF_DIR / filename
    
    with open(file_path, "wb") as buffer:  # noqa: ephemeral-upload-storage
        shutil.copyfileobj(file.file, buffer)
    
    pdf_url = f"/api/static/reports_pdf/{filename}"
    
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {"pdf_url": pdf_url, "updated_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    
    return {"message": "PDF uploaded", "pdf_url": pdf_url}


@router.post("/{session_id}/submit-final")
async def submit_final_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Submit final report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can submit reports")
    
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {"status": "submitted", "submitted_at": get_malaysia_time().isoformat()}}
    )
    
    return {"message": "Report submitted successfully"}


@router.get("/{session_id}/download-pdf")
async def download_pdf(session_id: str, current_user: User = Depends(get_current_user)):
    """Download PDF report"""
    if current_user.role not in ["admin", "super_admin", "coordinator", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    if not report or not report.get("pdf_url"):
        raise HTTPException(status_code=404, detail="PDF report not found")
    
    filename = report["pdf_url"].split('/')[-1]
    file_path = REPORT_PDF_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(file_path, media_type="application/pdf", filename=f"report_{session_id}.pdf")


@router.get("/{session_id}/status")
async def get_training_report_status(session_id: str, current_user=Depends(get_current_user)):
    """Get the status of a training report for a session"""
    if current_user.role not in ["coordinator", "admin", "supervisor"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})

    if not training_report:
        return {
            "docx_generated": False,
            "edited_uploaded": False,
            "pdf_submitted": False,
            "docx_filename": None,
            "edited_docx_filename": None,
            "pdf_filename": None,
            "status": None
        }

    return {
        "docx_generated": bool(training_report.get('docx_filename')),
        "edited_uploaded": bool(training_report.get('edited_docx_filename')),
        "pdf_submitted": training_report.get('status') == 'submitted',
        "docx_filename": training_report.get('docx_filename'),
        "edited_docx_filename": training_report.get('edited_docx_filename'),
        "pdf_filename": training_report.get('final_pdf_filename'),
        "status": training_report.get('status')
    }

