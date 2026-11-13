"""
Data Models for ASHA Voice Field Register
Complies with Gnani Hackathon PS1 specifications.
"""
from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import uuid

class DangerSignAlert(BaseModel):
    id: str
    name: str
    category: Literal["maternal", "newborn"]
    action_required: str
    guideline_reference: str = "MoHFW / NHM Module 6 & 7: Skills That Save Lives"

class VisitRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    beneficiary_id: Optional[str] = Field(None, description="Beneficiary ID or synthetic code")
    beneficiary_name: Optional[str] = Field(None, description="Beneficiary patient/mother/child name")
    visit_type: Optional[str] = Field(None, description="ANC checkup, PNC, Newborn care, or Immunisation")
    weight: Optional[float] = Field(None, description="Weight in kg (e.g. 2.8, 52.5)")
    vaccinations_due: List[str] = Field(default_factory=list, description="Vaccinations administered or due (e.g. TT injection, BCG, OPV)")
    supplements_given: List[str] = Field(default_factory=list, description="Supplements provided (e.g. IFA goli/tablets, Calcium)")
    next_visit_date: Optional[str] = Field(None, description="Next scheduled visit date or interval (e.g. 25 November)")
    danger_signs_flagged: List[str] = Field(default_factory=list, description="List of MoHFW danger signs detected")
    is_urgent_referral: bool = Field(False, description="True if maternal/newborn danger signs mandate immediate PHC referral")
    raw_transcript: str = Field("", description="Raw spoken notes transcribed by STT")
    language: str = Field("kn-IN", description="Language of interaction (kn-IN, hi-IN, te-IN, ta-IN)")
    is_confirmed: bool = Field(False, description="Whether the record was confirmed by voice")
    ai_disclosure_given: bool = Field(False, description="Whether AI identity announcement has been made for this entry")

class ExtractionResult(BaseModel):
    record: VisitRecord
    spoken_response: str = Field(..., description="Conversational text to be spoken by Gnani Timbre TTS")
    status: Literal["READBACK_PENDING", "CONFIRMED", "CORRECTION_APPLIED", "ESCALATED"]
    danger_detected: bool = False
    danger_alerts: List[DangerSignAlert] = Field(default_factory=list)

class SessionEvent(BaseModel):
    event: str
    data: Optional[dict] = None
