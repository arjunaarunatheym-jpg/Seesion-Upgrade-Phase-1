"""
Program-related Pydantic models
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


class Program(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    pass_percentage: float = 70.0
    certificate_title: Optional[str] = None
    certificate_subtitle: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class ProgramCreate(BaseModel):
    name: str
    description: Optional[str] = None
    pass_percentage: Optional[float] = 70.0
    certificate_title: Optional[str] = None
    certificate_subtitle: Optional[str] = None


class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pass_percentage: Optional[str] = None
    certificate_title: Optional[str] = None
    certificate_subtitle: Optional[str] = None
