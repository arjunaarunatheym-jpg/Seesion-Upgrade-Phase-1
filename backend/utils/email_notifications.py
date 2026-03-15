"""
Email Notification Utility for Admin Alerts
Uses Resend API to send notifications when marketing events occur
"""
import os
import asyncio
import logging
import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configure Resend
resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "arjuna@mddrc.com.my")


async def send_admin_notification(subject: str, html_content: str):
    """Legacy: Send notification email to admin only (non-blocking)"""
    return await send_smart_notification(subject, html_content, to=[ADMIN_EMAIL])


async def send_smart_notification(subject: str, html_content: str, to: list = None, cc: list = None, reply_to: list = None):
    """Smart email dispatcher with TO, CC, REPLY-TO support"""
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email notification")
        return None
    
    if not to:
        to = [ADMIN_EMAIL]
    
    # Filter out invalid/temp emails
    to = [e for e in to if e and "@temp.mddrc" not in e and "@marketing.mddrc" not in e]
    if cc:
        cc = [e for e in cc if e and "@temp.mddrc" not in e and "@marketing.mddrc" not in e]
    if reply_to:
        reply_to = [e for e in reply_to if e and "@temp.mddrc" not in e and "@marketing.mddrc" not in e]
    
    if not to:
        to = [ADMIN_EMAIL]
    
    params = {
        "from": SENDER_EMAIL,
        "to": to,
        "subject": subject,
        "html": html_content
    }
    if cc:
        params["cc"] = cc
    if reply_to:
        params["reply_to"] = reply_to
    
    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Smart notification sent: {subject} -> TO:{to}, CC:{cc}, REPLY-TO:{reply_to}")
        return email.get("id")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
        return None


def get_email_template(title: str, content: str, action_url: str = None, action_text: str = None):
    """Generate a simple HTML email template"""
    action_button = ""
    if action_url and action_text:
        action_button = f'''
        <tr>
            <td style="padding: 20px 0;">
                <a href="{action_url}" style="background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    {action_text}
                </a>
            </td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
    </head>
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
                    {action_button}
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


async def notify_new_lead(lead_data: dict, marketer_name: str):
    """Notify admin when a new lead is added"""
    content = f'''
    <p>A new lead has been added to the system:</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Company</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("company_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Contact Person</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("contact_person", "N/A")}</td>
        </tr>
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Email</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("contact_email", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Phone</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("contact_phone", "N/A")}</td>
        </tr>
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme Interest</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("programme_interest", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Added By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    '''
    
    html = get_email_template("New Lead Added", content)
    await send_admin_notification(f"[MDDRC] New Lead: {lead_data.get('company_name', 'Unknown')}", html)


async def notify_lead_stage_change(lead_data: dict, new_stage: str, marketer_name: str):
    """Notify admin when a lead stage changes to key stages"""
    stage_labels = {
        "contacted": "Contacted",
        "quotation_sent": "Quotation Sent",
        "negotiating": "Negotiating",
        "won": "Won",
        "lost": "Lost"
    }
    
    stage_label = stage_labels.get(new_stage, new_stage.replace("_", " ").title())
    
    # Different styling based on stage
    stage_color = "#2563eb"  # blue default
    if new_stage == "won":
        stage_color = "#16a34a"  # green
    elif new_stage == "lost":
        stage_color = "#dc2626"  # red
    elif new_stage == "quotation_sent":
        stage_color = "#f59e0b"  # amber
    
    content = f'''
    <p>A lead has moved to <strong style="color: {stage_color};">{stage_label}</strong> stage:</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Company</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("company_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">New Stage</td>
            <td style="padding: 10px; border: 1px solid #ddd;"><span style="background-color: {stage_color}; color: white; padding: 4px 12px; border-radius: 4px;">{stage_label}</span></td>
        </tr>
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Contact Person</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("contact_person", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Updated By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    '''
    
    html = get_email_template(f"Lead Stage: {stage_label}", content)
    await send_admin_notification(f"[MDDRC] Lead Update: {lead_data.get('company_name', 'Unknown')} → {stage_label}", html)


async def notify_quotation_for_approval(quotation_data: dict, client_name: str, marketer_name: str):
    """Quotation Created → TO: arjuna, CC: -"""
    content = f'''
    <p>A quotation requires your approval:</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Quotation No.</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("quotation_number", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Client</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{client_name}</td>
        </tr>
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("programme_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Participants</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("num_participants", 0)} pax</td>
        </tr>
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Total Amount</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #16a34a;">RM {quotation_data.get("total_amount", 0):,.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Submitted By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    <p style="color: #f59e0b; font-weight: bold;">Please review and approve this quotation in the Admin Dashboard.</p>
    '''
    
    html = get_email_template("Quotation Pending Approval", content)
    await send_smart_notification(
        f"[MDDRC] Approval Needed: {quotation_data.get('quotation_number', 'Quotation')} - {client_name}",
        html,
        to=[ADMIN_EMAIL]
    )


async def notify_discount_request(quotation_data: dict, client_name: str, marketer_name: str, discount_amount: float, discount_reason: str = ""):
    """Notify admin when a discount is applied and quotation needs re-approval"""
    content = f'''
    <p><strong style="color: #dc2626;">A discount has been applied to a quotation and requires your approval:</strong></p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Quotation No.</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("quotation_number", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Client</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{client_name}</td>
        </tr>
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Original Amount</td>
            <td style="padding: 10px; border: 1px solid #ddd;">RM {quotation_data.get("subtotal", 0):,.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #dc2626;">Discount Applied</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #dc2626;">- RM {discount_amount:,.2f}</td>
        </tr>
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">New Total</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #16a34a;">RM {quotation_data.get("total_amount", 0):,.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Discount Reason</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{discount_reason or "Not specified"}</td>
        </tr>
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Requested By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    <p style="color: #f59e0b; font-weight: bold;">Please review and approve/reject this discounted quotation.</p>
    '''
    
    html = get_email_template("Discount Approval Required", content)
    await send_admin_notification(f"[MDDRC] DISCOUNT: {quotation_data.get('quotation_number', 'Quotation')} - RM {discount_amount:,.2f} off", html)


async def notify_quotation_sent(quotation_data: dict, client_name: str, marketer_name: str, client_email: str = None, marketer_email: str = None):
    """Quotation Sent to Client → TO: client, CC: arjuna, REPLY-TO: marketer"""
    content = f'''
    <p>A quotation has been sent to the client:</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Quotation No.</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("quotation_number", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Client</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{client_name}</td>
        </tr>
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("programme_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Amount</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #16a34a;">RM {quotation_data.get("total_amount", 0):,.2f}</td>
        </tr>
        <tr style="background-color: #f1f5f9;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Sent By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    <p style="color: #2563eb;">The client is now reviewing this quotation.</p>
    '''
    
    html = get_email_template("Quotation Sent to Client", content)
    
    # If client email available, send to client with reply-to marketer
    to_list = [client_email] if client_email else [ADMIN_EMAIL]
    reply_to_list = [marketer_email] if marketer_email else None
    cc_list = [ADMIN_EMAIL] if client_email else None
    
    await send_smart_notification(
        f"[MDDRC] Quotation: {quotation_data.get('quotation_number', 'Quotation')} - {client_name}",
        html,
        to=to_list,
        cc=cc_list,
        reply_to=reply_to_list
    )


async def notify_lead_won(lead_data: dict, quotation_data: dict, marketer_name: str):
    """Notify admin when a lead is won"""
    content = f'''
    <p style="color: #16a34a; font-size: 18px; font-weight: bold;">🎉 A lead has been WON!</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #dcfce7;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Company</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("company_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Contact Person</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("contact_person", "N/A")}</td>
        </tr>
        <tr style="background-color: #dcfce7;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("programme_name", "N/A") if quotation_data else lead_data.get("programme_interest", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Deal Value</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #16a34a; font-size: 16px;">RM {quotation_data.get("total_amount", 0):,.2f if quotation_data else "N/A"}</td>
        </tr>
        <tr style="background-color: #dcfce7;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Won By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    <p style="color: #16a34a; font-weight: bold;">A draft session has been created for this deal. Please review in Sessions tab.</p>
    '''
    
    html = get_email_template("Deal Won! 🎉", content)
    await send_admin_notification(f"[MDDRC] 🎉 WON: {lead_data.get('company_name', 'Unknown')} - RM {quotation_data.get('total_amount', 0):,.2f if quotation_data else 'N/A'}", html)


async def notify_lead_lost(lead_data: dict, marketer_name: str, lost_reason: str = ""):
    """Notify admin when a lead is lost"""
    content = f'''
    <p style="color: #dc2626; font-size: 18px; font-weight: bold;">A lead has been marked as LOST</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Company</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("company_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Contact Person</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("contact_person", "N/A")}</td>
        </tr>
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme Interest</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lead_data.get("programme_interest", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #dc2626;">Reason for Loss</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{lost_reason or "Not specified"}</td>
        </tr>
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Updated By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    '''
    
    html = get_email_template("Lead Lost", content)
    await send_admin_notification(f"[MDDRC] Lost: {lead_data.get('company_name', 'Unknown')}", html)


async def notify_quotation_accepted(quotation_data: dict, client_name: str, marketer_name: str):
    """Notify admin when a quotation is accepted by client (deal won)"""
    content = f'''
    <p style="color: #16a34a; font-size: 18px; font-weight: bold;">🎉 Quotation Accepted - Deal Won!</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #dcfce7;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Quotation No.</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("quotation_number", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Client</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{client_name}</td>
        </tr>
        <tr style="background-color: #dcfce7;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("programme_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Participants</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("num_participants", 0)} pax</td>
        </tr>
        <tr style="background-color: #dcfce7;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Deal Value</td>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #16a34a; font-size: 16px;">RM {quotation_data.get("total_amount", 0):,.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Marked By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    <p style="color: #16a34a; font-weight: bold;">A draft session has been auto-created. Please review in Sessions tab.</p>
    '''
    
    html = get_email_template("Quotation Accepted! 🎉", content)
    await send_admin_notification(f"[MDDRC] 🎉 ACCEPTED: {quotation_data.get('quotation_number', 'Quotation')} - {client_name} - RM {quotation_data.get('total_amount', 0):,.2f}", html)


async def notify_quotation_declined(quotation_data: dict, client_name: str, marketer_name: str, notes: str = ""):
    """Notify admin when a quotation is declined by client"""
    content = f'''
    <p style="color: #dc2626; font-size: 18px; font-weight: bold;">Quotation Declined by Client</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Quotation No.</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("quotation_number", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Client</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{client_name}</td>
        </tr>
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("programme_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Amount</td>
            <td style="padding: 10px; border: 1px solid #ddd;">RM {quotation_data.get("total_amount", 0):,.2f}</td>
        </tr>
        <tr style="background-color: #fef2f2;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Decline Reason</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{notes or "Not specified"}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Updated By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{marketer_name}</td>
        </tr>
    </table>
    '''
    
    html = get_email_template("Quotation Declined", content)
    await send_admin_notification(f"[MDDRC] Declined: {quotation_data.get('quotation_number', 'Quotation')} - {client_name}", html)


async def notify_quotation_rejected(quotation_data: dict, client_name: str, admin_name: str, reason: str = ""):
    """Notify when admin rejects a quotation (internal rejection, not client decline)"""
    content = f'''
    <p style="color: #f59e0b; font-size: 18px; font-weight: bold;">Quotation Rejected by Admin</p>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #fef3cd;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Quotation No.</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("quotation_number", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Client</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{client_name}</td>
        </tr>
        <tr style="background-color: #fef3cd;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Programme</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{quotation_data.get("programme_name", "N/A")}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Amount</td>
            <td style="padding: 10px; border: 1px solid #ddd;">RM {quotation_data.get("total_amount", 0):,.2f}</td>
        </tr>
        <tr style="background-color: #fef3cd;">
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; color: #dc2626;">Rejection Reason</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{reason or "Not specified"}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Rejected By</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{admin_name}</td>
        </tr>
    </table>
    <p>The marketer will need to revise and resubmit this quotation.</p>
    '''
    
    html = get_email_template("Quotation Rejected", content)
    await send_admin_notification(f"[MDDRC] Rejected: {quotation_data.get('quotation_number', 'Quotation')} - {client_name}", html)
