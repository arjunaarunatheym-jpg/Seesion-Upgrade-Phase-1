"""
Security routes - Security admin functionality
Endpoints: 4
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from core import db, get_current_user
from models import User

router = APIRouter(prefix="/security", tags=["security"])

# Import rate limiting globals from server (these are shared app state)
# Note: In a production refactor, these should be in a shared state module
# For now, we access them via the core module or recreate lightweight versions
rate_limit_storage = {}
BLOCKED_IPS = set()
FAILED_LOGIN_ATTEMPTS = {}
RATE_LIMIT_REQUESTS = 500  # Increased for training sessions with 50+ participants
RATE_LIMIT_WINDOW = 60
MAX_FAILED_LOGINS = 10  # Increased for shared IPs
LOGIN_LOCKOUT_TIME = 180  # Reduced to 3 minutes


def clear_failed_logins(ip: str):
    """Clear failed login attempts for an IP"""
    if ip in FAILED_LOGIN_ATTEMPTS:
        del FAILED_LOGIN_ATTEMPTS[ip]


@router.get("/status")
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


@router.post("/block-ip")
async def block_ip(ip: str, current_user: User = Depends(get_current_user)):
    """Block an IP address (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    BLOCKED_IPS.add(ip)
    logging.warning(f"IP blocked by admin {current_user.email}: {ip}")
    return {"message": f"IP {ip} blocked"}


@router.post("/unblock-ip")
async def unblock_ip(ip: str, current_user: User = Depends(get_current_user)):
    """Unblock an IP address (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    BLOCKED_IPS.discard(ip)
    clear_failed_logins(ip)
    logging.info(f"IP unblocked by admin {current_user.email}: {ip}")
    return {"message": f"IP {ip} unblocked"}


@router.get("/audit-log")
async def get_security_audit(
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get security audit log (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    events = await db.security_audit.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return events
