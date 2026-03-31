"""
Settings routes - Application configuration endpoints
Endpoints: 11
- GET /settings
- PUT /settings  
- POST /settings/upload-logo
- POST /settings/upload-certificate-template
- GET /settings/certificate-templates
- GET /settings/certificate-templates/{template_id}
- POST /settings/certificate-templates
- PUT /settings/certificate-templates/{template_id}
- DELETE /settings/certificate-templates/{template_id}
- POST /settings/certificate-assets
- GET /static/certificate_assets/{filename}
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from datetime import datetime
from typing import List
from pathlib import Path
import shutil
import uuid

from core import db, get_current_user, get_malaysia_time, LOGO_DIR, TEMPLATE_DIR, ROOT_DIR
from models import User, Settings, SettingsUpdate

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=Settings)
async def get_settings():
    """Get application settings"""
    settings = await db.settings.find_one({"id": "app_settings"}, {"_id": 0})
    if not settings:
        default_settings = Settings()
        doc = default_settings.model_dump()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.settings.insert_one(doc)
        return default_settings
    
    if isinstance(settings.get('updated_at'), str):
        settings['updated_at'] = datetime.fromisoformat(settings['updated_at'])
    return Settings(**settings)


@router.put("/settings", response_model=Settings)
async def update_settings(settings_data: SettingsUpdate, current_user: User = Depends(get_current_user)):
    """Update application settings (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update settings")
    
    update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
    update_data['updated_at'] = get_malaysia_time().isoformat()
    
    await db.settings.update_one(
        {"id": "app_settings"},
        {"$set": update_data},
        upsert=True
    )
    
    settings = await db.settings.find_one({"id": "app_settings"}, {"_id": 0})
    if isinstance(settings.get('updated_at'), str):
        settings['updated_at'] = datetime.fromisoformat(settings['updated_at'])
    return Settings(**settings)


@router.post("/settings/upload-logo")
async def upload_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload company logo (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update settings")
    
    file_ext = file.filename.split(".")[-1]
    filename = f"logo.{file_ext}"
    file_path = LOGO_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logo_url = f"/api/static/logos/{filename}"
    
    await db.settings.update_one(
        {"id": "app_settings"},
        {"$set": {"logo_url": logo_url, "updated_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    
    return {"logo_url": logo_url}


@router.post("/settings/upload-certificate-template")
async def upload_certificate_template(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload certificate template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can upload templates")
    
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    
    filename = "certificate_template.docx"
    file_path = TEMPLATE_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    template_url = f"/api/static/templates/{filename}"
    
    await db.settings.update_one(
        {"id": "app_settings"},
        {"$set": {"certificate_template_url": template_url, "updated_at": get_malaysia_time().isoformat()}},
        upsert=True
    )
    
    return {"template_url": template_url, "message": "Certificate template uploaded successfully"}


# ==================== CERTIFICATE TEMPLATE DESIGNER ====================

@router.get("/settings/certificate-templates")
async def get_certificate_templates(current_user: User = Depends(get_current_user)):
    """Get all saved certificate templates"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can access certificate templates")
    
    templates = await db.certificate_templates.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return templates


@router.get("/settings/certificate-templates/{template_id}")
async def get_certificate_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific certificate template"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can access certificate templates")
    
    template = await db.certificate_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/settings/certificate-templates")
async def save_certificate_template(template_data: dict, current_user: User = Depends(get_current_user)):
    """Save a new certificate template"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can save certificate templates")
    
    template = {
        "id": str(uuid.uuid4()),
        "name": template_data.get("name", "Untitled Template"),
        "background": template_data.get("background"),
        "backgroundColor": template_data.get("backgroundColor"),
        "borderStyle": template_data.get("borderStyle"),
        "elements": template_data.get("elements", []),
        "is_default": template_data.get("is_default", False),
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat(),
        "updated_at": get_malaysia_time().isoformat()
    }
    
    # If this is set as default, unset other defaults
    if template["is_default"]:
        await db.certificate_templates.update_many(
            {"is_default": True},
            {"$set": {"is_default": False}}
        )
    
    await db.certificate_templates.insert_one(template)
    template.pop("_id", None)
    
    return {"message": "Template saved", "template": template}


@router.put("/settings/certificate-templates/{template_id}")
async def update_certificate_template(template_id: str, template_data: dict, current_user: User = Depends(get_current_user)):
    """Update an existing certificate template"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can update certificate templates")
    
    existing = await db.certificate_templates.find_one({"id": template_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_fields = {
        "name": template_data.get("name", existing.get("name")),
        "background": template_data.get("background", existing.get("background")),
        "backgroundColor": template_data.get("backgroundColor", existing.get("backgroundColor")),
        "borderStyle": template_data.get("borderStyle", existing.get("borderStyle")),
        "elements": template_data.get("elements", existing.get("elements")),
        "is_default": template_data.get("is_default", existing.get("is_default")),
        "updated_at": get_malaysia_time().isoformat()
    }
    
    # If this is set as default, unset other defaults
    if update_fields["is_default"]:
        await db.certificate_templates.update_many(
            {"is_default": True, "id": {"$ne": template_id}},
            {"$set": {"is_default": False}}
        )
    
    await db.certificate_templates.update_one({"id": template_id}, {"$set": update_fields})
    
    return {"message": "Template updated"}


@router.delete("/settings/certificate-templates/{template_id}")
async def delete_certificate_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Delete a certificate template"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can delete certificate templates")
    
    result = await db.certificate_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted"}


@router.post("/settings/certificate-assets")
async def upload_certificate_asset(
    file: UploadFile = File(...), 
    type: str = Form("logo"),
    current_user: User = Depends(get_current_user)
):
    """Upload logo or signature image for certificate template"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can upload certificate assets")
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")
    
    # Create directory if not exists
    asset_dir = ROOT_DIR / "static" / "certificate_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"{type}_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = asset_dir / filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    url = f"/api/static/certificate_assets/{filename}"
    
    return {"url": url, "filename": filename}


@router.get("/static/certificate_assets/{filename}")
async def get_certificate_asset(filename: str):
    """Serve certificate asset files"""
    file_path = ROOT_DIR / "static" / "certificate_assets" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(file_path)


# Indemnity Sections Management
@router.get("/settings/indemnity-sections")
async def get_indemnity_sections():
    """Get custom indemnity sections (public - for participant form)"""
    sections = await db.indemnity_sections.find({}, {"_id": 0}).sort("order", 1).to_list(None)
    return sections


@router.post("/settings/indemnity-sections")
async def save_indemnity_sections(sections: List[dict], current_user: User = Depends(get_current_user)):
    """Save custom indemnity sections (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can manage indemnity sections")
    await db.indemnity_sections.delete_many({})
    for idx, section in enumerate(sections):
        section["order"] = idx
        section["updated_at"] = get_malaysia_time().isoformat()
        await db.indemnity_sections.insert_one(section)
    return {"message": f"Saved {len(sections)} indemnity sections"}


# Feedback Questions Management (Admin)
@router.get("/settings/feedback-questions")
async def get_feedback_questions():
    """Get participant feedback questions (public - for participant form)"""
    questions = await db.feedback_questions.find({}, {"_id": 0}).sort("order", 1).to_list(None)
    if not questions:
        return [
            {"id": "A1", "order": 1, "category": "KUALITI KURSUS", "question": "Penganjur menepati jangkaan saya", "type": "rating", "required": True},
            {"id": "A2", "order": 2, "category": "KUALITI KURSUS", "question": "Kandungan kursus adalah jelas dan mudah difahami", "type": "rating", "required": True},
            {"id": "A3", "order": 3, "category": "KUALITI KURSUS", "question": "Hasil pembelajaran adalah selari dengan objektif dan penyampaian kursus", "type": "rating", "required": True},
            {"id": "A4", "order": 4, "category": "KUALITI KURSUS", "question": "Bahan pembelajaran sangat jelas, tepat, sangat mencukupi dan membantu", "type": "rating", "required": True},
            {"id": "A5", "order": 5, "category": "KUALITI KURSUS", "question": "Tempoh kursus adalah mencukupi", "type": "rating", "required": True},
            {"id": "A6", "order": 6, "category": "KUALITI KURSUS", "question": "Keseluruhannya, saya berpuas hati dengan kandungan kursus ini dan akan mencadangkan kursus ini kepada rakan sekerja saya", "type": "rating", "required": True},
            {"id": "A7", "order": 7, "category": "KUALITI KURSUS", "question": "Cadangan atau Pandangan anda mengenai KUALITI KURSUS", "type": "text", "required": False},
            {"id": "B1", "order": 8, "category": "PENYEDIA LATIHAN", "question": "Latihan telah disusun dan dilaksanakan dengan baik", "type": "rating", "required": True},
            {"id": "B2", "order": 9, "category": "PENYEDIA LATIHAN", "question": "Persekitaran kelas adalah kondusif untuk pembelajaran dan membolehkan saya belajar", "type": "rating", "required": True},
            {"id": "B3", "order": 10, "category": "PENYEDIA LATIHAN", "question": "Saya yakin dengan kebolehan saya mengaplikasikan kemahiran yang telah saya pelajari daripada latihan", "type": "rating", "required": True},
            {"id": "B4", "order": 11, "category": "PENYEDIA LATIHAN", "question": "Secara keseluruhannya, saya berpuas hati dengan penganjur/penyedia latihan", "type": "rating", "required": True},
            {"id": "B5", "order": 12, "category": "PENYEDIA LATIHAN", "question": "Cadangan atau Pandangan anda mengenai PENYEDIA LATIHAN / PENGANJUR / KESELURUHAN", "type": "text", "required": False},
            {"id": "C1", "order": 13, "category": "TRAINER", "question": "Trainer dapat menarik minat peserta dan membuatkan saya berminat dengan subjek latihan", "type": "rating", "required": True},
            {"id": "C2", "order": 14, "category": "TRAINER", "question": "Trainer mempunyai pemahaman yang mendalam tentang subjek yang diajar", "type": "rating", "required": True},
            {"id": "C3", "order": 15, "category": "TRAINER", "question": "Trainer mempunyai ilmu terkini tentang perkembangan terkini dalam subjek", "type": "rating", "required": True},
            {"id": "C4", "order": 16, "category": "TRAINER", "question": "Trainer menggunakan teknologi untuk menjadikan pembelajaran lebih menarik dan interaktif", "type": "rating", "required": True},
            {"id": "C5", "order": 17, "category": "TRAINER", "question": "Secara keseluruhannya, saya berpuas hati dengan trainer", "type": "rating", "required": True},
            {"id": "C6", "order": 18, "category": "TRAINER", "question": "Cadangan atau Pandangan anda mengenai TRAINER/PENCERAMAH/PAKAR", "type": "text", "required": False},
            {"id": "D1", "order": 19, "category": "UMUM", "question": "Sila nyatakan pandangan atau cadangan anda bagi memperbaiki perkhidmatan kami", "type": "text", "required": False},
        ]
    return questions


@router.post("/settings/feedback-questions")
async def save_feedback_questions(questions: List[dict], current_user: User = Depends(get_current_user)):
    """Save feedback questions (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can manage feedback questions")
    await db.feedback_questions.delete_many({})
    for idx, question in enumerate(questions):
        question["order"] = idx + 1
        question["updated_at"] = get_malaysia_time().isoformat()
        if "id" not in question or not question["id"]:
            question["id"] = f"Q{idx+1}"
        await db.feedback_questions.insert_one(question)
    return {"message": f"Saved {len(questions)} feedback questions"}

