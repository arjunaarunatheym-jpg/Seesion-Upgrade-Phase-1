"""
Marketing Module routes - Client management, quotations, and PDF generation
Endpoints: 27
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
import uuid
import csv
import re
import os

from fpdf import FPDF
from core import db, get_current_user, get_malaysia_time, ROOT_DIR
from models import User
from utils.email_notifications import (
    notify_new_lead,
    notify_lead_stage_change,
    notify_quotation_for_approval,
    notify_quotation_approved,
    notify_discount_request,
    notify_quotation_sent,
    notify_lead_won,
    notify_lead_lost,
    notify_quotation_accepted,
    notify_quotation_declined,
    notify_quotation_rejected
)

from pydantic import BaseModel, Field, ConfigDict
from pymongo import ReturnDocument


# ============ PDF TEXT SANITIZATION ============
def sanitize_text_for_pdf(text):
    """Sanitize text for PDF - remove problematic characters"""
    if text is None:
        return ""
    text = str(text)
    # Replace problematic characters
    replacements = {
        '\u2013': '-',  # en-dash
        '\u2014': '-',  # em-dash
        '\u2018': "'",  # left single quote
        '\u2019': "'",  # right single quote
        '\u201c': '"',  # left double quote
        '\u201d': '"',  # right double quote
        '\u2022': '*',  # bullet
        '\u2026': '...',  # ellipsis
        '\u00a0': ' ',  # non-breaking space
        '\r\n': '\n',   # Windows line ending
        '\r': '\n',     # Old Mac line ending
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Remove any remaining non-ASCII characters that might cause issues
    text = ''.join(char if ord(char) < 128 or char in 'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ' else '?' for char in text)
    return text


# ============ QUOTATION PDF CLASS ============
class QuotationPDF(FPDF):
    """Custom PDF class for quotation document generation - EXACT invoice styling"""
    
    def __init__(self, company_settings=None, primary_color_rgb=None):
        super().__init__()
        self.company_settings = company_settings or {}
        self.set_auto_page_break(auto=True, margin=30)
        self.primary_color = primary_color_rgb if primary_color_rgb else (26, 54, 93)
        self.secondary_color = (68, 114, 196)
        try:
            self.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
            self.add_font('DejaVu', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', uni=True)
            self.add_font('DejaVu', 'I', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf', uni=True)
            self.unicode_font = True
        except Exception:
            self.unicode_font = False
    
    def set_font_safe(self, style='', size=10):
        if self.unicode_font:
            self.set_font('DejaVu', style, size)
        else:
            self.set_font('Helvetica', style, size)
    
    def cell_safe(self, w, h, txt, **kwargs):
        self.cell(w, h, sanitize_text_for_pdf(txt), **kwargs)
    
    def multi_cell_safe(self, w, h, txt, **kwargs):
        self.multi_cell(w, h, sanitize_text_for_pdf(txt), **kwargs)

    def render_rich_text(self, text, line_height=5, default_size=10):
        """Render text with formatting tags like **bold**, *italic*, <u>, <big>, <small>, <highlight>, colors, <center>, <br>, <hr>, <pb>"""
        import re
        if not text:
            return
        lines = text.replace('<br>', '\n').replace('<br/>', '\n').split('\n')
        for line in lines:
            if not line.strip():
                self.ln(line_height)
                continue
            if '<pb>' in line or '<pagebreak>' in line or '<pb/>' in line:
                self.add_page()
                continue
            if '<hr>' in line or '<hr/>' in line:
                self.set_draw_color(180, 180, 180)
                self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
                self.ln(line_height + 2)
                continue
            is_centered = '<center>' in line
            if is_centered:
                line = line.replace('<center>', '').replace('</center>', '')
            segments = self._parse_rich_segments(line)
            if is_centered:
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
            page_width = 210
            left_margin = 10
            right_margin = 10
            max_x = page_width - right_margin
            for seg in segments:
                style = ''
                if seg.get('bold'): style += 'B'
                if seg.get('italic'): style += 'I'
                if seg.get('underline'): style += 'U'
                size = seg.get('size', default_size)
                self.set_font_safe(style, size)
                color = seg.get('color', (0, 0, 0))
                self.set_text_color(*color)
                seg_text = sanitize_text_for_pdf(seg['text'])
                words = seg_text.split(' ')
                current_line_words = []
                for word in words:
                    test_line = ' '.join(current_line_words + [word]) if current_line_words else word
                    test_width = self.get_string_width(test_line)
                    current_x = self.get_x()
                    if current_x + test_width > max_x:
                        if current_line_words:
                            line_text = ' '.join(current_line_words)
                            line_width = self.get_string_width(line_text)
                            if seg.get('highlight'):
                                x, y = self.get_x(), self.get_y()
                                self.set_fill_color(255, 255, 0)
                                self.rect(x, y, line_width + 1, line_height, 'F')
                                self.set_xy(x, y)
                            self.cell(line_width, line_height, line_text, ln=False)
                        self.ln(line_height)
                        self.set_x(left_margin)
                        current_line_words = [word]
                    else:
                        current_line_words.append(word)
                if current_line_words:
                    line_text = ' '.join(current_line_words)
                    line_width = self.get_string_width(line_text)
                    if seg.get('highlight'):
                        x, y = self.get_x(), self.get_y()
                        self.set_fill_color(255, 255, 0)
                        self.rect(x, y, line_width + 1, line_height, 'F')
                        self.set_xy(x, y)
                    self.cell(line_width, line_height, line_text, ln=False)
                    if self.get_x() < max_x - 5:
                        self.cell(self.get_string_width(' '), line_height, '', ln=False)
            self.ln(line_height)
            self.set_text_color(0, 0, 0)

    def _parse_rich_segments(self, text):
        """Parse text into segments with formatting attributes"""
        import re
        segments = []
        pattern = r'(\*\*([^*]+)\*\*|\*([^*]+)\*|<b>([^<]+)</b>|<i>([^<]+)</i>|<u>([^<]+)</u>|<big>([^<]+)</big>|<small>([^<]+)</small>|<highlight>([^<]+)</highlight>|<hl>([^<]+)</hl>|<red>([^<]+)</red>|<blue>([^<]+)</blue>|<green>([^<]+)</green>)'
        last_end = 0
        for match in re.finditer(pattern, text):
            if match.start() > last_end:
                plain = text[last_end:match.start()]
                if plain:
                    segments.append({'text': plain})
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
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                segments.append({'text': remaining})
        if not segments:
            segments = [{'text': text}]
        return segments

    def header(self):
        """Header matching invoice PDF exactly"""
        cs = self.company_settings
        logo_y = int(cs.get('logo_y') or 5)
        start_y = logo_y
        self.set_y(start_y)
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
                    self.image(str(logo_path), x=10, y=start_y - 2, w=logo_width)
                    logo_end_x = 10 + logo_width + 5
                except:
                    pass
        text_x = logo_end_x
        self.set_xy(text_x, start_y)
        self.set_font_safe('B', 14)
        self.set_text_color(*self.primary_color)
        company_name = cs.get('company_name', 'MALAYSIAN DEFENSIVE DRIVING AND RIDING CENTRE SDN BHD')
        self.cell(0, 6, sanitize_text_for_pdf(company_name), ln=True)
        self.set_x(text_x)
        self.set_font_safe('', 8)
        self.set_text_color(68, 68, 68)
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
            self.cell(0, 4, sanitize_text_for_pdf(' . '.join(line1_parts)), ln=True)
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
            self.cell(0, 4, sanitize_text_for_pdf(' . '.join(line2_parts)), ln=True)
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
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font_safe('', 8)
        self.set_text_color(85, 85, 85)
        bank_info = []
        if cs.get('bank_name'):
            bank_info.append(f"Bank: {cs.get('bank_name')}")
        if cs.get('bank_account_name'):
            bank_info.append(f"Account: {cs.get('bank_account_name')}")
        if cs.get('bank_account_number'):
            bank_info.append(f"No: {cs.get('bank_account_number')}")
        if bank_info:
            self.cell(0, 4, ' | '.join(bank_info), align='C', ln=True)
        footer_note = cs.get('invoice_footer_note', 'Thank you for your business!')
        self.cell(0, 4, footer_note, align='C', ln=True)
        tagline = cs.get('tagline', 'Towards a Nation of Safe Drivers')
        self.set_font_safe('I', 9)
        self.set_text_color(*self.primary_color)
        self.cell(0, 5, f'"{tagline}"', align='C', ln=True)
        self.set_font_safe('', 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 3, f'Page {self.page_no()}', align='C')


# ============ ATOMIC QUOTATION NUMBER GENERATOR (Improvement 2) ============
async def get_next_quotation_number():
    """
    Generate atomic, guaranteed-unique quotation number in format: QUO/MDDRC/YYYY/MM/XXXXX
    
    Uses MongoDB's atomic find_one_and_update to prevent race conditions.
    Counter resets monthly (each month gets its own counter).
    
    Returns: str - The full quotation number (e.g., "QUO/MDDRC/2026/02/00001")
    """
    now = get_malaysia_time()
    year = now.year
    month = now.month
    
    # Counter key is month-specific: "QUO/MDDRC/2026/02"
    counter_key = f"QUO/MDDRC/{year}/{str(month).zfill(2)}"
    
    # Atomic increment - returns the AFTER value
    result = await db.counters.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    
    sequence = result["seq"]
    
    # Format: QUO/MDDRC/YYYY/MM/XXXXX
    quotation_number = f"{counter_key}/{str(sequence).zfill(5)}"
    
    return quotation_number
# ============ END ATOMIC COUNTER ============


# ============ MARKETING AUDIT LOG (Improvement 2) ============
async def log_marketing_action(
    action: str,
    entity_type: str,  # "quotation", "client", "lead", "discount"
    entity_id: str,
    changed_by: User,
    before_value: dict = None,
    after_value: dict = None,
    reason: str = None,
    details: str = None
):
    """Log marketing actions for audit trail
    
    Used for tracking:
    - Quotation creation, status changes
    - Discount applications
    - Client modifications
    - Lead stage changes
    """
    log_entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before_value": before_value,
        "after_value": after_value,
        "changed_by_id": changed_by.id,
        "changed_by_name": changed_by.full_name,
        "changed_by_email": changed_by.email,
        "reason": reason,
        "details": details,
        "timestamp": get_malaysia_time().isoformat()
    }
    await db.marketing_audit_log.insert_one(log_entry)
    return log_entry
# ============ END MARKETING AUDIT LOG ============


# Marketing Models
class MarketingClient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class MarketingClientCreate(BaseModel):
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None

class DescriptionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    unit: Optional[str] = "pax"
    default_rate: float = 0
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class Quotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quotation_number: Optional[str] = None
    client_id: str
    programme_id: Optional[str] = None
    programme_name: Optional[str] = None
    items: List[dict] = []
    subtotal: float = 0
    discount_percentage: float = 0
    discount_amount: float = 0
    sst_percentage: float = 0
    sst_amount: float = 0
    total_amount: float = 0
    validity_days: int = 30
    terms_conditions: Optional[str] = None
    notes: Optional[str] = None
    status: str = "draft"  # draft, pending_approval, approved, sent, accepted, declined, expired
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    submitted_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    sent_at: Optional[str] = None
    client_response_at: Optional[str] = None
    client_response_notes: Optional[str] = None


router = APIRouter(prefix="/marketing", tags=["marketing"])


def check_marketing_access(user: User) -> bool:
    """Check if user has marketing access"""
    if user.role in ["admin", "super_admin"]:
        return True
    if user.role == "marketing":
        return True
    if "marketing" in (user.additional_roles or []):
        return True
    return False


# =====================================================
# CLIENTS
# =====================================================

@router.get("/clients")
async def get_marketing_clients(current_user: User = Depends(get_current_user)):
    """Get clients - marketers see only their own, admin sees all"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    clients = await db.marketing_clients.find(query, {"_id": 0}).to_list(1000)
    
    if current_user.role in ["admin", "super_admin"]:
        user_ids = list(set(c.get("created_by") for c in clients if c.get("created_by")))
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "full_name": 1}).to_list(100)
        user_map = {u["id"]: u.get("full_name", "Unknown") for u in users}
        for c in clients:
            c["marketer_name"] = user_map.get(c.get("created_by"), "Unknown")
    
    return clients


@router.get("/clients/all")
async def get_all_clients_admin(current_user: User = Depends(get_current_user)):
    """Admin only - Get all clients with marketer info"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    clients = await db.marketing_clients.find({}, {"_id": 0}).to_list(1000)
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u["full_name"] for u in users}
    
    for client in clients:
        client["marketer_name"] = user_map.get(client.get("created_by", ""), "Unknown")
    
    return clients


@router.post("/clients")
async def create_marketing_client(client_data: MarketingClientCreate, current_user: User = Depends(get_current_user)):
    """Create a new client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({
        "company_name": {"$regex": f"^{client_data.company_name}$", "$options": "i"},
        "created_by": current_user.id
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a client with this company name")
    
    client = MarketingClient(**client_data.model_dump(), created_by=current_user.id)
    doc = client.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    
    await db.marketing_clients.insert_one(doc)
    return {"message": "Client created successfully", "client": doc}


@router.put("/clients/{client_id}")
async def update_marketing_client(client_id: str, client_data: dict, current_user: User = Depends(get_current_user)):
    """Update a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own clients")
    
    update_fields = {k: v for k, v in client_data.items() if k not in ["id", "created_by", "created_at"]}
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    
    await db.marketing_clients.update_one({"id": client_id}, {"$set": update_fields})
    return {"message": "Client updated successfully"}


@router.delete("/clients/{client_id}")
async def delete_marketing_client(client_id: str, current_user: User = Depends(get_current_user)):
    """Delete a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own clients")
    
    quotation_count = await db.quotations.count_documents({"client_id": client_id})
    if quotation_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete client with {quotation_count} quotation(s)")
    
    await db.marketing_clients.delete_one({"id": client_id})
    return {"message": "Client deleted successfully"}


@router.get("/clients/export")
async def export_all_clients(current_user: User = Depends(get_current_user)):
    """Admin only - Export all clients as CSV"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    clients = await db.marketing_clients.find({}, {"_id": 0}).to_list(1000)
    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1}).to_list(1000)
    user_map = {u["id"]: u["full_name"] for u in users}
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Company Name", "Contact Person", "Email", "Phone", "Address", "Marketer", "Created Date"])
    
    for client in clients:
        marketer_name = user_map.get(client.get("created_by", ""), "Unknown")
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
    
    return StreamingResponse(
        BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="marketing_clients_{datetime.now().strftime("%Y%m%d")}.csv"'}
    )


# =====================================================
# QUOTATIONS
# =====================================================

@router.get("/quotations")
async def get_quotations(status: str = None, current_user: User = Depends(get_current_user)):
    """Get quotations"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    if status:
        query["status"] = status
    
    quotations = await db.quotations.find(query, {"_id": 0}).to_list(1000)
    
    client_ids = list(set(q.get("client_id") for q in quotations if q.get("client_id")))
    clients = await db.marketing_clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(100)
    client_map = {c["id"]: c for c in clients}
    
    user_ids = list(set(q.get("created_by") for q in quotations if q.get("created_by")))
    approver_ids = list(set(q.get("approved_by") for q in quotations if q.get("approved_by")))
    all_user_ids = list(set(user_ids + approver_ids))
    users = await db.users.find({"id": {"$in": all_user_ids}}, {"_id": 0, "id": 1, "full_name": 1, "digital_signature": 1}).to_list(100)
    user_map = {u["id"]: u for u in users}
    
    for q in quotations:
        client = client_map.get(q.get("client_id"), {})
        q["client_name"] = client.get("company_name", "Unknown")
        q["contact_person"] = client.get("contact_person", "")
        marketer_user = user_map.get(q.get("created_by"), {})
        q["marketer_name"] = marketer_user.get("full_name", "Unknown")
        q["marketer"] = {"full_name": marketer_user.get("full_name"), "digital_signature": marketer_user.get("digital_signature")}
        approver_user = user_map.get(q.get("approved_by"), {})
        q["approver"] = {"full_name": approver_user.get("full_name"), "digital_signature": approver_user.get("digital_signature")} if q.get("approved_by") else {}
        # Normalize created_at to string for sorting
        if isinstance(q.get("created_at"), datetime):
            q["created_at"] = q["created_at"].isoformat()
    
    quotations.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return quotations


@router.get("/quotations/{quotation_id}")
async def get_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Get a single quotation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Enrich with client info
    client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
    if client:
        quotation["client"] = client
    
    # Enrich with marketer and approver details (including digital signatures)
    if quotation.get("created_by"):
        marketer = await db.users.find_one({"id": quotation["created_by"]}, {"_id": 0, "id": 1, "full_name": 1, "digital_signature": 1})
        if marketer:
            quotation["marketer"] = {"full_name": marketer.get("full_name"), "digital_signature": marketer.get("digital_signature")}
            quotation["marketer_name"] = marketer.get("full_name", "Unknown")
    if quotation.get("approved_by"):
        approver = await db.users.find_one({"id": quotation["approved_by"]}, {"_id": 0, "id": 1, "full_name": 1, "digital_signature": 1})
        if approver:
            quotation["approver"] = {"full_name": approver.get("full_name"), "digital_signature": approver.get("digital_signature")}
    
    return quotation


@router.post("/quotations")
async def create_quotation(quotation_data: dict, current_user: User = Depends(get_current_user)):
    """Create a new quotation with atomic quotation number generation
    
    Uses atomic counter to prevent duplicate quotation numbers (Improvement 2).
    Format: QUO/MDDRC/YYYY/MM/XXXXX - counter resets monthly.
    
    BACKEND RECALCULATION (Improvement):
    - Ignores frontend totals (subtotal, discount_amount, sst_amount, total_amount)
    - Recalculates all amounts server-side from items[] to prevent tampering
    """
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # ============ ATOMIC QUOTATION NUMBER (Improvement 2) ============
    # Use atomic counter instead of count-based approach to prevent race conditions
    quotation_number = await get_next_quotation_number()
    # ============ END ATOMIC NUMBER ============
    
    now = get_malaysia_time()
    
    # Calculate valid_until date
    validity_days = quotation_data.get("validity_days", 30)
    valid_until = (now + timedelta(days=validity_days)).strftime("%Y-%m-%d")
    
    # ============ BACKEND RECALCULATION (Improvement) ============
    # Ignore frontend totals; recalculate from items to prevent tampering
    items = quotation_data.get("items", [])
    pricing_type = quotation_data.get("pricing_type", "per_pax")
    num_participants = quotation_data.get("num_participants", 1)
    rate_per_pax = float(quotation_data.get("rate_per_pax", 0))
    group_price = float(quotation_data.get("group_price", 0))
    discount_percentage = float(quotation_data.get("discount_percentage", 0))
    sst_percentage = float(quotation_data.get("sst_percentage", 0))
    
    # Calculate subtotal from items or pricing type
    if items:
        subtotal = sum(float(item.get("amount", 0)) for item in items)
    elif pricing_type == "per_pax":
        subtotal = rate_per_pax * num_participants
    else:
        subtotal = group_price
    
    # Add priced addon items (vehicle rental, equipment, etc.) to subtotal
    selected_items = quotation_data.get("selected_items", [])
    addon_total = 0
    for si in selected_items:
        up = float(si.get("unit_price", 0) or 0)
        qty = int(si.get("quantity", 1) or 1)
        if up > 0:
            addon_total += up * qty
    subtotal += addon_total
    
    # Calculate discount
    discount_amount = subtotal * (discount_percentage / 100) if discount_percentage > 0 else 0
    after_discount = subtotal - discount_amount
    
    # Calculate SST
    sst_amount = after_discount * (sst_percentage / 100) if sst_percentage > 0 else 0
    
    # Calculate total
    total_amount = after_discount + sst_amount
    # ============ END BACKEND RECALCULATION ============
    
    quotation = {
        "id": str(uuid.uuid4()),
        "quotation_number": quotation_number,
        "revision_number": 0,  # Track revision count
        "client_id": quotation_data.get("client_id"),
        "programme_id": quotation_data.get("programme_id"),
        "programme_name": quotation_data.get("programme_name"),
        "pricing_type": pricing_type,
        "num_participants": num_participants,
        "rate_per_pax": rate_per_pax,
        "group_price": group_price,
        "items": items,
        "subtotal": subtotal,  # Server-calculated
        "discount_percentage": discount_percentage,
        "discount_amount": discount_amount,  # Server-calculated
        "sst_percentage": sst_percentage,
        "sst_amount": sst_amount,  # Server-calculated
        "total_amount": total_amount,  # Server-calculated
        "validity_days": validity_days,
        "valid_until": valid_until,
        "selected_items": quotation_data.get("selected_items", []),  # Inclusions/exclusions
        "description_items": quotation_data.get("description_items", []),  # Legacy
        "custom_description": quotation_data.get("custom_description"),
        "terms_conditions": quotation_data.get("terms_conditions"),
        "notes": quotation_data.get("notes"),
        "remarks": quotation_data.get("remarks"),
        "status": "draft",
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.quotations.insert_one(quotation)
    
    # Audit log: Quotation created
    await log_marketing_action(
        action="quotation_created",
        entity_type="quotation",
        entity_id=quotation["id"],
        changed_by=current_user,
        after_value={"quotation_number": quotation_number, "total_amount": total_amount},
        details=f"New quotation created: {quotation_number}"
    )
    
    # Remove _id before returning (MongoDB adds it)
    quotation.pop("_id", None)
    
    # AUTO-CREATE LEAD for pipeline tracking
    # If this quotation has a client_id but was NOT created from a lead,
    # auto-create a lead at "quotation_sent" stage so it appears in the pipeline
    lead_id = quotation_data.get("lead_id")
    if not lead_id and quotation.get("client_id"):
        client = await db.marketing_clients.find_one({"id": quotation["client_id"]}, {"_id": 0})
        if client:
            lead_id = str(uuid.uuid4())
            auto_lead = {
                "id": lead_id,
                "company_name": client.get("company_name", ""),
                "contact_person": client.get("contact_person", ""),
                "contact_email": client.get("contact_email", ""),
                "contact_phone": client.get("contact_phone", ""),
                "source": "repeat_client",
                "stage": "quotation_sent",
                "stage_changed_at": now.isoformat(),
                "expected_value": total_amount,
                "programme_interest": quotation.get("programme_name", ""),
                "notes": f"Auto-created from quotation {quotation_number} (returning client)",
                "client_id": client["id"],
                "quotation_id": quotation["id"],
                "created_by": current_user.id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            await db.leads.insert_one(auto_lead)
            
            # Link lead back to quotation
            await db.quotations.update_one(
                {"id": quotation["id"]},
                {"$set": {"lead_id": lead_id}}
            )
            quotation["lead_id"] = lead_id
    
    return {"message": "Quotation created", "quotation": quotation}


@router.put("/quotations/{quotation_id}")
async def update_quotation(quotation_id: str, quotation_data: dict, current_user: User = Depends(get_current_user)):
    """Update a quotation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if existing.get("status") not in ["draft", "pending_approval"]:
        raise HTTPException(status_code=400, detail="Cannot edit quotation in this status")
    
    update_fields = {k: v for k, v in quotation_data.items() if k not in ["id", "created_by", "created_at", "quotation_number"]}
    update_fields["updated_at"] = get_malaysia_time().isoformat()
    
    # Recalculate valid_until if validity_days is updated
    if "validity_days" in update_fields:
        created_at_str = existing.get("created_at", get_malaysia_time().isoformat())
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except:
            created_at = get_malaysia_time()
        update_fields["valid_until"] = (created_at + timedelta(days=update_fields["validity_days"])).strftime("%Y-%m-%d")
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_fields})
    return {"message": "Quotation updated"}


@router.delete("/quotations/{quotation_id}")
async def delete_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Delete a quotation (only drafts can be deleted)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if current_user.role not in ["admin", "super_admin"] and existing.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if existing.get("status") not in ["draft"]:
        raise HTTPException(status_code=400, detail="Only draft quotations can be deleted")
    
    await db.quotations.delete_one({"id": quotation_id})
    return {"message": "Quotation deleted"}



@router.post("/quotations/{quotation_id}/submit")
async def submit_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Submit quotation for approval"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only draft quotations can be submitted")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "pending_approval", "submitted_at": get_malaysia_time().isoformat()}}
    )
    
    # Notify admin for approval (REPLY-TO: marketer)
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        await notify_quotation_for_approval(quotation, client_name, current_user.full_name, marketer_email=current_user.email)
    except:
        pass
    
    return {"message": "Quotation submitted for approval"}


@router.post("/quotations/{quotation_id}/approve")
async def approve_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Approve a quotation (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admin can approve")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Quotation is not pending approval")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "approved", "approved_at": get_malaysia_time().isoformat(), "approved_by": current_user.id}}
    )
    
    # Notify marketer who created the quotation (TO: marketer, CC: admin)
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        marketer = await db.users.find_one({"id": quotation.get("created_by")}, {"_id": 0, "email": 1})
        marketer_email = marketer.get("email") if marketer else None
        await notify_quotation_approved(quotation, client_name, current_user.full_name, marketer_email=marketer_email)
    except:
        pass
    
    return {"message": "Quotation approved"}


@router.post("/quotations/{quotation_id}/reject")
async def reject_quotation(quotation_id: str, reason: dict = None, current_user: User = Depends(get_current_user)):
    """Reject a quotation (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admin can reject")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    rejection_reason = reason.get("reason") if reason else None
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "draft", "rejection_reason": rejection_reason}}
    )
    
    # Send email notification (TO: marketer who created)
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        marketer = await db.users.find_one({"id": quotation.get("created_by")}, {"_id": 0, "email": 1})
        marketer_email = marketer.get("email") if marketer else None
        await notify_quotation_rejected(quotation, client_name, current_user.full_name, rejection_reason or "", marketer_email=marketer_email)
    except:
        pass
    
    return {"message": "Quotation rejected, returned to draft"}


# Helper function to sync lead stage when quotation status changes
async def sync_lead_stage_from_quotation(quotation_id: str, new_status: str):
    """Called when quotation status changes to sync lead stage and value"""
    lead = await db.leads.find_one({"quotation_id": quotation_id}, {"_id": 0})
    if not lead:
        return
    
    # Get quotation to sync value
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    
    stage_map = {
        "sent": "quotation_sent",
        "accepted": "won",
        "declined": "lost"
    }
    
    new_stage = stage_map.get(new_status)
    update_data = {
        "updated_at": get_malaysia_time().isoformat()
    }
    
    if new_stage and lead.get("stage") != new_stage:
        update_data["stage"] = new_stage
        update_data["stage_changed_at"] = get_malaysia_time().isoformat()
    
    # Sync expected_value with quotation's total_amount
    if quotation and quotation.get("total_amount"):
        update_data["expected_value"] = quotation["total_amount"]
    
    if len(update_data) > 1:  # More than just updated_at
        await db.leads.update_one(
            {"quotation_id": quotation_id},
            {"$set": update_data}
        )


@router.post("/quotations/{quotation_id}/mark-sent")
async def mark_quotation_sent(quotation_id: str, current_user: User = Depends(get_current_user)):
    """Mark quotation as sent to client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Only approved quotations can be marked as sent")
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"status": "sent", "sent_at": get_malaysia_time().isoformat()}}
    )
    
    # Sync lead stage
    await sync_lead_stage_from_quotation(quotation_id, "sent")
    
    # Send email notification (TO: client, CC: admin, REPLY-TO: marketer)
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        client_email = client.get("contact_email") if client else None
        await notify_quotation_sent(quotation, client_name, current_user.full_name, client_email=client_email, marketer_email=current_user.email)
    except:
        pass
    
    return {"message": "Quotation marked as sent"}


@router.post("/quotations/{quotation_id}/client-response")
async def record_client_response(quotation_id: str, response_data: dict, current_user: User = Depends(get_current_user)):
    """Record client response (accepted/declined). If accepted, auto-creates a draft session."""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # ========== STATUS GATE (Improvement) ==========
    # Only allow accept/decline if quotation is in "sent" status
    if quotation.get("status") != "sent":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot record response: quotation must be in 'sent' status (current: {quotation.get('status')})"
        )
    # ========== END STATUS GATE ==========
    
    response = response_data.get("response")  # accepted or declined
    if response not in ["accepted", "declined"]:
        raise HTTPException(status_code=400, detail="Response must be 'accepted' or 'declined'")
    
    # ========== IDEMPOTENCY CHECK (Improvement) ==========
    # If session already exists for this quotation, return it instead of creating duplicate
    if response == "accepted":
        existing_session = await db.sessions.find_one({"quotation_id": quotation_id}, {"_id": 0})
        if existing_session:
            return {
                "message": "Session already exists for this quotation",
                "session_id": existing_session.get("id"),
                "existing": True
            }
    # ========== END IDEMPOTENCY CHECK ==========
    
    now = get_malaysia_time()
    
    await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {
            "status": response,
            "client_response_at": now.isoformat(),
            "client_response_notes": response_data.get("notes"),
            "training_date": response_data.get("training_date"),
            "venue": response_data.get("venue")
        }}
    )
    
    # Sync lead stage
    await sync_lead_stage_from_quotation(quotation_id, response)
    
    result = {"message": f"Quotation marked as {response}"}
    
    # If accepted, create a draft session
    if response == "accepted":
        # Get client info
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        
        # Create or find company
        company_id = None
        company_name = client.get("company_name", "Unknown Company") if client else "Unknown Company"
        if client:
            existing_company = await db.companies.find_one(
                {"name": {"$regex": f"^{client['company_name']}$", "$options": "i"}},
                {"_id": 0}
            )
            if existing_company:
                company_id = existing_company.get("id")
            else:
                company_id = str(uuid.uuid4())
                await db.companies.insert_one({
                    "id": company_id,
                    "name": client["company_name"],
                    "address": client.get("company_address", ""),
                    "contact_person": client.get("contact_person", ""),
                    "contact_email": client.get("contact_email", ""),
                    "contact_phone": client.get("contact_phone", ""),
                    "created_at": now.isoformat()
                })
        
        # Get training date from response or quotation
        training_date = response_data.get("training_date") or quotation.get("training_date") or now.strftime("%Y-%m-%d")
        end_date = response_data.get("end_date") or training_date
        venue = response_data.get("venue") or quotation.get("venue") or ""
        
        # Build addon line items from priced quotation items (e.g. vehicle rental)
        addon_line_items = []
        q_selected = quotation.get("selected_items") or []
        if q_selected:
            q_item_ids = [s.get("item_id") for s in q_selected if s.get("item_id")]
            if q_item_ids:
                desc_items = await db.description_items.find({"id": {"$in": q_item_ids}}, {"_id": 0}).to_list(100)
                desc_map = {d["id"]: d for d in desc_items}
                for sel in q_selected:
                    d_item = desc_map.get(sel.get("item_id"))
                    up = sel.get("unit_price", 0)
                    if d_item and (d_item.get("has_pricing") or up > 0) and up > 0:
                        qty = sel.get("quantity", 1)
                        addon_line_items.append({
                            "description": d_item.get("name", "Add-on Item"),
                            "quantity": qty,
                            "unit_price": up,
                            "amount": up * qty
                        })
        
        # Create draft session
        session_id = str(uuid.uuid4())
        session_data = {
            "id": session_id,
            "name": f"{company_name} - {quotation.get('programme_name', 'Training')}",
            "program_id": quotation.get("programme_id", ""),
            "company_id": company_id or "",
            "location": venue,
            "start_date": training_date,
            "end_date": end_date,
            "expected_participants": quotation.get("num_participants", 0),
            "status": "draft",
            "completion_status": "ongoing",
            "supervisor_ids": [],
            "participant_ids": [],
            "trainer_assignments": [],
            "quotation_id": quotation_id,
            "marketing_user_id": quotation.get("created_by"),
            "addon_line_items": addon_line_items,
            "created_at": now.isoformat()
        }
        
        await db.sessions.insert_one(session_data)
        result["session_id"] = session_id
        result["message"] = "Quotation accepted and draft session created"
        
        # Send email notification for accepted quotation
        try:
            await notify_quotation_accepted(quotation, company_name, current_user.full_name)
        except:
            pass
    else:
        # Quotation declined
        try:
            client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
            client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
            await notify_quotation_declined(quotation, client_name, current_user.full_name, response_data.get("notes", ""))
        except:
            pass
    
    return result



@router.post("/quotations/{quotation_id}/apply-discount")
async def apply_discount_to_quotation(quotation_id: str, discount_data: dict, current_user: User = Depends(get_current_user)):
    """Apply discount to a sent quotation (for negotiation) - creates revision number
    
    Validation Rules (Improvement 2 - Marketing & Finance Hardening):
    1. Discount cannot be negative
    2. Discount cannot exceed subtotal
    3. Percentage discount cannot exceed 100%
    4. Cannot apply discount if subtotal = 0
    5. Cannot modify discount if quotation is accepted
    6. Final total must not be negative
    7. SST rate must be valid (0% or 6%)
    """
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # VALIDATION 5: Cannot modify discount if quotation is accepted
    if quotation.get("status") == "accepted":
        raise HTTPException(status_code=400, detail="Cannot modify discount on accepted quotations")
    
    # Only allow discount on SENT quotations (negotiation phase - client has already seen it)
    if quotation.get("status") != "sent":
        raise HTTPException(status_code=400, detail="Discounts can only be applied to quotations that have been sent to the client")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and quotation.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate new totals with discount
    subtotal = quotation.get("subtotal", 0)
    
    # VALIDATION 4: Cannot apply discount if subtotal = 0
    if subtotal <= 0:
        raise HTTPException(status_code=400, detail="Cannot apply discount to quotation with zero or negative subtotal")
    
    discount_type = discount_data.get("discount_type", "percentage")  # percentage or fixed
    discount_value = float(discount_data.get("discount_value", 0))
    
    # VALIDATION 1: Discount cannot be negative
    if discount_value < 0:
        raise HTTPException(status_code=400, detail="Discount value cannot be negative")
    
    # VALIDATION 3: Percentage discount cannot exceed 100%
    if discount_type == "percentage" and discount_value > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100%")
    
    if discount_type == "percentage":
        discount_amount = subtotal * (discount_value / 100)
        discount_percentage = discount_value
    else:
        # VALIDATION 2: Fixed discount cannot exceed subtotal
        if discount_value > subtotal:
            raise HTTPException(status_code=400, detail="Fixed discount cannot exceed subtotal amount")
        discount_amount = discount_value
        discount_percentage = (discount_value / subtotal * 100) if subtotal > 0 else 0
    
    # Recalculate with discount
    discounted_subtotal = subtotal - discount_amount
    
    # VALIDATION 6: Final total must not be negative (sanity check after discount)
    if discounted_subtotal < 0:
        raise HTTPException(status_code=400, detail="Discount would result in negative subtotal")
    
    sst_percentage = quotation.get("sst_percentage", 0)
    
    # VALIDATION 7: SST rate must be valid (0% or 6% for Malaysia)
    if sst_percentage not in [0, 6]:
        raise HTTPException(status_code=400, detail="SST rate must be 0% or 6%")
    
    sst_amount = discounted_subtotal * (sst_percentage / 100)
    new_total = discounted_subtotal + sst_amount
    
    # Increment revision number and update quotation number with suffix
    current_revision = quotation.get("revision_number", 0)
    new_revision = current_revision + 1
    
    # Get base quotation number (without revision suffix)
    base_number = quotation.get("quotation_number", "")
    if "-" in base_number:
        base_number = base_number.split("-")[0]  # Remove existing revision suffix
    
    new_quotation_number = f"{base_number}-{str(new_revision).zfill(2)}"
    
    # Update quotation - set to pending_approval for admin review
    update_data = {
        "quotation_number": new_quotation_number,
        "revision_number": new_revision,
        "discount_percentage": round(discount_percentage, 2),
        "discount_amount": round(discount_amount, 2),
        "sst_amount": round(sst_amount, 2),
        "total_amount": round(new_total, 2),
        "discount_reason": discount_data.get("reason", ""),
        "status": "pending_approval",  # Discount requires admin approval
        "updated_at": get_malaysia_time().isoformat()
    }
    
    await db.quotations.update_one({"id": quotation_id}, {"$set": update_data})
    
    # Audit log: Discount applied (Improvement 2)
    await log_marketing_action(
        action="discount_applied",
        entity_type="quotation",
        entity_id=quotation_id,
        changed_by=current_user,
        before_value={
            "quotation_number": quotation.get("quotation_number"),
            "discount_amount": quotation.get("discount_amount", 0),
            "total_amount": quotation.get("total_amount", 0),
            "status": quotation.get("status")
        },
        after_value={
            "quotation_number": new_quotation_number,
            "discount_amount": round(discount_amount, 2),
            "total_amount": round(new_total, 2),
            "status": "pending_approval"
        },
        reason=discount_data.get("reason", ""),
        details=f"Discount of RM {discount_amount:.2f} ({discount_percentage:.2f}%) applied. Revision {new_revision}"
    )
    
    # Send email notification for discount approval (REPLY-TO: marketer)
    try:
        client = await db.marketing_clients.find_one({"id": quotation.get("client_id")}, {"_id": 0})
        client_name = client.get("company_name", "Unknown Client") if client else "Unknown Client"
        updated_quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
        await notify_discount_request(
            updated_quotation, 
            client_name, 
            current_user.full_name, 
            discount_amount,
            discount_data.get("reason", ""),
            marketer_email=current_user.email
        )
    except:
        pass
    
    updated_quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    return {
        "message": f"Discount applied - Pending admin approval (Revision {new_revision})",
        "quotation": updated_quotation
    }


# Quotation PDF download is handled by the full implementation in server.py
# with rich text rendering support (bold, italic, highlight, colors, etc.)


# =====================================================
# DESCRIPTION ITEMS
# =====================================================

@router.get("/description-items")
async def get_description_items(current_user: User = Depends(get_current_user)):
    """Get all active description items (for marketers to select when creating quotations)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # All marketers can see all active description items
    items = await db.description_items.find({"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]}, {"_id": 0}).to_list(500)
    items.sort(key=lambda x: (x.get("category", ""), x.get("sort_order", 0)))
    return items


@router.get("/description-items/all")
async def get_all_description_items(current_user: User = Depends(get_current_user)):
    """Get all description items (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    items = await db.description_items.find({}, {"_id": 0}).to_list(500)
    return items


@router.post("/description-items")
async def create_description_item(item_data: dict, current_user: User = Depends(get_current_user)):
    """Create a description item (Admin only for inclusions/exclusions)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can create description items")
    
    item = {
        "id": str(uuid.uuid4()),
        "name": item_data.get("name"),
        "description": item_data.get("description", ""),
        "category": item_data.get("category", "inclusion"),  # "inclusion" or "exclusion"
        "has_quantity": item_data.get("has_quantity", False),  # Whether to show quantity input
        "has_pricing": item_data.get("has_pricing", False),  # Whether to show unit price input (e.g. vehicle rental)
        "default_unit_price": item_data.get("default_unit_price", 0),  # Default price per unit
        "is_active": True,
        "sort_order": item_data.get("sort_order", 0),
        "created_by": current_user.id,
        "created_at": get_malaysia_time().isoformat()
    }
    
    await db.description_items.insert_one(item)
    # Remove _id added by MongoDB before returning
    item.pop("_id", None)
    return {"message": "Item created", "item": item}


@router.put("/description-items/{item_id}")
async def update_description_item(item_id: str, item_data: dict, current_user: User = Depends(get_current_user)):
    """Update a description item"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    existing = await db.description_items.find_one({"id": item_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_fields = {k: v for k, v in item_data.items() if k not in ["id", "created_by", "created_at"]}
    await db.description_items.update_one({"id": item_id}, {"$set": update_fields})
    return {"message": "Item updated"}


@router.delete("/description-items/{item_id}")
async def delete_description_item(item_id: str, current_user: User = Depends(get_current_user)):
    """Delete a description item"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    await db.description_items.delete_one({"id": item_id})
    return {"message": "Item deleted"}


# =====================================================
# STATS & HELPERS
# =====================================================

@router.get("/stats")
async def get_marketing_stats(current_user: User = Depends(get_current_user)):
    """Get marketing stats"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    client_query = {}
    if current_user.role not in ["admin", "super_admin"]:
        client_query["created_by"] = current_user.id
    
    client_count = await db.marketing_clients.count_documents(client_query)
    total_quotations = await db.quotations.count_documents(query)
    pending = await db.quotations.count_documents({**query, "status": "pending_approval"})
    approved = await db.quotations.count_documents({**query, "status": "approved"})
    sent = await db.quotations.count_documents({**query, "status": "sent"})
    accepted = await db.quotations.count_documents({**query, "status": "accepted"})
    declined = await db.quotations.count_documents({**query, "status": "declined"})
    
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


@router.get("/programmes")
async def get_programmes_for_quotation(current_user: User = Depends(get_current_user)):
    """Get programmes list for quotation creation"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    programmes = await db.programs.find({}, {"_id": 0, "id": 1, "name": 1, "category": 1, "description": 1}).to_list(100)
    return programmes


@router.get("/default-terms")
async def get_default_terms(current_user: User = Depends(get_current_user)):
    """Get default terms and conditions"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    settings = await db.company_settings.find_one({}, {"_id": 0})
    default_terms = """1. This quotation is valid for 30 days from the date of issue.
2. A 50% deposit is required upon confirmation.
3. Full payment must be made before the training date.
4. Cancellation within 7 days of training will incur a 50% cancellation fee.
5. Prices are subject to SST where applicable."""
    
    return {"terms": settings.get("quotation_terms", default_terms) if settings else default_terms}


@router.get("/pdf-templates")
async def get_pdf_templates(current_user: User = Depends(get_current_user)):
    """Get PDF templates configuration"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    templates = await db.quotation_pdf_templates.find_one({"id": "quotation_pdf_templates"}, {"_id": 0})
    return templates or {"id": "quotation_pdf_templates", "cover_letter": "", "terms_conditions_pages": "", "primary_color": "#1a365d"}


@router.put("/pdf-templates")
async def update_pdf_templates(template_data: dict, current_user: User = Depends(get_current_user)):
    """Update PDF templates (admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    template_data["id"] = "quotation_pdf_templates"
    await db.quotation_pdf_templates.update_one(
        {"id": "quotation_pdf_templates"},
        {"$set": template_data},
        upsert=True
    )
    return {"message": "Templates updated"}


# ==================== LEAD PIPELINE ====================

class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None  # referral, website, cold_call, event, other
    stage: str = "inquiry"  # inquiry, contacted, quotation_sent, negotiating, won, lost
    notes: Optional[str] = None
    expected_value: float = 0
    follow_up_date: Optional[str] = None  # ISO date string
    lost_reason: Optional[str] = None
    quotation_id: Optional[str] = None
    client_id: Optional[str] = None  # Link to client if converted
    created_by: str  # Marketing user ID
    created_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    updated_at: datetime = Field(default_factory=get_malaysia_time)
    stage_changed_at: datetime = Field(default_factory=get_malaysia_time)


class LeadCreate(BaseModel):
    company_name: str
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    expected_value: float = 0
    follow_up_date: Optional[str] = None


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    source: Optional[str] = None
    stage: Optional[str] = None
    notes: Optional[str] = None
    expected_value: Optional[float] = None
    follow_up_date: Optional[str] = None
    lost_reason: Optional[str] = None
    quotation_id: Optional[str] = None
    client_id: Optional[str] = None


@router.get("/leads")
async def get_leads(
    stage: Optional[str] = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get leads - Marketing sees own (non-archived), Admin sees all including archived"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    
    # Marketing users only see their own leads
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
        # Marketing users never see archived leads
        query["is_archived"] = {"$ne": True}
    else:
        # Admins can choose to include archived or not
        if not include_archived:
            query["is_archived"] = {"$ne": True}
    
    if stage:
        query["stage"] = stage
    
    leads = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return leads


@router.get("/leads/archived")
async def get_archived_leads(current_user: User = Depends(get_current_user)):
    """Get archived leads (Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    leads = await db.leads.find({"is_archived": True}, {"_id": 0}).sort("archived_at", -1).to_list(500)
    return leads


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get single lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return lead


@router.post("/leads")
async def create_lead(lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    """Create new lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Check for duplicate company name for this user's leads
    existing = await db.leads.find_one({
        "company_name": {"$regex": f"^{lead_data.company_name.strip()}$", "$options": "i"},
        "created_by": current_user.id,
        "stage": {"$nin": ["won", "lost"]}  # Allow if previous lead was closed
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"You already have an active lead for '{lead_data.company_name}'. Please update the existing lead instead."
        )
    
    lead = Lead(
        company_name=lead_data.company_name.strip(),
        company_address=lead_data.company_address,
        contact_person=lead_data.contact_person,
        contact_email=lead_data.contact_email,
        contact_phone=lead_data.contact_phone,
        source=lead_data.source,
        notes=lead_data.notes,
        expected_value=lead_data.expected_value,
        follow_up_date=lead_data.follow_up_date,
        created_by=current_user.id,
        created_by_name=current_user.full_name
    )
    
    doc = lead.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    doc["stage_changed_at"] = doc["stage_changed_at"].isoformat()
    
    await db.leads.insert_one(doc)
    
    # Send email notification to admin
    try:
        await notify_new_lead(doc, current_user.full_name)
    except Exception as e:
        # Don't fail lead creation if email fails
        pass
    
    return lead


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, lead_data: LeadUpdate, current_user: User = Depends(get_current_user)):
    """Update lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = {k: v for k, v in lead_data.model_dump().items() if v is not None}
    update_data["updated_at"] = get_malaysia_time().isoformat()
    
    # Track stage changes and notify admin for key stages
    new_stage = update_data.get("stage")
    old_stage = lead.get("stage")
    if new_stage and new_stage != old_stage:
        update_data["stage_changed_at"] = get_malaysia_time().isoformat()
        # Notify admin for key stage changes
        if new_stage in ["contacted", "quotation_sent"]:
            try:
                await notify_lead_stage_change(lead, new_stage, current_user.full_name)
            except:
                pass
        elif new_stage == "won":
            try:
                # Get quotation for deal value
                quotation = None
                if lead.get("quotation_id"):
                    quotation = await db.quotations.find_one({"id": lead.get("quotation_id")}, {"_id": 0})
                await notify_lead_won(lead, quotation, current_user.full_name)
            except:
                pass
        elif new_stage == "lost":
            try:
                lost_reason = update_data.get("lost_reason", "") or lead_data.notes if hasattr(lead_data, 'notes') else ""
                await notify_lead_lost(lead, current_user.full_name, lost_reason)
            except:
                pass
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    # Sync client data if lead has a linked client and contact info changed
    if lead.get("client_id"):
        client_sync_fields = {}
        if "company_name" in update_data:
            client_sync_fields["company_name"] = update_data["company_name"]
        if "company_address" in update_data:
            client_sync_fields["company_address"] = update_data["company_address"]
        if "contact_person" in update_data:
            client_sync_fields["contact_person"] = update_data["contact_person"]
        if "contact_email" in update_data:
            client_sync_fields["contact_email"] = update_data["contact_email"]
        if "contact_phone" in update_data:
            client_sync_fields["contact_phone"] = update_data["contact_phone"]
        
        if client_sync_fields:
            client_sync_fields["updated_at"] = get_malaysia_time().isoformat()
            await db.marketing_clients.update_one(
                {"id": lead["client_id"]},
                {"$set": client_sync_fields}
            )
    
    # CASCADE: If company_name changed, update linked quotations and sessions
    if "company_name" in update_data:
        new_company_name = update_data["company_name"]
        
        # Update linked quotation(s)
        if lead.get("quotation_id"):
            await db.quotations.update_one(
                {"id": lead["quotation_id"]},
                {"$set": {"client_name": new_company_name}}
            )
        # Also update any quotation that references this lead
        await db.quotations.update_many(
            {"lead_id": lead_id},
            {"$set": {"client_name": new_company_name}}
        )
        
        # Update linked session(s)
        await db.sessions.update_many(
            {"lead_id": lead_id},
            {"$set": {"company_name": new_company_name}}
        )
        
        # Update invoices linked to sessions from this lead
        sessions_from_lead = await db.sessions.find({"lead_id": lead_id}, {"_id": 0, "id": 1}).to_list(100)
        for session in sessions_from_lead:
            await db.invoices.update_many(
                {"session_id": session["id"]},
                {"$set": {"company_name": new_company_name, "bill_to_name": new_company_name}}
            )
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return updated_lead


@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Delete lead"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Soft delete - archive the lead instead of permanent deletion
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "is_archived": True,
            "archived_at": get_malaysia_time().isoformat(),
            "archived_by": current_user.id,
            "archived_by_name": current_user.full_name
        }}
    )
    return {"message": "Lead archived"}


@router.post("/leads/{lead_id}/unarchive")
async def unarchive_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Unarchive a lead (Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"is_archived": False}, "$unset": {"archived_at": "", "archived_by": "", "archived_by_name": ""}}
    )
    return {"message": "Lead restored"}


@router.post("/leads/{lead_id}/revive")
async def revive_lead(lead_id: str, revive_data: dict, current_user: User = Depends(get_current_user)):
    """Revive a lost lead for future follow-up"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.get("stage") != "lost":
        raise HTTPException(status_code=400, detail="Only lost leads can be revived")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    now = get_malaysia_time()
    update_data = {
        "stage": "inquiry",  # Reset to inquiry
        "follow_up_date": revive_data.get("follow_up_date"),
        "notes": f"{lead.get('notes', '')}\n\n[Revived on {now.strftime('%d/%m/%Y')}] {revive_data.get('reason', '')}".strip(),
        "lost_reason": None,  # Clear lost reason
        "stage_changed_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return {"message": "Lead revived successfully", "lead": updated_lead}


@router.post("/leads/{lead_id}/mark-won")
async def mark_lead_won_and_create_session(lead_id: str, win_data: dict, current_user: User = Depends(get_current_user)):
    """Mark lead as won and optionally create draft session"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    now = get_malaysia_time()
    
    # Update lead to won
    lead_update = {
        "stage": "won",
        "stage_changed_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    await db.leads.update_one({"id": lead_id}, {"$set": lead_update})
    
    result = {"message": "Lead marked as won"}
    
    # Create draft session if training date provided
    training_date = win_data.get("training_date")
    if training_date:
        # Get client and quotation info
        client = None
        if lead.get("client_id"):
            client = await db.marketing_clients.find_one({"id": lead["client_id"]}, {"_id": 0})
        
        quotation = None
        if lead.get("quotation_id"):
            quotation = await db.quotations.find_one({"id": lead["quotation_id"]}, {"_id": 0})
        
        # Create or find company
        company_id = None
        if client:
            # Check if company exists
            existing_company = await db.companies.find_one(
                {"name": {"$regex": f"^{client['company_name']}$", "$options": "i"}},
                {"_id": 0}
            )
            if existing_company:
                company_id = existing_company.get("id")
            else:
                # Create company
                company_id = str(uuid.uuid4())
                await db.companies.insert_one({
                    "id": company_id,
                    "name": client["company_name"],
                    "address": client.get("company_address", ""),
                    "contact_person": client.get("contact_person", ""),
                    "contact_email": client.get("contact_email", ""),
                    "contact_phone": client.get("contact_phone", ""),
                    "created_at": now.isoformat()
                })
        
        # Get programme info
        programme_id = quotation.get("programme_id") if quotation else None
        programme_name = quotation.get("programme_name") if quotation else "Training Programme"
        
        # Create draft session
        session_id = str(uuid.uuid4())
        end_date = win_data.get("end_date") or training_date
        num_participants = win_data.get("num_participants", 0)
        
        session_data = {
            "id": session_id,
            "name": f"{client['company_name'] if client else lead['company_name']} - {programme_name}",
            "program_id": programme_id or "",
            "company_id": company_id or "",
            "location": win_data.get("venue", quotation.get("venue", "") if quotation else ""),
            "start_date": training_date,
            "end_date": end_date,
            "expected_participants": num_participants,
            "status": "draft",  # Draft status for admin review
            "completion_status": "ongoing",
            "supervisor_ids": [],
            "participant_ids": [],
            "trainer_assignments": [],
            "grant_id": win_data.get("grant_id", ""),
            "lead_id": lead_id,
            "quotation_id": lead.get("quotation_id"),
            "marketing_user_id": lead.get("created_by"),
            "created_at": now.isoformat()
        }
        
        await db.sessions.insert_one(session_data)
        result["session_id"] = session_id
        result["message"] = "Lead marked as won and draft session created"
    
    return result



@router.put("/leads/{lead_id}/stage")
async def update_lead_stage(lead_id: str, stage: str, current_user: User = Depends(get_current_user)):
    """Quick update lead stage (for drag-drop)"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    valid_stages = ["inquiry", "contacted", "quotation_sent", "negotiating", "won", "lost"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "stage": stage,
            "updated_at": get_malaysia_time().isoformat(),
            "stage_changed_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": f"Lead moved to {stage}"}


@router.post("/leads/{lead_id}/convert-to-client")
async def convert_lead_to_client(lead_id: str, current_user: User = Depends(get_current_user)):
    """Convert a lead to a client"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if already converted
    if lead.get("client_id"):
        raise HTTPException(status_code=400, detail="Lead already converted to client")
    
    # Create client from lead
    client = MarketingClient(
        company_name=lead["company_name"],
        contact_person=lead.get("contact_person"),
        contact_email=lead.get("contact_email"),
        contact_phone=lead.get("contact_phone"),
        notes=f"Converted from lead. Original notes: {lead.get('notes', '')}",
        created_by=current_user.id
    )
    
    doc = client.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.marketing_clients.insert_one(doc)
    
    # Update lead with client_id and mark as won
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "client_id": client.id,
            "stage": "won",
            "updated_at": get_malaysia_time().isoformat(),
            "stage_changed_at": get_malaysia_time().isoformat()
        }}
    )
    
    return {"message": "Lead converted to client", "client_id": client.id}


# ==================== FOLLOW-UP REMINDERS ====================

@router.get("/leads/reminders/pending")
async def get_pending_reminders(current_user: User = Depends(get_current_user)):
    """Get leads with overdue or upcoming follow-ups"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    today = get_malaysia_time().strftime("%Y-%m-%d")
    
    query = {
        "follow_up_date": {"$ne": None, "$lte": today},
        "stage": {"$nin": ["won", "lost"]}  # Only active leads
    }
    
    # Marketing users only see their own
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    overdue = await db.leads.find(query, {"_id": 0}).sort("follow_up_date", 1).to_list(100)
    
    # Also get upcoming (next 7 days)
    from datetime import timedelta
    next_week = (get_malaysia_time() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    upcoming_query = {
        "follow_up_date": {"$gt": today, "$lte": next_week},
        "stage": {"$nin": ["won", "lost"]}
    }
    if current_user.role not in ["admin", "super_admin"]:
        upcoming_query["created_by"] = current_user.id
    
    upcoming = await db.leads.find(upcoming_query, {"_id": 0}).sort("follow_up_date", 1).to_list(100)
    
    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "overdue_count": len(overdue),
        "upcoming_count": len(upcoming)
    }


# ==================== QUICK STATS ====================

@router.get("/stats/pipeline")
async def get_pipeline_stats(current_user: User = Depends(get_current_user)):
    """Get lead pipeline statistics - Marketing sees own, Admin sees all"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    # Get all leads for this user
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    
    # Count by stage
    stage_counts = {
        "inquiry": 0,
        "contacted": 0,
        "quotation_sent": 0,
        "negotiating": 0,
        "won": 0,
        "lost": 0
    }
    
    total_value = 0
    won_value = 0
    won_count = 0
    total_days_to_close = 0
    
    for lead in leads:
        stage = lead.get("stage", "inquiry")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        total_value += lead.get("expected_value", 0)
        
        if stage == "won":
            won_value += lead.get("expected_value", 0)
            won_count += 1
            # Calculate days to close
            if lead.get("created_at") and lead.get("stage_changed_at"):
                try:
                    created = datetime.fromisoformat(lead["created_at"].replace("Z", "+00:00")) if isinstance(lead["created_at"], str) else lead["created_at"]
                    closed = datetime.fromisoformat(lead["stage_changed_at"].replace("Z", "+00:00")) if isinstance(lead["stage_changed_at"], str) else lead["stage_changed_at"]
                    days = (closed - created).days
                    total_days_to_close += max(days, 0)
                except:
                    pass
    
    total_leads = len(leads)
    closed_leads = stage_counts["won"] + stage_counts["lost"]
    
    # Calculate conversion rate
    conversion_rate = round((won_count / closed_leads * 100), 1) if closed_leads > 0 else 0
    
    # Average deal size
    avg_deal_size = round(won_value / won_count, 2) if won_count > 0 else 0
    
    # Average days to close
    avg_days_to_close = round(total_days_to_close / won_count, 1) if won_count > 0 else 0
    
    return {
        "stage_counts": stage_counts,
        "total_leads": total_leads,
        "total_pipeline_value": total_value,
        "won_value": won_value,
        "conversion_rate": conversion_rate,
        "avg_deal_size": avg_deal_size,
        "avg_days_to_close": avg_days_to_close,
        "active_leads": total_leads - closed_leads
    }


@router.get("/stats/by-source")
async def get_stats_by_source(current_user: User = Depends(get_current_user)):
    """Get lead stats grouped by source"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    query = {}
    if current_user.role not in ["admin", "super_admin"]:
        query["created_by"] = current_user.id
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    
    source_stats = {}
    for lead in leads:
        source = lead.get("source") or "unknown"
        if source not in source_stats:
            source_stats[source] = {"total": 0, "won": 0, "value": 0}
        source_stats[source]["total"] += 1
        if lead.get("stage") == "won":
            source_stats[source]["won"] += 1
            source_stats[source]["value"] += lead.get("expected_value", 0)
    
    return source_stats


@router.get("/stats/by-user")
async def get_stats_by_user(current_user: User = Depends(get_current_user)):
    """Get lead stats by marketing user (Admin only)"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    leads = await db.leads.find({}, {"_id": 0}).to_list(1000)
    
    user_stats = {}
    for lead in leads:
        user_id = lead.get("created_by", "unknown")
        user_name = lead.get("created_by_name", "Unknown")
        
        if user_id not in user_stats:
            user_stats[user_id] = {
                "user_name": user_name,
                "total": 0,
                "won": 0,
                "lost": 0,
                "active": 0,
                "total_value": 0,
                "won_value": 0
            }
        
        user_stats[user_id]["total"] += 1
        user_stats[user_id]["total_value"] += lead.get("expected_value", 0)
        
        stage = lead.get("stage")
        if stage == "won":
            user_stats[user_id]["won"] += 1
            user_stats[user_id]["won_value"] += lead.get("expected_value", 0)
        elif stage == "lost":
            user_stats[user_id]["lost"] += 1
        else:
            user_stats[user_id]["active"] += 1
    
    return user_stats


# ==================== LEAD TO QUOTATION ====================

@router.post("/leads/{lead_id}/create-quotation")
async def create_quotation_from_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Create a quotation from a lead - auto-creates client if needed"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    # Get the lead
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if lead already has a quotation
    if lead.get("quotation_id"):
        existing_quotation = await db.quotations.find_one({"id": lead["quotation_id"]}, {"_id": 0})
        if existing_quotation:
            return {
                "message": "Lead already has a quotation",
                "quotation_id": lead["quotation_id"],
                "client_id": lead.get("client_id"),
                "already_exists": True
            }
    
    # Check if client already exists (by company name for this marketing user)
    client_id = lead.get("client_id")
    if not client_id:
        existing_client = await db.marketing_clients.find_one({
            "company_name": lead["company_name"],
            "created_by": current_user.id
        }, {"_id": 0})
        
        if existing_client:
            client_id = existing_client["id"]
        else:
            # Auto-create client from lead data
            new_client = MarketingClient(
                company_name=lead["company_name"],
                company_address=lead.get("company_address"),
                contact_person=lead.get("contact_person"),
                contact_email=lead.get("contact_email"),
                contact_phone=lead.get("contact_phone"),
                notes=f"Auto-created from lead. Source: {lead.get('source', 'N/A')}",
                created_by=current_user.id
            )
            
            doc = new_client.model_dump()
            doc["created_at"] = doc["created_at"].isoformat()
            await db.marketing_clients.insert_one(doc)
            client_id = new_client.id
    
    # Update lead with client_id
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "client_id": client_id,
            "updated_at": get_malaysia_time().isoformat()
        }}
    )
    
    # Return client data for quotation form pre-fill
    client = await db.marketing_clients.find_one({"id": client_id}, {"_id": 0})
    
    return {
        "message": "Client ready for quotation",
        "client_id": client_id,
        "client": client,
        "lead_id": lead_id,
        "already_exists": False
    }


@router.put("/leads/{lead_id}/link-quotation")
async def link_quotation_to_lead(lead_id: str, quotation_id: str, current_user: User = Depends(get_current_user)):
    """Link a quotation to a lead and update stage"""
    if not check_marketing_access(current_user):
        raise HTTPException(status_code=403, detail="Marketing access required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check ownership for non-admins
    if current_user.role not in ["admin", "super_admin"] and lead.get("created_by") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify quotation exists
    quotation = await db.quotations.find_one({"id": quotation_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Update lead with quotation link and sync value
    update_data = {
        "quotation_id": quotation_id,
        "updated_at": get_malaysia_time().isoformat()
    }
    
    # Sync expected_value with quotation's total_amount
    if quotation.get("total_amount"):
        update_data["expected_value"] = quotation["total_amount"]
    
    # Auto-update stage based on quotation status
    quotation_status = quotation.get("status", "draft")
    if quotation_status in ["sent", "accepted", "declined"]:
        if quotation_status == "accepted":
            update_data["stage"] = "won"
        elif quotation_status == "declined":
            update_data["stage"] = "lost"
        else:
            update_data["stage"] = "quotation_sent"
        update_data["stage_changed_at"] = get_malaysia_time().isoformat()
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    return {"message": "Quotation linked to lead", "stage": update_data.get("stage")}



@router.get("/quotations/{quotation_id}/download-pdf")
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
    priced_items = []  # Items with pricing (vehicle rental, equipment, etc.)
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
                    unit_price = sel.get("unit_price", 0)
                    has_pricing = item.get("has_pricing", False) or unit_price > 0
                    item_data = {
                        "name": item.get("name", ""),
                        "quantity": qty,
                        "has_quantity": item.get("has_quantity", False),
                        "has_pricing": has_pricing,
                        "unit_price": unit_price,
                        "amount": unit_price * qty if has_pricing else 0
                    }
                    category = item.get("category", "")
                    if category in ["inclusion", "inclusions"]:
                        inclusion_items.append(item_data)
                        if has_pricing and unit_price > 0:
                            priced_items.append(item_data)
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
    
    # Calculate training fee from the raw pricing fields (NOT by subtracting from subtotal)
    priced_items_total = sum(p.get("amount", 0) for p in priced_items)
    if pricing_type == 'per_group':
        training_fee = quotation.get("group_price", 0) or 0
    else:
        training_fee = (quotation.get("rate_per_pax", 0) or 0) * (num_pax or 0)
    
    # Correct subtotal = training fee + priced addon items
    correct_subtotal = training_fee + priced_items_total
    
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
    pdf.cell_safe(col_amount, actual_height, f"{training_fee:,.2f}", border=1, align='R')
    pdf.set_y(y_after_desc)
    
    # Draw priced items as separate line items (e.g. Vehicle Rental)
    for p_item in priced_items:
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        item_name = sanitize_text_for_pdf(p_item["name"])
        pdf.multi_cell(col_desc, 5, item_name, border=1)
        y_after = pdf.get_y()
        row_h = y_after - y_start
        pdf.set_xy(x_start + col_desc, y_start)
        pdf.cell_safe(col_qty, row_h, str(p_item.get("quantity", 1)), border=1, align='C')
        pdf.cell_safe(col_rate, row_h, f"{p_item.get('unit_price', 0):,.2f}", border=1, align='R')
        pdf.cell_safe(col_amount, row_h, f"{p_item.get('amount', 0):,.2f}", border=1, align='R')
        pdf.set_y(y_after)
    
    # Inclusions section - new format with quantities (non-priced items only)
    non_priced_inclusions = [i for i in inclusion_items if not (i.get("has_pricing") and i.get("unit_price", 0) > 0)]
    if non_priced_inclusions:
        pdf.set_font_safe('B', 9)
        pdf.set_fill_color(232, 245, 233)  # Light green
        pdf.cell_safe(col_desc + col_qty + col_rate + col_amount, 6, "INCLUSIONS", border='LRB', fill=True, align='L', ln=True)
        pdf.set_font_safe('', 8)
        for item in non_priced_inclusions:
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
    pdf.cell_safe(col_amount, 7, f"{correct_subtotal:,.2f}", border=1, align='R', ln=True)
    
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
    correct_sst = correct_subtotal * sst_pct / 100 if sst_pct > 0 else 0
    correct_total = correct_subtotal + correct_sst - (quotation.get("discount_amount", 0) or 0)
    if sst_pct > 0:
        pdf.cell_safe(col_desc + col_qty + col_rate, 7, f"SST ({sst_pct}%)", border=1, align='R')
        pdf.cell_safe(col_amount, 7, f"{correct_sst:,.2f}", border=1, align='R', ln=True)
    
    # Total row
    pdf.set_font_safe('B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell_safe(col_desc + col_qty + col_rate, 9, "TOTAL (RM)", border=1, align='R', fill=True)
    pdf.cell_safe(col_amount, 9, f"{correct_total:,.2f}", border=1, align='R', fill=True, ln=True)
    
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
