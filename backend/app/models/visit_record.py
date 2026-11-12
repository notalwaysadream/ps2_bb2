"""
Structured ASHA Visit Record Model
Matches Hackathon requirements:
- beneficiary_id
- visit_type (ANC, PNC, Immunisation, Newborn)
- weight (kg)
- vaccinations_due
- next_visit_date
- danger_signs_detected (flagged for PHC referral)
- notes_raw
- confirmed_by_voice
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class VisitRecord(BaseModel):
    beneficiary_id: Optional[str] = Field(None, description="ID or synthetic name of beneficiary")
    visit_type: Optional[str] = Field(None, description="ANC checkup, PNC, Newborn care, or Immunisation")
    weight: Optional[float] = Field(None, description="Weight in kg (e.g. 2.8)")
    vaccinations_due: List[str] = Field(default_factory=list, description="e.g. ['TT injection', 'BCG', 'OPV']")
    supplements_given: List[str] = Field(default_factory=list, description="e.g. ['IFA goli / tablets']")
    danger_signs_flagged: List[str] = Field(default_factory=list, description="Triggered danger signs")
    is_urgent_referral: bool = False
    next_visit_date: Optional[str] = Field(None, description="Next scheduled visit date or interval")
    raw_transcript: str = ""
    is_confirmed: bool = False
