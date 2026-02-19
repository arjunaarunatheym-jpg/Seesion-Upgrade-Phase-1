"""
Core utilities and shared dependencies for the application.
This module contains database connection, security helpers, and authentication.
"""
import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from collections import defaultdict

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

# ==================== DATABASE ====================
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'training_db')

if not MONGO_URL:
    raise ValueError("MONGO_URL environment variable is required")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ==================== PATHS ====================
ROOT_DIR = Path(__file__).parent.parent
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
CHECKLIST_PHOTOS_DIR = STATIC_DIR / "checklist_photos"
CHECKLIST_PHOTOS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# ==================== TIMEZONE HELPERS ====================
MALAYSIA_TZ = ZoneInfo("Asia/Kuala_Lumpur")

def get_malaysia_time() -> datetime:
    """Get current datetime in Malaysian timezone"""
    return datetime.now(MALAYSIA_TZ)

def get_malaysia_date():
    """Get current date in Malaysian timezone"""
    return get_malaysia_time().date()

def get_malaysia_time_str() -> str:
    """Get current time as HH:MM string in Malaysian timezone"""
    return get_malaysia_time().strftime("%H:%M")

# ==================== SECURITY ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY or SECRET_KEY == 'your-secret-key-change-in-production':
    raise ValueError("SECRET_KEY environment variable must be set to a secure random value")
ALGORITHM = "HS256"

# Rate limiting storage
rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60
BLOCKED_IPS = set()
FAILED_LOGIN_ATTEMPTS = defaultdict(list)
MAX_FAILED_LOGINS = 5
LOGIN_LOCKOUT_TIME = 300

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def check_login_lockout(ip: str) -> tuple[bool, int]:
    """Check if IP is locked out from login attempts"""
    attempts = FAILED_LOGIN_ATTEMPTS.get(ip, [])
    current_time = datetime.now(timezone.utc).timestamp()
    
    # Clean old attempts
    attempts = [t for t in attempts if current_time - t < LOGIN_LOCKOUT_TIME]
    FAILED_LOGIN_ATTEMPTS[ip] = attempts
    
    if len(attempts) >= MAX_FAILED_LOGINS:
        oldest = min(attempts)
        remaining = int(LOGIN_LOCKOUT_TIME - (current_time - oldest))
        return True, remaining
    return False, 0

def record_failed_login(ip: str):
    """Record a failed login attempt"""
    FAILED_LOGIN_ATTEMPTS[ip].append(datetime.now(timezone.utc).timestamp())

def clear_failed_logins(ip: str):
    """Clear failed login attempts for an IP"""
    FAILED_LOGIN_ATTEMPTS.pop(ip, None)

# ==================== MODELS (imported from models module) ====================
# These are imported here for convenience in route files
from models import (
    User, UserCreate, UserLogin, TokenResponse,
    Company, CompanyCreate, CompanyUpdate, BillingParty,
    Program, ProgramCreate, ProgramUpdate,
    Session, SessionCreate, ParticipantData, SupervisorData,
    ParticipantAccess, UpdateParticipantAccess,
    Settings, SettingsUpdate,
    Attendance
)

# ==================== AUTHENTICATION DEPENDENCY ====================
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """FastAPI dependency to get the current authenticated user"""
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


async def get_user_from_token(token: str) -> User:
    """Get user from a JWT token string (for query param auth)"""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== HELPER FUNCTIONS ====================
async def get_or_create_participant_access(participant_id: str, session_id: str) -> ParticipantAccess:
    """Get existing participant access or create a new one"""
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
    Find existing user by IC number (single source of truth)
    If found: update the user with NEW data (latest wins)
    If not found: create new user
    Returns: user dict with 'is_existing' flag and user data
    """
    import uuid
    
    full_name = user_data.get("full_name")
    email = user_data.get("email")
    id_number = user_data.get("id_number")
    phone_number = user_data.get("phone_number")
    
    # Search for existing user ONLY by IC number (unique identifier)
    existing_user = None
    if id_number:
        existing_user = await db.users.find_one({"id_number": id_number}, {"_id": 0})
    
    if existing_user:
        # User found - update with NEW data (latest entry wins)
        update_data = {
            "phone_number": phone_number,
            "company_id": company_id,
        }
        
        if full_name and full_name.strip():
            update_data["full_name"] = full_name.strip()
        
        if email and email.strip():
            update_data["email"] = email
        
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        await db.users.update_one(
            {"id": existing_user["id"]},
            {"$set": update_data}
        )
        
        updated_user = await db.users.find_one({"id": existing_user["id"]}, {"_id": 0})
        if isinstance(updated_user.get('created_at'), str):
            updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
        
        return {
            "is_existing": True,
            "user": User(**updated_user)
        }
    else:
        # User not found - create new
        password = user_data.get("password")
        if role == "participant" and not password:
            password = "mddrc1"
        
        hashed_password = pwd_context.hash(password)
        
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
