"""
Smart Email Dispatcher for MDDRC Training Management System.
Contextual TO / CC / REPLY-TO routing for every business event.

Routing Rules:
  Quotation Created (for approval) → TO: Admin | REPLY-TO: Marketer
  Quotation Approved                → TO: Marketer | CC: Admin
  Quotation Rejected                → TO: Marketer
  Quotation Sent to Client          → TO: Client | CC: Admin | REPLY-TO: Marketer
  Quotation Accepted (deal won)     → TO: Admin | CC: Finance
  Quotation Declined                → TO: Admin
  Discount Request                  → TO: Admin | REPLY-TO: Marketer
  Invoice Issued                    → TO: Client contact | CC: Admin, Finance
  Payment Received                  → TO: Admin, Finance
  Session Completed                 → TO: Admin | CC: Coordinator, Trainer
  Lead Created                      → TO: Admin
  Lead Stage Change                 → TO: Admin
  Lead Won                          → TO: Admin | CC: Finance
  Lead Lost                         → TO: Admin
"""
import os
import asyncio
import logging
import resend
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "arjuna@mddrc.com.my")


def _clean(emails):
    """Filter out invalid/placeholder emails."""
    if not emails:
        return []
    return [e for e in emails if e and "@temp.mddrc" not in e and "@marketing.mddrc" not in e and "@example.com" not in e]


async def send_smart_notification(subject: str, html_content: str, to: list = None, cc: list = None, reply_to: list = None):
    """Core dispatcher – sends email via Resend with TO / CC / REPLY-TO."""
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email")
        return None

    to = _clean(to) or [ADMIN_EMAIL]
    cc = _clean(cc) or None
    reply_to = _clean(reply_to) or None

    # Remove duplicates between TO and CC
    if cc:
        cc = [e for e in cc if e not in to]
        if not cc:
            cc = None

    params = {"from": SENDER_EMAIL, "to": to, "subject": subject, "html": html_content}
    if cc:
        params["cc"] = cc
    if reply_to:
        params["reply_to"] = reply_to

    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent: {subject} -> TO:{to} CC:{cc} REPLY-TO:{reply_to}")
        return result.get("id")
    except Exception as e:
        logger.error(f"Failed to send email '{subject}': {e}")
        return None


def _template(title: str, content: str, action_url: str = None, action_text: str = None):
    """Standard HTML email template."""
    action_button = ""
    if action_url and action_text:
        action_button = f'''
        <tr><td style="padding:20px 0;">
            <a href="{action_url}" style="background-color:#dc2626;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;">{action_text}</a>
        </td></tr>'''
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title></head>
    <body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;max-width:600px;margin:0 auto;padding:20px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8f9fa;border-radius:8px;">
      <tr><td style="padding:20px;text-align:center;background-color:#dc2626;border-radius:8px 8px 0 0;">
        <h1 style="color:white;margin:0;font-size:20px;">MDDRC Training System</h1>
      </td></tr>
      <tr><td style="padding:30px;">
        <h2 style="color:#1a365d;margin-top:0;">{title}</h2>
        {content}
        {action_button}
      </td></tr>
      <tr><td style="padding:15px;text-align:center;background-color:#e9ecef;border-radius:0 0 8px 8px;font-size:12px;color:#666;">
        This is an automated notification from MDDRC Training Management System.
      </td></tr>
    </table></body></html>'''


def _table(rows: list, highlight_color: str = "#f1f5f9"):
    """Build an HTML table from (label, value) pairs."""
    html = '<table style="width:100%;border-collapse:collapse;margin:15px 0;">'
    for i, (label, value) in enumerate(rows):
        bg = f' style="background-color:{highlight_color};"' if i % 2 == 0 else ""
        html += f'<tr{bg}><td style="padding:10px;border:1px solid #ddd;font-weight:bold;">{label}</td><td style="padding:10px;border:1px solid #ddd;">{value}</td></tr>'
    html += "</table>"
    return html


# ───────────────────────────────────────────────
#  QUOTATION EVENTS
# ───────────────────────────────────────────────

async def notify_quotation_for_approval(quotation: dict, client_name: str, marketer_name: str, marketer_email: str = None):
    """Quotation Created / Submitted for Approval  →  TO: Admin  |  REPLY-TO: Marketer"""
    rows = [
        ("Quotation No.", quotation.get("quotation_number", "N/A")),
        ("Client", client_name),
        ("Programme", quotation.get("programme_name", "N/A")),
        ("Participants", f"{quotation.get('num_participants', 0)} pax"),
        ("Total Amount", f"<strong style='color:#16a34a;'>RM {quotation.get('total_amount', 0):,.2f}</strong>"),
        ("Submitted By", marketer_name),
    ]
    content = f"<p>A quotation requires your approval:</p>{_table(rows)}<p style='color:#f59e0b;font-weight:bold;'>Please review and approve this quotation in the Admin Dashboard.</p>"
    html = _template("Quotation Pending Approval", content)
    await send_smart_notification(
        f"[MDDRC] Approval Needed: {quotation.get('quotation_number', 'Quotation')} - {client_name}",
        html,
        to=[ADMIN_EMAIL],
        reply_to=[marketer_email] if marketer_email else None,
    )


async def notify_quotation_approved(quotation: dict, client_name: str, admin_name: str, marketer_email: str = None):
    """Quotation Approved  →  TO: Marketer  |  CC: Admin"""
    rows = [
        ("Quotation No.", quotation.get("quotation_number", "N/A")),
        ("Client", client_name),
        ("Programme", quotation.get("programme_name", "N/A")),
        ("Total Amount", f"<strong style='color:#16a34a;'>RM {quotation.get('total_amount', 0):,.2f}</strong>"),
        ("Approved By", admin_name),
    ]
    content = f"<p style='color:#16a34a;font-weight:bold;'>Your quotation has been approved!</p>{_table(rows, '#dcfce7')}<p>You can now mark this quotation as sent to the client.</p>"
    html = _template("Quotation Approved", content)
    await send_smart_notification(
        f"[MDDRC] Approved: {quotation.get('quotation_number', 'Quotation')} - {client_name}",
        html,
        to=[marketer_email] if marketer_email else [ADMIN_EMAIL],
        cc=[ADMIN_EMAIL] if marketer_email else None,
    )


async def notify_quotation_rejected(quotation: dict, client_name: str, admin_name: str, reason: str = "", marketer_email: str = None):
    """Quotation Rejected  →  TO: Marketer"""
    rows = [
        ("Quotation No.", quotation.get("quotation_number", "N/A")),
        ("Client", client_name),
        ("Programme", quotation.get("programme_name", "N/A")),
        ("Amount", f"RM {quotation.get('total_amount', 0):,.2f}"),
        ("Rejection Reason", reason or "Not specified"),
        ("Rejected By", admin_name),
    ]
    content = f"<p style='color:#f59e0b;font-size:18px;font-weight:bold;'>Quotation Rejected by Admin</p>{_table(rows, '#fef3cd')}<p>Please revise and resubmit this quotation.</p>"
    html = _template("Quotation Rejected", content)
    await send_smart_notification(
        f"[MDDRC] Rejected: {quotation.get('quotation_number', 'Quotation')} - {client_name}",
        html,
        to=[marketer_email] if marketer_email else [ADMIN_EMAIL],
    )


async def notify_quotation_sent(quotation: dict, client_name: str, marketer_name: str, client_email: str = None, marketer_email: str = None):
    """Quotation Sent to Client  →  TO: Client  |  CC: Admin  |  REPLY-TO: Marketer"""
    rows = [
        ("Quotation No.", quotation.get("quotation_number", "N/A")),
        ("Client", client_name),
        ("Programme", quotation.get("programme_name", "N/A")),
        ("Amount", f"<strong style='color:#16a34a;'>RM {quotation.get('total_amount', 0):,.2f}</strong>"),
        ("Sent By", marketer_name),
    ]
    content = f"<p>A quotation has been sent to the client:</p>{_table(rows)}<p style='color:#2563eb;'>The client is now reviewing this quotation.</p>"
    html = _template("Quotation Sent to Client", content)

    to_list = [client_email] if client_email else [ADMIN_EMAIL]
    cc_list = [ADMIN_EMAIL] if client_email else None
    reply_to_list = [marketer_email] if marketer_email else None

    await send_smart_notification(
        f"[MDDRC] Quotation: {quotation.get('quotation_number', 'Quotation')} - {client_name}",
        html,
        to=to_list,
        cc=cc_list,
        reply_to=reply_to_list,
    )


async def notify_quotation_accepted(quotation: dict, client_name: str, marketer_name: str):
    """Quotation Accepted (deal won)  →  TO: Admin  |  CC: Finance"""
    rows = [
        ("Quotation No.", quotation.get("quotation_number", "N/A")),
        ("Client", client_name),
        ("Programme", quotation.get("programme_name", "N/A")),
        ("Participants", f"{quotation.get('num_participants', 0)} pax"),
        ("Deal Value", f"<strong style='color:#16a34a;font-size:16px;'>RM {quotation.get('total_amount', 0):,.2f}</strong>"),
        ("Marked By", marketer_name),
    ]
    content = f"<p style='color:#16a34a;font-size:18px;font-weight:bold;'>Quotation Accepted – Deal Won!</p>{_table(rows, '#dcfce7')}<p style='color:#16a34a;font-weight:bold;'>A draft session has been auto-created. Please review in Sessions tab.</p>"
    html = _template("Quotation Accepted!", content)

    # CC finance role users
    from core import db
    finance_emails = []
    async for u in db.users.find({"role": "finance", "is_active": {"$ne": False}}, {"_id": 0, "email": 1}):
        if u.get("email") and "@temp.mddrc" not in u["email"]:
            finance_emails.append(u["email"])

    await send_smart_notification(
        f"[MDDRC] ACCEPTED: {quotation.get('quotation_number', 'Quotation')} - {client_name} - RM {quotation.get('total_amount', 0):,.2f}",
        html,
        to=[ADMIN_EMAIL],
        cc=finance_emails or None,
    )


async def notify_quotation_declined(quotation: dict, client_name: str, marketer_name: str, notes: str = ""):
    """Quotation Declined  →  TO: Admin"""
    rows = [
        ("Quotation No.", quotation.get("quotation_number", "N/A")),
        ("Client", client_name),
        ("Programme", quotation.get("programme_name", "N/A")),
        ("Amount", f"RM {quotation.get('total_amount', 0):,.2f}"),
        ("Decline Reason", notes or "Not specified"),
        ("Updated By", marketer_name),
    ]
    content = f"<p style='color:#dc2626;font-size:18px;font-weight:bold;'>Quotation Declined by Client</p>{_table(rows, '#fef2f2')}"
    html = _template("Quotation Declined", content)
    await send_smart_notification(
        f"[MDDRC] Declined: {quotation.get('quotation_number', 'Quotation')} - {client_name}",
        html,
        to=[ADMIN_EMAIL],
    )


async def notify_discount_request(quotation: dict, client_name: str, marketer_name: str, discount_amount: float, discount_reason: str = "", marketer_email: str = None):
    """Discount Request  →  TO: Admin  |  REPLY-TO: Marketer"""
    rows = [
        ("Quotation No.", quotation.get("quotation_number", "N/A")),
        ("Client", client_name),
        ("Original Amount", f"RM {quotation.get('subtotal', 0):,.2f}"),
        ("<span style='color:#dc2626;'>Discount Applied</span>", f"<strong style='color:#dc2626;'>- RM {discount_amount:,.2f}</strong>"),
        ("New Total", f"<strong style='color:#16a34a;'>RM {quotation.get('total_amount', 0):,.2f}</strong>"),
        ("Reason", discount_reason or "Not specified"),
        ("Requested By", marketer_name),
    ]
    content = f"<p><strong style='color:#dc2626;'>A discount has been applied and requires your approval:</strong></p>{_table(rows, '#fef2f2')}<p style='color:#f59e0b;font-weight:bold;'>Please review and approve/reject this discounted quotation.</p>"
    html = _template("Discount Approval Required", content)
    await send_smart_notification(
        f"[MDDRC] DISCOUNT: {quotation.get('quotation_number', 'Quotation')} - RM {discount_amount:,.2f} off",
        html,
        to=[ADMIN_EMAIL],
        reply_to=[marketer_email] if marketer_email else None,
    )


# ───────────────────────────────────────────────
#  FINANCE EVENTS
# ───────────────────────────────────────────────

async def notify_invoice_issued(invoice: dict, session: dict = None):
    """Invoice Issued  →  TO: Client company contact  |  CC: Admin, Finance"""
    from core import db

    company_email = None
    if invoice.get("company_id"):
        company = await db.companies.find_one({"id": invoice["company_id"]}, {"_id": 0, "contact_email": 1})
        if company:
            company_email = company.get("contact_email")

    finance_emails = []
    async for u in db.users.find({"role": "finance", "is_active": {"$ne": False}}, {"_id": 0, "email": 1}):
        if u.get("email") and "@temp.mddrc" not in u["email"]:
            finance_emails.append(u["email"])

    rows = [
        ("Invoice No.", invoice.get("invoice_number", "N/A")),
        ("Company", invoice.get("company_name", "N/A")),
        ("Programme", invoice.get("programme_name", "N/A")),
        ("Amount", f"<strong style='color:#16a34a;'>RM {invoice.get('total_amount', 0):,.2f}</strong>"),
    ]
    content = f"<p>An invoice has been issued:</p>{_table(rows)}"
    html = _template("Invoice Issued", content)

    to_list = [company_email] if company_email else [ADMIN_EMAIL]
    cc_list = list(set([ADMIN_EMAIL] + finance_emails))
    if company_email:
        cc_list = [e for e in cc_list if e != company_email]

    await send_smart_notification(
        f"[MDDRC] Invoice Issued: {invoice.get('invoice_number', 'Invoice')} - {invoice.get('company_name', '')}",
        html,
        to=to_list,
        cc=cc_list or None,
    )


async def notify_payment_received(payment: dict, invoice: dict):
    """Payment Received  →  TO: Admin, Finance"""
    from core import db

    finance_emails = []
    async for u in db.users.find({"role": "finance", "is_active": {"$ne": False}}, {"_id": 0, "email": 1}):
        if u.get("email") and "@temp.mddrc" not in u["email"]:
            finance_emails.append(u["email"])

    rows = [
        ("Invoice No.", invoice.get("invoice_number", "N/A")),
        ("Company", invoice.get("company_name", "N/A")),
        ("Payment Amount", f"<strong style='color:#16a34a;'>RM {payment.get('amount', 0):,.2f}</strong>"),
        ("Payment Method", (payment.get("payment_method") or "N/A").replace("_", " ").title()),
        ("Reference", payment.get("reference_number") or "N/A"),
        ("Date", payment.get("payment_date", "N/A")),
    ]
    content = f"<p>A payment has been recorded:</p>{_table(rows, '#dcfce7')}"
    html = _template("Payment Received", content)

    to_list = list(set([ADMIN_EMAIL] + finance_emails))
    await send_smart_notification(
        f"[MDDRC] Payment: RM {payment.get('amount', 0):,.2f} - {invoice.get('company_name', '')}",
        html,
        to=to_list,
    )


# ───────────────────────────────────────────────
#  SESSION / OPERATIONS EVENTS
# ───────────────────────────────────────────────

async def notify_session_completed(session: dict):
    """Session Completed  →  TO: Admin  |  CC: Coordinator, Trainer"""
    from core import db

    cc_emails = []
    # Coordinator
    for cid in [session.get("coordinator_id")] + (session.get("assistant_coordinator_ids") or []):
        if cid:
            user = await db.users.find_one({"id": cid}, {"_id": 0, "email": 1})
            if user and user.get("email"):
                cc_emails.append(user["email"])
    # Trainers
    for ta in session.get("trainer_assignments") or []:
        tid = ta.get("trainer_id") if isinstance(ta, dict) else ta
        if tid:
            user = await db.users.find_one({"id": tid}, {"_id": 0, "email": 1})
            if user and user.get("email"):
                cc_emails.append(user["email"])

    rows = [
        ("Session", session.get("name", "N/A")),
        ("Date", f"{session.get('start_date', 'N/A')} to {session.get('end_date', 'N/A')}"),
        ("Location", session.get("location", "N/A")),
        ("Participants", str(len(session.get("participant_ids", [])))),
    ]
    content = f"<p>A training session has been completed:</p>{_table(rows)}"
    html = _template("Session Completed", content)

    await send_smart_notification(
        f"[MDDRC] Session Completed: {session.get('name', 'Session')}",
        html,
        to=[ADMIN_EMAIL],
        cc=cc_emails or None,
    )


# ───────────────────────────────────────────────
#  LEAD EVENTS
# ───────────────────────────────────────────────

async def notify_new_lead(lead_data: dict, marketer_name: str):
    """New Lead  →  TO: Admin"""
    rows = [
        ("Company", lead_data.get("company_name", "N/A")),
        ("Contact Person", lead_data.get("contact_person", "N/A")),
        ("Email", lead_data.get("contact_email", "N/A")),
        ("Phone", lead_data.get("contact_phone", "N/A")),
        ("Programme Interest", lead_data.get("programme_interest", "N/A")),
        ("Added By", marketer_name),
    ]
    content = f"<p>A new lead has been added to the system:</p>{_table(rows)}"
    html = _template("New Lead Added", content)
    await send_smart_notification(f"[MDDRC] New Lead: {lead_data.get('company_name', 'Unknown')}", html, to=[ADMIN_EMAIL])


async def notify_lead_stage_change(lead_data: dict, new_stage: str, marketer_name: str):
    """Lead Stage Change  →  TO: Admin"""
    stage_labels = {"contacted": "Contacted", "quotation_sent": "Quotation Sent", "negotiating": "Negotiating", "won": "Won", "lost": "Lost"}
    stage_label = stage_labels.get(new_stage, new_stage.replace("_", " ").title())
    stage_color = {"won": "#16a34a", "lost": "#dc2626", "quotation_sent": "#f59e0b"}.get(new_stage, "#2563eb")
    rows = [
        ("Company", lead_data.get("company_name", "N/A")),
        ("New Stage", f"<span style='background-color:{stage_color};color:white;padding:4px 12px;border-radius:4px;'>{stage_label}</span>"),
        ("Contact Person", lead_data.get("contact_person", "N/A")),
        ("Updated By", marketer_name),
    ]
    content = f"<p>A lead has moved to <strong style='color:{stage_color};'>{stage_label}</strong> stage:</p>{_table(rows)}"
    html = _template(f"Lead Stage: {stage_label}", content)
    await send_smart_notification(f"[MDDRC] Lead Update: {lead_data.get('company_name', 'Unknown')} -> {stage_label}", html, to=[ADMIN_EMAIL])


async def notify_lead_won(lead_data: dict, quotation_data: dict, marketer_name: str):
    """Lead Won  →  TO: Admin  |  CC: Finance"""
    from core import db
    finance_emails = []
    async for u in db.users.find({"role": "finance", "is_active": {"$ne": False}}, {"_id": 0, "email": 1}):
        if u.get("email") and "@temp.mddrc" not in u["email"]:
            finance_emails.append(u["email"])

    deal_value = f"RM {quotation_data.get('total_amount', 0):,.2f}" if quotation_data else "N/A"
    rows = [
        ("Company", lead_data.get("company_name", "N/A")),
        ("Contact Person", lead_data.get("contact_person", "N/A")),
        ("Programme", quotation_data.get("programme_name", "N/A") if quotation_data else lead_data.get("programme_interest", "N/A")),
        ("Deal Value", f"<strong style='color:#16a34a;font-size:16px;'>{deal_value}</strong>"),
        ("Won By", marketer_name),
    ]
    content = f"<p style='color:#16a34a;font-size:18px;font-weight:bold;'>A lead has been WON!</p>{_table(rows, '#dcfce7')}<p style='color:#16a34a;font-weight:bold;'>A draft session has been created for this deal.</p>"
    html = _template("Deal Won!", content)
    await send_smart_notification(
        f"[MDDRC] WON: {lead_data.get('company_name', 'Unknown')} - {deal_value}",
        html,
        to=[ADMIN_EMAIL],
        cc=finance_emails or None,
    )


async def notify_lead_lost(lead_data: dict, marketer_name: str, lost_reason: str = ""):
    """Lead Lost  →  TO: Admin"""
    rows = [
        ("Company", lead_data.get("company_name", "N/A")),
        ("Contact Person", lead_data.get("contact_person", "N/A")),
        ("Programme Interest", lead_data.get("programme_interest", "N/A")),
        ("Reason for Loss", lost_reason or "Not specified"),
        ("Updated By", marketer_name),
    ]
    content = f"<p style='color:#dc2626;font-size:18px;font-weight:bold;'>A lead has been marked as LOST</p>{_table(rows, '#fef2f2')}"
    html = _template("Lead Lost", content)
    await send_smart_notification(f"[MDDRC] Lost: {lead_data.get('company_name', 'Unknown')}", html, to=[ADMIN_EMAIL])
