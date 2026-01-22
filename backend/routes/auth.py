"""
Auth routes - Authentication endpoints
Endpoints: 6
- POST /auth/register
- POST /auth/login
- GET /auth/me
- POST /auth/forgot-password
- POST /auth/change-password
- POST /auth/reset-password
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime
import logging
import uuid

from core import (
    db, get_current_user, get_malaysia_time,
    hash_password, verify_password, create_access_token,
    check_login_lockout, record_failed_login, clear_failed_logins,
    pwd_context
)
from models import (
    User, UserCreate, UserLogin, TokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Security patterns for input validation
import re
MALICIOUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',
    r'\$where',
    r'\$gt|\$lt|\$ne|\$eq|\$regex',
    r';\s*drop\s+',
    r';\s*delete\s+',
    r'union\s+select',
    r'exec\s*\(',
    r'eval\s*\(',
    r'__proto__',
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


@router.post("/register", response_model=User)
async def register_user(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    """Register a new user (admin/coordinator only)"""
    # Role-based access control
    if current_user.role == "coordinator" or current_user.role == "assistant_admin":
        if user_data.role != "participant":
            raise HTTPException(status_code=403, detail="You can only create participants")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    password = user_data.password
    email = user_data.email
    
    if user_data.role == "participant":
        if not password:
            password = "mddrc1"
        if not email or email.strip() == "":
            if user_data.id_number:
                email = f"{user_data.id_number.replace('-', '').replace(' ', '')}@temp.mddrc.local"
            else:
                email = f"user_{uuid.uuid4().hex[:8]}@temp.mddrc.local"
    
    # Check if user exists
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
        email=email,
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


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
    """Login with email/IC number and password"""
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
    
    logging.info(f"Successful login: {user_data.email} from IP: {client_ip}")
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    user_doc.pop('password', None)
    user_doc.pop('hashed_password', None)
    user = User(**user_doc)
    
    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Request password reset (placeholder - would send email in production)"""
    user_doc = await db.users.find_one({"email": request.email}, {"_id": 0})
    
    # Always return success to prevent email enumeration
    return {"message": "If an account exists with this email, password reset instructions have been sent"}


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, current_user: User = Depends(get_current_user)):
    """Change password for logged-in user"""
    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(request.current_password, user_doc["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    hashed_password = hash_password(request.new_password)
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password": hashed_password}}
    )
    
    return {"message": "Password changed successfully"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password (MVP version - direct reset)"""
    user_doc = await db.users.find_one({"email": request.email}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed_password = pwd_context.hash(request.new_password)
    
    await db.users.update_one(
        {"email": request.email},
        {"$set": {"password": hashed_password}}
    )
    
    return {"message": "Password reset successfully"}
