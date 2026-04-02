"""
Pydantic models for the application.
All models are defined here and imported by route files.
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid

# Import timezone helper
try:
    from core import get_malaysia_time
except ImportError:
    # Fallback if core not yet available
    from zoneinfo import ZoneInfo
    MALAYSIA_TZ = ZoneInfo("Asia/Kuala_Lumpur")
    def get_malaysia_time():
        return datetime.now(MALAYSIA_TZ)


# ==================== USER MODELS ====================
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    full_name: str
    id_number: str
    role: str
    additional_roles: List[str] = []
    company_id: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    is_active: bool = True
    profile_verified: Optional[bool] = False
    indemnity_accepted: Optional[bool] = False
    indemnity_accepted_at: Optional[str] = None
    indemnity_signature: Optional[str] = None
    indemnity_signed_name: Optional[str] = None
    indemnity_signed_ic: Optional[str] = None
    indemnity_signed_date: Optional[str] = None
    indemnity_ip_address: Optional[str] = None
    indemnity_user_agent: Optional[str] = None
    indemnity_sections_accepted: Optional[dict] = None
    indemnity_vehicle_reg: Optional[str] = None
    indemnity_training_id: Optional[str] = None
    indemnity_trainer_name: Optional[str] = None
    indemnity_locked: Optional[bool] = False
    social_popup_dismissed: Optional[bool] = False

class UserCreate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    full_name: str
    id_number: str
    role: str
    additional_roles: List[str] = []
    company_id: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: User


# ==================== COMPANY MODELS ====================
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


# ==================== PROGRAM MODELS ====================
class Program(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    pass_percentage: float = 70.0
    certificate_title: Optional[str] = None
    certificate_subtitle: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class ProgramCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pass_percentage: Optional[float] = 70.0
    certificate_title: Optional[str] = None
    certificate_subtitle: Optional[str] = None

class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pass_percentage: Optional[float] = None
    certificate_title: Optional[str] = None
    certificate_subtitle: Optional[str] = None


# ==================== SESSION MODELS ====================
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
    assistant_coordinator_ids: List[str] = []
    status: str = "active"
    completion_status: str = "ongoing"
    is_archived: bool = False
    archived_date: Optional[datetime] = None
    completed_by_coordinator: bool = False
    completed_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)
    marketing_user_id: Optional[str] = None
    commission_type: Optional[str] = None
    commission_rate: Optional[float] = None
    commission_fixed_amount: Optional[float] = None
    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_status: Optional[str] = None
    company_name: Optional[str] = None
    program_name: Optional[str] = None
    cert_show_validity: bool = False
    cert_validity_months: int = 24

class ParticipantData(BaseModel):
    email: Optional[str] = ""
    password: str = "mddrc1"
    full_name: str
    id_number: str
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
    participants: List[ParticipantData] = []
    supervisors: List[SupervisorData] = []
    trainer_assignments: List[dict] = []
    coordinator_id: Optional[str] = None
    assistant_coordinator_ids: List[str] = []
    marketing_user_id: Optional[str] = None
    commission_type: Optional[str] = None
    commission_rate: Optional[float] = None
    commission_fixed_amount: Optional[float] = None
    cert_show_validity: bool = False
    cert_validity_months: int = 24


# ==================== PARTICIPANT ACCESS MODELS ====================
class ParticipantAccess(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    can_access_pre_test: bool = False
    can_access_post_test: bool = False
    can_access_checklist: bool = False
    can_access_feedback: bool = False
    can_clock_out: bool = False
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


# ==================== SETTINGS MODELS ====================
class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "app_settings"
    logo_url: Optional[str] = None
    company_name: str = "Malaysian Defensive Driving and Riding Centre Sdn Bhd"
    primary_color: str = "#3b82f6"
    secondary_color: str = "#6366f1"
    footer_text: str = ""
    certificate_template_url: Optional[str] = None
    max_certificate_file_size_mb: int = 5
    # Business Settings
    company_reg_no: str = ""
    sst_reg_no: str = ""
    sst_rate: float = 6.0
    default_payment_terms: str = "Net 30"
    bank_name: str = ""
    bank_account_no: str = ""
    bank_account_name: str = ""
    invoice_prefix: str = "INV"
    quotation_prefix: str = "QUO"
    credit_note_prefix: str = "CN"
    epf_employer_no: str = ""
    socso_employer_no: str = ""
    eis_employer_no: str = ""
    updated_at: datetime = Field(default_factory=get_malaysia_time)

class SettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    footer_text: Optional[str] = None
    max_certificate_file_size_mb: Optional[int] = None
    # Business Settings
    company_reg_no: Optional[str] = None
    sst_reg_no: Optional[str] = None
    sst_rate: Optional[float] = None
    default_payment_terms: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_account_name: Optional[str] = None
    invoice_prefix: Optional[str] = None
    quotation_prefix: Optional[str] = None
    credit_note_prefix: Optional[str] = None
    epf_employer_no: Optional[str] = None
    socso_employer_no: Optional[str] = None
    eis_employer_no: Optional[str] = None


# ==================== ATTENDANCE MODELS ====================
class Attendance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    date: str
    clock_in: Optional[str] = None
    clock_out: Optional[str] = None
    created_at: datetime = Field(default_factory=get_malaysia_time)

class AttendanceClockIn(BaseModel):
    session_id: str

class AttendanceClockOut(BaseModel):
    session_id: str


# ==================== PASSWORD MODELS ====================
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ==================== VEHICLE & CHECKLIST MODELS ====================
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


class VehicleDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    vehicle_model: str
    registration_number: str
    roadtax_expiry: str
    created_at: datetime = Field(default_factory=get_malaysia_time)


# ==================== FEEDBACK MODELS ====================
class CourseFeedback(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    session_id: str
    program_id: Optional[str] = None
    responses: List[dict]  # [{"question": str, "answer": str/int}]
    submitted_at: datetime = Field(default_factory=get_malaysia_time)


# ==================== COMPANY SETTINGS MODEL ====================
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
    bank_name: str = ""
    bank_account_name: str = ""
    bank_account_number: str = ""
    bank_swift_code: str = ""
    invoice_prefix: str = "INV/MDDRC"
    invoice_terms: str = "Upon receipt of invoice"
    invoice_footer_note: str = "Thank you for your business!"
