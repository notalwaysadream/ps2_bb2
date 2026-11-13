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
Your task is to extract structured home-visit records from the worker's spoken notes and generate a natural, concise spoken confirmation in the EXACT SAME language requested.

STRICT NAME & ID EXTRACTION RULES:
1. 'beneficiary_name': ALWAYS extract the mother's, child's, or patient's name into this field (e.g. 'Shantala', 'ಶಾಂತಲಾ', 'Shakuntala', 'Sunita Devi', 'Radha').
   - Workers frequently state names like: "name Shantala", "ಹೆಸರು ಶಾಂತಲಾ", "Shakuntala avara 3rd ANC", "Sunita Devi ka visit".
   - NEVER leave 'beneficiary_name' empty or null if a person's name was spoken.
2. 'beneficiary_id': Extract numeric or alphanumeric codes (e.g. '4408', '1042', 'B-12').
   - If both are spoken ("Beneficiary ID 4408, name Shantala"), put '4408' in beneficiary_id and 'Shantala' in beneficiary_name.
   - If only a name is given with no numeric ID ("Shakuntala avara visit"), put 'Shakuntala' in beneficiary_name and beneficiary_id as null.

STRICT LANGUAGE RULES - NEVER MIX LANGUAGES:
You MUST generate 'spoken_readback' strictly in the single requested language. DO NOT mix Hindi words into Kannada or English, and DO NOT mix Kannada words into Hindi.

1. If Language is 'kn-IN' (Kannada + English code-mix / Kanglish):
   - spoken_readback MUST be in pure Kannada + English.
   - NEVER use Hindi words (NEVER use 'Maine note kiya', 'wazan', 'kya yeh theek hai', 'aur', 'diya gaya').
   - Readback template format:
     "Naanu note maadiddene: Beneficiary {name} ({id}), {visit_type}, weight {weight} kg, {vaccines}, next visit {date}. Idu sariyagidiya?"
     (Or in Kannada script if the user spoke in Kannada script: "ನಾನು ನೋಟ್ ಮಾಡಿದ್ದೇನೆ: Beneficiary {name} ({id}), {visit_type}, ತೂಕ {weight} kg, {vaccines}, ಮುಂದಿನ ಭೇಟಿ {date}. ಇದು ಸರಿಯಾಗಿದೆಯೇ?")
   - If confirmed by worker ("houdu", "sari", "haudu", "save", "theek ide"):
     "Record save aagide."
   - If correcting mistake ("alla", "tappu", "illa", "change maadi"):
     "Naanu update maadiddene. Eega sariyagidiya?"

2. If Language is 'hi-IN' (Hindi + English code-mix / Hinglish):
   - spoken_readback MUST be in pure Hindi + English.
   - NEVER use Kannada words.
   - Readback template format:
     "Maine note kiya: Beneficiary {name} ({id}), {visit_type}, wazan {weight} kilo, {vaccines}, agla visit {date}. Kya yeh theek hai?"
   - If confirmed by worker ("haan", "theek hai", "sahi hai", "save"):
     "Record save ho gaya hai."
   - If correcting mistake ("nahi", "galat", "change"):
     "Maine update kar diya hai. Kya ab theek hai?"

3. If Language is 'en-IN' (English):
   - spoken_readback MUST be in English.
   - Readback template format:
     "I have noted: Beneficiary {name} ({id}), {visit_type}, weight {weight} kg, {vaccines}, next visit {date}. Is this correct?"
   - If confirmed: "Record has been saved successfully."
   - If correcting: "I have updated the record. Does this look correct?"

4. If Language is 'te-IN' (Telugu):
   - Readback format: "Nenu note chesanu: Beneficiary {name} ({id}), {visit_type}, weight {weight} kg, {vaccines}, next visit {date}. Idi sarigga unda?"
   - If confirmed: "Record save cheyabadindi."
   - If correcting: "Nenu update chesanu. Ippudu sarigga unda?"

5. If Language is 'ta-IN' (Tamil):
   - Readback format: "Naan note seythen: Beneficiary {name} ({id}), {visit_type}, weight {weight} kg, {vaccines}, next visit {date}. Ithu sariyaaga ullatha?"
   - If confirmed: "Record save seyyappattathu."
   - If correcting: "Naan update seythullen. Ippo sariyaaga irukka?"

You MUST output ONLY valid JSON matching this schema:
{
  "beneficiary_id": "string or null (numeric or alphanumeric ID code, e.g. '4408' or '1042')",
  "beneficiary_name": "string or null (person's name, e.g. 'Shantala', 'ಶಾಂತಲಾ', 'Shakuntala', 'Sunita Devi')",
  "visit_type": "string or null ('ANC checkup', 'PNC', 'Newborn care', 'Immunisation')",
  "weight": "float or null (weight in kilograms, e.g. 2.8 or 52.0)",
  "vaccinations_due": ["list of strings, e.g. ['TT injection', 'BCG', 'OPV']"],
  "supplements_given": ["list of strings, e.g. ['IFA goli', 'Calcium']"],
  "next_visit_date": "string or null (e.g. '25 November')",
  "is_confirmation_affirmative": "boolean (true if the worker confirms/agrees/saves)",
  "is_correction": "boolean (true if the worker is correcting an earlier detail)",
  "spoken_readback": "string (polite, concise summary in the exact requested language)"
}

Do NOT include markdown code fences or any text outside the JSON object.
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
        result = None
        if self._groq_client:
            try:
                result = await self._call_groq_llm(spoken_text, record, language)
            except Exception as e:
                logger.error(f"Groq LLM extraction failed: {e}. Falling back to heuristic extractor.")

        # Fallback to local heuristic extractor
        if not result:
            result = self._heuristic_extraction(spoken_text, record, language)

        # 3. AI identity disclosure before first readback for this data entry
        if not record.ai_disclosure_given and result.spoken_response and not result.danger_detected:
            ai_prefix = self._get_ai_disclosure(language, result.spoken_response)
            if not any(k in result.spoken_response.lower() for k in ["ai sahayak", "ai assistant", "ai ಸಹಾಯಕ"]):
                result.spoken_response = f"{ai_prefix} {result.spoken_response}".strip()
            record.ai_disclosure_given = True
            result.record = record

        return result

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

        models_to_try = [self.model]
        if "qwen/qwen3.8-27b" not in models_to_try:
            models_to_try.append("qwen/qwen3.8-27b")

        data = None
        last_error = None
        for m in models_to_try:
            try:
                completion = await self._groq_client.chat.completions.create(
                    model=m,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=1000
                )
                response_content = completion.choices[0].message.content
                if response_content and response_content.strip():
                    data = json.loads(response_content)
                    break
            except Exception as e:
                last_error = e
                logger.warning(f"Groq model {m} failed: {e}. Trying fallback model...")

        if not data:
            raise last_error or RuntimeError("Groq extraction failed to produce valid JSON")

        # Update record fields if extracted
        if data.get("beneficiary_id"):
            current_record.beneficiary_id = str(data["beneficiary_id"]).strip()
        if data.get("beneficiary_name"):
            current_record.beneficiary_name = str(data["beneficiary_name"]).strip()
        # Fallback: if beneficiary_name is not set but beneficiary_id is a person's name
        if not current_record.beneficiary_name and current_record.beneficiary_id:
            if not any(c.isdigit() for c in current_record.beneficiary_id):
                current_record.beneficiary_name = current_record.beneficiary_id
                current_record.beneficiary_id = None
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
            spoken = data.get("spoken_readback") or self._get_confirmation_phrase(language)
        elif is_correction:
            status = "CORRECTION_APPLIED"
            spoken = data.get("spoken_readback") or self._get_correction_phrase(language)
        else:
            status = "READBACK_PENDING"
            spoken = data.get("spoken_readback") or self._generate_default_readback(current_record, language)

        return ExtractionResult(
            record=current_record,
            spoken_response=spoken,
            status=status,
            danger_detected=False
        )

    def _get_confirmation_phrase(self, language: str) -> str:
        lang_prefix = (language or "kn-IN").split("-")[0].lower()
        if lang_prefix == "kn":
            return "Record save aagide."
        elif lang_prefix == "hi":
            return "Record save ho gaya hai."
        elif lang_prefix == "te":
            return "Record save cheyabadindi."
        elif lang_prefix == "ta":
            return "Record save seyyappattathu."
        return "Record has been saved successfully."

    def _get_correction_phrase(self, language: str) -> str:
        lang_prefix = (language or "kn-IN").split("-")[0].lower()
        if lang_prefix == "kn":
            return "Naanu update maadiddene. Eega sariyagidiya?"
        elif lang_prefix == "hi":
            return "Maine update kar diya hai. Kya ab theek hai?"
        elif lang_prefix == "te":
            return "Nenu update chesanu. Ippudu sarigga unda?"
        elif lang_prefix == "ta":
            return "Naan update seythullen. Ippo sariyaaga irukka?"
        return "I have updated the record. Does this look correct?"

    def _heuristic_extraction(
        self,
        text: str,
        record: VisitRecord,
        language: str
    ) -> ExtractionResult:
        """Deterministic heuristic extraction when offline or API key is absent."""
        lower = text.lower()
        lang_prefix = (language or "kn-IN").split("-")[0].lower()

        # Check affirmation across Kannada, Hindi, and English
        affirmative_words = [
            "theek hai", "haan", "yes", "save", "done", "sahi hai", "ok", "confirm",
            "houdu", "haudu", "sari", "theek ide", "save maadi", "aayithu"
        ]
        negative_words = ["nahi", "no", "galat", "change", "alla", "illa", "tappu", "badalisi"]

        if any(w in lower for w in affirmative_words) and not any(neg in lower for neg in negative_words):
            record.is_confirmed = True
            return ExtractionResult(
                record=record,
                spoken_response=self._get_confirmation_phrase(language),
                status="CONFIRMED"
            )

        # Beneficiary Name
        name_match = re.search(r"(?:name|hesaru|naama|naam|smt|shrimati)\s*[:\.]?\s*([a-zA-Z\u0C80-\u0CFF\u0900-\u097F]+(?:\s+[a-zA-Z\u0C80-\u0CFF\u0900-\u097F]+)?)", text, re.IGNORECASE)
        if not name_match:
            name_match = re.search(r"([a-zA-Z\u0C80-\u0CFF\u0900-\u097F]{3,})\s+(?:avara|avaru|ka|ki)\b", text, re.IGNORECASE)
        if name_match:
            cand = name_match.group(1).strip()
            if cand.lower() not in {"visit", "checkup", "anc", "pnc", "weight", "id", "beneficiary", "vaccine", "baby"}:
                record.beneficiary_name = cand

        # Beneficiary ID
        ben_match = re.search(r"(?:beneficiary\s*(?:id)?|id)\s*([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if ben_match:
            cand_id = ben_match.group(1).strip()
            if any(c.isdigit() for c in cand_id):
                record.beneficiary_id = cand_id
            elif not record.beneficiary_name:
                record.beneficiary_name = cand_id

        # Weight extraction (e.g. "52 kilo", "2.8 kg", "weight 3.1", "thooka 52")
        weight_match = re.search(r"(?:weight|wazan|thooka|tooka)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:kilo|kg|kilogram)", text, re.IGNORECASE)
        if weight_match:
            record.weight = float(weight_match.group(1))

        # Visit Type
        if "anc" in lower:
            record.visit_type = "ANC checkup"
        elif "pnc" in lower:
            record.visit_type = "PNC checkup"
        elif "newborn" in lower or "baby" in lower or "navjaat" in lower or "magu" in lower:
            record.visit_type = "Newborn care"
        elif "immunisation" in lower or "tika" in lower or "lasike" in lower:
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
        if "ifa" in lower or "iron" in lower or "goli" in lower or "maathre" in lower:
            if "IFA goli / tablets" not in record.supplements_given:
                record.supplements_given.append("IFA goli / tablets")

        # Next visit date
        date_match = re.search(r"(?:next visit|agla visit|mundina visit|visit)\s*(?:ko|ide)?\s*([0-9]+\s+[a-zA-Z]+|[a-zA-Z]+\s+[0-9]+)", text, re.IGNORECASE)
        if date_match:
            record.next_visit_date = date_match.group(1)

        is_correction = any(neg in lower for neg in negative_words)
        status = "CORRECTION_APPLIED" if is_correction else "READBACK_PENDING"
        spoken = self._get_correction_phrase(language) if is_correction else self._generate_default_readback(record, language)

        return ExtractionResult(
            record=record,
            spoken_response=spoken,
            status=status
        )

    def _get_ai_disclosure(self, language: str, text_sample: str = "") -> str:
        """Returns concise 2-second AI identity disclosure line in the selected language."""
        lang_prefix = (language or "kn-IN").split("-")[0].lower()
        has_kannada_script = any('\u0C80' <= c <= '\u0CFF' for c in text_sample)
        has_devanagari = any('\u0900' <= c <= '\u097F' for c in text_sample)

        if lang_prefix == "kn":
            return "ನಾನು ಒಂದು AI ಸಹಾಯಕ." if has_kannada_script else "Naanu ondu AI sahayaka."
        elif lang_prefix == "hi":
            return "मैं एक AI सहायक हूँ।" if has_devanagari else "Main ek AI sahayak hoon."
        elif lang_prefix == "te":
            return "Nenu oka AI assistant ni."
        elif lang_prefix == "ta":
            return "Naan oru AI assistant."
        else:
            return "I am an AI assistant."

    def _generate_default_readback(self, record: VisitRecord, language: str) -> str:
        lang_prefix = (language or "kn-IN").split("-")[0].lower()
        parts = []

        name_str = f"{record.beneficiary_name}" if record.beneficiary_name else ""
        id_str = f"ID {record.beneficiary_id}" if record.beneficiary_id else ""
        if name_str and id_str:
            parts.append(f"Beneficiary {name_str} ({id_str})")
        elif name_str:
            parts.append(f"Beneficiary {name_str}")
        elif id_str:
            parts.append(f"Beneficiary {id_str}")

        if record.visit_type:
            parts.append(f"{record.visit_type}")
        if record.weight:
            if lang_prefix == "hi":
                parts.append(f"wazan {record.weight} kilo")
            elif lang_prefix == "kn":
                parts.append(f"weight {record.weight} kg")
            else:
                parts.append(f"weight {record.weight} kg")
        if record.vaccinations_due:
            parts.append(f"{', '.join(record.vaccinations_due)}")
        if record.supplements_given:
            parts.append(f"{', '.join(record.supplements_given)}")
        if record.next_visit_date:
            if lang_prefix == "kn":
                parts.append(f"next visit {record.next_visit_date}")
            elif lang_prefix == "hi":
                parts.append(f"agla visit {record.next_visit_date}")
            else:
                parts.append(f"next visit {record.next_visit_date}")

        summary = ", ".join(parts) if parts else ("visit vivara" if lang_prefix == "kn" else "visit notes")

        if lang_prefix == "kn":
            return f"Naanu note maadiddene: {summary}. Idu sariyagidiya?"
        elif lang_prefix == "hi":
            return f"Maine note kiya: {summary}. Kya yeh theek hai?"
        elif lang_prefix == "te":
            return f"Nenu note chesanu: {summary}. Idi sarigga unda?"
        elif lang_prefix == "ta":
            return f"Naan note seythen: {summary}. Ithu sariyaaga ullatha?"
        else:
            return f"I have noted: {summary}. Is this correct?"

# Global singleton
llm_service = LLMService()
