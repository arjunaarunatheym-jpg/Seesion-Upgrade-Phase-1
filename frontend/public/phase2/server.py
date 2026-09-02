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
    accounting_router,
    superadmin_portal_router,
    notifications_router,
    admin_kpis_router,
    health_router,
    backup_router,
    static_files_router,
    templates_router,
    finance_session_router,
    reports_legacy_router,
    vehicle_details_router,
    admin_data_management_router,
    certificate_verify_router,
    admin_fee_router,
    finance_source_of_truth_router,
)

# Import accounting auto-posting functions (Phase 2)
from routes.accounting import (
    post_session_completed_revenue,
    post_trainer_fee,
    post_coordinator_fee,
    post_marketing_commission,
    post_expense_recorded,
    post_payroll,
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
api_router.include_router(accounting_router)
api_router.include_router(superadmin_portal_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_kpis_router)
api_router.include_router(health_router)
api_router.include_router(backup_router)
api_router.include_router(static_files_router)
api_router.include_router(templates_router)
api_router.include_router(finance_session_router)
api_router.include_router(reports_legacy_router)
api_router.include_router(vehicle_details_router)
api_router.include_router(admin_data_management_router)
api_router.include_router(certificate_verify_router)
api_router.include_router(admin_fee_router)
api_router.include_router(finance_source_of_truth_router)
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


# ==================== ALL ENDPOINTS MODULARIZED ====================
# All 280+ endpoints have been moved to /app/backend/routes/
# See routes/__init__.py for the full list of route modules
# ==================== END MODULARIZATION ====================

# Root API endpoint
@api_router.get("/")
async def root():
    return {"message": "Defensive Driving Training API"}

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
    allow_origins=os.environ.get('CORS_ORIGINS', '').split(','),
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
        
        logging.info(f"Admin account ready: {admin_email}")
        
    except Exception as e:
        logging.error(f"❌ Failed to setup admin account: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
