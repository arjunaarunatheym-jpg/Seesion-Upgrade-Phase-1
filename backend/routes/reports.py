"""
Training report routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List

from models import TrainingReport, ReportGenerateRequest
from services.auth_service import get_current_user
from utils import db

router = APIRouter(prefix="/training-reports", tags=["reports"])


@router.get("/coordinator", response_model=List[TrainingReport])
async def get_coordinator_reports(current_user = Depends(get_current_user)):
    """Get reports for current coordinator"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    query = {"coordinator_id": current_user.id} if current_user.role == "coordinator" else {}
    reports = await db.training_reports.find(query, {"_id": 0}).to_list(1000)
    
    from datetime import datetime
    for report in reports:
        if isinstance(report.get('created_at'), str):
            report['created_at'] = datetime.fromisoformat(report['created_at'])
        
        # Enrich with session data
        if report.get('session_id'):
            session = await db.sessions.find_one({"id": report['session_id']}, {"_id": 0})
            if session:
                report['session_name'] = session.get('name')
                
                if session.get('company_id'):
                    company = await db.companies.find_one({"id": session['company_id']}, {"_id": 0})
                    report['company_name'] = company.get('name') if company else "Unknown"
                
                if session.get('program_id'):
                    program = await db.programs.find_one({"id": session['program_id']}, {"_id": 0})
                    report['program_name'] = program.get('name') if program else "Unknown"
    
    return reports


@router.get("/admin/all", response_model=List[TrainingReport])
async def get_all_reports(current_user = Depends(get_current_user)):
    """Get all reports (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access all reports")
    
    reports = await db.training_reports.find({}, {"_id": 0}).to_list(1000)
    from datetime import datetime
    for report in reports:
        if isinstance(report.get('created_at'), str):
            report['created_at'] = datetime.fromisoformat(report['created_at'])
    return reports


@router.post("/generate")
async def generate_report(request: ReportGenerateRequest, current_user = Depends(get_current_user)):
    """Generate training report for a session"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    from models import TrainingReport
    
    # Check if report already exists
    existing = await db.training_reports.find_one({
        "session_id": request.session_id,
        "coordinator_id": current_user.id
    }, {"_id": 0})
    
    if existing:
        return {"message": "Report already exists", "report_id": existing['id']}
    
    report_obj = TrainingReport(
        session_id=request.session_id,
        coordinator_id=current_user.id
    )
    doc = report_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.training_reports.insert_one(doc)
    
    return {"message": "Report generated", "report_id": report_obj.id}


@router.get("/session/{session_id}", response_model=TrainingReport)
async def get_session_report(session_id: str, current_user = Depends(get_current_user)):
    """Get report for a specific session"""
    if current_user.role not in ["admin", "super_admin", "coordinator", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    from datetime import datetime
    if isinstance(report.get('created_at'), str):
        report['created_at'] = datetime.fromisoformat(report['created_at'])
    
    return TrainingReport(**report)


@router.post("/{session_id}/generate-docx")
async def generate_docx_report(session_id: str, current_user = Depends(get_current_user)):
    """Generate DOCX training report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Implementation from old server - placeholder for now
    return {"message": "DOCX report generation endpoint", "session_id": session_id}


@router.get("/{session_id}/download-docx")
async def download_docx_report(session_id: str, current_user = Depends(get_current_user)):
    """Download DOCX report"""
    if current_user.role not in ["admin", "super_admin", "coordinator", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    from fastapi.responses import FileResponse
    import os
    
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    docx_path = report.get("docx_path")
    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(status_code=404, detail="DOCX file not found")
    
    return FileResponse(docx_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=os.path.basename(docx_path))


@router.post("/{session_id}/upload-edited-docx")
async def upload_edited_docx(
    session_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload edited DOCX report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Save uploaded file
    from pathlib import Path
    REPORT_DIR = Path(__file__).parent.parent / "static" / "reports"
    REPORT_DIR.mkdir(exist_ok=True)
    
    file_path = REPORT_DIR / f"edited_{session_id}.docx"
    contents = await file.read()
    
    with open(file_path, 'wb') as f:
        f.write(contents)
    
    # Update report
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {"docx_path": str(file_path)}}
    )
    
    return {"message": "Edited DOCX uploaded successfully"}


@router.post("/{session_id}/upload-final-pdf")
async def upload_final_pdf(
    session_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload final PDF report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    from pathlib import Path
    REPORT_PDF_DIR = Path(__file__).parent.parent / "static" / "reports_pdf"
    REPORT_PDF_DIR.mkdir(exist_ok=True)
    
    file_path = REPORT_PDF_DIR / f"final_{session_id}.pdf"
    contents = await file.read()
    
    with open(file_path, 'wb') as f:
        f.write(contents)
    
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {"pdf_path": str(file_path), "status": "submitted"}}
    )
    
    return {"message": "Final PDF uploaded successfully", "pdf_path": str(file_path)}


@router.get("/{session_id}/download-pdf")
async def download_pdf_report(session_id: str, current_user = Depends(get_current_user)):
    """Download PDF report"""
    if current_user.role not in ["admin", "super_admin", "coordinator", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    from fastapi.responses import FileResponse
    import os
    
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    pdf_path = report.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path))


@router.post("/{session_id}/submit-final")
async def submit_final_report(session_id: str, current_user = Depends(get_current_user)):
    """Submit final report"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    from utils import get_malaysia_time
    
    await db.training_reports.update_one(
        {"session_id": session_id},
        {"$set": {
            "status": "submitted",
            "submitted_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Report submitted successfully"}
