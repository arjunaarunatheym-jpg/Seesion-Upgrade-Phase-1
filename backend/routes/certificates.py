"""
Certificates routes - Certificate management and generation
Endpoints: 10
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from typing import List
from datetime import datetime
from pathlib import Path
import uuid
import shutil

from core import db, get_current_user, get_malaysia_time
from models import User

from pydantic import BaseModel, Field, ConfigDict

# Paths
STATIC_DIR = Path(__file__).parent.parent / "static"
CERTIFICATE_DIR = STATIC_DIR / "certificates"
CERTIFICATE_DIR.mkdir(parents=True, exist_ok=True)
CERTIFICATE_PDF_DIR = STATIC_DIR / "certificates_pdf"
CERTIFICATE_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Models
class Certificate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    participant_id: str
    certificate_number: str
    file_path: Optional[str] = None
    issue_date: datetime = Field(default_factory=get_malaysia_time)

from typing import Optional

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("/participant/{participant_id}")
async def get_participant_certificates(participant_id: str, current_user: User = Depends(get_current_user)):
    """Get certificates for a specific participant"""
    if current_user.role == "participant" and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    certificates = await db.certificates.find({"participant_id": participant_id}, {"_id": 0}).to_list(100)
    for cert in certificates:
        if isinstance(cert.get('issue_date'), str):
            cert['issue_date'] = datetime.fromisoformat(cert['issue_date'])
    return certificates


@router.get("/my-certificates")
async def get_my_certificates(current_user: User = Depends(get_current_user)):
    """Get certificates for the current logged-in user (participant)"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can access this endpoint")
    
    certificates = await db.certificates.find({"participant_id": current_user.id}, {"_id": 0}).to_list(100)
    for cert in certificates:
        if isinstance(cert.get('issue_date'), str):
            cert['issue_date'] = datetime.fromisoformat(cert['issue_date'])
    return certificates


@router.get("/session/{session_id}")
async def get_session_certificates(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all certificates for a session"""
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can access certificates")
    
    access_records = await db.participant_access.find(
        {"session_id": session_id, "certificate_url": {"$exists": True, "$ne": None}},
        {"_id": 0}
    ).to_list(1000)
    
    certificates = []
    for access in access_records:
        if access.get('certificate_url'):
            certificates.append({
                "participant_id": access.get('participant_id'),
                "file_path": access.get('certificate_url'),
                "certificate_url": access.get('certificate_url'),
                "uploaded_at": access.get('certificate_uploaded_at'),
                "uploaded_by": access.get('certificate_uploaded_by')
            })
    
    return certificates


@router.get("/repository")
async def get_certificate_repository(current_user: User = Depends(get_current_user)):
    """Get all certificates (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    certificates = await db.certificates.find({}, {"_id": 0}).to_list(1000)
    
    for cert in certificates:
        if isinstance(cert.get('issue_date'), str):
            cert['issue_date'] = datetime.fromisoformat(cert['issue_date'])
        
        if cert.get("participant_id"):
            user = await db.users.find_one({"id": cert["participant_id"]}, {"_id": 0, "full_name": 1})
            cert["participant_name"] = user.get("full_name") if user else "Unknown"
        
        if cert.get("session_id"):
            session = await db.sessions.find_one({"id": cert["session_id"]}, {"_id": 0, "name": 1})
            cert["session_name"] = session.get("name") if session else "Unknown"
    
    return certificates


@router.post("/upload/{session_id}/{participant_id}")
async def upload_participant_certificate(
    session_id: str,
    participant_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload certificate PDF for a specific participant"""
    if current_user.role == "coordinator":
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.get("coordinator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only upload certificates for your assigned sessions")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only coordinators and admins can upload certificates")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    settings = await db.settings.find_one({"id": "app_settings"}, {"_id": 0})
    max_size_mb = settings.get('max_certificate_file_size_mb', 5) if settings else 5
    max_size_bytes = max_size_mb * 1024 * 1024
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > max_size_bytes:
        raise HTTPException(status_code=400, detail=f"File size exceeds maximum allowed size of {max_size_mb}MB")
    
    unique_filename = f"{session_id}_{participant_id}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = CERTIFICATE_PDF_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    certificate_url = f"/api/static/certificates_pdf/{unique_filename}"
    
    await db.participant_access.update_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"$set": {
            "certificate_url": certificate_url,
            "certificate_uploaded_at": get_malaysia_time().isoformat(),
            "certificate_uploaded_by": current_user.id
        }},
        upsert=True
    )
    
    return {
        "certificate_url": certificate_url,
        "message": "Certificate uploaded successfully",
        "file_size_mb": round(file_size / (1024 * 1024), 2)
    }


@router.get("/eligibility/{session_id}/{participant_id}")
async def check_certificate_eligibility(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    """Check if participant is eligible for certificate"""
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    access = await db.participant_access.find_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"_id": 0}
    )
    
    attendance = await db.attendance.find_one(
        {"participant_id": participant_id, "session_id": session_id, "clock_out": {"$ne": None}},
        {"_id": 0}
    )
    
    post_test = await db.test_results.find_one(
        {"participant_id": participant_id, "session_id": session_id, "test_type": {"$in": ["post", "post_test"]}},
        {"_id": 0}
    )
    
    feedback = await db.course_feedback.find_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"_id": 0}
    )
    
    return {
        "eligible": all([attendance, post_test and post_test.get("passed"), feedback]),
        "clocked_out": bool(attendance),
        "post_test_passed": bool(post_test and post_test.get("passed")),
        "feedback_submitted": bool(feedback),
        "certificate_uploaded": bool(access and access.get("certificate_url"))
    }


@router.post("/generate/{session_id}/{participant_id}")
async def generate_certificate(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    """Generate a certificate for a participant"""
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can generate certificates")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant = await db.users.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Generate certificate number
    year = datetime.now().year
    count = await db.certificates.count_documents({"certificate_number": {"$regex": f"^CERT{year}"}})
    certificate_number = f"CERT{year}{str(count + 1).zfill(5)}"
    
    certificate = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "participant_id": participant_id,
        "certificate_number": certificate_number,
        "participant_name": participant.get("full_name"),
        "session_name": session.get("name"),
        "program_id": session.get("program_id"),
        "issue_date": get_malaysia_time().isoformat(),
        "generated_by": current_user.id
    }
    
    await db.certificates.insert_one(certificate)
    
    return {"message": "Certificate generated", "certificate": certificate}


@router.get("/download/{certificate_id}")
async def download_certificate_by_id(certificate_id: str, current_user: User = Depends(get_current_user)):
    """Download certificate by certificate ID"""
    certificate = await db.certificates.find_one({"id": certificate_id}, {"_id": 0})
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    if current_user.role == "participant" and current_user.id != certificate.get("participant_id"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    file_path = certificate.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Certificate file not found")
    
    filename = file_path.split('/')[-1]
    full_path = CERTIFICATE_PDF_DIR / filename
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found on disk")
    
    return FileResponse(full_path, media_type="application/pdf", filename=f"certificate_{certificate_id}.pdf")


@router.get("/download/{session_id}/{participant_id}")
async def download_participant_certificate(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    """Download certificate for a participant in a session"""
    if current_user.id != participant_id and current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    access = await db.participant_access.find_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"_id": 0}
    )
    
    if not access or not access.get('certificate_url'):
        raise HTTPException(status_code=404, detail="No certificate uploaded for this participant")
    
    if current_user.id == participant_id:
        feedback_done = access.get('feedback_submitted', False) or access.get('feedback_completed', False)
        if not feedback_done:
            raise HTTPException(status_code=403, detail="Certificate not available. Please submit your feedback first.")
        
        attendance = await db.attendance.find_one(
            {"participant_id": participant_id, "session_id": session_id, "clock_out": {"$ne": None}},
            {"_id": 0}
        )
        if not attendance:
            raise HTTPException(status_code=403, detail="Certificate not available. Please clock out first.")
    
    filename = access['certificate_url'].split('/')[-1]
    file_path = CERTIFICATE_PDF_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found")
    
    participant = await db.users.find_one({"id": participant_id}, {"_id": 0})
    participant_name = participant.get('full_name', 'participant').replace(' ', '_') if participant else 'participant'
    
    return FileResponse(file_path, media_type="application/pdf", filename=f"{participant_name}_certificate.pdf")


@router.get("/preview/{certificate_id}")
async def preview_certificate(certificate_id: str, current_user: User = Depends(get_current_user)):
    """Preview certificate (returns certificate data)"""
    certificate = await db.certificates.find_one({"id": certificate_id}, {"_id": 0})
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    if isinstance(certificate.get('issue_date'), str):
        certificate['issue_date'] = datetime.fromisoformat(certificate['issue_date'])
    
    return certificate
