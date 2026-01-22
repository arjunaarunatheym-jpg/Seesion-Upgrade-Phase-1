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
    created_at: datetime = Field(default_factory=get_malaysia_time)

class ProgramCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pass_percentage: Optional[float] = 70.0

class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pass_percentage: Optional[float] = None


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
    updated_at: datetime = Field(default_factory=get_malaysia_time)

class SettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    footer_text: Optional[str] = None
    max_certificate_file_size_mb: Optional[int] = None


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
