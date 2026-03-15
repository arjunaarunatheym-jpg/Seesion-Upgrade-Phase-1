"""
Notification Settings & Broadcast routes
- GET /notifications/settings - Get all notification settings
- PUT /notifications/settings - Update notification settings
- GET /notifications/recipients - Get available recipients (staff)
- POST /notifications/broadcast - Send broadcast email
- POST /notifications/test - Send test notification
- GET /notifications/events - Get available notification events
"""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Body
from typing import Optional, List
from datetime import datetime
import uuid
import logging
import os
import asyncio
import base64
import resend

from core import db, get_current_user, get_malaysia_time
from models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)

resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

# All configurable notification events
NOTIFICATION_EVENTS = [
    {"id": "quotation_created", "label": "Quotation Created", "description": "When a new quotation is created", "category": "Marketing", "default_roles": ["admin"]},
    {"id": "quotation_approved", "label": "Quotation Approved", "description": "When admin approves a quotation", "category": "Marketing", "default_roles": ["marketing"], "note": "Also notifies the marketer who created it"},
    {"id": "quotation_sent", "label": "Quotation Sent to Client", "description": "When a quotation is sent to client", "category": "Marketing", "default_roles": ["admin"]},
    {"id": "quotation_rejected", "label": "Quotation Rejected", "description": "When admin rejects a quotation", "category": "Marketing", "default_roles": ["marketing"]},
    {"id": "lead_won", "label": "Lead Won", "description": "When a lead is marked as won", "category": "Marketing", "default_roles": ["admin", "finance"]},
    {"id": "lead_lost", "label": "Lead Lost", "description": "When a lead is marked as lost", "category": "Marketing", "default_roles": ["admin"]},
    {"id": "invoice_created", "label": "Invoice Created", "description": "When a new invoice is created", "category": "Finance", "default_roles": ["finance", "admin"]},
    {"id": "payment_received", "label": "Payment Received", "description": "When a payment is recorded", "category": "Finance", "default_roles": ["admin", "finance"]},
    {"id": "session_completed", "label": "Session Completed", "description": "When a session is marked as complete", "category": "Operations", "default_roles": ["admin"]},
    {"id": "post_eval_reminder", "label": "Post-Evaluation Reminder", "description": "Reminder sent to participants for post-training evaluation (3/6 months)", "category": "Operations", "default_roles": [], "note": "Sent to session participants using their contact_email"},
]


@router.get("/events")
async def get_notification_events(current_user: User = Depends(get_current_user)):
    """Get all available notification events"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return NOTIFICATION_EVENTS


@router.get("/settings")
async def get_notification_settings(current_user: User = Depends(get_current_user)):
    """Get current notification settings"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = await db.notification_settings.find({}, {"_id": 0}).to_list(100)
    
    # Merge saved settings with defaults for any events not yet configured
    saved_event_ids = {s.get("event_id") for s in settings}
    for event in NOTIFICATION_EVENTS:
        if event["id"] not in saved_event_ids:
            settings.append({
                "event_id": event["id"],
                "enabled": True,
                "recipient_roles": event["default_roles"],
                "recipient_user_ids": [],
                "custom_emails": []
            })
    
    return settings


@router.put("/settings")
async def update_notification_settings(settings: list = Body(...), current_user: User = Depends(get_current_user)):
    """Update notification settings"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time().isoformat()
    
    for s in settings:
        event_id = s.get("event_id")
        if not event_id:
            continue
        
        update_data = {
            "event_id": event_id,
            "enabled": s.get("enabled", True),
            "recipient_roles": s.get("recipient_roles", []),
            "recipient_user_ids": s.get("recipient_user_ids", []),
            "custom_emails": s.get("custom_emails", []),
            "updated_at": now,
            "updated_by": current_user.id
        }
        
        await db.notification_settings.update_one(
            {"event_id": event_id},
            {"$set": update_data},
            upsert=True
        )
    
    return {"message": "Notification settings updated"}


@router.get("/recipients")
async def get_available_recipients(current_user: User = Depends(get_current_user)):
    """Get available staff recipients for notification configuration (deduplicated by email)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    staff_roles = ["admin", "super_admin", "assistant_admin", "finance", "coordinator", "marketing", "trainer"]
    staff = await db.users.find(
        {"role": {"$in": staff_roles}, "is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1}
    ).to_list(500)
    
    # Deduplicate by email, merge roles, skip fake emails
    email_map = {}
    for s in staff:
        email = s.get("email", "")
        if not email or "@temp.mddrc" in email or "@marketing.mddrc" in email or email == "admin@example.com":
            continue
        if email in email_map:
            # Merge roles
            if s["role"] not in email_map[email]["roles"]:
                email_map[email]["roles"].append(s["role"])
        else:
            email_map[email] = {
                "id": s["id"],
                "full_name": s["full_name"],
                "email": email,
                "role": s["role"],
                "roles": [s["role"]]
            }
    
    result = []
    for email, data in email_map.items():
        result.append({
            "id": data["id"],
            "full_name": data["full_name"],
            "email": data["email"],
            "role": "/".join(data["roles"])
        })
    
    return sorted(result, key=lambda x: x["full_name"])


@router.post("/test")
async def send_test_notification(data: dict, current_user: User = Depends(get_current_user)):
    """Send a test notification email"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    to_email = data.get("email", current_user.email)
    
    if not resend.api_key:
        raise HTTPException(status_code=500, detail="RESEND_API_KEY not configured")
    
    html = _get_notification_template(
        "Test Notification",
        "<p>This is a test notification from MDDRC Training Management System.</p>"
        "<p>If you received this email, your notification settings are working correctly!</p>"
        f"<p><small>Sent at: {get_malaysia_time().strftime('%d %B %Y, %I:%M %p')}</small></p>"
    )
    
    try:
        result = await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": "[MDDRC] Test Notification",
            "html": html
        })
        return {"message": f"Test email sent to {to_email}", "email_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send: {str(e)}")


@router.post("/broadcast")
async def send_broadcast_email(
    subject: str = Form(...),
    message: str = Form(...),
    recipient_group: str = Form(...),
    session_id: Optional[str] = Form(None),
    custom_emails: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    """Send broadcast/greeting email to selected groups with optional attachment"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not resend.api_key:
        raise HTTPException(status_code=500, detail="RESEND_API_KEY not configured")
    
    # Resolve recipients based on group
    recipients = set()
    
    if recipient_group == "all_staff":
        staff = await db.users.find(
            {"role": {"$in": ["admin", "super_admin", "assistant_admin", "finance", "coordinator", "marketing", "trainer"]}, "is_active": {"$ne": False}},
            {"_id": 0, "email": 1}
        ).to_list(500)
        recipients = {s["email"] for s in staff if s.get("email") and "@temp.mddrc" not in s["email"]}
    
    elif recipient_group == "all_participants":
        participants = await db.users.find(
            {"role": "participant"},
            {"_id": 0, "email": 1, "contact_email": 1}
        ).to_list(5000)
        for p in participants:
            email = p.get("contact_email") or p.get("email", "")
            if email and "@temp.mddrc" not in email:
                recipients.add(email)
    
    elif recipient_group == "session_participants" and session_id:
        session = await db.sessions.find_one({"id": session_id}, {"_id": 0, "participant_ids": 1})
        if session:
            for pid in session.get("participant_ids", []):
                user = await db.users.find_one({"id": pid}, {"_id": 0, "email": 1, "contact_email": 1})
                if user:
                    email = user.get("contact_email") or user.get("email", "")
                    if email and "@temp.mddrc" not in email:
                        recipients.add(email)
    
    elif recipient_group == "custom" and custom_emails:
        for email in custom_emails.split(","):
            email = email.strip()
            if email and "@" in email:
                recipients.add(email)
    
    if not recipients:
        raise HTTPException(status_code=400, detail="No valid recipients found. Participants may not have provided their email yet.")
    
    # Build email HTML
    html = _get_broadcast_template(subject, message)
    
    # Handle attachment
    attachments = []
    if attachment:
        content = await attachment.read()
        encoded = base64.b64encode(content).decode("utf-8")
        attachments.append({
            "filename": attachment.filename,
            "content": encoded
        })
    
    # Send emails (in batches of 50 for Resend limits)
    recipient_list = list(recipients)
    sent_count = 0
    errors = []
    
    for i in range(0, len(recipient_list), 50):
        batch = recipient_list[i:i+50]
        try:
            params = {
                "from": SENDER_EMAIL,
                "to": batch,
                "subject": subject,
                "html": html
            }
            if attachments:
                params["attachments"] = attachments
            
            await asyncio.to_thread(resend.Emails.send, params)
            sent_count += len(batch)
        except Exception as e:
            errors.append(f"Batch {i//50 + 1}: {str(e)}")
    
    # Log the broadcast
    await db.broadcast_history.insert_one({
        "id": str(uuid.uuid4()),
        "subject": subject,
        "message": message,
        "recipient_group": recipient_group,
        "recipient_count": sent_count,
        "has_attachment": attachment is not None,
        "attachment_name": attachment.filename if attachment else None,
        "sent_by": current_user.id,
        "sent_by_name": current_user.full_name,
        "sent_at": get_malaysia_time().isoformat(),
        "errors": errors
    })
    
    result = {"message": f"Broadcast sent to {sent_count} recipients", "sent": sent_count, "total_recipients": len(recipient_list)}
    if errors:
        result["errors"] = errors
    return result


@router.get("/broadcast-history")
async def get_broadcast_history(current_user: User = Depends(get_current_user)):
    """Get history of sent broadcasts"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    history = await db.broadcast_history.find({}, {"_id": 0}).sort("sent_at", -1).to_list(50)
    return history


# ============ ENHANCED NOTIFICATION DISPATCHER ============

async def send_event_notification(event_id: str, subject: str, html_content: str, extra_recipients: list = None, cc: list = None, reply_to: list = None):
    """Send notification based on configured settings for an event, with optional CC/REPLY-TO."""
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not configured, skipping notification")
        return
    
    # Get settings for this event
    setting = await db.notification_settings.find_one({"event_id": event_id}, {"_id": 0})
    
    if setting and not setting.get("enabled", True):
        return  # Event disabled
    
    recipients = set()
    
    if setting:
        # Add recipients by role
        for role in setting.get("recipient_roles", []):
            users = await db.users.find(
                {"role": role, "is_active": {"$ne": False}},
                {"_id": 0, "email": 1}
            ).to_list(100)
            for u in users:
                if u.get("email") and "@temp.mddrc" not in u["email"]:
                    recipients.add(u["email"])
        
        # Add specific user recipients
        for uid in setting.get("recipient_user_ids", []):
            user = await db.users.find_one({"id": uid}, {"_id": 0, "email": 1})
            if user and user.get("email"):
                recipients.add(user["email"])
        
        # Add custom emails
        for email in setting.get("custom_emails", []):
            if email and "@" in email:
                recipients.add(email)
    else:
        # Use defaults from NOTIFICATION_EVENTS
        event_def = next((e for e in NOTIFICATION_EVENTS if e["id"] == event_id), None)
        if event_def:
            for role in event_def.get("default_roles", []):
                users = await db.users.find(
                    {"role": role, "is_active": {"$ne": False}},
                    {"_id": 0, "email": 1}
                ).to_list(100)
                for u in users:
                    if u.get("email") and "@temp.mddrc" not in u["email"]:
                        recipients.add(u["email"])
    
    # Add extra recipients (e.g., the specific marketer who created something)
    if extra_recipients:
        recipients.update(extra_recipients)
    
    if not recipients:
        admin_email = os.environ.get("ADMIN_EMAIL", "arjuna@mddrc.com.my")
        recipients.add(admin_email)
    
    # Clean CC/REPLY-TO
    clean_cc = [e for e in (cc or []) if e and "@temp.mddrc" not in e and e not in recipients]
    clean_reply_to = [e for e in (reply_to or []) if e and "@temp.mddrc" not in e]
    
    params = {
        "from": SENDER_EMAIL,
        "to": list(recipients),
        "subject": subject,
        "html": html_content
    }
    if clean_cc:
        params["cc"] = clean_cc
    if clean_reply_to:
        params["reply_to"] = clean_reply_to
    
    try:
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Event notification sent: {event_id} to {len(recipients)} recipients (CC:{clean_cc}, REPLY-TO:{clean_reply_to})")
    except Exception as e:
        logger.error(f"Failed to send event notification {event_id}: {str(e)}")


def _get_notification_template(title: str, content: str):
    """Standard notification email template"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>{title}</title></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-radius: 8px;">
            <tr>
                <td style="padding: 20px; text-align: center; background-color: #dc2626; border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 20px;">MDDRC Training System</h1>
                </td>
            </tr>
            <tr>
                <td style="padding: 30px;">
                    <h2 style="color: #1a365d; margin-top: 0;">{title}</h2>
                    {content}
                </td>
            </tr>
            <tr>
                <td style="padding: 15px; text-align: center; background-color: #e9ecef; border-radius: 0 0 8px 8px; font-size: 12px; color: #666;">
                    This is an automated notification from MDDRC Training Management System.
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''


def _get_broadcast_template(title: str, message: str):
    """Broadcast/greeting email template"""
    # Convert newlines to <br> for HTML
    formatted_message = message.replace("\n", "<br>")
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>{title}</title></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb;">
            <tr>
                <td style="padding: 20px; text-align: center; background: linear-gradient(135deg, #1a365d, #2d5a87); border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 22px;">MDDRC</h1>
                    <p style="color: #bdd4f0; margin: 5px 0 0 0; font-size: 13px;">Malaysian Defensive Driving & Riding Centre</p>
                </td>
            </tr>
            <tr>
                <td style="padding: 30px 25px;">
                    <h2 style="color: #1a365d; margin-top: 0; font-size: 20px;">{title}</h2>
                    <div style="font-size: 15px; color: #374151;">
                        {formatted_message}
                    </div>
                </td>
            </tr>
            <tr>
                <td style="padding: 15px; text-align: center; background-color: #f3f4f6; border-radius: 0 0 8px 8px; font-size: 11px; color: #9ca3af;">
                    MDDRC Training Management System<br>
                    This email was sent to you as a valued member of our training community.
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''
