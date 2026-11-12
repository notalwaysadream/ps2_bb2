"""
LLM Service for Structured ASHA Visit Extraction & Conversational Turns
Powered by Groq (Llama-3.3-70B / Llama-3.1-8B) for ultra-low latency streaming.
Supports code-mixed Indic languages (Hindi, Kannada, Telugu, Tamil + English).
"""
import json
import logging
import re
from typing import Optional
from app.config import GROQ_API_KEY, GROQ_MODEL, LLM_PROVIDER, is_valid_key
from app.models.visit_record import VisitRecord, ExtractionResult
from app.health_guardrails.danger_signs import detector

logger = logging.getLogger("llm_service")

EXTRACTION_SYSTEM_PROMPT = """You are an AI assistant for an Indian ASHA (Accredited Social Health Activist) healthcare worker.
Your task is to extract structured home-visit records from the worker's spoken notes and generate a natural, concise spoken confirmation in the same code-mixed language (e.g. Hindi-English / Hinglish).

You MUST output ONLY valid JSON matching this schema:
{
  "beneficiary_id": "string or null (e.g. '1042' or 'Sunita Devi')",
  "visit_type": "string or null ('ANC checkup', 'PNC', 'Newborn', 'Immunisation')",
  "weight": "float or null (weight in kilograms, e.g. 2.8 or 52.0)",
  "vaccinations_due": ["list of strings, e.g. ['TT injection', 'BCG', 'OPV']"],
  "supplements_given": ["list of strings, e.g. ['IFA goli', 'Calcium']"],
  "next_visit_date": "string or null (e.g. '25 November')",
  "is_confirmation_affirmative": "boolean (true if the worker is confirming/saying yes/save/theek hai)",
  "is_correction": "boolean (true if the worker is correcting an earlier mistake, e.g. 'nahi weight 2.8 kilo hai')",
  "spoken_readback": "string (A polite, concise 1-2 sentence spoken summary for Timbre TTS in the same language. For example: 'Maine note kiya: Beneficiary 1042, ANC checkup, wazan 52 kilo, TT injection diya gaya. Kya yeh theek hai?')"
}

RULES:
1. Handle code-mix health terminology: 'TT injection', 'ANC checkup', 'IFA goli' (Iron Folic Acid), 'PNC', 'wazan/weight', 'kilo/kg'.
2. If previous record details are provided, merge updates intelligently (e.g. if worker corrects only weight, keep the other fields).
3. If the worker confirms ("haan theek hai", "yes save", "theek hai"), set is_confirmation_affirmative to true, and spoken_readback to "Record save ho gaya hai."
4. Do NOT include markdown code fences or any text outside the JSON object.
"""

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GROQ_API_KEY
        self.model = model or GROQ_MODEL
        self._groq_client = None
        if is_valid_key(self.api_key):
            try:
                from groq import AsyncGroq
                self._groq_client = AsyncGroq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")
        else:
            logger.info("Groq API key is placeholder or missing. Using heuristic extraction.")

    async def process_utterance(
        self,
        spoken_text: str,
        current_record: Optional[VisitRecord] = None,
        language: str = "hi-IN"
    ) -> ExtractionResult:
        """
        Processes worker spoken note:
        1. Checks for MoHFW danger signs (escalates immediately if found).
        2. Calls LLM (or regex fallback) to extract structured fields and conversational read-back.
        3. Updates and returns the record state.
        """
        record = current_record or VisitRecord(language=language)
        record.raw_transcript = (record.raw_transcript + " " + spoken_text).strip()
        record.language = language

        # 1. MoHFW Danger Sign Check (High Priority Guardrail)
        danger_alerts = detector.scan_text(record.raw_transcript)
        if danger_alerts:
            record.danger_signs_flagged = list(set(record.danger_signs_flagged + [a.name for a in danger_alerts]))
            record.is_urgent_referral = True
            escalation_speech = detector.generate_escalation_speech(danger_alerts, language)

            return ExtractionResult(
                record=record,
                spoken_response=escalation_speech,
                status="ESCALATED",
                danger_detected=True,
                danger_alerts=danger_alerts
            )

        # 2. LLM Extraction
        if self._groq_client:
            try:
                result = await self._call_groq_llm(spoken_text, record, language)
                return result
            except Exception as e:
                logger.error(f"Groq LLM extraction failed: {e}. Falling back to heuristic extractor.")

        # Fallback to local heuristic extractor
        return self._heuristic_extraction(spoken_text, record, language)

    async def _call_groq_llm(
        self,
        spoken_text: str,
        current_record: VisitRecord,
        language: str
    ) -> ExtractionResult:
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current Record State:\n{current_record.model_dump_json()}\n\n"
                    f"New Spoken Utterance:\n\"{spoken_text}\"\n"
                    f"Language: {language}"
                )
            }
        ]

        completion = await self._groq_client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500
        )

        response_content = completion.choices[0].message.content
        data = json.loads(response_content)

        # Update record fields if extracted
        if data.get("beneficiary_id"):
            current_record.beneficiary_id = str(data["beneficiary_id"])
        if data.get("visit_type"):
            current_record.visit_type = data["visit_type"]
        if data.get("weight") is not None:
            try:
                current_record.weight = float(data["weight"])
            except (ValueError, TypeError):
                pass
        if data.get("vaccinations_due"):
            current_record.vaccinations_due = list(set(current_record.vaccinations_due + data["vaccinations_due"]))
        if data.get("supplements_given"):
            current_record.supplements_given = list(set(current_record.supplements_given + data["supplements_given"]))
        if data.get("next_visit_date"):
            current_record.next_visit_date = data["next_visit_date"]

        is_affirmative = data.get("is_confirmation_affirmative", False)
        is_correction = data.get("is_correction", False)

        if is_affirmative:
            current_record.is_confirmed = True
            status = "CONFIRMED"
            spoken = data.get("spoken_readback") or "Record safalta-purvak save ho gaya hai."
        elif is_correction:
            status = "CORRECTION_APPLIED"
            spoken = data.get("spoken_readback") or "Maine update kar diya hai. Kya ab theek hai?"
        else:
            status = "READBACK_PENDING"
            spoken = data.get("spoken_readback") or self._generate_default_readback(current_record, language)

        return ExtractionResult(
            record=current_record,
            spoken_response=spoken,
            status=status,
            danger_detected=False
        )

    def _heuristic_extraction(
        self,
        text: str,
        record: VisitRecord,
        language: str
    ) -> ExtractionResult:
        """Deterministic heuristic extraction when offline or API key is absent."""
        lower = text.lower()

        # Check affirmation
        affirmative_words = ["theek hai", "haan", "yes", "save", "done", "sahi hai", "ok", "confirm"]
        if any(w in lower for w in affirmative_words) and not any(neg in lower for neg in ["nahi", "no", "galat", "change"]):
            record.is_confirmed = True
            return ExtractionResult(
                record=record,
                spoken_response="Record safalta-purvak save ho gaya hai.",
                status="CONFIRMED"
            )

        # Beneficiary ID
        ben_match = re.search(r"(?:beneficiary\s*(?:id)?|id)\s*([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if ben_match:
            record.beneficiary_id = ben_match.group(1)

        # Weight extraction (e.g. "52 kilo", "2.8 kg", "weight 3.1")
        weight_match = re.search(r"(?:weight|wazan)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:kilo|kg|kilogram)", text, re.IGNORECASE)
        if weight_match:
            record.weight = float(weight_match.group(1))

        # Visit Type
        if "anc" in lower:
            record.visit_type = "ANC checkup"
        elif "pnc" in lower:
            record.visit_type = "PNC checkup"
        elif "newborn" in lower or "baby" in lower or "navjaat" in lower:
            record.visit_type = "Newborn care"
        elif "immunisation" in lower or "tika" in lower:
            record.visit_type = "Immunisation"

        # Vaccines
        if "tt" in lower or "tetanus" in lower:
            if "TT injection" not in record.vaccinations_due:
                record.vaccinations_due.append("TT injection")
        if "bcg" in lower:
            if "BCG" not in record.vaccinations_due:
                record.vaccinations_due.append("BCG")
        if "opv" in lower or "polio" in lower:
            if "OPV drops" not in record.vaccinations_due:
                record.vaccinations_due.append("OPV drops")

        # Supplements
        if "ifa" in lower or "iron" in lower or "goli" in lower:
            if "IFA goli / tablets" not in record.supplements_given:
                record.supplements_given.append("IFA goli / tablets")

        # Next visit date
        date_match = re.search(r"(?:next visit|agla visit|visit)\s*(?:ko)?\s*([0-9]+\s+[a-zA-Z]+|[a-zA-Z]+\s+[0-9]+)", text, re.IGNORECASE)
        if date_match:
            record.next_visit_date = date_match.group(1)

        is_correction = any(neg in lower for neg in ["nahi", "no", "galat", "badlo", "change"])
        status = "CORRECTION_APPLIED" if is_correction else "READBACK_PENDING"
        spoken = self._generate_default_readback(record, language)

        return ExtractionResult(
            record=record,
            spoken_response=spoken,
            status=status
        )

    def _generate_default_readback(self, record: VisitRecord, language: str) -> str:
        parts = []
        if record.beneficiary_id:
            parts.append(f"Beneficiary ID {record.beneficiary_id}")
        if record.visit_type:
            parts.append(f"{record.visit_type}")
        if record.weight:
            parts.append(f"wazan {record.weight} kilo")
        if record.vaccinations_due:
            parts.append(f"{', '.join(record.vaccinations_due)}")
        if record.next_visit_date:
            parts.append(f"agla visit {record.next_visit_date}")

        summary = ", ".join(parts) if parts else "aapke notes"
        return f"Maine note kiya: {summary}. Kya yeh theek hai?"

# Global singleton
llm_service = LLMService()
