from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from passlib.context import CryptContext
import jwt
import random
import shutil
import subprocess
from docx import Document
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import asyncio
import re
import html
from collections import defaultdict
import time
import hashlib
from io import BytesIO
from fpdf import FPDF

# ==================== SECURITY CONFIGURATION ====================
# Rate limiting storage (in-memory, consider Redis for production)
rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 500  # Max requests per window (increased for training sessions with 50+ participants)
RATE_LIMIT_WINDOW = 60  # Window in seconds
BLOCKED_IPS = set()  # Manually blocked IPs
FAILED_LOGIN_ATTEMPTS = defaultdict(list)
MAX_FAILED_LOGINS = 10  # Max failed attempts before lockout (increased for shared IPs)
LOGIN_LOCKOUT_TIME = 180  # Lockout time in seconds (3 minutes, reduced from 5)

# Security patterns to detect malicious input
MALICIOUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',  # XSS script tags
    r'javascript:',  # JavaScript protocol
    r'on\w+\s*=',  # Event handlers (onclick, onerror, etc.)
    r'\$where',  # MongoDB injection
    r'\$gt|\$lt|\$ne|\$eq|\$regex',  # MongoDB operators in strings
    r';\s*drop\s+',  # SQL-like injection attempts
    r';\s*delete\s+',
    r'union\s+select',
    r'exec\s*\(',  # Code execution attempts
    r'eval\s*\(',
    r'__proto__',  # Prototype pollution
    r'constructor\s*\[',
]

def is_malicious_input(value: str) -> bool:
    """Check if input contains malicious patterns"""
    if not isinstance(value, str):
        return False
    value_lower = value.lower()
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, value_lower, re.IGNORECASE):
            return True
    return False

def sanitize_input(value):
    """Sanitize input to prevent XSS and injection attacks"""
    if isinstance(value, str):
        # HTML escape
        value = html.escape(value)
        # Remove null bytes
        value = value.replace('\x00', '')
        # Limit length to prevent DoS
        if len(value) > 50000:
            value = value[:50000]
    elif isinstance(value, dict):
        return {k: sanitize_input(v) for k, v in value.items() if not k.startswith('$')}
    elif isinstance(value, list):
        return [sanitize_input(v) for v in value]
    return value

def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit"""
    current_time = time.time()
    # Clean old entries
    rate_limit_storage[ip] = [t for t in rate_limit_storage[ip] if current_time - t < RATE_LIMIT_WINDOW]
    
    if len(rate_limit_storage[ip]) >= RATE_LIMIT_REQUESTS:
        return False  # Rate limited
    
    rate_limit_storage[ip].append(current_time)
    return True

def check_login_lockout(ip: str) -> tuple[bool, int]:
    """Check if IP is locked out due to failed logins. Returns (is_locked, remaining_seconds)"""
    current_time = time.time()
    # Clean old entries
    FAILED_LOGIN_ATTEMPTS[ip] = [t for t in FAILED_LOGIN_ATTEMPTS[ip] if current_time - t < LOGIN_LOCKOUT_TIME]
    
    if len(FAILED_LOGIN_ATTEMPTS[ip]) >= MAX_FAILED_LOGINS:
        oldest = min(FAILED_LOGIN_ATTEMPTS[ip])
        remaining = int(LOGIN_LOCKOUT_TIME - (current_time - oldest))
        return True, max(0, remaining)
    return False, 0

def record_failed_login(ip: str):
    """Record a failed login attempt"""
    FAILED_LOGIN_ATTEMPTS[ip].append(time.time())

def clear_failed_logins(ip: str):
    """Clear failed login attempts after successful login"""
    FAILED_LOGIN_ATTEMPTS[ip] = []


# ==================== SECURITY MIDDLEWARE ====================
class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if IP is blocked
        if client_ip in BLOCKED_IPS:
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"}
            )
        
        # Rate limiting (skip for health checks)
        if not request.url.path.endswith('/health'):
            if not check_rate_limit(client_ip):
                logging.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."}
                )
        
        # Add security headers to response
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        
        return response


# Malaysian Timezone (UTC+8)
MALAYSIA_TZ = ZoneInfo("Asia/Kuala_Lumpur")

def get_malaysia_time():
    """Get current time in Malaysian timezone"""
    return datetime.now(MALAYSIA_TZ)

def get_malaysia_date():
    """Get current date in Malaysian timezone"""
    return get_malaysia_time().date()

def get_malaysia_time_str():
    """Get current time as string in HH:MM:SS format (Malaysian timezone)"""
    return get_malaysia_time().strftime("%H:%M:%S")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection with production-ready settings
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=20000
)
db_name = os.environ.get('DB_NAME')
if not db_name:
    raise ValueError("DB_NAME environment variable is required")
db = client[db_name]
print(f"🔥🔥🔥 CONNECTED TO DATABASE: {db_name} 🔥🔥🔥")
logging.info(f"🔥🔥🔥 CONNECTED TO DATABASE: {db_name} 🔥🔥🔥")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY or SECRET_KEY == 'your-secret-key-change-in-production':
    raise ValueError("SECRET_KEY environment variable must be set to a secure random value")
ALGORITHM = "HS256"

# ==================== FILE UPLOAD SECURITY ====================
ALLOWED_FILE_EXTENSIONS = {
    'documents': {'.xlsx', '.xls', '.csv', '.docx', '.doc', '.pdf', '.txt'},
    'images': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'},
    'all': {'.xlsx', '.xls', '.csv', '.docx', '.doc', '.pdf', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max
DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.sh', '.ps1', '.vbs', '.js', '.jar', '.msi', '.dll', '.scr', '.pif'}

# Magic bytes for file type verification
FILE_SIGNATURES = {
    b'\x50\x4b\x03\x04': ['xlsx', 'docx', 'zip'],  # ZIP-based formats
    b'\xd0\xcf\x11\xe0': ['xls', 'doc'],  # OLE format
    b'\xff\xd8\xff': ['jpg', 'jpeg'],
    b'\x89\x50\x4e\x47': ['png'],
    b'\x47\x49\x46\x38': ['gif'],
    b'\x25\x50\x44\x46': ['pdf'],
}

async def validate_file_upload(file: UploadFile, allowed_types: str = 'all') -> tuple[bool, str]:
    """
    Validate uploaded file for security
    Returns (is_valid, error_message)
    """
    if not file or not file.filename:
        return False, "No file provided"
    
    # Check extension
    ext = Path(file.filename).suffix.lower()
    
    if ext in DANGEROUS_EXTENSIONS:
        logging.warning(f"Blocked dangerous file upload: {file.filename}")
        return False, "File type not allowed for security reasons"
    
    allowed = ALLOWED_FILE_EXTENSIONS.get(allowed_types, ALLOWED_FILE_EXTENSIONS['all'])
    if ext not in allowed:
        return False, f"File type {ext} not allowed. Allowed: {', '.join(allowed)}"
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
    
    if size == 0:
        return False, "Empty file"
    
    # Verify file signature (magic bytes)
    header = await file.read(8)
    await file.seek(0)  # Reset position
    
    # Check if file signature matches claimed extension
    extension_verified = False
    for signature, extensions in FILE_SIGNATURES.items():
        if header.startswith(signature):
            if ext.lstrip('.') in extensions or ext in [f'.{e}' for e in extensions]:
                extension_verified = True
                break
    
    # For text files, we can't verify by signature
    if ext in {'.csv', '.txt'} and not extension_verified:
        extension_verified = True  # Allow text files
    
    return True, ""

def secure_filename(filename: str) -> str:
    """Generate a secure filename to prevent path traversal"""
    # Remove path components
    filename = Path(filename).name
    # Remove any dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    # Add random prefix to prevent overwrites
    prefix = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:8]
    return f"{prefix}_{filename}"


# Create the main app
app = FastAPI(
    title="MDDRC Training Management System",
    description="Secure training management platform",
    version="2.0.0"
)

# Add security middleware FIRST (before CORS)
app.add_middleware(SecurityMiddleware)

api_router = APIRouter(prefix="/api")

# ==================== MODULAR ROUTERS (Stages 1-13) ====================
# Import and include refactored routes
from routes import (
    settings_router,
    programs_router,
    companies_router,
    auth_router,
    users_router,
    attendance_router,
    participant_access_router,
    tests_router,
    feedback_router,
    checklists_router,
    sessions_new_router,
    hr_router,
    marketing_router,
    certificates_router,
    training_reports_router,
    supervisor_router,
    super_admin_router,
    security_router,
    finance_billing_router,
    finance_invoices_router,
    finance_payments_router,
    finance_petty_cash_router,
    finance_reports_router,
    finance_payables_router,
)

# Include all modular routers
api_router.include_router(settings_router)
api_router.include_router(programs_router)
api_router.include_router(companies_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(attendance_router)
api_router.include_router(participant_access_router)
api_router.include_router(tests_router)
api_router.include_router(feedback_router)
api_router.include_router(checklists_router)
api_router.include_router(sessions_new_router)
api_router.include_router(hr_router)
api_router.include_router(marketing_router)
api_router.include_router(certificates_router)
api_router.include_router(training_reports_router)
api_router.include_router(supervisor_router)
api_router.include_router(super_admin_router)
api_router.include_router(security_router)
api_router.include_router(finance_billing_router)
api_router.include_router(finance_invoices_router)
api_router.include_router(finance_payments_router)
api_router.include_router(finance_petty_cash_router)
api_router.include_router(finance_reports_router)
api_router.include_router(finance_payables_router)
# ==================== END MODULAR ROUTERS ====================

# Static files directory
STATIC_DIR = ROOT_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
LOGO_DIR = STATIC_DIR / "logos"
LOGO_DIR.mkdir(exist_ok=True)
CERTIFICATE_DIR = STATIC_DIR / "certificates"
CERTIFICATE_DIR.mkdir(exist_ok=True)
CERTIFICATE_PDF_DIR = STATIC_DIR / "certificates_pdf"
CERTIFICATE_PDF_DIR.mkdir(exist_ok=True)
REPORT_DIR = STATIC_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)
REPORT_PDF_DIR = STATIC_DIR / "reports_pdf"
REPORT_PDF_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR = STATIC_DIR / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR = STATIC_DIR / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)
CHECKLIST_PHOTOS_DIR = STATIC_DIR / "checklist_photos"
CHECKLIST_PHOTOS_DIR.mkdir(exist_ok=True)

# ============ MODELS ============

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None  # Optional - auto-generated for participants (used for login)
    full_name: str
    id_number: str
    role: str
    additional_roles: List[str] = []  # For dual roles (e.g., coordinator + marketing)
    company_id: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None
    # Real contact details (collected from participant)
    contact_email: Optional[str] = None  # Real email provided by participant
    contact_phone: Optional[str] = None  # Real phone provided by participant
    created_at: datetime = Field(default_factory=get_malaysia_time)
    is_active: bool = True
    # Profile verification fields for participants
    profile_verified: Optional[bool] = False
    indemnity_accepted: Optional[bool] = False
    indemnity_accepted_at: Optional[str] = None
    indemnity_signature: Optional[str] = None  # Digital signature data
    indemnity_signed_name: Optional[str] = None  # Full name typed by user
    indemnity_signed_ic: Optional[str] = None  # IC typed by user
    indemnity_signed_date: Optional[str] = None  # Date typed by user
    # Enhanced indemnity form data
    indemnity_ip_address: Optional[str] = None  # IP address at time of signing
    indemnity_user_agent: Optional[str] = None  # Browser info
    indemnity_sections_accepted: Optional[dict] = None  # {section_a: true, section_b: true, ...}
    indemnity_vehicle_reg: Optional[str] = None  # Vehicle registration at signing
    indemnity_training_id: Optional[str] = None  # Training session ID at signing
    indemnity_trainer_name: Optional[str] = None  # Trainer name at signing
    indemnity_locked: Optional[bool] = False  # Once submitted, record is locked
    # Social media popup tracking
    social_popup_dismissed: Optional[bool] = False  # True after user dismisses social popup

class UserCreate(BaseModel):
    email: Optional[str] = None  # Changed from EmailStr to str - no validation, auto-generated if needed
    password: Optional[str] = None
    full_name: str
    id_number: str
    role: str
    additional_roles: List[str] = []  # For dual roles (e.g., coordinator + marketing)
    company_id: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    email: str  # Can be email or IC number
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

class Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    registration_no: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Malaysia"
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class CompanyCreate(BaseModel):
    name: str
    registration_no: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    registration_no: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None

# Billing Party / Vendor model - for alternative billing entities like HRDC
class BillingParty(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    registration_no: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Malaysia"
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=get_malaysia_time)

class Program(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    pass_percentage: float = 70.0
    created_at: datetime = Field(default_factory=get_malaysia_time)

class ProgramCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pass_percentage: Optional[float] = 70.0

class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pass_percentage: Optional[float] = None

class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    program_id: str
    company_id: str
    location: str
    start_date: str
    end_date: str
    supervisor_ids: List[str] = []
    participant_ids: List[str] = []
    trainer_assignments: List[dict] = []
    coordinator_id: Optional[str] = None
    assistant_coordinator_ids: List[str] = []  # Assistant coordinators who can manage this session
    status: str = "active"  # "active" or "inactive"
    completion_status: str = "ongoing"  # "ongoing", "completed", "archived"
    is_archived: bool = False
    archived_date: Optional[datetime] = None
    completed_by_coordinator: bool = False
    completed_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    # Marketing commission fields
    marketing_user_id: Optional[str] = None
    commission_type: Optional[str] = None  # percentage or fixed
    commission_rate: Optional[float] = None
    commission_fixed_amount: Optional[float] = None
    # Invoice reference (read-only in training app)
    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_status: Optional[str] = None
    # Grant tracking
    grant_id: Optional[str] = None
    # Lead/quotation reference for auto-created sessions
    lead_id: Optional[str] = None
    quotation_id: Optional[str] = None
    # Enriched fields (populated at runtime)
    company_name: Optional[str] = None
    program_name: Optional[str] = None

class ParticipantData(BaseModel):
    email: Optional[str] = ""  # Optional - can be empty string
    password: str = "mddrc1"  # Default password
    full_name: str
    id_number: str  # Required - used as login username
    phone_number: Optional[str] = ""

class SupervisorData(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    id_number: str
    phone_number: Optional[str] = None

class SessionCreate(BaseModel):
    name: str
    program_id: str
    company_id: str
    location: str
    start_date: str
    end_date: str
    supervisor_ids: List[str] = []
    participant_ids: List[str] = []
    participants: List[ParticipantData] = []  # New participants to create or link
    supervisors: List[SupervisorData] = []  # New supervisors to create or link
    trainer_assignments: List[dict] = []
    coordinator_id: Optional[str] = None
    assistant_coordinator_ids: List[str] = []  # Backup coordinators
    # Marketing commission fields
    marketing_user_id: Optional[str] = None
    commission_type: Optional[str] = None  # percentage or fixed
    commission_rate: Optional[float] = None  # percentage value
    commission_fixed_amount: Optional[float] = None  # fixed amount if applicable
    # Reuse deleted invoice number
    reuse_invoice_number: Optional[str] = None  # If set, reuse this deleted invoice number

class ParticipantAccess(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    can_access_pre_test: bool = False
    can_access_post_test: bool = False
    can_access_checklist: bool = False
    can_access_feedback: bool = False
    can_clock_out: bool = False  # Release control for clock out
    pre_test_completed: bool = False
    post_test_completed: bool = False
    checklist_submitted: bool = False
    checklist_completed: bool = False
    feedback_submitted: bool = False
    feedback_completed: bool = False
    certificate_url: Optional[str] = None
    certificate_uploaded_at: Optional[str] = None
    certificate_uploaded_by: Optional[str] = None

class UpdateParticipantAccess(BaseModel):
    participant_id: str
    session_id: str
    can_access_pre_test: Optional[bool] = None
    can_access_post_test: Optional[bool] = None
    can_access_checklist: Optional[bool] = None
    can_access_feedback: Optional[bool] = None
    can_clock_out: Optional[bool] = None

class TestQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int

class Test(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program_id: str
    test_type: str
    questions: List[TestQuestion] = []
    created_at: datetime = Field(default_factory=get_malaysia_time)

class TestCreate(BaseModel):
    program_id: str
    test_type: str
    questions: List[TestQuestion]

class TestResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    test_id: str
    participant_id: str
    session_id: str
    test_type: str
    answers: List[int] = []
    score: float = 0.0
    total_questions: int = 0
    correct_answers: int = 0
    passed: bool = False
    submitted_at: datetime = Field(default_factory=get_malaysia_time)
    question_indices: Optional[List[int]] = None  # Store original question order for shuffled tests

class TestSubmit(BaseModel):
    test_id: str
    session_id: str
    answers: List[int]
    question_indices: Optional[List[int]] = None  # Original question indices for shuffled tests

class ChecklistTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program_id: str
    items: List[str] = []
    created_at: datetime = Field(default_factory=get_malaysia_time)

class ChecklistTemplateCreate(BaseModel):
    program_id: str
    items: List[str]

class VehicleChecklist(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    interval: str
    checklist_items: List[dict] = []
    submitted_at: datetime = Field(default_factory=get_malaysia_time)
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_status: str = "pending"

class ChecklistSubmit(BaseModel):
    session_id: str
    interval: str
    checklist_items: List[dict]

class ChecklistVerify(BaseModel):
    checklist_id: str
    status: str
    comments: Optional[str] = None

class VehicleDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    vehicle_model: str
    registration_number: str
    roadtax_expiry: str
    created_at: datetime = Field(default_factory=get_malaysia_time)

class VehicleDetailsSubmit(BaseModel):
    session_id: str
    vehicle_model: str
    registration_number: str
    roadtax_expiry: str

class TrainingReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    coordinator_id: str
    group_photo: Optional[str] = None
    theory_photo_1: Optional[str] = None
    theory_photo_2: Optional[str] = None
    practical_photo_1: Optional[str] = None
    practical_photo_2: Optional[str] = None
    practical_photo_3: Optional[str] = None
    additional_notes: Optional[str] = None
    status: str = "draft"  # draft, submitted
    created_at: datetime = Field(default_factory=get_malaysia_time)
    submitted_at: Optional[datetime] = None

class TrainingReportCreate(BaseModel):
    session_id: str
    group_photo: Optional[str] = None
    theory_photo_1: Optional[str] = None
    theory_photo_2: Optional[str] = None
    practical_photo_1: Optional[str] = None
    practical_photo_2: Optional[str] = None
    practical_photo_3: Optional[str] = None
    additional_notes: Optional[str] = None
    status: str = "draft"

class Attendance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    date: str
    clock_in: Optional[str] = None
    clock_out: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

# ==================== MARKETING QUOTATION MODELS ====================
class MarketingClient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    company_address: str
    contact_person: str
    contact_phone: str
    contact_email: str
    notes: Optional[str] = None
    created_by: str  # marketer user id (ownership)
    created_at: datetime = Field(default_factory=get_malaysia_time)
    updated_at: datetime = Field(default_factory=get_malaysia_time)

class MarketingClientCreate(BaseModel):
    company_name: str
    company_address: str
    contact_person: str
    contact_phone: str
    contact_email: str
    notes: Optional[str] = None

class QuotationDescriptionItem(BaseModel):
    """Reusable description items that admin creates for marketers to select"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # Short name for selection (e.g., "JPJ Trainers", "Venue Rental")
    description: str = ""  # Optional longer description
    category: str = "inclusion"  # "inclusion" or "exclusion"
    has_quantity: bool = False  # Whether marketer can specify quantity
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime = Field(default_factory=get_malaysia_time)

class Quotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quotation_number: str  # QOU/MDDRC/YYYY/MM/0001
    client_id: str
    programme_id: str
    programme_name: str
    pricing_type: str = "per_pax"  # "per_pax" or "per_group"
    num_participants: int = 1
    rate_per_pax: float = 0  # Used when pricing_type is "per_pax"
    group_price: float = 0  # Used when pricing_type is "per_group"
    subtotal: float
    sst_percent: float = 0
    sst_amount: float = 0
    total_amount: float
    validity_days: int = 30
    valid_until: str
    description_items: List[str] = []  # List of selected description item IDs (legacy)
    selected_items: List[dict] = []  # New: [{item_id: str, quantity: int}]
    custom_description: Optional[str] = None  # Additional custom description
    remarks: Optional[str] = None
    terms_conditions: Optional[str] = None
    status: str = "draft"  # draft, pending_approval, approved, rejected, sent, accepted, declined
    status_history: List[dict] = []
    admin_remarks: Optional[str] = None
    created_by: str  # marketer user id
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    sent_at: Optional[str] = None
    # Accepted quotation fields - added after client accepts
    training_date: Optional[str] = None  # Date of training (when accepted)
    venue: Optional[str] = None  # Training venue (when accepted)
    accepted_at: Optional[str] = None  # When client accepted
    created_at: datetime = Field(default_factory=get_malaysia_time)
    updated_at: datetime = Field(default_factory=get_malaysia_time)


# Quotation PDF Template model - admin managed templates for cover letter, terms
class QuotationPDFTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "quotation_pdf_templates"  # Singleton
    cover_letter: str = ""  # HTML/text for cover letter page
    terms_conditions_pages: str = ""  # HTML/text for terms & conditions (pages 3-6)
    primary_color: str = "#1a365d"  # Header/title color for PDF
    updated_at: datetime = Field(default_factory=get_malaysia_time)
    updated_by: Optional[str] = None

class QuotationCreate(BaseModel):
    client_id: str
    programme_id: str
    pricing_type: str = "per_pax"  # "per_pax" or "per_group"
    num_participants: int = 1
    rate_per_pax: float = 0
    group_price: float = 0
    sst_percent: float = 0
    validity_days: int = 30
    description_items: List[str] = []  # Selected description item IDs (legacy)
    selected_items: List[dict] = []  # New: [{item_id: str, quantity: int}]
    custom_description: Optional[str] = None
    remarks: Optional[str] = None
    terms_conditions: Optional[str] = None

class QuotationUpdate(BaseModel):
    pricing_type: Optional[str] = None
    num_participants: Optional[int] = None
    rate_per_pax: Optional[float] = None
    group_price: Optional[float] = None
    sst_percent: Optional[float] = None
    validity_days: Optional[int] = None
    description_items: Optional[List[str]] = None
    selected_items: Optional[List[dict]] = None  # New: [{item_id: str, quantity: int}]
    custom_description: Optional[str] = None
    remarks: Optional[str] = None
    terms_conditions: Optional[str] = None

class QuotationStatusUpdate(BaseModel):
    status: str
    remarks: Optional[str] = None
# ==================== END MARKETING MODELS ====================

class AttendanceClockIn(BaseModel):
    session_id: str

class AttendanceClockOut(BaseModel):
    session_id: str

# Super Admin models for data submission
class SuperAdminClockIn(BaseModel):
    session_id: str
    participant_id: str
    clock_in: str

class SuperAdminClockOut(BaseModel):
    session_id: str
    participant_id: str
    clock_out: str

class SuperAdminVehicleDetails(BaseModel):
    session_id: str
    participant_id: str
    vehicle_model: str
    registration_number: str
    roadtax_expiry: str

class SuperAdminChecklistSubmit(BaseModel):
    session_id: str
    participant_id: str
    checklist_items: List[dict]

class SuperAdminFeedbackSubmit(BaseModel):
    session_id: str
    participant_id: str
    responses: List[dict]

class SuperAdminTestSubmit(BaseModel):
    test_id: str
    session_id: str
    participant_id: str
    answers: List[int]

# Helper function to convert DOCX to PDF
def convert_docx_to_pdf(docx_path: Path, pdf_path: Path) -> bool:
    """Convert DOCX to PDF using LibreOffice"""
    try:
        # Verify input file exists
        if not docx_path.exists():
            logging.error(f"DOCX file not found: {docx_path}")
            return False
        
        # Use LibreOffice in headless mode to convert DOCX to PDF
        result = subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', str(pdf_path.parent),
            str(docx_path)
        ], check=True, capture_output=True, timeout=30)
        
        # Verify output file was created
        if not pdf_path.exists():
            logging.error(f"PDF file was not created: {pdf_path}")
            logging.error(f"LibreOffice output: {result.stdout.decode()}")
            logging.error(f"LibreOffice errors: {result.stderr.decode()}")
            return False
        
        return True
    except subprocess.TimeoutExpired:
        logging.error("PDF conversion timed out after 30 seconds")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"LibreOffice conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        logging.error(f"PDF conversion failed: {str(e)}")
        return False

class ChecklistItem(BaseModel):
    item: str
    status: str  # "good", "needs_repair"
    comments: str = ""
    photo_url: Optional[str] = None

class TrainerChecklistSubmit(BaseModel):
    participant_id: str
    session_id: str
    items: List[ChecklistItem]
    chief_trainer_comments: Optional[str] = None  # Only for chief trainers

class FeedbackQuestion(BaseModel):
    question: str
    type: str  # "rating" or "text"
    required: bool = True

class FeedbackTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    program_id: str
    questions: List[FeedbackQuestion]
    created_at: datetime = Field(default_factory=get_malaysia_time)

class FeedbackTemplateCreate(BaseModel):
    program_id: str
    questions: List[FeedbackQuestion]

class CourseFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    program_id: Optional[str] = None
    responses: List[dict]  # [{"question": str, "answer": str/int}]
    submitted_at: datetime = Field(default_factory=get_malaysia_time)

class FeedbackSubmit(BaseModel):
    session_id: str
    program_id: str
    responses: List[dict]  # [{"question": str, "answer": str/int}]

class Certificate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    program_name: str
    issue_date: datetime = Field(default_factory=get_malaysia_time)
    certificate_url: Optional[str] = None

class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "app_settings"
    logo_url: Optional[str] = None
    company_name: str = "Malaysian Defensive Driving and Riding Centre Sdn Bhd"
    primary_color: str = "#3b82f6"
    secondary_color: str = "#6366f1"
    footer_text: str = ""
    certificate_template_url: Optional[str] = None
    max_certificate_file_size_mb: int = 5  # Max certificate file size in MB
    updated_at: datetime = Field(default_factory=get_malaysia_time)

class SettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


# Coordinator and Chief Trainer Feedback Models
class CoordinatorFeedbackTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "coordinator_feedback_template"
    questions: List[dict] = [
        {
            "id": "training_smoothness",
            "question": "How smoothly did the training session run?",
            "type": "rating",
            "scale": 5
        },
        {
            "id": "participant_engagement",
            "question": "Rate the overall participant engagement level",
            "type": "rating",
            "scale": 5
        },
        {
            "id": "logistics",
            "question": "Were logistics (venue, equipment, timing) adequate?",
            "type": "rating",
            "scale": 5
        },
        {
            "id": "overall_observations",
            "question": "Please provide your overall observations about the training session",
            "type": "text"
        },
        {
            "id": "issues_identified",
            "question": "What issues or challenges were identified during the session?",
            "type": "text"
        },
        {
            "id": "recommendations",
            "question": "What are your recommendations for future sessions?",
            "type": "text"
        }
    ]
    updated_at: datetime = Field(default_factory=get_malaysia_time)

class ChiefTrainerFeedbackTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "chief_trainer_feedback_template"
    questions: List[dict] = [
        {
            "id": "pre_assessment",
            "question": "What were your observations from the pre-assessment?",
            "type": "text"
        },
        {
            "id": "theory_engagement",
            "question": "How engaged were participants during the theory session?",
            "type": "rating",
            "scale": 5
        },
        {
            "id": "practical_performance",
            "question": "Rate the overall practical session performance",
            "type": "rating",
            "scale": 5
        },
        {
            "id": "challenges",
            "question": "What challenges were encountered during training?",
            "type": "text"
        },
        {
            "id": "participant_dedication",
            "question": "Rate participant dedication and effort",
            "type": "rating",
            "scale": 5
        },
        {
            "id": "overall_impressions",
            "question": "Please share your overall impressions and recommendations",
            "type": "text"
        }
    ]
    updated_at: datetime = Field(default_factory=get_malaysia_time)

class CoordinatorFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    coordinator_id: str
    responses: dict = {}
    submitted_at: datetime = Field(default_factory=get_malaysia_time)

class ChiefTrainerFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    trainer_id: str
    responses: dict = {}
    submitted_at: datetime = Field(default_factory=get_malaysia_time)

class FeedbackTemplateUpdate(BaseModel):
    questions: List[dict]

    footer_text: Optional[str] = None
    max_certificate_file_size_mb: Optional[int] = None

# ============ FINANCE MODELS ============

class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_number: str  # e.g., INV/MDDRC/25/12/0001
    session_id: str
    company_id: str
    company_name: Optional[str] = None
    programme_name: Optional[str] = None
    training_dates: Optional[str] = None
    venue: Optional[str] = None
    pax: int = 0
    num_days: int = 1  # Number of training days
    
    # Bill To (editable by finance - e.g., HRD Corp)
    bill_to_name: Optional[str] = None  # e.g., "HUMAN RESOURCES DEVELOPMENT CORPORATION"
    bill_to_address: Optional[str] = None
    bill_to_reg_no: Optional[str] = None  # Company Registration Number
    your_reference: Optional[str] = None  # Client's reference number
    
    # Pricing type and line items
    pricing_type: str = "lumpsum"  # lumpsum or per_pax
    line_items: List[dict] = []  # [{description, quantity, unit_price, amount}]
    subtotal: float = 0.0
    mobilisation_fee: float = 0.0  # Mobilisation fee
    rounding: float = 0.0  # Rounding adjustment
    tax_rate: float = 0.0  # SST/GST percentage
    tax_amount: float = 0.0
    discount: float = 0.0
    total_amount: float = 0.0
    
    # Status workflow
    status: str = "auto_draft"  # auto_draft, finance_review, approved, issued, paid, cancelled
    
    # Tracking
    created_at: datetime = Field(default_factory=get_malaysia_time)
    updated_at: datetime = Field(default_factory=get_malaysia_time)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    issued_by: Optional[str] = None
    issued_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    # Version control for revisions
    version: int = 1
    parent_invoice_id: Optional[str] = None

class InvoiceUpdate(BaseModel):
    # Bill To fields (editable by finance)
    bill_to_name: Optional[str] = None
    bill_to_address: Optional[str] = None
    bill_to_reg_no: Optional[str] = None
    your_reference: Optional[str] = None
    
    # Training details (editable)
    programme_name: Optional[str] = None
    training_dates: Optional[str] = None
    venue: Optional[str] = None
    pax: Optional[int] = None
    num_days: Optional[int] = None
    
    # Pricing
    pricing_type: Optional[str] = None
    line_items: Optional[List[dict]] = None
    subtotal: Optional[float] = None
    mobilisation_fee: Optional[float] = None
    rounding: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    discount: Optional[float] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None

class Payment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_id: str
    amount: float
    payment_date: str  # YYYY-MM-DD
    payment_method: str  # bank_transfer, cheque, cash, online
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: str
    created_at: datetime = Field(default_factory=get_malaysia_time)

class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float
    payment_date: str
    payment_method: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    # Credit note fields
    create_credit_note: Optional[bool] = False
    deduction_percentage: Optional[float] = None
    deduction_amount: Optional[float] = None
    deduction_reason: Optional[str] = "HRDCorp Levy Deduction"

# Company Settings for Invoice/Receipt customization
class CompanySettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "company_settings"  # Singleton
    company_name: str = "MDDRC SDN BHD"
    company_reg_no: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    postcode: str = ""
    state: str = ""
    country: str = "Malaysia"
    phone: str = ""
    email: str = ""
    website: str = ""
    logo_url: Optional[str] = None
    # Bank details
    bank_name: str = ""
    bank_account_name: str = ""
    bank_account_number: str = ""
    bank_swift_code: str = ""
    # Invoice settings
    invoice_prefix: str = "INV/MDDRC"
    invoice_terms: str = "Upon receipt of invoice"
    invoice_footer_note: str = "Thank you for your business!"
    # Document styling settings
    tagline: str = "Towards a Nation of Safe Drivers"
    primary_color: str = "#1a365d"  # Header/title color
    secondary_color: str = "#4472C4"  # Accent color
    header_font: str = "Arial"  # Font for headers
    body_font: str = "Arial"  # Font for body text
    logo_width: int = 35  # Logo width in mm (PDF uses mm)
    logo_height: int = 20  # Logo height in mm (0 = auto-scale)
    logo_x: int = 10  # Logo X position in mm from left
    logo_y: int = 8  # Logo Y position in mm from top
    header_x: int = 50  # Header text X position in mm
    header_y: int = 8  # Header text Y position in mm
    logo_position: str = "left"  # left, center, right (legacy)
    show_watermark: bool = True  # Show watermark logo in background
    watermark_opacity: float = 0.08  # Watermark opacity (0.0 - 1.0)
    tagline_font: str = "Georgia"  # Font for tagline (elegant)
    tagline_style: str = "italic"  # normal, italic, bold
    # Dynamic custom fields for documents
    invoice_custom_fields: Optional[List[dict]] = None  # [{label, value, position}]
    indemnity_custom_fields: Optional[List[dict]] = None  # [{label, type, required}]
    payslip_custom_fields: Optional[List[dict]] = None  # [{label, type, default_value}]
    payadvice_custom_fields: Optional[List[dict]] = None  # [{label, show_in_summary}]
    # Custom indemnity form upload
    indemnity_form_url: Optional[str] = None  # URL to uploaded custom indemnity form PDF
    indemnity_form_filename: Optional[str] = None  # Original filename
    # Social media links - dynamic list
    social_media_links: Optional[List[dict]] = None  # [{platform, url, icon, is_active}]
    updated_at: datetime = Field(default_factory=get_malaysia_time)
    updated_by: Optional[str] = None

# Trainer Fee - Custom amount per trainer per session
class TrainerFee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    trainer_id: str
    trainer_name: Optional[str] = None
    role: str  # chief_trainer, trainer, assistant_trainer
    fee_amount: float = 0.0  # Custom fee set at booking
    remark: Optional[str] = None
    status: str = "pending"  # pending, approved, paid
    paid_date: Optional[str] = None
    paid_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

# Coordinator Fee - RM 50/day
class CoordinatorFee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    coordinator_id: str
    coordinator_name: Optional[str] = None
    num_days: int = 1
    daily_rate: float = 50.0  # RM 50 per day
    total_fee: float = 0.0  # daily_rate * num_days
    status: str = "pending"  # pending, approved, paid
    paid_date: Optional[str] = None
    paid_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

# Session Expenses - Both estimated and actual
class SessionExpense(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    category: str  # accommodation, allowance, petrol, toll, wear_tear, printing, hrdc_levy, sst, other
    description: Optional[str] = None
    expense_type: str = "fixed"  # fixed or percentage
    percentage_rate: float = 0.0  # If percentage-based
    estimated_amount: float = 0.0
    actual_amount: float = 0.0
    quantity: int = 1
    unit_price: float = 0.0
    remark: Optional[str] = None
    status: str = "estimated"  # estimated, actual, approved, paid
    created_at: datetime = Field(default_factory=get_malaysia_time)
    updated_at: datetime = Field(default_factory=get_malaysia_time)

# Marketing Commission - Based on PROFIT
class MarketingCommission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    marketing_user_id: str
    marketing_user_name: Optional[str] = None
    commission_type: str = "percentage"  # percentage or fixed
    commission_rate: float = 0.0  # percentage of PROFIT (e.g., 10.0 for 10%)
    fixed_amount: float = 0.0  # if commission_type is fixed
    calculated_amount: float = 0.0  # actual commission (calculated from profit)
    invoice_id: Optional[str] = None
    status: str = "pending"  # pending, approved, paid
    paid_date: Optional[str] = None
    paid_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    updated_at: datetime = Field(default_factory=get_malaysia_time)

class MarketingCommissionCreate(BaseModel):
    session_id: str
    marketing_user_id: str
    commission_type: str = "percentage"
    commission_rate: float = 0.0
    fixed_amount: float = 0.0

# Session Profit Summary - Calculated view
class SessionProfitSummary(BaseModel):
    session_id: str
    session_name: Optional[str] = None
    company_name: Optional[str] = None
    training_dates: Optional[str] = None
    
    # Revenue
    invoice_total: float = 0.0
    less_tax: float = 0.0
    gross_revenue: float = 0.0
    
    # Expenses breakdown
    trainer_fees_total: float = 0.0
    coordinator_fees_total: float = 0.0
    cash_expenses_total: float = 0.0  # Training aid expenses
    marketing_commission: float = 0.0
    other_expenses: float = 0.0
    total_expenses: float = 0.0
    
    # Profit
    profit: float = 0.0
    profit_percentage: float = 0.0

# For backward compatibility - alias
class TrainerIncome(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    trainer_id: str
    trainer_role: str
    amount: float = 0.0
    status: str = "pending"
    paid_date: Optional[str] = None
    paid_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    coordinator_id: str
    amount: float = 0.0
    status: str = "pending"  # pending, approved, paid
    paid_date: Optional[str] = None
    paid_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class FinanceAuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str  # invoice, payment, commission, trainer_income, coordinator_fee
    entity_id: str
    action: str  # created, updated, status_changed, deleted
    before_value: Optional[dict] = None
    after_value: Optional[dict] = None
    changed_by: str
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=get_malaysia_time)

# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    # JWT expiration should remain in UTC for standard compliance
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        
        if isinstance(user_doc.get('created_at'), str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        
        return User(**user_doc)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_or_create_participant_access(participant_id: str, session_id: str):
    access_doc = await db.participant_access.find_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"_id": 0}
    )
    
    if not access_doc:
        access_obj = ParticipantAccess(
            participant_id=participant_id,
            session_id=session_id
        )
        doc = access_obj.model_dump()
        await db.participant_access.insert_one(doc)
        return access_obj
    
    return ParticipantAccess(**access_doc)

async def find_or_create_user(user_data: dict, role: str, company_id: str) -> dict:
    """
    Find existing user based on role:
    - Supervisors: Email is the unique identifier
    - Participants: IC number is the unique identifier
    If found: update the user with NEW data (latest wins)
    If not found: create new user
    Returns: user dict with 'is_existing' flag and user data
    """
    full_name = user_data.get("full_name")
    email = user_data.get("email")
    id_number = user_data.get("id_number")
    phone_number = user_data.get("phone_number")
    
    existing_user = None
    
    # Different lookup strategy based on role
    if role == "supervisor":
        # For supervisors: email is the unique identifier
        if email and email.strip():
            existing_user = await db.users.find_one({"email": email.strip()}, {"_id": 0})
    else:
        # For participants: IC number is the unique identifier
        if id_number:
            existing_user = await db.users.find_one({"id_number": id_number}, {"_id": 0})
    
    if existing_user:
        # User found - update with NEW data (latest entry wins)
        update_data = {
            "phone_number": phone_number,
            "company_id": company_id,
        }
        
        # Update full_name with latest value (fixes typo correction issue)
        if full_name and full_name.strip():
            update_data["full_name"] = full_name.strip()
        
        # For participants: update email only if it doesn't belong to another user
        if role != "supervisor" and email and email.strip():
            email_owner = await db.users.find_one({"email": email.strip()}, {"id": 1})
            if not email_owner or email_owner.get("id") == existing_user["id"]:
                update_data["email"] = email.strip()
        
        # For supervisors: update IC if provided
        if role == "supervisor" and id_number:
            update_data["id_number"] = id_number
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if update_data:
            await db.users.update_one(
                {"id": existing_user["id"]},
                {"$set": update_data}
            )
        
        # Return updated user data
        updated_user = await db.users.find_one({"id": existing_user["id"]}, {"_id": 0})
        if isinstance(updated_user.get('created_at'), str):
            updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
        
        return {
            "is_existing": True,
            "user": User(**updated_user)
        }
    else:
        # User not found - create new
        # Check for email conflicts before creating
        if email and email.strip():
            email_owner = await db.users.find_one({"email": email.strip()}, {"id": 1})
            if email_owner:
                # Email already used - generate temp email for participants only
                if role != "supervisor":
                    if id_number:
                        email = f"{id_number.replace('-', '').replace(' ', '')}@temp.mddrc.local"
                    else:
                        email = f"user_{uuid.uuid4().hex[:8]}@temp.mddrc.local"
                # For supervisors with duplicate email, return error (shouldn't happen as we search by email)
        
        # Use default password 'mddrc1' for participants/supervisors if no password provided
        password = user_data.get("password")
        if role in ["participant", "supervisor"] and not password:
            password = "mddrc1"
        
        hashed_password = pwd_context.hash(password)
        
        # Auto-generate email if not provided (for unique constraint)
        if not email or email.strip() == "":
            if id_number:
                email = f"{id_number.replace('-', '').replace(' ', '')}@temp.mddrc.local"
            else:
                email = f"user_{uuid.uuid4().hex[:8]}@temp.mddrc.local"
        
        new_user = User(
            email=email,
            full_name=full_name,
            id_number=user_data.get("id_number"),
            role=role,
            company_id=company_id,
            phone_number=phone_number
        )
        
        user_doc = new_user.model_dump()
        user_doc["created_at"] = user_doc["created_at"].isoformat()
        user_doc["password"] = hashed_password
        
        await db.users.insert_one(user_doc)
        
        return {
            "is_existing": False,
            "user": new_user
        }

# Training Report Models
class TrainingReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    program_id: str
    company_id: str
    generated_by: str  # coordinator_id
    content: str  # Markdown content
    status: str  # "draft" or "published"
    created_at: datetime = Field(default_factory=get_malaysia_time)
    published_at: Optional[datetime] = None
    published_to_supervisors: List[str] = []  # List of supervisor IDs

class ReportGenerateRequest(BaseModel):
    session_id: str

class ReportUpdateRequest(BaseModel):
    content: str

# ============ ROUTES ============

@api_router.get("/")
async def root():
    return {"message": "Defensive Driving Training API"}

# Auth Routes
@api_router.post("/auth/register", response_model=User)
async def register_user(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    # Role-based access control:
    # - Admins can create any user
    # - Coordinators can only create participants
    # - Assistant Admins can only create participants
    if current_user.role == "coordinator" or current_user.role == "assistant_admin":
        if user_data.role != "participant":
            raise HTTPException(status_code=403, detail="You can only create participants")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # For participants: use default password if not provided
    password = user_data.password
    email = user_data.email
    
    if user_data.role == "participant":
        # Default password: mddrc1
        if not password:
            password = "mddrc1"
        # Auto-generate email if not provided (for unique constraint)
        if not email or email.strip() == "":
            if user_data.id_number:
                email = f"{user_data.id_number.replace('-', '').replace(' ', '')}@temp.mddrc.local"
            else:
                email = f"user_{uuid.uuid4().hex[:8]}@temp.mddrc.local"
    
    # Check if user exists by email OR IC number
    existing = await db.users.find_one({
        "$or": [
            {"id_number": user_data.id_number},
            {"email": email}
        ]
    }, {"_id": 0})
    
    if existing:
        if existing.get('id_number') == user_data.id_number:
            raise HTTPException(status_code=400, detail="User already exists with this IC number")
        else:
            raise HTTPException(status_code=400, detail="User already exists with this email")
    
    hashed_pw = hash_password(password)
    user_obj = User(
        email=email,  # Now always has a value (auto-generated if needed)
        full_name=user_data.full_name,
        id_number=user_data.id_number,
        role=user_data.role,
        company_id=user_data.company_id,
        location=user_data.location
    )
    
    doc = user_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['password'] = hashed_pw
    
    await db.users.insert_one(doc)
    return user_obj

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
    """Secure login with rate limiting and lockout protection"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Check for login lockout
    is_locked, remaining = check_login_lockout(client_ip)
    if is_locked:
        logging.warning(f"Locked out IP attempted login: {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail=f"Too many failed attempts. Try again in {remaining} seconds."
        )
    
    # Check for malicious input
    if is_malicious_input(user_data.email) or is_malicious_input(user_data.password):
        logging.warning(f"Malicious login attempt from IP: {client_ip}")
        record_failed_login(client_ip)
        raise HTTPException(status_code=400, detail="Invalid input detected")
    
    # Allow login with email OR IC number
    query_conditions = [{"id_number": user_data.email}]
    
    if "@" in user_data.email:
        query_conditions.append({"email": user_data.email})
    
    user_doc = await db.users.find_one({
        "$or": query_conditions
    }, {"_id": 0})
    
    if not user_doc:
        record_failed_login(client_ip)
        # Use generic message to prevent user enumeration
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    password_hash = user_doc.get('password') or user_doc.get('hashed_password')
    if not password_hash:
        record_failed_login(client_ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(user_data.password, password_hash):
        record_failed_login(client_ip)
        logging.info(f"Failed login attempt for user: {user_data.email} from IP: {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user_doc.get('is_active', True):
        raise HTTPException(status_code=401, detail="Account is inactive")
    
    # Clear failed attempts on successful login
    clear_failed_logins(client_ip)
    
    token = create_access_token({"sub": user_doc['id']})
    
    # Log successful login
    logging.info(f"Successful login: {user_data.email} from IP: {client_ip}")
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    user_doc.pop('password', None)
    user_doc.pop('hashed_password', None)
    user = User(**user_doc)
    
    return TokenResponse(access_token=token, token_type="bearer", user=user)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str

@api_router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Simple forgot password endpoint that checks if user exists
    In production, this would send an email with reset link
    """
    user_doc = await db.users.find_one({"email": request.email}, {"_id": 0})
    
    # Always return success to prevent email enumeration
    if not user_doc:
        return {"message": "If an account exists with this email, password reset instructions have been sent"}
    
    # For MVP: Return success message
    # In production: Generate token, send email with reset link
    return {"message": "If an account exists with this email, password reset instructions have been sent"}

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@api_router.post("/auth/change-password")
async def change_password(request: ChangePasswordRequest, current_user: User = Depends(get_current_user)):
    """
    Change password for logged-in user
    """
    # Verify current password
    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(request.current_password, user_doc["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Minimum password length
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Hash and update new password
    hashed_password = hash_password(request.new_password)
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password": hashed_password}}
    )
    
    return {"message": "Password changed successfully"}

@api_router.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password for a user
    In production, this would require a valid reset token from email
    For MVP: Allow direct reset with email verification
    """
    user_doc = await db.users.find_one({"email": request.email}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash new password
    hashed_password = pwd_context.hash(request.new_password)
    
    # Update password
    await db.users.update_one(
        {"email": request.email},
        {"$set": {"password": hashed_password}}
    )
    
    return {"message": "Password reset successfully"}

# Company Routes
@api_router.post("/companies", response_model=Company)
async def create_company(company_data: CompanyCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create companies")
    
    company_obj = Company(
        name=company_data.name,
        registration_no=company_data.registration_no,
        address_line1=company_data.address_line1,
        address_line2=company_data.address_line2,
        city=company_data.city,
        postcode=company_data.postcode,
        state=company_data.state,
        phone=company_data.phone,
        email=company_data.email,
        contact_person=company_data.contact_person
    )
    doc = company_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.companies.insert_one(doc)
    return company_obj

@api_router.get("/companies", response_model=List[Company])
async def get_companies(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}  # Case-insensitive search
    
    companies = await db.companies.find(query, {"_id": 0}).to_list(1000)
    for company in companies:
        if isinstance(company.get('created_at'), str):
            company['created_at'] = datetime.fromisoformat(company['created_at'])
    return companies

@api_router.put("/companies/{company_id}", response_model=Company)
async def update_company(company_id: str, company_data: CompanyUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can update companies")
    
    update_dict = {k: v for k, v in company_data.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = await db.companies.update_one(
        {"id": company_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company_doc = await db.companies.find_one({"id": company_id}, {"_id": 0})
    return company_doc

# ============ BILLING PARTIES / VENDORS ============

@api_router.post("/finance/billing-parties")
async def create_billing_party(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new billing party / vendor"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    billing_party = BillingParty(
        name=data.get("name"),
        registration_no=data.get("registration_no"),
        address_line1=data.get("address_line1"),
        address_line2=data.get("address_line2"),
        city=data.get("city"),
        postcode=data.get("postcode"),
        state=data.get("state"),
        phone=data.get("phone"),
        email=data.get("email"),
        contact_person=data.get("contact_person")
    )
    doc = billing_party.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.billing_parties.insert_one(doc)
    doc.pop('_id', None)  # Remove ObjectId before returning
    return {"message": "Billing party created", "billing_party": doc}

@api_router.get("/finance/billing-parties")
async def get_billing_parties(current_user: User = Depends(get_current_user)):
    """Get all billing parties"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    parties = await db.billing_parties.find({"is_active": True}, {"_id": 0}).to_list(100)
    return parties

@api_router.put("/finance/billing-parties/{party_id}")
async def update_billing_party(party_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a billing party"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_dict = {k: v for k, v in data.items() if v is not None and k != "id"}
    
    result = await db.billing_parties.update_one(
        {"id": party_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Billing party not found")
    
    return {"message": "Updated successfully"}

@api_router.delete("/finance/billing-parties/{party_id}")
async def delete_billing_party(party_id: str, current_user: User = Depends(get_current_user)):
    """Soft delete a billing party"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.billing_parties.update_one(
        {"id": party_id},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "Deleted successfully"}

@api_router.delete("/companies/{company_id}")
async def delete_company(company_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete companies")
    
    result = await db.companies.delete_one({"id": company_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"message": "Company deleted successfully"}

# Program Routes
@api_router.post("/programs", response_model=Program)
async def create_program(program_data: ProgramCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create programs")
    
    program_obj = Program(**program_data.model_dump())
    doc = program_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.programs.insert_one(doc)
    return program_obj

@api_router.get("/programs", response_model=List[Program])
async def get_programs(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}  # Case-insensitive search
    
    programs = await db.programs.find(query, {"_id": 0}).to_list(1000)
    for program in programs:
        if isinstance(program.get('created_at'), str):
            program['created_at'] = datetime.fromisoformat(program['created_at'])
    return programs

@api_router.put("/programs/{program_id}", response_model=Program)
async def update_program(program_id: str, program_data: ProgramUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update programs")
    
    update_data = {k: v for k, v in program_data.model_dump().items() if v is not None}
    
    result = await db.programs.update_one(
        {"id": program_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    
    program_doc = await db.programs.find_one({"id": program_id}, {"_id": 0})
    if isinstance(program_doc.get('created_at'), str):
        program_doc['created_at'] = datetime.fromisoformat(program_doc['created_at'])
    return Program(**program_doc)

@api_router.delete("/programs/{program_id}")
async def delete_program(program_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete programs")
    
    result = await db.programs.delete_one({"id": program_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    
    return {"message": "Program deleted successfully"}

# User Delete Route
@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete users")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Delete user from database
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Clean up: Remove user from all sessions
    await db.sessions.update_many(
        {"participant_ids": user_id},
        {"$pull": {"participant_ids": user_id}}
    )
    
    # Clean up: Delete participant_access records
    await db.participant_access.delete_many({"participant_id": user_id})
    
    # Clean up: Delete attendance records
    await db.attendance.delete_many({"participant_id": user_id})
    
    return {"message": "User and all related data deleted successfully"}

# Update own profile (for participants) - MUST BE BEFORE /users/{user_id} to avoid route conflict
@api_router.put("/users/profile")
async def update_own_profile(profile_data: dict, request: Request, current_user: User = Depends(get_current_user)):
    """Allow users to update their own profile (limited fields)"""
    
    # Update allowed fields based on role
    update_data = {}
    
    # All users can update these
    if "full_name" in profile_data:
        update_data["full_name"] = profile_data["full_name"]
    if "id_number" in profile_data:
        update_data["id_number"] = profile_data["id_number"]
    if "phone" in profile_data:
        update_data["phone"] = profile_data["phone"]
    if "emergency_contact" in profile_data:
        update_data["emergency_contact"] = profile_data["emergency_contact"]
    if "emergency_phone" in profile_data:
        update_data["emergency_phone"] = profile_data["emergency_phone"]
    if "blood_type" in profile_data:
        update_data["blood_type"] = profile_data["blood_type"]
    if "medical_conditions" in profile_data:
        update_data["medical_conditions"] = profile_data["medical_conditions"]
    # Real contact details (participant provides their actual email/phone)
    if "contact_email" in profile_data:
        update_data["contact_email"] = profile_data["contact_email"]
    if "contact_phone" in profile_data:
        update_data["contact_phone"] = profile_data["contact_phone"]
    # Social popup dismissed
    if "social_popup_dismissed" in profile_data:
        update_data["social_popup_dismissed"] = profile_data["social_popup_dismissed"]
    
    # Profile verification fields
    if "profile_verified" in profile_data:
        update_data["profile_verified"] = profile_data["profile_verified"]
    if "indemnity_accepted" in profile_data:
        update_data["indemnity_accepted"] = profile_data["indemnity_accepted"]
    if "indemnity_accepted_at" in profile_data:
        update_data["indemnity_accepted_at"] = profile_data["indemnity_accepted_at"]
    # Digital signature fields
    if "indemnity_signature" in profile_data:
        update_data["indemnity_signature"] = profile_data["indemnity_signature"]
    if "indemnity_signed_name" in profile_data:
        update_data["indemnity_signed_name"] = profile_data["indemnity_signed_name"]
    if "indemnity_signed_ic" in profile_data:
        update_data["indemnity_signed_ic"] = profile_data["indemnity_signed_ic"]
    if "indemnity_signed_date" in profile_data:
        update_data["indemnity_signed_date"] = profile_data["indemnity_signed_date"]
    # Enhanced indemnity fields
    if "indemnity_sections_accepted" in profile_data:
        update_data["indemnity_sections_accepted"] = profile_data["indemnity_sections_accepted"]
    if "indemnity_training_id" in profile_data:
        update_data["indemnity_training_id"] = profile_data["indemnity_training_id"]
    if "indemnity_trainer_name" in profile_data:
        update_data["indemnity_trainer_name"] = profile_data["indemnity_trainer_name"]
    if "indemnity_vehicle_reg" in profile_data:
        update_data["indemnity_vehicle_reg"] = profile_data["indemnity_vehicle_reg"]
    if "indemnity_locked" in profile_data:
        update_data["indemnity_locked"] = profile_data["indemnity_locked"]
    
    # Capture IP address and user agent when indemnity is being accepted
    if profile_data.get("indemnity_accepted") == True:
        client_ip = request.client.host if request.client else "unknown"
        # Try to get real IP from headers (in case of proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        update_data["indemnity_ip_address"] = client_ip
        update_data["indemnity_user_agent"] = request.headers.get("User-Agent", "unknown")
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_data["updated_at"] = get_malaysia_time().isoformat()
    
    # Update user
    await db.users.update_one({"id": current_user.id}, {"$set": update_data})
    
    # Fetch and return updated user
    updated_user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "password": 0})
    
    return updated_user

# User Update Route (admin only)
@api_router.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")
    
    # Find existing user
    existing_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if email is being changed and if it conflicts with another user
    if user_data.get("email") and user_data["email"] != existing_user.get("email"):
        email_exists = await db.users.find_one({"email": user_data["email"], "id": {"$ne": user_id}}, {"_id": 0})
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already in use by another user")
    
    # Update allowed fields
    update_data = {}
    if "full_name" in user_data:
        update_data["full_name"] = user_data["full_name"]
    if "email" in user_data:
        update_data["email"] = user_data["email"]
    if "id_number" in user_data:
        # Check if new IC number conflicts with another user
        new_ic = user_data["id_number"]
        if new_ic and new_ic != existing_user.get("id_number"):
            ic_exists = await db.users.find_one({"id_number": new_ic, "id": {"$ne": user_id}}, {"_id": 0})
            if ic_exists:
                raise HTTPException(status_code=400, detail="IC number already in use by another user")
        update_data["id_number"] = new_ic
    if "phone_number" in user_data:
        update_data["phone_number"] = user_data["phone_number"]
    if "additional_roles" in user_data:
        update_data["additional_roles"] = user_data["additional_roles"]
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # Update user
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    # Fetch and return updated user
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if isinstance(updated_user.get('created_at'), str):
        updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
    
    return User(**updated_user)

# Check if user exists

@api_router.post("/users/coordinator")
async def create_coordinator(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new coordinator user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create coordinators")
    
    # Check if email already exists
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    
    user_doc = {
        "id": user_id,
        "email": data.get("email"),
        "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""),
        "hashed_password": hashed_password,
        "role": "coordinator",
        "additional_roles": data.get("additional_roles", []),
        "is_verified": True,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Coordinator created successfully"}


@api_router.post("/users/assistant-admin")
async def create_assistant_admin(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new assistant admin user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create assistant admins")
    
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    
    user_doc = {
        "id": user_id,
        "email": data.get("email"),
        "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""),
        "hashed_password": hashed_password,
        "role": "assistant_admin",
        "additional_roles": data.get("additional_roles", []),
        "is_verified": True,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Assistant Admin created successfully"}


@api_router.post("/users/finance")
async def create_finance_user(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new finance user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create finance users")
    
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    
    user_doc = {
        "id": user_id,
        "email": data.get("email"),
        "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""),
        "hashed_password": hashed_password,
        "role": "finance",
        "additional_roles": data.get("additional_roles", []),
        "is_verified": True,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Finance user created successfully"}


@api_router.post("/users/trainer")
async def create_trainer(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new trainer user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create trainers")
    
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    
    user_doc = {
        "id": user_id,
        "email": data.get("email"),
        "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""),
        "hashed_password": hashed_password,
        "role": "trainer",
        "additional_roles": data.get("additional_roles", []),
        "is_verified": True,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Trainer created successfully"}


@api_router.post("/users/marketing")
async def create_marketing_user(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new marketing user"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create marketing users")
    
    existing = await db.users.find_one({"email": data.get("email")})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(data.get("password", "mddrc1"))
    
    user_doc = {
        "id": user_id,
        "email": data.get("email"),
        "full_name": data.get("full_name"),
        "id_number": data.get("id_number", ""),
        "hashed_password": hashed_password,
        "role": "marketing",
        "additional_roles": data.get("additional_roles", []),
        "is_verified": True,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.users.insert_one(user_doc)
    return {"id": user_id, "message": "Marketing user created successfully"}


@api_router.post("/users/check-exists")
async def check_user_exists(
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    id_number: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Check if a user exists by fullname OR email OR id_number"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can check user existence")
    
    query = {"$or": []}
    
    if full_name:
        query["$or"].append({"full_name": full_name})
    if email:
        query["$or"].append({"email": email})
    if id_number:
        query["$or"].append({"id_number": id_number})
    
    if not query["$or"]:
        return {"exists": False, "user": None}
    
    existing_user = await db.users.find_one(query, {"_id": 0, "hashed_password": 0})
    
    if existing_user:
        if isinstance(existing_user.get('created_at'), str):
            existing_user['created_at'] = datetime.fromisoformat(existing_user['created_at'])
        return {
            "exists": True,
            "user": User(**existing_user)
        }
    
    return {"exists": False, "user": None}

# Get indemnity records for participants in a session (Admin only)
@api_router.get("/sessions/{session_id}/indemnity-records")
async def get_session_indemnity_records(session_id: str, current_user: User = Depends(get_current_user)):
    """Get indemnity acceptance records for all participants in a session"""
    if current_user.role not in ["admin", "coordinator", "assistant_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get participants with indemnity data
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

# Export indemnity records as Excel
@api_router.get("/sessions/{session_id}/indemnity-records/export")
async def export_session_indemnity_records(session_id: str, current_user: User = Depends(get_current_user)):
    """Export indemnity records as Excel file"""
    if current_user.role not in ["admin", "coordinator", "assistant_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get participants
    participant_ids = session.get("participant_ids", [])
    participants = await db.users.find(
        {"id": {"$in": participant_ids}},
        {"_id": 0}
    ).to_list(1000)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Indemnity Records"
    
    # Headers
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

# Session Routes
@api_router.post("/sessions")
async def create_session(session_data: SessionCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create sessions")
    
    # Process new participants (find or create)
    processed_participant_ids = list(session_data.participant_ids)  # Start with existing IDs
    participant_results = []
    
    for participant_data in session_data.participants:
        result = await find_or_create_user(
            participant_data.model_dump(),
            role="participant",
            company_id=session_data.company_id
        )
        processed_participant_ids.append(result["user"].id)
        participant_results.append({
            "name": result["user"].full_name,
            "email": result["user"].email,
            "is_existing": result["is_existing"]
        })
    
    # Process new supervisors (find or create)
    processed_supervisor_ids = list(session_data.supervisor_ids)  # Start with existing IDs
    supervisor_results = []
    
    for supervisor_data in session_data.supervisors:
        result = await find_or_create_user(
            supervisor_data.model_dump(),
            role="pic_supervisor",
            company_id=session_data.company_id
        )
        processed_supervisor_ids.append(result["user"].id)
        supervisor_results.append({
            "name": result["user"].full_name,
            "email": result["user"].email,
            "is_existing": result["is_existing"]
        })
    
    # Create session with processed IDs
    session_obj = Session(
        name=session_data.name,
        program_id=session_data.program_id,
        company_id=session_data.company_id,
        location=session_data.location,
        start_date=session_data.start_date,
        end_date=session_data.end_date,
        participant_ids=processed_participant_ids,
        supervisor_ids=processed_supervisor_ids,
        trainer_assignments=session_data.trainer_assignments,
        coordinator_id=session_data.coordinator_id,
        # Marketing commission fields
        marketing_user_id=session_data.marketing_user_id,
        commission_type=session_data.commission_type,
        commission_rate=session_data.commission_rate,
        commission_fixed_amount=session_data.commission_fixed_amount,
    )
    
    doc = session_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    # completion_status is already set to "ongoing" by default in the model
    # completed_by_coordinator is already set to False by default in the model
    
    await db.sessions.insert_one(doc)
    
    # Auto-create draft invoice for this session
    # Check if we should reuse a deleted invoice number
    reuse_number = session_data.reuse_invoice_number
    try:
        invoice = await create_auto_invoice_for_session(doc, current_user.id, reuse_invoice_number=reuse_number)
        # Update session with invoice reference
        await db.sessions.update_one(
            {"id": session_obj.id},
            {"$set": {
                "invoice_id": invoice["id"],
                "invoice_number": invoice["invoice_number"],
                "invoice_status": invoice["status"]
            }}
        )
        session_obj.invoice_id = invoice["id"]
        session_obj.invoice_number = invoice["invoice_number"]
        session_obj.invoice_status = invoice["status"]
        
        # If we reused a deleted invoice number, mark it as used
        if reuse_number:
            await db.deleted_invoice_numbers.update_one(
                {"invoice_number": reuse_number},
                {"$set": {"is_available": False, "reused_at": get_malaysia_time().isoformat(), "reused_session_id": session_obj.id}}
            )
    except Exception as e:
        logging.error(f"Failed to create auto-invoice for session {session_obj.id}: {str(e)}")
    
    # Create marketing commission record if marketing person assigned
    if session_data.marketing_user_id:
        commission_record = {
            "id": str(uuid.uuid4()),
            "session_id": session_obj.id,
            "marketing_user_id": session_data.marketing_user_id,
            "commission_type": session_data.commission_type or "percentage",
            "commission_rate": session_data.commission_rate or 0.0,
            "fixed_amount": session_data.commission_fixed_amount or 0.0,
            "calculated_amount": 0.0,  # Will be calculated when invoice is issued
            "status": "pending",
            "created_at": get_malaysia_time().isoformat(),
            "updated_at": get_malaysia_time().isoformat()
        }
        await db.marketing_commissions.insert_one(commission_record)
    
    # Create participant access records
    for participant_id in processed_participant_ids:
        await get_or_create_participant_access(participant_id, session_obj.id)
    
    return {
        "session": session_obj,
        "participant_results": participant_results,
        "supervisor_results": supervisor_results
    }

@api_router.get("/sessions", response_model=List[Session])
async def get_sessions(
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # Get sessions based on role-specific rules
    current_date = get_malaysia_time().date()
    current_date_str = current_date.isoformat()
    
    # Base query: exclude archived sessions
    # For trainers: show only current/future sessions (end_date >= today) that aren't completed
    # For coordinators/admin: show ALL non-completed sessions (no date filtering) - manual completion required
    if current_user.role == "trainer":
        # Trainers see only sessions where they're assigned as trainer OR assistant coordinator
        # AND session end_date is today or in the future (past sessions go to Past Training)
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},  # Not archived
                {"status": "active"},
                # Only show current/future sessions (end_date >= today)
                {"end_date": {"$gte": current_date_str}},
                # Also exclude completed sessions
                {
                    "$or": [
                        {"completed_by_coordinator": {"$exists": False}},
                        {"completed_by_coordinator": False},
                        {"completion_status": {"$exists": False}},
                        {"completion_status": "ongoing"}
                    ]
                },
                # Trainer can see sessions where they're assigned as trainer OR assistant coordinator
                {
                    "$or": [
                        {"trainer_assignments.trainer_id": current_user.id},
                        {"assistant_coordinator_ids": current_user.id}
                    ]
                }
            ]
        }
    elif current_user.role == "assistant_admin":
        # Asst Admin sees all non-completed sessions (like admin) OR sessions where they're assistant coordinator
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},  # Not archived
                {
                    "$or": [
                        {"completion_status": {"$exists": False}},  # Legacy: No completion_status field
                        {"completion_status": "ongoing"},  # Ongoing sessions
                        {"completion_status": {"$nin": ["completed", "archived"]}}  # Not completed or archived
                    ]
                }
            ]
        }
    else:
        # Coordinators/Admin: Show all non-completed sessions (regardless of end_date)
        # Sessions only disappear when marked as completed by coordinator
        query = {
            "$and": [
                {"is_archived": {"$ne": True}},  # Not archived
                {
                    "$or": [
                        {"completion_status": {"$exists": False}},  # Legacy: No completion_status field
                        {"completion_status": "ongoing"},  # Ongoing sessions
                        {"completion_status": {"$nin": ["completed", "archived"]}}  # Not completed or archived
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
    
    # Add role-specific filters
    if current_user.role not in ["admin", "trainer"]:
        query["$and"].append({"status": "active"})
    
    if current_user.role == "participant":
        query["$and"].append({"participant_ids": current_user.id})
        sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
        
        # Auto-create participant_access records for each session
        for session in sessions:
            await get_or_create_participant_access(current_user.id, session['id'])
    elif current_user.role == "supervisor":
        query["$and"].append({"supervisor_ids": current_user.id})
        sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    else:
        sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich sessions with company and program data
    for session in sessions:
        if isinstance(session.get('created_at'), str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
        
        # Get company info
        if session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
        else:
            session["company_name"] = "Unknown"
        
        # Get program info
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name", "Unknown") if program else "Unknown"
        else:
            session["program_name"] = "Unknown"
    
    # Apply text search filter (after enrichment to search company/program names)
    if search:
        search_lower = search.lower()
        sessions = [
            s for s in sessions
            if search_lower in s.get("name", "").lower()
            or search_lower in s.get("company_name", "").lower()
            or search_lower in s.get("program_name", "").lower()
            or search_lower in s.get("location", "").lower()
        ]
    
    return sessions

@api_router.put("/sessions/{session_id}/toggle-status")
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

@api_router.get("/sessions/past-training")
async def get_past_training_sessions(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get archived/past training sessions with filtering by month and year"""
    if current_user.role not in ["admin", "coordinator", "assistant_admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Debug: log received parameters
    print(f"Past training request - month: {month}, year: {year}, role: {current_user.role}")
    
    # Build query based on user role and archival rules
    current_date = get_malaysia_time().date()
    current_date_str = current_date.isoformat()
    
    if current_user.role == "trainer":
        # For trainers: Show sessions that are either:
        # 1. Completed by coordinator, OR
        # 2. End date has passed (automatically moved to past training)
        # AND trainer must be assigned to the session
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
    else:
        # For admin/coordinator/assistant_admin: Show sessions marked as completed
        query = {
            "$or": [
                {"completed_by_coordinator": True},
                {"completion_status": "completed"},
                {"completion_status": "archived"},
                {"is_archived": True}
            ]
        }
    
    # Add date filtering if provided
    if month and year:
        # Filter by sessions that ended in the specified month/year
        start_of_month = f"{year}-{month:02d}-01"
        if month == 12:
            end_of_month = f"{year+1}-01-01"
        else:
            end_of_month = f"{year}-{month+1:02d}-01"
        
        # Combine with existing query using $and
        date_filter = {
            "end_date": {
                "$gte": start_of_month,
                "$lt": end_of_month
            }
        }
        
        # Wrap existing query with the date filter
        if "$and" in query:
            query["$and"].append(date_filter)
        else:
            query = {"$and": [query, date_filter]}
    
    # Get matching sessions
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with company and program data
    for session in sessions:
        # Get company info
        if session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
        else:
            session["company_name"] = "Unknown"
        
        # Get program info
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name", "Unknown") if program else "Unknown"
        else:
            session["program_name"] = "Unknown"
    
    return sessions

@api_router.get("/sessions/calendar")
async def get_calendar_sessions(current_user: User = Depends(get_current_user)):
    """Get sessions for calendar view (shows all sessions from past year to next year)"""
    if current_user.role not in ["admin", "coordinator", "assistant_admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get all sessions from 1 year ago to 1 year in future
    current_date = get_malaysia_time().date()
    one_year_ago = current_date.replace(year=current_date.year - 1)
    one_year_from_now = current_date.replace(year=current_date.year + 1)
    
    query = {
        "start_date": {
            "$gte": one_year_ago.isoformat(),
            "$lte": one_year_from_now.isoformat()
        }
    }
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with company and program data for calendar display
    for session in sessions:
        # Get company info
        if session.get("company_id"):
            company = await db.companies.find_one({"id": session["company_id"]}, {"_id": 0})
            session["company_name"] = company.get("name", "Unknown") if company else "Unknown"
        else:
            session["company_name"] = "Unknown"
        
        # Get program info
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session["program_id"]}, {"_id": 0})
            session["program_name"] = program.get("name", "Unknown") if program else "Unknown"
        else:
            session["program_name"] = "Unknown"
        
        # Add participant count
        session["participant_count"] = len(session.get("participant_ids", []))
    
    return sessions

@api_router.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str, current_user: User = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if isinstance(session.get('created_at'), str):
        session['created_at'] = datetime.fromisoformat(session['created_at'])
    
    return session

@api_router.get("/sessions/{session_id}/participants")
async def get_session_participants(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can view participants")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participants = []
    for participant_id in session['participant_ids']:
        user_doc = await db.users.find_one({"id": participant_id}, {"_id": 0, "password": 0})
        if user_doc:
            if isinstance(user_doc.get('created_at'), str):
                user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
            
            access = await get_or_create_participant_access(participant_id, session_id)
            
            participants.append({
                "user": user_doc,
                "access": access.model_dump()
            })
    
    return participants

@api_router.post("/sessions/{session_id}/participants")
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
    
    # participant_ids is a list of IC numbers or user IDs
    ids_to_add = participant_ids.get("participant_ids", [])
    if not ids_to_add:
        raise HTTPException(status_code=400, detail="No participant IDs provided")
    
    # Find users by IC number or user ID
    added_ids = []
    for identifier in ids_to_add:
        # Try to find by IC number first, then by user ID
        user = await db.users.find_one(
            {"$or": [{"id_number": identifier}, {"id": identifier}]},
            {"_id": 0, "id": 1}
        )
        if user:
            added_ids.append(user["id"])
        else:
            raise HTTPException(status_code=404, detail=f"User not found: {identifier}")
    
    # Get current participant list
    current_participants = session.get("participant_ids", [])
    
    # Add new participants (avoid duplicates)
    newly_added = []
    for user_id in added_ids:
        if user_id not in current_participants:
            current_participants.append(user_id)
            newly_added.append(user_id)
    
    # Update session
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"participant_ids": current_participants}}
    )
    
    # Create participant_access records for newly added participants
    # This ensures checklists and tests show up for trainers immediately
    for user_id in newly_added:
        await get_or_create_participant_access(user_id, session_id)
    
    return {
        "message": f"Successfully added {len(added_ids)} participant(s)",
        "added_count": len(added_ids)
    }


@api_router.get("/sessions/{session_id}/participants/enriched")
async def get_session_participants_enriched(session_id: str, current_user: User = Depends(get_current_user)):
    """
    Optimized endpoint that returns ALL participant data in ONE call.
    Includes: attendance, test results, checklists, feedback, vehicle details.
    """
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can view enriched participants")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get('participant_ids', [])
    if not participant_ids:
        return []
    
    # Fetch ALL data in bulk queries (much faster than individual calls)
    all_tests = await db.test_results.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    all_attendance = await db.attendance.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    all_checklists = await db.vehicle_checklists.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    all_feedback = await db.feedback.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    all_vehicles = await db.vehicle_details.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Build lookup dictionaries for O(1) access
    tests_by_participant = {}
    for t in all_tests:
        pid = t.get('participant_id')
        if pid not in tests_by_participant:
            tests_by_participant[pid] = []
        tests_by_participant[pid].append(t)
    
    attendance_by_participant = {}
    for a in all_attendance:
        pid = a.get('participant_id')
        if pid not in attendance_by_participant:
            attendance_by_participant[pid] = []
        attendance_by_participant[pid].append(a)
    
    checklists_by_participant = {c.get('participant_id'): c for c in all_checklists}
    feedback_by_participant = {f.get('participant_id'): f for f in all_feedback}
    vehicles_by_participant = {v.get('participant_id'): v for v in all_vehicles}
    
    # Enrich participants
    enriched = []
    for pid in participant_ids:
        user = await db.users.find_one({"id": pid}, {"_id": 0, "password": 0})
        if not user:
            continue
        
        # Get participant's data from lookup dicts
        tests = tests_by_participant.get(pid, [])
        pre_test = next((t for t in tests if t.get('test_type') == 'pre'), None)
        post_test = next((t for t in tests if t.get('test_type') == 'post'), None)
        
        attendance = attendance_by_participant.get(pid, [])
        has_clock_in = len(attendance) > 0 and attendance[0].get('clock_in')
        
        checklist = checklists_by_participant.get(pid)
        feedback = feedback_by_participant.get(pid)
        vehicle = vehicles_by_participant.get(pid)
        
        enriched.append({
            "id": user.get('id'),
            "full_name": user.get('full_name'),
            "email": user.get('email'),
            "id_number": user.get('id_number'),
            "phone_number": user.get('phone_number'),
            "sessionId": session_id,
            "attendance": attendance,
            "clockedIn": has_clock_in,
            "vehicleDetails": vehicle is not None,
            "preTest": {"score": pre_test.get('score'), "passed": pre_test.get('passed'), "completed": True} if pre_test else None,
            "postTest": {"score": post_test.get('score'), "passed": post_test.get('passed'), "completed": True} if post_test else None,
            "checklist": {"completed": True, "data": checklist} if checklist else None,
            "feedback": {"completed": True, "data": feedback} if feedback else None
        })
    
    return enriched


@api_router.post("/sessions/{session_id}/participants/bulk-upload")
async def bulk_upload_participants(
    session_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload participants from Excel file (xlsx or xls)
    
    Expected columns: "Full Name", "IC", "Company Name"
    IC format: UPPERCASE, no dashes
    Company: Exact match, creates new if not found
    """
    if current_user.role not in ["admin", "assistant_admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Check session exists
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate file format
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")
    
    try:
        # Read Excel file
        import pandas as pd
        import io
        
        contents = await file.read()
        
        # Try reading as xlsx first, then xls
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
        # Normalize column names (remove extra spaces, convert to lowercase for matching)
        df.columns = df.columns.str.strip()
        
        # Map alternative column names to standard names
        column_mappings = {
            'Full Name': ['Full Name', 'NAME', 'Name', 'FULL NAME', 'Full name'],
            'IC': ['IC', 'IC NUMBER', 'IC Number', 'Ic Number', 'IC_NUMBER', 'ic number'],
            'Company Name': ['Company Name', 'COMPANY NAME', 'Company name', 'COMPANY', 'Company']
        }
        
        # Find and rename columns
        final_columns = {}
        for standard_name, alternatives in column_mappings.items():
            found = False
            for alt in alternatives:
                if alt in df.columns:
                    final_columns[alt] = standard_name
                    found = True
                    break
            if not found:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required column: {standard_name}. Accepted names: {', '.join(alternatives[:3])}"
                )
        
        # Rename columns to standard names
        df.rename(columns=final_columns, inplace=True)
        
        # Validate data and collect errors
        errors = []
        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 because Excel rows start at 1 and we have header
            
            # Check for missing values
            if pd.isna(row['Full Name']) or str(row['Full Name']).strip() == '':
                errors.append(f"Row {row_num}: Missing Full Name")
            
            if pd.isna(row['IC']) or str(row['IC']).strip() == '':
                errors.append(f"Row {row_num}: Missing IC")
            
            if pd.isna(row['Company Name']) or str(row['Company Name']).strip() == '':
                errors.append(f"Row {row_num}: Missing Company Name")
        
        # If there are validation errors, stop and return them
        if errors:
            raise HTTPException(status_code=400, detail="Validation errors:\n" + "\n".join(errors))
        
        # Process participants
        added_participants = []
        created_companies = []
        
        for idx, row in df.iterrows():
            row_num = idx + 2
            
            # Format all fields: UPPERCASE, IC with no dashes
            ic_number = str(row['IC']).strip().upper().replace('-', '')
            full_name = str(row['Full Name']).strip().upper()
            company_name = str(row['Company Name']).strip().upper()
            
            # Find or create company
            company = await db.companies.find_one({"name": company_name}, {"_id": 0})
            if not company:
                # Create new company
                company_id = str(uuid.uuid4())
                company = {
                    "id": company_id,
                    "name": company_name,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.companies.insert_one({**company, "_id": company_id})
                created_companies.append(company_name)
            
            company_id = company["id"]
            
            # Check if user already exists
            existing_user = await db.users.find_one({"id_number": ic_number}, {"_id": 0})
            
            if existing_user:
                # User exists, just add to session
                user_id = existing_user["id"]
            else:
                # Create new participant
                user_id = str(uuid.uuid4())
                
                # Generate unique temp email
                temp_email = f"user_{user_id[:8]}@temp.mddrc.local"
                
                user_data = {
                    "id": user_id,
                    "email": temp_email,
                    "full_name": full_name,
                    "id_number": ic_number,
                    "password": pwd_context.hash("mddrc1"),
                    "role": "participant",
                    "company_id": company_id,
                    "location": "",
                    "phone_number": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                }
                
                await db.users.insert_one({**user_data, "_id": user_id})
            
            added_participants.append({
                "id": user_id,
                "name": full_name,
                "ic": ic_number,
                "company": company_name
            })
        
        # Add all participants to session
        current_participants = session.get("participant_ids", [])
        new_participant_ids = [p["id"] for p in added_participants]
        
        # Avoid duplicates
        for user_id in new_participant_ids:
            if user_id not in current_participants:
                current_participants.append(user_id)
        
        # Update session
        await db.sessions.update_one(
            {"id": session_id},
            {"$set": {"participant_ids": current_participants}}
        )
        
        # Create participant_access records
        for user_id in new_participant_ids:
            await get_or_create_participant_access(user_id, session_id)
        
        return {
            "message": "Bulk upload successful",
            "total_uploaded": len(added_participants),
            "participants": added_participants,
            "new_companies_created": created_companies if created_companies else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.put("/sessions/{session_id}")
async def update_session(session_id: str, session_data: dict, current_user: User = Depends(get_current_user)):
    # Allow admins to update any session, coordinators can update sessions they're assigned to
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if current_user.role == "coordinator":
        # Check if coordinator is assigned to this session
        if session.get("coordinator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update sessions assigned to you")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins and coordinators can update sessions")
    
    # Check if participant_ids changed (new participants added)
    old_participant_ids = set(session.get("participant_ids", []))
    new_participant_ids = set(session_data.get("participant_ids", []))
    newly_added_participants = new_participant_ids - old_participant_ids
    
    result = await db.sessions.update_one(
        {"id": session_id},
        {"$set": session_data}
    )
    
    # Return the updated session
    updated_session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    return updated_session

@api_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete sessions")
    
    # Get session first to verify it exists
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check for auto-draft invoices and save their numbers for reuse
    invoices = await db.invoices.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    saved_invoice_numbers = []
    
    for invoice in invoices:
        # Only save numbers from auto-draft invoices (never issued)
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
                    "is_available": True  # Can be reused
                })
                saved_invoice_numbers.append(invoice_number)
    
    # Delete ALL related data for this session
    total_deleted = 0
    
    # Delete the session itself first (uses "id" field)
    result = await db.sessions.delete_one({"id": session_id})
    total_deleted += result.deleted_count
    
    # Delete from related collections (use "session_id" field)
    related_collections = [
        "test_results",
        "course_feedback",
        "attendance",
        "attendance_records",
        "participant_attendance",
        "vehicle_checklists",
        "vehicle_details",
        "certificates",
        "participant_access",
        "training_reports",
        "chief_trainer_feedback",
        "coordinator_feedback",
        # Finance-related collections
        "trainer_fees",
        "coordinator_fees",
        "session_expenses",
        "invoices",
        "credit_notes",
        "marketing_commissions",
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


@api_router.get("/finance/deleted-invoice-numbers")
async def get_deleted_invoice_numbers(current_user: User = Depends(get_current_user)):
    """Get list of deleted invoice numbers available for reuse"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Admin or Finance access required")
    
    # Get available deleted invoice numbers
    deleted_numbers = await db.deleted_invoice_numbers.find(
        {"is_available": True},
        {"_id": 0}
    ).sort("invoice_number", 1).to_list(100)
    
    return deleted_numbers


@api_router.delete("/finance/deleted-invoice-numbers/{invoice_number}")
async def remove_deleted_invoice_number(invoice_number: str, current_user: User = Depends(get_current_user)):
    """Remove a deleted invoice number from the reuse pool (permanently discard)"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Admin or Finance access required")
    
    # URL decode the invoice number (slashes are encoded)
    import urllib.parse
    decoded_number = urllib.parse.unquote(invoice_number)
    
    result = await db.deleted_invoice_numbers.delete_one({"invoice_number": decoded_number})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice number not found in deleted pool")
    
    return {"message": f"Invoice number {decoded_number} removed from reuse pool"}


@api_router.delete("/sessions/bulk/delete-all")
async def delete_all_sessions(current_user: User = Depends(get_current_user)):
    """Delete ALL sessions and related data - for testing/cleanup purposes"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete all sessions")
    
    # Get all session IDs first
    all_sessions = await db.sessions.find({}, {"_id": 0, "id": 1}).to_list(1000)
    session_ids = [s["id"] for s in all_sessions]
    
    if not session_ids:
        return {
            "message": "No sessions to delete",
            "sessions_deleted": 0,
            "total_records_deleted": 0
        }
    
    total_deleted = 0
    
    # Collections to clean
    collections_to_clean = [
        "sessions",
        "test_results",
        "course_feedback",
        "attendance",
        "attendance_records",
        "participant_attendance",
        "vehicle_checklists",
        "vehicle_details",
        "certificates",
        "participant_access",
        "training_reports",
        "chief_trainer_feedback",
        "coordinator_feedback",
    ]
    
    # Delete from all collections
    for collection_name in collections_to_clean:
        result = await db[collection_name].delete_many({})
        total_deleted += result.deleted_count
    
    return {
        "message": f"All sessions and related data deleted successfully",
        "sessions_deleted": len(session_ids),
        "total_records_deleted": total_deleted
    }


# Participant Access Routes
@api_router.post("/participant-access/update")
async def update_participant_access(access_data: UpdateParticipantAccess, current_user: User = Depends(get_current_user)):
    # Allow admins and coordinators to update access
    if current_user.role == "coordinator":
        # Verify coordinator is assigned to this session
        session = await db.sessions.find_one({"id": access_data.session_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.get("coordinator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only manage access for sessions assigned to you")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins and coordinators can update access")
    
    await get_or_create_participant_access(access_data.participant_id, access_data.session_id)
    
    update_fields = {}
    if access_data.can_access_pre_test is not None:
        update_fields['can_access_pre_test'] = access_data.can_access_pre_test
    if access_data.can_access_post_test is not None:
        update_fields['can_access_post_test'] = access_data.can_access_post_test
    if access_data.can_access_checklist is not None:
        update_fields['can_access_checklist'] = access_data.can_access_checklist
    if access_data.can_access_feedback is not None:
        update_fields['can_access_feedback'] = access_data.can_access_feedback
    
    await db.participant_access.update_one(
        {"participant_id": access_data.participant_id, "session_id": access_data.session_id},
        {"$set": update_fields}
    )
    
    return {"message": "Access updated successfully"}

@api_router.get("/participant-access/{session_id}")
async def get_my_access(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can check access")
    
    access = await get_or_create_participant_access(current_user.id, session_id)
    return access

@api_router.get("/participant-access/session/{session_id}")
async def get_session_access(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all participant access records for a session"""
    # Get session to check permissions
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check permissions - admin, coordinator, assistant_admin can always access
    # Trainers can access if they're assigned to the session or are assistant coordinators
    can_access = False
    if current_user.role in ["coordinator", "admin", "assistant_admin"]:
        can_access = True
    elif current_user.role == "trainer":
        # Check if trainer is assigned to this session
        trainer_ids = [t.get("trainer_id") for t in session.get("trainer_assignments", [])]
        assistant_coord_ids = session.get("assistant_coordinator_ids", [])
        if current_user.id in trainer_ids or current_user.id in assistant_coord_ids:
            can_access = True
    
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied")
    
    access_records = await db.participant_access.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    return access_records

@api_router.post("/participant-access/session/{session_id}/toggle")
async def toggle_session_access(session_id: str, access_data: dict, current_user: User = Depends(get_current_user)):
    """Toggle access for all participants in a session (coordinator/admin/trainer/assistant_admin)"""
    # Get session to check permissions
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check permissions - admin, coordinator, assistant_admin can always access
    # Trainers can access if they're assigned to the session or are assistant coordinators
    can_access = False
    if current_user.role in ["coordinator", "admin", "assistant_admin"]:
        can_access = True
    elif current_user.role == "trainer":
        # Check if trainer is assigned to this session
        trainer_ids = [t.get("trainer_id") for t in session.get("trainer_assignments", [])]
        assistant_coord_ids = session.get("assistant_coordinator_ids", [])
        if current_user.id in trainer_ids or current_user.id in assistant_coord_ids:
            can_access = True
    
    if not can_access:
        raise HTTPException(status_code=403, detail="You don't have permission to control access for this session")
    
    access_type = access_data.get("access_type")
    enabled = access_data.get("enabled", False)
    
    # Map access_type to field name
    field_mapping = {
        "pre_test": "can_access_pre_test",
        "post_test": "can_access_post_test",
        "feedback": "can_access_feedback",
        "checklist": "can_access_checklist",
        "clock_out": "can_clock_out"
    }
    
    if access_type not in field_mapping:
        raise HTTPException(status_code=400, detail="Invalid access type")
    
    field_name = field_mapping[access_type]
    
    # Update all participant access records for this session
    participant_ids = session.get("participant_ids", [])
    
    for participant_id in participant_ids:
        # Ensure access record exists
        await get_or_create_participant_access(participant_id, session_id)
        
        # Update the field
        await db.participant_access.update_one(
            {"participant_id": participant_id, "session_id": session_id},
            {"$set": {field_name: enabled}}
        )
    
    status_text = "enabled" if enabled else "disabled"
    return {"message": f"{access_type} access {status_text} for {len(participant_ids)} participants"}

# Coordinator Control Routes
@api_router.post("/sessions/{session_id}/release-pre-test")
async def release_pre_test(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can release tests")
    
    # Get session to verify it exists
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update all participant access records for this session
    result = await db.participant_access.update_many(
        {"session_id": session_id},
        {"$set": {"can_access_pre_test": True}}
    )
    
    return {"message": f"Pre-test released to {result.modified_count} participants"}

@api_router.post("/sessions/{session_id}/release-post-test")
async def release_post_test(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can release tests")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await db.participant_access.update_many(
        {"session_id": session_id},
        {"$set": {"can_access_post_test": True}}
    )
    
    return {"message": f"Post-test released to {result.modified_count} participants"}

@api_router.post("/sessions/{session_id}/release-feedback")
async def release_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can release feedback")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await db.participant_access.update_many(
        {"session_id": session_id},
        {"$set": {"can_access_feedback": True}}
    )
    
    return {"message": f"Feedback form released to {result.modified_count} participants"}

@api_router.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "coordinator", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all participant access records
    access_records = await db.participant_access.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    
    total_participants = len(access_records)
    pre_test_released = any(a.get('can_access_pre_test', False) for a in access_records)
    post_test_released = any(a.get('can_access_post_test', False) for a in access_records)
    feedback_released = any(a.get('can_access_feedback', False) for a in access_records)
    
    pre_test_completed = sum(1 for a in access_records if a.get('pre_test_completed', False))
    post_test_completed = sum(1 for a in access_records if a.get('post_test_completed', False))
    feedback_submitted = sum(1 for a in access_records if a.get('feedback_submitted', False))
    
    return {
        "session_id": session_id,
        "session_name": session.get('name', ''),
        "total_participants": total_participants,
        "pre_test": {
            "released": pre_test_released,
            "completed": pre_test_completed
        },
        "post_test": {
            "released": post_test_released,
            "completed": post_test_completed
        },
        "feedback": {
            "released": feedback_released,
            "submitted": feedback_submitted
        }
    }

@api_router.post("/sessions/{session_id}/participants/{participant_id}/attendance")
async def mark_participant_attendance(
    session_id: str,
    participant_id: str,
    status: str,  # "present" or "absent"
    current_user: User = Depends(get_current_user)
):
    """Mark participant as present or absent for a session"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can mark attendance")
    
    if status not in ["present", "absent"]:
        raise HTTPException(status_code=400, detail="Status must be 'present' or 'absent'")
    
    # Check if session exists
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if participant is in this session
    if participant_id not in session.get("participant_ids", []):
        raise HTTPException(status_code=400, detail="Participant not enrolled in this session")
    
    # Update or create attendance record
    await db.participant_attendance.update_one(
        {
            "session_id": session_id,
            "participant_id": participant_id
        },
        {
            "$set": {
                "status": status,
                "marked_by": current_user.id,
                "marked_at": get_malaysia_time().isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "message": f"Participant marked as {status}",
        "status": status
    }

@api_router.get("/sessions/{session_id}/participants/attendance")
async def get_session_attendance_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get attendance status for all participants in a session"""
    if current_user.role not in ["coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get all attendance records for this session
    attendance_records = await db.participant_attendance.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Return as dictionary with participant_id as key
    attendance_dict = {record["participant_id"]: record["status"] for record in attendance_records}
    
    return attendance_dict

@api_router.get("/sessions/{session_id}/completion-checklist")
async def get_completion_checklist(session_id: str, current_user: User = Depends(get_current_user)):
    """Get checklist status for session completion (training report upload status)"""
    if current_user.role not in ["coordinator", "admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Check if training report is uploaded
    training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    checklist = {
        "can_complete": False,
        "items": {
            "training_report_uploaded": {
                "completed": bool(training_report and training_report.get("final_pdf_filename")),
                "label": "Final Training Report (PDF) Uploaded",
                "required": True
            }
        }
    }
    
    # Check if all required items are completed
    checklist["can_complete"] = all(
        item["completed"] for item in checklist["items"].values() if item["required"]
    )
    
    return checklist

@api_router.post("/sessions/{session_id}/mark-completed")
async def mark_session_completed(session_id: str, current_user: User = Depends(get_current_user)):
    """Mark session as completed by coordinator - archives session and pushes report to supervisors"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can mark sessions as completed")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # VALIDATION: Check if training report is uploaded (required before completing)
    training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    if not training_report or not training_report.get("final_pdf_filename"):
        raise HTTPException(
            status_code=400, 
            detail="Training report must be uploaded before marking session as completed. Please upload the final PDF report first."
        )
    
    # Update session completion status and archive
    await db.sessions.update_one(
        {"id": session_id},
        {
            "$set": {
                "completion_status": "completed",
                "completed_by_coordinator": True,
                "completed_date": get_malaysia_time().isoformat(),
                "report_available_to_supervisors": True  # Flag to indicate report is now available
            }
        }
    )
    
    # Update training report to mark as available to supervisors
    await db.training_reports.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "available_to_supervisors": True,
                "pushed_to_supervisors_at": get_malaysia_time().isoformat()
            }
        }
    )
    
    return {
        "message": "Session marked as completed successfully. Report is now available to supervisors.",
        "session_archived": True,
        "report_pushed_to_supervisors": True
    }

@api_router.get("/sessions/{session_id}/results-summary")
async def get_results_summary(session_id: str, current_user: User = Depends(get_current_user)):
    # Check if user has permission (admin, coordinator, or chief trainer)
    if current_user.role not in ["admin", "coordinator", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get all participants in the session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    participant_ids = session.get('participant_ids', [])
    
    # Get participant details
    participants = await db.users.find(
        {"id": {"$in": participant_ids}},
        {"_id": 0, "password": 0}
    ).to_list(1000)
    
    # Get test results for all participants
    test_results = await db.test_results.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Get feedback for all participants
    feedbacks = await db.course_feedback.find(
        {"session_id": session_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Build summary
    summary = []
    for participant in participants:
        p_results = [r for r in test_results if r['participant_id'] == participant['id']]
        p_feedback = next((f for f in feedbacks if f['participant_id'] == participant['id']), None)
        
        pre_test = next((r for r in p_results if r['test_type'] == 'pre'), None)
        post_test = next((r for r in p_results if r['test_type'] == 'post'), None)
        
        summary.append({
            "participant": {
                "id": participant['id'],
                "name": participant['full_name'],
                "email": participant['email']
            },
            "pre_test": {
                "completed": pre_test is not None,
                "score": pre_test['score'] if pre_test else 0,
                "correct": pre_test['correct_answers'] if pre_test else 0,
                "total": pre_test['total_questions'] if pre_test else 0,
                "passed": pre_test['passed'] if pre_test else False,
                "result_id": pre_test['id'] if pre_test else None
            },
            "post_test": {
                "completed": post_test is not None,
                "score": post_test['score'] if post_test else 0,
                "correct": post_test['correct_answers'] if post_test else 0,
                "total": post_test['total_questions'] if post_test else 0,
                "passed": post_test['passed'] if post_test else False,
                "result_id": post_test['id'] if post_test else None
            },
            "feedback_submitted": p_feedback is not None
        })
    
    return {
        "session_id": session_id,
        "session_name": session.get('name', ''),
        "program_id": session.get('program_id', ''),
        "participants": summary
    }

# User Routes
@api_router.get("/users", response_model=List[User])
async def get_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "supervisor", "coordinator", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    query = {}
    
    # Role filter
    if role:
        query["role"] = role
    
    # Company filter
    if company_id:
        query["company_id"] = company_id
    
    # Search filter (name, email, id_number)
    if search:
        search_pattern = {"$regex": search, "$options": "i"}  # Case-insensitive
        query["$or"] = [
            {"full_name": search_pattern},
            {"email": search_pattern},
            {"id_number": search_pattern}
        ]
    
    users = await db.users.find(query, {"_id": 0, "password": 0}).to_list(1000)
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    return users

# Export participants with contact details (Admin only)
# MUST be before /users/{user_id} to avoid route conflict
@api_router.get("/users/export/participants")
async def export_participants_csv(
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Export participant contact details to CSV - Admin only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can export participant data")
    
    # Build query
    query = {"role": "participant"}
    if company_id:
        query["company_id"] = company_id
    
    # Get participants
    participants = await db.users.find(query, {"_id": 0, "password": 0}).to_list(5000)
    
    # If session_id provided, filter to only that session's participants
    if session_id:
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        if session:
            session_participant_ids = set(session.get("participant_ids", []))
            participants = [p for p in participants if p.get("id") in session_participant_ids]
    
    # Build CSV
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Full Name", "IC Number", "Login Email", "Contact Email", "Contact Phone",
        "Company", "Profile Verified", "Indemnity Accepted", "Created At"
    ])
    
    # Get company names
    company_ids = list(set(p.get("company_id") for p in participants if p.get("company_id")))
    companies = await db.companies.find({"id": {"$in": company_ids}}, {"_id": 0}).to_list(500)
    company_map = {c["id"]: c.get("name", "") for c in companies}
    
    # Data rows
    for p in participants:
        writer.writerow([
            p.get("full_name", ""),
            p.get("id_number", ""),
            p.get("email", ""),
            p.get("contact_email", ""),
            p.get("contact_phone", ""),
            company_map.get(p.get("company_id"), p.get("company_id", "")),
            "Yes" if p.get("profile_verified") else "No",
            "Yes" if p.get("indemnity_accepted") else "No",
            p.get("created_at", "")[:10] if p.get("created_at") else ""
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants_export.csv"}
    )

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Allow access if: admin, supervisor, or the user themselves
    if current_user.role not in ["admin", "supervisor", "trainer", "coordinator"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return user

# Test Routes
@api_router.post("/tests", response_model=Test)
async def create_test(test_data: TestCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can create tests")
    
    test_obj = Test(**test_data.model_dump())
    doc = test_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.tests.insert_one(doc)
    return test_obj

@api_router.get("/tests/program/{program_id}", response_model=List[Test])
async def get_tests_by_program(program_id: str, current_user: User = Depends(get_current_user)):
    tests = await db.tests.find({"program_id": program_id}, {"_id": 0}).to_list(100)
    for test in tests:
        if isinstance(test.get('created_at'), str):
            test['created_at'] = datetime.fromisoformat(test['created_at'])
    return tests

@api_router.delete("/tests/{test_id}")
async def delete_test(test_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete tests")
    
    result = await db.tests.delete_one({"id": test_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {"message": "Test deleted successfully"}


@api_router.post("/tests/bulk-upload")
async def bulk_upload_test_questions(
    file: UploadFile = File(...),
    program_id: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload test questions from Excel file
    
    Simplified format (when program_id is provided):
    - Question Text, Option A, Option B, Option C, Option D, Correct Answer, Points
    
    Legacy format (when program_id not provided):
    - Program Name, Question Type, Question Text, Option A, Option B, Option C, Option D, Correct Answer, Points
    """
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Validate file format
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")
    
    try:
        import pandas as pd
        import io
        
        contents = await file.read()
        
        # Try reading as xlsx first, then xls
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
        # Normalize column names
        df.columns = df.columns.str.strip()
        
        # Check if we're using the simplified format (program_id provided)
        use_simplified_format = program_id is not None
        
        if use_simplified_format:
            # Verify program exists
            program = await db.programs.find_one({"id": program_id}, {"_id": 0})
            if not program:
                raise HTTPException(status_code=404, detail="Program not found")
            
            # Simplified column mappings - no Program Name or Question Type needed
            column_mappings = {
                'Question Text': ['Question Text', 'QUESTION TEXT', 'Question', 'QUESTION'],
                'Option A': ['Option A', 'OPTION A', 'A'],
                'Option B': ['Option B', 'OPTION B', 'B'],
                'Option C': ['Option C', 'OPTION C', 'C'],
                'Option D': ['Option D', 'OPTION D', 'D'],
                'Correct Answer': ['Correct Answer', 'CORRECT ANSWER', 'Answer', 'ANSWER', 'Correct'],
                'Points': ['Points', 'POINTS', 'Score', 'SCORE']
            }
        else:
            # Legacy column mappings
            column_mappings = {
                'Program Name': ['Program Name', 'PROGRAM NAME', 'Program', 'PROGRAM'],
                'Question Type': ['Question Type', 'QUESTION TYPE', 'Type', 'TYPE'],
                'Question Text': ['Question Text', 'QUESTION TEXT', 'Question', 'QUESTION'],
                'Option A': ['Option A', 'OPTION A', 'A'],
                'Option B': ['Option B', 'OPTION B', 'B'],
                'Option C': ['Option C', 'OPTION C', 'C'],
                'Option D': ['Option D', 'OPTION D', 'D'],
                'Correct Answer': ['Correct Answer', 'CORRECT ANSWER', 'Answer', 'ANSWER', 'Correct'],
                'Points': ['Points', 'POINTS', 'Score', 'SCORE']
            }
        
        # Find and rename columns
        final_columns = {}
        missing_required = []
        for standard_name, alternatives in column_mappings.items():
            found = False
            for alt in alternatives:
                if alt in df.columns:
                    final_columns[alt] = standard_name
                    found = True
                    break
            # Points is optional
            if not found and standard_name != 'Points':
                missing_required.append(standard_name)
        
        if missing_required:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required column(s): {', '.join(missing_required)}"
            )
        
        df.rename(columns=final_columns, inplace=True)
        
        # Validate data
        errors = []
        for idx, row in df.iterrows():
            row_num = idx + 2
            
            if not use_simplified_format:
                if pd.isna(row.get('Program Name')) or str(row.get('Program Name', '')).strip() == '':
                    errors.append(f"Row {row_num}: Missing Program Name")
                if pd.isna(row.get('Question Type')) or str(row.get('Question Type', '')).strip() == '':
                    errors.append(f"Row {row_num}: Missing Question Type")
                elif str(row.get('Question Type', '')).lower() not in ['pre_test', 'post_test', 'pre', 'post']:
                    errors.append(f"Row {row_num}: Question Type must be 'pre_test' or 'post_test'")
            
            if pd.isna(row.get('Question Text')) or str(row.get('Question Text', '')).strip() == '':
                errors.append(f"Row {row_num}: Missing Question Text")
            if pd.isna(row.get('Correct Answer')) or str(row.get('Correct Answer', '')).strip() == '':
                errors.append(f"Row {row_num}: Missing Correct Answer")
            elif str(row.get('Correct Answer', '')).strip().upper() not in ['A', 'B', 'C', 'D']:
                errors.append(f"Row {row_num}: Correct Answer must be A, B, C, or D")
        
        if errors:
            raise HTTPException(status_code=400, detail="Validation errors:\n" + "\n".join(errors[:10]))
        
        # Process questions
        if use_simplified_format:
            # Simplified flow: All questions go to this program for both pre and post tests
            questions_list = []
            for idx, row in df.iterrows():
                correct_answer = str(row['Correct Answer']).strip().upper()
                correct_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}.get(correct_answer, 0)
                
                questions_list.append({
                    "question_text": str(row['Question Text']).strip(),
                    "options": [
                        str(row.get('Option A', '')).strip() if pd.notna(row.get('Option A')) else "",
                        str(row.get('Option B', '')).strip() if pd.notna(row.get('Option B')) else "",
                        str(row.get('Option C', '')).strip() if pd.notna(row.get('Option C')) else "",
                        str(row.get('Option D', '')).strip() if pd.notna(row.get('Option D')) else ""
                    ],
                    "correct_answer": correct_index,
                    "points": int(row['Points']) if 'Points' in df.columns and pd.notna(row.get('Points')) else 5
                })
            
            # Delete existing tests for this program
            await db.tests.delete_many({"program_id": program_id})
            
            # Create pre and post tests with same questions
            now = get_malaysia_time().isoformat()
            
            await db.tests.insert_one({
                "id": str(uuid.uuid4()),
                "program_id": program_id,
                "title": f"{program['name']} - Pre-Test",
                "test_type": "pre",
                "questions": questions_list,
                "created_at": now
            })
            
            await db.tests.insert_one({
                "id": str(uuid.uuid4()),
                "program_id": program_id,
                "title": f"{program['name']} - Post-Test",
                "test_type": "post",
                "questions": questions_list,
                "created_at": now
            })
            
            return {
                "message": "Questions uploaded successfully",
                "total_uploaded": len(questions_list),
                "program": program['name']
            }
        
        # Legacy flow for backward compatibility
        added_questions = []
        programs_not_found = []
        
        for idx, row in df.iterrows():
            program_name = str(row['Program Name']).strip()
            
            # Find program
            prog = await db.programs.find_one({"name": program_name}, {"_id": 0})
            if not prog:
                if program_name not in programs_not_found:
                    programs_not_found.append(program_name)
                continue
            
            # Normalize question type
            question_type = str(row['Question Type']).lower().strip()
            if question_type == 'pre':
                question_type = 'pre_test'
            elif question_type == 'post':
                question_type = 'post_test'
            
            correct_answer = str(row['Correct Answer']).strip().upper()
            correct_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}.get(correct_answer, 0)
            
            # Create test question
            test_id = str(uuid.uuid4())
            test_data = {
                "id": test_id,
                "program_id": prog["id"],
                "test_type": question_type,
                "questions": [
                    {
                        "question_text": str(row['Question Text']).strip(),
                        "options": [
                            str(row['Option A']).strip() if pd.notna(row['Option A']) else "",
                            str(row['Option B']).strip() if pd.notna(row['Option B']) else "",
                            str(row['Option C']).strip() if pd.notna(row['Option C']) else "",
                            str(row['Option D']).strip() if pd.notna(row['Option D']) else ""
                        ],
                        "correct_answer": correct_index,
                        "points": int(row['Points']) if 'Points' in df.columns and pd.notna(row.get('Points')) else 5
                    }
                ],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Check if test already exists for this program and type
            existing_test = await db.tests.find_one(
                {"program_id": prog["id"], "test_type": question_type},
                {"_id": 0}
            )
            
            if existing_test:
                # Append question to existing test
                await db.tests.update_one(
                    {"id": existing_test["id"]},
                    {"$push": {"questions": test_data["questions"][0]}}
                )
                added_questions.append({
                    "program": program_name,
                    "type": question_type,
                    "action": "added_to_existing_test"
                })
            else:
                # Create new test
                await db.tests.insert_one({**test_data, "_id": test_id})
                added_questions.append({
                    "program": program_name,
                    "type": question_type,
                    "action": "created_new_test"
                })
        
        response = {
            "message": "Bulk upload successful",
            "total_uploaded": len(added_questions),
            "questions": added_questions
        }
        
        if programs_not_found:
            response["warnings"] = f"Programs not found: {', '.join(programs_not_found)}"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.post("/checklist-templates/bulk-upload")
async def bulk_upload_checklist_items(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload checklist items from Excel file
    
    Expected columns: Program Name, Item Name
    """
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")
    
    try:
        import pandas as pd
        import io
        
        contents = await file.read()
        
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
        df.columns = df.columns.str.strip()
        
        # Map columns
        column_mappings = {
            'Program Name': ['Program Name', 'PROGRAM NAME', 'Program', 'PROGRAM'],
            'Item Name': ['Item Name', 'ITEM NAME', 'Item', 'ITEM', 'Checklist Item']
        }
        
        final_columns = {}
        for standard_name, alternatives in column_mappings.items():
            found = False
            for alt in alternatives:
                if alt in df.columns:
                    final_columns[alt] = standard_name
                    found = True
                    break
            if not found:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required column: {standard_name}"
                )
        
        df.rename(columns=final_columns, inplace=True)
        
        # Validate
        errors = []
        for idx, row in df.iterrows():
            row_num = idx + 2
            if pd.isna(row['Program Name']) or str(row['Program Name']).strip() == '':
                errors.append(f"Row {row_num}: Missing Program Name")
            if pd.isna(row['Item Name']) or str(row['Item Name']).strip() == '':
                errors.append(f"Row {row_num}: Missing Item Name")
        
        if errors:
            raise HTTPException(status_code=400, detail="Validation errors:\n" + "\n".join(errors))
        
        # Process items
        added_items = []
        programs_not_found = []
        
        for idx, row in df.iterrows():
            program_name = str(row['Program Name']).strip()
            item_name = str(row['Item Name']).strip()
            
            # Find program
            program = await db.programs.find_one({"name": program_name}, {"_id": 0})
            if not program:
                if program_name not in programs_not_found:
                    programs_not_found.append(program_name)
                continue
            
            # Check if checklist template exists for this program
            template = await db.checklist_templates.find_one(
                {"program_id": program["id"]},
                {"_id": 0}
            )
            
            if template:
                # Add item to existing template
                await db.checklist_templates.update_one(
                    {"id": template["id"]},
                    {"$push": {"items": item_name}}
                )
                added_items.append({
                    "program": program_name,
                    "item": item_name,
                    "action": "added_to_existing_template"
                })
            else:
                # Create new template
                template_id = str(uuid.uuid4())
                template_data = {
                    "id": template_id,
                    "program_id": program["id"],
                    "items": [item_name],
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.checklist_templates.insert_one({**template_data, "_id": template_id})
                added_items.append({
                    "program": program_name,
                    "item": item_name,
                    "action": "created_new_template"
                })
        
        response = {
            "message": "Bulk upload successful",
            "total_uploaded": len(added_items),
            "items": added_items
        }
        
        if programs_not_found:
            response["warnings"] = f"Programs not found: {', '.join(programs_not_found)}"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.post("/feedback-templates/bulk-upload")
async def bulk_upload_feedback_questions(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Bulk upload feedback questions from Excel file
    
    Expected columns: Program Name, Question Text, Question Type, Options
    """
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")
    
    try:
        import pandas as pd
        import io
        
        contents = await file.read()
        
        try:
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(io.BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
        
        df.columns = df.columns.str.strip()
        
        # Map columns
        column_mappings = {
            'Program Name': ['Program Name', 'PROGRAM NAME', 'Program', 'PROGRAM'],
            'Question Text': ['Question Text', 'QUESTION TEXT', 'Question', 'QUESTION'],
            'Question Type': ['Question Type', 'QUESTION TYPE', 'Type', 'TYPE'],
            'Options': ['Options', 'OPTIONS', 'Choices', 'CHOICES']
        }
        
        final_columns = {}
        for standard_name, alternatives in column_mappings.items():
            found = False
            for alt in alternatives:
                if alt in df.columns:
                    final_columns[alt] = standard_name
                    found = True
                    break
            if not found and standard_name != 'Options':  # Options is optional
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required column: {standard_name}"
                )
        
        df.rename(columns=final_columns, inplace=True)
        
        # Validate
        errors = []
        for idx, row in df.iterrows():
            row_num = idx + 2
            if pd.isna(row['Program Name']) or str(row['Program Name']).strip() == '':
                errors.append(f"Row {row_num}: Missing Program Name")
            if pd.isna(row['Question Text']) or str(row['Question Text']).strip() == '':
                errors.append(f"Row {row_num}: Missing Question Text")
            if pd.isna(row['Question Type']) or str(row['Question Type']).strip() == '':
                errors.append(f"Row {row_num}: Missing Question Type")
            elif str(row['Question Type']).lower() not in ['rating', 'multiple_choice', 'text']:
                errors.append(f"Row {row_num}: Question Type must be 'rating', 'multiple_choice', or 'text'")
        
        if errors:
            raise HTTPException(status_code=400, detail="Validation errors:\n" + "\n".join(errors))
        
        # Process questions
        added_questions = []
        programs_not_found = []
        
        for idx, row in df.iterrows():
            program_name = str(row['Program Name']).strip()
            question_text = str(row['Question Text']).strip()
            question_type = str(row['Question Type']).lower().strip()
            
            # Parse options
            options = []
            if 'Options' in df.columns and pd.notna(row['Options']) and str(row['Options']).strip():
                options = [opt.strip() for opt in str(row['Options']).split(',')]
            
            # Find program
            program = await db.programs.find_one({"name": program_name}, {"_id": 0})
            if not program:
                if program_name not in programs_not_found:
                    programs_not_found.append(program_name)
                continue
            
            # Create feedback question
            question_data = {
                "question_text": question_text,
                "question_type": question_type,
                "options": options if question_type == "multiple_choice" else []
            }
            
            # Check if template exists
            template = await db.feedback_templates.find_one(
                {"program_id": program["id"]},
                {"_id": 0}
            )
            
            if template:
                # Add question to existing template
                await db.feedback_templates.update_one(
                    {"id": template["id"]},
                    {"$push": {"questions": question_data}}
                )
                added_questions.append({
                    "program": program_name,
                    "question": question_text,
                    "action": "added_to_existing_template"
                })
            else:
                # Create new template
                template_id = str(uuid.uuid4())
                template_data = {
                    "id": template_id,
                    "program_id": program["id"],
                    "questions": [question_data],
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.feedback_templates.insert_one({**template_data, "_id": template_id})
                added_questions.append({
                    "program": program_name,
                    "question": question_text,
                    "action": "created_new_template"
                })
        
        response = {
            "message": "Bulk upload successful",
            "total_uploaded": len(added_questions),
            "questions": added_questions
        }
        
        if programs_not_found:
            response["warnings"] = f"Programs not found: {', '.join(programs_not_found)}"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@api_router.get("/sessions/{session_id}/tests/available")
async def get_available_tests(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can access this")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get participant access
    access = await get_or_create_participant_access(current_user.id, session_id)
    
    # Get tests for the session's program
    tests = await db.tests.find({"program_id": session['program_id']}, {"_id": 0}).to_list(10)
    
    available_tests = []
    for test in tests:
        if isinstance(test.get('created_at'), str):
            test['created_at'] = datetime.fromisoformat(test['created_at'])
        
        test_type = test['test_type']
        can_access = False
        is_completed = False
        
        # Handle both "pre"/"post" and "pre_test"/"post_test" formats
        if test_type in ["pre", "pre_test"]:
            can_access = access.can_access_pre_test
            is_completed = access.pre_test_completed
        elif test_type in ["post", "post_test"]:
            can_access = access.can_access_post_test
            is_completed = access.post_test_completed
        
        if can_access and not is_completed:
            # Don't send correct answers to participant
            test_copy = test.copy()
            questions = test['questions'].copy()
            
            # Shuffle post-test questions
            if test_type == "post":
                random.shuffle(questions)
            
            test_copy['questions'] = [
                {
                    'question': q['question'],
                    'options': q['options']
                }
                for q in questions
            ]
            available_tests.append(test_copy)
    
    return available_tests

@api_router.get("/tests/{test_id}")
async def get_test(test_id: str, current_user: User = Depends(get_current_user)):
    test_doc = await db.tests.find_one({"id": test_id}, {"_id": 0})
    if not test_doc:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if isinstance(test_doc.get('created_at'), str):
        test_doc['created_at'] = datetime.fromisoformat(test_doc['created_at'])
    
    # Make a copy of questions for shuffling
    questions = test_doc['questions'].copy()
    
    # Shuffle post-test questions for participants
    if current_user.role == "participant" and test_doc['test_type'] == "post":
        random.shuffle(questions)
    
    # Don't send correct answers to participants before submission
    if current_user.role == "participant":
        test_doc['questions'] = [
            {
                'question': q['question'],
                'options': q['options'],
                'original_index': test_doc['questions'].index(q)  # Track original position
            }
            for q in questions
        ]
    else:
        test_doc['questions'] = questions
    
    return test_doc

@api_router.post("/tests/submit", response_model=TestResult)
async def submit_test(submission: TestSubmit, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can submit tests")
    
    test_doc = await db.tests.find_one({"id": submission.test_id}, {"_id": 0})
    if not test_doc:
        raise HTTPException(status_code=404, detail="Test not found")
    
    program_doc = await db.programs.find_one({"id": test_doc['program_id']}, {"_id": 0})
    pass_percentage = program_doc.get('pass_percentage', 70.0) if program_doc else 70.0
    
    questions = test_doc['questions']
    
    # Ensure both are integers for comparison
    correct = 0
    for i, ans in enumerate(submission.answers):
        if i < len(questions):
            # If question_indices provided (shuffled test), use original index
            if submission.question_indices and i < len(submission.question_indices):
                original_idx = submission.question_indices[i]
            else:
                original_idx = i
            
            if original_idx < len(questions):
                submitted_answer = int(ans)
                correct_answer = int(questions[original_idx]['correct_answer'])
                if submitted_answer == correct_answer:
                    correct += 1
    
    score = (correct / len(questions)) * 100 if questions else 0
    passed = score >= pass_percentage
    
    result_obj = TestResult(
        test_id=submission.test_id,
        participant_id=current_user.id,
        session_id=submission.session_id,
        test_type=test_doc['test_type'],
        answers=submission.answers,
        score=score,
        total_questions=len(questions),
        correct_answers=correct,
        passed=passed,
        question_indices=submission.question_indices  # Store the shuffled order
    )
    
    doc = result_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    await db.test_results.insert_one(doc)
    
    # Handle both "pre"/"post" and "pre_test"/"post_test" formats
    test_type = test_doc['test_type']
    if test_type in ['pre', 'pre_test']:
        update_field = 'pre_test_completed'
    else:
        update_field = 'post_test_completed'
    await db.participant_access.update_one(
        {"participant_id": current_user.id, "session_id": submission.session_id},
        {"$set": {update_field: True}}
    )
    
    return result_obj

@api_router.get("/tests/results/participant/{participant_id}", response_model=List[TestResult])
async def get_participant_results(participant_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role == "participant" and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    results = await db.test_results.find({"participant_id": participant_id}, {"_id": 0}).to_list(100)
    for result in results:
        if isinstance(result.get('submitted_at'), str):
            result['submitted_at'] = datetime.fromisoformat(result['submitted_at'])
        # Set default test_type if missing (for old records)
        if 'test_type' not in result:
            result['test_type'] = 'pre'
        # Set default total_questions and correct_answers if missing
        if 'total_questions' not in result:
            result['total_questions'] = len(result.get('answers', []))
        if 'correct_answers' not in result:
            result['correct_answers'] = int((result.get('score', 0) / 100) * result['total_questions'])
    return results

@api_router.put("/tests/results/{result_id}")
async def update_test_result(result_id: str, score: float, passed: bool, current_user: User = Depends(get_current_user)):
    """Update test result score and pass status - Super Admin only"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can update test results")
    
    result = await db.test_results.find_one({"id": result_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    await db.test_results.update_one(
        {"id": result_id},
        {"$set": {"score": score, "passed": passed}}
    )
    
    return {"message": "Test result updated successfully"}

@api_router.post("/tests/super-admin-submit", response_model=TestResult)
async def super_admin_submit_test(data: SuperAdminTestSubmit, current_user: User = Depends(get_current_user)):
    """Submit test on behalf of participant - Super Admin only"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit tests for participants")
    
    test_doc = await db.tests.find_one({"id": data.test_id}, {"_id": 0})
    if not test_doc:
        raise HTTPException(status_code=404, detail="Test not found")
    
    program_doc = await db.programs.find_one({"id": test_doc['program_id']}, {"_id": 0})
    pass_percentage = program_doc.get('pass_percentage', 70.0) if program_doc else 70.0
    
    questions = test_doc['questions']
    
    # Calculate correct answers from provided answers
    correct = 0
    for i, ans in enumerate(data.answers):
        if i < len(questions):
            submitted_answer = int(ans)
            correct_answer = int(questions[i]['correct_answer'])
            if submitted_answer == correct_answer:
                correct += 1
    
    score = (correct / len(questions)) * 100 if questions else 0
    passed = score >= pass_percentage
    
    result_obj = TestResult(
        test_id=data.test_id,
        participant_id=data.participant_id,
        session_id=data.session_id,
        test_type=test_doc['test_type'],
        answers=data.answers,
        score=score,
        total_questions=len(questions),
        correct_answers=correct,
        passed=passed
    )
    
    doc = result_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    # Check if test result already exists for this participant, session, and test type
    existing = await db.test_results.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id,
        "test_type": test_doc['test_type']
    })
    
    if existing:
        # Update existing test result
        await db.test_results.update_one(
            {
                "participant_id": data.participant_id,
                "session_id": data.session_id,
                "test_type": test_doc['test_type']
            },
            {"$set": {
                "test_id": data.test_id,
                "answers": data.answers,
                "score": score,
                "total_questions": len(questions),
                "correct_answers": correct,
                "passed": passed,
                "submitted_at": doc['submitted_at']
            }}
        )
    else:
        # Insert new test result
        await db.test_results.insert_one(doc)
    
    update_field = 'pre_test_completed' if test_doc['test_type'] == 'pre' else 'post_test_completed'
    await db.participant_access.update_one(
        {"participant_id": data.participant_id, "session_id": data.session_id},
        {"$set": {update_field: True}},
        upsert=True
    )
    
    return result_obj

class SuperAdminClockIn(BaseModel):
    session_id: str
    participant_id: str
    clock_in: str

class SuperAdminClockOut(BaseModel):
    session_id: str
    participant_id: str
    clock_out: str

@api_router.post("/super-admin/attendance/clock-in")
async def super_admin_clock_in(data: SuperAdminClockIn, current_user: User = Depends(get_current_user)):
    """Super admin clock in for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can manage attendance")
    
    # Parse the datetime and convert to Malaysian timezone for consistency
    clock_in_dt = datetime.fromisoformat(data.clock_in.replace('Z', '+00:00'))
    # Convert to Malaysia timezone
    clock_in_malaysia = clock_in_dt.astimezone(MALAYSIA_TZ)
    date_str = clock_in_malaysia.date().isoformat()
    time_str = clock_in_malaysia.strftime("%H:%M:%S")
    
    # Find existing attendance by participant and session ONLY (not date)
    # This ensures only ONE attendance record per participant per session
    existing = await db.attendance.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    }, {"_id": 0})
    
    if existing:
        # Update existing record with new date and time
        await db.attendance.update_one(
            {"id": existing['id']},
            {"$set": {
                "clock_in": time_str,
                "date": date_str
            }}
        )
    else:
        attendance_obj = Attendance(
            participant_id=data.participant_id,
            session_id=data.session_id,
            date=date_str,
            clock_in=time_str
        )
        doc = attendance_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.attendance.insert_one(doc)
    
    return {"message": "Attendance updated successfully"}

@api_router.post("/super-admin/attendance/clock-out")
async def super_admin_clock_out(data: SuperAdminClockOut, current_user: User = Depends(get_current_user)):
    """Super admin clock out for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can manage attendance")
    
    # Parse the datetime and convert to Malaysian timezone for consistency
    clock_out_dt = datetime.fromisoformat(data.clock_out.replace('Z', '+00:00'))
    # Convert to Malaysia timezone
    clock_out_malaysia = clock_out_dt.astimezone(MALAYSIA_TZ)
    date_str = clock_out_malaysia.date().isoformat()
    time_str = clock_out_malaysia.strftime("%H:%M:%S")
    
    # Find existing attendance by participant and session ONLY (not date)
    # This ensures we update the same single attendance record
    existing = await db.attendance.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    }, {"_id": 0})
    
    if existing:
        await db.attendance.update_one(
            {"id": existing['id']},
            {"$set": {"clock_out": time_str}}
        )
        return {"message": "Attendance updated successfully"}
    else:
        raise HTTPException(status_code=404, detail="No clock-in record found. Please clock in first.")

@api_router.post("/super-admin/checklist/submit")
async def super_admin_checklist_submit(data: SuperAdminChecklistSubmit, current_user: User = Depends(get_current_user)):
    """Super admin submit checklist for participant - same as trainer portal"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit checklists")
    
    # Get session to determine interval (default to "pre" if not specified)
    session = await db.sessions.find_one({"id": data.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # For Super Admin, use standardized interval to match trainer submissions
    checklist_obj = VehicleChecklist(
        participant_id=data.participant_id,
        session_id=data.session_id,
        interval="trainer_inspection",  # Use same interval as trainer for consistency
        checklist_items=data.checklist_items,
        verified_by="super_admin",
        verified_at=datetime.now(timezone.utc),
        verification_status="completed"
    )
    
    doc = checklist_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    doc['verified_at'] = doc['verified_at'].isoformat()
    
    # Use upsert to prevent duplicates - same as trainer endpoint
    await db.vehicle_checklists.update_one(
        {
            "participant_id": data.participant_id,
            "session_id": data.session_id
        },
        {"$set": doc},
        upsert=True
    )
    
    # Update participant_access to mark checklist as completed
    await db.participant_access.update_one(
        {
            "participant_id": data.participant_id,
            "session_id": data.session_id
        },
        {"$set": {"checklist_completed": True}},
        upsert=True
    )
    
    return {"message": "Checklist submitted successfully"}

@api_router.post("/super-admin/feedback/submit")
async def super_admin_feedback_submit(data: SuperAdminFeedbackSubmit, current_user: User = Depends(get_current_user)):
    """Super admin submit feedback for participant with actual responses"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit feedback")
    
    # Get session to fetch program_id
    session = await db.sessions.find_one({"id": data.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    program_id = session.get('program_id')
    if not program_id:
        raise HTTPException(status_code=400, detail="Session has no program_id")
    
    feedback_obj = CourseFeedback(
        participant_id=data.participant_id,
        session_id=data.session_id,
        program_id=program_id,
        responses=data.responses
    )
    
    doc = feedback_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    # Check if feedback already exists for this participant and session
    existing = await db.course_feedback.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    })
    
    if existing:
        # Update existing feedback
        await db.course_feedback.update_one(
            {"participant_id": data.participant_id, "session_id": data.session_id},
            {"$set": {
                "program_id": program_id,
                "responses": data.responses,
                "submitted_at": doc['submitted_at']
            }}
        )
    else:
        # Insert new feedback
        await db.course_feedback.insert_one(doc)
    
    # Update participant_access to mark feedback as completed
    await db.participant_access.update_one(
        {"participant_id": data.participant_id, "session_id": data.session_id},
        {"$set": {"feedback_completed": True}},
        upsert=True
    )
    
    return {"message": "Feedback submitted successfully"}

@api_router.post("/super-admin/vehicle-details")
async def super_admin_vehicle_details(data: SuperAdminVehicleDetails, current_user: User = Depends(get_current_user)):
    """Super admin submit vehicle details for participant"""
    if current_user.email != "arjuna@mddrc.com.my":
        raise HTTPException(status_code=403, detail="Only super admin can submit vehicle details")
    
    # Check if vehicle details already exist
    existing = await db.vehicle_details.find_one({
        "participant_id": data.participant_id,
        "session_id": data.session_id
    })
    
    if existing:
        # Update existing record
        await db.vehicle_details.update_one(
            {"participant_id": data.participant_id, "session_id": data.session_id},
            {"$set": {
                "vehicle_model": data.vehicle_model,
                "registration_number": data.registration_number,
                "roadtax_expiry": data.roadtax_expiry
            }}
        )
        return {"message": "Vehicle details updated successfully"}
    else:
        # Create new record
        vehicle_obj = VehicleDetails(
            participant_id=data.participant_id,
            session_id=data.session_id,
            vehicle_model=data.vehicle_model,
            registration_number=data.registration_number,
            roadtax_expiry=data.roadtax_expiry
        )
        
        doc = vehicle_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.vehicle_details.insert_one(doc)
        
        return {"message": "Vehicle details saved successfully"}

@api_router.get("/tests/results/session/{session_id}")
async def get_session_test_results(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all test results for a session (for coordinators/admins/trainers)"""
    if current_user.role not in ["coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    results = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    
    for result in results:
        if isinstance(result.get('submitted_at'), str):
            result['submitted_at'] = datetime.fromisoformat(result['submitted_at'])
    
    return results

@api_router.get("/tests/results/{result_id}")
async def get_test_result_detail(result_id: str, current_user: User = Depends(get_current_user)):
    result = await db.test_results.find_one({"id": result_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    # Participants can only see their own results
    if current_user.role == "participant" and result['participant_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    if isinstance(result.get('submitted_at'), str):
        result['submitted_at'] = datetime.fromisoformat(result['submitted_at'])
    
    # Get the test questions with correct answers
    test = await db.tests.find_one({"id": result['test_id']}, {"_id": 0})
    if test:
        questions = test['questions']
        
        # If question_indices exists (shuffled test), reorder questions to match participant's view
        if result.get('question_indices'):
            reordered_questions = []
            for idx in result['question_indices']:
                if idx < len(questions):
                    reordered_questions.append(questions[idx])
            result['test_questions'] = reordered_questions
        else:
            result['test_questions'] = questions
    
    return result

@api_router.get("/debug/database-info")
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

# Checklist Template Routes
@api_router.post("/checklist-templates", response_model=ChecklistTemplate)
async def create_checklist_template(template_data: ChecklistTemplateCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can create checklist templates")
    
    existing = await db.checklist_templates.find_one({"program_id": template_data.program_id}, {"_id": 0})
    if existing:
        await db.checklist_templates.update_one(
            {"program_id": template_data.program_id},
            {"$set": {"items": template_data.items}}
        )
        existing['items'] = template_data.items
        if isinstance(existing.get('created_at'), str):
            existing['created_at'] = datetime.fromisoformat(existing['created_at'])
        return ChecklistTemplate(**existing)
    
    template_obj = ChecklistTemplate(**template_data.model_dump())
    doc = template_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.checklist_templates.insert_one(doc)
    return template_obj

@api_router.get("/checklist-templates", response_model=List[ChecklistTemplate])
async def get_all_checklist_templates(current_user: User = Depends(get_current_user)):
    """Get all checklist templates"""
    templates = await db.checklist_templates.find({}, {"_id": 0}).to_list(length=None)
    result = []
    for template in templates:
        if isinstance(template.get('created_at'), str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
        result.append(ChecklistTemplate(**template))
    return result

@api_router.get("/checklist-templates/program/{program_id}", response_model=ChecklistTemplate)
async def get_checklist_template(program_id: str, current_user: User = Depends(get_current_user)):
    template = await db.checklist_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        return ChecklistTemplate(program_id=program_id, items=[])
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    return ChecklistTemplate(**template)

@api_router.get("/checklists/templates/program/{program_id}", response_model=ChecklistTemplate)
async def get_checklist_template_alias(program_id: str, current_user: User = Depends(get_current_user)):
    """Alias endpoint for backward compatibility - trainers use this"""
    template = await db.checklist_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        return ChecklistTemplate(program_id=program_id, items=[])
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    return ChecklistTemplate(**template)

@api_router.get("/checklists/templates", response_model=List[ChecklistTemplate])
async def get_all_checklist_templates_alias(current_user: User = Depends(get_current_user)):
    """Alias endpoint for /checklist-templates - used by AdminDashboard"""
    templates = await db.checklist_templates.find({}, {"_id": 0}).to_list(100)
    result = []
    for t in templates:
        if isinstance(t.get('created_at'), str):
            t['created_at'] = datetime.fromisoformat(t['created_at'])
        result.append(ChecklistTemplate(**t))
    return result

@api_router.put("/checklist-templates/{template_id}", response_model=ChecklistTemplate)
async def update_checklist_template(template_id: str, template_data: ChecklistTemplateCreate, current_user: User = Depends(get_current_user)):
    """Update a checklist template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can update checklist templates")
    
    existing = await db.checklist_templates.find_one({"id": template_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await db.checklist_templates.update_one(
        {"id": template_id},
        {"$set": {"items": template_data.items, "program_id": template_data.program_id}}
    )
    
    existing['items'] = template_data.items
    existing['program_id'] = template_data.program_id
    if isinstance(existing.get('created_at'), str):
        existing['created_at'] = datetime.fromisoformat(existing['created_at'])
    
    return ChecklistTemplate(**existing)

@api_router.delete("/checklist-templates/{template_id}/items/{item_index}")
async def delete_checklist_item(template_id: str, item_index: int, current_user: User = Depends(get_current_user)):
    """Delete a specific item from a checklist template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete checklist items")
    
    # Get the template
    template = await db.checklist_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if the item index is valid
    if item_index < 0 or item_index >= len(template.get("items", [])):
        raise HTTPException(status_code=400, detail="Invalid item index")
    
    # Remove the item at the specified index
    items = template.get("items", [])
    items.pop(item_index)
    
    # Update the template with the modified items list
    await db.checklist_templates.update_one(
        {"id": template_id},
        {"$set": {"items": items}}
    )
    
    return {"message": "Checklist item deleted successfully"}

@api_router.delete("/checklist-templates/{template_id}")
async def delete_checklist_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Delete a checklist template"""
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete checklist templates")
    
    result = await db.checklist_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}

# Vehicle Details Routes
@api_router.post("/vehicle-details/submit", response_model=VehicleDetails)
async def submit_vehicle_details(vehicle_data: VehicleDetailsSubmit, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can submit vehicle details")
    
    # Check if already exists
    existing = await db.vehicle_details.find_one({
        "participant_id": current_user.id,
        "session_id": vehicle_data.session_id
    }, {"_id": 0})
    
    if existing:
        # Update existing
        await db.vehicle_details.update_one(
            {"participant_id": current_user.id, "session_id": vehicle_data.session_id},
            {"$set": {
                "vehicle_model": vehicle_data.vehicle_model,
                "registration_number": vehicle_data.registration_number,
                "roadtax_expiry": vehicle_data.roadtax_expiry
            }}
        )
        existing.update(vehicle_data.model_dump())
        if isinstance(existing.get('created_at'), str):
            existing['created_at'] = datetime.fromisoformat(existing['created_at'])
        return VehicleDetails(**existing)
    
    vehicle_obj = VehicleDetails(
        participant_id=current_user.id,
        session_id=vehicle_data.session_id,
        vehicle_model=vehicle_data.vehicle_model,
        registration_number=vehicle_data.registration_number,
        roadtax_expiry=vehicle_data.roadtax_expiry
    )
    
    doc = vehicle_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.vehicle_details.insert_one(doc)
    return vehicle_obj

@api_router.get("/vehicle-details/{session_id}/{participant_id}")
async def get_vehicle_details(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    vehicle = await db.vehicle_details.find_one({
        "participant_id": participant_id,
        "session_id": session_id
    }, {"_id": 0})
    
    if not vehicle:
        return None
    
    if isinstance(vehicle.get('created_at'), str):
        vehicle['created_at'] = datetime.fromisoformat(vehicle['created_at'])
    return vehicle

# Attendance Routes
@api_router.post("/attendance/clock-in")
async def clock_in(attendance_data: AttendanceClockIn, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can clock in")
    
    # Use Malaysian time
    today = get_malaysia_date().isoformat()
    now = get_malaysia_time_str()
    
    # First check if ANY attendance record exists for this participant/session (regardless of date)
    # This prevents double check-in when super admin has already set attendance
    existing_any = await db.attendance.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id
    }, {"_id": 0})
    
    if existing_any and existing_any.get('clock_in'):
        raise HTTPException(status_code=400, detail="Already clocked in for this session")
    
    # Check if there's a record for today specifically
    existing_today = await db.attendance.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id,
        "date": today
    }, {"_id": 0})
    
    if existing_today:
        # Update existing today's record
        await db.attendance.update_one(
            {"id": existing_today['id']},
            {"$set": {"clock_in": now}}
        )
        return {"message": "Clocked in successfully", "time": now}
    
    if existing_any:
        # Update the existing record (from a different date) with today's clock in
        await db.attendance.update_one(
            {"id": existing_any['id']},
            {"$set": {"clock_in": now, "date": today}}
        )
        return {"message": "Clocked in successfully", "time": now}
    
    # Create new record
    attendance_obj = Attendance(
        participant_id=current_user.id,
        session_id=attendance_data.session_id,
        date=today,
        clock_in=now
    )
    
    doc = attendance_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.attendance.insert_one(doc)
    
    return {"message": "Clocked in successfully", "time": now}

@api_router.post("/attendance/clock-out")
async def clock_out(attendance_data: AttendanceClockOut, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can clock out")
    
    # Check if clock out has been released by coordinator
    access = await db.participant_access.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id
    }, {"_id": 0})
    
    if not access or not access.get("can_clock_out"):
        raise HTTPException(status_code=403, detail="Clock out not yet released by coordinator")
    
    # Use Malaysian time
    now = get_malaysia_time_str()
    
    # First check for ANY existing attendance record (regardless of date)
    # This handles cases where super admin set attendance on a different date
    existing = await db.attendance.find_one({
        "participant_id": current_user.id,
        "session_id": attendance_data.session_id
    }, {"_id": 0})
    
    if not existing or not existing.get('clock_in'):
        raise HTTPException(status_code=400, detail="Please clock in first")
    
    if existing.get('clock_out'):
        raise HTTPException(status_code=400, detail="Already clocked out for this session")
    
    await db.attendance.update_one(
        {"id": existing['id']},
        {"$set": {"clock_out": now}}
    )
    
    return {"message": "Clocked out successfully", "time": now}

@api_router.get("/attendance/session/{session_id}")
async def get_session_attendance(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all attendance records for a session (for supervisors/coordinators/trainers)"""
    if current_user.role not in ["pic_supervisor", "coordinator", "admin", "trainer"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get session to verify access
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all attendance records for the session
    print(f"Querying attendance for session_id: {session_id}")
    logging.info(f"Querying attendance for session_id: {session_id}")
    attendance_records = await db.attendance.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    print(f"Found {len(attendance_records)} attendance records")
    logging.info(f"Found {len(attendance_records)} attendance records")
    
    # Get participant details only if we have attendance records
    participant_map = {}
    if attendance_records:
        participant_ids = list(set([r['participant_id'] for r in attendance_records]))
        logging.info(f"Looking up {len(participant_ids)} unique participants")
        
        if participant_ids:  # Only query if we have IDs to look up
            participants = await db.users.find({"id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
            participant_map = {p['id']: p for p in participants}
            logging.info(f"Found {len(participants)} participant records")
    
    # Enrich attendance records with participant info
    for record in attendance_records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        participant = participant_map.get(record['participant_id'])
        if participant:
            record['participant_name'] = participant.get('full_name', 'Unknown')
            record['participant_email'] = participant.get('email', '')
        else:
            # Still include record even if participant not found
            record['participant_name'] = f"Participant {record['participant_id']}"
            record['participant_email'] = ''
            logging.warning(f"Could not find participant info for ID: {record['participant_id']}")
    
    return attendance_records

@api_router.get("/attendance/{session_id}/{participant_id}")
async def get_attendance(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    attendance_records = await db.attendance.find({
        "participant_id": participant_id,
        "session_id": session_id
    }, {"_id": 0}).to_list(100)
    
    for record in attendance_records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
    
    return attendance_records
    
    print(f"=== ATTENDANCE ENDPOINT CALLED FOR SESSION: {session_id} ===")
    logging.info(f"=== ATTENDANCE ENDPOINT CALLED FOR SESSION: {session_id} ===")
    
    if current_user.role not in ["pic_supervisor", "coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get session to verify access
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all attendance records for the session
    print(f"Querying attendance for session_id: {session_id}")
    logging.info(f"Querying attendance for session_id: {session_id}")
    attendance_records = await db.attendance.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    print(f"Found {len(attendance_records)} attendance records")
    logging.info(f"Found {len(attendance_records)} attendance records")
    
    # Get participant details only if we have attendance records
    participant_map = {}
    if attendance_records:
        participant_ids = list(set([r['participant_id'] for r in attendance_records]))
        logging.info(f"Looking up {len(participant_ids)} unique participants")
        
        if participant_ids:  # Only query if we have IDs to look up
            participants = await db.users.find({"id": {"$in": participant_ids}}, {"_id": 0}).to_list(1000)
            participant_map = {p['id']: p for p in participants}
            logging.info(f"Found {len(participants)} participant records")
    
    # Enrich attendance records with participant info
    for record in attendance_records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        participant = participant_map.get(record['participant_id'])
        if participant:
            record['participant_name'] = participant.get('full_name', 'Unknown')
            record['participant_email'] = participant.get('email', '')
        else:
            # Still include record even if participant not found
            record['participant_name'] = f"Participant {record['participant_id']}"
            record['participant_email'] = ''
            logging.warning(f"Could not find participant info for ID: {record['participant_id']}")
    
    return attendance_records

# Training Report Routes
@api_router.post("/training-reports", response_model=TrainingReport)
async def create_training_report(report_data: TrainingReportCreate, current_user: User = Depends(get_current_user)):
    """Create or update training completion report (coordinator only)"""
    if current_user.role != "coordinator":
        raise HTTPException(status_code=403, detail="Only coordinators can create training reports")
    
    # Check if report already exists for this session
    existing = await db.training_reports.find_one({"session_id": report_data.session_id}, {"_id": 0})
    
    if existing:
        # Update existing report
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
    
    # Create new report
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

@api_router.get("/training-reports/{session_id}")
async def get_training_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Get training report for a session"""
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    if not report:
        # Return 404 instead of empty structure
        raise HTTPException(status_code=404, detail="Training report not found")
    
    if isinstance(report.get('created_at'), str):
        report['created_at'] = datetime.fromisoformat(report['created_at'])
    if isinstance(report.get('submitted_at'), str) and report.get('submitted_at'):
        report['submitted_at'] = datetime.fromisoformat(report['submitted_at'])
    
    return report

@api_router.get("/training-reports/coordinator/{coordinator_id}")
async def get_coordinator_reports(coordinator_id: str, current_user: User = Depends(get_current_user)):
    """Get all training reports for a coordinator"""
    if current_user.role != "coordinator" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    reports = await db.training_reports.find({"coordinator_id": coordinator_id}, {"_id": 0}).to_list(100)
    
    for report in reports:
        if isinstance(report.get('created_at'), str):
            report['created_at'] = datetime.fromisoformat(report['created_at'])
        if isinstance(report.get('submitted_at'), str) and report.get('submitted_at'):
            report['submitted_at'] = datetime.fromisoformat(report['submitted_at'])
    
    return reports


@api_router.get("/training-reports/admin/all")
async def get_all_training_reports(
    search: Optional[str] = None,
    company_id: Optional[str] = None,
    program_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all training reports with search and filter - Admin only"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    # Build query
    query = {"status": "submitted"}  # Only show submitted reports
    
    if status:
        query["status"] = status
    
    # Get all submitted reports
    reports = await db.training_reports.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich each report with session, coordinator, company, program details
    enriched_reports = []
    
    for report in reports:
        session = await db.sessions.find_one({"id": report['session_id']}, {"_id": 0})
        if not session:
            continue
        
        # Get coordinator details
        coordinator = await db.users.find_one({"id": report.get('coordinator_id')}, {"_id": 0})
        
        # Get company and program details
        company = await db.companies.find_one({"id": session.get('company_id')}, {"_id": 0})
        program = await db.programs.find_one({"id": session.get('program_id')}, {"_id": 0})
        
        # Get participant count
        participant_count = len(session.get('participant_ids', []))
        
        # Apply filters
        if company_id and session.get('company_id') != company_id:
            continue
        
        if program_id and session.get('program_id') != program_id:
            continue
        
        # Apply date filter
        if start_date:
            session_date = session.get('start_date')
            if session_date and session_date < start_date:
                continue
        
        if end_date:
            session_date = session.get('end_date')
            if session_date and session_date > end_date:
                continue
        
        # Build enriched report
        enriched = {
            **report,
            "session_name": session.get('name', 'Unknown'),
            "session_start_date": session.get('start_date'),
            "session_end_date": session.get('end_date'),
            "session_location": session.get('location'),
            "coordinator_name": coordinator.get('full_name') if coordinator else 'Unknown',
            "company_name": company.get('name') if company else 'Unknown',
            "company_id": session.get('company_id'),
            "program_name": program.get('name') if program else 'Unknown',
            "program_id": session.get('program_id'),
            "participant_count": participant_count
        }
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            searchable_text = f"{enriched['session_name']} {enriched['coordinator_name']} {enriched['company_name']} {enriched['program_name']} {enriched['session_location']}".lower()
            
            if search_lower not in searchable_text:
                continue
        
        enriched_reports.append(enriched)
    
    # Sort by submitted date (most recent first)
    enriched_reports.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)
    
    return {
        "total": len(enriched_reports),
        "reports": enriched_reports
    }


@api_router.post("/training-reports/{session_id}/generate-ai-report")
async def generate_ai_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Generate AI training report using ChatGPT"""
    if current_user.role != "coordinator" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only coordinators can generate reports")
    
    from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get session details
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get program details
    program = await db.programs.find_one({"id": session['program_id']}, {"_id": 0})
    
    # Get company details
    company = await db.companies.find_one({"id": session['company_id']}, {"_id": 0})
    
    # Get participants count
    participant_count = len(session.get('participant_ids', []))
    
    # Get attendance records
    attendance_records = await db.attendance.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    total_attendance = len(set([r['participant_id'] for r in attendance_records]))
    
    # Get test results
    test_results = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(1000)
    passed_tests = len([r for r in test_results if r.get('passed', False)])
    
    # Get training report with photos
    training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    # Build context for AI
    context = f"""
Generate a professional defensive driving training completion report in a structured format similar to official training documentation.

**SESSION INFORMATION:**
Program Name: {program.get('name', 'N/A') if program else 'N/A'}
Company: {company.get('name', 'N/A') if company else 'N/A'}
Training Location: {session.get('location', 'N/A')}
Training Period: {session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')}
Total Participants: {participant_count}
Attendance: {total_attendance} out of {participant_count} participants
Assessment Pass Rate: {passed_tests} out of {len(test_results)} passed

**DOCUMENTATION:**
- Group Photo: {'Attached' if training_report and training_report.get('group_photo') else 'Not provided'}
- Theory Session Photos: {2 if training_report and training_report.get('theory_photo_1') and training_report.get('theory_photo_2') else 0} photos attached
- Practical Session Photos: {3 if training_report and training_report.get('practical_photo_1') and training_report.get('practical_photo_2') and training_report.get('practical_photo_3') else 0} photos attached

**REQUIRED REPORT STRUCTURE:**

# TRAINING COMPLETION REPORT

## 1. EXECUTIVE SUMMARY
[Provide a 2-3 sentence overview of the training session]

## 2. TRAINING PROGRAM DETAILS
- Program Name: [name]
- Training Duration: [dates]
- Location: [location]
- Target Audience: [company employees]

## 3. TRAINING OBJECTIVES
[List 3-4 key objectives of the defensive driving program]

## 4. TRAINING DELIVERY
**Theory Sessions:**
[Describe theory topics covered - 2-3 sentences]

**Practical Sessions:**
[Describe hands-on activities and exercises - 2-3 sentences]

## 5. PARTICIPANT PERFORMANCE
- Total Enrolled: {participant_count}
- Attendance Rate: {round((total_attendance/participant_count)*100) if participant_count > 0 else 0}%
- Assessment Pass Rate: {round((passed_tests/len(test_results))*100) if len(test_results) > 0 else 0}%

## 6. KEY LEARNING OUTCOMES
[List 4-5 key skills/knowledge participants gained]
- 
- 
- 

## 7. TRAINING EFFECTIVENESS
[Evaluate based on attendance and pass rates - 2-3 sentences]

## 8. OBSERVATIONS & FEEDBACK
[Note any significant observations about participant engagement, questions asked, areas of difficulty]

## 9. RECOMMENDATIONS
[Provide 2-3 recommendations for future training sessions]

## 10. CONCLUSION
[Summarize the overall success of the training]

---
Report Prepared By: Training Coordinator
Date: {get_malaysia_time().strftime('%Y-%m-%d')}

Please generate this report professionally with proper formatting, specific details based on the data provided, and maintain a formal tone suitable for official documentation.
"""
    
    try:
        # Initialize LLM Chat
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"report_{session_id}",
            system_message="You are a professional training report writer specializing in defensive driving and road safety training programs."
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=context)
        
        # Generate report
        ai_response = await chat.send_message(user_message)
        
        return {
            "session_id": session_id,
            "generated_report": ai_response,
            "metadata": {
                "participant_count": participant_count,
                "attendance_rate": f"{total_attendance}/{participant_count}",
                "test_pass_rate": f"{passed_tests}/{len(test_results)}",
                "photos_included": bool(training_report)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI report: {str(e)}")


# Professional DOCX Report Generation
@api_router.post("/training-reports/{session_id}/generate-docx")
async def generate_docx_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Generate a professional DOCX training report with all data populated"""
    
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can generate reports")
    
    try:
        # Gather all session data
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        program = await db.programs.find_one({"id": session.get('program_id')}, {"_id": 0}) if session.get('program_id') else None
        company = await db.companies.find_one({"id": session.get('company_id')}, {"_id": 0}) if session.get('company_id') else None
        
        # Validate required data
        if not program:
            raise HTTPException(status_code=400, detail="Program not found for this session. Please ensure the session has a valid program assigned.")
        if not company:
            raise HTTPException(status_code=400, detail="Company not found for this session. Please ensure the session has a valid company assigned.")
        
        # Get participants with full details
        participant_ids = session.get('participant_ids', [])
        participants = []
        for pid in participant_ids:
            user = await db.users.find_one({"id": pid}, {"_id": 0})
            if user:
                # Get pre and post test results
                pre_test = await db.test_results.find_one({
                    "participant_id": pid,
                    "session_id": session_id,
                    "test_type": "pre"
                }, {"_id": 0})
                
                post_test = await db.test_results.find_one({
                    "participant_id": pid,
                    "session_id": session_id,
                    "test_type": "post"
                }, {"_id": 0})
                
                participants.append({
                    "name": user.get('full_name'),
                    "id_number": user.get('id_number', 'N/A'),
                    "pre_test_score": pre_test.get('score', 0) if pre_test else 0,
                    "pre_test_passed": pre_test.get('passed', False) if pre_test else False,
                    "post_test_score": post_test.get('score', 0) if post_test else 0,
                    "post_test_passed": post_test.get('passed', False) if post_test else False,
                    "improvement": (post_test.get('score', 0) if post_test else 0) - (pre_test.get('score', 0) if pre_test else 0)
                })
        
        # Get vehicle checklists with issues
        checklists = await db.vehicle_checklists.find({"session_id": session_id}, {"_id": 0}).to_list(100)
        vehicle_issues = []
        for checklist in checklists:
            participant = await db.users.find_one({"id": checklist['participant_id']}, {"_id": 0})
            issues_list = []
            for item in checklist.get('checklist_items', []):
                if item.get('status') == 'needs_repair':
                    issues_list.append({
                        "item": item.get('item', 'Unknown'),
                        "comment": item.get('comments', 'No comment'),
                        "photo_url": item.get('photo_url', '')
                    })
            
            if issues_list:
                vehicle_issues.append({
                    "participant_name": participant.get('full_name') if participant else 'Unknown',
                    "issues": issues_list
                })
        
        # Get training photos from training report
        training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
        training_photos = {
            "group_photo": training_report.get('group_photo') if training_report else None,
            "theory_photo_1": training_report.get('theory_photo_1') if training_report else None,
            "theory_photo_2": training_report.get('theory_photo_2') if training_report else None,
            "practical_photo_1": training_report.get('practical_photo_1') if training_report else None,
            "practical_photo_2": training_report.get('practical_photo_2') if training_report else None,
            "practical_photo_3": training_report.get('practical_photo_3') if training_report else None
        }
        
        # Get participant feedback
        all_feedback = await db.course_feedback.find({"session_id": session_id}, {"_id": 0}).to_list(100)
        feedback_data = []
        for feedback in all_feedback:
            participant = await db.users.find_one({"id": feedback['participant_id']}, {"_id": 0})
            feedback_data.append({
                "participant_name": participant.get('full_name') if participant else 'Unknown',
                "responses": feedback.get('responses', [])
            })
        
        # Determine vehicle type from program name for objectives
        program_name_lower = program.get('name', '').lower()
        is_motorcycle = 'motor' in program_name_lower or 'bike' in program_name_lower or 'rider' in program_name_lower
        is_truck = 'truck' in program_name_lower or 'lorry' in program_name_lower or 'heavy' in program_name_lower
        
        # Create DOCX document with enhanced formatting
        doc = Document()
        
        # COVER PAGE
        title = doc.add_heading('DEFENSIVE DRIVING/RIDING TRAINING', 0)
        title.alignment = 1  # Center alignment
        subtitle = doc.add_heading('COMPREHENSIVE COMPLETION REPORT', 0)
        subtitle.alignment = 1
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Cover details in a cleaner format
        cover_table = doc.add_table(rows=7, cols=2)
        cover_table.style = 'Light List Accent 1'
        cover_details = [
            ('Program:', program.get('name', 'N/A')),
            ('Company:', company.get('name', 'N/A')),
            ('Location:', session.get('location', 'N/A')),
            ('Training Period:', f"{session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')}"),
            ('Participants:', str(len(participants))),
            ('Submitted by:', current_user.full_name),
            ('Date:', get_malaysia_time().strftime('%Y-%m-%d'))
        ]
        for idx, (label, value) in enumerate(cover_details):
            cover_table.rows[idx].cells[0].text = label
            cover_table.rows[idx].cells[1].text = value
        
        doc.add_paragraph()
        doc.add_paragraph()
        footer_text = doc.add_paragraph('Prepared by: MDDRC (Malaysian Defensive Driving & Riding Centre)')
        footer_text.alignment = 1
        doc.add_page_break()
        
        # EXECUTIVE SUMMARY - COMPREHENSIVE
        doc.add_heading('1. EXECUTIVE SUMMARY', 1)
        pre_avg = sum([p['pre_test_score'] for p in participants]) / len(participants) if participants else 0
        post_avg = sum([p['post_test_score'] for p in participants]) / len(participants) if participants else 0
        improvement = post_avg - pre_avg
        
        # Count pass/fail statistics
        pre_pass_count = sum([1 for p in participants if p['pre_test_passed']])
        post_pass_count = sum([1 for p in participants if p['post_test_passed']])
        improved_count = sum([1 for p in participants if p['improvement'] > 0])
        
        doc.add_paragraph(
            f"This comprehensive report documents the Defensive {'Riding' if is_motorcycle else 'Driving'} Training "
            f"conducted for {company.get('name', 'N/A')} at {session.get('location', 'N/A')} from "
            f"{session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')}. The program was designed to "
            f"enhance safety awareness, reinforce defensive {'riding' if is_motorcycle else 'driving'} techniques, "
            f"and reduce commuting-related accidents, aligning with the company's commitment to employee safety."
        )
        doc.add_paragraph()
        
        doc.add_paragraph(
            f"The training program successfully engaged {len(participants)} participants through a structured "
            f"curriculum combining theoretical instruction and practical hands-on sessions. Participants demonstrated "
            f"high engagement levels and openness to feedback, contributing to a positive learning environment."
        )
        doc.add_paragraph()
        
        # KEY OUTCOMES heading
        doc.add_paragraph("KEY OUTCOMES:", style='Heading 3')
        outcomes = [
            f"• Total Participants: {len(participants)}",
            f"• Pre-Training Assessment Average: {pre_avg:.1f}%",
            f"• Post-Training Assessment Average: {post_avg:.1f}%",
            f"• Overall Improvement: {improvement:+.1f}%",
            f"• Pre-Test Pass Rate: {pre_pass_count}/{len(participants)} ({(pre_pass_count/len(participants)*100):.0f}% if len(participants) > 0 else 0)",
            f"• Post-Test Pass Rate: {post_pass_count}/{len(participants)} ({(post_pass_count/len(participants)*100):.0f}% if len(participants) > 0 else 0)",
            f"• Participants Showing Improvement: {improved_count}/{len(participants)} ({(improved_count/len(participants)*100):.0f}% if len(participants) > 0 else 0)"
        ]
        for outcome in outcomes:
            doc.add_paragraph(outcome)
        doc.add_paragraph()
        
        # TRAINING IMPACT
        doc.add_paragraph("TRAINING IMPACT:", style='Heading 3')
        doc.add_paragraph(
            f"The training successfully enhanced participants' understanding of hazard awareness, proper braking control, "
            f"and {'balance techniques' if is_motorcycle else 'vehicle control'}. Participants demonstrated improved ability "
            f"to identify potential road hazards and apply defensive {'riding' if is_motorcycle else 'driving'} principles. "
            f"The program fostered a culture of safety discipline and mutual learning among participants."
        )
        doc.add_paragraph()
        
        # SAFETY OBSERVATIONS (if vehicle issues found)
        if vehicle_issues:
            doc.add_paragraph("SAFETY OBSERVATIONS:", style='Heading 3')
            doc.add_paragraph(
                f"Vehicle inspections revealed {len(vehicle_issues)} {'motorcycles' if is_motorcycle else 'vehicles'} "
                f"with safety concerns requiring immediate attention. Detailed recommendations for addressing these issues "
                f"are provided in Section 9 of this report."
            )
        
        doc.add_page_break()
        
        # TRAINING OBJECTIVES
        doc.add_heading('2. TRAINING OBJECTIVES', 1)
        doc.add_paragraph(
            "This training program was designed with the following core objectives to enhance workplace safety and reduce accident risks:"
        )
        doc.add_paragraph()
        
        if is_motorcycle:
            objectives = [
                "• Improve rider safety awareness and hazard recognition on Malaysian roads",
                "• Reinforce defensive riding techniques for daily commuting",
                "• Reduce motorcycle-related accidents and injuries among employees",
                "• Promote proper Personal Protective Equipment (PPE) usage and motorcycle maintenance",
                "• Align riding behavior with company safety values and policies",
                "• Develop emergency response skills for critical road situations"
            ]
        elif is_truck:
            objectives = [
                "• Enhance heavy vehicle safety awareness and load management",
                "• Reinforce defensive driving techniques for commercial vehicles",
                "• Reduce delivery delays caused by accidents and vehicle breakdowns",
                "• Improve vehicle pre-trip inspection and maintenance practices",
                "• Minimize company liability and insurance costs through safer driving",
                "• Align driving behavior with company safety standards and regulations"
            ]
        else:  # Car/general driving
            objectives = [
                "• Improve driver safety awareness and hazard perception",
                "• Reinforce defensive driving techniques for daily operations",
                "• Reduce vehicle-related accidents and associated costs",
                "• Promote proper vehicle maintenance and pre-drive safety checks",
                "• Align driving behavior with company safety policies",
                "• Develop emergency response and accident avoidance skills"
            ]
        
        for objective in objectives:
            doc.add_paragraph(objective)
        doc.add_paragraph()
        doc.add_paragraph(
            "These objectives support the organization's commitment to employee welfare and operational excellence "
            "through enhanced road safety practices."
        )
        doc.add_page_break()
        
        # TRAINING AGENDA
        doc.add_heading('3. TRAINING AGENDA', 1)
        doc.add_paragraph(
            f"The training was conducted over a {2 if is_motorcycle else 2}-day period, combining theoretical instruction "
            f"with practical hands-on sessions:"
        )
        doc.add_paragraph()
        
        # DAY 1
        doc.add_heading('DAY 1 - Theory & Foundation', 2)
        if is_motorcycle:
            day1_items = [
                ('08:00 - 08:30', 'Registration & Welcome Briefing'),
                ('08:30 - 10:00', 'Hazard Recognition & Road Awareness'),
                ('10:00 - 10:15', 'Break'),
                ('10:15 - 12:00', 'Safe Distance Management & Speed Control'),
                ('12:00 - 13:00', 'Lunch'),
                ('13:00 - 14:30', 'Traffic Law & Regulations Review'),
                ('14:30 - 14:45', 'Break'),
                ('14:45 - 16:30', 'Fatigue Management & Weather Conditions'),
                ('16:30 - 17:00', 'Pre-Test Assessment & Day 1 Review')
            ]
        else:
            day1_items = [
                ('08:00 - 08:30', 'Registration & Welcome Briefing'),
                ('08:30 - 10:00', 'Defensive Driving Principles & Hazard Recognition'),
                ('10:00 - 10:15', 'Break'),
                ('10:15 - 12:00', 'Safe Following Distance & Speed Management'),
                ('12:00 - 13:00', 'Lunch'),
                ('13:00 - 14:30', 'Traffic Law & Road Safety Regulations'),
                ('14:30 - 14:45', 'Break'),
                ('14:45 - 16:30', 'Driver Fatigue & Weather Driving Conditions'),
                ('16:30 - 17:00', 'Pre-Test Assessment & Day 1 Summary')
            ]
        
        agenda_table_day1 = doc.add_table(rows=len(day1_items)+1, cols=2)
        agenda_table_day1.style = 'Light Grid Accent 1'
        agenda_table_day1.rows[0].cells[0].text = 'Time'
        agenda_table_day1.rows[0].cells[1].text = 'Activity'
        for idx, (time, activity) in enumerate(day1_items, 1):
            agenda_table_day1.rows[idx].cells[0].text = time
            agenda_table_day1.rows[idx].cells[1].text = activity
        
        doc.add_paragraph()
        
        # DAY 2
        doc.add_heading('DAY 2 - Practical Skills & Assessment', 2)
        if is_motorcycle:
            day2_items = [
                ('08:00 - 08:30', 'Day 2 Safety Briefing & PPE Check'),
                ('08:30 - 10:00', 'Emergency Braking Techniques (Practical)'),
                ('10:00 - 10:15', 'Break'),
                ('10:15 - 12:00', 'Obstacle Avoidance & Swerving Maneuvers'),
                ('12:00 - 13:00', 'Lunch'),
                ('13:00 - 14:30', 'Cornering Techniques & Body Positioning'),
                ('14:30 - 14:45', 'Break'),
                ('14:45 - 16:00', 'Left Lane Riding & Traffic Integration'),
                ('16:00 - 16:45', 'Post-Test Assessment'),
                ('16:45 - 17:00', 'Certificate Presentation & Closing')
            ]
        else:
            day2_items = [
                ('08:00 - 08:30', 'Day 2 Safety Briefing & Vehicle Check'),
                ('08:30 - 10:00', 'Emergency Braking & Stopping Techniques'),
                ('10:00 - 10:15', 'Break'),
                ('10:15 - 12:00', 'Obstacle Avoidance & Lane Change Maneuvers'),
                ('12:00 - 13:00', 'Lunch'),
                ('13:00 - 14:30', 'Cornering & Vehicle Control Exercises'),
                ('14:30 - 14:45', 'Break'),
                ('14:45 - 16:00', 'Traffic Integration & Road Scenarios'),
                ('16:00 - 16:45', 'Post-Test Assessment & Performance Review'),
                ('16:45 - 17:00', 'Certificate Presentation & Program Closure')
            ]
        
        agenda_table_day2 = doc.add_table(rows=len(day2_items)+1, cols=2)
        agenda_table_day2.style = 'Light Grid Accent 1'
        agenda_table_day2.rows[0].cells[0].text = 'Time'
        agenda_table_day2.rows[0].cells[1].text = 'Activity'
        for idx, (time, activity) in enumerate(day2_items, 1):
            agenda_table_day2.rows[idx].cells[0].text = time
            agenda_table_day2.rows[idx].cells[1].text = activity
        
        doc.add_page_break()
        
        # TRAINING DETAILS
        doc.add_heading('4. TRAINING DETAILS', 1)
        doc.add_paragraph(f"Program: {program.get('name', 'N/A')}")
        doc.add_paragraph(f"Location: {session.get('location', 'N/A')}")
        doc.add_paragraph(f"Dates: {session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')}")
        doc.add_paragraph(f"Total Participants: {len(participants)}")
        doc.add_paragraph()
        doc.add_paragraph("Participants List:")
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Light Grid Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Name'
        hdr_cells[1].text = 'ID Number'
        for p in participants:
            row_cells = table.add_row().cells
            row_cells[0].text = p['name']
            row_cells[1].text = str(p['id_number'])
        doc.add_page_break()
        
        # PRE-POST EVALUATION SUMMARY
        doc.add_heading('5. PRE-POST EVALUATION SUMMARY', 1)
        # Summary statistics
        doc.add_paragraph(f"Pre-Test Pass Rate: {pre_pass_count}/{len(participants)} participants ({(pre_pass_count/len(participants)*100):.0f}%)")
        doc.add_paragraph(f"Post-Test Pass Rate: {post_pass_count}/{len(participants)} participants ({(post_pass_count/len(participants)*100):.0f}%)")
        doc.add_paragraph(f"Participants Showing Improvement: {improved_count}/{len(participants)} ({(improved_count/len(participants)*100):.0f}%)")
        doc.add_paragraph(f"Average Score Change: {improvement:+.1f}%")
        doc.add_paragraph()
        
        # Performance Summary Table
        doc.add_paragraph("TABULATED RESULTS:", style='Heading 3')
        table = doc.add_table(rows=1, cols=6)
        table.style = 'Light Grid Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Participant'
        hdr_cells[1].text = 'ID Number'
        hdr_cells[2].text = 'Pre-Test'
        hdr_cells[3].text = 'Post-Test'
        hdr_cells[4].text = 'Improvement'
        hdr_cells[5].text = 'Status'
        
        for p in participants:
            row_cells = table.add_row().cells
            row_cells[0].text = p['name']
            row_cells[1].text = str(p['id_number'])
            row_cells[2].text = f"{p['pre_test_score']:.0f}%"
            row_cells[3].text = f"{p['post_test_score']:.0f}%"
            row_cells[4].text = f"{p['improvement']:+.0f}%"
            row_cells[5].text = 'PASS' if p['post_test_passed'] else 'FAIL'
        
        doc.add_page_break()
        
        # DETAILED PERFORMANCE ANALYSIS WITH INSIGHTS
        doc.add_heading('6. DETAILED PERFORMANCE ANALYSIS', 1)
        doc.add_paragraph("Individual participant performance with remarks and recommendations:")
        doc.add_paragraph()
        
        for idx, p in enumerate(participants, 1):
            doc.add_paragraph(f"{idx}. {p['name']} (ID: {p['id_number']})", style='Heading 3')
            perf_text = f"   Pre-Test: {p['pre_test_score']:.0f}% | Post-Test: {p['post_test_score']:.0f}% | Change: {p['improvement']:+.0f}%"
            doc.add_paragraph(perf_text)
            
            # Generate performance remarks based on improvement
            if p['improvement'] >= 20:
                remark = "EXCELLENT IMPROVEMENT - Participant demonstrated exceptional learning and engagement. Strong grasp of defensive techniques."
            elif p['improvement'] >= 10:
                remark = "GOOD IMPROVEMENT - Participant showed solid progress and understanding of safety principles."
            elif p['improvement'] >= 0:
                remark = "SATISFACTORY PROGRESS - Participant maintained or slightly improved performance. Continue practicing learned techniques."
            elif p['improvement'] >= -10:
                remark = "NEEDS ATTENTION - Minor score decrease observed. Recommend follow-up coaching and review of key concepts."
            else:
                remark = "REQUIRES IMMEDIATE SUPPORT - Significant score decrease. Recommend one-on-one coaching session and practical refresher."
            
            # Pass/Fail status remark
            if not p['pre_test_passed'] and p['post_test_passed']:
                remark += " Successfully progressed from FAIL to PASS status."
            elif not p['post_test_passed']:
                remark += " Did not achieve passing score - recommend additional training."
            
            doc.add_paragraph(f"   Remark: {remark}")
            doc.add_paragraph()
        
        # Overall Performance Insights
        doc.add_paragraph("OVERALL PERFORMANCE INSIGHTS:", style='Heading 3')
        high_performers = [p for p in participants if p['improvement'] >= 15]
        needs_support = [p for p in participants if p['improvement'] < 0]
        
        insights = []
        if high_performers:
            insights.append(f"• {len(high_performers)} participant(s) demonstrated excellent improvement (≥15% gain), indicating strong training absorption.")
        if needs_support:
            insights.append(f"• {len(needs_support)} participant(s) showed score decrease and require targeted follow-up support.")
        insights.append(f"• Average improvement of {improvement:+.1f}% indicates {'effective' if improvement > 5 else 'moderate'} training impact.")
        insights.append(f"• Post-test pass rate of {(post_pass_count/len(participants)*100):.0f}% {'meets' if post_pass_count/len(participants) >= 0.8 else 'is below'} target standards.")
        
        for insight in insights:
            doc.add_paragraph(insight)
        
        doc.add_page_break()
        
        # Get chief trainer feedback before displaying
        chief_trainer_feedback = await db.chief_trainer_feedback.find_one({"session_id": session_id}, {"_id": 0})
        
        # TRAINER FEEDBACK (Enhanced narrative)
        if chief_trainer_feedback:
            responses = chief_trainer_feedback.get('responses', {})
            template = await db.feedback_templates.find_one({"id": "chief_trainer_feedback_template"}, {"_id": 0})
            
            doc.add_paragraph(
                "The chief trainer provided comprehensive feedback on the training delivery, participant engagement, "
                "and safety observations throughout the program. Key observations and recommendations are detailed below:"
            )
            doc.add_paragraph()
            
            # Extract narrative responses from chief trainer
            for question_id, answer in responses.items():
                if template:
                    for q in template.get('questions', []):
                        if q.get('id') == question_id:
                            doc.add_paragraph(f"{q.get('question')}:", style='Heading 3')
                            if q.get('type') == 'rating':
                                stars = '⭐' * int(answer) if isinstance(answer, (int, float)) else answer
                                doc.add_paragraph(f"   Rating: {stars} ({answer}/{q.get('scale', 5)})")
                            else:
                                doc.add_paragraph(f"   {answer}")
                            doc.add_paragraph()
            
            # Add professional summary quote
            doc.add_paragraph()
            doc.add_paragraph(
                "The trainer observed that participants were highly engaged and receptive to feedback. "
                "Safety issues identified during vehicle inspections were communicated to participants and management. "
                "Overall, the training environment was conducive to learning with participants demonstrating strong "
                "commitment to improving their safety practices."
            )
        else:
            doc.add_paragraph("[Chief Trainer feedback pending submission]")
        
        doc.add_page_break()
        
        # TRAINING PHOTOS
        doc.add_heading('8. TRAINING PHOTOS', 1)
        if training_photos['group_photo']:
            doc.add_paragraph("Group Photo:", style='Heading 3')
            doc.add_paragraph(f"[Photo URL: {training_photos['group_photo']}]")
            doc.add_paragraph()
        
        if training_photos['theory_photo_1'] or training_photos['theory_photo_2']:
            doc.add_paragraph("Theory Session Photos:", style='Heading 3')
            if training_photos['theory_photo_1']:
                doc.add_paragraph(f"[Photo 1 URL: {training_photos['theory_photo_1']}]")
            if training_photos['theory_photo_2']:
                doc.add_paragraph(f"[Photo 2 URL: {training_photos['theory_photo_2']}]")
            doc.add_paragraph()
        
        if training_photos['practical_photo_1'] or training_photos['practical_photo_2'] or training_photos['practical_photo_3']:
            doc.add_paragraph("Practical Session Photos:", style='Heading 3')
            if training_photos['practical_photo_1']:
                doc.add_paragraph(f"[Photo 1 URL: {training_photos['practical_photo_1']}]")
            if training_photos['practical_photo_2']:
                doc.add_paragraph(f"[Photo 2 URL: {training_photos['practical_photo_2']}]")
            if training_photos['practical_photo_3']:
                doc.add_paragraph(f"[Photo 3 URL: {training_photos['practical_photo_3']}]")
        
        doc.add_page_break()
        
        # PARTICIPANT FEEDBACK SUMMARY (Enhanced)
        doc.add_heading('9. PARTICIPANT FEEDBACK SUMMARY', 1)
        if feedback_data:
            # Calculate average star ratings
            star_questions = []
            text_questions = []
            
            # Categorize questions
            if feedback_data:
                for response in feedback_data[0]['responses']:
                    if isinstance(response['answer'], int):
                        star_questions.append(response['question'])
                    else:
                        text_questions.append(response['question'])
            
            # PART 1: QUANTITATIVE FEEDBACK
            if star_questions:
                doc.add_paragraph("A. QUANTITATIVE FEEDBACK (Rating Scores):", style='Heading 3')
                doc.add_paragraph("Average ratings across all participants on a 5-point scale:")
                doc.add_paragraph()
                
                for question in star_questions:
                    ratings = [r['answer'] for fb in feedback_data for r in fb['responses'] if r['question'] == question and isinstance(r['answer'], int)]
                    if ratings:
                        avg_rating = sum(ratings) / len(ratings)
                        stars = '⭐' * int(round(avg_rating))
                        doc.add_paragraph(f"• {question}: {stars} ({avg_rating:.1f}/5.0)")
                
                # Overall satisfaction calculation
                all_ratings = [r['answer'] for fb in feedback_data for r in fb['responses'] if isinstance(r['answer'], int)]
                if all_ratings:
                    overall_avg = sum(all_ratings) / len(all_ratings)
                    doc.add_paragraph()
                    doc.add_paragraph(f"OVERALL SATISFACTION: {'⭐' * int(round(overall_avg))} ({overall_avg:.1f}/5.0)", style='Heading 3')
                doc.add_paragraph()
            
            # PART 2: QUALITATIVE FEEDBACK THEMES
            if text_questions:
                doc.add_paragraph("B. QUALITATIVE FEEDBACK (Key Themes):", style='Heading 3')
                
                # Collect all text responses
                all_text_responses = []
                for fb in feedback_data:
                    for response in fb['responses']:
                        if not isinstance(response['answer'], int):
                            all_text_responses.append(response['answer'])
                
                # Analyze common themes (simple keyword matching)
                positive_keywords = ['good', 'excellent', 'great', 'helpful', 'informative', 'clear', 'effective']
                improvement_keywords = ['more', 'extend', 'longer', 'additional', 'better', 'improve']
                
                positive_count = sum(1 for resp in all_text_responses if any(kw in str(resp).lower() for kw in positive_keywords))
                improvement_count = sum(1 for resp in all_text_responses if any(kw in str(resp).lower() for kw in improvement_keywords))
                
                doc.add_paragraph(f"• Positive Remarks: {positive_count} participants expressed satisfaction with training delivery and content")
                if improvement_count > 0:
                    doc.add_paragraph(f"• Improvement Suggestions: {improvement_count} participants suggested enhancements (e.g., extended duration, additional videos)")
                doc.add_paragraph()
                
                # PART 3: INDIVIDUAL RESPONSES (Detailed)
                doc.add_paragraph("C. DETAILED INDIVIDUAL RESPONSES:", style='Heading 3')
                for idx, fb in enumerate(feedback_data, 1):
                    doc.add_paragraph(f"{idx}. {fb['participant_name']}", style='Heading 4')
                    for response in fb['responses']:
                        if not isinstance(response['answer'], int):  # Text responses
                            doc.add_paragraph(f"   Q: {response['question']}")
                            doc.add_paragraph(f"   A: {response['answer']}")
                            doc.add_paragraph()
        else:
            doc.add_paragraph("No feedback submitted yet.")
        
        doc.add_page_break()
        
        # MOTORCYCLE/VEHICLE CONDITION & EMPLOYER RECOMMENDATIONS (Enhanced)
        doc.add_heading('10. VEHICLE CONDITION ASSESSMENT & EMPLOYER RECOMMENDATIONS', 1)
        
        if vehicle_issues:
            doc.add_paragraph(
                f"During the training program, pre-ride safety inspections were conducted on all participant "
                f"{'motorcycles' if is_motorcycle else 'vehicles'}. The inspections revealed {len(vehicle_issues)} "
                f"{'motorcycles' if is_motorcycle else 'vehicles'} with safety concerns that require immediate attention."
            )
            doc.add_paragraph()
            
            # PART A: SAFETY ISSUES IDENTIFIED
            doc.add_paragraph("A. SAFETY ISSUES IDENTIFIED:", style='Heading 3')
            for vehicle_issue in vehicle_issues:
                doc.add_paragraph(f"Participant: {vehicle_issue['participant_name']}", style='Heading 4')
                for issue in vehicle_issue['issues']:
                    doc.add_paragraph(f"   • {issue['item']}: {issue['comment']}")
                    if issue['photo_url']:
                        doc.add_paragraph(f"     [Photo Evidence: {issue['photo_url']}]")
                doc.add_paragraph()
            
            # PART B: SAFETY IMPLICATIONS
            doc.add_paragraph("B. SAFETY IMPLICATIONS:", style='Heading 3')
            common_issues = {}
            for vehicle_issue in vehicle_issues:
                for issue in vehicle_issue['issues']:
                    item_category = issue['item'].lower()
                    if 'tyre' in item_category or 'tire' in item_category:
                        common_issues['worn_tyres'] = common_issues.get('worn_tyres', 0) + 1
                    elif 'lamp' in item_category or 'light' in item_category:
                        common_issues['faulty_lamps'] = common_issues.get('faulty_lamps', 0) + 1
                    elif 'chain' in item_category:
                        common_issues['loose_chains'] = common_issues.get('loose_chains', 0) + 1
                    elif 'mirror' in item_category:
                        common_issues['missing_mirrors'] = common_issues.get('missing_mirrors', 0) + 1
                    elif 'ppe' in item_category or 'helmet' in item_category or 'jacket' in item_category:
                        common_issues['ppe_issues'] = common_issues.get('ppe_issues', 0) + 1
            
            if common_issues:
                for issue_type, count in common_issues.items():
                    if issue_type == 'worn_tyres':
                        doc.add_paragraph(f"• Worn Tyres ({count} cases): Increased risk of skidding and loss of control, especially in wet conditions")
                    elif issue_type == 'faulty_lamps':
                        doc.add_paragraph(f"• Faulty Lamps/Lights ({count} cases): Reduced visibility at night, increased accident risk")
                    elif issue_type == 'loose_chains':
                        doc.add_paragraph(f"• Loose Chains ({count} cases): Risk of chain breakage leading to loss of control")
                    elif issue_type == 'missing_mirrors':
                        doc.add_paragraph(f"• Missing/Damaged Mirrors ({count} cases): Impaired situational awareness and blind spot monitoring")
                    elif issue_type == 'ppe_issues':
                        doc.add_paragraph(f"• PPE Non-Compliance ({count} cases): Increased severity of injuries in case of accidents")
            doc.add_paragraph()
            
            # PART C: RECOMMENDATIONS FOR EMPLOYER
            doc.add_paragraph("C. RECOMMENDATIONS FOR EMPLOYER:", style='Heading 3')
            recommendations = [
                "1. IMMEDIATE ACTION REQUIRED:",
                f"   • Conduct immediate safety inspections on all {len(vehicle_issues)} flagged {'motorcycles' if is_motorcycle else 'vehicles'}",
                "   • Ground vehicles until critical safety issues are resolved",
                "   • Provide temporary alternative transportation if needed",
                "",
                "2. ESTABLISH REGULAR MAINTENANCE PROTOCOL:",
                f"   • Implement monthly pre-ride safety inspection checklist for all {'motorcycles' if is_motorcycle else 'vehicles'}",
                "   • Assign designated personnel for routine maintenance verification",
                "   • Maintain detailed maintenance logs for each vehicle",
                "",
                "3. PPE COMPLIANCE:",
                "   • Enforce mandatory PPE usage policy (helmet, jacket, gloves, boots)",
                "   • Provide company-issued PPE if necessary",
                "   • Conduct regular PPE condition checks",
                "",
                "4. INTEGRATE INTO SAFETY SOP:",
                "   • Include vehicle inspection as part of daily work routine",
                "   • Establish clear reporting channels for safety issues",
                "   • Implement consequences for non-compliance",
                "",
                "5. SUPPLEMENTARY TRAINING:",
                "   • Conduct basic vehicle maintenance workshop for employees",
                "   • Provide refresher training on pre-ride safety checks"
            ]
            for rec in recommendations:
                doc.add_paragraph(rec)
        else:
            doc.add_paragraph("✓ EXCELLENT RESULT: All vehicles inspected were found to be in good working condition with no safety concerns identified.")
            doc.add_paragraph()
            doc.add_paragraph(
                "This indicates strong commitment to vehicle maintenance and safety standards. We recommend "
                "continuing current maintenance practices and conducting regular quarterly safety inspections."
            )
        
        doc.add_page_break()
        
        # COORDINATOR FEEDBACK (Enhanced)
        doc.add_heading('11. COORDINATOR FEEDBACK', 1)
        coordinator_feedback = await db.coordinator_feedback.find_one({"session_id": session_id}, {"_id": 0})
        if coordinator_feedback:
            doc.add_paragraph(
                "The training coordinator provided comprehensive observations on logistics, participant engagement, "
                "and overall program execution. Key observations and recommendations are detailed below:"
            )
            doc.add_paragraph()
            
            responses = coordinator_feedback.get('responses', {})
            for question_id, answer in responses.items():
                # Get question text from template
                template = await db.feedback_templates.find_one({"id": "coordinator_feedback_template"}, {"_id": 0})
                if template:
                    for q in template.get('questions', []):
                        if q.get('id') == question_id:
                            doc.add_paragraph(f"{q.get('question')}:", style='Heading 3')
                            if q.get('type') == 'rating':
                                stars = '⭐' * int(answer) if isinstance(answer, (int, float)) else answer
                                doc.add_paragraph(f"   Rating: {stars} ({answer}/{q.get('scale', 5)})")
                            else:
                                doc.add_paragraph(f"   {answer}")
                            doc.add_paragraph()
            
            # Add formal closing
            doc.add_paragraph()
            doc.add_paragraph(
                f"The coordinator acknowledges the strong collaboration between {company.get('name', 'the company')}, "
                "MDDRC training team, and participants throughout the program. Participants demonstrated excellent "
                "discipline and commitment to learning, contributing to the overall success of the training initiative."
            )
        else:
            doc.add_paragraph("[Coordinator feedback pending submission]")
        
        doc.add_page_break()
        
        # RECOMMENDATIONS MOVING FORWARD
        doc.add_heading('12. RECOMMENDATIONS MOVING FORWARD', 1)
        doc.add_paragraph(
            "Based on the training outcomes, participant feedback, and safety observations, "
            "the following recommendations are proposed to sustain and enhance the safety culture:"
        )
        doc.add_paragraph()
        
        recommendations_forward = [
            "1. ENFORCE PRE-RIDE/PRE-DRIVE SAFETY CHECKS:",
            f"   • Mandate daily pre-{'ride' if is_motorcycle else 'drive'} safety inspections using a standardized checklist",
            "   • Implement digital logging system for inspection records",
            "   • Designate safety officers to conduct random spot checks",
            "",
            "2. MONTHLY VERIFICATION PROGRAM:",
            "   • Conduct monthly vehicle condition audits",
            "   • Schedule preventive maintenance based on mileage/usage",
            "   • Track and analyze vehicle-related incidents",
            "",
            "3. MAINTENANCE SUPPORT:",
            "   • Establish partnerships with authorized service centers for employee discounts",
            "   • Provide maintenance subsidy program for safety-critical components",
            "   • Create emergency maintenance fund for immediate safety repairs",
            "",
            "4. POST-TRAINING MATERIALS:",
            "   • Distribute safety reminder cards or posters for display",
            "   • Share digital safety tips via company communication channels",
            "   • Conduct quarterly safety awareness campaigns",
            "",
            "5. TAILOR PRACTICALS TO CLIENT ROUTES:",
            "   • Identify high-risk routes and areas commonly used by employees",
            "   • Conduct route-specific safety briefings",
            "   • Share incident hotspot maps and avoidance strategies",
            "",
            "6. PROMOTE SAFETY CULTURE:",
            "   • Recognize and reward safe riding/driving behavior",
            "   • Establish peer mentorship program for new employees",
            "   • Include safety KPIs in performance evaluations",
            "",
            "7. FOLLOW-UP FOR OUTLIERS:",
            f"   • Provide one-on-one coaching for {len([p for p in participants if p['improvement'] < 0])} participants who showed score decrease" if any(p['improvement'] < 0 for p in participants) else "   • Continue monitoring participant performance in real-world scenarios",
            "   • Conduct 3-month post-training assessment to measure retention",
            "   • Offer refresher training for employees showing concerning behavior"
        ]
        
        for rec in recommendations_forward:
            doc.add_paragraph(rec)
        
        doc.add_page_break()
        
        # CONCLUSION
        doc.add_heading('13. CONCLUSION', 1)
        doc.add_paragraph(
            f"The Defensive {'Riding' if is_motorcycle else 'Driving'} Training conducted for "
            f"{company.get('name', 'N/A')} from {session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')} "
            f"was successfully completed with {len(participants)} participants demonstrating measurable improvement in "
            f"safety awareness and defensive {'riding' if is_motorcycle else 'driving'} competencies."
        )
        doc.add_paragraph()
        
        doc.add_paragraph(
            f"Key achievements include an average score improvement of {improvement:+.1f}%, "
            f"a post-training pass rate of {(post_pass_count/len(participants)*100):.0f}%, and high participant "
            f"satisfaction levels. The training successfully enhanced hazard recognition skills, emergency response "
            f"techniques, and safety-first mindset among participants."
        )
        doc.add_paragraph()
        
        if vehicle_issues:
            doc.add_paragraph(
                f"Vehicle safety inspections identified {len(vehicle_issues)} {'motorcycles' if is_motorcycle else 'vehicles'} "
                "requiring immediate attention. Detailed recommendations have been provided to address these concerns "
                "and prevent potential accidents."
            )
            doc.add_paragraph()
        
        doc.add_paragraph(
            "MDDRC extends sincere appreciation to the management and employees of "
            f"{company.get('name', 'the company')} for their strong collaboration and commitment throughout this program. "
            "The enthusiastic participation and positive learning attitude demonstrated by all participants contributed "
            "significantly to the program's success."
        )
        doc.add_paragraph()
        
        doc.add_paragraph(
            "We remain committed to supporting your organization's journey towards a safer workplace and look forward "
            "to continued partnership in promoting road safety excellence."
        )
        
        doc.add_page_break()
        
        # APPENDICES
        doc.add_heading('APPENDICES', 1)
        
        # APPENDIX A: Pre & Post Test Raw Scores
        doc.add_heading('Appendix A: Pre & Post Test Raw Scores', 2)
        appendix_table = doc.add_table(rows=len(participants)+1, cols=5)
        appendix_table.style = 'Light Grid Accent 1'
        hdr = appendix_table.rows[0].cells
        hdr[0].text = 'No.'
        hdr[1].text = 'Participant Name'
        hdr[2].text = 'Pre-Test Score'
        hdr[3].text = 'Post-Test Score'
        hdr[4].text = 'Improvement'
        
        for idx, p in enumerate(participants, 1):
            row = appendix_table.rows[idx].cells
            row[0].text = str(idx)
            row[1].text = p['name']
            row[2].text = f"{p['pre_test_score']:.0f}%"
            row[3].text = f"{p['post_test_score']:.0f}%"
            row[4].text = f"{p['improvement']:+.0f}%"
        
        doc.add_page_break()
        
        # APPENDIX B: Vehicle Condition Photos
        if vehicle_issues:
            doc.add_heading('Appendix B: Vehicle Condition Photos', 2)
            doc.add_paragraph("Photographic evidence of safety issues identified during vehicle inspections:")
            doc.add_paragraph()
            for vehicle_issue in vehicle_issues:
                doc.add_paragraph(f"{vehicle_issue['participant_name']}:", style='Heading 4')
                for issue in vehicle_issue['issues']:
                    if issue['photo_url']:
                        doc.add_paragraph(f"• {issue['item']}")
                        doc.add_paragraph(f"  [Photo URL: {issue['photo_url']}]")
                doc.add_paragraph()
            doc.add_page_break()
        
        # APPENDIX C: Feedback Form Summary
        doc.add_heading('Appendix C: Participant Feedback Form Summary', 2)
        if feedback_data:
            doc.add_paragraph("Complete participant feedback responses:")
            doc.add_paragraph()
            for idx, fb in enumerate(feedback_data, 1):
                doc.add_paragraph(f"{idx}. {fb['participant_name']}", style='Heading 4')
                for response in fb['responses']:
                    doc.add_paragraph(f"   Q: {response['question']}")
                    doc.add_paragraph(f"   A: {response['answer']}")
                doc.add_paragraph()
        else:
            doc.add_paragraph("[No feedback data available]")
        
        doc.add_page_break()
        
        # SIGNATURES
        doc.add_heading('APPROVAL & SIGNATURES', 1)
        doc.add_paragraph()
        sig_table = doc.add_table(rows=4, cols=2)
        sig_table.style = 'Light List'
        
        sig_table.rows[0].cells[0].text = 'Prepared by:'
        sig_table.rows[0].cells[1].text = ''
        sig_table.rows[1].cells[0].text = 'Name:'
        sig_table.rows[1].cells[1].text = current_user.full_name
        sig_table.rows[2].cells[0].text = 'Position:'
        sig_table.rows[2].cells[1].text = 'Training Coordinator'
        sig_table.rows[3].cells[0].text = 'Date:'
        sig_table.rows[3].cells[1].text = get_malaysia_time().strftime('%Y-%m-%d')
        
        doc.add_paragraph()
        doc.add_paragraph()
        doc.add_paragraph("_" * 60)
        doc.add_paragraph()
        
        sig_table2 = doc.add_table(rows=4, cols=2)
        sig_table2.style = 'Light List'
        sig_table2.rows[0].cells[0].text = 'Reviewed & Approved by:'
        sig_table2.rows[0].cells[1].text = ''
        sig_table2.rows[1].cells[0].text = 'Name:'
        sig_table2.rows[1].cells[1].text = '________________________'
        sig_table2.rows[2].cells[0].text = 'Position:'
        sig_table2.rows[2].cells[1].text = 'Person In Charge / Supervisor'
        sig_table2.rows[3].cells[0].text = 'Date:'
        sig_table2.rows[3].cells[1].text = '________________________'
        
        doc.add_paragraph()
        doc.add_paragraph()
        footer = doc.add_paragraph('--- END OF REPORT ---')
        footer.alignment = 1
        
        doc.add_page_break()
        
        # SIGNATURES
        doc.add_heading('11. SIGNATURES', 1)
        doc.add_paragraph()
        doc.add_paragraph("_" * 40)
        doc.add_paragraph(f"Coordinator: {current_user.full_name}")
        doc.add_paragraph(f"Date: ________________")
        doc.add_paragraph()
        doc.add_paragraph()
        doc.add_paragraph("_" * 40)
        doc.add_paragraph("PIC/Supervisor Signature")
        doc.add_paragraph(f"Date: ________________")
        
        # Save DOCX
        report_filename = f"Training_Report_{session_id}_{get_malaysia_time().strftime('%Y%m%d_%H%M%S')}.docx"
        report_path = REPORT_DIR / report_filename
        doc.save(str(report_path))
        
        # Update training report record with DOCX filename
        await db.training_reports.update_one(
            {"session_id": session_id},
            {"$set": {"docx_filename": report_filename, "generated_at": get_malaysia_time().isoformat()}},
            upsert=True
        )
        
        return {
            "message": "DOCX report generated successfully",
            "filename": report_filename,
            "download_url": f"/api/training-reports/{session_id}/download-docx"
        }
        
    except Exception as e:
        logging.error(f"Failed to generate DOCX report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@api_router.get("/training-reports/{session_id}/status")
async def get_training_report_status(session_id: str, current_user: User = Depends(get_current_user)):
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


@api_router.get("/training-reports/{session_id}/download-docx")
async def download_docx_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Download the generated DOCX report"""
    
    if current_user.role not in ["coordinator", "admin", "supervisor"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get report filename from database
    training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    if not training_report or not training_report.get('docx_filename'):
        raise HTTPException(status_code=404, detail="Report not found. Please generate it first.")
    
    report_path = REPORT_DIR / training_report['docx_filename']
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        path=str(report_path),
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=training_report['docx_filename'],
        headers={"Content-Disposition": f"attachment; filename={training_report['docx_filename']}"}
    )

@api_router.post("/training-reports/{session_id}/upload-edited-docx")
async def upload_edited_docx(
    session_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload edited DOCX report"""
    
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can upload reports")
    
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only DOCX files are allowed")
    
    try:
        # Save edited DOCX
        edited_filename = f"Training_Report_{session_id}_edited_{get_malaysia_time().strftime('%Y%m%d_%H%M%S')}.docx"
        edited_path = REPORT_DIR / edited_filename
        
        with open(edited_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update database
        await db.training_reports.update_one(
            {"session_id": session_id},
            {"$set": {
                "edited_docx_filename": edited_filename,
                "uploaded_at": get_malaysia_time().isoformat()
            }},
            upsert=True
        )
        
        return {
            "message": "Edited report uploaded successfully",
            "filename": edited_filename
        }
        
    except Exception as e:
        logging.error(f"Failed to upload edited report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload report: {str(e)}")



@api_router.post("/training-reports/{session_id}/upload-final-pdf")
async def upload_final_pdf_report(
    session_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload final edited PDF report"""
    
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can upload reports")
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Check file size (max 20MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    max_size = 20 * 1024 * 1024  # 20MB
    if file_size > max_size:
        raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")
    
    try:
        # Save final PDF
        pdf_filename = f"Training_Report_{session_id}_final_{get_malaysia_time().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = REPORT_PDF_DIR / pdf_filename
        
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get session and program details
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        program = None
        company = None
        if session:
            if session.get('program_id'):
                program = await db.programs.find_one({"id": session['program_id']}, {"_id": 0})
            if session.get('company_id'):
                company = await db.companies.find_one({"id": session['company_id']}, {"_id": 0})
        
        # Update database with submitted status
        await db.training_reports.update_one(
            {"session_id": session_id},
            {"$set": {
                "final_pdf_filename": pdf_filename,
                "pdf_url": f"/api/static/reports_pdf/{pdf_filename}",
                "status": "submitted",
                "submitted_at": get_malaysia_time().isoformat(),
                "submitted_by": current_user.id,
                "program_id": program.get('id') if program else None,
                "company_id": company.get('id') if company else None,
                "session_name": session.get('name') if session else None,
                "session_start_date": session.get('start_date') if session else None,
                "session_end_date": session.get('end_date') if session else None
            }},
            upsert=True
        )
        
        return {
            "message": "Final report uploaded successfully. You can now mark the session as completed.",
            "filename": pdf_filename,
            "pdf_url": f"/api/static/reports_pdf/{pdf_filename}"
        }
        
    except Exception as e:
        logging.error(f"Failed to upload final PDF: {str(e)}")


# Get submitted reports for supervisor
@api_router.get("/training-reports/supervisor/sessions")
async def get_supervisor_reports(current_user: User = Depends(get_current_user)):
    """Get all submitted reports for sessions assigned to supervisor"""
    
    if current_user.role not in ["supervisor", "pic_supervisor", "admin"]:
        raise HTTPException(status_code=403, detail="Only supervisors and admins can access this")
    
    # Get sessions assigned to supervisor (check both supervisor_id and supervisor_ids array)
    if current_user.role in ["supervisor", "pic_supervisor"]:
        sessions = await db.sessions.find({
            "$or": [
                {"supervisor_id": current_user.id},
                {"supervisor_ids": {"$in": [current_user.id]}}
            ]
        }, {"_id": 0}).to_list(100)
    else:
        # Admin can see all
        sessions = await db.sessions.find({}, {"_id": 0}).to_list(1000)
    
    session_ids = [s['id'] for s in sessions]
    
    # Get submitted reports for these sessions that are marked as completed
    # Only show reports that have been pushed to supervisors (session marked as completed)
    reports = await db.training_reports.find(
        {
            "session_id": {"$in": session_ids},
            "status": "submitted",
            "available_to_supervisors": True  # Only show completed/archived sessions
        },
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with session details
    enriched_reports = []
    for report in reports:
        session = next((s for s in sessions if s['id'] == report['session_id']), None)
        if session:
            enriched_reports.append({
                **report,
                "session_name": session.get('name'),
                "session_start_date": session.get('start_date'),
                "session_end_date": session.get('end_date'),
                "location": session.get('location')
            })
    
    return enriched_reports

@api_router.post("/training-reports/{session_id}/submit-final")
async def submit_final_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Submit final report - converts to PDF and notifies supervisor/admin"""
    
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can submit reports")
    
    try:
        # Get the latest report (edited if exists, otherwise generated)
        training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
        
        if not training_report:
            raise HTTPException(status_code=404, detail="No report found. Please generate a report first.")
        
        docx_filename = training_report.get('edited_docx_filename') or training_report.get('docx_filename')
        
        if not docx_filename:
            raise HTTPException(status_code=404, detail="No report file found")
        
        docx_path = REPORT_DIR / docx_filename
        
        if not docx_path.exists():
            raise HTTPException(status_code=404, detail="Report file not found")
        
        # Convert DOCX to PDF using LibreOffice
        pdf_filename = docx_filename.replace('.docx', '.pdf')
        pdf_path = REPORT_PDF_DIR / pdf_filename
        
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', str(REPORT_PDF_DIR),
            str(docx_path)
        ], check=True)
        
        # Update training report status
        await db.training_reports.update_one(
            {"session_id": session_id},
            {"$set": {
                "pdf_filename": pdf_filename,
                "status": "submitted",
                "submitted_at": get_malaysia_time().isoformat(),
                "submitted_by": current_user.id
            }}
        )
        
        # Get session and create notifications for supervisor and admin
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        
        # Notify supervisor
        if session.get('supervisor_ids'):
            for supervisor_id in session['supervisor_ids']:
                await db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": supervisor_id,
                    "type": "training_report_submitted",
                    "message": f"Training report for {session.get('name')} has been submitted",
                    "session_id": session_id,
                    "read": False,
                    "created_at": get_malaysia_time().isoformat()
                })
        
        # Notify all admins
        admins = await db.users.find({"role": "admin"}, {"_id": 0}).to_list(100)
        for admin in admins:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": admin['id'],
                "type": "training_report_submitted",
                "message": f"Training report for {session.get('name')} has been submitted by {current_user.full_name}",
                "session_id": session_id,
                "read": False,
                "created_at": get_malaysia_time().isoformat()
            })
        
        return {
            "message": "Report submitted successfully and PDF generated",
            "pdf_filename": pdf_filename,
            "download_url": f"/api/training-reports/{session_id}/download-pdf"
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"PDF conversion failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to convert report to PDF")
    except Exception as e:
        logging.error(f"Failed to submit report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit report: {str(e)}")

@api_router.get("/training-reports/{session_id}/download-pdf")
async def download_pdf_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Download the final PDF report"""
    
    if current_user.role not in ["coordinator", "admin", "supervisor"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get report filename from database
    training_report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    if not training_report or not training_report.get('pdf_filename'):
        raise HTTPException(status_code=404, detail="PDF report not found. Please submit the report first.")
    
    pdf_path = REPORT_PDF_DIR / training_report['pdf_filename']
    
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        path=str(pdf_path),
        media_type='application/pdf',
        filename=training_report['pdf_filename']
    )

# Trainer Checklist Routes
@api_router.post("/trainer-checklist/submit")
async def submit_trainer_checklist(checklist_data: TrainerChecklistSubmit, current_user: User = Depends(get_current_user)):
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can submit checklists")
    
    # Create checklist
    checklist_obj = VehicleChecklist(
        participant_id=checklist_data.participant_id,
        session_id=checklist_data.session_id,
        interval="trainer_inspection",
        checklist_items=[item.model_dump() for item in checklist_data.items],
        verified_by=current_user.id,
        verified_at=datetime.now(timezone.utc),
        verification_status="completed"
    )
    
    doc = checklist_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    doc['verified_at'] = doc['verified_at'].isoformat()
    
    # Use upsert to prevent duplicate checklists for the same participant/session
    await db.vehicle_checklists.update_one(
        {
            "participant_id": checklist_data.participant_id,
            "session_id": checklist_data.session_id
        },
        {"$set": doc},
        upsert=True
    )
    
    # Update participant_access to mark checklist as completed
    await db.participant_access.update_one(
        {
            "participant_id": checklist_data.participant_id,
            "session_id": checklist_data.session_id
        },
        {"$set": {"checklist_completed": True}},
        upsert=True
    )
    
    # If chief trainer submitted comments, save to session
    if checklist_data.chief_trainer_comments:
        session = await db.sessions.find_one({"id": checklist_data.session_id}, {"_id": 0})
        if session:
            # Check if current trainer is chief
            trainer_assignments = session.get('trainer_assignments', [])
            is_chief = any(t['trainer_id'] == current_user.id and t.get('role') == 'chief' for t in trainer_assignments)
            
            if is_chief:
                await db.sessions.update_one(
                    {"id": checklist_data.session_id},
                    {"$set": {
                        "chief_trainer_comments": checklist_data.chief_trainer_comments,
                        "chief_trainer_id": current_user.id,
                        "chief_trainer_name": current_user.full_name,
                        "comments_submitted_at": get_malaysia_time().isoformat()
                    }}
                )
    
    return {"message": "Checklist submitted successfully", "checklist_id": checklist_obj.id}

@api_router.get("/trainer-checklist/{session_id}/assigned-participants")
async def get_assigned_participants(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all trainers in session
    trainer_assignments = session.get('trainer_assignments', [])
    trainers = [t['trainer_id'] for t in trainer_assignments]
    
    if not trainers:
        return []
    
    # Get all participant IDs
    all_participant_ids = session.get('participant_ids', [])
    
    # ===== DYNAMIC ATTENDANCE-BASED FILTERING =====
    # Logic: Participant is PRESENT if EITHER:
    #   1. Has clocked in, OR
    #   2. Coordinator marked as "present"
    # This is dynamic - late arrivals are automatically added when they clock in or get marked
    
    # Get all clock-in records for this session
    attendance_records = await db.attendance.find(
        {"session_id": session_id, "clock_in": {"$exists": True, "$ne": None, "$ne": ""}},
        {"_id": 0, "participant_id": 1}
    ).to_list(1000)
    clocked_in_ids = set(record["participant_id"] for record in attendance_records)
    
    # Get coordinator-marked attendance status
    coordinator_attendance = await db.participant_attendance.find(
        {"session_id": session_id},
        {"_id": 0, "participant_id": 1, "status": 1}
    ).to_list(1000)
    
    # Build sets for present/absent based on coordinator marking
    marked_present_ids = set(
        record["participant_id"] for record in coordinator_attendance 
        if record.get("status") == "present"
    )
    marked_absent_ids = set(
        record["participant_id"] for record in coordinator_attendance 
        if record.get("status") == "absent"
    )
    
    # Determine which participants are PRESENT (either clocked in OR marked present)
    # A participant is PRESENT if:
    #   - They clocked in (regardless of coordinator marking), OR
    #   - Coordinator marked them as "present" (even without clock-in)
    present_participant_ids = []
    
    # Check if training has started (at least one person clocked in or marked)
    training_started = len(clocked_in_ids) > 0 or len(marked_present_ids) > 0 or len(marked_absent_ids) > 0
    
    for pid in all_participant_ids:
        if pid in clocked_in_ids:
            # Clocked in = PRESENT (even if coordinator marked absent by mistake)
            present_participant_ids.append(pid)
        elif pid in marked_present_ids:
            # Coordinator marked present (even without clock-in) = PRESENT
            present_participant_ids.append(pid)
        elif not training_started:
            # Training hasn't started yet - include everyone
            present_participant_ids.append(pid)
        # else: Not clocked in AND not marked present AND training started = ABSENT (excluded)
    
    participant_ids = present_participant_ids
    # ===== END DYNAMIC FILTERING =====
    
    total_participants = len(participant_ids)
    total_trainers = len(trainers)
    
    if total_trainers == 0 or total_participants == 0:
        return []
    
    # DYNAMIC EQUAL DISTRIBUTION among trainers
    # Recalculated each time based on current attendance
    participants_per_trainer = total_participants // total_trainers
    remainder = total_participants % total_trainers
    
    # Find current trainer's index in the list
    try:
        current_trainer_index = trainers.index(current_user.id)
    except ValueError:
        return []
    
    # Calculate start index for this trainer
    # Remainder goes to LAST trainers (not first)
    # E.g., 16 participants, 3 trainers = 5, 5, 6 (last gets extra)
    remainder_start_index = total_trainers - remainder  # Index where remainder starts
    
    start_index = 0
    for i in range(current_trainer_index):
        start_index += participants_per_trainer + (1 if i >= remainder_start_index else 0)
    
    # Calculate assigned count for this trainer
    assigned_count = participants_per_trainer + (1 if current_trainer_index >= remainder_start_index else 0)
    
    end_index = start_index + assigned_count
    assigned_participant_ids = participant_ids[start_index:end_index]
    
    # Get participant details
    participants = await db.users.find(
        {"id": {"$in": assigned_participant_ids}},
        {"_id": 0, "password": 0}
    ).to_list(100)
    
    # Sort by name for consistent ordering
    participants.sort(key=lambda p: p.get('full_name', ''))
    
    # Get vehicle details and checklist status for each
    for participant in participants:
        vehicle = await db.vehicle_details.find_one({
            "participant_id": participant['id'],
            "session_id": session_id
        }, {"_id": 0})
        participant['vehicle_details'] = vehicle
        
        # Get existing checklist
        checklist = await db.vehicle_checklists.find_one({
            "participant_id": participant['id'],
            "session_id": session_id,
            "verified_by": current_user.id
        }, {"_id": 0})
        participant['checklist'] = checklist
        
        # Add attendance status for reference
        participant['clocked_in'] = participant['id'] in clocked_in_ids
        participant['marked_present'] = participant['id'] in marked_present_ids
    
    return participants

# Vehicle Checklist Routes
@api_router.post("/checklists/submit", response_model=VehicleChecklist)
async def submit_checklist(checklist_data: ChecklistSubmit, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can submit checklists")
    
    checklist_obj = VehicleChecklist(
        participant_id=current_user.id,
        session_id=checklist_data.session_id,
        interval=checklist_data.interval,
        checklist_items=checklist_data.checklist_items
    )
    
    doc = checklist_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    if doc.get('verified_at'):
        doc['verified_at'] = doc['verified_at'].isoformat()
    
    await db.vehicle_checklists.insert_one(doc)
    
    await db.participant_access.update_one(
        {"participant_id": current_user.id, "session_id": checklist_data.session_id},
        {"$set": {"checklist_submitted": True}}
    )
    
    return checklist_obj

@api_router.get("/checklists/participant/{participant_id}")
async def get_participant_checklists(participant_id: str, current_user: User = Depends(get_current_user)):
    """Get all checklists for a participant (completed by trainers)"""
    # Allow participant themselves, trainers, coordinators, and admins
    if current_user.role not in ["trainer", "coordinator", "admin"] and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    checklists = await db.vehicle_checklists.find({
        "participant_id": participant_id
    }, {"_id": 0}).to_list(1000)
    
    for checklist in checklists:
        if isinstance(checklist.get('submitted_at'), str):
            checklist['submitted_at'] = datetime.fromisoformat(checklist['submitted_at'])
        if checklist.get('verified_at') and isinstance(checklist['verified_at'], str):
            checklist['verified_at'] = datetime.fromisoformat(checklist['verified_at'])
    
    return checklists

@api_router.get("/vehicle-checklists/{session_id}/{participant_id}")
async def get_checklist(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    # Allow trainer, coordinator, admin, or the participant themselves
    if current_user.role not in ["trainer", "coordinator", "admin"] and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    checklist = await db.vehicle_checklists.find_one({
        "participant_id": participant_id,
        "session_id": session_id
    }, {"_id": 0})
    
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    
    if isinstance(checklist.get('submitted_at'), str):
        checklist['submitted_at'] = datetime.fromisoformat(checklist['submitted_at'])
    if checklist.get('verified_at') and isinstance(checklist['verified_at'], str):
        checklist['verified_at'] = datetime.fromisoformat(checklist['verified_at'])
    
    return checklist

@api_router.get("/checklists/session/{session_id}")
async def get_checklists_by_session(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all checklists for a session - for trainers to check completion status"""
    # Allow trainers, coordinators, and admins
    if current_user.role not in ["trainer", "coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    checklists = await db.vehicle_checklists.find({
        "session_id": session_id
    }, {"_id": 0}).to_list(1000)
    
    # Convert datetime strings
    for checklist in checklists:
        if isinstance(checklist.get('submitted_at'), str):
            checklist['submitted_at'] = datetime.fromisoformat(checklist['submitted_at'])
        if checklist.get('verified_at') and isinstance(checklist['verified_at'], str):
            checklist['verified_at'] = datetime.fromisoformat(checklist['verified_at'])
    
    return checklists


@api_router.get("/checklists/participant/{participant_id}", response_model=List[VehicleChecklist])
async def get_participant_checklists(participant_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role == "participant" and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    checklists = await db.vehicle_checklists.find({"participant_id": participant_id}, {"_id": 0}).to_list(100)
    for checklist in checklists:
        if isinstance(checklist.get('submitted_at'), str):
            checklist['submitted_at'] = datetime.fromisoformat(checklist['submitted_at'])
        if checklist.get('verified_at') and isinstance(checklist['verified_at'], str):
            checklist['verified_at'] = datetime.fromisoformat(checklist['verified_at'])
    return checklists

@api_router.get("/checklists/pending", response_model=List[VehicleChecklist])
async def get_pending_checklists(current_user: User = Depends(get_current_user)):
    if current_user.role != "supervisor" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only supervisors can verify checklists")
    
    checklists = await db.vehicle_checklists.find({"verification_status": "pending"}, {"_id": 0}).to_list(100)
    for checklist in checklists:
        if isinstance(checklist.get('submitted_at'), str):
            checklist['submitted_at'] = datetime.fromisoformat(checklist['submitted_at'])
    return checklists

@api_router.post("/checklists/verify")
async def verify_checklist(verification: ChecklistVerify, current_user: User = Depends(get_current_user)):
    if current_user.role != "supervisor" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only supervisors can verify checklists")
    
    result = await db.vehicle_checklists.update_one(
        {"id": verification.checklist_id},
        {
            "$set": {
                "verification_status": verification.status,
                "verified_by": current_user.id,
                "verified_at": get_malaysia_time().isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Checklist not found")
    
    return {"message": "Checklist verified successfully"}

# Course Feedback Routes
# Feedback Template Routes
@api_router.post("/feedback-templates", response_model=FeedbackTemplate)
async def create_feedback_template(template_data: FeedbackTemplateCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can create feedback templates")
    
    # Delete existing template for this program
    await db.feedback_templates.delete_many({"program_id": template_data.program_id})
    
    template_obj = FeedbackTemplate(
        program_id=template_data.program_id,
        questions=template_data.questions
    )
    
    doc = template_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.feedback_templates.insert_one(doc)
    
    return template_obj

@api_router.get("/feedback-templates/program/{program_id}")
async def get_feedback_template(program_id: str, current_user: User = Depends(get_current_user)):
    template = await db.feedback_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        # Return default template instead of error
        return {
            "program_id": program_id,
            "questions": [
                {"question": "Overall Training Experience", "type": "rating", "required": True},
                {"question": "Training Content Quality", "type": "rating", "required": True},
                {"question": "Trainer Effectiveness", "type": "rating", "required": True},
                {"question": "Venue & Facilities", "type": "rating", "required": True},
                {"question": "Suggestions for Improvement", "type": "text", "required": False},
                {"question": "Additional Comments", "type": "text", "required": False}
            ]
        }
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    
    return template

@api_router.get("/feedback/templates/program/{program_id}")
async def get_feedback_template_alias(program_id: str, current_user: User = Depends(get_current_user)):
    """Alias endpoint for backward compatibility - returns array format"""
    template = await db.feedback_templates.find_one({"program_id": program_id}, {"_id": 0})
    if not template:
        # Return default template in array format
        return [{
            "program_id": program_id,
            "questions": [
                {"question": "Overall Training Experience", "type": "rating", "required": True},
                {"question": "Training Content Quality", "type": "rating", "required": True},
                {"question": "Trainer Effectiveness", "type": "rating", "required": True},
                {"question": "Venue & Facilities", "type": "rating", "required": True},
                {"question": "Suggestions for Improvement", "type": "text", "required": False},
                {"question": "Additional Comments", "type": "text", "required": False}
            ]
        }]
    
    if isinstance(template.get('created_at'), str):
        template['created_at'] = datetime.fromisoformat(template['created_at'])
    
    return [template]  # Return as array for backward compatibility

@api_router.delete("/feedback-templates/{template_id}")
async def delete_feedback_template(template_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and assistant admins can delete feedback templates")
    
    result = await db.feedback_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback template not found")
    
    return {"message": "Feedback template deleted successfully"}

@api_router.post("/feedback/submit", response_model=CourseFeedback)
async def submit_feedback(feedback_data: FeedbackSubmit, current_user: User = Depends(get_current_user)):
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can submit feedback")
    
    # Check if feedback already exists for this participant and session
    existing_feedback = await db.course_feedback.find_one({
        "participant_id": current_user.id,
        "session_id": feedback_data.session_id
    })
    
    if existing_feedback:
        raise HTTPException(status_code=400, detail="You have already submitted feedback for this session")
    
    feedback_obj = CourseFeedback(
        participant_id=current_user.id,
        session_id=feedback_data.session_id,
        program_id=feedback_data.program_id,
        responses=feedback_data.responses
    )
    
    doc = feedback_obj.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    await db.course_feedback.insert_one(doc)
    
    # Ensure participant_access record exists and update feedback status
    # Set both feedback_completed and feedback_submitted for consistency
    await db.participant_access.update_one(
        {"participant_id": current_user.id, "session_id": feedback_data.session_id},
        {"$set": {"feedback_completed": True, "feedback_submitted": True}},
        upsert=True
    )
    
    return feedback_obj

@api_router.get("/feedback/session/{session_id}", response_model=List[CourseFeedback])
async def get_session_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "supervisor", "coordinator", "trainer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    feedback = await db.course_feedback.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    for fb in feedback:
        if isinstance(fb.get('submitted_at'), str):
            fb['submitted_at'] = datetime.fromisoformat(fb['submitted_at'])
    return feedback

@api_router.get("/feedback/company/{company_id}")
async def get_company_feedback(company_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view company feedback")
    
    sessions = await db.sessions.find({"company_id": company_id}, {"_id": 0}).to_list(1000)
    session_ids = [s['id'] for s in sessions]
    
    feedback = await db.course_feedback.find({"session_id": {"$in": session_ids}}, {"_id": 0}).to_list(1000)
    for fb in feedback:
        if isinstance(fb.get('submitted_at'), str):
            fb['submitted_at'] = datetime.fromisoformat(fb['submitted_at'])
    
    return feedback



# Coordinator & Chief Trainer Feedback Routes

# Get Coordinator Feedback Template
@api_router.get("/coordinator-feedback-template")
async def get_coordinator_feedback_template(current_user: User = Depends(get_current_user)):
    """Get coordinator feedback template"""
    template = await db.feedback_templates.find_one({"id": "coordinator_feedback_template"}, {"_id": 0})
    if not template:
        # Create default template
        default_template = CoordinatorFeedbackTemplate()
        doc = default_template.model_dump()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.feedback_templates.insert_one(doc)
        return default_template
    return template

# Update Coordinator Feedback Template (Admin only)
@api_router.put("/coordinator-feedback-template")
async def update_coordinator_feedback_template(
    template_update: FeedbackTemplateUpdate, 
    current_user: User = Depends(get_current_user)
):
    """Update coordinator feedback template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update feedback templates")
    
    await db.feedback_templates.update_one(
        {"id": "coordinator_feedback_template"},
        {
            "$set": {
                "questions": template_update.questions,
                "updated_at": get_malaysia_time().isoformat()
            }
        },
        upsert=True
    )
    return {"message": "Template updated successfully"}

# Get Chief Trainer Feedback Template
@api_router.get("/chief-trainer-feedback-template")
async def get_chief_trainer_feedback_template(current_user: User = Depends(get_current_user)):
    """Get chief trainer feedback template"""
    template = await db.feedback_templates.find_one({"id": "chief_trainer_feedback_template"}, {"_id": 0})
    if not template:
        # Create default template
        default_template = ChiefTrainerFeedbackTemplate()
        doc = default_template.model_dump()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.feedback_templates.insert_one(doc)
        return default_template
    return template

# Update Chief Trainer Feedback Template (Admin only)
@api_router.put("/chief-trainer-feedback-template")
async def update_chief_trainer_feedback_template(
    template_update: FeedbackTemplateUpdate, 
    current_user: User = Depends(get_current_user)
):
    """Update chief trainer feedback template (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update feedback templates")
    
    await db.feedback_templates.update_one(
        {"id": "chief_trainer_feedback_template"},
        {
            "$set": {
                "questions": template_update.questions,
                "updated_at": get_malaysia_time().isoformat()
            }
        },
        upsert=True
    )
    return {"message": "Template updated successfully"}

# Submit Coordinator Feedback
@api_router.post("/coordinator-feedback/{session_id}")
async def submit_coordinator_feedback(
    session_id: str,
    responses: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit coordinator feedback for a session"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators and admins can submit coordinator feedback")
    
    # Check if feedback already exists
    existing = await db.coordinator_feedback.find_one({"session_id": session_id}, {"_id": 0})
    
    feedback = CoordinatorFeedback(
        session_id=session_id,
        coordinator_id=current_user.id,
        responses=responses
    )
    
    doc = feedback.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    if existing:
        # Update existing feedback
        await db.coordinator_feedback.update_one(
            {"session_id": session_id},
            {"$set": doc}
        )
    else:
        # Insert new feedback
        await db.coordinator_feedback.insert_one(doc)
    
    return {"message": "Coordinator feedback submitted successfully", "feedback": feedback}

# Get Coordinator Feedback for Session
@api_router.get("/coordinator-feedback/{session_id}")
async def get_coordinator_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    """Get coordinator feedback for a session"""
    feedback = await db.coordinator_feedback.find_one({"session_id": session_id}, {"_id": 0})
    if not feedback:
        return None
    return feedback

# Submit Chief Trainer Feedback
@api_router.post("/chief-trainer-feedback/{session_id}")
async def submit_chief_trainer_feedback(
    session_id: str,
    responses: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit chief trainer feedback for a session"""
    if current_user.role not in ["chief_trainer", "trainer", "admin"]:
        raise HTTPException(status_code=403, detail="Only trainers and admins can submit chief trainer feedback")
    
    # Check if feedback already exists
    existing = await db.chief_trainer_feedback.find_one({"session_id": session_id}, {"_id": 0})
    
    feedback = ChiefTrainerFeedback(
        session_id=session_id,
        trainer_id=current_user.id,
        responses=responses
    )
    
    doc = feedback.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    
    if existing:
        # Update existing feedback
        await db.chief_trainer_feedback.update_one(
            {"session_id": session_id},
            {"$set": doc}
        )
    else:
        # Insert new feedback
        await db.chief_trainer_feedback.insert_one(doc)
    
    return {"message": "Chief trainer feedback submitted successfully", "feedback": feedback}

# Get Chief Trainer Feedback for Session
@api_router.get("/chief-trainer-feedback/{session_id}")
async def get_chief_trainer_feedback(session_id: str, current_user: User = Depends(get_current_user)):
    """Get chief trainer feedback for a session"""
    feedback = await db.chief_trainer_feedback.find_one({"session_id": session_id}, {"_id": 0})
    if not feedback:
        return None
    return feedback

# Certificate Routes
@api_router.get("/certificates/participant/{participant_id}", response_model=List[Certificate])
async def get_participant_certificates(participant_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role == "participant" and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    certificates = await db.certificates.find({"participant_id": participant_id}, {"_id": 0}).to_list(100)
    for cert in certificates:
        if isinstance(cert.get('issue_date'), str):
            cert['issue_date'] = datetime.fromisoformat(cert['issue_date'])
    return certificates

@api_router.get("/certificates/my-certificates", response_model=List[Certificate])
async def get_my_certificates(current_user: User = Depends(get_current_user)):
    """Get certificates for the current logged-in user (participant)"""
    if current_user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participants can access this endpoint")
    
    certificates = await db.certificates.find({"participant_id": current_user.id}, {"_id": 0}).to_list(100)
    for cert in certificates:
        if isinstance(cert.get('issue_date'), str):
            cert['issue_date'] = datetime.fromisoformat(cert['issue_date'])
    return certificates


# Settings Routes
@api_router.get("/settings", response_model=Settings)
async def get_settings():
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

@api_router.post("/settings/upload-logo")
async def upload_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
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

@api_router.put("/settings", response_model=Settings)
async def update_settings(settings_data: SettingsUpdate, current_user: User = Depends(get_current_user)):
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

# Certificate Template Upload
@api_router.post("/settings/upload-certificate-template")
async def upload_certificate_template(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
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

# Indemnity Sections Management
@api_router.get("/settings/indemnity-sections")
async def get_indemnity_sections():
    """Get custom indemnity sections (public - for participant form)"""
    sections = await db.indemnity_sections.find({}, {"_id": 0}).sort("order", 1).to_list(None)
    return sections

@api_router.post("/settings/indemnity-sections")
async def save_indemnity_sections(sections: List[dict], current_user: User = Depends(get_current_user)):
    """Save custom indemnity sections (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can manage indemnity sections")
    
    # Clear existing and insert new
    await db.indemnity_sections.delete_many({})
    
    for idx, section in enumerate(sections):
        section["order"] = idx
        section["updated_at"] = get_malaysia_time().isoformat()
        await db.indemnity_sections.insert_one(section)
    
    return {"message": f"Saved {len(sections)} indemnity sections"}

# Feedback Questions Management (Admin)
@api_router.get("/settings/feedback-questions")
async def get_feedback_questions():
    """Get participant feedback questions (public - for participant form)"""
    questions = await db.feedback_questions.find({}, {"_id": 0}).sort("order", 1).to_list(None)
    if not questions:
        # Return default Bahasa Malaysia questions
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

@api_router.post("/settings/feedback-questions")
async def save_feedback_questions(questions: List[dict], current_user: User = Depends(get_current_user)):
    """Save feedback questions (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can manage feedback questions")
    
    # Clear existing and insert new
    await db.feedback_questions.delete_many({})
    
    for idx, question in enumerate(questions):
        question["order"] = idx + 1
        question["updated_at"] = get_malaysia_time().isoformat()
        if "id" not in question or not question["id"]:
            question["id"] = f"Q{idx+1}"
        await db.feedback_questions.insert_one(question)
    
    return {"message": f"Saved {len(questions)} feedback questions"}

# Excel Export for Session Feedback Report
@api_router.get("/sessions/{session_id}/export-feedback-excel")
async def export_session_feedback_excel(session_id: str, current_user: User = Depends(get_current_user)):
    """Export session feedback data as Excel file"""
    if current_user.role not in ["admin", "coordinator", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can export feedback")
    
    # Get session details
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get participants
    participants = await db.participants.find({"session_id": session_id}, {"_id": 0}).to_list(None)
    
    # Get feedback questions
    questions = await db.feedback_questions.find({}, {"_id": 0}).sort("order", 1).to_list(None)
    if not questions:
        # Use default questions
        questions = [
            {"id": "A1", "category": "KUALITI KURSUS", "question": "Penganjur menepati jangkaan saya", "type": "rating"},
            {"id": "A2", "category": "KUALITI KURSUS", "question": "Kandungan kursus adalah jelas dan mudah difahami", "type": "rating"},
            {"id": "A3", "category": "KUALITI KURSUS", "question": "Hasil pembelajaran adalah selari dengan objektif dan penyampaian kursus", "type": "rating"},
            {"id": "A4", "category": "KUALITI KURSUS", "question": "Bahan pembelajaran sangat jelas, tepat, sangat mencukupi dan membantu", "type": "rating"},
            {"id": "A5", "category": "KUALITI KURSUS", "question": "Tempoh kursus adalah mencukupi", "type": "rating"},
            {"id": "A6", "category": "KUALITI KURSUS", "question": "Keseluruhannya, saya berpuas hati dengan kandungan kursus", "type": "rating"},
            {"id": "A7", "category": "KUALITI KURSUS", "question": "Cadangan mengenai KUALITI KURSUS", "type": "text"},
            {"id": "B1", "category": "PENYEDIA LATIHAN", "question": "Latihan telah disusun dan dilaksanakan dengan baik", "type": "rating"},
            {"id": "B2", "category": "PENYEDIA LATIHAN", "question": "Persekitaran kelas kondusif", "type": "rating"},
            {"id": "B3", "category": "PENYEDIA LATIHAN", "question": "Yakin mengaplikasikan kemahiran", "type": "rating"},
            {"id": "B4", "category": "PENYEDIA LATIHAN", "question": "Berpuas hati dengan penganjur", "type": "rating"},
            {"id": "B5", "category": "PENYEDIA LATIHAN", "question": "Cadangan mengenai PENYEDIA LATIHAN", "type": "text"},
            {"id": "C1", "category": "TRAINER", "question": "Trainer menarik minat peserta", "type": "rating"},
            {"id": "C2", "category": "TRAINER", "question": "Trainer mempunyai pemahaman mendalam", "type": "rating"},
            {"id": "C3", "category": "TRAINER", "question": "Trainer mempunyai ilmu terkini", "type": "rating"},
            {"id": "C4", "category": "TRAINER", "question": "Trainer menggunakan teknologi", "type": "rating"},
            {"id": "C5", "category": "TRAINER", "question": "Berpuas hati dengan trainer", "type": "rating"},
            {"id": "C6", "category": "TRAINER", "question": "Cadangan mengenai TRAINER", "type": "text"},
            {"id": "D1", "category": "UMUM", "question": "Pandangan untuk memperbaiki perkhidmatan", "type": "text"},
        ]
    
    # Get feedback submissions
    feedbacks = await db.course_feedback.find({"session_id": session_id}, {"_id": 0}).to_list(None)
    feedback_by_participant = {f.get('participant_id'): f for f in feedbacks}
    
    # Get test results
    test_results = await db.test_results.find({"session_id": session_id}, {"_id": 0}).to_list(None)
    pre_tests = {r['participant_id']: r for r in test_results if r.get('test_type') == 'pre'}
    post_tests = {r['participant_id']: r for r in test_results if r.get('test_type') == 'post'}
    
    # Get attendance
    attendance_records = await db.attendance.find({"session_id": session_id}, {"_id": 0}).to_list(None)
    
    # Create Excel workbook
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    wb = Workbook()
    
    # Sheet 1: Session Info
    ws_info = wb.active
    ws_info.title = "Session Info"
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    info_data = [
        ["FEEDBACK REPORT"],
        [""],
        ["Company", session.get("company_name", "N/A")],
        ["Program", session.get("program_name", "N/A")],
        ["Trainer", session.get("trainer_name", "N/A")],
        ["Coordinator", session.get("coordinator_name", "N/A")],
        ["Venue", session.get("venue_name", "N/A")],
        ["Start Date", session.get("start_date", "N/A")],
        ["End Date", session.get("end_date", "N/A")],
        ["Total Participants", len(participants)],
    ]
    for row in info_data:
        ws_info.append(row)
    ws_info['A1'].font = Font(bold=True, size=16)
    
    # Sheet 2: Participants & Test Results
    ws_participants = wb.create_sheet("Participants")
    participant_headers = ["No", "Nama Peserta", "IC Number", "Email", "Pre-Test Score", "Pre-Test %", "Pre-Test Status", "Post-Test Score", "Post-Test %", "Post-Test Status", "Remark"]
    ws_participants.append(participant_headers)
    for cell in ws_participants[1]:
        cell.fill = header_fill
        cell.font = header_font
    
    for idx, p in enumerate(participants, 1):
        pre = pre_tests.get(p['id'], {})
        post = post_tests.get(p['id'], {})
        
        pre_score = f"{pre.get('correct_answers', 0)}/{pre.get('total_questions', 0)}" if pre else "N/A"
        pre_pct = round((pre.get('correct_answers', 0) / pre.get('total_questions', 1)) * 100) if pre and pre.get('total_questions') else 0
        pre_status = "Pass" if pre.get('passed') else "Fail" if pre else "N/A"
        
        post_score = f"{post.get('correct_answers', 0)}/{post.get('total_questions', 0)}" if post else "N/A"
        post_pct = round((post.get('correct_answers', 0) / post.get('total_questions', 1)) * 100) if post and post.get('total_questions') else 0
        post_status = "Pass" if post.get('passed') else "Fail" if post else "N/A"
        
        remark = "Improved (Pass)" if post.get('passed') and (post_pct > pre_pct or post.get('passed')) else "No Change" if pre.get('passed') == post.get('passed') else "Needs Improvement"
        
        ws_participants.append([
            idx,
            p.get('full_name', 'N/A'),
            p.get('ic_number', 'N/A'),
            p.get('email', 'N/A'),
            pre_score,
            f"{pre_pct}%",
            pre_status,
            post_score,
            f"{post_pct}%",
            post_status,
            remark
        ])
    
    # Sheet 3: Feedback Responses
    ws_feedback = wb.create_sheet("Feedback Responses")
    # Build headers: Participant Name + all questions
    rating_questions = [q for q in questions if q.get('type') == 'rating']
    text_questions = [q for q in questions if q.get('type') == 'text']
    
    fb_headers = ["No", "Nama Peserta"] + [f"{q['id']}: {q['question'][:50]}" for q in rating_questions] + [f"{q['id']}: {q['question'][:50]}" for q in text_questions]
    ws_feedback.append(fb_headers)
    for cell in ws_feedback[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True)
    
    for idx, p in enumerate(participants, 1):
        fb = feedback_by_participant.get(p['id'], {})
        responses = fb.get('responses', [])
        response_map = {r.get('question_id', r.get('question', '')): r.get('answer') for r in responses}
        
        row_data = [idx, p.get('full_name', 'N/A')]
        # Add rating responses
        for q in rating_questions:
            val = response_map.get(q['id'], response_map.get(q['question'], ''))
            row_data.append(val if val else '')
        # Add text responses
        for q in text_questions:
            val = response_map.get(q['id'], response_map.get(q['question'], ''))
            row_data.append(val if val else '')
        
        ws_feedback.append(row_data)
    
    # Sheet 4: Summary Statistics
    ws_summary = wb.create_sheet("Summary")
    ws_summary.append(["FEEDBACK SUMMARY"])
    ws_summary['A1'].font = Font(bold=True, size=14)
    ws_summary.append([])
    
    # Calculate averages for rating questions
    ws_summary.append(["Question ID", "Category", "Question", "Average Score", "Response Count"])
    for cell in ws_summary[3]:
        cell.fill = header_fill
        cell.font = header_font
    
    for q in rating_questions:
        scores = []
        for fb in feedbacks:
            for r in fb.get('responses', []):
                if r.get('question_id') == q['id'] or r.get('question') == q['question']:
                    if isinstance(r.get('answer'), (int, float)):
                        scores.append(r['answer'])
        avg = round(sum(scores) / len(scores), 2) if scores else 0
        ws_summary.append([q['id'], q.get('category', ''), q['question'][:60], avg, len(scores)])
    
    # Adjust column widths
    for ws in wb.worksheets:
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to bytes
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    # Generate filename
    company_short = (session.get("company_name", "Session") or "Session").replace(" ", "_")[:20]
    date_str = session.get("start_date", "")[:10].replace("-", "") if session.get("start_date") else ""
    filename = f"FEEDBACK_REPORT_{company_short}_{date_str}.xlsx"
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Upload Certificate for Participant
@api_router.post("/certificates/upload/{session_id}/{participant_id}")
async def upload_participant_certificate(
    session_id: str, 
    participant_id: str,
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user)
):
    """Upload certificate PDF for a specific participant in a session."""
    # Only coordinators assigned to the session or admins can upload
    if current_user.role == "coordinator":
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.get("coordinator_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only upload certificates for your assigned sessions")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only coordinators and admins can upload certificates")
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Get max file size from settings
    settings = await db.settings.find_one({"id": "app_settings"}, {"_id": 0})
    max_size_mb = settings.get('max_certificate_file_size_mb', 5) if settings else 5
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=400, 
            detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
        )
    
    # Create unique filename
    file_extension = ".pdf"
    unique_filename = f"{session_id}_{participant_id}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = CERTIFICATE_PDF_DIR / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    certificate_url = f"/api/static/certificates_pdf/{unique_filename}"
    
    # Update participant access record with certificate info
    await db.participant_access.update_one(
        {"participant_id": participant_id, "session_id": session_id},
        {
            "$set": {
                "certificate_url": certificate_url,
                "certificate_uploaded_at": get_malaysia_time().isoformat(),
                "certificate_uploaded_by": current_user.id
            }
        },
        upsert=True
    )
    
    return {
        "certificate_url": certificate_url,
        "message": "Certificate uploaded successfully",
        "file_size_mb": round(file_size / (1024 * 1024), 2)
    }



@api_router.get("/certificates/session/{session_id}")
async def get_session_certificates(session_id: str, current_user: User = Depends(get_current_user)):
    """Get all certificates for a session (from participant_access)"""
    if current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Only admins and coordinators can access certificates")
    
    # Get all participant access records for this session that have certificates
    access_records = await db.participant_access.find(
        {
            "session_id": session_id,
            "certificate_url": {"$exists": True, "$ne": None}
        },
        {"_id": 0}
    ).to_list(1000)
    
    # Format for frontend
    certificates = []
    for access in access_records:
        if access.get('certificate_url'):
            certificates.append({
                "participant_id": access.get('participant_id'),
                "file_path": access.get('certificate_url'),  # Use file_path for compatibility
                "certificate_url": access.get('certificate_url'),
                "uploaded_at": access.get('certificate_uploaded_at'),
                "uploaded_by": access.get('certificate_uploaded_by')
            })
    
    return certificates

# Download Certificate for Participant
@api_router.get("/certificates/download/{session_id}/{participant_id}")
async def download_participant_certificate(
    session_id: str, 
    participant_id: str, 
    current_user: User = Depends(get_current_user)
):
    """Download certificate for a participant. Only accessible if participant has submitted feedback and clocked out."""
    
    # Check if user is the participant or admin/coordinator
    if current_user.id != participant_id and current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if session is active (participants can only access if session is active)
    if current_user.id == participant_id and session.get("status") != "active":
        raise HTTPException(status_code=403, detail="Certificate access is not available. Session is not active.")
    
    # Get participant access
    access = await db.participant_access.find_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"_id": 0}
    )
    
    if not access:
        raise HTTPException(status_code=404, detail="No certificate found")
    
    # Check if certificate exists
    certificate_url = access.get('certificate_url')
    if not certificate_url:
        raise HTTPException(status_code=404, detail="No certificate uploaded for this participant")
    
    # For participants, check eligibility (feedback + clock out)
    if current_user.id == participant_id:
        # Check feedback submission (check both fields for backward compatibility)
        feedback_done = access.get('feedback_submitted', False) or access.get('feedback_completed', False)
        if not feedback_done:
            raise HTTPException(
                status_code=403, 
                detail="Certificate not available. Please submit your feedback first."
            )
        
        # Check if clocked out
        attendance = await db.attendance.find_one(
            {
                "participant_id": participant_id,
                "session_id": session_id,
                "clock_out": {"$ne": None}
            },
            {"_id": 0}
        )
        
        if not attendance:
            raise HTTPException(
                status_code=403,
                detail="Certificate not available. Please clock out first."
            )
    
    # Get file path
    filename = certificate_url.split('/')[-1]
    file_path = CERTIFICATE_PDF_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found")
    
    # Get participant name for filename
    participant = await db.users.find_one({"id": participant_id}, {"_id": 0})
    participant_name = participant.get('full_name', 'participant').replace(' ', '_') if participant else 'participant'
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"{participant_name}_certificate.pdf"
    )

# Check Certificate Eligibility
@api_router.get("/certificates/eligibility/{session_id}/{participant_id}")
async def check_certificate_eligibility(
    session_id: str,
    participant_id: str,
    current_user: User = Depends(get_current_user)
):
    """Check if participant is eligible to view certificate."""
    
    # Only the participant themselves or admin/coordinator can check
    if current_user.id != participant_id and current_user.role not in ["admin", "coordinator"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get participant access
    access = await db.participant_access.find_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"_id": 0}
    )
    
    # Check conditions
    has_certificate = bool(access and access.get('certificate_url'))
    feedback_submitted = bool(access and access.get('feedback_submitted', False))
    
    # Check clock out
    attendance = await db.attendance.find_one(
        {
            "participant_id": participant_id,
            "session_id": session_id,
            "clock_out": {"$ne": None}
        },
        {"_id": 0}
    )
    clocked_out = bool(attendance)
    
    session_active = session.get("status") == "active"
    
    eligible = has_certificate and feedback_submitted and clocked_out and session_active
    
    return {
        "eligible": eligible,
        "has_certificate": has_certificate,
        "feedback_submitted": feedback_submitted,
        "clocked_out": clocked_out,
        "session_active": session_active,
        "certificate_url": access.get('certificate_url') if access else None,
        "message": "Eligible to download certificate" if eligible else "Not yet eligible for certificate"
    }


# Get All Certificates (Admin Only)
@api_router.get("/certificates/repository")
async def get_certificates_repository(current_user: User = Depends(get_current_user)):
    """Get all uploaded certificates for admin repository."""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access certificate repository")
    
    # Get all participant access records that have certificates
    certificates = await db.participant_access.find(
        {"certificate_url": {"$exists": True, "$ne": None}},
        {"_id": 0}
    ).to_list(length=None)
    
    # Enrich with participant, session, and program details
    enriched_certificates = []
    
    for cert in certificates:
        participant_id = cert.get('participant_id')
        session_id = cert.get('session_id')
        
        # Get participant details
        participant = await db.users.find_one({"id": participant_id}, {"_id": 0})
        
        # Get session details
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
        
        # Get program details if session has program_id
        program = None
        if session and session.get('program_id'):
            program = await db.programs.find_one({"id": session['program_id']}, {"_id": 0})
        
        # Get company details if session has company_id
        company = None
        if session and session.get('company_id'):
            company = await db.companies.find_one({"id": session['company_id']}, {"_id": 0})
        
        enriched_certificates.append({
            "certificate_url": cert.get('certificate_url'),
            "uploaded_at": cert.get('certificate_uploaded_at'),
            "uploaded_by": cert.get('certificate_uploaded_by'),
            "participant_id": participant_id,
            "participant_name": participant.get('full_name') if participant else 'Unknown',
            "participant_id_number": participant.get('id_number') if participant else 'N/A',
            "participant_email": participant.get('email') if participant else 'N/A',
            "session_id": session_id,
            "session_name": session.get('name') if session else 'Unknown Session',
            "session_start_date": session.get('start_date') if session else None,
            "session_end_date": session.get('end_date') if session else None,
            "program_name": program.get('name') if program else 'N/A',
            "company_name": company.get('name') if company else 'N/A',
            "feedback_submitted": cert.get('feedback_submitted', False),
        })
    
    # Sort by upload date (most recent first)
    enriched_certificates.sort(key=lambda x: x.get('uploaded_at') or '', reverse=True)
    
    return enriched_certificates


# Generate Certificate
@api_router.post("/certificates/generate/{session_id}/{participant_id}")
async def generate_certificate(session_id: str, participant_id: str, current_user: User = Depends(get_current_user)):
    # Only admin can generate, or participant can generate their own
    if current_user.role != "admin" and current_user.id != participant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Check if feedback is submitted (required for certificate)
    access = await db.participant_access.find_one(
        {"participant_id": participant_id, "session_id": session_id},
        {"_id": 0}
    )
    
    if not access:
        # Auto-create if doesn't exist
        access = await get_or_create_participant_access(participant_id, session_id)
    
    if not access.get('feedback_submitted', False):
        raise HTTPException(status_code=400, detail="Please submit feedback first. Go to your dashboard and click 'Submit Feedback' button.")
    
    # Get participant details
    participant = await db.users.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get session details
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get program details
    program = await db.programs.find_one({"id": session['program_id']}, {"_id": 0})
    program_name = program['name'] if program else "Training Program"
    
    # Get company details
    company = await db.companies.find_one({"id": session['company_id']}, {"_id": 0})
    company_name = company['name'] if company else ""
    
    # Get settings for company name (already in template, no replacement needed)
    
    # Load template
    template_path = TEMPLATE_DIR / "certificate_template.docx"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Certificate template not found. Please upload a template first.")
    
    # Create document from template
    doc = Document(template_path)
    
    # Replace placeholders in paragraphs
    replacements = {
        '«PARTICIPANT_NAME»': participant['full_name'],
        '«IC_NUMBER»': participant['id_number'],
        '«COMPANY_NAME»': company_name,
        '«PROGRAMME NAME»': program_name,
        '<<PROGRAMME NAME>>': program_name,
        '«VENUE»': session['location'],
        '«DATE»': session['end_date']
    }
    
    # Replace in paragraphs
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value)
    
    # Replace in tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in replacements.items():
                    if key in cell.text:
                        cell.text = cell.text.replace(key, value)
    
    # Save as new DOCX document
    cert_filename = f"certificate_{participant_id}_{session_id}.docx"
    cert_path = CERTIFICATE_DIR / cert_filename
    doc.save(cert_path)
    
    # Convert to PDF
    pdf_filename = f"certificate_{participant_id}_{session_id}.pdf"
    pdf_path = CERTIFICATE_PDF_DIR / pdf_filename
    
    # Convert and verify
    conversion_success = convert_docx_to_pdf(cert_path, pdf_path)
    if not conversion_success or not pdf_path.exists():
        raise HTTPException(status_code=500, detail="Failed to convert certificate to PDF. Please contact support.")
    
    # Store certificate record (using PDF URL)
    cert_url = f"/api/static/certificates_pdf/{pdf_filename}"
    
    # Check if certificate already exists
    existing_cert = await db.certificates.find_one({
        "participant_id": participant_id,
        "session_id": session_id
    }, {"_id": 0})
    
    if existing_cert:
        # Update existing
        await db.certificates.update_one(
            {"id": existing_cert['id']},
            {"$set": {
                "certificate_url": cert_url,
                "issue_date": get_malaysia_time().isoformat()
            }}
        )
        cert_id = existing_cert['id']
    else:
        # Create new
        cert_obj = Certificate(
            participant_id=participant_id,
            session_id=session_id,
            program_name=program_name,
            certificate_url=cert_url
        )
        doc_cert = cert_obj.model_dump()
        doc_cert['issue_date'] = doc_cert['issue_date'].isoformat()
        await db.certificates.insert_one(doc_cert)
        cert_id = cert_obj.id
    
    return {
        "certificate_id": cert_id,
        "certificate_url": cert_url,
        "download_url": f"/api/certificates/download/{cert_id}",
        "message": "Certificate generated successfully"
    }

@api_router.get("/certificates/download/{certificate_id}")
async def download_certificate(certificate_id: str, current_user: User = Depends(get_current_user)):
    cert = await db.certificates.find_one({"id": certificate_id}, {"_id": 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Only participant or admin can download
    if current_user.role != "admin" and current_user.id != cert['participant_id']:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    cert_url = cert['certificate_url']
    filename = cert_url.split('/')[-1]
    
    # Check if it's a PDF or DOCX
    if filename.endswith('.pdf'):
        file_path = CERTIFICATE_PDF_DIR / filename
        media_type = 'application/pdf'
    else:
        file_path = CERTIFICATE_DIR / filename
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found")
    
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/certificates/preview/{certificate_id}")
async def preview_certificate(certificate_id: str, current_user: User = Depends(get_current_user)):
    cert = await db.certificates.find_one({"id": certificate_id}, {"_id": 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    # Only participant or admin can preview
    if current_user.role != "admin" and current_user.id != cert['participant_id']:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    cert_url = cert['certificate_url']
    filename = cert_url.split('/')[-1]
    
    # Check if it's a PDF or DOCX
    if filename.endswith('.pdf'):
        file_path = CERTIFICATE_PDF_DIR / filename
        media_type = 'application/pdf'
    else:
        file_path = CERTIFICATE_DIR / filename
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found")
    
    # Return PDF with inline disposition for browser preview
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

# Static files
@api_router.get("/static/logos/{filename}")
async def get_logo(filename: str):
    file_path = LOGO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(file_path)

@api_router.get("/static/certificates/{filename}")
async def get_certificate(filename: str):
    file_path = CERTIFICATE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate not found")
    return FileResponse(file_path)

@api_router.get("/static/certificates_pdf/{filename}")
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

@api_router.get("/static/templates/{filename}")
async def get_template(filename: str):
    file_path = TEMPLATE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return FileResponse(file_path)

@api_router.post("/checklist-photos/upload")
async def upload_checklist_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can upload checklist photos")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1]
    filename = f"{str(uuid.uuid4())}.{file_extension}"
    file_path = CHECKLIST_PHOTOS_DIR / filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    photo_url = f"/api/static/checklist-photos/{filename}"
    return {"photo_url": photo_url}

@api_router.get("/static/checklist-photos/{filename}")
async def get_checklist_photo(filename: str):
    file_path = CHECKLIST_PHOTOS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(file_path)

# ============ AI REPORT GENERATION ============

async def generate_training_report_content(session_id: str, program_id: str, company_id: str) -> str:
    """Generate comprehensive training report using AI"""
    
    # Gather all data
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    program = await db.programs.find_one({"id": program_id}, {"_id": 0})
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    
    # Get all participants
    participant_ids = session.get('participant_ids', [])
    participants = []
    for pid in participant_ids:
        user = await db.users.find_one({"id": pid}, {"_id": 0})
        if user:
            participants.append(user)
    
    # Get pre-test results
    pre_tests = await db.test_results.find({
        "session_id": session_id,
        "test_type": "pre"
    }, {"_id": 0}).to_list(100)
    
    # Get post-test results
    post_tests = await db.test_results.find({
        "session_id": session_id,
        "test_type": "post"
    }, {"_id": 0}).to_list(100)
    
    # Get checklists
    checklists = await db.vehicle_checklists.find({
        "session_id": session_id
    }, {"_id": 0}).to_list(100)
    
    # Get feedback
    feedbacks = await db.course_feedback.find({
        "session_id": session_id
    }, {"_id": 0}).to_list(100)
    
    # Get attendance
    attendance = await db.attendance_records.find({
        "session_id": session_id
    }, {"_id": 0}).to_list(100)
    
    # Create participant ID to name mapping
    participant_map = {p.get('id'): p.get('full_name') for p in participants}
    
    # Build comprehensive data structure
    training_data = {
        "session": {
            "name": session.get('name'),
            "location": session.get('location'),
            "start_date": str(session.get('start_date')),
            "end_date": str(session.get('end_date'))
        },
        "program": {
            "name": program.get('name'),
            "description": program.get('description', '')
        },
        "company": {
            "name": company.get('name')
        },
        "participants": {
            "total": len(participants),
            "names": [p.get('full_name') for p in participants],
            "id_map": participant_map
        },
        "pre_test_results": {
            "total_participants": len(pre_tests),
            "average_score": sum([t.get('score', 0) for t in pre_tests]) / len(pre_tests) if pre_tests else 0,
            "pass_rate": sum([1 for t in pre_tests if t.get('passed', False)]) / len(pre_tests) * 100 if pre_tests else 0,
            "details": [{"participant": t.get('participant_id'), "score": t.get('score'), "passed": t.get('passed')} for t in pre_tests]
        },
        "post_test_results": {
            "total_participants": len(post_tests),
            "average_score": sum([t.get('score', 0) for t in post_tests]) / len(post_tests) if post_tests else 0,
            "pass_rate": sum([1 for t in post_tests if t.get('passed', False)]) / len(post_tests) * 100 if post_tests else 0,
            "improvement": (sum([t.get('score', 0) for t in post_tests]) / len(post_tests) if post_tests else 0) - (sum([t.get('score', 0) for t in pre_tests]) / len(pre_tests) if pre_tests else 0),
            "details": [{"participant": t.get('participant_id'), "score": t.get('score'), "passed": t.get('passed')} for t in post_tests]
        },
        "checklist_summary": {
            "total_checklists": len(checklists),
            "items_needing_repair": sum([len([item for item in c.get('checklist_items', []) if item.get('status') == 'needs_repair']) for c in checklists]),
            "common_issues": [],
            "details": [{"participant": c.get('participant_id'), "items": c.get('checklist_items', [])} for c in checklists]
        },
        "feedback_summary": {
            "total_responses": len(feedbacks),
            "average_ratings": {},
            "comments": [f.get('responses', {}) for f in feedbacks]
        },
        "attendance": {
            "total_records": len(attendance),
            "attendance_rate": len([a for a in attendance if a.get('clock_out_time')]) / len(attendance) * 100 if attendance else 100
        }
    }
    
    # Create prompt for AI report generation
    prompt = f"""Generate a comprehensive Defensive Driving/Riding Training Report based on the following data:

TRAINING DETAILS:
- Program: {training_data['program']['name']}
- Company: {training_data['company']['name']}
- Session: {training_data['session']['name']}
- Location: {training_data['session']['location']}
- Dates: {training_data['session']['start_date']} to {training_data['session']['end_date']}
- Total Participants: {training_data['participants']['total']}

PRE-TEST RESULTS:
- Participants Tested: {training_data['pre_test_results']['total_participants']}
- Average Score: {training_data['pre_test_results']['average_score']:.1f}%
- Pass Rate: {training_data['pre_test_results']['pass_rate']:.1f}%

POST-TEST RESULTS:
- Participants Tested: {training_data['post_test_results']['total_participants']}
- Average Score: {training_data['post_test_results']['average_score']:.1f}%
- Pass Rate: {training_data['post_test_results']['pass_rate']:.1f}%
- Improvement: {training_data['post_test_results']['improvement']:.1f}%

VEHICLE CHECKLIST FINDINGS:
- Total Checklists Completed: {training_data['checklist_summary']['total_checklists']}
- Items Needing Repair: {training_data['checklist_summary']['items_needing_repair']}

DETAILED CHECKLIST ISSUES (items marked as 'needs_repair'):
{chr(10).join([
    f"- {training_data['participants']['id_map'].get(detail['participant'], 'Unknown participant')}: " + 
    ", ".join([
        f"Item: '{item.get('item', 'Unknown item')}' | Issue: '{item.get('comments', 'No comment')}'" 
        for item in detail['items'] 
        if item.get('status') == 'needs_repair'
    ])
    for detail in training_data['checklist_summary']['details']
    if any(item.get('status') == 'needs_repair' for item in detail['items'])
]) if training_data['checklist_summary']['items_needing_repair'] > 0 else '- No items needing repair'}

FEEDBACK:
- Total Responses: {training_data['feedback_summary']['total_responses']}

ATTENDANCE:
- Attendance Rate: {training_data['attendance']['attendance_rate']:.1f}%

Generate a professional training report with the following sections:
1. Executive Summary (2-3 paragraphs)
2. Training Overview (objectives, dates, location, participants)
3. Pre-Training Assessment (detailed analysis of pre-test results)
4. Post-Training Assessment (detailed analysis of post-test results, comparison with pre-test)
5. Vehicle Inspection Findings - READ CAREFULLY: Format each issue EXACTLY as "   - **[ITEM_CATEGORY]** - [TRAINER_COMMENT]" where:
   * ITEM_CATEGORY = The vehicle part name ONLY (Helmet, Side mirror, Safety vest, Brake, Tire, Lights, etc.)
   * TRAINER_COMMENT = The full comment from the trainer describing the issue
   * You MUST extract the item category intelligently from the 'Item' field even if it contains the full description
   * Examples:
     - If Item='No sirim helmet', extract 'Helmet' as ITEM_CATEGORY
     - If Item='No side mirror', extract 'Side mirror' as ITEM_CATEGORY  
     - If Item='Worn out', you must infer from context (likely Brake or Tire)
   * Format: "   - **Helmet** - No sirim helmet"
   * Format: "   - **Side mirror** - No side mirror"
6. Participant Feedback (summary of feedback responses)
7. Key Observations and Recommendations
8. Conclusion

Use professional language, include data-driven insights, and provide actionable recommendations for the company.
Format using Markdown with proper headings and bullet points.

ABSOLUTE CRITICAL RULES FOR VEHICLE INSPECTION SECTION:
1. Each issue line MUST start with "   - **[ITEM_CATEGORY]** - [DESCRIPTION]"
2. ITEM_CATEGORY must be a clean vehicle part name extracted from the Item field:
   - "No sirim helmet" → Extract "Helmet"
   - "No side mirror" → Extract "Side mirror"
   - "No safety vest" → Extract "Safety vest"
   - "Missing" or "Need to change" → Infer from context what part it refers to
3. Use the 'Issue' field as the DESCRIPTION after the dash
4. NEVER write "undefined" or leave item unnamed
5. Be intelligent in extracting the core item name from any description"""

    # Call LLM for report generation
    try:
        api_key = os.getenv('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY not configured")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"report_gen_{uuid.uuid4().hex[:8]}",
            system_message="You are a professional training report writer specializing in defensive driving and road safety training programs."
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        return response
    except Exception as e:
        logging.error(f"Report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@api_router.post("/reports/generate")
async def generate_report(request: ReportGenerateRequest, current_user: User = Depends(get_current_user)):
    """Generate AI training report (Coordinator only)"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can generate reports")
    
    # Get session details
    session = await db.sessions.find_one({"id": request.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Generate report content
    content = await generate_training_report_content(
        request.session_id,
        session['program_id'],
        session['company_id']
    )
    
    # Save as draft
    report = TrainingReport(
        session_id=request.session_id,
        program_id=session['program_id'],
        company_id=session['company_id'],
        generated_by=current_user.id,
        content=content,
        status="draft"
    )
    
    await db.training_reports.insert_one(report.model_dump())
    
    return report

@api_router.get("/reports/session/{session_id}")
async def get_session_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Get report for session"""
    if current_user.role not in ["coordinator", "admin", "pic_supervisor"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    report = await db.training_reports.find_one({"session_id": session_id}, {"_id": 0})
    
    # If pic_supervisor, only return published reports
    if current_user.role == "pic_supervisor":
        if not report or report.get('status') != "published":
            raise HTTPException(status_code=404, detail="No published report found")
        if current_user.id not in report.get('published_to_supervisors', []):
            raise HTTPException(status_code=403, detail="Report not published to you")
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report

@api_router.put("/reports/{report_id}")
async def update_report(report_id: str, request: ReportUpdateRequest, current_user: User = Depends(get_current_user)):
    """Update report content (draft only)"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can edit reports")
    
    report = await db.training_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report['status'] == "published":
        raise HTTPException(status_code=400, detail="Cannot edit published report")
    
    await db.training_reports.update_one(
        {"id": report_id},
        {"$set": {"content": request.content}}
    )
    
    return {"message": "Report updated successfully"}

@api_router.post("/reports/{report_id}/publish")
async def publish_report(report_id: str, current_user: User = Depends(get_current_user)):
    """Publish report to supervisors"""
    if current_user.role not in ["coordinator", "admin"]:
        raise HTTPException(status_code=403, detail="Only coordinators can publish reports")
    
    report = await db.training_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get session to find supervisors
    session = await db.sessions.find_one({"id": report['session_id']}, {"_id": 0})
    supervisor_ids = session.get('supervisor_ids', [])
    
    await db.training_reports.update_one(
        {"id": report_id},
        {"$set": {
            "status": "published",
            "published_at": datetime.now(timezone.utc),
            "published_to_supervisors": supervisor_ids
        }}
    )
    
    return {"message": "Report published successfully", "published_to": supervisor_ids}

# ============ SUPERVISOR ENDPOINTS ============

@api_router.get("/supervisor/sessions")
async def get_supervisor_sessions(current_user: User = Depends(get_current_user)):
    """Get sessions for supervisor"""
    if current_user.role != "pic_supervisor":
        raise HTTPException(status_code=403, detail="Only supervisors can access this")
    
    # Find sessions where user is listed as supervisor
    sessions = await db.sessions.find({
        "supervisor_ids": current_user.id
    }, {"_id": 0}).to_list(100)
    
    return sessions

@api_router.get("/supervisor/attendance/{session_id}")
async def get_supervisor_session_attendance(session_id: str, current_user: User = Depends(get_current_user)):
    """Get attendance for session (Supervisor)"""
    if current_user.role != "pic_supervisor":
        raise HTTPException(status_code=403, detail="Only supervisors can access this")
    
    # Verify supervisor has access to this session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or current_user.id not in session.get('supervisor_ids', []):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get attendance records
    attendance = await db.attendance.find({
        "session_id": session_id
    }, {"_id": 0}).to_list(100)
    
    # Get participant details
    for record in attendance:
        participant = await db.users.find_one({"id": record['participant_id']}, {"_id": 0, "password": 0})
        if participant:
            record['participant_name'] = participant.get('full_name', 'Unknown')
            record['participant_email'] = participant.get('email', '')
        else:
            record['participant_name'] = f"Participant {record['participant_id']}"
            record['participant_email'] = ''
    
    return attendance

# ============ FINANCE PORTAL ROUTES ============

# Invoice number generation
async def generate_invoice_number():
    """Generate unique invoice number: INV/MDDRC/YYYY/MM/0001
    Resets sequence each month. Respects sequence overrides from admin."""
    now = get_malaysia_time()
    year = now.year
    month = now.month
    prefix = f"INV/MDDRC/{year}/{month:02d}/"
    
    # Check for sequence override
    sequence_override = await db.invoice_sequence_settings.find_one(
        {"year": year, "month": month},
        {"_id": 0}
    )
    
    last_invoice = await db.invoices.find_one(
        {"invoice_number": {"$regex": f"^INV/MDDRC/{year}/{month:02d}/"}},
        sort=[("invoice_number", -1)]
    )
    
    if sequence_override and sequence_override.get("next_sequence"):
        # Use the override sequence
        new_num = sequence_override["next_sequence"]
        # Clear the override after use
        await db.invoice_sequence_settings.delete_one({"year": year, "month": month})
    elif last_invoice:
        # Extract last number from invoice number like INV/MDDRC/2025/12/0001
        last_num = int(last_invoice["invoice_number"].split("/")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"{prefix}{new_num:04d}"

# Credit Note number generation
async def generate_credit_note_number():
    """Generate unique credit note number: CN/MDDRC/YYYY/MM/0001
    Resets sequence each month"""
    now = get_malaysia_time()
    year = now.year
    month = now.month
    prefix = f"CN/MDDRC/{year}/{month:02d}/"
    
    last_cn = await db.credit_notes.find_one(
        {"cn_number": {"$regex": f"^CN/MDDRC/{year}/{month:02d}/"}},
        sort=[("cn_number", -1)]
    )
    
    if last_cn:
        last_num = int(last_cn["cn_number"].split("/")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"{prefix}{new_num:04d}"

# Audit logging for finance
async def log_finance_action(entity_type: str, entity_id: str, action: str, 
                             changed_by: str, before_value: dict = None, 
                             after_value: dict = None, reason: str = None):
    log_entry = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "before_value": before_value,
        "after_value": after_value,
        "changed_by": changed_by,
        "reason": reason,
        "timestamp": get_malaysia_time().isoformat()
    }
    await db.finance_audit_log.insert_one(log_entry)

# Auto-create invoice when session is created
async def create_auto_invoice_for_session(session_data: dict, created_by: str, reuse_invoice_number: str = None):
    # Use reused invoice number if provided, otherwise generate new one
    if reuse_invoice_number:
        # Verify the number is available for reuse
        deleted_record = await db.deleted_invoice_numbers.find_one({
            "invoice_number": reuse_invoice_number,
            "is_available": True
        })
        if deleted_record:
            invoice_number = reuse_invoice_number
        else:
            # Number not available, generate new one
            invoice_number = await generate_invoice_number()
    else:
        invoice_number = await generate_invoice_number()
    
    company = await db.companies.find_one({"id": session_data.get("company_id")}, {"_id": 0})
    programme = await db.programs.find_one({"id": session_data.get("program_id")}, {"_id": 0})
    
    invoice = {
        "id": str(uuid.uuid4()),
        "invoice_number": invoice_number,
        "session_id": session_data.get("id"),
        "company_id": session_data.get("company_id"),
        "company_name": company.get("name") if company else None,
        "programme_name": programme.get("name") if programme else None,
        "training_dates": f"{session_data.get('start_date')} to {session_data.get('end_date')}",
        "venue": session_data.get("location"),
        "pax": len(session_data.get("participant_ids", [])),
        "line_items": [],
        "subtotal": 0.0,
        "tax_rate": 0.0,
        "tax_amount": 0.0,
        "total_amount": 0.0,
        "status": "auto_draft",
        "created_at": get_malaysia_time().isoformat(),
        "updated_at": get_malaysia_time().isoformat(),
        "version": 1
    }
    
    await db.invoices.insert_one(invoice)
    
    await log_finance_action(
        entity_type="invoice",
        entity_id=invoice["id"],
        action="created",
        changed_by=created_by,
        after_value=invoice
    )
    
    return invoice

# ============ FINANCE API ENDPOINTS ============

@api_router.get("/finance/invoices")
async def get_invoices(
    status: Optional[str] = None,
    company_id: Optional[str] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all invoices with optional year filter"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if status:
        query["status"] = status
    if company_id:
        query["company_id"] = company_id
    
    # Get all invoices first, then filter by year in Python for consistent date handling
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Filter by year if specified - handle both string and datetime formats
    if year:
        def get_invoice_year(inv):
            # First try invoice_date, then created_at
            date_val = inv.get("invoice_date") or inv.get("created_at")
            if not date_val:
                return None
            if isinstance(date_val, str):
                try:
                    return datetime.fromisoformat(date_val.replace('Z', '+00:00')).year
                except:
                    # Try parsing just the year from YYYY-MM-DD format
                    try:
                        return int(date_val[:4])
                    except:
                        return None
            elif hasattr(date_val, 'year'):
                return date_val.year
            return None
        
        invoices = [inv for inv in invoices if get_invoice_year(inv) == year]
    
    return invoices

# MUST be before /finance/invoices/{invoice_id} to avoid route conflict
@api_router.get("/finance/invoices/export")
async def export_invoices(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Export invoices data for Excel download"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if status:
        query["status"] = status
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", 1).to_list(10000)
    
    # Get all payments for payment status
    payments = await db.payments.find({}, {"_id": 0}).to_list(10000)
    payment_by_invoice = {p.get("invoice_id"): p for p in payments}
    
    # Get all credit notes
    credit_notes = await db.credit_notes.find({}, {"_id": 0}).to_list(10000)
    cn_by_invoice = {}
    for cn in credit_notes:
        inv_id = cn.get("invoice_id")
        if inv_id:
            if inv_id not in cn_by_invoice:
                cn_by_invoice[inv_id] = []
            cn_by_invoice[inv_id].append(cn)
    
    # Format for Excel export with user's requested headers
    export_data = []
    bil = 1
    for inv in invoices:
        # Get payment status
        payment = payment_by_invoice.get(inv.get("id"))
        payment_status = "Paid" if payment else "Unpaid"
        
        # Get credit notes
        inv_credit_notes = cn_by_invoice.get(inv.get("id"), [])
        cn_info = ""
        if inv_credit_notes:
            cn_parts = []
            for cn in inv_credit_notes:
                cn_parts.append(f"{cn.get('cn_number', 'CN')}: RM{cn.get('amount', 0)}")
            cn_info = "; ".join(cn_parts)
        
        export_data.append({
            "Bil": bil,
            "Date": str(inv.get("created_at", ""))[:10] if inv.get("created_at") else "",
            "Invoice Number": inv.get("invoice_number", ""),
            "Bill To": inv.get("bill_to_name") or inv.get("company_name", ""),
            "Programme": inv.get("programme_name", ""),
            "Company Name": inv.get("company_name", ""),
            "Venue": inv.get("venue", ""),
            "No of Participants": inv.get("pax", 0),
            "Invoice Value (RM)": inv.get("total_amount", 0),
            "Invoice Status": inv.get("status", "").replace("_", " ").title(),
            "Payment Status": payment_status,
            "Credit Note No & Value": cn_info
        })
        bil += 1
    
    return export_data

@api_router.get("/finance/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, current_user: User = Depends(get_current_user)):
    """Get single invoice"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice

@api_router.put("/finance/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    update_data: InvoiceUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update invoice (Finance only)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can update invoices")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") in ["issued", "paid"]:
        raise HTTPException(status_code=400, detail="Cannot modify issued/paid invoice")
    
    before_value = dict(invoice)
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = get_malaysia_time().isoformat()
    
    await db.invoices.update_one({"id": invoice_id}, {"$set": update_dict})
    
    if "status" in update_dict:
        await db.sessions.update_one(
            {"invoice_id": invoice_id},
            {"$set": {"invoice_status": update_dict["status"]}}
        )
    
    await log_finance_action("invoice", invoice_id, "updated", current_user.id, before_value, update_dict)
    
    return await db.invoices.find_one({"id": invoice_id}, {"_id": 0})

@api_router.post("/finance/invoices/{invoice_id}/approve")
async def approve_invoice(invoice_id: str, current_user: User = Depends(get_current_user)):
    """Approve invoice"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can approve invoices")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") not in ["auto_draft", "finance_review"]:
        raise HTTPException(status_code=400, detail="Invoice cannot be approved from current status")
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_at": get_malaysia_time().isoformat(),
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    await db.sessions.update_one({"invoice_id": invoice_id}, {"$set": {"invoice_status": "approved"}})
    await log_finance_action("invoice", invoice_id, "status_changed", current_user.id, 
                            {"status": invoice.get("status")}, {"status": "approved"})
    
    return {"message": "Invoice approved successfully"}

@api_router.post("/finance/invoices/{invoice_id}/issue")
async def issue_invoice(invoice_id: str, current_user: User = Depends(get_current_user)):
    """Issue invoice"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can issue invoices")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved invoices can be issued")
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "status": "issued",
            "issued_by": current_user.id,
            "issued_at": get_malaysia_time().isoformat(),
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    await db.sessions.update_one({"invoice_id": invoice_id}, {"$set": {"invoice_status": "issued"}})
    
    # Calculate marketing commission when invoice is issued
    session = await db.sessions.find_one({"invoice_id": invoice_id}, {"_id": 0})
    if session and session.get("marketing_user_id"):
        commission_amount = 0.0
        if session.get("commission_type") == "percentage":
            commission_amount = invoice.get("total_amount", 0) * (session.get("commission_rate", 0) / 100)
        else:
            commission_amount = session.get("commission_fixed_amount", 0)
        
        await db.marketing_commissions.update_one(
            {"session_id": session["id"]},
            {"$set": {
                "calculated_amount": commission_amount,
                "invoice_id": invoice_id,
                "status": "approved",
                "updated_at": get_malaysia_time().isoformat()
            }},
            upsert=True
        )
    
    await log_finance_action("invoice", invoice_id, "status_changed", current_user.id,
                            {"status": invoice.get("status")}, {"status": "issued"})
    
    return {"message": "Invoice issued successfully"}

@api_router.post("/finance/invoices/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: str, reason: str = "", current_user: User = Depends(get_current_user)):
    """Cancel invoice"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can cancel invoices")
    
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_by": current_user.id,
            "cancelled_at": get_malaysia_time().isoformat(),
            "cancellation_reason": reason,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    await db.sessions.update_one({"invoice_id": invoice_id}, {"$set": {"invoice_status": "cancelled"}})
    await log_finance_action("invoice", invoice_id, "status_changed", current_user.id,
                            {"status": invoice.get("status")}, {"status": "cancelled", "reason": reason}, reason)
    
    return {"message": "Invoice cancelled successfully"}

# ============= CREDIT NOTE ENDPOINTS =============

@api_router.get("/finance/credit-notes")
async def get_credit_notes(current_user: User = Depends(get_current_user)):
    """Get all credit notes"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    credit_notes = await db.credit_notes.find({}, {"_id": 0}).to_list(1000)
    return credit_notes

@api_router.post("/finance/credit-notes")
async def create_credit_note(cn_data: dict, current_user: User = Depends(get_current_user)):
    """Create a credit note (e.g., for HRDCorp 4% deduction)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    invoice_id = cn_data.get("invoice_id")
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0}) if invoice_id else None
    
    now = get_malaysia_time()
    cn_number = await generate_credit_note_number()
    
    credit_note = {
        "id": str(uuid.uuid4()),
        "cn_number": cn_number,
        "invoice_id": invoice_id,
        "invoice_number": invoice.get("invoice_number") if invoice else None,
        "session_id": cn_data.get("session_id"),
        "company_id": cn_data.get("company_id") or (invoice.get("company_id") if invoice else None),
        "company_name": cn_data.get("company_name") or (invoice.get("company_name") if invoice else None),
        "reason": cn_data.get("reason", "HRDCorp Levy Deduction"),
        "description": cn_data.get("description", "4% HRDCorp levy deducted from payment"),
        "amount": float(cn_data.get("amount", 0)),
        "percentage": float(cn_data.get("percentage", 4)),  # Default 4% for HRDCorp
        "status": "draft",
        "created_by": current_user.id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.insert_one(credit_note)
    await log_finance_action("credit_note", credit_note["id"], "created", current_user.id, after_value=credit_note)
    
    return {"message": "Credit note created", "cn_number": cn_number, "id": credit_note["id"]}

@api_router.get("/finance/credit-notes/{cn_id}")
async def get_credit_note(cn_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific credit note"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    return credit_note

@api_router.put("/finance/credit-notes/{cn_id}")
async def update_credit_note(cn_id: str, update_data: dict, current_user: User = Depends(get_current_user)):
    """Update a credit note"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can update credit notes")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") == "approved":
        raise HTTPException(status_code=400, detail="Cannot modify approved credit note")
    
    allowed_fields = ["reason", "description", "amount", "percentage", "status"]
    update_dict = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}
    update_dict["updated_at"] = get_malaysia_time().isoformat()
    
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    await log_finance_action("credit_note", cn_id, "updated", current_user.id, credit_note, update_dict)
    
    return await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})

@api_router.post("/finance/credit-notes/{cn_id}/approve")
async def approve_credit_note(cn_id: str, current_user: User = Depends(get_current_user)):
    """Approve a credit note"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can approve credit notes")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft credit notes can be approved")
    
    now = get_malaysia_time()
    update_dict = {
        "status": "approved",
        "approved_by": current_user.id,
        "approved_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    await log_finance_action("credit_note", cn_id, "approved", current_user.id, credit_note, update_dict)
    
    return {"message": "Credit note approved", "cn_number": credit_note.get("cn_number")}

@api_router.post("/finance/credit-notes/{cn_id}/issue")
async def issue_credit_note(cn_id: str, current_user: User = Depends(get_current_user)):
    """Issue a credit note (typically after payment received)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can issue credit notes")
    
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") not in ["draft", "approved"]:
        raise HTTPException(status_code=400, detail="Credit note must be draft or approved to be issued")
    
    now = get_malaysia_time()
    update_dict = {
        "status": "issued",
        "issued_by": current_user.id,
        "issued_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    await log_finance_action("credit_note", cn_id, "issued", current_user.id, credit_note, update_dict)
    
    return {"message": "Credit note issued", "cn_number": credit_note.get("cn_number")}

# Credit Note Management Endpoints (similar to Invoice Management)

class BackdateCreditNoteRequest(BaseModel):
    new_date: str  # YYYY-MM-DD format
    reason: str

class EditCreditNoteRequest(BaseModel):
    company_name: Optional[str] = None
    reason: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    percentage: Optional[float] = None
    edit_reason: str  # Mandatory reason for edit

@api_router.put("/finance/admin/credit-notes/{cn_id}/backdate")
async def backdate_credit_note(
    cn_id: str,
    request: BackdateCreditNoteRequest,
    current_user: User = Depends(get_current_user)
):
    """Backdate a credit note - Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can backdate credit notes")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the credit note
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    company_name = credit_note.get("company_name", "Unknown")
    amount = credit_note.get("amount", 0)
    record_ref = f"{credit_note.get('cn_number')} - {company_name} - RM {amount:,.2f}"
    
    # Get old date
    old_created_at = credit_note.get("created_at")
    if isinstance(old_created_at, datetime):
        old_date = old_created_at.strftime("%Y-%m-%d")
    elif isinstance(old_created_at, str):
        old_date = old_created_at[:10]
    else:
        old_date = "Unknown"
    
    # Parse new date
    try:
        new_datetime = datetime.strptime(request.new_date, "%Y-%m-%d")
        new_datetime = new_datetime.replace(tzinfo=MALAYSIA_TZ)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Credit Note Backdated",
        record_reference=record_ref,
        entity_type="credit_note",
        entity_id=cn_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="created_at",
        from_value=old_date,
        to_value=request.new_date
    )
    
    # Update the credit note date
    await db.credit_notes.update_one(
        {"id": cn_id},
        {"$set": {
            "created_at": new_datetime.isoformat(),
            "cn_date": request.new_date,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Credit note backdated successfully", "old_date": old_date, "new_date": request.new_date}

@api_router.put("/finance/admin/credit-notes/{cn_id}/edit")
async def edit_credit_note_admin(
    cn_id: str,
    request: EditCreditNoteRequest,
    current_user: User = Depends(get_current_user)
):
    """Edit credit note details - Admin/Finance only with audit trail"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can edit credit notes")
    
    if not request.edit_reason or len(request.edit_reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Edit reason is required (minimum 5 characters)")
    
    # Get the credit note
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    record_ref = f"{credit_note.get('cn_number')} - {credit_note.get('company_name', 'Unknown')}"
    
    # Build update dict and track changes
    update_dict = {"updated_at": get_malaysia_time().isoformat()}
    changes = []
    
    if request.company_name is not None and request.company_name != credit_note.get("company_name"):
        changes.append(("company_name", credit_note.get("company_name"), request.company_name))
        update_dict["company_name"] = request.company_name
    
    if request.reason is not None and request.reason != credit_note.get("reason"):
        changes.append(("reason", credit_note.get("reason"), request.reason))
        update_dict["reason"] = request.reason
    
    if request.description is not None and request.description != credit_note.get("description"):
        changes.append(("description", credit_note.get("description"), request.description))
        update_dict["description"] = request.description
    
    if request.amount is not None and request.amount != credit_note.get("amount"):
        changes.append(("amount", str(credit_note.get("amount")), str(request.amount)))
        update_dict["amount"] = request.amount
    
    if request.percentage is not None and request.percentage != credit_note.get("percentage"):
        changes.append(("percentage", str(credit_note.get("percentage")), str(request.percentage)))
        update_dict["percentage"] = request.percentage
    
    if not changes:
        return {"message": "No changes detected"}
    
    # Create audit trail entries for each change
    for field, from_val, to_val in changes:
        await create_audit_trail_entry(
            action="Credit Note Edited",
            record_reference=record_ref,
            entity_type="credit_note",
            entity_id=cn_id,
            changed_by=current_user,
            reason=request.edit_reason,
            field_changed=field,
            from_value=str(from_val) if from_val else "",
            to_value=str(to_val) if to_val else ""
        )
    
    # Update the credit note
    await db.credit_notes.update_one({"id": cn_id}, {"$set": update_dict})
    
    return {"message": "Credit note updated successfully", "changes": len(changes)}

@api_router.put("/finance/admin/credit-notes/{cn_id}/void")
async def void_credit_note(
    cn_id: str,
    reason: str = "",
    current_user: User = Depends(get_current_user)
):
    """Void a credit note - Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can void credit notes")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the credit note
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    if credit_note.get("status") == "voided":
        raise HTTPException(status_code=400, detail="Credit note is already voided")
    
    record_ref = f"{credit_note.get('cn_number')} - {credit_note.get('company_name', 'Unknown')}"
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Credit Note Voided",
        record_reference=record_ref,
        entity_type="credit_note",
        entity_id=cn_id,
        changed_by=current_user,
        reason=reason,
        field_changed="status",
        from_value=credit_note.get("status"),
        to_value="voided"
    )
    
    # Update the credit note status
    await db.credit_notes.update_one(
        {"id": cn_id},
        {"$set": {
            "status": "voided",
            "voided_by": current_user.id,
            "voided_at": get_malaysia_time().isoformat(),
            "void_reason": reason,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Credit note voided successfully"}

@api_router.put("/finance/admin/credit-notes/{cn_id}/number")
async def edit_credit_note_number(
    cn_id: str,
    year: int,
    month: int,
    sequence: int,
    reason: str = "",
    current_user: User = Depends(get_current_user)
):
    """Edit credit note number - Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can edit credit note numbers")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the credit note
    credit_note = await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})
    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")
    
    old_number = credit_note.get("cn_number")
    new_number = f"CN/MDDRC/{year}/{str(month).zfill(2)}/{str(sequence).zfill(4)}"
    
    # Check if new number already exists
    existing = await db.credit_notes.find_one({"cn_number": new_number, "id": {"$ne": cn_id}}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail=f"Credit note number {new_number} already exists")
    
    record_ref = f"{old_number} → {new_number}"
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Credit Note Number Changed",
        record_reference=record_ref,
        entity_type="credit_note",
        entity_id=cn_id,
        changed_by=current_user,
        reason=reason,
        field_changed="cn_number",
        from_value=old_number,
        to_value=new_number
    )
    
    # Update the credit note number
    await db.credit_notes.update_one(
        {"id": cn_id},
        {"$set": {
            "cn_number": new_number,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Credit note number updated successfully", "old_number": old_number, "new_number": new_number}

@api_router.post("/finance/session/{session_id}/credit-note")
async def create_session_credit_note(session_id: str, cn_data: dict, current_user: User = Depends(get_current_user)):
    """Create a credit note for a session (typically for HRDCorp deduction)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get the session's invoice
    invoice = await db.invoices.find_one({"session_id": session_id}, {"_id": 0})
    
    # Get company info
    company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
    
    # Calculate CN amount
    percentage = float(cn_data.get("percentage", 4))  # Default 4% for HRDCorp
    base_amount = float(cn_data.get("base_amount", invoice.get("total_amount", 0) if invoice else 0))
    cn_amount = float(cn_data.get("amount", 0)) or (base_amount * percentage / 100)
    
    now = get_malaysia_time()
    cn_number = await generate_credit_note_number()
    
    credit_note = {
        "id": str(uuid.uuid4()),
        "cn_number": cn_number,
        "invoice_id": invoice.get("id") if invoice else None,
        "invoice_number": invoice.get("invoice_number") if invoice else None,
        "session_id": session_id,
        "session_name": session.get("name"),
        "company_id": session.get("company_id"),
        "company_name": company.get("name") if company else None,
        "reason": cn_data.get("reason", "HRDCorp Levy Deduction"),
        "description": cn_data.get("description", f"{percentage}% HRDCorp levy deducted from payment"),
        "base_amount": base_amount,
        "percentage": percentage,
        "amount": cn_amount,
        "status": "draft",
        "created_by": current_user.id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.credit_notes.insert_one(credit_note)
    await log_finance_action("credit_note", credit_note["id"], "created", current_user.id, after_value=credit_note)
    
    return {"message": "Credit note created", "cn_number": cn_number, "id": credit_note["id"], "amount": cn_amount}

@api_router.get("/finance/payments")
async def get_payments(current_user: User = Depends(get_current_user)):
    """Get all payments"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    payments = await db.payments.find({}, {"_id": 0}).sort("payment_date", -1).to_list(100)
    
    # Enrich with invoice info
    for payment in payments:
        if payment.get("invoice_id"):
            invoice = await db.invoices.find_one({"id": payment["invoice_id"]}, {"_id": 0, "invoice_number": 1, "company_name": 1})
            if invoice:
                payment["invoice_number"] = invoice.get("invoice_number")
                payment["company_name"] = invoice.get("company_name")
    
    return payments

@api_router.post("/finance/payments")
async def record_payment(payment_data: PaymentCreate, current_user: User = Depends(get_current_user)):
    """Record payment"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can record payments")
    
    invoice = await db.invoices.find_one({"id": payment_data.invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") not in ["issued", "paid", "partial"]:
        raise HTTPException(status_code=400, detail="Can only record payments for issued invoices")
    
    payment = {
        "id": str(uuid.uuid4()),
        "invoice_id": payment_data.invoice_id,
        "invoice_number": invoice.get("invoice_number"),
        "company_name": invoice.get("company_name"),
        "amount": payment_data.amount,
        "payment_date": payment_data.payment_date,
        "payment_method": payment_data.payment_method,
        "reference_number": payment_data.reference_number,
        "notes": payment_data.notes,
        "deduction_amount": payment_data.deduction_amount or 0,
        "recorded_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.payments.insert_one(payment)
    
    # Remove MongoDB _id if present (not JSON serializable)
    payment.pop("_id", None)
    
    # Create credit note if requested
    credit_note_created = None
    if payment_data.create_credit_note and (payment_data.deduction_percentage or payment_data.deduction_amount):
        try:
            # Calculate deduction amount
            if payment_data.deduction_amount and payment_data.deduction_amount > 0:
                deduction_amount = payment_data.deduction_amount
                deduction_percentage = (deduction_amount / invoice.get("total_amount", 1)) * 100
            elif payment_data.deduction_percentage and payment_data.deduction_percentage > 0:
                deduction_percentage = payment_data.deduction_percentage
                deduction_amount = (invoice.get("total_amount", 0) * deduction_percentage) / 100
            else:
                deduction_amount = 0
                deduction_percentage = 0
            
            if deduction_amount > 0:
                # Generate credit note number
                now = get_malaysia_time()
                year = now.year
                month = now.month
                last_cn = await db.credit_notes.find_one(
                    {"cn_number": {"$regex": f"^CN/MDDRC/{year}/{month:02d}/"}},
                    sort=[("cn_number", -1)]
                )
                if last_cn:
                    last_num = int(last_cn["cn_number"].split("/")[-1])
                    cn_number = f"CN/MDDRC/{year}/{month:02d}/{str(last_num + 1).zfill(4)}"
                else:
                    cn_number = f"CN/MDDRC/{year}/{month:02d}/0001"
                
                credit_note = {
                    "id": str(uuid.uuid4()),
                    "cn_number": cn_number,
                    "invoice_id": payment_data.invoice_id,
                    "invoice_number": invoice.get("invoice_number"),
                    "session_id": invoice.get("session_id"),
                    "session_name": invoice.get("session_name") or invoice.get("programme_name"),
                    "company_id": invoice.get("company_id"),
                    # Use bill_to_name if available (for HRDCorp invoices), otherwise company_name
                    "company_name": invoice.get("bill_to_name") or invoice.get("company_name"),
                    "bill_to_name": invoice.get("bill_to_name"),
                    "bill_to_address": invoice.get("bill_to_address"),
                    "reason": payment_data.deduction_reason or "HRDCorp Levy Deduction",
                    "description": f"{deduction_percentage:.1f}% deduction",
                    "base_amount": invoice.get("total_amount", 0),
                    "percentage": deduction_percentage,
                    "amount": round(deduction_amount, 2),
                    "status": "draft",
                    "created_by": current_user.id,
                    "created_at": get_malaysia_time().isoformat(),
                    "cn_date": payment_data.payment_date
                }
                
                await db.credit_notes.insert_one(credit_note)
                credit_note.pop("_id", None)
                credit_note_created = credit_note
                
                await log_finance_action("credit_note", credit_note["id"], "created", current_user.id, after_value=credit_note)
        except Exception as e:
            print(f"Error creating credit note: {e}")
    
    # Check if fully paid
    all_payments = await db.payments.find({"invoice_id": payment_data.invoice_id}, {"_id": 0}).to_list(100)
    total_paid = sum(p.get("amount", 0) for p in all_payments)
    
    if total_paid >= invoice.get("total_amount", 0):
        await db.invoices.update_one({"id": payment_data.invoice_id}, {"$set": {"status": "paid", "updated_at": get_malaysia_time().isoformat()}})
        await db.sessions.update_one({"invoice_id": payment_data.invoice_id}, {"$set": {"invoice_status": "paid"}})
    elif total_paid > 0:
        await db.invoices.update_one({"id": payment_data.invoice_id}, {"$set": {"status": "partial", "updated_at": get_malaysia_time().isoformat()}})
    
    await log_finance_action("payment", payment["id"], "created", current_user.id, after_value=payment)
    
    result = {"payment": payment}
    if credit_note_created:
        result["credit_note"] = credit_note_created
    
    return result

# Company Settings APIs
@api_router.get("/finance/company-settings")
async def get_company_settings(current_user: User = Depends(get_current_user)):
    """Get company settings for invoices/receipts"""
    # Allow marketing users to read company settings (for quotation PDF)
    has_marketing = "marketing" in (current_user.additional_roles or []) or current_user.role == "marketing"
    if current_user.role not in ["admin", "super_admin", "finance"] and not has_marketing:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.company_settings.find_one({"id": "company_settings"}, {"_id": 0})
    if not settings:
        # Return default settings
        settings = CompanySettings().model_dump()
        await db.company_settings.insert_one(settings)
    
    return settings

@api_router.put("/finance/company-settings")
async def update_company_settings(settings_data: dict, current_user: User = Depends(get_current_user)):
    """Update company settings"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can update settings")
    
    settings_data["updated_at"] = get_malaysia_time().isoformat()
    settings_data["updated_by"] = current_user.id
    settings_data["id"] = "company_settings"
    
    await db.company_settings.update_one(
        {"id": "company_settings"},
        {"$set": settings_data},
        upsert=True
    )
    
    return {"message": "Settings updated successfully"}


@api_router.get("/finance/pdf-layout-preview")
async def get_pdf_layout_preview(current_user: User = Depends(get_current_user)):
    """Generate a preview PDF with current layout settings"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get company settings
    company_settings = await db.company_settings.find_one({"id": "company_settings"}, {"_id": 0})
    if not company_settings:
        company_settings = {}
    
    # Parse primary color
    primary_color_hex = company_settings.get("primary_color", "#1a365d")
    try:
        primary_color_rgb = tuple(int(primary_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    except:
        primary_color_rgb = (26, 54, 93)
    
    # Create preview PDF
    pdf = QuotationPDF(company_settings, primary_color_rgb)
    pdf.add_page()
    
    # Add sample content
    pdf.set_font_safe('B', 12)
    pdf.ln(10)
    pdf.cell_safe(0, 8, "QUOTATION LAYOUT PREVIEW", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font_safe('', 10)
    pdf.multi_cell_safe(0, 5, "This is a preview of your PDF layout. Adjust the settings below to customize the header layout:\n\n" +
        f"• Logo X Position: {company_settings.get('logo_x', 10)}mm\n" +
        f"• Logo Y Position: {company_settings.get('logo_y', 8)}mm\n" +
        f"• Logo Width: {company_settings.get('logo_width', 35)}mm\n" +
        f"• Logo Height: {company_settings.get('logo_height', 0)}mm (0 = auto)\n" +
        f"• Header X Position: {company_settings.get('header_x', 50)}mm\n" +
        f"• Header Y Position: {company_settings.get('header_y', 8)}mm\n")
    
    # Output PDF
    pdf_output = pdf.output()
    
    return Response(
        content=bytes(pdf_output),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=layout_preview.pdf"}
    )



# Upload company logo for documents (payslip, pay advice, invoices)
@api_router.post("/finance/company-settings/upload-logo")
async def upload_company_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload company logo for document headers"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can upload logo")
    
    # Validate file type
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only image files (PNG, JPG, JPEG, GIF, WEBP) are allowed")
    
    # Read file content
    content = await file.read()
    
    # Save to uploads folder
    upload_dir = "uploads/company"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = get_malaysia_time().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"company_logo_{timestamp}{file_ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Generate URL for the file
    logo_url = f"/api/uploads/company/{safe_filename}"
    
    # Update company settings
    await db.company_settings.update_one(
        {"id": "company_settings"},
        {"$set": {
            "logo_url": logo_url,
            "logo_filename": file.filename,
            "updated_at": get_malaysia_time().isoformat(),
            "updated_by": current_user.id
        }},
        upsert=True
    )
    
    return {
        "message": "Logo uploaded successfully",
        "url": logo_url,
        "filename": file.filename
    }

# Serve uploaded company files (logo, etc.)
@api_router.get("/uploads/company/{filename}")
async def get_company_file(filename: str):
    """Serve uploaded company files"""
    file_path = f"uploads/company/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type based on extension
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

# Upload custom indemnity form PDF
@api_router.post("/finance/company-settings/upload-indemnity-form")
async def upload_indemnity_form(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload custom indemnity form PDF"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can upload indemnity form")
    
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
        raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX files are allowed")
    
    # Read file content
    content = await file.read()
    
    # Save to uploads folder
    upload_dir = "uploads/indemnity"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = get_malaysia_time().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"indemnity_form_{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Generate URL for the file
    file_url = f"/api/uploads/indemnity/{safe_filename}"
    
    # Update company settings
    await db.company_settings.update_one(
        {"id": "company_settings"},
        {"$set": {
            "indemnity_form_url": file_url,
            "indemnity_form_filename": file.filename,
            "updated_at": get_malaysia_time().isoformat(),
            "updated_by": current_user.id
        }},
        upsert=True
    )
    
    return {
        "message": "Indemnity form uploaded successfully",
        "url": file_url,
        "filename": file.filename
    }

# Serve uploaded indemnity form files
@api_router.get("/uploads/indemnity/{filename}")
async def get_indemnity_file(filename: str):
    """Serve uploaded indemnity form file"""
    file_path = f"uploads/indemnity/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type
    content_type = "application/pdf"
    if filename.lower().endswith('.doc'):
        content_type = "application/msword"
    elif filename.lower().endswith('.docx'):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    return FileResponse(file_path, media_type=content_type, filename=filename)

# Receipt Data API (for printing)
@api_router.get("/finance/payments/{payment_id}/receipt")
async def get_receipt_data(payment_id: str, current_user: User = Depends(get_current_user)):
    """Get receipt data for printing"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Get invoice details
    invoice = await db.invoices.find_one({"id": payment.get("invoice_id")}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get company settings
    settings = await db.company_settings.find_one({"id": "company_settings"}, {"_id": 0})
    if not settings:
        settings = CompanySettings().model_dump()
    
    # Generate receipt number
    receipt_count = await db.payments.count_documents({})
    year = get_malaysia_time().year
    month = get_malaysia_time().month
    receipt_number = f"RCP/{year}/{month:02d}/{receipt_count:04d}"
    
    return {
        "receipt_number": receipt_number,
        "payment": payment,
        "invoice": invoice,
        "company_settings": settings
    }

# Session Payables Report (Course Registration Form style)
@api_router.get("/finance/session/{session_id}/payables-report")
async def get_session_payables_report(session_id: str, current_user: User = Depends(get_current_user)):
    """Get comprehensive payables report for a session (like Course Registration Form)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get session
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get company
    company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0})
    
    # Get program
    program = await db.programs.find_one({"id": session.get("program_id")}, {"_id": 0})
    
    # Get participants count
    participant_count = len(session.get("participant_ids", []))
    
    # Get coordinator
    coordinator = await db.users.find_one({"id": session.get("coordinator_id")}, {"_id": 0, "full_name": 1})
    
    # Get invoice
    invoice = await db.invoices.find_one({"session_id": session_id}, {"_id": 0})
    
    # Get trainer fees
    trainer_fees = await db.trainer_fees.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    
    # Get coordinator fees
    coordinator_fees = await db.coordinator_fees.find({"session_id": session_id}, {"_id": 0}).to_list(10)
    
    # Get expenses
    expenses = await db.session_expenses.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    
    # Get marketing commission
    marketing = await db.marketing_commissions.find({"session_id": session_id}, {"_id": 0}).to_list(10)
    
    # Calculate totals
    total_trainer_fees = sum(t.get("fee_amount", 0) for t in trainer_fees)
    total_coordinator_fees = sum(c.get("total_fee", 0) for c in coordinator_fees)
    total_marketing = sum(m.get("commission_amount", 0) for m in marketing)
    total_expenses = sum(e.get("actual_amount") or e.get("amount", 0) for e in expenses)
    
    # Get costing data
    costing = await db.session_costing.find_one({"session_id": session_id}, {"_id": 0})
    
    return {
        "session": {
            "id": session_id,
            "name": session.get("name"),
            "start_date": session.get("start_date"),
            "end_date": session.get("end_date"),
            "venue": session.get("venue"),
            "num_days": session.get("num_days", 1)
        },
        "client": {
            "company_name": company.get("name") if company else session.get("company_name"),
            "contact_person": session.get("contact_person"),
            "contact_phone": session.get("contact_phone"),
            "contact_email": session.get("contact_email")
        },
        "program": {
            "name": program.get("name") if program else session.get("program_name"),
            "category": program.get("category") if program else ""
        },
        "participants": {
            "count": participant_count,
            "target": session.get("pax", 0)
        },
        "coordinator": {
            "name": coordinator.get("full_name") if coordinator else "",
            "id": session.get("coordinator_id")
        },
        "invoice": {
            "number": invoice.get("invoice_number") if invoice else "",
            "status": invoice.get("status") if invoice else "",
            "total_amount": invoice.get("total_amount", 0) if invoice else 0,
            "bill_to": invoice.get("bill_to_name") if invoice else ""
        },
        "payables": {
            "trainer_fees": trainer_fees,
            "coordinator_fees": coordinator_fees,
            "marketing_commissions": marketing,
            "expenses": expenses
        },
        "totals": {
            "trainer_fees": total_trainer_fees,
            "coordinator_fees": total_coordinator_fees,
            "marketing_commissions": total_marketing,
            "expenses": total_expenses,
            "total_payables": total_trainer_fees + total_coordinator_fees + total_marketing + total_expenses,
            "invoice_amount": invoice.get("total_amount", 0) if invoice else 0,
            "profit": (invoice.get("total_amount", 0) if invoice else 0) - (total_trainer_fees + total_coordinator_fees + total_marketing + total_expenses)
        },
        "costing": costing
    }

async def get_payments(invoice_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get payments with invoice details"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if invoice_id:
        query["invoice_id"] = invoice_id
    
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enrich with invoice details
    result = []
    for payment in payments:
        invoice = await db.invoices.find_one({"id": payment.get("invoice_id")}, {"_id": 0, "invoice_number": 1, "company_name": 1, "session_id": 1})
        if invoice:  # Only include if invoice exists
            payment["invoice_number"] = invoice.get("invoice_number", "N/A")
            payment["company_name"] = invoice.get("company_name", "")
            result.append(payment)
        else:
            # Orphaned payment - delete it
            await db.payments.delete_one({"id": payment.get("id")})
    
    return result

@api_router.get("/finance/income/trainer/{trainer_id}")
async def get_trainer_income(trainer_id: str, current_user: User = Depends(get_current_user)):
    """Get trainer income from all sessions"""
    if current_user.role == "trainer" and current_user.id != trainer_id:
        raise HTTPException(status_code=403, detail="Can only view your own income")
    
    if current_user.role not in ["admin", "super_admin", "finance", "trainer"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get records from trainer_fees collection (set in session costing)
    records = await db.trainer_fees.find({"trainer_id": trainer_id}, {"_id": 0}).to_list(1000)
    
    # Filter out records for deleted sessions and enrich with session details
    valid_records = []
    for record in records:
        session = await db.sessions.find_one({"id": record.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "end_date": 1, "company_id": 1})
        if session:  # Only include if session still exists
            record["session_name"] = session.get("name")
            record["training_dates"] = f"{session.get('start_date')} to {session.get('end_date')}"
            record["start_date"] = session.get("start_date")  # For filtering
            # Get company name
            if session.get("company_id"):
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
                record["company_name"] = company.get("name") if company else None
            record["amount"] = record.get("fee_amount", 0)  # Map fee_amount to amount for consistency
            valid_records.append(record)
        else:
            # Session was deleted - clean up orphaned fee record
            await db.trainer_fees.delete_one({"id": record.get("id")})
    
    total = sum(r.get("fee_amount", 0) for r in valid_records)
    paid = sum(r.get("fee_amount", 0) for r in valid_records if r.get("status") == "paid")
    
    return {"records": valid_records, "summary": {"total_income": total, "paid_income": paid, "pending_income": total - paid}}

@api_router.get("/finance/income/coordinator/{coordinator_id}")
async def get_coordinator_income(coordinator_id: str, current_user: User = Depends(get_current_user)):
    """Get coordinator income from all sessions"""
    if current_user.role == "coordinator" and current_user.id != coordinator_id:
        if "coordinator" not in (current_user.additional_roles or []):
            raise HTTPException(status_code=403, detail="Can only view your own income")
    
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        if "coordinator" not in (current_user.additional_roles or []):
            raise HTTPException(status_code=403, detail="Access denied")
    
    records = await db.coordinator_fees.find({"coordinator_id": coordinator_id}, {"_id": 0}).to_list(1000)
    
    # Filter out records for deleted sessions and enrich with session details
    valid_records = []
    for record in records:
        session = await db.sessions.find_one({"id": record.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "end_date": 1, "company_id": 1})
        if session:  # Only include if session still exists
            record["session_name"] = session.get("name")
            record["training_dates"] = f"{session.get('start_date')} to {session.get('end_date')}"
            record["start_date"] = session.get("start_date")  # For filtering
            # Get company name
            company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
            record["company_name"] = company.get("name") if company else None
            record["amount"] = record.get("total_fee", 0)  # Map total_fee to amount for consistency
            valid_records.append(record)
        else:
            # Session was deleted - clean up orphaned fee record
            await db.coordinator_fees.delete_one({"id": record.get("id")})
    
    total = sum(r.get("total_fee", 0) for r in valid_records)
    paid = sum(r.get("total_fee", 0) for r in valid_records if r.get("status") == "paid")
    
    return {"records": valid_records, "summary": {"total_fees": total, "paid_fees": paid, "pending_fees": total - paid}}

@api_router.get("/finance/income/marketing/{marketing_id}")
async def get_marketing_income(marketing_id: str, current_user: User = Depends(get_current_user)):
    """Get marketing income"""
    is_marketing = current_user.role == "marketing" or "marketing" in (current_user.additional_roles or [])
    
    if is_marketing and current_user.id != marketing_id:
        raise HTTPException(status_code=403, detail="Can only view your own income")
    
    if current_user.role not in ["admin", "super_admin", "finance", "marketing"]:
        if "marketing" not in (current_user.additional_roles or []):
            raise HTTPException(status_code=403, detail="Access denied")
    
    records = await db.marketing_commissions.find({"marketing_user_id": marketing_id}, {"_id": 0}).to_list(1000)
    
    # Filter out records for deleted sessions
    valid_records = []
    for record in records:
        session = await db.sessions.find_one({"id": record.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "end_date": 1, "company_id": 1})
        if session:  # Only include if session still exists
            record["session_name"] = session.get("name")
            record["training_dates"] = f"{session.get('start_date')} to {session.get('end_date')}"
            record["start_date"] = session.get("start_date")  # For filtering
            company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
            record["company_name"] = company.get("name") if company else None
            valid_records.append(record)
        else:
            # Session was deleted - clean up orphaned commission record
            await db.marketing_commissions.delete_one({"id": record.get("id")})
    
    total = sum(r.get("calculated_amount", 0) for r in valid_records)
    paid = sum(r.get("calculated_amount", 0) for r in valid_records if r.get("status") == "paid")
    
    return {"records": valid_records, "summary": {"total_commission": total, "paid_commission": paid, "pending_commission": total - paid}}

@api_router.get("/finance/marketing-users")
async def get_marketing_users(current_user: User = Depends(get_current_user)):
    """Get list of users who can be assigned as marketing (all staff members)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all staff who can potentially be marketing (coordinators, trainers, assistant_admin, or anyone with marketing role)
    marketing_users = await db.users.find(
        {"role": {"$in": ["marketing", "coordinator", "trainer", "assistant_admin"]}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1, "additional_roles": 1, "id_number": 1}
    ).to_list(100)
    
    return marketing_users

@api_router.get("/finance/dashboard")
async def get_finance_dashboard(year: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get finance dashboard with optional year filter"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Helper function to extract year from date value
    def get_date_year(date_val):
        if not date_val:
            return None
        if isinstance(date_val, str):
            try:
                return datetime.fromisoformat(date_val.replace('Z', '+00:00')).year
            except:
                try:
                    return int(date_val[:4])
                except:
                    return None
        elif hasattr(date_val, 'year'):
            return date_val.year
        return None
    
    # Get all invoices and filter in Python for consistent date handling
    all_invoices_raw = await db.invoices.find({}, {"_id": 0}).to_list(5000)
    
    # Filter by year if specified
    if year:
        invoices_for_year = [inv for inv in all_invoices_raw if get_date_year(inv.get("invoice_date") or inv.get("created_at")) == year]
    else:
        invoices_for_year = all_invoices_raw
    
    # Invoice counts
    total_invoices = len(invoices_for_year)
    draft_invoices = len([inv for inv in invoices_for_year if inv.get("status") in ["auto_draft", "finance_review"]])
    approved_invoices = len([inv for inv in invoices_for_year if inv.get("status") == "approved"])
    issued_invoices = len([inv for inv in invoices_for_year if inv.get("status") == "issued"])
    paid_invoices = len([inv for inv in invoices_for_year if inv.get("status") == "paid"])
    
    # Financial totals
    financial_invoices = [inv for inv in invoices_for_year if inv.get("status") in ["issued", "paid"]]
    total_issued_amount = sum(inv.get("total_amount", 0) for inv in financial_invoices)
    total_collected = sum(inv.get("total_amount", 0) for inv in financial_invoices if inv.get("status") == "paid")
    
    # Payables with year filter (based on created_at)
    pending_trainer_all = await db.trainer_fees.find({"status": {"$ne": "paid"}}, {"_id": 0, "fee_amount": 1, "created_at": 1, "session_start_date": 1}).to_list(1000)
    pending_coord_all = await db.coordinator_fees.find({"status": {"$ne": "paid"}}, {"_id": 0, "total_fee": 1, "created_at": 1, "session_start_date": 1}).to_list(1000)
    pending_comm_all = await db.marketing_commissions.find({"status": {"$in": ["pending", "approved"]}}, {"_id": 0, "calculated_amount": 1, "created_at": 1, "session_start_date": 1}).to_list(1000)
    
    if year:
        pending_trainer = [r for r in pending_trainer_all if get_date_year(r.get("session_start_date") or r.get("created_at")) == year]
        pending_coord = [r for r in pending_coord_all if get_date_year(r.get("session_start_date") or r.get("created_at")) == year]
        pending_comm = [r for r in pending_comm_all if get_date_year(r.get("session_start_date") or r.get("created_at")) == year]
    else:
        pending_trainer = pending_trainer_all
        pending_coord = pending_coord_all
        pending_comm = pending_comm_all
    
    total_pending = sum(r.get("fee_amount", 0) for r in pending_trainer) + sum(r.get("total_fee", 0) for r in pending_coord) + sum(r.get("calculated_amount", 0) for r in pending_comm)
    
    # Get available years for the dropdown
    available_years = set()
    for inv in all_invoices_raw:
        inv_year = get_date_year(inv.get("invoice_date") or inv.get("created_at"))
        if inv_year:
            available_years.add(inv_year)
    
    return {
        "invoices": {"total": total_invoices, "draft": draft_invoices, "approved": approved_invoices, "issued": issued_invoices, "paid": paid_invoices},
        "financials": {"total_issued": total_issued_amount, "total_collected": total_collected, "outstanding_receivables": total_issued_amount - total_collected},
        "payables": {"pending_total": total_pending},
        "available_years": sorted(list(available_years), reverse=True),
        "selected_year": year
    }

@api_router.get("/finance/audit-log")
async def get_audit_log(entity_type: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 100, current_user: User = Depends(get_current_user)):
    """Get audit log"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    
    logs = await db.finance_audit_log.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    # Enrich with user names and ensure serializable
    result = []
    for log in logs:
        user = await db.users.find_one({"id": log.get("changed_by")}, {"_id": 0, "full_name": 1})
        log_dict = {
            "id": log.get("id"),
            "entity_type": log.get("entity_type"),
            "entity_id": log.get("entity_id"),
            "action": log.get("action"),
            "changed_by": log.get("changed_by"),
            "changed_by_name": user.get("full_name") if user else "Unknown",
            "timestamp": log.get("timestamp"),
            "before_value": str(log.get("before_value", "")) if log.get("before_value") else None,
            "after_value": str(log.get("after_value", "")) if log.get("after_value") else None,
            "remark": log.get("remark")
        }
        result.append(log_dict)
    
    return result

@api_router.post("/finance/income/trainer/{record_id}/mark-paid")
async def mark_trainer_paid(record_id: str, current_user: User = Depends(get_current_user)):
    """Mark trainer income as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.trainer_income.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.trainer_income.update_one({"id": record_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id}})
    await log_finance_action("trainer_income", record_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Marked as paid"}

@api_router.post("/finance/income/coordinator/{record_id}/mark-paid")
async def mark_coordinator_paid(record_id: str, current_user: User = Depends(get_current_user)):
    """Mark coordinator fee as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.coordinator_fees.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.coordinator_fees.update_one({"id": record_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id}})
    await log_finance_action("coordinator_fee", record_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Marked as paid"}

@api_router.post("/finance/income/commission/{record_id}/mark-paid")
async def mark_commission_paid(record_id: str, current_user: User = Depends(get_current_user)):
    """Mark commission as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.marketing_commissions.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.marketing_commissions.update_one({"id": record_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}})
    await log_finance_action("marketing_commission", record_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Marked as paid"}

@api_router.post("/finance/trainer-fees/{fee_id}/mark-paid")
async def mark_trainer_fee_paid(fee_id: str, current_user: User = Depends(get_current_user)):
    """Mark trainer fee as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.trainer_fees.find_one({"id": fee_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Fee record not found")
    
    await db.trainer_fees.update_one({"id": fee_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}})
    await log_finance_action("trainer_fee", fee_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Trainer fee marked as paid"}

@api_router.post("/finance/coordinator-fees/{fee_id}/mark-paid")
async def mark_coordinator_fee_paid(fee_id: str, current_user: User = Depends(get_current_user)):
    """Mark coordinator fee as paid"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can mark payments")
    
    record = await db.coordinator_fees.find_one({"id": fee_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Fee record not found")
    
    await db.coordinator_fees.update_one({"id": fee_id}, {"$set": {"status": "paid", "paid_date": get_malaysia_time().strftime("%Y-%m-%d"), "paid_by": current_user.id, "updated_at": get_malaysia_time().isoformat()}})
    await log_finance_action("coordinator_fee", fee_id, "status_changed", current_user.id, {"status": record.get("status")}, {"status": "paid"})
    
    return {"message": "Coordinator fee marked as paid"}

# ============ PAYABLES PERIOD MANAGEMENT ============

class PayablesPeriodCreate(BaseModel):
    year: int
    month: int

@api_router.get("/finance/payables/periods")
async def get_payables_periods(current_user: User = Depends(get_current_user)):
    """Get all payables periods with open/closed status"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    periods = await db.payables_periods.find({}, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return periods

@api_router.post("/finance/payables/periods")
async def create_payables_period(period: PayablesPeriodCreate, current_user: User = Depends(get_current_user)):
    """Create a new payables period (opens it)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = await db.payables_periods.find_one({"year": period.year, "month": period.month}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Period already exists")
    
    now = get_malaysia_time()
    new_period = {
        "id": str(uuid.uuid4()),
        "year": period.year,
        "month": period.month,
        "status": "open",
        "opened_at": now.isoformat(),
        "opened_by": current_user.id,
        "created_at": now.isoformat()
    }
    
    await db.payables_periods.insert_one({**new_period, "_id": new_period["id"]})
    return new_period

@api_router.post("/finance/payables/periods/{period_id}/close")
async def close_payables_period(period_id: str, current_user: User = Depends(get_current_user)):
    """Close a payables period - no more changes allowed after closing"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    period = await db.payables_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Period is already closed")
    
    now = get_malaysia_time()
    await db.payables_periods.update_one(
        {"id": period_id},
        {"$set": {
            "status": "closed",
            "closed_at": now.isoformat(),
            "closed_by": current_user.id,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Period closed successfully"}

@api_router.post("/finance/payables/periods/{period_id}/reopen")
async def reopen_payables_period(period_id: str, reason: str = "", current_user: User = Depends(get_current_user)):
    """Reopen a closed payables period - requires admin and reason"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can reopen periods")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    period = await db.payables_periods.find_one({"id": period_id}, {"_id": 0})
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    
    if period.get("status") == "open":
        raise HTTPException(status_code=400, detail="Period is already open")
    
    now = get_malaysia_time()
    await db.payables_periods.update_one(
        {"id": period_id},
        {"$set": {
            "status": "open",
            "reopened_at": now.isoformat(),
            "reopened_by": current_user.id,
            "reopen_reason": reason,
            "updated_at": now.isoformat()
        }}
    )
    
    # Create audit trail
    await create_audit_trail_entry(
        action="Payables Period Reopened",
        record_reference=f"{period['year']}-{str(period['month']).zfill(2)}",
        entity_type="payables_period",
        entity_id=period_id,
        changed_by=current_user,
        reason=reason,
        field_changed="status",
        from_value="closed",
        to_value="open"
    )
    
    return {"message": "Period reopened successfully"}

@api_router.get("/finance/payables/period-status")
async def get_period_status(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Check if a specific period is open or closed"""
    period = await db.payables_periods.find_one({"year": year, "month": month}, {"_id": 0})
    if not period:
        return {"status": "open", "exists": False}  # If no period record, assume open
    return {"status": period.get("status", "open"), "exists": True, "period": period}

# ============ PAYABLES EXCEL EXPORT ============

@api_router.get("/finance/payables/export-excel")
async def export_payables_excel(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Export payables for a specific month as Excel format data"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Define date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    end_date = end_date.replace(hour=23, minute=59, second=59)
    
    # Collect all payables from all sources
    payables_data = []
    
    # 1. Trainer fees - get from same endpoint trainers see
    trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(1000)
    for fee in trainer_fees:
        # Get session info
        session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        
        # Check if session is in the target month
        session_date = session.get("start_date")
        if session_date:
            try:
                if isinstance(session_date, str):
                    session_dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                else:
                    session_dt = session_date
                if session_dt.year != year or session_dt.month != month:
                    continue
            except:
                continue
        else:
            continue
        
        # Get company info
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        company_name = company.get("name") if company else "-"
        
        # Get invoice info
        invoice = await db.invoices.find_one({"session_id": fee.get("session_id")}, {"_id": 0, "invoice_number": 1})
        invoice_number = invoice.get("invoice_number") if invoice else "-"
        
        payables_data.append({
            "name": fee.get("trainer_name", "Unknown").upper(),
            "invoice_number": invoice_number,
            "training_date": session_date,
            "position": fee.get("trainer_role", "Trainer").title(),
            "company": company_name,
            "details": session.get("name", "-"),
            "amount": fee.get("fee_amount", 0),
            "status": fee.get("status", "pending"),
            "type": "trainer"
        })
    
    # 2. Coordinator fees
    coord_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(1000)
    for fee in coord_fees:
        session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        
        session_date = session.get("start_date")
        if session_date:
            try:
                if isinstance(session_date, str):
                    session_dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                else:
                    session_dt = session_date
                if session_dt.year != year or session_dt.month != month:
                    continue
            except:
                continue
        else:
            continue
        
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        company_name = company.get("name") if company else "-"
        
        invoice = await db.invoices.find_one({"session_id": fee.get("session_id")}, {"_id": 0, "invoice_number": 1})
        invoice_number = invoice.get("invoice_number") if invoice else "-"
        
        payables_data.append({
            "name": fee.get("coordinator_name", "Unknown").upper(),
            "invoice_number": invoice_number,
            "training_date": session_date,
            "position": "Coordinator",
            "company": company_name,
            "details": session.get("name", "-"),
            "amount": fee.get("total_fee", 0),
            "status": fee.get("status", "pending"),
            "type": "coordinator"
        })
    
    # 3. Marketing commissions
    mkt_comm = await db.marketing_commissions.find({}, {"_id": 0}).to_list(1000)
    for comm in mkt_comm:
        session = await db.sessions.find_one({"id": comm.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        
        session_date = session.get("start_date")
        if session_date:
            try:
                if isinstance(session_date, str):
                    session_dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                else:
                    session_dt = session_date
                if session_dt.year != year or session_dt.month != month:
                    continue
            except:
                continue
        else:
            continue
        
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        company_name = company.get("name") if company else "-"
        
        invoice = await db.invoices.find_one({"session_id": comm.get("session_id")}, {"_id": 0, "invoice_number": 1})
        invoice_number = invoice.get("invoice_number") if invoice else "-"
        
        # Get marketer name - try multiple fields
        marketer_name = comm.get("marketer_name") or comm.get("user_name")
        if not marketer_name or marketer_name == "Unknown":
            # Look up from marketing_user_id
            mkt_user_id = comm.get("marketing_user_id") or comm.get("user_id")
            if mkt_user_id:
                mkt_user = await db.users.find_one({"id": mkt_user_id}, {"_id": 0, "full_name": 1})
                if mkt_user:
                    marketer_name = mkt_user.get("full_name", "Unknown")
        
        payables_data.append({
            "name": (marketer_name or "Unknown").upper(),
            "invoice_number": invoice_number,
            "training_date": session_date,
            "position": "Marketing",
            "company": company_name,
            "details": session.get("name", "-"),
            "amount": comm.get("calculated_amount", 0),
            "status": comm.get("status", "pending"),
            "type": "marketing"
        })
    
    # Sort by name, then by date
    payables_data.sort(key=lambda x: (x["name"], x.get("training_date", "")))
    
    # Group by name and calculate totals
    grouped_data = {}
    for item in payables_data:
        name = item["name"]
        if name not in grouped_data:
            grouped_data[name] = {"items": [], "total": 0}
        grouped_data[name]["items"].append(item)
        grouped_data[name]["total"] += item["amount"]
    
    # Calculate grand total
    grand_total = sum(g["total"] for g in grouped_data.values())
    
    return {
        "period": f"{year}-{str(month).zfill(2)}",
        "period_name": datetime(year, month, 1).strftime("%B %Y"),
        "data": grouped_data,
        "grand_total": grand_total,
        "generated_at": get_malaysia_time().isoformat()
    }

# ============ PAYABLES LIST ENDPOINTS ============

@api_router.get("/finance/payables/trainer-fees")
async def get_pending_trainer_fees(current_user: User = Depends(get_current_user)):
    """Get all trainer fees (pending and paid)"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get valid session IDs first
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "name": 1, "start_date": 1}).to_list(1000)
    session_map = {s["id"]: {"name": s["name"], "start_date": s.get("start_date")} for s in sessions}
    
    fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(1000)
    
    # Enrich with trainer and session names, filter out orphans
    result = []
    for fee in fees:
        if fee.get("session_id") not in session_map:
            # Orphaned record - delete it
            await db.trainer_fees.delete_one({"id": fee.get("id")})
            continue
            
        trainer = await db.users.find_one({"id": fee.get("trainer_id")}, {"_id": 0, "full_name": 1})
        fee["trainer_name"] = trainer.get("full_name") if trainer else "Unknown"
        fee["session_name"] = session_map.get(fee.get("session_id"), {}).get("name", "Unknown Session")
        fee["session_start_date"] = session_map.get(fee.get("session_id"), {}).get("start_date")
        result.append(fee)
    
    return result

@api_router.get("/finance/payables/coordinator-fees")
async def get_pending_coordinator_fees(current_user: User = Depends(get_current_user)):
    """Get all coordinator fees"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get valid session IDs
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "name": 1, "start_date": 1}).to_list(1000)
    session_map = {s["id"]: {"name": s["name"], "start_date": s.get("start_date")} for s in sessions}
    
    fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(1000)
    
    result = []
    for fee in fees:
        if fee.get("session_id") not in session_map:
            await db.coordinator_fees.delete_one({"id": fee.get("id")})
            continue
            
        coordinator = await db.users.find_one({"id": fee.get("coordinator_id")}, {"_id": 0, "full_name": 1})
        fee["coordinator_name"] = coordinator.get("full_name") if coordinator else "Unknown"
        fee["session_name"] = session_map.get(fee.get("session_id"), {}).get("name", "Unknown Session")
        fee["session_start_date"] = session_map.get(fee.get("session_id"), {}).get("start_date")
        result.append(fee)
    
    return result

@api_router.get("/finance/payables/marketing-commissions")
async def get_pending_marketing_commissions(current_user: User = Depends(get_current_user)):
    """Get all marketing commissions - use values from session costing directly"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get valid session IDs
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "name": 1, "start_date": 1}).to_list(1000)
    session_map = {s["id"]: {"name": s["name"], "start_date": s.get("start_date")} for s in sessions}
    
    comms = await db.marketing_commissions.find({}, {"_id": 0}).to_list(1000)
    
    result = []
    for comm in comms:
        session_id = comm.get("session_id")
        if session_id not in session_map:
            await db.marketing_commissions.delete_one({"id": comm.get("id")})
            continue
        
        # Get ALL invoices for this session (not just one)
        invoices = await db.invoices.find({"session_id": session_id}, {"_id": 0, "total_amount": 1, "tax_amount": 1}).to_list(100)
        invoice_total = sum(inv.get("total_amount", 0) for inv in invoices)
        tax_amount = sum(inv.get("tax_amount", 0) for inv in invoices)
        gross_revenue = invoice_total - tax_amount
        
        # Get expenses
        trainer_fees = await db.trainer_fees.find({"session_id": session_id}, {"_id": 0, "fee_amount": 1}).to_list(100)
        trainer_fees_total = sum(f.get("fee_amount", 0) for f in trainer_fees)
        
        coord_fee = await db.coordinator_fees.find_one({"session_id": session_id}, {"_id": 0, "total_fee": 1})
        coordinator_fee_total = coord_fee.get("total_fee", 0) if coord_fee else 0
        
        expenses = await db.session_expenses.find({"session_id": session_id}, {"_id": 0, "actual_amount": 1, "estimated_amount": 1}).to_list(100)
        cash_expenses_actual = sum(e.get("actual_amount", 0) for e in expenses)
        cash_expenses_estimated = sum(e.get("estimated_amount", 0) for e in expenses)
        cash_expenses = cash_expenses_actual if cash_expenses_actual > 0 else cash_expenses_estimated
        
        # Calculate profit before marketing
        total_expenses_before_marketing = trainer_fees_total + coordinator_fee_total + cash_expenses
        profit_before_marketing = gross_revenue - total_expenses_before_marketing
        
        # Calculate marketing commission
        if comm.get("commission_type") == "percentage":
            calculated_amount = profit_before_marketing * (comm.get("commission_rate", 0) / 100)
        else:
            calculated_amount = comm.get("fixed_amount") or 0.0
        
        # Update the stored value if it differs (keep DB in sync)
        if abs(calculated_amount - (comm.get("calculated_amount") or 0)) > 0.01:
            await db.marketing_commissions.update_one(
                {"id": comm.get("id")},
                {"$set": {"calculated_amount": calculated_amount, "updated_at": get_malaysia_time().isoformat()}}
            )
        
        user = await db.users.find_one({"id": comm.get("marketing_user_id")}, {"_id": 0, "full_name": 1})
        comm["marketing_user_name"] = user.get("full_name") if user else "Unknown"
        comm["session_name"] = session_map.get(session_id, {}).get("name", "Unknown Session")
        comm["session_start_date"] = session_map.get(session_id, {}).get("start_date")
        comm["calculated_amount"] = calculated_amount  # Use the calculated value, not stored
        result.append(comm)
    
    return result

# ============ SESSION COSTING & PROFIT ENDPOINTS ============

@api_router.get("/finance/session/{session_id}/costing")
async def get_session_costing(session_id: str, current_user: User = Depends(get_current_user)):
    """Get complete costing breakdown for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get invoice
    invoice = await db.invoices.find_one({"session_id": session_id}, {"_id": 0})
    invoice_total = invoice.get("total_amount", 0) if invoice else 0
    tax_amount = invoice.get("tax_amount", 0) if invoice else 0
    
    # Get trainer fees (from saved fees or from session assignments)
    trainer_fees = await db.trainer_fees.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    
    # Enrich trainer fees with trainer names if missing
    for fee in trainer_fees:
        if not fee.get("trainer_name") or fee.get("trainer_name") == "Unknown Trainer":
            if fee.get("trainer_id"):
                trainer = await db.users.find_one({"id": fee.get("trainer_id")}, {"_id": 0, "full_name": 1})
                fee["trainer_name"] = trainer.get("full_name") if trainer else "Unknown Trainer"
    
    # Check if we have valid trainer fees (with trainer_ids matching session trainers)
    session_trainer_ids = [ta.get("trainer_id") for ta in session.get("trainer_assignments", [])]
    existing_fee_trainer_ids = [f.get("trainer_id") for f in trainer_fees]
    
    # Find trainers that are in session assignments but don't have fees yet
    new_trainer_ids = [tid for tid in session_trainer_ids if tid not in existing_fee_trainer_ids]
    
    # Add new trainers to trainer_fees
    for ta in session.get("trainer_assignments", []):
        if ta.get("trainer_id") in new_trainer_ids:
            trainer = await db.users.find_one({"id": ta.get("trainer_id")}, {"_id": 0, "full_name": 1})
            trainer_fees.append({
                "trainer_id": ta.get("trainer_id"),
                "trainer_name": trainer.get("full_name") if trainer else "Unknown Trainer",
                "role": ta.get("role", "regular"),
                "fee_amount": 0,
                "remark": "",
                "status": "pending"
            })
    
    # Filter out trainers that are no longer in session assignments
    trainer_fees = [f for f in trainer_fees if f.get("trainer_id") in session_trainer_ids]
    
    trainer_fees_total = sum(f.get("fee_amount", 0) for f in trainer_fees)
    
    # Get coordinator fee
    coord_fee = await db.coordinator_fees.find_one({"session_id": session_id}, {"_id": 0})
    coordinator_fee_total = coord_fee.get("total_fee", 0) if coord_fee else 0
    
    # Get expenses
    expenses = await db.session_expenses.find({"session_id": session_id}, {"_id": 0}).to_list(100)
    cash_expenses_estimated = sum(e.get("estimated_amount", 0) for e in expenses)
    cash_expenses_actual = sum(e.get("actual_amount", 0) for e in expenses)
    
    # Get marketing commission
    marketing = await db.marketing_commissions.find_one({"session_id": session_id}, {"_id": 0})
    
    # Calculate profit (before marketing commission)
    gross_revenue = invoice_total - tax_amount
    # Use actual expenses if > 0, otherwise use estimated
    cash_expenses_used = cash_expenses_actual if cash_expenses_actual > 0 else cash_expenses_estimated
    total_expenses_before_marketing = trainer_fees_total + coordinator_fee_total + cash_expenses_used
    profit_before_marketing = gross_revenue - total_expenses_before_marketing
    
    # Calculate marketing commission on-the-fly using stored rate/type
    # This ensures consistency with Profit Summary display
    marketing_amount = 0.0
    if marketing:
        if marketing.get("commission_type") == "percentage":
            marketing_amount = profit_before_marketing * (marketing.get("commission_rate", 0) / 100)
        else:
            marketing_amount = marketing.get("fixed_amount") or 0.0
    
    # Final profit
    total_expenses = total_expenses_before_marketing + marketing_amount
    final_profit = gross_revenue - total_expenses
    profit_percentage = (final_profit / gross_revenue * 100) if gross_revenue > 0 else 0
    
    # Get company name
    company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
    
    # Calculate headcount for F&B (participants + trainers + coordinator)
    trainer_count = len(session.get("trainer_assignments", []))
    coordinator_count = 1 if session.get("coordinator_id") else 0
    total_headcount = len(session.get("participant_ids", [])) + trainer_count + coordinator_count
    
    return {
        "session_id": session_id,
        "session_name": session.get("name"),
        "company_name": company.get("name") if company else None,
        "training_dates": f"{session.get('start_date')} to {session.get('end_date')}",
        "pax": len(session.get("participant_ids", [])),
        "trainer_count": trainer_count,
        "coordinator_count": coordinator_count,
        "total_headcount": total_headcount,
        
        # Revenue
        "invoice_total": invoice_total,
        "less_tax": tax_amount,
        "gross_revenue": gross_revenue,
        
        # Expenses breakdown
        "trainer_fees": trainer_fees,
        "trainer_fees_total": trainer_fees_total,
        "coordinator_fee": coord_fee,
        "coordinator_fee_total": coordinator_fee_total,
        "expenses": expenses,
        "cash_expenses_estimated": cash_expenses_estimated,
        "cash_expenses_actual": cash_expenses_actual,
        "marketing": marketing,
        "marketing_commission": marketing_amount,
        "total_expenses": total_expenses,
        
        # Profit
        "profit": final_profit,
        "profit_percentage": round(profit_percentage, 2)
    }

@api_router.post("/finance/session/{session_id}/invoice")
async def save_session_invoice(session_id: str, invoice_data: dict, current_user: User = Depends(get_current_user)):
    """Save or update invoice for a session (create if not exists)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if invoice exists for this session
    existing = await db.invoices.find_one({"session_id": session_id}, {"_id": 0})
    
    now = get_malaysia_time()
    
    if existing:
        # Update existing invoice
        update_dict = {
            "pricing_type": invoice_data.get("pricing_type", "lumpsum"),
            "line_items": invoice_data.get("line_items", []),
            "subtotal": invoice_data.get("subtotal", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "total_amount": invoice_data.get("total_amount", 0),
            "updated_at": now.isoformat()
        }
        await db.invoices.update_one({"id": existing["id"]}, {"$set": update_dict})
        return {"message": "Invoice updated", "invoice_id": existing["id"]}
    else:
        # Create new invoice
        invoice_number = await generate_invoice_number()
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        
        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "session_id": session_id,
            "company_id": session.get("company_id"),
            "company_name": company.get("name") if company else None,
            "session_name": session.get("name"),
            "pricing_type": invoice_data.get("pricing_type", "lumpsum"),
            "line_items": invoice_data.get("line_items", []),
            "subtotal": invoice_data.get("subtotal", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "total_amount": invoice_data.get("total_amount", 0),
            "status": "draft",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": current_user.id
        }
        await db.invoices.insert_one(invoice)
        return {"message": "Invoice created", "invoice_id": invoice["id"], "invoice_number": invoice_number}

@api_router.post("/finance/session/{session_id}/additional-invoice")
async def save_additional_invoice(session_id: str, invoice_data: dict, current_user: User = Depends(get_current_user)):
    """Create or update additional invoice for multi-company sessions"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    company_id = invoice_data.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Company ID required")
    
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    now = get_malaysia_time()
    invoice_id = invoice_data.get("invoice_id")
    
    if invoice_id:
        # Update existing additional invoice
        update_dict = {
            "company_id": company_id,
            "company_name": company.get("name"),
            "total_amount": invoice_data.get("total_amount", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "updated_at": now.isoformat()
        }
        await db.invoices.update_one({"id": invoice_id}, {"$set": update_dict})
        return {"message": "Additional invoice updated", "invoice_id": invoice_id}
    else:
        # Check if invoice already exists for this session + company
        existing = await db.invoices.find_one({"session_id": session_id, "company_id": company_id}, {"_id": 0})
        if existing:
            update_dict = {
                "total_amount": invoice_data.get("total_amount", 0),
                "tax_rate": invoice_data.get("tax_rate", 0),
                "tax_amount": invoice_data.get("tax_amount", 0),
                "updated_at": now.isoformat()
            }
            await db.invoices.update_one({"id": existing["id"]}, {"$set": update_dict})
            return {"message": "Additional invoice updated", "invoice_id": existing["id"]}
        
        # Create new additional invoice
        # Check if we should reuse a deleted invoice number
        reuse_number = invoice_data.get("reuse_invoice_number")
        if reuse_number:
            # Verify the number is available for reuse
            deleted_record = await db.deleted_invoice_numbers.find_one({
                "invoice_number": reuse_number,
                "is_available": True
            })
            if deleted_record:
                invoice_number = reuse_number
                # Mark as used
                await db.deleted_invoice_numbers.update_one(
                    {"invoice_number": reuse_number},
                    {"$set": {"is_available": False, "reused_at": now.isoformat(), "reused_session_id": session_id}}
                )
            else:
                invoice_number = await generate_invoice_number()
        else:
            invoice_number = await generate_invoice_number()
        
        # Get program name for the invoice
        program_name = ""
        if session.get("program_id"):
            program = await db.programs.find_one({"id": session.get("program_id")}, {"_id": 0, "name": 1})
            program_name = program.get("name", "") if program else ""
        
        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": invoice_number,
            "session_id": session_id,
            "company_id": company_id,
            "company_name": company.get("name"),
            "bill_to_name": company.get("name"),
            "bill_to_address": f"{company.get('address_line1', '')} {company.get('address_line2', '')}".strip(),
            "bill_to_reg_no": company.get("registration_no", ""),
            "session_name": session.get("name"),
            "programme_name": program_name,
            "venue": session.get("location", ""),
            "training_dates": f"{session.get('start_date', '')} - {session.get('end_date', '')}",
            "pricing_type": "lumpsum",
            "line_items": [{"description": "Training Course Fee", "quantity": 1, "unit_price": invoice_data.get("total_amount", 0), "amount": invoice_data.get("total_amount", 0)}],
            "subtotal": invoice_data.get("total_amount", 0),
            "tax_rate": invoice_data.get("tax_rate", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "total_amount": invoice_data.get("total_amount", 0),
            "status": "auto_draft",
            "is_additional": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": current_user.id
        }
        await db.invoices.insert_one(invoice)
        return {"message": "Additional invoice created", "invoice_id": invoice["id"], "invoice_number": invoice_number}

@api_router.post("/finance/session/{session_id}/trainer-fees")
async def save_trainer_fees(session_id: str, fees: List[dict], current_user: User = Depends(get_current_user)):
    """Save trainer fees for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Clear existing fees for this session
    await db.trainer_fees.delete_many({"session_id": session_id})
    
    # Insert new fees
    for fee in fees:
        trainer = await db.users.find_one({"id": fee.get("trainer_id")}, {"_id": 0, "full_name": 1})
        fee_record = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "trainer_id": fee.get("trainer_id"),
            "trainer_name": trainer.get("full_name") if trainer else fee.get("trainer_name"),
            "role": fee.get("role", "trainer"),
            "fee_amount": float(fee.get("fee_amount", 0)),
            "remark": fee.get("remark"),
            "status": "pending",
            "created_at": get_malaysia_time().isoformat()
        }
        await db.trainer_fees.insert_one(fee_record)
    
    return {"message": f"Saved {len(fees)} trainer fees"}

@api_router.post("/finance/session/{session_id}/coordinator-fee")
async def save_coordinator_fee(session_id: str, fee_data: dict, current_user: User = Depends(get_current_user)):
    """Save coordinator fee for a session (RM 50/day)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    coordinator_id = fee_data.get("coordinator_id") or session.get("coordinator_id")
    if not coordinator_id:
        raise HTTPException(status_code=400, detail="No coordinator assigned")
    
    coordinator = await db.users.find_one({"id": coordinator_id}, {"_id": 0, "full_name": 1})
    
    # Calculate days
    num_days = fee_data.get("num_days", 1)
    daily_rate = fee_data.get("daily_rate", 50.0)
    total_fee = num_days * daily_rate
    
    # Check if coordinator fee exists for this session
    existing_fee = await db.coordinator_fees.find_one({"session_id": session_id}, {"_id": 0, "id": 1})
    fee_id = existing_fee.get("id") if existing_fee and existing_fee.get("id") else str(uuid.uuid4())
    
    # Upsert coordinator fee with id
    await db.coordinator_fees.update_one(
        {"session_id": session_id},
        {"$set": {
            "id": fee_id,
            "coordinator_id": coordinator_id,
            "coordinator_name": coordinator.get("full_name") if coordinator else None,
            "num_days": num_days,
            "daily_rate": daily_rate,
            "total_fee": total_fee,
            "status": "pending",
            "created_at": get_malaysia_time().isoformat()
        }},
        upsert=True
    )
    
    return {"message": "Coordinator fee saved", "total_fee": total_fee}

@api_router.post("/finance/session/{session_id}/expenses")
async def save_session_expenses(session_id: str, expenses: List[dict], current_user: User = Depends(get_current_user)):
    """Save expenses for a session (estimated or actual)"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    for expense in expenses:
        expense_id = expense.get("id")
        
        if expense_id:
            # Update existing
            await db.session_expenses.update_one(
                {"id": expense_id},
                {"$set": {
                    "category": expense.get("category"),
                    "description": expense.get("description"),
                    "expense_type": expense.get("expense_type", "fixed"),
                    "percentage_rate": float(expense.get("percentage_rate", 0)),
                    "estimated_amount": float(expense.get("estimated_amount", 0)),
                    "actual_amount": float(expense.get("actual_amount", 0)),
                    "quantity": int(expense.get("quantity", 1)),
                    "unit_price": float(expense.get("unit_price", 0)),
                    "remark": expense.get("remark"),
                    "status": expense.get("status", "estimated"),
                    "updated_at": get_malaysia_time().isoformat()
                }}
            )
        else:
            # Insert new
            expense_record = {
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "category": expense.get("category"),
                "description": expense.get("description"),
                "expense_type": expense.get("expense_type", "fixed"),
                "percentage_rate": float(expense.get("percentage_rate", 0)),
                "estimated_amount": float(expense.get("estimated_amount", 0)),
                "actual_amount": float(expense.get("actual_amount", 0)),
                "quantity": int(expense.get("quantity", 1)),
                "unit_price": float(expense.get("unit_price", 0)),
                "remark": expense.get("remark"),
                "status": expense.get("status", "estimated"),
                "created_at": get_malaysia_time().isoformat(),
                "updated_at": get_malaysia_time().isoformat()
            }
            await db.session_expenses.insert_one(expense_record)
    
    return {"message": f"Saved {len(expenses)} expenses"}

@api_router.delete("/finance/session/{session_id}/expense/{expense_id}")
async def delete_session_expense(session_id: str, expense_id: str, current_user: User = Depends(get_current_user)):
    """Delete a session expense"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.session_expenses.delete_one({"id": expense_id, "session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return {"message": "Expense deleted"}

@api_router.post("/finance/session/{session_id}/marketing")
async def save_marketing_commission(session_id: str, marketing_data: dict, current_user: User = Depends(get_current_user)):
    """Save or create marketing person and commission for a session"""
    if current_user.role not in ["admin", "super_admin", "finance", "coordinator"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    marketing_user_id = marketing_data.get("marketing_user_id")
    
    # If creating new marketing person (like participant auto-creation)
    if marketing_data.get("create_new") and not marketing_user_id:
        full_name = marketing_data.get("full_name")
        id_number = marketing_data.get("id_number")
        
        if not full_name or not id_number:
            raise HTTPException(status_code=400, detail="Name and ID number required for new marketing person")
        
        # Check if user exists
        existing = await db.users.find_one({"id_number": id_number}, {"_id": 0})
        if existing:
            marketing_user_id = existing.get("id")
            # Add marketing to additional_roles if not already
            if "marketing" not in (existing.get("additional_roles") or []):
                await db.users.update_one(
                    {"id": marketing_user_id},
                    {"$addToSet": {"additional_roles": "marketing"}}
                )
        else:
            # Create new user with marketing role
            email_safe = id_number.replace(" ", "").replace("-", "")
            new_user = {
                "id": str(uuid.uuid4()),
                "email": f"{email_safe}@marketing.mddrc.local",
                "full_name": full_name,
                "id_number": id_number,
                "role": "marketing",
                "additional_roles": [],
                "password": pwd_context.hash("mddrc1"),  # Default password
                "created_at": get_malaysia_time().isoformat(),
                "is_active": True
            }
            await db.users.insert_one(new_user)
            marketing_user_id = new_user["id"]
    
    if not marketing_user_id:
        raise HTTPException(status_code=400, detail="Marketing user ID required")
    
    # Get marketing user name
    marketing_user = await db.users.find_one({"id": marketing_user_id}, {"_id": 0, "full_name": 1})
    
    # Calculate commission immediately from session costing
    costing = await get_session_costing(session_id, current_user)
    gross_revenue = costing.get("gross_revenue", 0)
    # Use actual expenses if available, otherwise estimated
    cash_expenses = costing.get("cash_expenses_actual", 0) or costing.get("cash_expenses_estimated", 0)
    total_expenses = costing.get("trainer_fees_total", 0) + costing.get("coordinator_fee_total", 0) + cash_expenses
    profit_before_marketing = gross_revenue - total_expenses
    
    commission_type = marketing_data.get("commission_type", "percentage")
    commission_rate = float(marketing_data.get("commission_rate", 0))
    fixed_amount = float(marketing_data.get("fixed_amount", 0))
    
    if commission_type == "percentage":
        calculated_amount = profit_before_marketing * commission_rate / 100
    else:
        calculated_amount = fixed_amount
    
    # Get session start_date for P&L filtering
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0, "start_date": 1, "invoice_id": 1})
    
    # Upsert marketing commission
    await db.marketing_commissions.update_one(
        {"session_id": session_id},
        {"$set": {
            "id": str(uuid.uuid4()),  # Ensure ID exists
            "marketing_user_id": marketing_user_id,
            "marketing_user_name": marketing_user.get("full_name") if marketing_user else None,
            "commission_type": commission_type,
            "commission_rate": commission_rate,
            "fixed_amount": fixed_amount,
            "calculated_amount": calculated_amount,
            "session_name": costing.get("session_name"),
            "company_name": costing.get("company_name"),
            "training_dates": costing.get("training_dates"),
            "session_start_date": session.get("start_date") if session else None,
            "invoice_id": session.get("invoice_id") if session else None,
            "status": "pending",
            "updated_at": get_malaysia_time().isoformat()
        }},
        upsert=True
    )
    
    # Update session with marketing user
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "marketing_user_id": marketing_user_id,
            "commission_type": marketing_data.get("commission_type", "percentage"),
            "commission_rate": float(marketing_data.get("commission_rate", 0)),
            "commission_fixed_amount": float(marketing_data.get("fixed_amount", 0))
        }}
    )
    
    return {"message": "Marketing commission saved", "marketing_user_id": marketing_user_id}

@api_router.post("/finance/session/{session_id}/calculate-profit")
async def calculate_and_save_profit(session_id: str, current_user: User = Depends(get_current_user)):
    """Calculate and finalize profit for a session"""
    if current_user.role not in ["admin", "super_admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Finance can finalize profit")
    
    # Get full costing
    costing = await get_session_costing(session_id, current_user)
    
    # Update marketing commission with calculated amount
    marketing = await db.marketing_commissions.find_one({"session_id": session_id}, {"_id": 0})
    if marketing:
        await db.marketing_commissions.update_one(
            {"session_id": session_id},
            {"$set": {
                "calculated_amount": costing["marketing_commission"],
                "status": "approved",
                "updated_at": get_malaysia_time().isoformat()
            }}
        )
    
    return {
        "message": "Profit calculated",
        "profit": costing["profit"],
        "profit_percentage": costing["profit_percentage"],
        "marketing_commission": costing["marketing_commission"]
    }

# Get expense categories
@api_router.get("/finance/expense-categories")
async def get_expense_categories(current_user: User = Depends(get_current_user)):
    """Get list of expense categories with their calculation types and rates"""
    return [
        {"id": "fnb", "name": "F&B", "type": "per_pax", "rate": 25, "description": "RM 25 per pax (auto-calculated)"},
        {"id": "hrdc_levy", "name": "HRDCorp Levy", "type": "percentage", "rate": 4, "description": "4% of invoice"},
        {"id": "wear_tear", "name": "Wear and Tear", "type": "percentage", "rate": 2, "description": "2% of invoice"},
        {"id": "printing", "name": "Printing", "type": "percentage", "rate": 1, "description": "1% of invoice"},
        {"id": "accommodation", "name": "Accommodation", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "allowance", "name": "Allowance", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "petrol", "name": "Petrol", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "toll", "name": "Toll / Touch N Go", "type": "fixed", "rate": 0, "description": "Fixed amount"},
        {"id": "sst", "name": "SST", "type": "percentage", "rate": 0, "description": "Custom percentage"},
        {"id": "muafakat", "name": "Muafakat", "type": "percentage", "rate": 0, "description": "Custom percentage"},
        {"id": "other", "name": "Other Expenses", "type": "fixed", "rate": 0, "description": "Fixed amount"}
    ]

# ============ SUPER ADMIN FINANCE FEATURES ============

# Model for audit trail entries with detailed format
class AuditTrailEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str  # Invoice Number Changed, Invoice Voided, Payment Deleted, etc.
    record_reference: str  # e.g., "KONE ELEVATORS - RM 8,000"
    entity_type: str  # invoice, payment
    entity_id: str
    field_changed: Optional[str] = None  # e.g., "invoice_number"
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    changed_by_name: str
    changed_by_email: str
    reason: str  # Required reason for the change
    timestamp: datetime = Field(default_factory=get_malaysia_time)

async def create_audit_trail_entry(
    action: str,
    record_reference: str,
    entity_type: str,
    entity_id: str,
    changed_by: User,
    reason: str,
    field_changed: str = None,
    from_value: str = None,
    to_value: str = None
):
    """Create a detailed audit trail entry"""
    entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "record_reference": record_reference,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "field_changed": field_changed,
        "from_value": from_value,
        "to_value": to_value,
        "changed_by_name": changed_by.full_name,
        "changed_by_email": changed_by.email,
        "reason": reason,
        "timestamp": get_malaysia_time().isoformat()
    }
    await db.audit_trail.insert_one(entry)
    return entry

# Edit Invoice Number
class InvoiceNumberEditRequest(BaseModel):
    year: int
    month: int
    sequence: int
    reason: str

@api_router.put("/finance/admin/invoices/{invoice_id}/number")
async def edit_invoice_number(
    invoice_id: str,
    request: InvoiceNumberEditRequest,
    current_user: User = Depends(get_current_user)
):
    """Edit invoice number (year/month/sequence) - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can edit invoice numbers")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the invoice
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    old_invoice_number = invoice["invoice_number"]
    
    # Build new invoice number: INV/MDDRC/YYYY/MM/NNNN
    new_invoice_number = f"INV/MDDRC/{request.year}/{request.month:02d}/{request.sequence:04d}"
    
    # Check if new invoice number already exists (excluding current invoice)
    existing = await db.invoices.find_one({
        "invoice_number": new_invoice_number,
        "id": {"$ne": invoice_id}
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"Invoice number {new_invoice_number} already exists")
    
    # Get company name for record reference
    company_name = invoice.get("company_name", "Unknown")
    total_amount = invoice.get("total_amount", 0)
    record_ref = f"{company_name} - RM {total_amount:,.2f}"
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Invoice Number Changed",
        record_reference=record_ref,
        entity_type="invoice",
        entity_id=invoice_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="invoice_number",
        from_value=old_invoice_number,
        to_value=new_invoice_number
    )
    
    # Update the invoice
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "invoice_number": new_invoice_number,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {
        "message": "Invoice number updated successfully",
        "old_number": old_invoice_number,
        "new_number": new_invoice_number
    }

# Void Invoice
class VoidInvoiceRequest(BaseModel):
    reason: str

@api_router.post("/finance/admin/invoices/{invoice_id}/void")
async def void_invoice(
    invoice_id: str,
    request: VoidInvoiceRequest,
    current_user: User = Depends(get_current_user)
):
    """Void an invoice - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can void invoices")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the invoice
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") == "voided":
        raise HTTPException(status_code=400, detail="Invoice is already voided")
    
    old_status = invoice.get("status")
    company_name = invoice.get("company_name", "Unknown")
    total_amount = invoice.get("total_amount", 0)
    record_ref = f"{company_name} - RM {total_amount:,.2f}"
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Invoice Voided",
        record_reference=record_ref,
        entity_type="invoice",
        entity_id=invoice_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="status",
        from_value=old_status,
        to_value="voided"
    )
    
    # Update the invoice status to voided
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "status": "voided",
            "voided_by": current_user.id,
            "voided_at": get_malaysia_time().isoformat(),
            "void_reason": request.reason,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Invoice voided successfully", "invoice_number": invoice.get("invoice_number")}

# Create replacement invoice for voided invoice
@api_router.post("/finance/invoices/{invoice_id}/create-replacement")
async def create_replacement_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """Create a replacement invoice for a voided invoice - only available for voided invoices"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can create replacement invoices")
    
    # Get the voided invoice
    voided_invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not voided_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if voided_invoice.get("status") != "voided":
        raise HTTPException(status_code=400, detail="Replacement invoice can only be created for voided invoices")
    
    # Check if replacement already exists
    existing_replacement = await db.invoices.find_one({
        "replaces_invoice_id": invoice_id,
        "status": {"$ne": "voided"}
    }, {"_id": 0})
    if existing_replacement:
        raise HTTPException(status_code=400, detail=f"A replacement invoice already exists: {existing_replacement.get('invoice_number')}")
    
    # Generate new invoice number
    new_invoice_number = await generate_invoice_number()
    
    # Create replacement invoice copying data from voided one
    replacement_invoice = {
        "id": str(uuid.uuid4()),
        "invoice_number": new_invoice_number,
        "session_id": voided_invoice.get("session_id"),
        "company_id": voided_invoice.get("company_id"),
        "company_name": voided_invoice.get("company_name"),
        "programme_name": voided_invoice.get("programme_name"),
        "training_dates": voided_invoice.get("training_dates"),
        "venue": voided_invoice.get("venue"),
        "pax": voided_invoice.get("pax"),
        "line_items": voided_invoice.get("line_items", []),
        "subtotal": voided_invoice.get("subtotal", 0),
        "tax_rate": voided_invoice.get("tax_rate", 0),
        "tax_amount": voided_invoice.get("tax_amount", 0),
        "total_amount": voided_invoice.get("total_amount", 0),
        "discount": voided_invoice.get("discount", 0),
        "mobilisation_fee": voided_invoice.get("mobilisation_fee", 0),
        "rounding": voided_invoice.get("rounding", 0),
        "pricing_type": voided_invoice.get("pricing_type"),
        "bill_to_name": voided_invoice.get("bill_to_name"),
        "bill_to_address": voided_invoice.get("bill_to_address"),
        "bill_to_reg_no": voided_invoice.get("bill_to_reg_no"),
        "your_reference": voided_invoice.get("your_reference", ""),
        "status": "auto_draft",
        "replaces_invoice_id": invoice_id,
        "replaces_invoice_number": voided_invoice.get("invoice_number"),
        "created_at": get_malaysia_time().isoformat(),
        "updated_at": get_malaysia_time().isoformat(),
        "version": 1
    }
    
    await db.invoices.insert_one(replacement_invoice)
    
    # Update session with new invoice reference
    if voided_invoice.get("session_id"):
        await db.sessions.update_one(
            {"id": voided_invoice.get("session_id")},
            {"$set": {
                "invoice_id": replacement_invoice["id"],
                "invoice_number": new_invoice_number,
                "invoice_status": "auto_draft"
            }}
        )
    
    # Log the action
    await log_finance_action(
        entity_type="invoice",
        entity_id=replacement_invoice["id"],
        action="created",
        changed_by=current_user.id,
        after_value={"invoice_number": new_invoice_number, "replaces": voided_invoice.get("invoice_number")}
    )
    
    return {
        "message": "Replacement invoice created successfully",
        "new_invoice_id": replacement_invoice["id"],
        "new_invoice_number": new_invoice_number,
        "replaces_invoice_number": voided_invoice.get("invoice_number")
    }

# Reverse voided invoice back to draft
@api_router.post("/finance/invoices/{invoice_id}/reverse-void")
async def reverse_voided_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """Reverse a voided invoice back to draft status - Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can reverse voided invoices")
    
    # Get the voided invoice
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.get("status") != "voided":
        raise HTTPException(status_code=400, detail="Only voided invoices can be reversed")
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Invoice Void Reversed",
        record_reference=f"{invoice.get('company_name')} - {invoice.get('invoice_number')}",
        entity_type="invoice",
        entity_id=invoice_id,
        changed_by=current_user,
        reason="Void reversed by admin",
        field_changed="status",
        from_value="voided",
        to_value="auto_draft"
    )
    
    # Reverse the void - set back to draft and clear void fields
    await db.invoices.update_one(
        {"id": invoice_id},
        {
            "$set": {
                "status": "auto_draft",
                "updated_at": get_malaysia_time().isoformat()
            },
            "$unset": {
                "void_reason": "",
                "voided_at": "",
                "voided_by": "",
                "approved_at": "",
                "approved_by": "",
                "issued_at": "",
                "issued_by": ""
            }
        }
    )
    
    # Update session invoice_status if linked
    if invoice.get("session_id"):
        await db.sessions.update_one(
            {"id": invoice.get("session_id")},
            {"$set": {"invoice_status": "auto_draft"}}
        )
    
    return {
        "message": "Invoice void reversed successfully",
        "invoice_number": invoice.get("invoice_number"),
        "new_status": "auto_draft"
    }

# Edit Paid Invoice
class EditPaidInvoiceRequest(BaseModel):
    bill_to_name: Optional[str] = None
    bill_to_address: Optional[str] = None
    total_amount: Optional[float] = None
    reason: str

@api_router.put("/finance/admin/invoices/{invoice_id}/edit-paid")
async def edit_paid_invoice(
    invoice_id: str,
    request: EditPaidInvoiceRequest,
    current_user: User = Depends(get_current_user)
):
    """Edit a paid invoice - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can edit paid invoices")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the invoice
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    company_name = invoice.get("company_name", "Unknown")
    total_amount = invoice.get("total_amount", 0)
    record_ref = f"{company_name} - RM {total_amount:,.2f}"
    
    # Build update data
    update_data = {"updated_at": get_malaysia_time().isoformat()}
    changes = []
    
    if request.bill_to_name is not None and request.bill_to_name != invoice.get("bill_to_name"):
        changes.append(f"Bill To: {invoice.get('bill_to_name')} → {request.bill_to_name}")
        update_data["bill_to_name"] = request.bill_to_name
    
    if request.bill_to_address is not None and request.bill_to_address != invoice.get("bill_to_address"):
        changes.append(f"Address changed")
        update_data["bill_to_address"] = request.bill_to_address
    
    if request.total_amount is not None and request.total_amount != invoice.get("total_amount"):
        changes.append(f"Amount: RM {invoice.get('total_amount'):,.2f} → RM {request.total_amount:,.2f}")
        update_data["total_amount"] = request.total_amount
    
    if not changes:
        return {"message": "No changes detected"}
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Paid Invoice Edited",
        record_reference=record_ref,
        entity_type="invoice",
        entity_id=invoice_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="multiple",
        from_value="; ".join([c.split(" → ")[0] if " → " in c else c for c in changes]),
        to_value="; ".join([c.split(" → ")[1] if " → " in c else c for c in changes])
    )
    
    # Update the invoice
    await db.invoices.update_one({"id": invoice_id}, {"$set": update_data})
    
    return {"message": "Paid invoice updated successfully", "changes": changes}

# Delete Payment Record
class DeletePaymentRequest(BaseModel):
    reason: str

@api_router.delete("/finance/admin/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    request: DeletePaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Delete a payment record - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can delete payments")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the payment
    payment = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Get related invoice for reference
    invoice = await db.invoices.find_one({"id": payment.get("invoice_id")}, {"_id": 0})
    company_name = invoice.get("company_name", "Unknown") if invoice else "Unknown"
    
    record_ref = f"{company_name} - RM {payment.get('amount', 0):,.2f} ({payment.get('payment_method', 'Unknown')})"
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Payment Deleted",
        record_reference=record_ref,
        entity_type="payment",
        entity_id=payment_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="deleted",
        from_value=f"RM {payment.get('amount', 0):,.2f}",
        to_value="Deleted"
    )
    
    # Delete the payment
    await db.payments.delete_one({"id": payment_id})
    
    # Update invoice status if it was paid
    if invoice and invoice.get("status") == "paid":
        # Check if there are other payments for this invoice
        remaining_payments = await db.payments.count_documents({"invoice_id": invoice["id"]})
        if remaining_payments == 0:
            await db.invoices.update_one(
                {"id": invoice["id"]},
                {"$set": {"status": "issued", "updated_at": get_malaysia_time().isoformat()}}
            )
    
    return {"message": "Payment deleted successfully"}

# Backdate Invoice
class BackdateInvoiceRequest(BaseModel):
    new_date: str  # YYYY-MM-DD format
    reason: str

@api_router.put("/finance/admin/invoices/{invoice_id}/backdate")
async def backdate_invoice(
    invoice_id: str,
    request: BackdateInvoiceRequest,
    current_user: User = Depends(get_current_user)
):
    """Backdate an invoice - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can backdate invoices")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the invoice
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    company_name = invoice.get("company_name", "Unknown")
    total_amount = invoice.get("total_amount", 0)
    record_ref = f"{company_name} - RM {total_amount:,.2f}"
    
    # Get old date
    old_created_at = invoice.get("created_at")
    if isinstance(old_created_at, datetime):
        old_date = old_created_at.strftime("%Y-%m-%d")
    elif isinstance(old_created_at, str):
        old_date = old_created_at[:10]
    else:
        old_date = "Unknown"
    
    # Parse new date
    try:
        new_datetime = datetime.strptime(request.new_date, "%Y-%m-%d")
        new_datetime = new_datetime.replace(tzinfo=MALAYSIA_TZ)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Invoice Backdated",
        record_reference=record_ref,
        entity_type="invoice",
        entity_id=invoice_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="created_at",
        from_value=old_date,
        to_value=request.new_date
    )
    
    # Update the invoice date
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "created_at": new_datetime.isoformat(),
            "invoice_date": request.new_date,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Invoice backdated successfully", "old_date": old_date, "new_date": request.new_date}

# Reset Sequence Counter
class ResetSequenceRequest(BaseModel):
    year: int
    month: int
    new_sequence: int
    reason: str

@api_router.post("/finance/admin/sequence/reset")
async def reset_invoice_sequence(
    request: ResetSequenceRequest,
    current_user: User = Depends(get_current_user)
):
    """Reset invoice sequence counter - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can reset sequence")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    if request.new_sequence < 1:
        raise HTTPException(status_code=400, detail="Sequence must be at least 1")
    
    # Get current highest sequence for the month
    prefix = f"INV/MDDRC/{request.year}/{request.month:02d}/"
    last_invoice = await db.invoices.find_one(
        {"invoice_number": {"$regex": f"^{prefix}"}},
        sort=[("invoice_number", -1)]
    )
    
    current_sequence = 0
    if last_invoice:
        current_sequence = int(last_invoice["invoice_number"].split("/")[-1])
    
    # Store the sequence override in a settings collection
    await db.invoice_sequence_settings.update_one(
        {"year": request.year, "month": request.month},
        {
            "$set": {
                "next_sequence": request.new_sequence,
                "reset_by": current_user.id,
                "reset_at": get_malaysia_time().isoformat(),
                "reset_reason": request.reason
            }
        },
        upsert=True
    )
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Invoice Sequence Reset",
        record_reference=f"Sequence for {request.year}/{request.month:02d}",
        entity_type="sequence",
        entity_id=f"{request.year}-{request.month:02d}",
        changed_by=current_user,
        reason=request.reason,
        field_changed="next_sequence",
        from_value=str(current_sequence),
        to_value=str(request.new_sequence)
    )
    
    return {
        "message": "Sequence reset successfully",
        "year": request.year,
        "month": request.month,
        "old_sequence": current_sequence,
        "new_sequence": request.new_sequence
    }

# Get Audit Trail with filters
@api_router.get("/finance/admin/audit-trail")
async def get_admin_audit_trail(
    entity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get detailed audit trail - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can view audit trail")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = end_date + "T23:59:59"
        else:
            query["timestamp"] = {"$lte": end_date + "T23:59:59"}
    
    logs = await db.audit_trail.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    return logs

# Export Audit Trail as Excel
@api_router.get("/finance/admin/audit-trail/export")
async def export_audit_trail(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Export audit trail as Excel - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can export audit trail")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    query = {}
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = end_date + "T23:59:59"
        else:
            query["timestamp"] = {"$lte": end_date + "T23:59:59"}
    
    logs = await db.audit_trail.find(query, {"_id": 0}).sort("timestamp", -1).to_list(5000)
    
    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Audit Trail"
    
    # Headers
    headers = ["Date/Time", "Action", "Record", "Field Changed", "From", "To", "Changed By", "Email", "Reason"]
    ws.append(headers)
    
    # Style headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
    
    # Data rows
    for log in logs:
        timestamp = log.get("timestamp", "")
        if isinstance(timestamp, str):
            # Format: DD MMM YYYY, HH:MM:SS
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%d %b %Y, %H:%M:%S")
            except:
                pass
        
        ws.append([
            timestamp,
            log.get("action", ""),
            log.get("record_reference", ""),
            log.get("field_changed", ""),
            log.get("from_value", ""),
            log.get("to_value", ""),
            log.get("changed_by_name", ""),
            log.get("changed_by_email", ""),
            log.get("reason", "")
        ])
    
    # Auto-width columns
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Audit_Trail_{get_malaysia_time().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ============ EXCEL TEMPLATES FOR BULK UPLOAD ============

@api_router.get("/templates/pre-post-assessment")
async def download_assessment_template(current_user: User = Depends(get_current_user)):
    """Download Excel template for Pre/Post Assessment bulk upload"""
    if current_user.role not in ["admin", "trainer", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pre-Post Assessment"
    
    # Headers
    headers = [
        "participant_ic",          # Required - IC number to identify participant
        "participant_name",        # Optional - for reference
        "test_type",              # Required - "pre" or "post"
        "correct_answers",        # Required - number of correct answers
        "total_questions",        # Required - total number of questions
        "score_percentage",       # Auto-calculated - for reference only
        "passed",                 # Auto-calculated - for reference only
        "session_name",           # Optional - for reference
        "notes"                   # Optional - any additional notes
    ]
    ws.append(headers)
    
    # Style headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
    
    # Sample data rows
    sample_data = [
        ["871128385485", "Ahmad Bin Ali", "pre", 36, 40, "=D2/E2*100", "=IF(F2>=70,\"PASS\",\"FAIL\")", "KONE Training Session", "Morning batch"],
        ["880215143265", "Siti Binti Hassan", "pre", 28, 40, "=D3/E3*100", "=IF(F3>=70,\"PASS\",\"FAIL\")", "KONE Training Session", ""],
        ["871128385485", "Ahmad Bin Ali", "post", 38, 40, "=D4/E4*100", "=IF(F4>=70,\"PASS\",\"FAIL\")", "KONE Training Session", "Improved from pre-test"],
        ["880215143265", "Siti Binti Hassan", "post", 35, 40, "=D5/E5*100", "=IF(F5>=70,\"PASS\",\"FAIL\")", "KONE Training Session", ""],
    ]
    
    for row in sample_data:
        ws.append(row)
    
    # Instructions sheet
    ws_inst = wb.create_sheet("Instructions")
    instructions = [
        ["PRE/POST ASSESSMENT BULK UPLOAD TEMPLATE"],
        [""],
        ["REQUIRED COLUMNS:"],
        ["participant_ic", "IC Number of participant (must exist in system)"],
        ["test_type", "Either 'pre' or 'post'"],
        ["correct_answers", "Number of correct answers (e.g., 36)"],
        ["total_questions", "Total questions in test (e.g., 40)"],
        [""],
        ["OPTIONAL COLUMNS:"],
        ["participant_name", "Name for reference only"],
        ["score_percentage", "Auto-calculated: (correct/total)*100"],
        ["passed", "Auto-calculated: PASS if >=70%, FAIL otherwise"],
        ["session_name", "Session reference"],
        ["notes", "Any additional notes"],
        [""],
        ["NOTES:"],
        ["- Same participant can have both PRE and POST test entries"],
        ["- System will calculate percentage and pass/fail automatically"],
        ["- Passing mark is 70%"],
        ["- Delete sample rows before uploading your data"],
    ]
    for row in instructions:
        ws_inst.append(row)
    
    # Auto-width columns
    for ws_sheet in [ws, ws_inst]:
        for column in ws_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws_sheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=PrePost_Assessment_Template.xlsx"}
    )

@api_router.get("/templates/feedback")
async def download_feedback_template(current_user: User = Depends(get_current_user)):
    """Download Excel template for Feedback bulk upload"""
    if current_user.role not in ["admin", "trainer", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Feedback"
    
    # Headers - Generic feedback questions
    headers = [
        "participant_ic",           # Required
        "participant_name",         # Optional - for reference
        "session_name",            # Optional - for reference
        "q1_course_content",       # Rating 1-5: Course content quality
        "q2_trainer_knowledge",    # Rating 1-5: Trainer's knowledge
        "q3_trainer_delivery",     # Rating 1-5: Trainer's delivery style
        "q4_training_materials",   # Rating 1-5: Training materials quality
        "q5_practical_sessions",   # Rating 1-5: Practical session effectiveness
        "q6_facilities",           # Rating 1-5: Training facilities
        "q7_time_management",      # Rating 1-5: Time management
        "q8_overall_satisfaction", # Rating 1-5: Overall satisfaction
        "q9_recommend_others",     # Yes/No: Would recommend to others
        "q10_comments",            # Text: Additional comments/suggestions
    ]
    ws.append(headers)
    
    # Style headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
    
    # Sample data
    sample_data = [
        ["871128385485", "Ahmad Bin Ali", "KONE Training", 5, 5, 4, 5, 5, 4, 5, 5, "Yes", "Excellent training program!"],
        ["880215143265", "Siti Binti Hassan", "KONE Training", 4, 5, 5, 4, 4, 4, 4, 4, "Yes", "More practical sessions would be better."],
    ]
    
    for row in sample_data:
        ws.append(row)
    
    # Instructions sheet
    ws_inst = wb.create_sheet("Instructions")
    instructions = [
        ["FEEDBACK BULK UPLOAD TEMPLATE"],
        [""],
        ["REQUIRED COLUMNS:"],
        ["participant_ic", "IC Number of participant (must exist in system)"],
        [""],
        ["RATING COLUMNS (1-5 scale):"],
        ["q1_course_content", "Rate course content quality (1=Poor, 5=Excellent)"],
        ["q2_trainer_knowledge", "Rate trainer's subject knowledge"],
        ["q3_trainer_delivery", "Rate trainer's delivery and presentation"],
        ["q4_training_materials", "Rate quality of training materials"],
        ["q5_practical_sessions", "Rate practical/hands-on sessions"],
        ["q6_facilities", "Rate training facilities"],
        ["q7_time_management", "Rate time management during training"],
        ["q8_overall_satisfaction", "Rate overall satisfaction"],
        [""],
        ["OTHER COLUMNS:"],
        ["q9_recommend_others", "Would recommend to others? (Yes/No)"],
        ["q10_comments", "Additional comments or suggestions (text)"],
        [""],
        ["RATING SCALE:"],
        ["1 = Poor"],
        ["2 = Fair"],
        ["3 = Good"],
        ["4 = Very Good"],
        ["5 = Excellent"],
        [""],
        ["NOTES:"],
        ["- Delete sample rows before uploading your data"],
        ["- All rating columns should be numbers 1-5"],
    ]
    for row in instructions:
        ws_inst.append(row)
    
    # Auto-width
    for ws_sheet in [ws, ws_inst]:
        for column in ws_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws_sheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Feedback_Template.xlsx"}
    )

@api_router.get("/templates/checklist")
async def download_checklist_template(current_user: User = Depends(get_current_user)):
    """Download Excel template for Vehicle Checklist bulk upload"""
    if current_user.role not in ["admin", "trainer", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Vehicle Checklist"
    
    # Headers - Standard vehicle checklist items
    headers = [
        "participant_ic",          # Required
        "participant_name",        # Optional
        "session_name",           # Optional
        "vehicle_model",          # Vehicle details
        "registration_number",
        "roadtax_expiry",         # YYYY-MM-DD format
        # Checklist items with status (good/satisfactory/needs_repair)
        "tyres_condition",
        "tyres_comments",
        "brakes_condition",
        "brakes_comments",
        "lights_condition",
        "lights_comments",
        "horn_condition",
        "horn_comments",
        "mirrors_condition",
        "mirrors_comments",
        "steering_condition",
        "steering_comments",
        "windscreen_condition",
        "windscreen_comments",
        "wipers_condition",
        "wipers_comments",
        "seatbelt_condition",
        "seatbelt_comments",
        "engine_condition",
        "engine_comments",
        "overall_remarks",
    ]
    ws.append(headers)
    
    # Style headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="ED7D31", end_color="ED7D31", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
    
    # Sample data
    sample_data = [
        ["871128385485", "Ahmad Bin Ali", "KONE Training", "Honda City", "WMY1234", "2026-06-30",
         "good", "", "good", "", "good", "", "good", "", "good", "", 
         "good", "", "satisfactory", "Minor scratch", "good", "", "good", "", "good", "", "Vehicle in good condition"],
        ["880215143265", "Siti Binti Hassan", "KONE Training", "Toyota Vios", "BKA5678", "2026-08-15",
         "good", "", "needs_repair", "Brake pads worn", "good", "", "good", "", "good", "",
         "good", "", "good", "", "good", "", "good", "", "satisfactory", "Minor noise", "Needs brake service"],
    ]
    
    for row in sample_data:
        ws.append(row)
    
    # Instructions sheet
    ws_inst = wb.create_sheet("Instructions")
    instructions = [
        ["VEHICLE CHECKLIST BULK UPLOAD TEMPLATE"],
        [""],
        ["REQUIRED COLUMNS:"],
        ["participant_ic", "IC Number of participant (must exist in system)"],
        [""],
        ["VEHICLE DETAILS:"],
        ["vehicle_model", "Vehicle make and model (e.g., Honda City)"],
        ["registration_number", "Vehicle registration number"],
        ["roadtax_expiry", "Road tax expiry date (YYYY-MM-DD format)"],
        [""],
        ["CHECKLIST ITEM STATUS VALUES:"],
        ["good", "Item is in good working condition"],
        ["satisfactory", "Item is acceptable but may need attention"],
        ["needs_repair", "Item requires repair/replacement"],
        [""],
        ["CHECKLIST ITEMS:"],
        ["tyres_condition/comments", "Tyre condition and any comments"],
        ["brakes_condition/comments", "Brake system condition"],
        ["lights_condition/comments", "All lights (head, tail, signal)"],
        ["horn_condition/comments", "Horn functionality"],
        ["mirrors_condition/comments", "Side and rear mirrors"],
        ["steering_condition/comments", "Steering system"],
        ["windscreen_condition/comments", "Windscreen condition"],
        ["wipers_condition/comments", "Windscreen wipers"],
        ["seatbelt_condition/comments", "Seatbelt functionality"],
        ["engine_condition/comments", "Engine performance"],
        [""],
        ["NOTES:"],
        ["- Delete sample rows before uploading your data"],
        ["- Comments are required for 'needs_repair' status"],
        ["- Date format must be YYYY-MM-DD"],
    ]
    for row in instructions:
        ws_inst.append(row)
    
    # Auto-width
    for ws_sheet in [ws, ws_inst]:
        for column in ws_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws_sheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Vehicle_Checklist_Template.xlsx"}
    )

# ============ PROGRAM CONFIGURATION TEMPLATES (Master Files) ============

@api_router.get("/templates/program-test-questions")
async def download_test_questions_template(current_user: User = Depends(get_current_user)):
    """Download Excel template for Pre/Post Test Questions (Program Configuration)"""
    if current_user.role not in ["admin", "trainer", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Test Questions"
    
    # Headers for test questions
    headers = [
        "program_name",           # For reference
        "test_type",              # "pre" or "post" (same questions usually)
        "question_number",        # 1, 2, 3...
        "question_text",          # The actual question
        "option_1",               # First answer option
        "option_2",               # Second answer option
        "option_3",               # Third answer option
        "option_4",               # Fourth answer option
        "correct_answer",         # 1, 2, 3, or 4 (which option is correct)
    ]
    ws.append(headers)
    
    # Style headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
    
    # Sample data - Defensive Driving questions
    sample_data = [
        ["Defensive Driving", "pre", 1, "What is the safest following distance in normal conditions?", "1 second", "2 seconds", "3 seconds", "4 seconds", 3],
        ["Defensive Driving", "pre", 2, "When should you use your hazard lights?", "When parking illegally", "When your vehicle breaks down", "When driving slowly", "When it's raining", 2],
        ["Defensive Driving", "pre", 3, "What does a yellow traffic light mean?", "Speed up", "Stop if safe to do so", "Continue at same speed", "Honk your horn", 2],
        ["Defensive Driving", "pre", 4, "What is the first thing to check before changing lanes?", "Speedometer", "Mirrors and blind spots", "Radio", "Air conditioning", 2],
        ["Defensive Driving", "pre", 5, "In wet conditions, you should:", "Drive faster to clear water", "Maintain normal speed", "Reduce speed and increase following distance", "Use high beam lights", 3],
    ]
    
    for row in sample_data:
        ws.append(row)
    
    # Instructions sheet
    ws_inst = wb.create_sheet("Instructions")
    instructions = [
        ["PRE/POST TEST QUESTIONS TEMPLATE (PROGRAM CONFIGURATION)"],
        [""],
        ["PURPOSE:"],
        ["This template is for creating/restoring TEST QUESTIONS for a program."],
        ["Use this to quickly re-upload your test questions after redeployment."],
        [""],
        ["COLUMNS:"],
        ["program_name", "Name of the program (for your reference)"],
        ["test_type", "'pre' or 'post' - typically same questions for both"],
        ["question_number", "Question sequence number (1, 2, 3...)"],
        ["question_text", "The full question text"],
        ["option_1 to option_4", "Four answer options"],
        ["correct_answer", "Number 1-4 indicating which option is correct"],
        [""],
        ["HOW TO USE:"],
        ["1. Fill in your questions following the sample format"],
        ["2. Save this file locally as your master copy"],
        ["3. After redeployment, go to Programs tab → Edit Program → Tests"],
        ["4. Add questions manually using this file as reference"],
        ["   (or use bulk upload if available)"],
        [""],
        ["TIPS:"],
        ["- Keep questions clear and concise"],
        ["- Ensure only ONE correct answer per question"],
        ["- Use consistent formatting for all options"],
        ["- Recommended: 20-40 questions per program"],
        ["- Delete sample rows and add your own questions"],
    ]
    for row in instructions:
        ws_inst.append(row)
    
    # Auto-width
    for ws_sheet in [ws, ws_inst]:
        for column in ws_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws_sheet.column_dimensions[column_letter].width = min(max_length + 2, 60)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Program_Test_Questions_Template.xlsx"}
    )

@api_router.get("/templates/program-feedback-questions")
async def download_feedback_questions_template(current_user: User = Depends(get_current_user)):
    """Download Excel template for Feedback Questions (Program Configuration)"""
    if current_user.role not in ["admin", "trainer", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Feedback Questions"
    
    # Headers
    headers = [
        "program_name",           # For reference
        "question_number",        # 1, 2, 3...
        "question_text",          # The feedback question
        "question_type",          # "rating" (1-5 scale) or "text" (free text)
        "required",               # "yes" or "no"
    ]
    ws.append(headers)
    
    # Style headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
    
    # Sample data - Standard feedback questions
    sample_data = [
        ["Defensive Driving", 1, "How would you rate the overall quality of the training program?", "rating", "yes"],
        ["Defensive Driving", 2, "How knowledgeable was the trainer on the subject matter?", "rating", "yes"],
        ["Defensive Driving", 3, "How effective was the trainer's delivery and presentation style?", "rating", "yes"],
        ["Defensive Driving", 4, "How useful were the training materials provided?", "rating", "yes"],
        ["Defensive Driving", 5, "How effective were the practical/hands-on sessions?", "rating", "yes"],
        ["Defensive Driving", 6, "How would you rate the training facilities and environment?", "rating", "yes"],
        ["Defensive Driving", 7, "How well was the training time managed?", "rating", "yes"],
        ["Defensive Driving", 8, "How likely are you to recommend this training to others?", "rating", "yes"],
        ["Defensive Driving", 9, "What did you find most valuable about this training?", "text", "no"],
        ["Defensive Driving", 10, "What suggestions do you have for improving this training?", "text", "no"],
    ]
    
    for row in sample_data:
        ws.append(row)
    
    # Instructions sheet
    ws_inst = wb.create_sheet("Instructions")
    instructions = [
        ["FEEDBACK QUESTIONS TEMPLATE (PROGRAM CONFIGURATION)"],
        [""],
        ["PURPOSE:"],
        ["This template is for creating/restoring FEEDBACK QUESTIONS for a program."],
        ["Use this to quickly re-create your feedback form after redeployment."],
        [""],
        ["COLUMNS:"],
        ["program_name", "Name of the program (for your reference)"],
        ["question_number", "Question sequence (1, 2, 3...)"],
        ["question_text", "The feedback question text"],
        ["question_type", "'rating' = 1-5 scale, 'text' = free text answer"],
        ["required", "'yes' = must answer, 'no' = optional"],
        [""],
        ["QUESTION TYPES:"],
        ["rating", "Participant selects 1-5 (1=Poor, 5=Excellent)"],
        ["text", "Participant types free-form answer"],
        [""],
        ["HOW TO USE:"],
        ["1. Customize questions for your program"],
        ["2. Save this file locally as your master copy"],
        ["3. After redeployment, go to Feedback tab → Create Template"],
        ["4. Add questions using this file as reference"],
        [""],
        ["RECOMMENDED STRUCTURE:"],
        ["- 6-8 rating questions covering key aspects"],
        ["- 1-2 text questions for open feedback"],
        ["- Keep questions clear and specific"],
        ["- Delete sample rows and add your own questions"],
    ]
    for row in instructions:
        ws_inst.append(row)
    
    # Auto-width
    for ws_sheet in [ws, ws_inst]:
        for column in ws_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws_sheet.column_dimensions[column_letter].width = min(max_length + 2, 60)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Program_Feedback_Questions_Template.xlsx"}
    )

@api_router.get("/templates/program-checklist-items")
async def download_checklist_items_template(current_user: User = Depends(get_current_user)):
    """Download Excel template for Checklist Items (Program Configuration)"""
    if current_user.role not in ["admin", "trainer", "assistant_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Checklist Items"
    
    # Headers
    headers = [
        "program_name",           # For reference
        "item_number",            # 1, 2, 3...
        "checklist_item",         # The item to check
        "category",               # Optional: group items by category
    ]
    ws.append(headers)
    
    # Style headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="ED7D31", end_color="ED7D31", fill_type="solid")
        cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
    
    # Sample data - Vehicle checklist items
    sample_data = [
        ["Defensive Driving", 1, "Tyres - Check tread depth and pressure", "Exterior"],
        ["Defensive Driving", 2, "Tyres - Check for damage or bulges", "Exterior"],
        ["Defensive Driving", 3, "Brakes - Test brake pedal feel", "Safety"],
        ["Defensive Driving", 4, "Brakes - Check handbrake operation", "Safety"],
        ["Defensive Driving", 5, "Lights - Headlights (low and high beam)", "Lights"],
        ["Defensive Driving", 6, "Lights - Tail lights and brake lights", "Lights"],
        ["Defensive Driving", 7, "Lights - Turn signals (front and rear)", "Lights"],
        ["Defensive Driving", 8, "Lights - Hazard lights", "Lights"],
        ["Defensive Driving", 9, "Horn - Test horn functionality", "Safety"],
        ["Defensive Driving", 10, "Mirrors - Side mirrors condition and adjustment", "Visibility"],
        ["Defensive Driving", 11, "Mirrors - Rear view mirror condition", "Visibility"],
        ["Defensive Driving", 12, "Windscreen - Check for cracks or chips", "Visibility"],
        ["Defensive Driving", 13, "Wipers - Front wiper operation", "Visibility"],
        ["Defensive Driving", 14, "Wipers - Rear wiper operation (if equipped)", "Visibility"],
        ["Defensive Driving", 15, "Seatbelts - Driver seatbelt condition", "Safety"],
        ["Defensive Driving", 16, "Seatbelts - Passenger seatbelts", "Safety"],
        ["Defensive Driving", 17, "Steering - Check for play or stiffness", "Controls"],
        ["Defensive Driving", 18, "Engine - Check for unusual sounds", "Engine"],
        ["Defensive Driving", 19, "Engine - Oil level", "Engine"],
        ["Defensive Driving", 20, "Coolant - Check coolant level", "Engine"],
    ]
    
    for row in sample_data:
        ws.append(row)
    
    # Instructions sheet
    ws_inst = wb.create_sheet("Instructions")
    instructions = [
        ["CHECKLIST ITEMS TEMPLATE (PROGRAM CONFIGURATION)"],
        [""],
        ["PURPOSE:"],
        ["This template is for creating/restoring CHECKLIST ITEMS for a program."],
        ["Use this to quickly re-create your vehicle inspection checklist after redeployment."],
        [""],
        ["COLUMNS:"],
        ["program_name", "Name of the program (for your reference)"],
        ["item_number", "Item sequence (1, 2, 3...)"],
        ["checklist_item", "The item to be inspected"],
        ["category", "Optional grouping (Exterior, Safety, Lights, etc.)"],
        [""],
        ["HOW TO USE:"],
        ["1. List all inspection items for your program"],
        ["2. Save this file locally as your master copy"],
        ["3. After redeployment, go to Checklist Templates tab → Create"],
        ["4. Add items using this file as reference"],
        [""],
        ["RECOMMENDED CATEGORIES:"],
        ["Exterior", "Body, tyres, paint"],
        ["Safety", "Brakes, seatbelts, horn"],
        ["Lights", "All vehicle lights"],
        ["Visibility", "Mirrors, windscreen, wipers"],
        ["Controls", "Steering, pedals, gear"],
        ["Engine", "Oil, coolant, sounds"],
        [""],
        ["TIPS:"],
        ["- Be specific about what to check"],
        ["- Group related items together"],
        ["- 15-25 items is typical for vehicle inspection"],
        ["- Delete sample rows and add your own items"],
    ]
    for row in instructions:
        ws_inst.append(row)
    
    # Auto-width
    for ws_sheet in [ws, ws_inst]:
        for column in ws_sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws_sheet.column_dimensions[column_letter].width = min(max_length + 2, 60)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Program_Checklist_Items_Template.xlsx"}
    )

# Override Validation - Edit invoice without amount checks
class OverrideValidationRequest(BaseModel):
    total_amount: float
    reason: str
    skip_validation: bool = True

@api_router.put("/finance/admin/invoices/{invoice_id}/override")
async def override_invoice_validation(
    invoice_id: str,
    request: OverrideValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """Override invoice amount without validation - Super Admin/Finance only"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can override validation")
    
    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    # Get the invoice
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    company_name = invoice.get("company_name", "Unknown")
    old_amount = invoice.get("total_amount", 0)
    record_ref = f"{company_name} - RM {old_amount:,.2f}"
    
    # Create audit trail entry
    await create_audit_trail_entry(
        action="Invoice Amount Override",
        record_reference=record_ref,
        entity_type="invoice",
        entity_id=invoice_id,
        changed_by=current_user,
        reason=request.reason,
        field_changed="total_amount",
        from_value=f"RM {old_amount:,.2f}",
        to_value=f"RM {request.total_amount:,.2f}"
    )
    
    # Update the invoice amount directly
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "total_amount": request.total_amount,
            "validation_overridden": True,
            "override_reason": request.reason,
            "overridden_by": current_user.id,
            "overridden_at": get_malaysia_time().isoformat(),
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {
        "message": "Invoice amount overridden successfully",
        "old_amount": old_amount,
        "new_amount": request.total_amount
    }

# Get all invoices for admin management
@api_router.get("/finance/admin/invoices")
async def get_admin_invoices(
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all invoices for admin management"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can access")
    
    query = {}
    if status and status != "all":
        query["status"] = status
    if search:
        query["$or"] = [
            {"invoice_number": {"$regex": search, "$options": "i"}},
            {"company_name": {"$regex": search, "$options": "i"}}
        ]
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return invoices

# Get all payments for admin management
@api_router.get("/finance/admin/payments")
async def get_admin_payments(
    invoice_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all payments for admin management"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin and Finance can access")
    
    query = {}
    if invoice_id:
        query["invoice_id"] = invoice_id
    
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Enrich with invoice data
    for payment in payments:
        invoice = await db.invoices.find_one({"id": payment.get("invoice_id")}, {"_id": 0})
        if invoice:
            payment["invoice_number"] = invoice.get("invoice_number")
            payment["company_name"] = invoice.get("company_name")
    
    return payments

# =====================================================
# HR & PAYROLL MODULE
# =====================================================

# Staff Management
@api_router.get("/hr/staff")
async def get_staff(current_user: User = Depends(get_current_user)):
    """Get all staff records with user details"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    staff_records = await db.hr_staff.find({}, {"_id": 0}).to_list(500)
    
    # Enrich with user data
    for staff in staff_records:
        if staff.get("user_id"):
            user = await db.users.find_one({"id": staff["user_id"]}, {"_id": 0, "full_name": 1, "email": 1, "id_number": 1})
            if user:
                staff["full_name"] = user.get("full_name") or staff.get("full_name")
                staff["email"] = user.get("email")
                # Use id_number as nric if not already set
                if not staff.get("nric"):
                    staff["nric"] = user.get("id_number", "")
    
    return staff_records

@api_router.post("/hr/staff")
async def create_staff(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new staff record"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can manage staff")
    
    staff_id = str(uuid.uuid4())
    
    # Get user info if user_id provided
    full_name = None
    if data.get("user_id"):
        user = await db.users.find_one({"id": data["user_id"]}, {"_id": 0, "full_name": 1})
        full_name = user.get("full_name") if user else None
    
    staff_record = {
        "id": staff_id,
        "user_id": data.get("user_id"),
        "employee_id": data.get("employee_id"),
        "full_name": full_name or data.get("full_name", ""),
        "nric": data.get("nric", ""),
        "designation": data.get("designation", ""),
        "department": data.get("department", ""),
        "date_joined": data.get("date_joined"),
        "date_of_birth": data.get("date_of_birth"),
        "bank_name": data.get("bank_name", ""),
        "bank_account": data.get("bank_account", ""),
        "basic_salary": float(data.get("basic_salary", 0)),
        "housing_allowance": float(data.get("housing_allowance", 0)),
        "transport_allowance": float(data.get("transport_allowance", 0)),
        "meal_allowance": float(data.get("meal_allowance", 0)),
        "phone_allowance": float(data.get("phone_allowance", 0)),
        "other_allowance": float(data.get("other_allowance", 0)),
        "epf_number": data.get("epf_number", ""),
        "socso_number": data.get("socso_number", ""),
        "tax_number": data.get("tax_number", ""),
        "employee_epf_rate": float(data.get("employee_epf_rate", 11)),
        "employer_epf_rate": float(data.get("employer_epf_rate", 13)),
        "is_active": data.get("is_active", True),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_staff.insert_one(staff_record)
    return {"id": staff_id, "message": "Staff created successfully"}

@api_router.put("/hr/staff/{staff_id}")
async def update_staff(staff_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a staff record"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can manage staff")
    
    
    existing = await db.hr_staff.find_one({"id": staff_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    update_data = {
        "employee_id": data.get("employee_id", existing.get("employee_id")),
        "nric": data.get("nric", existing.get("nric", "")),
        "designation": data.get("designation", existing.get("designation")),
        "department": data.get("department", existing.get("department")),
        "date_joined": data.get("date_joined", existing.get("date_joined")),
        "date_of_birth": data.get("date_of_birth", existing.get("date_of_birth")),
        "bank_name": data.get("bank_name", existing.get("bank_name")),
        "bank_account": data.get("bank_account", existing.get("bank_account")),
        "basic_salary": float(data.get("basic_salary", existing.get("basic_salary", 0))),
        "housing_allowance": float(data.get("housing_allowance", existing.get("housing_allowance", 0))),
        "transport_allowance": float(data.get("transport_allowance", existing.get("transport_allowance", 0))),
        "meal_allowance": float(data.get("meal_allowance", existing.get("meal_allowance", 0))),
        "phone_allowance": float(data.get("phone_allowance", existing.get("phone_allowance", 0))),
        "other_allowance": float(data.get("other_allowance", existing.get("other_allowance", 0))),
        "epf_number": data.get("epf_number", existing.get("epf_number")),
        "socso_number": data.get("socso_number", existing.get("socso_number")),
        "tax_number": data.get("tax_number", existing.get("tax_number")),
        "employee_epf_rate": float(data.get("employee_epf_rate", existing.get("employee_epf_rate", 11))),
        "employer_epf_rate": float(data.get("employer_epf_rate", existing.get("employer_epf_rate", 13))),
        "is_active": data.get("is_active", existing.get("is_active", True)),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.hr_staff.update_one({"id": staff_id}, {"$set": update_data})
    return {"message": "Staff updated successfully"}

@api_router.delete("/hr/staff/{staff_id}")
async def delete_staff(staff_id: str, current_user: User = Depends(get_current_user)):
    """Delete a staff record"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can manage staff")
    
    result = await db.hr_staff.delete_one({"id": staff_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    return {"message": "Staff deleted successfully"}

# Get users available to link as staff
@api_router.get("/hr/available-users")
async def get_available_users(current_user: User = Depends(get_current_user)):
    """Get users that can be linked as staff (coordinators, trainers, admin)"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get existing staff user IDs
    existing_staff = await db.hr_staff.find({}, {"user_id": 1}).to_list(500)
    existing_user_ids = [s.get("user_id") for s in existing_staff if s.get("user_id")]
    
    # Get eligible users not yet linked
    users = await db.users.find(
        {
            "role": {"$in": ["trainer", "coordinator", "assistant_admin", "admin"]},
            "id": {"$nin": existing_user_ids}
        },
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1, "id_number": 1}
    ).to_list(200)
    
    return users

# =====================================================
# PAYROLL PERIOD MANAGEMENT
# =====================================================

@api_router.get("/hr/payroll-periods")
async def get_payroll_periods(year: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get all payroll periods"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        query["year"] = year
    
    periods = await db.payroll_periods.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return periods

@api_router.post("/hr/payroll-periods")
async def create_payroll_period(data: dict, current_user: User = Depends(get_current_user)):
    """Create or open a payroll period for a month"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can manage payroll periods")
    
    year = data.get("year")
    month = data.get("month")
    
    if not year or not month:
        raise HTTPException(status_code=400, detail="Year and month required")
    
    # Check if period already exists
    existing = await db.payroll_periods.find_one({"year": year, "month": month})
    if existing:
        raise HTTPException(status_code=400, detail="Payroll period already exists")
    
    period = {
        "id": str(uuid.uuid4()),
        "year": year,
        "month": month,
        "period_name": f"{year}-{str(month).zfill(2)}",
        "status": "open",  # open, closed
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "opened_by": current_user.email,
        "closed_at": None,
        "closed_by": None
    }
    
    await db.payroll_periods.insert_one(period)
    return {"id": period["id"], "message": "Payroll period created"}

@api_router.put("/hr/payroll-periods/{period_id}/close")
async def close_payroll_period(period_id: str, current_user: User = Depends(get_current_user)):
    """Close a payroll period - makes all payslips read-only"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can close payroll periods")
    
    period = await db.payroll_periods.find_one({"id": period_id})
    if not period:
        raise HTTPException(status_code=404, detail="Payroll period not found")
    
    if period.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Period already closed")
    
    await db.payroll_periods.update_one(
        {"id": period_id},
        {"$set": {
            "status": "closed",
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "closed_by": current_user.email
        }}
    )
    
    # Also lock all payslips for this period
    await db.payslips.update_many(
        {"period_id": period_id},
        {"$set": {"is_locked": True}}
    )
    
    return {"message": "Payroll period closed successfully"}

# =====================================================
# STATUTORY CONTRIBUTION CALCULATOR
# =====================================================

def calculate_age_from_nric(nric: str, reference_date: str = None) -> int:
    """Calculate age from Malaysian NRIC (first 6 digits = YYMMDD)"""
    if not nric or len(nric) < 6:
        return 30  # Default
    
    try:
        # Extract YYMMDD
        yy = int(nric[:2])
        mm = int(nric[2:4])
        dd = int(nric[4:6])
        
        # Determine century (if YY > 30, assume 1900s, else 2000s)
        current_year = datetime.now().year
        current_yy = current_year % 100
        
        if yy > current_yy + 5:  # e.g., 85 > 31, so 1985
            year = 1900 + yy
        else:
            year = 2000 + yy
        
        dob = datetime(year, mm, dd)
        ref = datetime.fromisoformat(reference_date) if reference_date else datetime.now()
        age = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
        return max(18, min(age, 100))  # Clamp between 18-100
    except:
        return 30

async def get_statutory_rates_from_db(rate_type: str, wages: float):
    """Get statutory rates from uploaded Excel tables"""
    # Find the rate bracket for given wages
    rate = await db.statutory_rates.find_one({
        "rate_type": rate_type,
        "min_wages": {"$lte": wages},
        "max_wages": {"$gte": wages}
    }, {"_id": 0})
    return rate

def calculate_epf(basic_salary: float, age: int, custom_employee_rate: float = None, custom_employer_rate: float = None):
    """Calculate EPF contributions based on salary and age"""
    # Age 60 and above: Employer 4%, Employee 0% (voluntary)
    if age >= 60:
        employer_rate = 4.0
        employee_rate = 0.0
    else:
        # Below 60: Standard rates
        # Employer: 13% if salary <= 5000, 12% if > 5000
        employer_rate = custom_employer_rate if custom_employer_rate else (13.0 if basic_salary <= 5000 else 12.0)
        employee_rate = custom_employee_rate if custom_employee_rate else 11.0
    
    employee_amount = round(basic_salary * employee_rate / 100, 2)
    employer_amount = round(basic_salary * employer_rate / 100, 2)
    
    return {
        "employee_rate": employee_rate,
        "employer_rate": employer_rate,
        "employee_amount": employee_amount,
        "employer_amount": employer_amount
    }

def calculate_socso(wages: float, age: int):
    """Calculate SOCSO contributions based on wages and age
    Uses SOCSO contribution table (Act 4) - wage ceiling RM6,000
    """
    # Cap wages at RM6,000
    capped_wages = min(wages, 6000)
    
    # Simplified SOCSO rates (approximate based on tables)
    # Full rates from PERKESO tables would be used in production
    if age >= 60:
        # Second Category: Only employer contributes (Invalidity Scheme only)
        employer_rate = 1.25
        employee_rate = 0.0
    else:
        # First Category: Both contribute
        employer_rate = 1.75  # Approximate
        employee_rate = 0.5   # Approximate
    
    employee_amount = round(capped_wages * employee_rate / 100, 2)
    employer_amount = round(capped_wages * employer_rate / 100, 2)
    
    return {
        "employee_rate": employee_rate,
        "employer_rate": employer_rate,
        "employee_amount": employee_amount,
        "employer_amount": employer_amount,
        "capped_wages": capped_wages
    }

def calculate_eis(wages: float, age: int):
    """Calculate EIS contributions
    Rate: 0.2% each for employer and employee
    Wage ceiling: RM6,000
    Age 60+: No contribution
    """
    if age >= 60:
        return {
            "employee_rate": 0.0,
            "employer_rate": 0.0,
            "employee_amount": 0.0,
            "employer_amount": 0.0,
            "capped_wages": 0
        }
    
    # Cap wages at RM6,000
    capped_wages = min(wages, 6000)
    
    employee_rate = 0.2
    employer_rate = 0.2
    
    employee_amount = round(capped_wages * employee_rate / 100, 2)
    employer_amount = round(capped_wages * employer_rate / 100, 2)
    
    return {
        "employee_rate": employee_rate,
        "employer_rate": employer_rate,
        "employee_amount": employee_amount,
        "employer_amount": employer_amount,
        "capped_wages": capped_wages
    }

def calculate_age(date_of_birth: str, reference_date: str = None) -> int:
    """Calculate age from date of birth"""
    if not date_of_birth:
        return 30  # Default assumption
    
    try:
        dob = datetime.fromisoformat(date_of_birth.replace('Z', '+00:00'))
        ref = datetime.fromisoformat(reference_date) if reference_date else datetime.now()
        age = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
        return age
    except:
        return 30

# =====================================================
# STATUTORY RATES UPLOAD (Excel)
# =====================================================

@api_router.post("/hr/statutory-rates/upload")
async def upload_statutory_rates(
    file: UploadFile = File(...),
    rate_type: str = Form(...),  # epf, socso, eis
    current_user: User = Depends(get_current_user)
):
    """Upload Excel file with statutory contribution rates"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can upload statutory rates")
    
    if rate_type not in ["epf", "socso", "eis"]:
        raise HTTPException(status_code=400, detail="rate_type must be epf, socso, or eis")
    
    try:
        import openpyxl
        from io import BytesIO
        
        contents = await file.read()
        wb = openpyxl.load_workbook(BytesIO(contents))
        ws = wb.active
        
        # Delete existing rates for this type
        await db.statutory_rates.delete_many({"rate_type": rate_type})
        
        # Parse Excel - expected columns: min_wages, max_wages, employee_amount/rate, employer_amount/rate
        rates = []
        headers = [cell.value for cell in ws[1]]
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]:  # Skip empty rows
                continue
            
            rate_record = {
                "id": str(uuid.uuid4()),
                "rate_type": rate_type,
                "min_wages": float(row[0]) if row[0] else 0,
                "max_wages": float(row[1]) if row[1] else 999999,
                "employee_amount": float(row[2]) if len(row) > 2 and row[2] else 0,
                "employer_amount": float(row[3]) if len(row) > 3 and row[3] else 0,
                "total_amount": float(row[4]) if len(row) > 4 and row[4] else 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            rates.append(rate_record)
        
        if rates:
            await db.statutory_rates.insert_many(rates)
        
        return {"message": f"Uploaded {len(rates)} {rate_type.upper()} rate records"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel file: {str(e)}")

@api_router.get("/hr/statutory-rates")
async def get_statutory_rates(rate_type: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get uploaded statutory rates"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if rate_type:
        query["rate_type"] = rate_type
    
    rates = await db.statutory_rates.find(query, {"_id": 0}).sort("min_wages", 1).to_list(500)
    return rates

@api_router.get("/hr/statutory-rates/templates/{rate_type}")
async def download_statutory_template(rate_type: str, current_user: User = Depends(get_current_user)):
    """Download Excel template for statutory rates"""
    if rate_type not in ["epf", "socso", "eis"]:
        raise HTTPException(status_code=400, detail="Invalid rate type")
    
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{rate_type.upper()} Rates"
    
    # Headers
    headers = ["Min Wages (RM)", "Max Wages (RM)", "Employee Amount (RM)", "Employer Amount (RM)", "Total (RM)"]
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    
    # Sample data based on type
    if rate_type == "epf":
        sample_data = [
            [0, 20, 0, 0, 0],
            [20, 40, 4, 5, 9],
            [40, 60, 6, 8, 14],
        ]
    elif rate_type == "socso":
        sample_data = [
            [0, 30, 0.10, 0.40, 0.50],
            [30, 50, 0.20, 0.70, 0.90],
            [50, 70, 0.30, 1.00, 1.30],
        ]
    else:  # eis
        sample_data = [
            [0, 30, 0.05, 0.05, 0.10],
            [30, 50, 0.10, 0.10, 0.20],
        ]
    
    for row_idx, row_data in enumerate(sample_data, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Set column widths
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 20
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={rate_type}_rates_template.xlsx"}
    )

# =====================================================
# PAYSLIP GENERATION
# =====================================================

@api_router.get("/hr/payslips")
async def get_payslips(
    staff_id: Optional[str] = None,
    period_id: Optional[str] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get payslips with optional filters"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if staff_id:
        query["staff_id"] = staff_id
    if period_id:
        query["period_id"] = period_id
    if year:
        query["year"] = year
    
    payslips = await db.payslips.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(500)
    return payslips

@api_router.post("/hr/payslips/generate")
async def generate_payslip(data: dict, current_user: User = Depends(get_current_user)):
    """Generate a payslip for a staff member"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    staff_id = data.get("staff_id")
    period_id = data.get("period_id")
    year = data.get("year")
    month = data.get("month")
    
    # Get staff details
    staff = await db.hr_staff.find_one({"id": staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get linked user for NRIC if available
    user_nric = None
    if staff.get("user_id"):
        user = await db.users.find_one({"id": staff["user_id"]}, {"_id": 0, "id_number": 1})
        user_nric = user.get("id_number") if user else None
    
    # Use staff's own NRIC or linked user's NRIC
    nric = staff.get("nric") or user_nric or ""
    
    # Check if period exists and is open
    period = None
    if period_id:
        period = await db.payroll_periods.find_one({"id": period_id}, {"_id": 0})
    elif year and month:
        period = await db.payroll_periods.find_one({"year": year, "month": month}, {"_id": 0})
    
    if period and period.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Cannot generate payslip for closed period")
    
    # Check if payslip already exists
    existing = await db.payslips.find_one({
        "staff_id": staff_id,
        "year": year or period.get("year"),
        "month": month or period.get("month")
    })
    if existing:
        raise HTTPException(status_code=400, detail="Payslip already exists for this period. Delete it first to regenerate.")
    
    # Calculate age from NRIC (first 6 digits = YYMMDD) or fallback to DOB
    if nric and len(nric) >= 6:
        age = calculate_age_from_nric(nric, f"{year}-{month:02d}-01")
    else:
        age = calculate_age(staff.get("date_of_birth"), f"{year}-{month}-01")
    
    # Calculate earnings
    basic_salary = data.get("basic_salary") if data.get("basic_salary") is not None else staff.get("basic_salary", 0)
    total_allowances = (
        (data.get("housing_allowance") if data.get("housing_allowance") is not None else staff.get("housing_allowance", 0)) +
        (data.get("transport_allowance") if data.get("transport_allowance") is not None else staff.get("transport_allowance", 0)) +
        (data.get("meal_allowance") if data.get("meal_allowance") is not None else staff.get("meal_allowance", 0)) +
        (data.get("phone_allowance") if data.get("phone_allowance") is not None else staff.get("phone_allowance", 0)) +
        (data.get("other_allowance") if data.get("other_allowance") is not None else staff.get("other_allowance", 0))
    )
    overtime = data.get("overtime", 0)
    bonus = data.get("bonus", 0)
    commission = data.get("commission", 0)
    other_earnings = data.get("other_earnings", 0)
    
    gross_salary = basic_salary + total_allowances + overtime + bonus + commission + other_earnings
    
    # Calculate statutory deductions (use provided values if given, otherwise auto-calculate)
    epf = calculate_epf(basic_salary, age, staff.get("employee_epf_rate"), staff.get("employer_epf_rate"))
    socso = calculate_socso(gross_salary, age)
    eis = calculate_eis(gross_salary, age)
    
    # Allow overriding auto-calculated values
    epf_employee = data.get("epf_employee") if data.get("epf_employee") is not None else epf["employee_amount"]
    epf_employer = data.get("epf_employer") if data.get("epf_employer") is not None else epf["employer_amount"]
    socso_employee = data.get("socso_employee") if data.get("socso_employee") is not None else socso["employee_amount"]
    socso_employer = data.get("socso_employer") if data.get("socso_employer") is not None else socso["employer_amount"]
    eis_employee = data.get("eis_employee") if data.get("eis_employee") is not None else eis["employee_amount"]
    eis_employer = data.get("eis_employer") if data.get("eis_employer") is not None else eis["employer_amount"]
    
    # Other deductions
    pcb = data.get("pcb", 0)  # Income tax
    loan_deduction = data.get("loan_deduction", 0)
    other_deductions = data.get("other_deductions", 0)
    
    total_deductions = epf_employee + socso_employee + eis_employee + pcb + loan_deduction + other_deductions
    nett_pay = gross_salary - total_deductions
    
    # Get YTD data
    ytd_data = await db.payslips.aggregate([
        {"$match": {"staff_id": staff_id, "year": year, "month": {"$lt": month}}},
        {"$group": {
            "_id": None,
            "ytd_basic": {"$sum": "$basic_salary"},
            "ytd_allowances": {"$sum": "$total_allowances"},
            "ytd_overtime": {"$sum": "$overtime"},
            "ytd_bonus": {"$sum": "$bonus"},
            "ytd_gross": {"$sum": "$gross_salary"},
            "ytd_epf_employee": {"$sum": "$epf_employee"},
            "ytd_epf_employer": {"$sum": "$epf_employer"},
            "ytd_socso_employee": {"$sum": "$socso_employee"},
            "ytd_socso_employer": {"$sum": "$socso_employer"},
            "ytd_eis_employee": {"$sum": "$eis_employee"},
            "ytd_eis_employer": {"$sum": "$eis_employer"},
            "ytd_pcb": {"$sum": "$pcb"},
            "ytd_nett": {"$sum": "$nett_pay"}
        }}
    ]).to_list(1)
    
    ytd = ytd_data[0] if ytd_data else {}
    
    payslip = {
        "id": str(uuid.uuid4()),
        "staff_id": staff_id,
        "period_id": period["id"] if period else None,
        "year": year or period.get("year"),
        "month": month or period.get("month"),
        "period_name": f"{year}-{str(month).zfill(2)}",
        
        # Staff info snapshot
        "employee_id": staff.get("employee_id"),
        "full_name": staff.get("full_name"),
        "nric": nric,
        "designation": staff.get("designation"),
        "department": staff.get("department"),
        "epf_number": staff.get("epf_number"),
        "socso_number": staff.get("socso_number"),
        "tax_number": staff.get("tax_number"),
        "bank_name": staff.get("bank_name"),
        "bank_account": staff.get("bank_account"),
        "age": age,
        
        # Earnings
        "basic_salary": basic_salary,
        "housing_allowance": data.get("housing_allowance") if data.get("housing_allowance") is not None else staff.get("housing_allowance", 0),
        "transport_allowance": data.get("transport_allowance") if data.get("transport_allowance") is not None else staff.get("transport_allowance", 0),
        "meal_allowance": data.get("meal_allowance") if data.get("meal_allowance") is not None else staff.get("meal_allowance", 0),
        "phone_allowance": data.get("phone_allowance") if data.get("phone_allowance") is not None else staff.get("phone_allowance", 0),
        "other_allowance": data.get("other_allowance") if data.get("other_allowance") is not None else staff.get("other_allowance", 0),
        "total_allowances": total_allowances,
        "overtime": overtime,
        "bonus": bonus,
        "commission": commission,
        "other_earnings": other_earnings,
        "gross_salary": gross_salary,
        
        # Deductions (use editable values)
        "epf_employee": epf_employee,
        "epf_employer": epf_employer,
        "epf_employee_rate": epf["employee_rate"],
        "epf_employer_rate": epf["employer_rate"],
        "socso_employee": socso_employee,
        "socso_employer": socso_employer,
        "eis_employee": eis_employee,
        "eis_employer": eis_employer,
        "pcb": pcb,
        "loan_deduction": loan_deduction,
        "other_deductions": other_deductions,
        "total_deductions": total_deductions,
        
        "nett_pay": nett_pay,
        
        # YTD (including current month)
        "ytd_basic": ytd.get("ytd_basic", 0) + basic_salary,
        "ytd_allowances": ytd.get("ytd_allowances", 0) + total_allowances,
        "ytd_overtime": ytd.get("ytd_overtime", 0) + overtime,
        "ytd_bonus": ytd.get("ytd_bonus", 0) + bonus,
        "ytd_gross": ytd.get("ytd_gross", 0) + gross_salary,
        "ytd_epf_employee": ytd.get("ytd_epf_employee", 0) + epf["employee_amount"],
        "ytd_epf_employer": ytd.get("ytd_epf_employer", 0) + epf["employer_amount"],
        "ytd_socso_employee": ytd.get("ytd_socso_employee", 0) + socso["employee_amount"],
        "ytd_socso_employer": ytd.get("ytd_socso_employer", 0) + socso["employer_amount"],
        "ytd_eis_employee": ytd.get("ytd_eis_employee", 0) + eis["employee_amount"],
        "ytd_eis_employer": ytd.get("ytd_eis_employer", 0) + eis["employer_amount"],
        "ytd_pcb": ytd.get("ytd_pcb", 0) + pcb,
        "ytd_nett": ytd.get("ytd_nett", 0) + nett_pay,
        
        "is_locked": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.email
    }
    
    await db.payslips.insert_one(payslip)
    return {"id": payslip["id"], "message": "Payslip generated successfully", "nett_pay": nett_pay}

@api_router.delete("/hr/payslips/{payslip_id}")
async def delete_payslip(payslip_id: str, current_user: User = Depends(get_current_user)):
    """Delete a payslip (only if period is open)"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can delete payslips")
    
    payslip = await db.payslips.find_one({"id": payslip_id})
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    if payslip.get("is_locked"):
        raise HTTPException(status_code=400, detail="Cannot delete locked payslip. Period is closed.")
    
    await db.payslips.delete_one({"id": payslip_id})
    return {"message": "Payslip deleted"}

@api_router.get("/hr/payslips/{payslip_id}")
async def get_payslip(payslip_id: str, current_user: User = Depends(get_current_user)):
    """Get a single payslip with full details"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    payslip = await db.payslips.find_one({"id": payslip_id}, {"_id": 0})
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    return payslip

# =====================================================
# PAY ADVICE (For Session Workers)
# =====================================================

@api_router.get("/hr/pay-advice")
async def get_pay_advice_list(
    period_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all pay advice records"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if period_id:
        query["period_id"] = period_id
    if year:
        query["year"] = year
    if month:
        query["month"] = month
    
    advice_list = await db.pay_advice.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return advice_list

@api_router.post("/hr/pay-advice/generate")
async def generate_pay_advice(data: dict, current_user: User = Depends(get_current_user)):
    """Generate pay advice for a session worker based on their session work"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_id = data.get("user_id")
    year = data.get("year")
    month = data.get("month")
    
    if not user_id or not year or not month:
        raise HTTPException(status_code=400, detail="user_id, year, and month are required")
    
    # Check if pay advice already exists for this user/period
    existing = await db.pay_advice.find_one({"user_id": user_id, "year": year, "month": month}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Pay advice already exists for this period. Delete it first to regenerate.")
    
    # Check period status (use payables_periods)
    period = await db.payables_periods.find_one({"year": year, "month": month})
    
    # Get user details
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    end_date = end_date.replace(hour=23, minute=59, second=59)
    
    # Build session details from all sources
    session_details = []
    total_amount = 0
    
    # 1. Get trainer fees - filter by session date
    trainer_fees = await db.trainer_fees.find({"trainer_id": user_id}, {"_id": 0}).to_list(500)
    for fee in trainer_fees:
        session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        
        # Check if session is in the target month
        session_date = session.get("start_date")
        if session_date:
            try:
                if isinstance(session_date, str):
                    session_dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                else:
                    session_dt = session_date
                if session_dt.year != year or session_dt.month != month:
                    continue
            except:
                continue
        else:
            continue
        
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        
        session_details.append({
            "session_id": fee.get("session_id"),
            "session_name": session.get("name"),
            "company_name": company.get("name") if company else "Unknown",
            "session_date": session_date,
            "role": fee.get("trainer_role", "Trainer"),
            "amount": fee.get("fee_amount", 0),
            "status": fee.get("status", "pending"),
            "remark": fee.get("remark", "")
        })
        total_amount += fee.get("fee_amount", 0)
    
    # 2. Get coordinator fees - filter by session date
    coord_fees = await db.coordinator_fees.find({"coordinator_id": user_id}, {"_id": 0}).to_list(500)
    for fee in coord_fees:
        session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        
        session_date = session.get("start_date")
        if session_date:
            try:
                if isinstance(session_date, str):
                    session_dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                else:
                    session_dt = session_date
                if session_dt.year != year or session_dt.month != month:
                    continue
            except:
                continue
        else:
            continue
        
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        
        session_details.append({
            "session_id": fee.get("session_id"),
            "session_name": session.get("name"),
            "company_name": company.get("name") if company else "Unknown",
            "session_date": session_date,
            "role": "Coordinator",
            "amount": fee.get("total_fee", 0),
            "status": fee.get("status", "pending"),
            "remark": f"{fee.get('num_days', 1)} day(s) @ RM{fee.get('daily_rate', 50)}/day"
        })
        total_amount += fee.get("total_fee", 0)
    
    # 3. Get marketing commissions - filter by session date
    mkt_comm = await db.marketing_commissions.find({"marketing_user_id": user_id}, {"_id": 0}).to_list(500)
    for comm in mkt_comm:
        session = await db.sessions.find_one({"id": comm.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
        if not session:
            continue
        
        session_date = session.get("start_date")
        if session_date:
            try:
                if isinstance(session_date, str):
                    session_dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                else:
                    session_dt = session_date
                if session_dt.year != year or session_dt.month != month:
                    continue
            except:
                continue
        else:
            continue
        
        company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1})
        
        session_details.append({
            "session_id": comm.get("session_id"),
            "session_name": session.get("name"),
            "company_name": company.get("name") if company else "Unknown",
            "session_date": session_date,
            "role": "Marketing",
            "amount": comm.get("calculated_amount", 0),
            "status": comm.get("status", "pending"),
            "remark": f"{comm.get('commission_type', 'Commission')} @ {comm.get('commission_percentage', 0)}%"
        })
        total_amount += comm.get("calculated_amount", 0)
    
    if not session_details:
        raise HTTPException(status_code=400, detail="No session work found for this user in this period")
    
    # Sort by session date
    session_details.sort(key=lambda x: x.get("session_date", ""))
    
    # Calculate payment month (following month - training done Dec means payment in Jan)
    # Training done in month X is paid by 15th of month X+1
    payment_year = year
    payment_month = month + 1
    if payment_month > 12:
        payment_month = 1
        payment_year = year + 1
    
    # Create pay advice
    now = get_malaysia_time()
    pay_advice = {
        "id": str(uuid.uuid4()),
        "advice_number": f"PA/MDDRC/{payment_year}/{str(payment_month).zfill(2)}/{str(uuid.uuid4())[:4].upper()}",
        "user_id": user_id,
        "period_id": period["id"] if period else None,
        # Store both training and payment periods for clarity
        "training_year": year,
        "training_month": month,
        "year": payment_year,  # Payment year
        "month": payment_month,  # Payment month
        "period_name": f"{datetime(payment_year, payment_month, 1).strftime('%B %Y')}",  # Shows payment month
        "training_period_name": f"{datetime(year, month, 1).strftime('%B %Y')}",  # Shows training month
        
        # User info
        "full_name": user.get("full_name"),
        "id_number": user.get("id_number"),
        "email": user.get("email"),
        "phone": user.get("phone_number"),
        "bank_name": user.get("bank_name"),
        "bank_account": user.get("bank_account"),
        
        # Session details
        "session_details": session_details,
        "total_sessions": len(session_details),
        "gross_amount": total_amount,
        "deductions": 0,
        "nett_amount": total_amount,
        
        "is_locked": False,
        "created_at": now.isoformat(),
        "created_by": current_user.id,
        "created_by_name": current_user.full_name or current_user.email
    }
    
    await db.pay_advice.insert_one({**pay_advice, "_id": pay_advice["id"]})
    return {"id": pay_advice["id"], "message": "Pay advice generated successfully", "total_sessions": len(session_details), "total_amount": total_amount}

@api_router.get("/hr/pay-advice/{advice_id}")
async def get_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Get a single pay advice"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    advice = await db.pay_advice.find_one({"id": advice_id}, {"_id": 0})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    
    return advice

@api_router.delete("/hr/pay-advice/{advice_id}")
async def delete_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Delete a pay advice (only if not locked)"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can delete pay advice")
    
    advice = await db.pay_advice.find_one({"id": advice_id})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    
    if advice.get("is_locked"):
        raise HTTPException(status_code=400, detail="Cannot delete locked pay advice. Period is closed.")
    
    await db.pay_advice.delete_one({"id": advice_id})
    return {"message": "Pay advice deleted"}

@api_router.post("/hr/pay-advice/{advice_id}/lock")
async def lock_pay_advice(advice_id: str, current_user: User = Depends(get_current_user)):
    """Lock a pay advice (finalize it so staff can view)"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can lock pay advice")
    
    advice = await db.pay_advice.find_one({"id": advice_id}, {"_id": 0})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    
    if advice.get("is_locked"):
        raise HTTPException(status_code=400, detail="Pay advice is already locked")
    
    now = get_malaysia_time()
    await db.pay_advice.update_one(
        {"id": advice_id},
        {"$set": {
            "is_locked": True,
            "locked_at": now.isoformat(),
            "locked_by": current_user.id,
            "locked_by_name": current_user.full_name or current_user.email
        }}
    )
    return {"message": "Pay advice locked successfully"}

@api_router.post("/hr/pay-advice/{advice_id}/unlock")
async def unlock_pay_advice(advice_id: str, reason: str = "", current_user: User = Depends(get_current_user)):
    """Unlock a pay advice (requires admin and reason)"""
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can unlock pay advice")
    
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason is required (minimum 5 characters)")
    
    advice = await db.pay_advice.find_one({"id": advice_id}, {"_id": 0})
    if not advice:
        raise HTTPException(status_code=404, detail="Pay advice not found")
    
    if not advice.get("is_locked"):
        raise HTTPException(status_code=400, detail="Pay advice is not locked")
    
    now = get_malaysia_time()
    await db.pay_advice.update_one(
        {"id": advice_id},
        {"$set": {
            "is_locked": False,
            "unlocked_at": now.isoformat(),
            "unlocked_by": current_user.id,
            "unlock_reason": reason
        }}
    )
    
    # Create audit trail
    await create_audit_trail_entry(
        action="Pay Advice Unlocked",
        record_reference=f"{advice.get('full_name')} - {advice.get('period_name')}",
        entity_type="pay_advice",
        entity_id=advice_id,
        changed_by=current_user,
        reason=reason,
        field_changed="is_locked",
        from_value="true",
        to_value="false"
    )
    
    return {"message": "Pay advice unlocked successfully"}

@api_router.post("/hr/pay-advice/bulk-generate")
async def bulk_generate_pay_advice(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Bulk generate pay advice for all session workers who have work in the period"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Get all sessions in this month
    sessions = await db.sessions.find({}, {"_id": 0, "id": 1, "start_date": 1}).to_list(1000)
    session_ids = []
    for s in sessions:
        sd = s.get("start_date")
        if sd:
            try:
                if isinstance(sd, str):
                    sdt = datetime.fromisoformat(sd.replace('Z', '+00:00'))
                else:
                    sdt = sd
                if sdt.year == year and sdt.month == month:
                    session_ids.append(s["id"])
            except:
                pass
    
    if not session_ids:
        return {"message": "No sessions found for this period", "generated": 0}
    
    # Find unique users who worked in these sessions
    user_ids = set()
    
    # Trainers
    trainer_fees = await db.trainer_fees.find({"session_id": {"$in": session_ids}}, {"_id": 0, "trainer_id": 1}).to_list(1000)
    for tf in trainer_fees:
        if tf.get("trainer_id"):
            user_ids.add(tf["trainer_id"])
    
    # Coordinators
    coord_fees = await db.coordinator_fees.find({"session_id": {"$in": session_ids}}, {"_id": 0, "coordinator_id": 1}).to_list(1000)
    for cf in coord_fees:
        if cf.get("coordinator_id"):
            user_ids.add(cf["coordinator_id"])
    
    # Marketing
    mkt_comm = await db.marketing_commissions.find({"session_id": {"$in": session_ids}}, {"_id": 0, "marketing_user_id": 1}).to_list(1000)
    for mc in mkt_comm:
        if mc.get("marketing_user_id"):
            user_ids.add(mc["marketing_user_id"])
    
    # Generate pay advice for each user
    generated = 0
    skipped = 0
    errors = []
    
    for user_id in user_ids:
        try:
            # Check if already exists
            existing = await db.pay_advice.find_one({"user_id": user_id, "year": year, "month": month})
            if existing:
                skipped += 1
                continue
            
            # Reuse the generate function logic (simplified)
            user = await db.users.find_one({"id": user_id}, {"_id": 0})
            if not user:
                continue
            
            # Build session details
            session_details = []
            total_amount = 0
            
            # Trainer fees
            for fee in await db.trainer_fees.find({"trainer_id": user_id, "session_id": {"$in": session_ids}}, {"_id": 0}).to_list(100):
                session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1}) if session else None
                session_details.append({
                    "session_id": fee.get("session_id"),
                    "session_name": session.get("name") if session else "Unknown",
                    "company_name": company.get("name") if company else "Unknown",
                    "session_date": session.get("start_date") if session else None,
                    "role": fee.get("trainer_role", "Trainer"),
                    "amount": fee.get("fee_amount", 0),
                    "status": fee.get("status", "pending")
                })
                total_amount += fee.get("fee_amount", 0)
            
            # Coordinator fees
            for fee in await db.coordinator_fees.find({"coordinator_id": user_id, "session_id": {"$in": session_ids}}, {"_id": 0}).to_list(100):
                session = await db.sessions.find_one({"id": fee.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1}) if session else None
                session_details.append({
                    "session_id": fee.get("session_id"),
                    "session_name": session.get("name") if session else "Unknown",
                    "company_name": company.get("name") if company else "Unknown",
                    "session_date": session.get("start_date") if session else None,
                    "role": "Coordinator",
                    "amount": fee.get("total_fee", 0),
                    "status": fee.get("status", "pending")
                })
                total_amount += fee.get("total_fee", 0)
            
            # Marketing commission
            for comm in await db.marketing_commissions.find({"marketing_user_id": user_id, "session_id": {"$in": session_ids}}, {"_id": 0}).to_list(100):
                session = await db.sessions.find_one({"id": comm.get("session_id")}, {"_id": 0, "name": 1, "start_date": 1, "company_id": 1})
                company = await db.companies.find_one({"id": session.get("company_id")}, {"_id": 0, "name": 1}) if session else None
                session_details.append({
                    "session_id": comm.get("session_id"),
                    "session_name": session.get("name") if session else "Unknown",
                    "company_name": company.get("name") if company else "Unknown",
                    "session_date": session.get("start_date") if session else None,
                    "role": "Marketing",
                    "amount": comm.get("calculated_amount", 0),
                    "status": comm.get("status", "pending")
                })
                total_amount += comm.get("calculated_amount", 0)
            
            if not session_details:
                continue
            
            # Calculate payment month (following month - training done Dec means payment in Jan)
            payment_year = year
            payment_month = month + 1
            if payment_month > 12:
                payment_month = 1
                payment_year = year + 1
            
            now = get_malaysia_time()
            pay_advice = {
                "id": str(uuid.uuid4()),
                "advice_number": f"PA/MDDRC/{payment_year}/{str(payment_month).zfill(2)}/{str(uuid.uuid4())[:4].upper()}",
                "user_id": user_id,
                # Store both training and payment periods
                "training_year": year,
                "training_month": month,
                "year": payment_year,  # Payment year
                "month": payment_month,  # Payment month
                "period_name": f"{datetime(payment_year, payment_month, 1).strftime('%B %Y')}",  # Payment month display
                "training_period_name": f"{datetime(year, month, 1).strftime('%B %Y')}",  # Training month
                "full_name": user.get("full_name"),
                "id_number": user.get("id_number"),
                "email": user.get("email"),
                "phone": user.get("phone_number"),
                "bank_name": user.get("bank_name"),
                "bank_account": user.get("bank_account"),
                "session_details": session_details,
                "total_sessions": len(session_details),
                "gross_amount": total_amount,
                "deductions": 0,
                "nett_amount": total_amount,
                "is_locked": False,
                "created_at": now.isoformat(),
                "created_by": current_user.id
            }
            
            await db.pay_advice.insert_one({**pay_advice, "_id": pay_advice["id"]})
            generated += 1
        except Exception as e:
            errors.append(f"{user_id}: {str(e)}")
    
    return {
        "message": f"Bulk generation complete",
        "generated": generated,
        "skipped": skipped,
        "total_workers": len(user_ids),
        "errors": errors[:5] if errors else []
    }

@api_router.post("/hr/pay-advice/bulk-lock")
async def bulk_lock_pay_advice(year: int, month: int, current_user: User = Depends(get_current_user)):
    """Bulk lock all pay advice for a period"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    result = await db.pay_advice.update_many(
        {"year": year, "month": month, "is_locked": False},
        {"$set": {
            "is_locked": True,
            "locked_at": now.isoformat(),
            "locked_by": current_user.id
        }}
    )
    
    return {"message": f"Locked {result.modified_count} pay advice records"}

# =====================================================
# SELF-SERVICE PAYSLIP/PAY ADVICE (For Staff Portal)
# =====================================================

@api_router.get("/hr/my-payslips")
async def get_my_payslips(year: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get current user's own payslips (only locked/finalized ones)"""
    # Find staff record linked to this user
    staff = await db.hr_staff.find_one({"user_id": current_user.id}, {"_id": 0})
    
    if not staff:
        # Check if user has any payslips directly by email match
        staff = await db.hr_staff.find_one({"email": current_user.email}, {"_id": 0})
    
    if not staff:
        return []
    
    query = {"staff_id": staff["id"], "is_locked": True}  # Only show locked payslips
    if year:
        query["year"] = year
    
    payslips = await db.payslips.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return payslips

@api_router.get("/hr/my-pay-advice")
async def get_my_pay_advice(year: Optional[int] = None, current_user: User = Depends(get_current_user)):
    """Get current user's own pay advice (only locked/finalized ones)"""
    query = {"user_id": current_user.id, "is_locked": True}  # Only show locked pay advice
    if year:
        query["year"] = year
    
    advice_list = await db.pay_advice.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    return advice_list

# =====================================================
# EA FORM (Annual Remuneration Statement)
# =====================================================

@api_router.get("/hr/ea-form/{staff_id}/{year}")
async def get_ea_form_data(staff_id: str, year: int, current_user: User = Depends(get_current_user)):
    """Get EA Form data for a staff member for a specific year"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get staff details
    staff = await db.hr_staff.find_one({"id": staff_id}, {"_id": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get all payslips for this staff for the year
    payslips = await db.payslips.find(
        {"staff_id": staff_id, "year": year},
        {"_id": 0}
    ).sort("month", 1).to_list(12)
    
    # Calculate annual totals
    annual_data = {
        "gross_salary": 0,
        "basic_salary": 0,
        "allowances": 0,
        "overtime": 0,
        "bonus": 0,
        "commission": 0,
        "epf_employee": 0,
        "epf_employer": 0,
        "socso_employee": 0,
        "socso_employer": 0,
        "eis_employee": 0,
        "eis_employer": 0,
        "pcb": 0,
        "other_deductions": 0
    }
    
    monthly_breakdown = []
    
    for ps in payslips:
        annual_data["gross_salary"] += ps.get("gross_salary", 0)
        annual_data["basic_salary"] += ps.get("basic_salary", 0)
        annual_data["allowances"] += ps.get("total_allowances", 0)
        annual_data["overtime"] += ps.get("overtime", 0)
        annual_data["bonus"] += ps.get("bonus", 0)
        annual_data["commission"] += ps.get("commission", 0)
        annual_data["epf_employee"] += ps.get("epf_employee", 0)
        annual_data["epf_employer"] += ps.get("epf_employer", 0)
        annual_data["socso_employee"] += ps.get("socso_employee", 0)
        annual_data["socso_employer"] += ps.get("socso_employer", 0)
        annual_data["eis_employee"] += ps.get("eis_employee", 0)
        annual_data["eis_employer"] += ps.get("eis_employer", 0)
        annual_data["pcb"] += ps.get("pcb", 0)
        annual_data["other_deductions"] += ps.get("loan_deduction", 0) + ps.get("other_deductions", 0)
        
        monthly_breakdown.append({
            "month": ps.get("month"),
            "gross_salary": ps.get("gross_salary", 0),
            "epf_employee": ps.get("epf_employee", 0),
            "socso_employee": ps.get("socso_employee", 0),
            "eis_employee": ps.get("eis_employee", 0),
            "pcb": ps.get("pcb", 0),
            "nett_pay": ps.get("nett_pay", 0)
        })
    
    return {
        "year": year,
        "staff_id": staff_id,
        "employee_details": {
            "full_name": staff.get("full_name"),
            "nric": staff.get("nric"),
            "employee_id": staff.get("employee_id"),
            "designation": staff.get("designation"),
            "epf_number": staff.get("epf_number"),
            "socso_number": staff.get("socso_number"),
            "tax_number": staff.get("tax_number")
        },
        "annual_totals": annual_data,
        "monthly_breakdown": monthly_breakdown,
        "months_worked": len(payslips)
    }

@api_router.get("/hr/my-ea-form/{year}")
async def get_my_ea_form(year: int, current_user: User = Depends(get_current_user)):
    """Get current user's own EA Form data"""
    # Find staff record linked to this user
    staff = await db.hr_staff.find_one({"user_id": current_user.id}, {"_id": 0})
    if not staff:
        staff = await db.hr_staff.find_one({"email": current_user.email}, {"_id": 0})
    
    if not staff:
        raise HTTPException(status_code=404, detail="Staff record not found")
    
    # Reuse the main EA form function logic
    payslips = await db.payslips.find(
        {"staff_id": staff["id"], "year": year, "is_locked": True},
        {"_id": 0}
    ).sort("month", 1).to_list(12)
    
    annual_data = {
        "gross_salary": 0,
        "basic_salary": 0,
        "allowances": 0,
        "overtime": 0,
        "bonus": 0,
        "commission": 0,
        "epf_employee": 0,
        "epf_employer": 0,
        "socso_employee": 0,
        "eis_employee": 0,
        "pcb": 0
    }
    
    monthly_breakdown = []
    
    for ps in payslips:
        annual_data["gross_salary"] += ps.get("gross_salary", 0)
        annual_data["basic_salary"] += ps.get("basic_salary", 0)
        annual_data["allowances"] += ps.get("total_allowances", 0)
        annual_data["overtime"] += ps.get("overtime", 0)
        annual_data["bonus"] += ps.get("bonus", 0)
        annual_data["commission"] += ps.get("commission", 0)
        annual_data["epf_employee"] += ps.get("epf_employee", 0)
        annual_data["epf_employer"] += ps.get("epf_employer", 0)
        annual_data["socso_employee"] += ps.get("socso_employee", 0)
        annual_data["eis_employee"] += ps.get("eis_employee", 0)
        annual_data["pcb"] += ps.get("pcb", 0)
        
        monthly_breakdown.append({
            "month": ps.get("month"),
            "gross_salary": ps.get("gross_salary", 0),
            "epf_employee": ps.get("epf_employee", 0),
            "pcb": ps.get("pcb", 0),
            "nett_pay": ps.get("nett_pay", 0)
        })
    
    return {
        "year": year,
        "employee_details": {
            "full_name": staff.get("full_name"),
            "nric": staff.get("nric"),
            "employee_id": staff.get("employee_id"),
            "designation": staff.get("designation"),
            "epf_number": staff.get("epf_number"),
            "tax_number": staff.get("tax_number")
        },
        "annual_totals": annual_data,
        "monthly_breakdown": monthly_breakdown
    }


# ==================== PROFIT/LOSS LEDGER APIs ====================

class ManualIncomeEntry(BaseModel):
    description: str
    amount: float
    category: str = "Other Income"
    date: str  # YYYY-MM-DD
    notes: Optional[str] = None

class ManualExpenseEntry(BaseModel):
    description: str
    amount: float
    category: str
    date: str  # YYYY-MM-DD
    notes: Optional[str] = None

@api_router.get("/finance/profit-loss")
async def get_profit_loss_report(
    year: int = None,
    month: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get Profit/Loss report - monthly breakdown and YTD
    
    IMPORTANT: All session-related expenses (trainer fees, coordinator fees, 
    marketing commissions, session expenses) are attributed to the month based 
    on the SESSION'S START DATE, not the record's created_at date.
    """
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    # Build date range for the year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get all invoices for the year (INCOME) - filter by session start date
    # First get sessions for the year to map invoice amounts to correct months
    sessions = await db.sessions.find({
        "start_date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0, "id": 1, "start_date": 1, "invoice_id": 1}).to_list(10000)
    
    session_date_map = {}  # session_id -> start_date
    invoice_session_map = {}  # invoice_id -> session_id
    for s in sessions:
        session_date_map[s.get("id")] = s.get("start_date", "")
        if s.get("invoice_id"):
            invoice_session_map[s.get("invoice_id")] = s.get("id")
    
    # Get all invoices
    invoices = await db.invoices.find({}, {"_id": 0}).to_list(10000)
    
    # Get manual income entries
    manual_income = await db.manual_income.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(1000)
    
    # Get payslips (EXPENSE - Payroll)
    payslips = await db.hr_payslips.find({
        "year": year
    }, {"_id": 0}).to_list(1000)
    
    # Get pay advice (EXPENSE - Session Workers)
    pay_advice = await db.hr_pay_advices.find({
        "year": year
    }, {"_id": 0}).to_list(1000)
    
    # Get ALL trainer fees - we'll filter by session date using session_date_map
    all_trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    
    # Get ALL coordinator fees - we'll filter by session date using session_date_map
    all_coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    
    # Get ALL session expenses - we'll filter by session date using session_date_map
    all_session_expenses = await db.session_expenses.find({}, {"_id": 0}).to_list(10000)
    
    # Get ALL marketing commissions - include pending, approved, and paid for accrual accounting
    # Expense should be recognized when the session occurs, not when payment is made
    all_marketing_commissions = await db.marketing_commissions.find({
        "status": {"$in": ["pending", "approved", "paid"]}
    }, {"_id": 0}).to_list(10000)
    
    # Get petty cash expenses - only approved transactions
    petty_cash = await db.petty_cash_transactions.find({
        "date": {"$gte": start_date, "$lte": end_date},
        "type": "expense",
        "status": "approved"  # Only count approved petty cash
    }, {"_id": 0}).to_list(1000)
    
    # Get manual expense entries
    manual_expenses = await db.manual_expenses.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(1000)
    
    # Build monthly breakdown
    monthly_data = {}
    for m in range(1, 13):
        monthly_data[m] = {
            "month": m,
            "month_name": ["", "January", "February", "March", "April", "May", "June", 
                          "July", "August", "September", "October", "November", "December"][m],
            "income": {
                "invoices": 0,
                "manual": 0,
                "total": 0
            },
            "expenses": {
                "payroll": 0,
                "session_workers": 0,  # Trainer + Coordinator fees
                "marketing_commissions": 0,
                "session_expenses": 0,  # F&B, venue, HRDCorp levy, etc
                "petty_cash": 0,
                "manual": 0,
                "total": 0
            },
            "net_profit": 0
        }
    
    # Process invoices (income) - attribute to session's start date month
    for inv in invoices:
        try:
            if inv.get("status") not in ["approved", "paid"]:
                continue
            amount = float(inv.get("total_amount") or inv.get("amount") or 0)
            inv_id = inv.get("id")
            
            # Try to find session for this invoice to get correct month
            session_id = invoice_session_map.get(inv_id)
            if session_id and session_id in session_date_map:
                session_date = session_date_map[session_id]
                if session_date.startswith(str(year)):
                    inv_month = int(session_date[5:7])
                    monthly_data[inv_month]["income"]["invoices"] += amount
            else:
                # Fallback to invoice created_at
                inv_date = inv.get("created_at", "")[:10]
                if inv_date.startswith(str(year)):
                    inv_month = int(inv_date[5:7]) if len(inv_date) >= 7 else 1
                    monthly_data[inv_month]["income"]["invoices"] += amount
        except:
            pass
    
    # Process manual income
    for inc in manual_income:
        try:
            inc_month = int(inc.get("date", "")[5:7])
            monthly_data[inc_month]["income"]["manual"] += float(inc.get("amount", 0))
        except:
            pass
    
    # Process payroll (expense)
    for ps in payslips:
        try:
            ps_month = ps.get("month", 1)
            # Total cost = gross + employer contributions
            gross = float(ps.get("gross_salary", 0))
            epf_er = float(ps.get("epf_employer", 0))
            socso_er = float(ps.get("socso_employer", 0))
            eis_er = float(ps.get("eis_employer", 0))
            monthly_data[ps_month]["expenses"]["payroll"] += gross + epf_er + socso_er + eis_er
        except:
            pass
    
    # Process pay advice (session workers) - only if pay advice system is used
    for pa in pay_advice:
        try:
            pa_month = pa.get("month", 1)
            monthly_data[pa_month]["expenses"]["session_workers"] += float(pa.get("amount", 0))
        except:
            pass
    
    # Process trainer fees - use session_date_map to get session's start_date
    for tf in all_trainer_fees:
        try:
            session_id = tf.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            tf_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            amount = float(tf.get("fee_amount") or 0)
            monthly_data[tf_month]["expenses"]["session_workers"] += amount
        except:
            pass
    
    # Process coordinator fees - use session_date_map to get session's start_date
    for cf in all_coordinator_fees:
        try:
            session_id = cf.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            cf_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            amount = float(cf.get("total_fee") or 0)
            monthly_data[cf_month]["expenses"]["session_workers"] += amount
        except:
            pass
    
    # Process session expenses (F&B, venue, HRDCorp, etc) - use session's start_date
    for exp in all_session_expenses:
        try:
            session_id = exp.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            exp_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            # Use actual_amount first, then estimated_amount as fallback
            amount = float(exp.get("actual_amount") or exp.get("estimated_amount") or exp.get("amount") or 0)
            monthly_data[exp_month]["expenses"]["session_expenses"] += amount
        except:
            pass
    
    # Process marketing commissions - use session_date_map to get session's start_date
    for mc in all_marketing_commissions:
        try:
            session_id = mc.get("session_id")
            session_date = session_date_map.get(session_id, "")
            if not session_date or not session_date.startswith(str(year)):
                continue
            mc_month = int(session_date[5:7]) if len(session_date) >= 7 else 1
            amount = float(mc.get("calculated_amount") or 0)
            monthly_data[mc_month]["expenses"]["marketing_commissions"] += amount
        except:
            pass
    
    # Process petty cash
    for pc in petty_cash:
        try:
            pc_month = int(pc.get("date", "")[5:7])
            monthly_data[pc_month]["expenses"]["petty_cash"] += float(pc.get("amount", 0))
        except:
            pass
    
    # Process manual expenses
    for exp in manual_expenses:
        try:
            exp_month = int(exp.get("date", "")[5:7])
            monthly_data[exp_month]["expenses"]["manual"] += float(exp.get("amount", 0))
        except:
            pass
    
    # Calculate totals and net profit
    ytd_income = 0
    ytd_expenses = 0
    
    for m in range(1, 13):
        md = monthly_data[m]
        md["income"]["total"] = md["income"]["invoices"] + md["income"]["manual"]
        md["expenses"]["total"] = (md["expenses"]["payroll"] + md["expenses"]["session_workers"] + 
                                   md["expenses"]["marketing_commissions"] + md["expenses"]["session_expenses"] + 
                                   md["expenses"]["petty_cash"] + md["expenses"]["manual"])
        md["net_profit"] = md["income"]["total"] - md["expenses"]["total"]
        ytd_income += md["income"]["total"]
        ytd_expenses += md["expenses"]["total"]
    
    return {
        "year": year,
        "monthly_breakdown": list(monthly_data.values()),
        "ytd_summary": {
            "total_income": ytd_income,
            "total_expenses": ytd_expenses,
            "net_profit": ytd_income - ytd_expenses,
            "profit_margin": round((ytd_income - ytd_expenses) / ytd_income * 100, 2) if ytd_income > 0 else 0
        },
        "expense_breakdown": {
            "payroll": sum(md["expenses"]["payroll"] for md in monthly_data.values()),
            "session_workers": sum(md["expenses"]["session_workers"] for md in monthly_data.values()),
            "marketing_commissions": sum(md["expenses"]["marketing_commissions"] for md in monthly_data.values()),
            "session_expenses": sum(md["expenses"]["session_expenses"] for md in monthly_data.values()),
            "petty_cash": sum(md["expenses"]["petty_cash"] for md in monthly_data.values()),
            "manual": sum(md["expenses"]["manual"] for md in monthly_data.values())
        }
    }


@api_router.get("/finance/profit-loss/by-programme")
async def get_profit_loss_by_programme(
    year: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get Profit/Loss report broken down by programme (dynamic).
    
    Income and direct costs are grouped by programme.
    Overhead costs (payroll, petty cash, manual) are shown separately.
    """
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get all programmes
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1, "category": 1}).to_list(100)
    programme_map = {p["id"]: p for p in programmes}
    
    # Get sessions for the year with their programme info
    sessions = await db.sessions.find({
        "start_date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(10000)
    
    # Build session lookup maps
    session_to_programme = {}  # session_id -> programme_id
    session_to_invoice = {}    # session_id -> invoice_id
    invoice_to_session = {}    # invoice_id -> session_id
    
    for s in sessions:
        sid = s.get("id")
        session_to_programme[sid] = s.get("program_id")
        if s.get("invoice_id"):
            session_to_invoice[sid] = s.get("invoice_id")
            invoice_to_session[s.get("invoice_id")] = sid
    
    # Initialize programme data structure
    programme_data = {}
    for prog in programmes:
        programme_data[prog["id"]] = {
            "programme_id": prog["id"],
            "programme_name": prog.get("name", "Unknown"),
            "category": prog.get("category", ""),
            "income": 0,
            "expenses": {
                "trainer_fees": 0,
                "coordinator_fees": 0,
                "marketing_commissions": 0,
                "session_expenses": 0,
                "total": 0
            },
            "gross_profit": 0,
            "gross_margin_pct": 0,
            "session_count": 0
        }
    
    # Add "Other/Unassigned" category for income without programme
    programme_data["_other"] = {
        "programme_id": "_other",
        "programme_name": "Other / Unassigned",
        "category": "Other",
        "income": 0,
        "expenses": {
            "trainer_fees": 0,
            "coordinator_fees": 0,
            "marketing_commissions": 0,
            "session_expenses": 0,
            "total": 0
        },
        "gross_profit": 0,
        "gross_margin_pct": 0,
        "session_count": 0
    }
    
    # Count sessions per programme
    for s in sessions:
        prog_id = s.get("program_id") or "_other"
        if prog_id in programme_data:
            programme_data[prog_id]["session_count"] += 1
    
    # Process invoices (INCOME) - attribute to programme via session
    invoices = await db.invoices.find({
        "status": {"$in": ["approved", "issued", "paid"]}
    }, {"_id": 0}).to_list(10000)
    
    for inv in invoices:
        try:
            amount = float(inv.get("total_amount") or inv.get("amount") or 0)
            inv_id = inv.get("id")
            
            # Find programme via session
            session_id = invoice_to_session.get(inv_id)
            prog_id = session_to_programme.get(session_id, "_other") if session_id else "_other"
            
            # Verify session is in our year
            if session_id and session_id in session_to_programme:
                if prog_id in programme_data:
                    programme_data[prog_id]["income"] += amount
                else:
                    programme_data["_other"]["income"] += amount
            else:
                # Fallback: check invoice date
                inv_date = inv.get("created_at", "")[:10]
                if inv_date.startswith(str(year)):
                    programme_data["_other"]["income"] += amount
        except:
            pass
    
    # Process trainer fees - attribute to programme via session
    trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    for tf in trainer_fees:
        try:
            session_id = tf.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                programme_data[prog_id]["expenses"]["trainer_fees"] += float(tf.get("fee_amount") or 0)
        except:
            pass
    
    # Process coordinator fees
    coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    for cf in coordinator_fees:
        try:
            session_id = cf.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                programme_data[prog_id]["expenses"]["coordinator_fees"] += float(cf.get("total_fee") or 0)
        except:
            pass
    
    # Process marketing commissions - include pending for accrual accounting
    marketing_comms = await db.marketing_commissions.find({
        "status": {"$in": ["pending", "approved", "paid"]}
    }, {"_id": 0}).to_list(10000)
    for mc in marketing_comms:
        try:
            session_id = mc.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                programme_data[prog_id]["expenses"]["marketing_commissions"] += float(mc.get("calculated_amount") or 0)
        except:
            pass
    
    # Process session expenses (F&B, venue, etc.)
    session_expenses = await db.session_expenses.find({}, {"_id": 0}).to_list(10000)
    for exp in session_expenses:
        try:
            session_id = exp.get("session_id")
            if session_id not in session_to_programme:
                continue
            prog_id = session_to_programme.get(session_id) or "_other"
            if prog_id in programme_data:
                amount = float(exp.get("actual_amount") or exp.get("estimated_amount") or exp.get("amount") or 0)
                programme_data[prog_id]["expenses"]["session_expenses"] += amount
        except:
            pass
    
    # Calculate totals and margins
    total_income = 0
    total_direct_expenses = 0
    
    for prog_id, data in programme_data.items():
        # Calculate total direct expenses
        data["expenses"]["total"] = (
            data["expenses"]["trainer_fees"] +
            data["expenses"]["coordinator_fees"] +
            data["expenses"]["marketing_commissions"] +
            data["expenses"]["session_expenses"]
        )
        
        # Calculate gross profit and margin
        data["gross_profit"] = data["income"] - data["expenses"]["total"]
        data["gross_margin_pct"] = round((data["gross_profit"] / data["income"] * 100), 2) if data["income"] > 0 else 0
        
        total_income += data["income"]
        total_direct_expenses += data["expenses"]["total"]
    
    # Get overhead costs (not tied to programmes)
    payslips = await db.hr_payslips.find({"year": year}, {"_id": 0}).to_list(1000)
    overhead_payroll = sum(
        float(ps.get("gross_salary", 0)) + float(ps.get("epf_employer", 0)) + 
        float(ps.get("socso_employer", 0)) + float(ps.get("eis_employer", 0))
        for ps in payslips
    )
    
    petty_cash = await db.petty_cash_transactions.find({
        "date": {"$gte": start_date, "$lte": end_date},
        "type": "expense",
        "status": "approved"
    }, {"_id": 0}).to_list(1000)
    overhead_petty_cash = sum(float(pc.get("amount", 0)) for pc in petty_cash)
    
    manual_expenses = await db.manual_expenses.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(1000)
    overhead_manual = sum(float(exp.get("amount", 0)) for exp in manual_expenses)
    
    # Manual income (other income streams)
    manual_income = await db.manual_income.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(1000)
    other_income = sum(float(inc.get("amount", 0)) for inc in manual_income)
    
    total_overhead = overhead_payroll + overhead_petty_cash + overhead_manual
    total_expenses = total_direct_expenses + total_overhead
    net_profit = total_income + other_income - total_expenses
    
    # Filter out programmes with no activity
    active_programmes = [data for data in programme_data.values() if data["income"] > 0 or data["expenses"]["total"] > 0]
    active_programmes.sort(key=lambda x: x["income"], reverse=True)
    
    return {
        "year": year,
        "programmes": active_programmes,
        "summary": {
            "total_programme_income": total_income,
            "other_income": other_income,
            "total_income": total_income + other_income,
            "total_direct_costs": total_direct_expenses,
            "gross_profit": total_income - total_direct_expenses,
            "gross_margin_pct": round((total_income - total_direct_expenses) / total_income * 100, 2) if total_income > 0 else 0,
            "overhead": {
                "payroll": overhead_payroll,
                "petty_cash": overhead_petty_cash,
                "manual": overhead_manual,
                "total": total_overhead
            },
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "net_margin_pct": round(net_profit / (total_income + other_income) * 100, 2) if (total_income + other_income) > 0 else 0
        }
    }


@api_router.get("/finance/subledger/trainers")
async def get_trainer_subledger(
    year: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get Trainer & Coordinator Sub-ledger - aggregated by person"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get sessions for the year
    sessions = await db.sessions.find({
        "start_date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0, "id": 1, "start_date": 1, "program_id": 1}).to_list(10000)
    session_ids = {s["id"] for s in sessions}
    session_map = {s["id"]: s for s in sessions}
    
    # Get programmes
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    programme_map = {p["id"]: p.get("name", "Unknown") for p in programmes}
    
    # Get all users for name lookup
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
    
    # Get trainer fees for sessions in this year
    trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    
    # Aggregate by trainer
    trainer_data = {}
    for tf in trainer_fees:
        session_id = tf.get("session_id")
        if session_id not in session_ids:
            continue
        
        trainer_id = tf.get("trainer_id")
        if not trainer_id:
            continue
        
        if trainer_id not in trainer_data:
            trainer_data[trainer_id] = {
                "user_id": trainer_id,
                "name": user_map.get(trainer_id, tf.get("trainer_name", "Unknown")),
                "role": "Trainer",
                "total_earned": 0,
                "total_paid": 0,
                "balance": 0,
                "sessions": []
            }
        
        session = session_map.get(session_id, {})
        amount = float(tf.get("fee_amount") or 0)
        is_paid = tf.get("status") == "paid"
        
        trainer_data[trainer_id]["total_earned"] += amount
        if is_paid:
            trainer_data[trainer_id]["total_paid"] += amount
        
        trainer_data[trainer_id]["sessions"].append({
            "session_id": session_id,
            "date": session.get("start_date", ""),
            "programme": programme_map.get(session.get("program_id"), "Unknown"),
            "amount": amount,
            "status": tf.get("status", "pending")
        })
    
    # Get coordinator fees
    coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    
    coordinator_data = {}
    for cf in coordinator_fees:
        session_id = cf.get("session_id")
        if session_id not in session_ids:
            continue
        
        coord_id = cf.get("coordinator_id")
        if not coord_id:
            continue
        
        if coord_id not in coordinator_data:
            coordinator_data[coord_id] = {
                "user_id": coord_id,
                "name": user_map.get(coord_id, cf.get("coordinator_name", "Unknown")),
                "role": "Coordinator",
                "total_earned": 0,
                "total_paid": 0,
                "balance": 0,
                "sessions": []
            }
        
        session = session_map.get(session_id, {})
        amount = float(cf.get("total_fee") or 0)
        is_paid = cf.get("status") == "paid"
        
        coordinator_data[coord_id]["total_earned"] += amount
        if is_paid:
            coordinator_data[coord_id]["total_paid"] += amount
        
        coordinator_data[coord_id]["sessions"].append({
            "session_id": session_id,
            "date": session.get("start_date", ""),
            "programme": programme_map.get(session.get("program_id"), "Unknown"),
            "amount": amount,
            "status": cf.get("status", "pending")
        })
    
    # Calculate balances
    for data in trainer_data.values():
        data["balance"] = data["total_earned"] - data["total_paid"]
        data["sessions"].sort(key=lambda x: x["date"], reverse=True)
    
    for data in coordinator_data.values():
        data["balance"] = data["total_earned"] - data["total_paid"]
        data["sessions"].sort(key=lambda x: x["date"], reverse=True)
    
    trainers = sorted(trainer_data.values(), key=lambda x: x["total_earned"], reverse=True)
    coordinators = sorted(coordinator_data.values(), key=lambda x: x["total_earned"], reverse=True)
    
    return {
        "year": year,
        "trainers": trainers,
        "coordinators": coordinators,
        "totals": {
            "trainer_earned": sum(t["total_earned"] for t in trainers),
            "trainer_paid": sum(t["total_paid"] for t in trainers),
            "trainer_balance": sum(t["balance"] for t in trainers),
            "coordinator_earned": sum(c["total_earned"] for c in coordinators),
            "coordinator_paid": sum(c["total_paid"] for c in coordinators),
            "coordinator_balance": sum(c["balance"] for c in coordinators)
        }
    }


@api_router.get("/finance/subledger/marketing")
async def get_marketing_subledger(
    year: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get Marketing Commission Sub-ledger - aggregated by marketer"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get sessions for the year
    sessions = await db.sessions.find({
        "start_date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0, "id": 1, "start_date": 1, "program_id": 1, "company_name": 1}).to_list(10000)
    session_ids = {s["id"] for s in sessions}
    session_map = {s["id"]: s for s in sessions}
    
    # Get programmes
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    programme_map = {p["id"]: p.get("name", "Unknown") for p in programmes}
    
    # Get users
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
    
    # Get marketing commissions
    commissions = await db.marketing_commissions.find({}, {"_id": 0}).to_list(10000)
    
    marketer_data = {}
    for mc in commissions:
        session_id = mc.get("session_id")
        if session_id not in session_ids:
            continue
        
        marketer_id = mc.get("marketing_user_id") or mc.get("user_id")
        if not marketer_id:
            continue
        
        if marketer_id not in marketer_data:
            marketer_data[marketer_id] = {
                "user_id": marketer_id,
                "name": user_map.get(marketer_id, mc.get("marketer_name", "Unknown")),
                "total_commission": 0,
                "total_paid": 0,
                "balance": 0,
                "clients": []
            }
        
        session = session_map.get(session_id, {})
        amount = float(mc.get("calculated_amount") or 0)
        is_paid = mc.get("status") == "paid"
        
        marketer_data[marketer_id]["total_commission"] += amount
        if is_paid:
            marketer_data[marketer_id]["total_paid"] += amount
        
        marketer_data[marketer_id]["clients"].append({
            "session_id": session_id,
            "date": session.get("start_date", ""),
            "client": session.get("company_name", "Unknown"),
            "programme": programme_map.get(session.get("program_id"), "Unknown"),
            "commission_rate": mc.get("commission_rate", 0),
            "amount": amount,
            "status": mc.get("status", "pending")
        })
    
    # Calculate balances
    for data in marketer_data.values():
        data["balance"] = data["total_commission"] - data["total_paid"]
        data["clients"].sort(key=lambda x: x["date"], reverse=True)
    
    marketers = sorted(marketer_data.values(), key=lambda x: x["total_commission"], reverse=True)
    
    return {
        "year": year,
        "marketers": marketers,
        "totals": {
            "total_commission": sum(m["total_commission"] for m in marketers),
            "total_paid": sum(m["total_paid"] for m in marketers),
            "total_balance": sum(m["balance"] for m in marketers)
        }
    }


@api_router.get("/finance/subledger/payroll")
async def get_payroll_subledger(
    year: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get Staff Payroll Register - aggregated by employee"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    # Get payslips for the year
    payslips = await db.hr_payslips.find({"year": year}, {"_id": 0}).to_list(1000)
    
    # Get staff info
    staff = await db.hr_staff.find({}, {"_id": 0}).to_list(1000)
    staff_map = {s["id"]: s for s in staff}
    
    employee_data = {}
    for ps in payslips:
        staff_id = ps.get("staff_id")
        if not staff_id:
            continue
        
        if staff_id not in employee_data:
            staff_info = staff_map.get(staff_id, {})
            employee_data[staff_id] = {
                "staff_id": staff_id,
                "name": ps.get("full_name") or staff_info.get("full_name", "Unknown"),
                "employee_id": staff_info.get("employee_id", ""),
                "designation": staff_info.get("designation", ""),
                "total_gross": 0,
                "total_epf": 0,
                "total_socso": 0,
                "total_eis": 0,
                "total_net": 0,
                "months": []
            }
        
        employee_data[staff_id]["total_gross"] += float(ps.get("gross_salary", 0))
        employee_data[staff_id]["total_epf"] += float(ps.get("epf_employee", 0))
        employee_data[staff_id]["total_socso"] += float(ps.get("socso_employee", 0))
        employee_data[staff_id]["total_eis"] += float(ps.get("eis_employee", 0))
        employee_data[staff_id]["total_net"] += float(ps.get("nett_pay", 0))
        
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        employee_data[staff_id]["months"].append({
            "month": ps.get("month"),
            "month_name": month_names[ps.get("month", 1)],
            "gross": float(ps.get("gross_salary", 0)),
            "epf": float(ps.get("epf_employee", 0)),
            "socso": float(ps.get("socso_employee", 0)),
            "eis": float(ps.get("eis_employee", 0)),
            "net": float(ps.get("nett_pay", 0))
        })
    
    # Sort months
    for data in employee_data.values():
        data["months"].sort(key=lambda x: x["month"])
    
    employees = sorted(employee_data.values(), key=lambda x: x["name"])
    
    return {
        "year": year,
        "employees": employees,
        "totals": {
            "total_gross": sum(e["total_gross"] for e in employees),
            "total_epf": sum(e["total_epf"] for e in employees),
            "total_socso": sum(e["total_socso"] for e in employees),
            "total_eis": sum(e["total_eis"] for e in employees),
            "total_net": sum(e["total_net"] for e in employees)
        }
    }


# Chart of Accounts - Static configuration based on user's Excel template
CHART_OF_ACCOUNTS = {
    # Assets (1xxx)
    "1001": {"name": "Cash at Bank", "type": "Asset"},
    "1002": {"name": "Petty Cash", "type": "Asset"},
    "1100": {"name": "Accounts Receivable", "type": "Asset"},
    
    # Liabilities (2xxx)
    "2001": {"name": "Accounts Payable", "type": "Liability"},
    "2100": {"name": "Trainer Payable", "type": "Liability"},
    "2101": {"name": "Coordinator Payable", "type": "Liability"},
    "2102": {"name": "Marketing Commission Payable", "type": "Liability"},
    "2200": {"name": "EPF Payable", "type": "Liability"},
    "2201": {"name": "SOCSO Payable", "type": "Liability"},
    "2202": {"name": "EIS Payable", "type": "Liability"},
    "2210": {"name": "Salary Payable", "type": "Liability"},
    
    # Income (4xxx) - Dynamic by programme
    "4000": {"name": "Training Income - General", "type": "Income"},
    "4001": {"name": "Training Income - Cars", "type": "Income"},
    "4002": {"name": "Training Income - Motorcycles", "type": "Income"},
    "4003": {"name": "Training Income - Heavy Vehicles", "type": "Income"},
    "4004": {"name": "Training Income - Bus", "type": "Income"},
    "4100": {"name": "Other Income", "type": "Income"},
    
    # Expenses (5xxx)
    "5001": {"name": "Trainer Fees", "type": "Expense"},
    "5002": {"name": "Coordinator Fees", "type": "Expense"},
    "5003": {"name": "Marketing Commission", "type": "Expense"},
    "5100": {"name": "Staff Salaries", "type": "Expense"},
    "5101": {"name": "EPF - Employer", "type": "Expense"},
    "5102": {"name": "SOCSO - Employer", "type": "Expense"},
    "5103": {"name": "EIS - Employer", "type": "Expense"},
    "5200": {"name": "F&B Expenses", "type": "Expense"},
    "5201": {"name": "Venue Expenses", "type": "Expense"},
    "5202": {"name": "HRDCorp Levy", "type": "Expense"},
    "5300": {"name": "Petty Cash Expenses", "type": "Expense"},
    "5400": {"name": "Other Expenses", "type": "Expense"},
}


@api_router.get("/finance/chart-of-accounts")
async def get_chart_of_accounts(current_user: User = Depends(get_current_user)):
    """Get the Chart of Accounts"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    accounts = []
    for code, info in sorted(CHART_OF_ACCOUNTS.items()):
        accounts.append({
            "code": code,
            "name": info["name"],
            "type": info["type"]
        })
    return accounts


@api_router.get("/finance/general-ledger")
async def get_general_ledger(
    year: int = None,
    month: int = None,
    current_user: User = Depends(get_current_user)
):
    """Get General Ledger with double-entry transactions.
    
    Every transaction has matching Debit and Credit entries.
    Tags (session_id, programme, venue) are for reference only - not in GL.
    """
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    if month:
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
    else:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
    
    gl_entries = []
    entry_id = 1
    
    # Get programmes for mapping
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    programme_map = {p["id"]: p.get("name", "Unknown") for p in programmes}
    
    # Get sessions for the year
    sessions = await db.sessions.find({
        "start_date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(10000)
    session_map = {s.get("id"): s for s in sessions}
    
    # 1. INVOICES - DR Accounts Receivable, CR Training Income
    invoices = await db.invoices.find({
        "status": {"$in": ["approved", "issued", "paid"]}
    }, {"_id": 0}).to_list(10000)
    
    for inv in invoices:
        try:
            # Check if invoice is in our date range (by session date or created date)
            session_id = None
            session = None
            
            # Find session linked to this invoice
            for s in sessions:
                if s.get("invoice_id") == inv.get("id"):
                    session_id = s.get("id")
                    session = s
                    break
            
            if not session:
                # Fallback to created_at date
                inv_date = inv.get("created_at", "")[:10]
                if not (inv_date >= start_date and inv_date <= end_date):
                    continue
            
            amount = float(inv.get("total_amount") or inv.get("amount") or 0)
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date") if session else inv.get("created_at", "")[:10]
            ref = inv.get("invoice_number", f"INV-{inv.get('id', '')[:8]}")
            programme = programme_map.get(session.get("program_id"), "General") if session else "General"
            
            # Determine income account based on programme
            income_account = "4000"  # Default
            prog_name = programme.lower() if programme else ""
            if "car" in prog_name:
                income_account = "4001"
            elif "motorcycle" in prog_name or "motor" in prog_name:
                income_account = "4002"
            elif "heavy" in prog_name or "truck" in prog_name:
                income_account = "4003"
            elif "bus" in prog_name:
                income_account = "4004"
            
            # Debit AR, Credit Income
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": ref,
                "description": f"Invoice issued - {inv.get('company_name', 'Customer')}",
                "account_code": "1100",
                "account_name": CHART_OF_ACCOUNTS["1100"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"session_id": session_id, "programme": programme}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": ref,
                "description": f"Invoice issued - {inv.get('company_name', 'Customer')}",
                "account_code": income_account,
                "account_name": CHART_OF_ACCOUNTS[income_account]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"session_id": session_id, "programme": programme}
            })
            entry_id += 1
        except:
            pass
    
    # 2. PAYMENTS RECEIVED - DR Bank, CR Accounts Receivable
    payments = await db.payments.find({}, {"_id": 0}).to_list(10000)
    for pmt in payments:
        try:
            pmt_date = pmt.get("payment_date", pmt.get("created_at", ""))[:10]
            if not (pmt_date >= start_date and pmt_date <= end_date):
                continue
            
            amount = float(pmt.get("amount", 0))
            if amount <= 0:
                continue
            
            ref = pmt.get("reference", f"PMT-{pmt.get('id', '')[:8]}")
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": pmt_date,
                "reference": ref,
                "description": f"Payment received - {pmt.get('payment_method', 'Bank')}",
                "account_code": "1001",
                "account_name": CHART_OF_ACCOUNTS["1001"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": pmt_date,
                "reference": ref,
                "description": f"Payment received - {pmt.get('payment_method', 'Bank')}",
                "account_code": "1100",
                "account_name": CHART_OF_ACCOUNTS["1100"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {}
            })
            entry_id += 1
        except:
            pass
    
    # 3. TRAINER FEES - DR Trainer Fees Expense, CR Trainer Payable
    session_ids = set(session_map.keys())
    trainer_fees = await db.trainer_fees.find({}, {"_id": 0}).to_list(10000)
    for tf in trainer_fees:
        try:
            session_id = tf.get("session_id")
            if session_id not in session_ids:
                continue
            
            session = session_map.get(session_id, {})
            amount = float(tf.get("fee_amount", 0))
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date", tf.get("created_at", "")[:10])
            programme = programme_map.get(session.get("program_id"), "Unknown")
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"TF-{session_id[:8]}",
                "description": f"Trainer fee accrual - {tf.get('trainer_name', 'Trainer')}",
                "account_code": "5001",
                "account_name": CHART_OF_ACCOUNTS["5001"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"session_id": session_id, "programme": programme, "trainer_id": tf.get("trainer_id")}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"TF-{session_id[:8]}",
                "description": f"Trainer fee accrual - {tf.get('trainer_name', 'Trainer')}",
                "account_code": "2100",
                "account_name": CHART_OF_ACCOUNTS["2100"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"session_id": session_id, "programme": programme, "trainer_id": tf.get("trainer_id")}
            })
            entry_id += 1
        except:
            pass
    
    # 4. COORDINATOR FEES - DR Coordinator Fees Expense, CR Coordinator Payable
    coordinator_fees = await db.coordinator_fees.find({}, {"_id": 0}).to_list(10000)
    for cf in coordinator_fees:
        try:
            session_id = cf.get("session_id")
            if session_id not in session_ids:
                continue
            
            session = session_map.get(session_id, {})
            amount = float(cf.get("total_fee", 0))
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date", cf.get("created_at", "")[:10])
            programme = programme_map.get(session.get("program_id"), "Unknown")
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"CF-{session_id[:8]}",
                "description": f"Coordinator fee accrual - {cf.get('coordinator_name', 'Coordinator')}",
                "account_code": "5002",
                "account_name": CHART_OF_ACCOUNTS["5002"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"session_id": session_id, "programme": programme}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"CF-{session_id[:8]}",
                "description": f"Coordinator fee accrual - {cf.get('coordinator_name', 'Coordinator')}",
                "account_code": "2101",
                "account_name": CHART_OF_ACCOUNTS["2101"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"session_id": session_id, "programme": programme}
            })
            entry_id += 1
        except:
            pass
    
    # 5. MARKETING COMMISSIONS - DR Marketing Expense, CR Marketing Payable
    marketing_comms = await db.marketing_commissions.find({
        "status": {"$in": ["approved", "paid"]}
    }, {"_id": 0}).to_list(10000)
    for mc in marketing_comms:
        try:
            session_id = mc.get("session_id")
            if session_id not in session_ids:
                continue
            
            session = session_map.get(session_id, {})
            amount = float(mc.get("calculated_amount", 0))
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date", mc.get("created_at", "")[:10])
            programme = programme_map.get(session.get("program_id"), "Unknown")
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"MC-{session_id[:8]}",
                "description": f"Marketing commission - {mc.get('marketer_name', 'Marketer')}",
                "account_code": "5003",
                "account_name": CHART_OF_ACCOUNTS["5003"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"session_id": session_id, "programme": programme, "marketer_id": mc.get("marketing_user_id")}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"MC-{session_id[:8]}",
                "description": f"Marketing commission - {mc.get('marketer_name', 'Marketer')}",
                "account_code": "2102",
                "account_name": CHART_OF_ACCOUNTS["2102"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"session_id": session_id, "programme": programme, "marketer_id": mc.get("marketing_user_id")}
            })
            entry_id += 1
        except:
            pass
    
    # 6. PAYROLL - DR Salaries & Employer Contributions, CR Payables
    payslips = await db.hr_payslips.find({"year": year}, {"_id": 0}).to_list(1000)
    if month:
        payslips = [p for p in payslips if p.get("month") == month]
    
    for ps in payslips:
        try:
            gross = float(ps.get("gross_salary", 0))
            epf_er = float(ps.get("epf_employer", 0))
            socso_er = float(ps.get("socso_employer", 0))
            eis_er = float(ps.get("eis_employer", 0))
            epf_ee = float(ps.get("epf_employee", 0))
            socso_ee = float(ps.get("socso_employee", 0))
            eis_ee = float(ps.get("eis_employee", 0))
            net_pay = float(ps.get("nett_pay", 0))
            
            m = ps.get("month", 1)
            trans_date = f"{year}-{m:02d}-28"  # End of month
            ref = f"PAY-{year}{m:02d}"
            emp_name = ps.get("full_name", "Staff")
            
            # DR Salaries (gross)
            if gross > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"Salary - {emp_name}",
                    "account_code": "5100",
                    "account_name": CHART_OF_ACCOUNTS["5100"]["name"],
                    "debit": gross,
                    "credit": 0,
                    "tags": {"employee": emp_name}
                })
            
            # DR Employer EPF
            if epf_er > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"EPF Employer - {emp_name}",
                    "account_code": "5101",
                    "account_name": CHART_OF_ACCOUNTS["5101"]["name"],
                    "debit": epf_er,
                    "credit": 0,
                    "tags": {"employee": emp_name}
                })
            
            # DR Employer SOCSO
            if socso_er > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"SOCSO Employer - {emp_name}",
                    "account_code": "5102",
                    "account_name": CHART_OF_ACCOUNTS["5102"]["name"],
                    "debit": socso_er,
                    "credit": 0,
                    "tags": {"employee": emp_name}
                })
            
            # DR Employer EIS
            if eis_er > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"EIS Employer - {emp_name}",
                    "account_code": "5103",
                    "account_name": CHART_OF_ACCOUNTS["5103"]["name"],
                    "debit": eis_er,
                    "credit": 0,
                    "tags": {"employee": emp_name}
                })
            
            # CR EPF Payable (employee + employer)
            total_epf = epf_ee + epf_er
            if total_epf > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"EPF Payable - {emp_name}",
                    "account_code": "2200",
                    "account_name": CHART_OF_ACCOUNTS["2200"]["name"],
                    "debit": 0,
                    "credit": total_epf,
                    "tags": {"employee": emp_name}
                })
            
            # CR SOCSO Payable
            total_socso = socso_ee + socso_er
            if total_socso > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"SOCSO Payable - {emp_name}",
                    "account_code": "2201",
                    "account_name": CHART_OF_ACCOUNTS["2201"]["name"],
                    "debit": 0,
                    "credit": total_socso,
                    "tags": {"employee": emp_name}
                })
            
            # CR EIS Payable
            total_eis = eis_ee + eis_er
            if total_eis > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"EIS Payable - {emp_name}",
                    "account_code": "2202",
                    "account_name": CHART_OF_ACCOUNTS["2202"]["name"],
                    "debit": 0,
                    "credit": total_eis,
                    "tags": {"employee": emp_name}
                })
            
            # CR Salary Payable (net)
            if net_pay > 0:
                gl_entries.append({
                    "entry_id": entry_id,
                    "date": trans_date,
                    "reference": ref,
                    "description": f"Salary Payable - {emp_name}",
                    "account_code": "2210",
                    "account_name": CHART_OF_ACCOUNTS["2210"]["name"],
                    "debit": 0,
                    "credit": net_pay,
                    "tags": {"employee": emp_name}
                })
            
            entry_id += 1
        except:
            pass
    
    # 7. SESSION EXPENSES (F&B, Venue, etc.)
    session_expenses = await db.session_expenses.find({}, {"_id": 0}).to_list(10000)
    for exp in session_expenses:
        try:
            session_id = exp.get("session_id")
            if session_id not in session_ids:
                continue
            
            session = session_map.get(session_id, {})
            amount = float(exp.get("actual_amount") or exp.get("estimated_amount") or exp.get("amount") or 0)
            if amount <= 0:
                continue
            
            trans_date = session.get("start_date", exp.get("created_at", "")[:10])
            programme = programme_map.get(session.get("program_id"), "Unknown")
            exp_type = exp.get("expense_type", "").lower()
            
            # Determine account based on expense type
            if "f&b" in exp_type or "food" in exp_type or "beverage" in exp_type:
                account = "5200"
            elif "venue" in exp_type:
                account = "5201"
            elif "hrdc" in exp_type or "levy" in exp_type:
                account = "5202"
            else:
                account = "5400"
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"SE-{session_id[:8]}",
                "description": f"Session expense - {exp.get('expense_type', 'Expense')}",
                "account_code": account,
                "account_name": CHART_OF_ACCOUNTS[account]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"session_id": session_id, "programme": programme}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"SE-{session_id[:8]}",
                "description": f"Session expense - {exp.get('expense_type', 'Expense')}",
                "account_code": "2001",
                "account_name": CHART_OF_ACCOUNTS["2001"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"session_id": session_id, "programme": programme}
            })
            entry_id += 1
        except:
            pass
    
    # 8. PETTY CASH EXPENSES
    petty_cash = await db.petty_cash_transactions.find({
        "date": {"$gte": start_date, "$lte": end_date},
        "type": "expense",
        "status": "approved"
    }, {"_id": 0}).to_list(1000)
    
    for pc in petty_cash:
        try:
            amount = float(pc.get("amount", 0))
            if amount <= 0:
                continue
            
            trans_date = pc.get("date", "")[:10]
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"PC-{pc.get('id', '')[:8]}",
                "description": f"Petty cash - {pc.get('description', 'Expense')}",
                "account_code": "5300",
                "account_name": CHART_OF_ACCOUNTS["5300"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"category": pc.get("category")}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"PC-{pc.get('id', '')[:8]}",
                "description": f"Petty cash - {pc.get('description', 'Expense')}",
                "account_code": "1002",
                "account_name": CHART_OF_ACCOUNTS["1002"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"category": pc.get("category")}
            })
            entry_id += 1
        except:
            pass
    
    # 9. MANUAL INCOME
    manual_income = await db.manual_income.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(1000)
    
    for mi in manual_income:
        try:
            amount = float(mi.get("amount", 0))
            if amount <= 0:
                continue
            
            trans_date = mi.get("date", "")[:10]
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"MI-{mi.get('id', '')[:8]}",
                "description": f"Other income - {mi.get('description', 'Income')}",
                "account_code": "1001",
                "account_name": CHART_OF_ACCOUNTS["1001"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"category": mi.get("category")}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"MI-{mi.get('id', '')[:8]}",
                "description": f"Other income - {mi.get('description', 'Income')}",
                "account_code": "4100",
                "account_name": CHART_OF_ACCOUNTS["4100"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"category": mi.get("category")}
            })
            entry_id += 1
        except:
            pass
    
    # 10. MANUAL EXPENSES
    manual_expenses = await db.manual_expenses.find({
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).to_list(1000)
    
    for me in manual_expenses:
        try:
            amount = float(me.get("amount", 0))
            if amount <= 0:
                continue
            
            trans_date = me.get("date", "")[:10]
            
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"ME-{me.get('id', '')[:8]}",
                "description": f"Other expense - {me.get('description', 'Expense')}",
                "account_code": "5400",
                "account_name": CHART_OF_ACCOUNTS["5400"]["name"],
                "debit": amount,
                "credit": 0,
                "tags": {"category": me.get("category")}
            })
            gl_entries.append({
                "entry_id": entry_id,
                "date": trans_date,
                "reference": f"ME-{me.get('id', '')[:8]}",
                "description": f"Other expense - {me.get('description', 'Expense')}",
                "account_code": "1001",
                "account_name": CHART_OF_ACCOUNTS["1001"]["name"],
                "debit": 0,
                "credit": amount,
                "tags": {"category": me.get("category")}
            })
            entry_id += 1
        except:
            pass
    
    # Sort by date, then entry_id
    gl_entries.sort(key=lambda x: (x["date"], x["entry_id"]))
    
    # Calculate totals
    total_debit = sum(e["debit"] for e in gl_entries)
    total_credit = sum(e["credit"] for e in gl_entries)
    
    # Generate trial balance (aggregated by account)
    trial_balance = {}
    for entry in gl_entries:
        code = entry["account_code"]
        if code not in trial_balance:
            trial_balance[code] = {
                "account_code": code,
                "account_name": entry["account_name"],
                "account_type": CHART_OF_ACCOUNTS.get(code, {}).get("type", "Unknown"),
                "debit": 0,
                "credit": 0
            }
        trial_balance[code]["debit"] += entry["debit"]
        trial_balance[code]["credit"] += entry["credit"]
    
    # Calculate net balance per account
    for code, bal in trial_balance.items():
        bal["net"] = bal["debit"] - bal["credit"]
    
    trial_balance_list = sorted(trial_balance.values(), key=lambda x: x["account_code"])
    
    return {
        "year": year,
        "month": month,
        "entries": gl_entries,
        "trial_balance": trial_balance_list,
        "totals": {
            "total_debit": total_debit,
            "total_credit": total_credit,
            "is_balanced": abs(total_debit - total_credit) < 0.01
        }
    }


@api_router.post("/finance/manual-income")
async def add_manual_income(entry: ManualIncomeEntry, current_user: User = Depends(get_current_user)):
    """Add a one-off manual income entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = {
        "id": str(uuid.uuid4()),
        "description": entry.description,
        "amount": entry.amount,
        "category": entry.category,
        "date": entry.date,
        "notes": entry.notes,
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    await db.manual_income.insert_one(record)
    return {"message": "Income entry added", "id": record["id"]}

@api_router.get("/finance/manual-income")
async def get_manual_income(year: int = None, current_user: User = Depends(get_current_user)):
    """Get manual income entries"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        query["date"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    
    entries = await db.manual_income.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return entries

@api_router.delete("/finance/manual-income/{entry_id}")
async def delete_manual_income(entry_id: str, current_user: User = Depends(get_current_user)):
    """Delete a manual income entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.manual_income.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Entry deleted"}

@api_router.post("/finance/manual-expense")
async def add_manual_expense(entry: ManualExpenseEntry, current_user: User = Depends(get_current_user)):
    """Add a one-off manual expense entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    record = {
        "id": str(uuid.uuid4()),
        "description": entry.description,
        "amount": entry.amount,
        "category": entry.category,
        "date": entry.date,
        "notes": entry.notes,
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    await db.manual_expenses.insert_one(record)
    return {"message": "Expense entry added", "id": record["id"]}

@api_router.get("/finance/manual-expenses")
async def get_manual_expenses(year: int = None, current_user: User = Depends(get_current_user)):
    """Get manual expense entries"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        query["date"] = {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}
    
    entries = await db.manual_expenses.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return entries

@api_router.delete("/finance/manual-expense/{entry_id}")
async def delete_manual_expense(entry_id: str, current_user: User = Depends(get_current_user)):
    """Delete a manual expense entry"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.manual_expenses.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Entry deleted"}


# ==================== PETTY CASH MODULE APIs ====================

class PettyCashSetup(BaseModel):
    float_amount: float
    custodian_id: Optional[str] = None
    custodian_name: Optional[str] = None
    approval_threshold: float = 100.0

class PettyCashTransaction(BaseModel):
    type: str
    amount: float
    description: str
    category: Optional[str] = None
    receipt_url: Optional[str] = None
    date: str
    notes: Optional[str] = None

class PettyCashReconciliation(BaseModel):
    physical_count: float
    notes: Optional[str] = None

@api_router.get("/finance/petty-cash/settings")
async def get_petty_cash_settings(current_user: User = Depends(get_current_user)):
    """Get petty cash settings"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.petty_cash_settings.find_one({}, {"_id": 0})
    if not settings:
        settings = {
            "float_amount": 500.0,
            "current_balance": 500.0,
            "custodian_id": None,
            "custodian_name": None,
            "approval_threshold": 100.0,
            "last_reconciliation": None
        }
    return settings

@api_router.post("/finance/petty-cash/setup")
async def setup_petty_cash(setup: PettyCashSetup, current_user: User = Depends(get_current_user)):
    """Setup or update petty cash settings"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = await db.petty_cash_settings.find_one({})
    
    settings = {
        "float_amount": setup.float_amount,
        "current_balance": setup.float_amount if not existing else existing.get("current_balance", setup.float_amount),
        "custodian_id": setup.custodian_id,
        "custodian_name": setup.custodian_name,
        "approval_threshold": setup.approval_threshold,
        "updated_at": get_malaysia_time().isoformat(),
        "updated_by": current_user.id
    }
    
    if existing:
        await db.petty_cash_settings.update_one({}, {"$set": settings})
    else:
        settings["created_at"] = get_malaysia_time().isoformat()
        settings["last_reconciliation"] = None
        await db.petty_cash_settings.insert_one(settings)
    
    return {"message": "Petty cash settings updated", "settings": {k: v for k, v in settings.items() if k != "_id"}}

@api_router.post("/finance/petty-cash/transaction")
async def add_petty_cash_transaction(txn: PettyCashTransaction, current_user: User = Depends(get_current_user)):
    """Add a petty cash transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.petty_cash_settings.find_one({})
    if not settings:
        raise HTTPException(status_code=400, detail="Petty cash not set up")
    
    current_balance = settings.get("current_balance", 0)
    
    if txn.type == "expense":
        if txn.amount > current_balance:
            raise HTTPException(status_code=400, detail=f"Insufficient balance. Current: RM {current_balance:.2f}")
        new_balance = current_balance - txn.amount
    elif txn.type == "topup":
        new_balance = current_balance + txn.amount
    else:
        raise HTTPException(status_code=400, detail="Invalid type")
    
    requires_approval = txn.type == "expense" and txn.amount > settings.get("approval_threshold", 100)
    
    transaction = {
        "id": str(uuid.uuid4()),
        "type": txn.type,
        "amount": txn.amount,
        "description": txn.description,
        "category": txn.category or "Miscellaneous",
        "receipt_url": txn.receipt_url,
        "date": txn.date,
        "notes": txn.notes,
        "balance_before": current_balance,
        "balance_after": new_balance,
        "status": "pending" if requires_approval else "approved",
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": get_malaysia_time().isoformat(),
        "approved_by": None if requires_approval else current_user.id,
        "approved_at": None if requires_approval else get_malaysia_time().isoformat()
    }
    
    await db.petty_cash_transactions.insert_one(transaction)
    
    if not requires_approval:
        await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": new_balance}})
    
    return {
        "message": "Transaction added" + (" (pending approval)" if requires_approval else ""),
        "transaction_id": transaction["id"],
        "new_balance": new_balance if not requires_approval else current_balance,
        "requires_approval": requires_approval
    }

@api_router.get("/finance/petty-cash/transactions")
async def get_petty_cash_transactions(
    year: int = None,
    month: int = None,
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get petty cash transactions"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if year:
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        if month:
            start = f"{year}-{month:02d}-01"
            end = f"{year}-{month:02d}-31"
        query["date"] = {"$gte": start, "$lte": end}
    if status:
        query["status"] = status
    
    transactions = await db.petty_cash_transactions.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return transactions

@api_router.post("/finance/petty-cash/approve/{transaction_id}")
async def approve_petty_cash_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Approve a pending transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    txn = await db.petty_cash_transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if txn.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Not pending")
    
    await db.petty_cash_transactions.update_one(
        {"id": transaction_id},
        {"$set": {"status": "approved", "approved_by": current_user.id, "approved_at": get_malaysia_time().isoformat()}}
    )
    
    settings = await db.petty_cash_settings.find_one({})
    new_balance = settings.get("current_balance", 0)
    if txn.get("type") == "expense":
        new_balance -= txn.get("amount", 0)
    elif txn.get("type") == "topup":
        new_balance += txn.get("amount", 0)
    
    await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": new_balance}})
    return {"message": "Approved", "new_balance": new_balance}

@api_router.post("/finance/petty-cash/reject/{transaction_id}")
async def reject_petty_cash_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Reject a pending transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    txn = await db.petty_cash_transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    if txn.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Not pending")
    
    await db.petty_cash_transactions.update_one(
        {"id": transaction_id},
        {"$set": {"status": "rejected", "rejected_by": current_user.id, "rejected_at": get_malaysia_time().isoformat()}}
    )
    return {"message": "Rejected"}

@api_router.delete("/finance/petty-cash/transaction/{transaction_id}")
async def delete_petty_cash_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Delete a transaction"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    txn = await db.petty_cash_transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Not found")
    
    if txn.get("status") == "approved":
        settings = await db.petty_cash_settings.find_one({})
        current_balance = settings.get("current_balance", 0)
        if txn.get("type") == "expense":
            new_balance = current_balance + txn.get("amount", 0)
        elif txn.get("type") == "topup":
            new_balance = current_balance - txn.get("amount", 0)
        else:
            new_balance = current_balance
        await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": new_balance}})
    
    await db.petty_cash_transactions.delete_one({"id": transaction_id})
    return {"message": "Deleted"}

@api_router.post("/finance/petty-cash/reconcile")
async def reconcile_petty_cash(recon: PettyCashReconciliation, current_user: User = Depends(get_current_user)):
    """Reconcile petty cash"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.petty_cash_settings.find_one({})
    if not settings:
        raise HTTPException(status_code=400, detail="Not set up")
    
    system_balance = settings.get("current_balance", 0)
    variance = recon.physical_count - system_balance
    
    reconciliation = {
        "id": str(uuid.uuid4()),
        "date": get_malaysia_time().isoformat()[:10],
        "system_balance": system_balance,
        "physical_count": recon.physical_count,
        "variance": variance,
        "notes": recon.notes,
        "reconciled_by": current_user.id,
        "reconciled_by_name": current_user.full_name,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.petty_cash_reconciliations.insert_one(reconciliation)
    await db.petty_cash_settings.update_one({}, {"$set": {"current_balance": recon.physical_count, "last_reconciliation": reconciliation["date"]}})
    
    if abs(variance) > 0.01:
        adjustment = {
            "id": str(uuid.uuid4()),
            "type": "adjustment",
            "amount": abs(variance),
            "description": f"Reconciliation adjustment",
            "category": "Adjustment",
            "date": get_malaysia_time().isoformat()[:10],
            "notes": recon.notes,
            "balance_before": system_balance,
            "balance_after": recon.physical_count,
            "status": "approved",
            "created_by": current_user.id,
            "created_by_name": current_user.full_name,
            "created_at": get_malaysia_time().isoformat(),
            "approved_by": current_user.id,
            "approved_at": get_malaysia_time().isoformat()
        }
        await db.petty_cash_transactions.insert_one(adjustment)
    
    return {"message": "Complete", "system_balance": system_balance, "physical_count": recon.physical_count, "variance": variance, "new_balance": recon.physical_count}

@api_router.get("/finance/petty-cash/reconciliations")
async def get_reconciliation_history(current_user: User = Depends(get_current_user)):
    """Get reconciliation history"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    reconciliations = await db.petty_cash_reconciliations.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return reconciliations

@api_router.get("/finance/petty-cash/summary")
async def get_petty_cash_summary(year: int = None, current_user: User = Depends(get_current_user)):
    """Get petty cash summary"""
    if current_user.role not in ["admin", "finance"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    year = year or now.year
    
    query = {"date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}, "type": "expense", "status": "approved"}
    transactions = await db.petty_cash_transactions.find(query, {"_id": 0}).to_list(10000)
    
    by_category = {}
    for txn in transactions:
        cat = txn.get("category", "Miscellaneous")
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += txn.get("amount", 0)
    
    by_month = {}
    for txn in transactions:
        try:
            m = int(txn.get("date", "")[5:7])
            if m not in by_month:
                by_month[m] = 0
            by_month[m] += txn.get("amount", 0)
        except:
            pass
    
    settings = await db.petty_cash_settings.find_one({}, {"_id": 0})
    
    return {
        "year": year,
        "current_balance": settings.get("current_balance", 0) if settings else 0,
        "float_amount": settings.get("float_amount", 0) if settings else 0,
        "by_category": by_category,
        "by_month": by_month,
        "total_expenses": sum(c["total"] for c in by_category.values())
    }


# ==================== HEALTH & SECURITY ADMIN ENDPOINTS ====================

@api_router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Quick DB check
        await db.command('ping')
        return {
            "status": "healthy",
            "timestamp": get_malaysia_time().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@api_router.get("/security/status")
async def security_status(current_user: User = Depends(get_current_user)):
    """Get security status (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "rate_limited_ips": len([ip for ip, times in rate_limit_storage.items() if len(times) >= RATE_LIMIT_REQUESTS]),
        "blocked_ips": len(BLOCKED_IPS),
        "locked_out_ips": len([ip for ip in FAILED_LOGIN_ATTEMPTS if len(FAILED_LOGIN_ATTEMPTS[ip]) >= MAX_FAILED_LOGINS]),
        "rate_limit_config": {
            "requests_per_window": RATE_LIMIT_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW
        },
        "login_security": {
            "max_failed_attempts": MAX_FAILED_LOGINS,
            "lockout_seconds": LOGIN_LOCKOUT_TIME
        }
    }

@api_router.post("/security/block-ip")
async def block_ip(ip: str, current_user: User = Depends(get_current_user)):
    """Block an IP address (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    BLOCKED_IPS.add(ip)
    logging.warning(f"IP blocked by admin {current_user.email}: {ip}")
    return {"message": f"IP {ip} blocked"}

@api_router.post("/security/unblock-ip")
async def unblock_ip(ip: str, current_user: User = Depends(get_current_user)):
    """Unblock an IP address (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    BLOCKED_IPS.discard(ip)
    clear_failed_logins(ip)
    logging.info(f"IP unblocked by admin {current_user.email}: {ip}")
    return {"message": f"IP {ip} unblocked"}

@api_router.get("/security/audit-log")
async def get_security_audit(
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get security audit log (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get recent security events from audit log
    events = await db.security_audit.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return events


# ==================== MARKETING QUOTATION ENDPOINTS ====================

async def generate_quotation_number():
    """Generate quotation number in format QOU/MDDRC/YYYY/MM/0001"""
    now = get_malaysia_time()
    year = now.year
    month = now.month
    prefix = f"QOU/MDDRC/{year}/{month:02d}/"
    
    # Find the highest number for this month
    latest = await db.quotations.find_one(
        {"quotation_number": {"$regex": f"^{prefix}"}},
        sort=[("quotation_number", -1)]
    )
    
    if latest:
        try:
            last_num = int(latest["quotation_number"].split("/")[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"{prefix}{new_num:04d}"


def check_marketing_access(user):
    """Check if user has marketing access"""
    return user.role == "marketing" or "marketing" in (user.additional_roles or []) or user.role in ["admin", "super_admin"]


@api_router.get("/marketing/clients")
async def get_marketing_clients(current_user: User = Depends(get_current_user)):
    """Get clients - marketers see only their own, admin sees all"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    clients = await db.marketing_clients.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with marketer name for admin view
    if current_user.role in ["admin", "super_admin"]:
        user_ids = list(set(c.get("created_by") for c in clients if c.get("created_by")))
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "full_name": 1}).to_list(100)
        user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
        for c in clients:
            c["marketer_name"] = user_map.get(c.get("created_by"), "Unknown")
    
    return clients


@api_router.post("/marketing/clients")
async def create_marketing_client(client_data: MarketingClientCreate, current_user: User = Depends(get_current_user)):
    """Create a new client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Check if company already exists for this marketer
    existing = await db.marketing_clients.find_one({
        "company_name": {"$regex": f"^{client_data.company_name}$", "$options": "i"},
        "created_by": current_user.id
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a client with this company name")
    
    client = MarketingClient(
        **client_data.model_dump(),
        created_by=current_user.id
    )
    
    await db.marketing_clients.insert_one(client.model_dump())
    return {"message": "Client created successfully", "client": client.model_dump()}


@api_router.put("/marketing/clients/{client_id}")
async def update_marketing_client(client_id: str, client_data: dict, current_user: User = Depends(get_current_user)):
    """Update a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check ownership unless admin
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own clients")
    
    update_fields = {k: v for k, v in client_data.items() if k not in ["id", "created_by", "created_at"]}
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    
    await db.marketing_clients.update_one({"id": client_id}, {"$set": update_fields})
    return {"message": "Client updated successfully"}


@api_router.delete("/marketing/clients/{client_id}")
async def delete_marketing_client(client_id: str, current_user: User = Depends(get_current_user)):
    """Delete a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check ownership unless admin
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own clients")
    
    # Check if client has quotations
    quotation_count = await db.quotations.count_documents({"client_id": client_id})
    if quotation_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete client with {quotation_count} quotation(s)")
    
    await db.marketing_clients.delete_one({"id": client_id})
    return {"message": "Client deleted successfully"}


@api_router.get("/marketing/clients/export")
async def export_all_clients(current_user: User = Depends(get_current_user)):
    """Admin only - Export all clients with marketer info as CSV"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all clients
    clients = await db.marketing_clients.find({}, {"_id": 0}).to_list(1000)
    
    # Get all users for marketer names
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u["full_name"] for u in users}
    
    # Build CSV
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Company Name",
        "Contact Person",
        "Email",
        "Phone",
        "Address",
        "Marketer",
        "Created Date"
    ])
    
    # Data rows
    for client in clients:
        marketer_id = client.get("created_by", "")
        marketer_name = user_map.get(marketer_id, "Unknown")
        created_at = client.get("created_at", "")
        if isinstance(created_at, datetime):
            created_at = created_at.strftime("%Y-%m-%d")
        
        writer.writerow([
            client.get("company_name", ""),
            client.get("contact_person", ""),
            client.get("contact_email", ""),
            client.get("contact_phone", ""),
            client.get("company_address", "").replace("\n", ", "),
            marketer_name,
            created_at
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    # Return as streaming response
    return StreamingResponse(
        BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="marketing_clients_{datetime.now().strftime("%Y%m%d")}.csv"'
        }
    )


@api_router.get("/marketing/clients/all")
async def get_all_clients_admin(current_user: User = Depends(get_current_user)):
    """Admin only - Get all clients with marketer info"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all clients
    clients = await db.marketing_clients.find({}, {"_id": 0}).to_list(1000)
    
    # Get all users for marketer names
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u["full_name"] for u in users}
    
    # Enrich clients with marketer names
    for client in clients:
        marketer_id = client.get("created_by", "")
        client["marketer_name"] = user_map.get(marketer_id, "Unknown")
    
    return clients


@api_router.get("/marketing/quotations")
async def get_quotations(status: str = None, current_user: User = Depends(get_current_user)):
    """Get quotations - marketers see only their own, admin sees all"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    if status:
        query["status"] = status
    
    quotations = await db.quotations.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with client and marketer info
    client_ids = list(set(q.get("client_id") for q in quotations if q.get("client_id")))
    clients = await db.marketing_clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(100)
    client_map = {c["id"]: c for c in clients}
    
    user_ids = list(set(q.get("created_by") for q in quotations if q.get("created_by")))
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "full_name": 1}).to_list(100)
    user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
    
    for q in quotations:
        client = client_map.get(q.get("client_id"), {})
        q["client_name"] = client.get("company_name", "Unknown")
        q["contact_person"] = client.get("contact_person", "")
        q["marketer_name"] = user_map.get(q.get("created_by"), "Unknown")
    
    # Sort by created_at descending
    quotations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return quotations


@api_router.get("/marketing/stats")
async def get_marketing_stats(current_user: User = Depends(get_current_user)):
    """Get marketing stats for dashboard"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    # Client count
    client_query = {}
    if current_user.role not in ["admin", "super_admin"]:
        client_query["created_by"] = current_user.id
    client_count = await db.marketing_clients.count_documents(client_query)
    
    # Quotation counts by status
    total_quotations = await db.quotations.count_documents(query)
    pending = await db.quotations.count_documents({**query, "status": "pending_approval"})
    approved = await db.quotations.count_documents({**query, "status": "approved"})
    sent = await db.quotations.count_documents({**query, "status": "sent"})
    accepted = await db.quotations.count_documents({**query, "status": "accepted"})
    declined = await db.quotations.count_documents({**query, "status": "declined"})
    
    # Total value of accepted quotations
    accepted_quotations = await db.quotations.find({**query, "status": "accepted"}, {"_id": 0, "total_amount": 1}).to_list(1000)
    total_accepted_value = sum(q.get("total_amount", 0) for q in accepted_quotations)
    
    return {
        "clients": client_count,
        "total_quotations": total_quotations,
        "pending_approval": pending,
        "approved": approved,
        "sent": sent,
        "accepted": accepted,
        "declined": declined,
        "total_accepted_value": total_accepted_value
    }


@api_router.get("/marketing/programmes")
async def get_programmes_for_quotation(current_user: User = Depends(get_current_user)):
    """Get programmes list for quotation creation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1, "category": 1, "description": 1}).to_list(100)
    return programmes


@api_router.get("/marketing/default-terms")
async def get_default_terms(current_user: User = Depends(get_current_user)):
    """Get default terms and conditions for quotations"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    settings = await db.company_settings.find_one({}, {"_id": 0})
    default_terms = settings.get("quotation_terms", """1. This quotation is valid for 30 days from the date of issue.
2. A 50% deposit is required upon confirmation.
3. Full payment must be made before the training date.
4. Cancellation within 7 days of training will incur a 50% cancellation fee.
5. Prices are subject to SST where applicable.""") if settings else """1. This quotation is valid for 30 days from the date of issue.
2. A 50% deposit is required upon confirmation.
3. Full payment must be made before the training date.
4. Cancellation within 7 days of training will incur a 50% cancellation fee.
5. Prices are subject to SST where applicable."""
    
    return {"terms": default_terms}


@api_router.get("/marketing/quotations/{quotation_id}")
async def get_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Get a single quotation with full details"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Check ownership unless admin
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Enrich with client info
    client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
    quotation["client"] = client
    
    # Enrich with marketer info
    marketer = await db.users.find_one({"id": quotation.get("created_by")}, {"_id": 0, "full_name": 1, "email": 1})
    quotation["marketer"] = marketer
    
    # Enrich with approver info
    if quotation.get("approved_by"):
        approver = await db.users.find_one({"id": quotation.get("approved_by")}, {"_id": 0, "full_name": 1})
        quotation["approver"] = approver
    
    return quotation


@api_router.post("/marketing/quotations")
async def create_quotation(quotation_data: QuotationCreate, current_user: User = Depends(get_current_user)):
    """Create a new quotation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Verify client exists and belongs to marketer
    client = await db.marketing_clients.find_one({"id": quotation_data.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role not in ["admin", "super_admin"] and client.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="This client belongs to another marketer")
    
    # Verify programme exists
    programme = await db.programs.find_one({"id": quotation_data.programme_id}, {"_id": 0})
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")
    
    # Calculate amounts based on pricing type
    if quotation_data.pricing_type == "per_group":
        subtotal = quotation_data.group_price
    else:  # per_pax
        subtotal = quotation_data.num_participants * quotation_data.rate_per_pax
    
    sst_amount = subtotal * (quotation_data.sst_percent / 100)
    total_amount = subtotal + sst_amount
    
    # Calculate validity date
    now = get_malaysia_time()
    valid_until = (now + timedelta(days=quotation_data.validity_days)).strftime("%Y-%m-%d")
    
    # Generate quotation number
    quotation_number = await generate_quotation_number()
    
    quotation = Quotation(
        quotation_number=quotation_number,
        client_id=quotation_data.client_id,
        programme_id=quotation_data.programme_id,
        programme_name=programme.get("name", "Unknown Programme"),
        pricing_type=quotation_data.pricing_type,
        num_participants=quotation_data.num_participants,
        rate_per_pax=quotation_data.rate_per_pax,
        group_price=quotation_data.group_price,
        subtotal=subtotal,
        sst_percent=quotation_data.sst_percent,
        sst_amount=sst_amount,
        total_amount=total_amount,
        validity_days=quotation_data.validity_days,
        valid_until=valid_until,
        description_items=quotation_data.description_items,
        selected_items=quotation_data.selected_items,
        custom_description=quotation_data.custom_description,
        remarks=quotation_data.remarks,
        terms_conditions=quotation_data.terms_conditions,
        status="draft",
        status_history=[{
            "status": "draft",
            "by": current_user.id,
            "by_name": current_user.full_name,
            "at": now.isoformat(),
            "remarks": "Quotation created"
        }],
        created_by=current_user.id
    )
    
    await db.quotations.insert_one(quotation.model_dump())
    return {"message": "Quotation created successfully", "quotation": quotation.model_dump()}


@api_router.put("/marketing/quotations/{quotation_id}")
async def update_quotation(quotation_id: str, quotation_data: QuotationUpdate, current_user: User = Depends(get_current_user)):
    """Update a quotation (only if draft)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Check ownership unless admin
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own quotations")
    
    # Only allow editing if draft or rejected (for revision)
    if quotation.get("status") not in ["draft", "rejected"]:
        raise HTTPException(status_code=400, detail="Can only edit quotations in draft or rejected status")
    
    update_fields = {}
    data = quotation_data.model_dump(exclude_none=True)
    
    # Recalculate amounts if pricing changed
    num_pax = data.get("num_participants", quotation.get("num_participants"))
    rate = data.get("rate_per_pax", quotation.get("rate_per_pax"))
    sst_pct = data.get("sst_percent", quotation.get("sst_percent"))
    validity = data.get("validity_days", quotation.get("validity_days"))
    
    subtotal = num_pax * rate
    sst_amount = subtotal * (sst_pct / 100)
    total_amount = subtotal + sst_amount
    
    now = get_malaysia_time()
    valid_until = (now + timedelta(days=validity)).strftime("%Y-%m-%d")
    
    update_fields.update({
        "num_participants": num_pax,
        "rate_per_pax": rate,
        "sst_percent": sst_pct,
        "subtotal": subtotal,
        "sst_amount": sst_amount,
        "total_amount": total_amount,
        "validity_days": validity,
        "valid_until": valid_until,
        "remarks": data.get("remarks", quotation.get("remarks")),
        "terms_conditions": data.get("terms_conditions", quotation.get("terms_conditions")),
        "updated_at": now.isoformat()
    })
    
    # If it was rejected, reset to draft
    if quotation.get("status") == "rejected":
        update_fields["status"] = "draft"
        status_history = quotation.get("status_history", [])
        status_history.append({
            "status": "draft",
            "by": current_user.id,
            "by_name": current_user.full_name,
            "at": now.isoformat(),
            "remarks": "Revised after rejection"
        })
        update_fields["status_history"] = status_history
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_fields})
    return {"message": "Quotation updated successfully"}


@api_router.post("/marketing/quotations/{quotation_id}/submit")
async def submit_quotation_for_approval(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Submit quotation for admin approval"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only submit your own quotations")
    
    if quotation.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft quotations can be submitted")
    
    now = get_malaysia_time()
    status_history = quotation.get("status_history", [])
    status_history.append({
        "status": "pending_approval",
        "by": current_user.id,
        "by_name": current_user.full_name,
        "at": now.isoformat(),
        "remarks": "Submitted for approval"
    })
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {
            "status": "pending_approval",
            "status_history": status_history,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Quotation submitted for approval"}


@api_router.post("/marketing/quotations/{quotation_id}/approve")
async def approve_quotation(quotation_id: str, remarks: str = None, current_user: User = Depends(get_current_user)):
    """Admin approve quotation"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admin can approve quotations")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Quotation is not pending approval")
    
    now = get_malaysia_time()
    status_history = quotation.get("status_history", [])
    status_history.append({
        "status": "approved",
        "by": current_user.id,
        "by_name": current_user.full_name,
        "at": now.isoformat(),
        "remarks": remarks or "Approved"
    })
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {
            "status": "approved",
            "status_history": status_history,
            "approved_by": current_user.id,
            "approved_at": now.isoformat(),
            "admin_remarks": remarks,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Quotation approved"}


@api_router.post("/marketing/quotations/{quotation_id}/reject")
async def reject_quotation(quotation_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin reject quotation"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admin can reject quotations")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Quotation is not pending approval")
    
    remarks = data.get("remarks", "")
    now = get_malaysia_time()
    status_history = quotation.get("status_history", [])
    status_history.append({
        "status": "rejected",
        "by": current_user.id,
        "by_name": current_user.full_name,
        "at": now.isoformat(),
        "remarks": remarks
    })
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {
            "status": "rejected",
            "status_history": status_history,
            "admin_remarks": remarks,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Quotation rejected"}


@api_router.post("/marketing/quotations/{quotation_id}/mark-sent")
async def mark_quotation_sent(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Mark quotation as sent to client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own quotations")
    
    if quotation.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved quotations can be marked as sent")
    
    now = get_malaysia_time()
    status_history = quotation.get("status_history", [])
    status_history.append({
        "status": "sent",
        "by": current_user.id,
        "by_name": current_user.full_name,
        "at": now.isoformat(),
        "remarks": "Sent to client"
    })
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {
            "status": "sent",
            "status_history": status_history,
            "sent_at": now.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Quotation marked as sent"}


@api_router.post("/marketing/quotations/{quotation_id}/client-response")
async def update_client_response(quotation_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update quotation with client's response (accepted/declined)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own quotations")
    
    if quotation.get("status") != "sent":
        raise HTTPException(status_code=400, detail="Only sent quotations can have client response")
    
    response = data.get("response")  # accepted or declined
    if response not in ["accepted", "declined"]:
        raise HTTPException(status_code=400, detail="Invalid response. Must be 'accepted' or 'declined'")
    
    now = get_malaysia_time()
    status_history = quotation.get("status_history", [])
    
    update_data = {
        "status": response,
        "status_history": status_history,
        "updated_at": now.isoformat()
    }
    
    # If accepting, require training_date and venue
    if response == "accepted":
        training_date = data.get("training_date")
        venue = data.get("venue")
        
        if not training_date or not venue:
            raise HTTPException(status_code=400, detail="Training date and venue are required when accepting quotation")
        
        update_data["training_date"] = training_date
        update_data["venue"] = venue
        update_data["accepted_at"] = now.isoformat()
        
        status_history.append({
            "status": response,
            "by": current_user.id,
            "by_name": current_user.full_name,
            "at": now.isoformat(),
            "remarks": f"Client accepted. Training: {training_date} at {venue}"
        })
    else:
        status_history.append({
            "status": response,
            "by": current_user.id,
            "by_name": current_user.full_name,
            "at": now.isoformat(),
            "remarks": data.get("remarks", f"Client {response}")
        })
    
    update_data["status_history"] = status_history
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": update_data}
    )
    
    return {"message": f"Quotation marked as {response}"}


# ==================== QUOTATION DESCRIPTION ITEMS (Admin) ====================

@api_router.get("/marketing/description-items")
async def get_description_items_legacy(current_user: User = Depends(get_current_user)):
    """LEGACY: Redirects to main endpoint in routes/marketing.py"""
    # This endpoint is shadowed by routes/marketing.py - keeping for reference
    pass


@api_router.get("/marketing/description-items/all")
async def get_all_description_items(current_user: User = Depends(get_current_user)):
    """Get all description items including inactive (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    items = await db.quotation_description_items.find({}, {"_id": 0}).to_list(100)
    items.sort(key=lambda x: (x.get("category", ""), x.get("sort_order", 0)))
    return items


@api_router.post("/marketing/description-items")
async def create_description_item(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new description item (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    item = QuotationDescriptionItem(
        name=data.get("name", ""),
        description=data.get("description", ""),
        category=data.get("category", "inclusion"),
        has_quantity=data.get("has_quantity", False),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True)
    )
    
    await db.quotation_description_items.insert_one(item.model_dump())
    return {"message": "Description item created", "item": item.model_dump()}


@api_router.put("/marketing/description-items/{item_id}")
async def update_description_item(item_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a description item (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_fields = {k: v for k, v in data.items() if k not in ["id", "created_at"]}
    await db.quotation_description_items.update_one({"id": item_id}, {"$set": update_fields})
    return {"message": "Description item updated"}


@api_router.delete("/marketing/description-items/{item_id}")
async def delete_description_item(item_id: str, current_user: User = Depends(get_current_user)):
    """Delete a description item (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await db.quotation_description_items.delete_one({"id": item_id})
    return {"message": "Description item deleted"}


# ==================== PDF TEMPLATES (Admin) ====================

@api_router.get("/marketing/pdf-templates")
async def get_pdf_templates(current_user: User = Depends(get_current_user)):
    """Get PDF templates for quotation generation"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    templates = await db.quotation_pdf_templates.find_one({"id": "quotation_pdf_templates"}, {"_id": 0})
    if not templates:
        # Return default empty templates
        return {
            "id": "quotation_pdf_templates",
            "cover_letter": "",
            "terms_conditions_pages": "",
            "updated_at": None,
            "updated_by": None
        }
    return templates


@api_router.put("/marketing/pdf-templates")
async def update_pdf_templates(data: dict, current_user: User = Depends(get_current_user)):
    """Update PDF templates for quotation generation (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = get_malaysia_time()
    update_data = {
        "id": "quotation_pdf_templates",
        "cover_letter": data.get("cover_letter", ""),
        "terms_conditions_pages": data.get("terms_conditions_pages", ""),
        "primary_color": data.get("primary_color", "#1a365d"),
        "updated_at": now.isoformat(),
        "updated_by": current_user.id
    }
    
    await db.quotation_pdf_templates.update_one(
        {"id": "quotation_pdf_templates"},
        {"$set": update_data},
        upsert=True
    )
    
    return {"message": "PDF templates updated successfully"}


# ==================== QUOTATION PDF GENERATION ====================

def sanitize_text_for_pdf(text):
    """Remove or replace characters that might cause font issues"""
    if not text:
        return ""
    # Replace common problematic characters
    replacements = {
        '–': '-',  # en-dash
        '—': '-',  # em-dash
        ''': "'",  # smart quote
        ''': "'",  # smart quote
        '"': '"',  # smart quote
        '"': '"',  # smart quote
        '…': '...',  # ellipsis
        '\u200b': '',  # zero-width space
        '\xa0': ' ',  # non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Filter out any remaining non-ASCII characters that might cause issues
    return ''.join(c if ord(c) < 256 else '-' for c in text)


def strip_html_tags(html_text):
    """Strip HTML tags and convert to plain text, preserving line breaks"""
    if not html_text:
        return ""
    import re
    # Replace <br>, </p>, </div>, </li> with newlines
    text = re.sub(r'<br\s*/?>', '\n', html_text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'</div>', '\n', text)
    text = re.sub(r'</li>', '\n', text)
    # Add bullet for <li>
    text = re.sub(r'<li>', '• ', text)
    # Replace headings with caps and newlines
    text = re.sub(r'<h[1-3][^>]*>(.*?)</h[1-3]>', r'\n\1\n', text, flags=re.IGNORECASE)
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


class QuotationPDF(FPDF):
    """Custom PDF class for quotation document generation - EXACT invoice styling"""
    
    def __init__(self, company_settings=None, primary_color_rgb=None):
        super().__init__()
        self.company_settings = company_settings or {}
        self.set_auto_page_break(auto=True, margin=30)  # Space for footer
        # Colors - use custom or default
        self.primary_color = primary_color_rgb if primary_color_rgb else (26, 54, 93)  # Dark blue #1a365d
        self.secondary_color = (68, 114, 196)  # Blue #4472C4
        # Add Unicode font support
        try:
            self.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
            self.add_font('DejaVu', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', uni=True)
            self.add_font('DejaVu', 'I', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf', uni=True)
            self.unicode_font = True
        except Exception:
            self.unicode_font = False
    
    def set_font_safe(self, style='', size=10):
        """Set font with fallback for Unicode support"""
        if self.unicode_font:
            self.set_font('DejaVu', style, size)
        else:
            self.set_font('Helvetica', style, size)
    
    def cell_safe(self, w, h, txt, **kwargs):
        """Cell with text sanitization"""
        self.cell(w, h, sanitize_text_for_pdf(txt), **kwargs)
    
    def multi_cell_safe(self, w, h, txt, **kwargs):
        """Multi-cell with text sanitization and wrapping"""
        self.multi_cell(w, h, sanitize_text_for_pdf(txt), **kwargs)
    
    def render_rich_text(self, text, line_height=5, default_size=10):
        """
        Render text with formatting tags:
        - **text** or <b>text</b> = Bold
        - *text* or <i>text</i> = Italic
        - <u>text</u> = Underline
        - <big>text</big> = Larger font (12pt)
        - <small>text</small> = Smaller font (8pt)
        - <highlight>text</highlight> or <hl>text</hl> = Yellow highlight
        - <red>text</red>, <blue>text</blue>, <green>text</green> = Colored text
        - <center>text</center> = Centered text
        - <br> or \n = Line break
        - <hr> = Horizontal line
        - <pb> or <pagebreak> = Page break (new page)
        """
        import re
        
        if not text:
            return
        
        # Process the text line by line
        lines = text.replace('<br>', '\n').replace('<br/>', '\n').split('\n')
        
        for line in lines:
            if not line.strip():
                self.ln(line_height)
                continue
            
            # Check for page break
            if '<pb>' in line or '<pagebreak>' in line or '<pb/>' in line:
                self.add_page()
                continue
            
            # Check for horizontal rule
            if '<hr>' in line or '<hr/>' in line:
                self.set_draw_color(180, 180, 180)
                self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
                self.ln(line_height + 2)
                continue
            
            # Check for centered text
            is_centered = '<center>' in line
            if is_centered:
                line = line.replace('<center>', '').replace('</center>', '')
            
            # Parse and render segments with formatting
            segments = self._parse_rich_segments(line)
            
            if is_centered:
                # Calculate total width for centering
                total_width = 0
                for seg in segments:
                    style = ''
                    if seg.get('bold'): style += 'B'
                    if seg.get('italic'): style += 'I'
                    size = seg.get('size', default_size)
                    self.set_font_safe(style, size)
                    total_width += self.get_string_width(sanitize_text_for_pdf(seg['text']))
                start_x = (210 - total_width) / 2
                self.set_x(start_x)
            
            # Calculate available width for text wrapping
            page_width = 210  # A4 width in mm
            left_margin = 10
            right_margin = 10
            max_x = page_width - right_margin
            start_x = self.get_x() if self.get_x() > left_margin else left_margin
            
            for seg in segments:
                # Apply formatting
                style = ''
                if seg.get('bold'):
                    style += 'B'
                if seg.get('italic'):
                    style += 'I'
                if seg.get('underline'):
                    style += 'U'
                
                size = seg.get('size', default_size)
                self.set_font_safe(style, size)
                
                # Apply color
                color = seg.get('color', (0, 0, 0))
                self.set_text_color(*color)
                
                seg_text = sanitize_text_for_pdf(seg['text'])
                
                # Word-wrap long segments
                words = seg_text.split(' ')
                current_line_words = []
                
                for word in words:
                    test_line = ' '.join(current_line_words + [word]) if current_line_words else word
                    test_width = self.get_string_width(test_line)
                    current_x = self.get_x()
                    
                    # Check if this word fits on current line
                    if current_x + test_width > max_x:
                        # Print current line if we have words
                        if current_line_words:
                            line_text = ' '.join(current_line_words)
                            line_width = self.get_string_width(line_text)
                            
                            # Apply highlight for this line portion
                            if seg.get('highlight'):
                                x, y = self.get_x(), self.get_y()
                                self.set_fill_color(255, 255, 0)
                                self.rect(x, y, line_width + 1, line_height, 'F')
                                self.set_xy(x, y)
                            
                            self.cell(line_width, line_height, line_text, ln=False)
                        
                        # Move to next line
                        self.ln(line_height)
                        self.set_x(left_margin)
                        current_line_words = [word]
                    else:
                        current_line_words.append(word)
                
                # Print remaining words
                if current_line_words:
                    line_text = ' '.join(current_line_words)
                    line_width = self.get_string_width(line_text)
                    
                    # Apply highlight
                    if seg.get('highlight'):
                        x, y = self.get_x(), self.get_y()
                        self.set_fill_color(255, 255, 0)
                        self.rect(x, y, line_width + 1, line_height, 'F')
                        self.set_xy(x, y)
                    
                    self.cell(line_width, line_height, line_text, ln=False)
                    
                    # Add space after segment if not at line end
                    if self.get_x() < max_x - 5:
                        self.cell(self.get_string_width(' '), line_height, '', ln=False)
            
            self.ln(line_height)
            self.set_text_color(0, 0, 0)  # Reset to black
    
    def _parse_rich_segments(self, text):
        """Parse text into segments with formatting attributes"""
        import re
        
        segments = []
        
        # Pattern to match formatting tags
        pattern = r'(\*\*([^*]+)\*\*|\*([^*]+)\*|<b>([^<]+)</b>|<i>([^<]+)</i>|<u>([^<]+)</u>|<big>([^<]+)</big>|<small>([^<]+)</small>|<highlight>([^<]+)</highlight>|<hl>([^<]+)</hl>|<red>([^<]+)</red>|<blue>([^<]+)</blue>|<green>([^<]+)</green>)'
        
        last_end = 0
        for match in re.finditer(pattern, text):
            # Add plain text before this match
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                if plain:
                    segments.append({'text': plain})
            
            # Determine formatting based on matched group
            full_match = match.group(0)
            
            if full_match.startswith('**') or full_match.startswith('<b>'):
                content = match.group(2) or match.group(4)
                segments.append({'text': content, 'bold': True})
            elif full_match.startswith('*') or full_match.startswith('<i>'):
                content = match.group(3) or match.group(5)
                segments.append({'text': content, 'italic': True})
            elif full_match.startswith('<u>'):
                segments.append({'text': match.group(6), 'underline': True})
            elif full_match.startswith('<big>'):
                segments.append({'text': match.group(7), 'size': 12})
            elif full_match.startswith('<small>'):
                segments.append({'text': match.group(8), 'size': 8})
            elif full_match.startswith('<highlight>') or full_match.startswith('<hl>'):
                content = match.group(9) or match.group(10)
                segments.append({'text': content, 'highlight': True, 'bold': True})
            elif full_match.startswith('<red>'):
                segments.append({'text': match.group(11), 'color': (200, 0, 0)})
            elif full_match.startswith('<blue>'):
                segments.append({'text': match.group(12), 'color': (0, 0, 200)})
            elif full_match.startswith('<green>'):
                segments.append({'text': match.group(13), 'color': (0, 150, 0)})
            
            last_end = match.end()
        
        # Add remaining plain text
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                segments.append({'text': remaining})
        
        # If no formatting found, return whole text as one segment
        if not segments:
            segments = [{'text': text}]
        
        return segments
    
    def header(self):
        """Header matching invoice PDF exactly - logo left, company info right, border below"""
        cs = self.company_settings
        
        # Get logo Y position from settings (default 5 for higher placement)
        logo_y = int(cs.get('logo_y') or 5)
        start_y = logo_y
        self.set_y(start_y)
        
        # Logo on the left - 100px in invoice ≈ 26mm in PDF
        logo_url = cs.get('logo_url')
        logo_width = 26
        logo_end_x = 10
        
        if logo_url:
            logo_path = None
            if logo_url.startswith('/api/static/'):
                logo_path = ROOT_DIR / logo_url.replace('/api/static/', 'static/')
            elif logo_url.startswith('/static/'):
                logo_path = ROOT_DIR / logo_url.lstrip('/')
            elif logo_url.startswith('/'):
                logo_path = ROOT_DIR / logo_url.lstrip('/')
            
            if logo_path and logo_path.exists():
                try:
                    # Place logo aligned with company name (same Y as text start)
                    self.image(str(logo_path), x=10, y=start_y - 2, w=logo_width)
                    logo_end_x = 10 + logo_width + 5
                except:
                    pass
        
        # Company details to the right of logo
        text_x = logo_end_x
        self.set_xy(text_x, start_y)
        
        # Company name - 18px bold in invoice ≈ 14pt
        self.set_font_safe('B', 14)
        self.set_text_color(*self.primary_color)
        company_name = cs.get('company_name', 'MALAYSIAN DEFENSIVE DRIVING AND RIDING CENTRE SDN BHD')
        self.cell(0, 6, sanitize_text_for_pdf(company_name), ln=True)
        
        # Company info - 11px in invoice ≈ 8pt, color #444
        self.set_x(text_x)
        self.set_font_safe('', 8)
        self.set_text_color(68, 68, 68)
        
        # Line 1: (Reg No) • Address Line 1, Address Line 2
        line1_parts = []
        if cs.get('company_reg_no'):
            line1_parts.append(f"({cs.get('company_reg_no')})")
        addr_parts = []
        if cs.get('address_line1'):
            addr_parts.append(cs.get('address_line1'))
        if cs.get('address_line2'):
            addr_parts.append(cs.get('address_line2'))
        if addr_parts:
            line1_parts.append(', '.join(addr_parts))
        if line1_parts:
            self.cell(0, 4, sanitize_text_for_pdf(' • '.join(line1_parts)), ln=True)
        
        # Line 2: City Postcode, State • Tel: xxx • email
        self.set_x(text_x)
        line2_parts = []
        location_parts = []
        if cs.get('city'):
            location_parts.append(cs.get('city'))
        if cs.get('postcode'):
            location_parts.append(cs.get('postcode'))
        location_str = ' '.join(location_parts)
        if cs.get('state'):
            location_str += f", {cs.get('state')}"
        if location_str:
            line2_parts.append(location_str)
        if cs.get('phone'):
            line2_parts.append(f"Tel: {cs.get('phone')}")
        if cs.get('email'):
            line2_parts.append(cs.get('email'))
        if line2_parts:
            self.cell(0, 4, sanitize_text_for_pdf(' • '.join(line2_parts)), ln=True)
        
        # Border line at bottom of header - 3px solid in invoice ≈ 1mm
        self.ln(3)
        line_y = self.get_y()
        self.set_draw_color(*self.primary_color)
        self.set_line_width(1)
        self.line(10, line_y, 200, line_y)
        self.ln(6)
    
    def footer(self):
        """Invoice-style footer with bank details and tagline"""
        cs = self.company_settings
        
        self.set_y(-28)
        
        # Separator line
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        
        self.ln(2)
        self.set_font_safe('', 8)
        self.set_text_color(85, 85, 85)
        
        # Bank details (like invoice)
        bank_info = []
        if cs.get('bank_name'):
            bank_info.append(f"Bank: {cs.get('bank_name')}")
        if cs.get('bank_account_name'):
            bank_info.append(f"Account: {cs.get('bank_account_name')}")
        if cs.get('bank_account_number'):
            bank_info.append(f"No: {cs.get('bank_account_number')}")
        if bank_info:
            self.cell(0, 4, ' | '.join(bank_info), align='C', ln=True)
        
        # Footer note
        footer_note = cs.get('invoice_footer_note', 'Thank you for your business!')
        self.cell(0, 4, footer_note, align='C', ln=True)
        
        # Tagline in italic primary color (like invoice)
        tagline = cs.get('tagline', 'Towards a Nation of Safe Drivers')
        self.set_font_safe('I', 9)
        self.set_text_color(*self.primary_color)
        self.cell(0, 5, f'"{tagline}"', align='C', ln=True)
        
        # Page number
        self.set_font_safe('', 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 3, f'Page {self.page_no()}', align='C')


@api_router.get("/marketing/quotations/{quotation_id}/download-pdf")
async def download_quotation_pdf(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Generate and download full quotation PDF package (7 pages)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Get quotation
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Only allow download for approved/sent/accepted quotations
    if quotation.get("status") not in ["approved", "sent", "accepted"]:
        raise HTTPException(status_code=400, detail="Only approved/sent/accepted quotations can be downloaded")
    
    # Get client info
    client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
    if not client:
        client = {}
    
    # Get company settings
    company_settings = await db.company_settings.find_one({"id": "company_settings"}, {"_id": 0})
    if not company_settings:
        company_settings = {}
    
    # Get PDF templates
    templates = await db.quotation_pdf_templates.find_one({"id": "quotation_pdf_templates"}, {"_id": 0})
    if not templates:
        templates = {"cover_letter": "", "terms_conditions_pages": "", "primary_color": "#1a365d"}
    
    # Get selected items with their details (new system)
    inclusion_items = []
    exclusion_items = []
    selected_items = quotation.get("selected_items") or []
    if selected_items:
        item_ids = [s.get("item_id") for s in selected_items if s.get("item_id")]
        if item_ids:
            # Query from description_items collection (the active collection)
            items_cursor = await db.description_items.find(
                {"id": {"$in": item_ids}},
                {"_id": 0}
            ).to_list(100)
            items_map = {item["id"]: item for item in items_cursor}
            for sel in selected_items:
                item = items_map.get(sel.get("item_id"))
                if item:
                    qty = sel.get("quantity", 1)
                    item_data = {"name": item.get("name", ""), "quantity": qty, "has_quantity": item.get("has_quantity", False)}
                    category = item.get("category", "")
                    if category in ["inclusion", "inclusions"]:
                        inclusion_items.append(item_data)
                    elif category in ["exclusion", "exclusions"]:
                        exclusion_items.append(item_data)
    
    # Legacy: Get description items text (for old quotations)
    description_items_text = []
    if quotation.get("description_items") and not selected_items:
        items = await db.description_items.find(
            {"id": {"$in": quotation.get("description_items")}},
            {"_id": 0}
        ).to_list(100)
        description_items_text = [item.get("name", "") or item.get("description", "") for item in items]
    
    # Get marketer/approver info
    marketer = await db.users.find_one({"id": quotation.get("created_by")}, {"_id": 0, "full_name": 1})
    approver = None
    if quotation.get("approved_by"):
        approver = await db.users.find_one({"id": quotation.get("approved_by")}, {"_id": 0, "full_name": 1})
    
    # Parse primary color from templates
    primary_color_hex = templates.get("primary_color", "#1a365d")
    try:
        primary_color_rgb = tuple(int(primary_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    except:
        primary_color_rgb = (26, 54, 93)
    
    # Generate PDF with custom color
    pdf = QuotationPDF(company_settings, primary_color_rgb)
    
    # ===== PAGE 1: COVER LETTER =====
    pdf.add_page()
    
    # Date (after automatic header)
    pdf.set_font_safe('', 10)
    pdf.set_text_color(0, 0, 0)
    created_date = quotation.get("created_at", "")
    if isinstance(created_date, str):
        try:
            created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
        except:
            created_date = datetime.now()
    pdf.cell_safe(0, 6, created_date.strftime("%d %B %Y"), ln=True)
    pdf.ln(5)
    
    # Recipient
    pdf.set_font_safe('B', 10)
    pdf.cell_safe(0, 5, client.get("contact_person", ""), ln=True)
    pdf.set_font_safe('', 10)
    pdf.cell_safe(0, 5, client.get("company_name", ""), ln=True)
    
    # Address - multi-line
    address = client.get("company_address", "")
    for line in address.split('\n'):
        pdf.cell_safe(0, 5, line.strip(), ln=True)
    
    pdf.ln(8)
    
    # Salutation
    pdf.cell_safe(0, 6, f"Dear {client.get('contact_person', 'Sir/Madam')},", ln=True)
    pdf.ln(5)
    
    # Get programme name for cover letter - directly from quotation
    cover_programme_name = quotation.get("programme_name", "") or ""
    if not cover_programme_name.strip() and quotation.get("programme_id"):
        cover_programme = await db.programs.find_one({"id": quotation.get("programme_id")}, {"_id": 0, "name": 1})
        if cover_programme:
            cover_programme_name = cover_programme.get("name", "")
    if not cover_programme_name.strip():
        cover_programme_name = "Training Programme"
    
    # Get marketer name for placeholder
    marketer_full_name = marketer.get("full_name", "") if marketer else ""
    
    # Cover letter content (from template or default)
    cover_letter = templates.get("cover_letter", "")
    if cover_letter:
        # Replace placeholders
        cover_letter = cover_letter.replace("{{programme_name}}", cover_programme_name)
        cover_letter = cover_letter.replace("{{company_name}}", client.get("company_name", ""))
        cover_letter = cover_letter.replace("{{contact_person}}", client.get("contact_person", ""))
        cover_letter = cover_letter.replace("{{quotation_number}}", quotation.get("quotation_number", ""))
        cover_letter = cover_letter.replace("{{total_amount}}", f"RM {quotation.get('total_amount', 0):,.2f}")
        cover_letter = cover_letter.replace("{{marketer_name}}", marketer_full_name)
        
        # Use rich text rendering for formatted content
        pdf.render_rich_text(cover_letter, line_height=5, default_size=10)
    else:
        # Default cover letter
        pdf.set_font_safe('B', 10)
        pdf.cell_safe(0, 6, f"RE: QUOTATION FOR {sanitize_text_for_pdf(cover_programme_name).upper()}", ln=True)
        pdf.ln(5)
        pdf.set_font_safe('', 10)
        pdf.multi_cell_safe(0, 5, f"Thank you for your interest in our training programme. We are pleased to submit our quotation for the {cover_programme_name} programme as per your request.")
        pdf.ln(3)
        pdf.multi_cell_safe(0, 5, "Please find attached the detailed quotation for your kind perusal and consideration.")
    
    pdf.ln(10)
    
    # Signature
    pdf.set_font_safe('', 10)
    pdf.cell_safe(0, 5, "Yours faithfully,", ln=True)
    pdf.ln(15)
    pdf.set_font_safe('B', 10)
    pdf.cell_safe(0, 5, marketer.get("full_name", "") if marketer else "", ln=True)
    pdf.set_font_safe('', 10)
    pdf.cell_safe(0, 5, "Marketing Executive", ln=True)
    pdf.cell_safe(0, 5, company_settings.get("company_name", "MDDRC Sdn Bhd"), ln=True)
    
    # ===== PAGE 2: QUOTATION DETAILS =====
    pdf.add_page()
    
    # Title
    pdf.set_font_safe('B', 16)
    pdf.set_text_color(26, 54, 93)
    pdf.cell_safe(0, 10, "QUOTATION", align='C', ln=True)
    pdf.ln(3)
    
    # Quotation info in a box
    pdf.set_fill_color(248, 249, 250)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, pdf.get_y(), 190, 20, 'DF')
    pdf.set_font_safe('', 9)
    pdf.set_text_color(0, 0, 0)
    
    y_info = pdf.get_y() + 3
    pdf.set_xy(15, y_info)
    pdf.cell_safe(60, 5, f"Quotation No: {quotation.get('quotation_number', '')}")
    pdf.set_xy(85, y_info)
    pdf.cell_safe(60, 5, f"Date: {created_date.strftime('%d %B %Y')}")
    
    # Parse valid_until date - calculate from created_at if missing
    valid_until = quotation.get("valid_until")
    valid_until_str = ""
    validity_days = quotation.get("validity_days", 30)
    
    if valid_until:
        if isinstance(valid_until, str):
            try:
                if 'T' in valid_until:
                    valid_until_dt = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
                else:
                    valid_until_dt = datetime.strptime(valid_until, "%Y-%m-%d")
                valid_until_str = valid_until_dt.strftime("%d %B %Y")
            except:
                valid_until_str = valid_until
        elif hasattr(valid_until, 'strftime'):
            valid_until_str = valid_until.strftime("%d %B %Y")
    else:
        # Calculate valid_until from created_at + validity_days
        created_at = quotation.get("created_at", "")
        if isinstance(created_at, str):
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                valid_until_dt = created_dt + timedelta(days=validity_days)
                valid_until_str = valid_until_dt.strftime("%d %B %Y")
            except:
                pass
        elif hasattr(created_at, 'strftime'):
            valid_until_dt = created_at + timedelta(days=validity_days)
            valid_until_str = valid_until_dt.strftime("%d %B %Y")
    
    pdf.set_xy(15, y_info + 7)
    pdf.cell_safe(60, 5, f"Valid Until: {valid_until_str}")
    pdf.set_xy(85, y_info + 7)
    pdf.cell_safe(60, 5, f"Status: {quotation.get('status', '').title()}")
    
    pdf.set_y(pdf.get_y() + 25)
    
    # Client info box
    pdf.set_fill_color(232, 244, 253)
    pdf.set_font_safe('B', 9)
    pdf.cell_safe(0, 6, "TO:", fill=True, ln=True)
    pdf.set_font_safe('', 9)
    pdf.cell_safe(0, 5, client.get("company_name", ""), ln=True)
    for line in client.get("company_address", "").split('\n'):
        pdf.cell_safe(0, 5, line.strip(), ln=True)
    pdf.cell_safe(0, 5, f"Attn: {client.get('contact_person', '')}", ln=True)
    pdf.cell_safe(0, 5, f"Tel: {client.get('contact_phone', '')}", ln=True)
    pdf.ln(5)
    
    # Training date/venue if accepted
    if quotation.get("status") == "accepted" and quotation.get("training_date"):
        pdf.set_fill_color(232, 253, 232)
        pdf.set_font_safe('B', 9)
        pdf.cell_safe(0, 6, "TRAINING DETAILS:", fill=True, ln=True)
        pdf.set_font_safe('', 9)
        pdf.cell_safe(0, 5, f"Date: {quotation.get('training_date', '')}", ln=True)
        pdf.cell_safe(0, 5, f"Venue: {quotation.get('venue', '')}", ln=True)
        pdf.ln(5)
    
    # Quotation table with text wrapping for description
    pdf.set_font_safe('B', 9)
    pdf.set_fill_color(*pdf.primary_color)
    pdf.set_text_color(255, 255, 255)
    
    # Table header - adjusted column widths for better text fit
    col_desc = 100  # Wider for description
    col_qty = 20
    col_rate = 30
    col_amount = 35
    
    pdf.cell_safe(col_desc, 7, "Description", border=1, fill=True)
    pdf.cell_safe(col_qty, 7, "Qty", border=1, fill=True, align='C')
    pdf.cell_safe(col_rate, 7, "Rate (RM)", border=1, fill=True, align='R')
    pdf.cell_safe(col_amount, 7, "Amount (RM)", border=1, fill=True, align='R', ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font_safe('', 9)
    
    # Table content with text wrapping
    pricing_type = quotation.get("pricing_type", "per_pax")
    
    # Get programme name - directly from quotation (it's stored there)
    programme_name = quotation.get("programme_name", "") or ""
    # Fallback to programs collection if not in quotation
    if not programme_name.strip() and quotation.get("programme_id"):
        programme = await db.programs.find_one({"id": quotation.get("programme_id")}, {"_id": 0, "name": 1})
        if programme:
            programme_name = programme.get("name", "")
    if not programme_name.strip():
        programme_name = "Training Programme"
    
    if pricing_type == "per_group":
        rate_display = f"{quotation.get('group_price', 0):,.2f}"
        qty_display = "1 group"
    else:
        num_pax = quotation.get("num_participants", 1)
        rate_per_pax = quotation.get("rate_per_pax", 0)
        subtotal = quotation.get("subtotal", 0)
        total_amount = quotation.get("total_amount", 0)
        
        # If rate_per_pax is 0 but we have subtotal and num_pax, calculate it
        if rate_per_pax == 0 and num_pax > 0 and subtotal > 0:
            rate_per_pax = subtotal / num_pax
        # If still 0 and we have total_amount, use that
        elif rate_per_pax == 0 and num_pax > 0 and total_amount > 0:
            rate_per_pax = total_amount / num_pax
        # If num_pax is 1 and rate is 0, try to derive from total
        elif num_pax == 1 and rate_per_pax == 0 and total_amount > 0:
            # Check if total_amount looks like a group price (>1000 and not divisible)
            # or a per-pax rate for potentially more participants
            # Try to detect the actual number of pax by checking if there's a reasonable unit price
            for potential_pax in [2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30]:
                unit_price = total_amount / potential_pax
                # Check if unit price is a round number (likely intended)
                if unit_price == int(unit_price) or (unit_price * 100) == int(unit_price * 100):
                    # Looks reasonable
                    if unit_price >= 100 and unit_price <= 5000:
                        num_pax = potential_pax
                        rate_per_pax = unit_price
                        break
            # Fallback if no match
            if rate_per_pax == 0:
                rate_per_pax = total_amount
        
        rate_display = f"{rate_per_pax:,.2f}"
        qty_display = str(num_pax)
    
    # Draw main programme row
    programme_name = sanitize_text_for_pdf(programme_name)
    
    # Use multi_cell for description to enable text wrapping
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    
    # Draw description cell with wrapping
    pdf.multi_cell(col_desc, 5, programme_name, border=1)
    y_after_desc = pdf.get_y()
    actual_height = y_after_desc - y_start
    
    # Draw other cells at same height
    pdf.set_xy(x_start + col_desc, y_start)
    pdf.cell_safe(col_qty, actual_height, qty_display, border=1, align='C')
    pdf.cell_safe(col_rate, actual_height, rate_display, border=1, align='R')
    pdf.cell_safe(col_amount, actual_height, f"{quotation.get('subtotal', 0):,.2f}", border=1, align='R')
    pdf.set_y(y_after_desc)
    
    # Inclusions section - new format with quantities
    if inclusion_items:
        pdf.set_font_safe('B', 9)
        pdf.set_fill_color(232, 245, 233)  # Light green
        pdf.cell_safe(col_desc + col_qty + col_rate + col_amount, 6, "INCLUSIONS", border='LRB', fill=True, align='L', ln=True)
        pdf.set_font_safe('', 8)
        for item in inclusion_items:
            item_text = item["name"]
            if item.get("has_quantity") and item.get("quantity", 1) > 1:
                item_text = f"{item['name']} x {item['quantity']}"
            pdf.set_fill_color(250, 250, 250)
            pdf.cell_safe(col_desc + col_qty + col_rate + col_amount, 5, f"  • {item_text}", border='LRB', fill=True, ln=True)
    
    # Exclusions section - new format
    if exclusion_items:
        pdf.set_font_safe('B', 9)
        pdf.set_fill_color(255, 235, 238)  # Light red
        pdf.cell_safe(col_desc + col_qty + col_rate + col_amount, 6, "EXCLUSIONS", border='LRB', fill=True, align='L', ln=True)
        pdf.set_font_safe('', 8)
        for item in exclusion_items:
            item_text = item["name"]
            if item.get("has_quantity") and item.get("quantity", 1) > 1:
                item_text = f"{item['name']} x {item['quantity']}"
            pdf.set_fill_color(250, 250, 250)
            pdf.cell_safe(col_desc + col_qty + col_rate + col_amount, 5, f"  • {item_text}", border='LRB', fill=True, ln=True)
    
    # Legacy description items (old format) and custom description
    if description_items_text or quotation.get("custom_description"):
        all_desc = description_items_text + ([quotation.get("custom_description")] if quotation.get("custom_description") else [])
        for desc in all_desc:
            if desc:
                pdf.set_font_safe('I', 8)
                pdf.set_fill_color(250, 250, 250)
                pdf.multi_cell_safe(col_desc + col_qty + col_rate + col_amount, 5, f"  Note: {desc}", border='LRB', fill=True)
    
    pdf.set_font_safe('', 9)
    pdf.ln(2)
    
    # Subtotal row
    pdf.cell_safe(col_desc + col_qty + col_rate, 7, "Subtotal", border=1, align='R')
    pdf.cell_safe(col_amount, 7, f"{quotation.get('subtotal', 0):,.2f}", border=1, align='R', ln=True)
    
    # Discount row if applicable
    if quotation.get("discount_amount", 0) > 0:
        discount_pct = quotation.get("discount_percentage", 0)
        discount_label = f"Discount ({discount_pct}%)" if discount_pct > 0 else "Discount"
        pdf.set_text_color(255, 102, 0)  # Orange for discount
        pdf.cell_safe(col_desc + col_qty + col_rate, 7, discount_label, border=1, align='R')
        pdf.cell_safe(col_amount, 7, f"-{quotation.get('discount_amount', 0):,.2f}", border=1, align='R', ln=True)
        pdf.set_text_color(0, 0, 0)  # Reset color
    
    # SST row if applicable
    sst_pct = quotation.get("sst_percentage", 0) or quotation.get("sst_percent", 0)
    if sst_pct > 0:
        pdf.cell_safe(col_desc + col_qty + col_rate, 7, f"SST ({sst_pct}%)", border=1, align='R')
        pdf.cell_safe(col_amount, 7, f"{quotation.get('sst_amount', 0):,.2f}", border=1, align='R', ln=True)
    
    # Total row
    pdf.set_font_safe('B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell_safe(col_desc + col_qty + col_rate, 9, "TOTAL (RM)", border=1, align='R', fill=True)
    pdf.cell_safe(col_amount, 9, f"{quotation.get('total_amount', 0):,.2f}", border=1, align='R', fill=True, ln=True)
    
    # Validity note
    pdf.ln(5)
    pdf.set_fill_color(255, 243, 205)
    pdf.set_font_safe('B', 9)
    pdf.cell_safe(0, 7, f"This quotation is valid until {valid_until_str}", fill=True, align='C', ln=True)
    
    # Remarks if any
    if quotation.get("remarks"):
        pdf.ln(3)
        pdf.set_font_safe('I', 8)
        pdf.multi_cell_safe(0, 4, f"Remarks: {quotation.get('remarks')}")
    
    # Signatures at bottom - clean format with blue signature names
    pdf.ln(10)
    pdf.set_font_safe('', 9)
    y_pos = pdf.get_y()
    pdf.set_xy(10, y_pos)
    pdf.cell_safe(90, 5, "Prepared by:", ln=False)
    pdf.cell_safe(90, 5, "Approved by:", ln=True)
    
    # Signature names in blue - cursive style
    pdf.ln(8)
    pdf.set_font_safe('I', 12)  # Italic for cursive effect
    pdf.set_text_color(0, 0, 128)  # Dark blue for signature
    marketer_name = marketer.get("full_name", "") if marketer else ""
    # Get approver full name from database  
    approver_name = approver.get("full_name", "Arjuna Arunatheym") if approver else "Arjuna Arunatheym"
    pdf.cell_safe(90, 6, marketer_name, ln=False, align='C')
    pdf.cell_safe(90, 6, approver_name, ln=True, align='C')
    
    # Reset color and add titles below names
    pdf.set_text_color(0, 0, 0)
    pdf.set_font_safe('', 8)
    pdf.cell_safe(90, 4, "Marketing Manager", ln=False, align='C')
    pdf.cell_safe(90, 4, "Chief Executive Officer", ln=True, align='C')
    
    # ===== PAGES 3-6: TERMS & CONDITIONS =====
    terms_content = templates.get("terms_conditions_pages", "")
    if terms_content:
        # Replace placeholders in terms content
        terms_content = terms_content.replace("{{programme_name}}", cover_programme_name)
        terms_content = terms_content.replace("{{company_name}}", client.get("company_name", ""))
        terms_content = terms_content.replace("{{contact_person}}", client.get("contact_person", ""))
        terms_content = terms_content.replace("{{quotation_number}}", quotation.get("quotation_number", ""))
        terms_content = terms_content.replace("{{total_amount}}", f"RM {quotation.get('total_amount', 0):,.2f}")
        terms_content = terms_content.replace("{{marketer_name}}", marketer_full_name)
        
        # Use page breaks <pb> or split by length
        if '<pb>' in terms_content or '<pagebreak>' in terms_content:
            # Split by explicit page breaks
            terms_pages = [p.strip() for p in terms_content.replace('<pagebreak>', '<pb>').split('<pb>') if p.strip()]
        else:
            # Split terms into pages (roughly 2500 chars per page for better fit)
            page_size = 2500
            terms_pages = [terms_content[i:i+page_size] for i in range(0, len(terms_content), page_size)]
        
        for i, page_content in enumerate(terms_pages[:4]):  # Max 4 pages for T&C
            pdf.add_page()
            
            if i == 0:
                pdf.set_font_safe('B', 14)
                pdf.set_text_color(26, 54, 93)
                pdf.cell_safe(0, 8, "TERMS & CONDITIONS", align='C', ln=True)
                pdf.ln(3)
            
            pdf.set_text_color(0, 0, 0)
            # Use rich text rendering for formatted content
            pdf.render_rich_text(page_content, line_height=4.5, default_size=9)
    else:
        # Default terms page
        pdf.add_page()
        
        pdf.set_font_safe('B', 14)
        pdf.set_text_color(26, 54, 93)
        pdf.cell_safe(0, 8, "TERMS & CONDITIONS", align='C', ln=True)
        pdf.ln(3)
        
        pdf.set_font_safe('', 9)
        pdf.set_text_color(0, 0, 0)
        
        default_terms = quotation.get("terms_conditions", "")
        if default_terms:
            for line in default_terms.split('\n'):
                pdf.multi_cell_safe(0, 4.5, line.strip())
                pdf.ln(1)
        else:
            pdf.multi_cell_safe(0, 4.5, "1. Payment terms: Upon receipt of invoice.")
            pdf.multi_cell_safe(0, 4.5, "2. Cancellation must be made at least 7 days before training date.")
            pdf.multi_cell_safe(0, 4.5, "3. All prices are in Malaysian Ringgit (RM).")
            pdf.multi_cell_safe(0, 4.5, "4. This quotation is subject to change without prior notice.")
    
    # ===== REGISTRATION FORM PAGE =====
    pdf.add_page()
    
    # Form Title
    pdf.set_font_safe('B', 14)
    pdf.set_text_color(*pdf.primary_color)
    pdf.cell_safe(0, 8, "REGISTRATION FORM", align='C', ln=True)
    pdf.ln(2)
    
    pdf.set_font_safe('', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell_safe(0, 4, "Please fill up all the information CLEARLY and ACCURATELY. Thank you.", align='C', ln=True)
    pdf.ln(3)
    
    # Account Manager & Order Details Box
    pdf.set_fill_color(248, 249, 250)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_font_safe('', 8)
    pdf.set_text_color(0, 0, 0)
    
    y_box = pdf.get_y()
    pdf.rect(10, y_box, 190, 16, 'D')
    
    # Row 1
    pdf.set_xy(12, y_box + 2)
    marketer_name = (marketer.get('full_name', '') if marketer else '')[:25]
    pdf.cell_safe(95, 5, f"Account Manager: {marketer_name}")
    pdf.set_xy(107, y_box + 2)
    pdf.cell_safe(90, 5, f"Quotation No: {quotation.get('quotation_number', '')}")
    
    # Row 2
    pdf.set_xy(12, y_box + 8)
    pdf.cell_safe(95, 5, "Purchase Order: ___________________")
    pdf.set_xy(107, y_box + 8)
    pdf.cell_safe(90, 5, f"Date: {created_date.strftime('%d %B %Y')}")
    
    pdf.set_y(y_box + 20)
    
    # Tick Relevant Box section - better spaced
    pdf.set_font_safe('B', 8)
    pdf.cell_safe(35, 5, "Please tick relevant:")
    pdf.set_font_safe('', 8)
    x_pos = pdf.get_x()
    y_pos = pdf.get_y()
    pdf.rect(x_pos, y_pos + 1, 3, 3)
    pdf.cell_safe(30, 5, "   New Registration")
    x_pos = pdf.get_x()
    pdf.rect(x_pos, y_pos + 1, 3, 3)
    pdf.cell_safe(25, 5, "   Company")
    x_pos = pdf.get_x()
    pdf.rect(x_pos, y_pos + 1, 3, 3)
    pdf.cell_safe(25, 5, "   Individual", ln=True)
    pdf.ln(3)
    
    # Course Information Section
    pdf.set_fill_color(*pdf.secondary_color)
    pdf.set_font_safe('B', 9)
    pdf.set_text_color(255, 255, 255)
    pdf.cell_safe(0, 6, "COURSE INFORMATION", fill=True, ln=True)
    
    pdf.set_font_safe('', 8)
    pdf.set_text_color(0, 0, 0)
    
    # Two column layout - use smaller font for values to prevent overflow
    col1_w = 95
    col2_w = 95
    
    # Truncate values to fit
    prog_name = sanitize_text_for_pdf(quotation.get('programme_name', ''))[:40]
    org_name = sanitize_text_for_pdf(client.get('company_name', ''))[:30]
    address = client.get('company_address', '').split('\n')[0][:30] if client.get('company_address') else ''
    contact = sanitize_text_for_pdf(client.get('contact_person', ''))[:25]
    email = sanitize_text_for_pdf(client.get('contact_email', ''))[:30]
    phone = sanitize_text_for_pdf(client.get('contact_phone', ''))[:15]
    
    pdf.set_font_safe('', 7)
    pdf.cell_safe(col1_w, 5, f"Course Title: {prog_name}", border='LTR')
    pdf.cell_safe(col2_w, 5, f"Course Date: {quotation.get('training_date', '______________')}", border='LTR', ln=True)
    
    pdf.cell_safe(col1_w, 5, f"Organization: {org_name}", border='LR')
    pdf.cell_safe(col2_w, 5, "Company Tax ID: ________________", border='LR', ln=True)
    
    pdf.cell_safe(col1_w, 5, f"Billing Address: {address}", border='LR')
    pdf.cell_safe(col2_w, 5, "Company Reg No: ________________", border='LR', ln=True)
    
    pdf.cell_safe(col1_w, 5, f"Requester: {contact}", border='LR')
    pdf.cell_safe(col2_w, 5, "Designation: ___________________", border='LR', ln=True)
    
    pdf.cell_safe(col1_w, 5, f"Email: {email}", border='LR')
    pdf.cell_safe(col2_w, 5, f"Tel: {phone}", border='LR', ln=True)
    
    pdf.cell_safe(col1_w, 5, "Payment Terms: _________________", border='LRB')
    pdf.cell_safe(col2_w, 5, "Finance Email: _________________", border='LRB', ln=True)
    
    pdf.ln(3)
    
    # Participant's Particulars Table
    pdf.set_fill_color(*pdf.secondary_color)
    pdf.set_font_safe('B', 8)
    pdf.set_text_color(255, 255, 255)
    pdf.cell_safe(0, 6, "PARTICIPANT'S PARTICULARS", fill=True, ln=True)
    
    # Table header - adjusted column widths for mobile/print
    pdf.set_font_safe('B', 6)
    pdf.cell_safe(8, 6, "No", border=1, fill=True, align='C')
    pdf.cell_safe(40, 6, "Full Name", border=1, fill=True)
    pdf.cell_safe(40, 6, "Corporate Email", border=1, fill=True)
    pdf.cell_safe(22, 6, "Tel/Mobile", border=1, fill=True)
    pdf.cell_safe(28, 6, "IC/Passport", border=1, fill=True)
    pdf.cell_safe(22, 6, "Fees (RM)", border=1, fill=True, align='C')
    pdf.cell_safe(30, 6, "Signature", border=1, fill=True, align='C', ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font_safe('', 7)
    
    # Empty rows for participants - more rows
    num_rows = min(max(quotation.get("num_participants", 5), 5), 10)
    for i in range(num_rows):
        pdf.cell_safe(8, 8, str(i+1), border=1, align='C')
        pdf.cell_safe(40, 8, "", border=1)
        pdf.cell_safe(40, 8, "", border=1)
        pdf.cell_safe(22, 8, "", border=1)
        pdf.cell_safe(28, 8, "", border=1)
        pdf.cell_safe(22, 8, "", border=1)
        pdf.cell_safe(30, 8, "", border=1, ln=True)
    
    pdf.ln(2)
    pdf.set_font_safe('I', 6)
    pdf.cell_safe(0, 4, "(Please attach another copy if the space above is insufficient)", align='C', ln=True)
    
    # PDPA Consent
    pdf.ln(3)
    pdf.set_font_safe('B', 8)
    pdf.set_text_color(*pdf.primary_color)
    pdf.cell_safe(0, 5, "PDPA CONSENT", ln=True)
    pdf.set_font_safe('', 6)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell_safe(0, 3, "By signing this form, you hereby agree to give your consent to collect, obtain, store and process the personal data that you provide in this form for the purpose of training delivery, certification, and compliance. Personal data may also be transferred to principals, accreditors and examination institutes as part of course delivery.")
    
    # Authorized Signatory Section
    pdf.ln(3)
    pdf.set_font_safe('B', 8)
    pdf.set_text_color(*pdf.primary_color)
    pdf.cell_safe(0, 5, "AUTHORIZED SIGNATORY & COMPANY STAMP", ln=True)
    
    pdf.set_font_safe('', 7)
    pdf.set_text_color(0, 0, 0)
    
    # Two columns for signature - better layout
    y_sig = pdf.get_y()
    
    # Left column - signature fields
    pdf.set_xy(10, y_sig)
    pdf.cell_safe(90, 5, "Name: _______________________________")
    pdf.set_xy(10, y_sig + 6)
    pdf.cell_safe(90, 5, "Designation: __________________________")
    pdf.set_xy(10, y_sig + 12)
    pdf.cell_safe(90, 5, "Date: ________________________________")
    pdf.set_xy(10, y_sig + 18)
    pdf.cell_safe(90, 5, "Signature: ___________________________")
    
    # Right column - company stamp box
    pdf.set_draw_color(180, 180, 180)
    pdf.rect(110, y_sig, 80, 23, 'D')
    pdf.set_xy(112, y_sig + 8)
    pdf.set_font_safe('I', 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell_safe(76, 4, "Company Stamp", align='C')
    
    # Generate PDF bytes
    pdf_bytes = pdf.output()
    
    # Return as streaming response
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Quotation_{quotation.get("quotation_number", "").replace("/", "_")}.pdf"'
        }
    )


# ==================== END MARKETING QUOTATION ENDPOINTS ====================
# Include router (after all routes are defined)
app.include_router(api_router)

# Root health endpoint for deployment health checks
@app.get("/health")
async def root_health_check():
    """Root health check endpoint for Kubernetes/deployment monitoring"""
    try:
        await db.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def setup_admin_account():
    """Create or update admin account on startup"""
    try:
        # Wait for MongoDB connection with timeout
        try:
            await asyncio.wait_for(db.command('ping'), timeout=10.0)
            logging.info("✅ MongoDB connection established")
        except asyncio.TimeoutError:
            logging.error("❌ MongoDB connection timeout - startup will continue but some features may not work")
            return
        except Exception as conn_err:
            logging.error(f"❌ MongoDB connection error: {conn_err} - startup will continue")
            return
        
        # PERFORMANCE OPTIMIZATION: Create database indexes
        # Indexes dramatically speed up queries on large datasets
        logging.info("📊 Creating database indexes for performance optimization...")
        
        try:
            # Users collection indexes
            await db.users.create_index("id", unique=True)
            await db.users.create_index("email", unique=True)
            await db.users.create_index("role")
            await db.users.create_index([("company_id", 1), ("role", 1)])
            
            # Sessions collection indexes
            await db.sessions.create_index("id", unique=True)
            await db.sessions.create_index("program_id")
            await db.sessions.create_index("company_id")
            await db.sessions.create_index([("start_date", 1), ("end_date", 1)])
            
            # Test results collection indexes
            await db.test_results.create_index([("session_id", 1), ("participant_id", 1)])
            await db.test_results.create_index("test_type")
            
            # Attendance collection indexes
            await db.attendance.create_index([("session_id", 1), ("participant_id", 1)])
            await db.attendance.create_index([("session_id", 1), ("date", 1)])
            
            # Participant access collection indexes
            await db.participant_access.create_index([("session_id", 1), ("participant_id", 1)], unique=True)
            
            # Feedback collection indexes
            await db.course_feedback.create_index([("session_id", 1), ("participant_id", 1)])
            
            # Vehicle issues collection indexes
            await db.vehicle_issues.create_index([("session_id", 1), ("participant_id", 1)])
            
            logging.info("✅ Database indexes created successfully")
        except Exception as idx_error:
            logging.warning(f"⚠️  Index creation warning (may already exist): {str(idx_error)}")
        
        # Admin credentials from environment variables
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'changeme123')
        admin_name = "Arjuna Arunatheym"
        admin_id_number = "ADMIN001"
        
        # Check if admin exists
        existing_admin = await db.users.find_one({"role": "admin"})
        
        # Hash password
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(admin_password)
        
        if existing_admin:
            # Update existing admin
            await db.users.update_one(
                {"role": "admin"},
                {"$set": {
                    "email": admin_email,
                    "password": hashed_password,
                    "full_name": admin_name,
                    "id_number": admin_id_number
                }}
            )
            logging.info(f"✅ Admin account updated: {admin_email}")
        else:
            # Create new admin
            admin_doc = {
                "id": str(uuid.uuid4()),
                "email": admin_email,
                "password": hashed_password,
                "full_name": admin_name,
                "id_number": admin_id_number,
                "phone_number": "",
                "role": "admin",
                "company_id": None,
                "created_at": get_malaysia_time().isoformat()
            }
            await db.users.insert_one(admin_doc)
            logging.info(f"✅ Admin account created: {admin_email}")
        
        logging.info(f"🔐 Admin credentials: {admin_email} / {admin_password}")
        
    except Exception as e:
        logging.error(f"❌ Failed to setup admin account: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
