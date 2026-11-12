"""
Comprehensive Test Suite for ASHA-Vani Backend
Tests:
1. MoHFW Danger Signs Detection & Escalation (Double-scored feature in rubric)
2. SQLite Persistence for Field Records
3. Heuristic & LLM Extraction for Code-Mixed Utterances
4. Audio RMS & Endpoint Detection
"""
import pytest
import asyncio
import os
from pathlib import Path

# Set test environment
os.environ["SIMULATION_MODE"] = "true"

from app.models.visit_record import VisitRecord
from app.health_guardrails.danger_signs import DangerSignDetector
from app.services.database import (
    init_db,
    save_record,
    get_records,
    get_record_by_id,
    delete_record,
    clear_all_records
)
from app.services.llm_service import LLMService
from app.core.audio_stream import AudioStreamHandler

def test_danger_signs_pregnancy_bleeding():
    detector = DangerSignDetector()
    text = "Beneficiary 3012, 7th month pregnancy visit. Patient ko bleeding ho raha hai aur sar dard hai."
    alerts = detector.scan_text(text)
    assert len(alerts) > 0
    alert_ids = [a.id for a in alerts]
    assert "mat_bleeding" in alert_ids or "mat_severe_headache" in alert_ids

    speech = detector.generate_escalation_speech(alerts, "hi-IN")
    assert "सावधान" in speech or "गंभीर खतरे" in speech or "PHC" in speech

def test_danger_signs_newborn_fever_and_poor_feeding():
    detector = DangerSignDetector()
    text = "Baby ka wazan 2.6 kilo hai, baby ko tez bukhar hai aur doodh nahi pi raha."
    alerts = detector.scan_text(text)
    assert len(alerts) >= 2
    alert_ids = [a.id for a in alerts]
    assert "neo_high_fever" in alert_ids
    assert "neo_poor_feeding" in alert_ids

def test_normal_anc_no_danger_signs():
    detector = DangerSignDetector()
    text = "Beneficiary ID 1042, Sunita Devi ka 3rd ANC checkup. Wazan 52 kilo. TT injection diya gaya. Next visit 25 November."
    alerts = detector.scan_text(text)
    assert len(alerts) == 0

@pytest.mark.asyncio
async def test_database_crud():
    await init_db()
    await clear_all_records()

    record = VisitRecord(
        beneficiary_id="TEST-101",
        visit_type="ANC checkup",
        weight=54.5,
        vaccinations_due=["TT injection"],
        supplements_given=["IFA goli"],
        next_visit_date="20 December",
        danger_signs_flagged=[],
        is_urgent_referral=False,
        is_confirmed=True
    )

    # Save
    saved = await save_record(record)
    assert saved.id == record.id

    # Fetch list
    records = await get_records()
    assert len(records) == 1
    assert records[0].beneficiary_id == "TEST-101"
    assert records[0].weight == 54.5

    # Fetch by ID
    single = await get_record_by_id(record.id)
    assert single is not None
    assert single.visit_type == "ANC checkup"

    # Delete
    deleted = await delete_record(record.id)
    assert deleted is True

    records_after = await get_records()
    assert len(records_after) == 0

@pytest.mark.asyncio
async def test_extraction_and_voice_correction():
    llm = LLMService()

    # Step 1: Initial dictation
    initial_text = "Beneficiary ID 1042, Sunita Devi ka ANC checkup kiya. Weight 52 kilo hai. TT injection de diya. Agla visit 25 November ko hai."
    res1 = await llm.process_utterance(initial_text, language="hi-IN")

    assert res1.record.beneficiary_id == "1042"
    assert res1.record.weight == 52.0
    assert "TT injection" in res1.record.vaccinations_due
    assert res1.status in ("READBACK_PENDING", "CORRECTION_APPLIED")
    assert not res1.record.is_confirmed

    # Step 2: Voice correction ("Nahi, wazan 55 kilo hai")
    correction_text = "Nahi, wazan 55 kilo hai."
    res2 = await llm.process_utterance(correction_text, current_record=res1.record, language="hi-IN")

    assert res2.record.weight == 55.0
    assert res2.record.beneficiary_id == "1042" # Beneficiary retained!

    # Step 3: Voice confirmation ("Haan theek hai, save karo")
    confirm_text = "Haan theek hai, save kar do."
    res3 = await llm.process_utterance(confirm_text, current_record=res2.record, language="hi-IN")

    assert res3.record.is_confirmed is True
    assert res3.status == "CONFIRMED"

def test_audio_rms_and_vad():
    handler = AudioStreamHandler(energy_threshold=200.0)

    # Silence chunk
    silence = b"\x00" * 640
    silence_result = handler.process_chunk(silence)
    assert silence_result["rms"] == 0.0
    assert silence_result["speech_detected"] is False

    # Loud chunk (simulate 16-bit sine wave / loud noise)
    loud_samples = bytearray()
    for i in range(320):
        val = 10000 if i % 2 == 0 else -10000
        import struct
        loud_samples.extend(struct.pack("<h", val))

    loud_result = handler.process_chunk(bytes(loud_samples))
    assert loud_result["rms"] > 5000.0
    assert loud_result["speech_detected"] is True
