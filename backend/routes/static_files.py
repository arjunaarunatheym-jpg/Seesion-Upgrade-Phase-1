"""
Static Files routes - File serving and upload endpoints
Endpoints: 9
- GET /static/logos/{filename}
- GET /static/certificates/{filename}
- GET /static/certificates_pdf/{filename}
- GET /static/templates/{filename}
- GET /static/checklist-photos/{filename}
- POST /checklist-photos/upload
- GET /uploads/company/{filename}
- GET /uploads/indemnity/{filename}
- GET /debug/database-info
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
import uuid
import shutil
import os

from core import (
    db, get_current_user,
    LOGO_DIR, CERTIFICATE_DIR, CERTIFICATE_PDF_DIR,
    TEMPLATE_DIR, CHECKLIST_PHOTOS_DIR
)
from models import User

db_name = os.environ.get('DB_NAME', 'unknown')

router = APIRouter(tags=["static_files"])


@router.get("/static/logos/{filename}")
async def get_logo(filename: str):
    file_path = LOGO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(file_path)


@router.get("/static/certificates/{filename}")
async def get_certificate(filename: str):
    file_path = CERTIFICATE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate not found")
    return FileResponse(file_path)


@router.get("/static/certificates_pdf/{filename}")
async def get_certificate_pdf(filename: str):
    file_path = CERTIFICATE_PDF_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate PDF not found")
    return FileResponse(
        file_path,
        media_type='application/pdf',
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "X-Content-Type-Options": "nosniff"
        }
    )


@router.get("/static/templates/{filename}")
async def get_template(filename: str):
    file_path = TEMPLATE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return FileResponse(file_path)


@router.get("/static/docs/{filename}")
async def get_doc(filename: str):
    from pathlib import Path
    docs_dir = Path(__file__).parent.parent / "static" / "docs"
    file_path = docs_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(file_path, filename=filename)


@router.post("/checklist-photos/upload")
async def upload_checklist_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can upload checklist photos")

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    file_extension = file.filename.split('.')[-1]
    filename = f"{str(uuid.uuid4())}.{file_extension}"
    file_path = CHECKLIST_PHOTOS_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    photo_url = f"/api/static/checklist-photos/{filename}"
    return {"photo_url": photo_url}


@router.get("/static/checklist-photos/{filename}")
async def get_checklist_photo(filename: str):
    file_path = CHECKLIST_PHOTOS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(file_path)


@router.get("/uploads/company/{filename}")
async def get_company_file(filename: str):
    """Serve uploaded company files"""
    file_path = f"uploads/company/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    content_type = content_types.get(ext, 'application/octet-stream')

    return FileResponse(file_path, media_type=content_type, filename=filename)


@router.get("/uploads/indemnity/{filename}")
async def get_indemnity_file(filename: str):
    """Serve uploaded indemnity form file"""
    file_path = f"uploads/indemnity/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    content_type = "application/pdf"
    if filename.lower().endswith('.doc'):
        content_type = "application/msword"
    elif filename.lower().endswith('.docx'):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(file_path, media_type=content_type, filename=filename)


@router.get("/debug/database-info")
async def get_database_info(current_user: User = Depends(get_current_user)):
    """Debug endpoint to check which database is being used"""
    users_count = await db.users.count_documents({})
    tests_count = await db.tests.count_documents({})
    sessions_count = await db.sessions.count_documents({})
    test_results_count = await db.test_results.count_documents({})

    return {
        "db_name": db_name,
        "collections": {
            "users": users_count,
            "tests": tests_count,
            "sessions": sessions_count,
            "test_results": test_results_count
        }
    }
