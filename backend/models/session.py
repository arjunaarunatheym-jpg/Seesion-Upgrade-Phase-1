"""
Session-related Pydantic models
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid
from .user import ParticipantData, SupervisorData


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
    status: str = "active"  # "active" or "inactive"
    completion_status: str = "ongoing"  # "ongoing", "completed", "archived"
    is_archived: bool = False
    archived_date: Optional[datetime] = None
    completed_by_coordinator: bool = False
    completed_date: Optional[datetime] = None
    funding_source: Optional[str] = None  # "self_pay" | "hrdcorp" | None
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    # Enriched fields (populated at runtime)
    company_name: Optional[str] = None
    program_name: Optional[str] = None


class SessionCreate(BaseModel):
    name: str
    program_id: str
    company_id: str
    location: str
    start_date: str
    end_date: str
    supervisor_ids: List[str] = []
    participant_ids: List[str] = []
    participants: List[ParticipantData] = []  # New participants to create or link
    supervisors: List[SupervisorData] = []  # New supervisors to create or link
    trainer_assignments: List[dict] = []
    coordinator_id: Optional[str] = None
