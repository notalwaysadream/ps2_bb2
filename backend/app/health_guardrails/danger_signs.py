"""
MoHFW Danger Signs Detector & Escalation Engine
Cites: Ministry of Health and Family Welfare (MoHFW) / National Health Mission (NHM)
ASHA Training Modules 6 & 7: Skills That Save Lives.

Enforces zero diagnostic hallucination:
- Detects danger symptoms from official guideline lists.
- Triggers immediate Primary Health Centre (PHC/FRU) referral advisory.
- Flags record with is_urgent_referral = True.
- Never suggests medications, diagnosis, or self-treatment.
"""
import re
import json
from pathlib import Path
from typing import List, Tuple
from app.models.visit_record import DangerSignAlert

GUIDELINE_FILE = Path(__file__).parent / "guideline_data.json"

class DangerSignDetector:
    def __init__(self, guideline_path: Path = GUIDELINE_FILE):
        self.guideline_path = guideline_path
        self.rules = self._load_guidelines()

    def _load_guidelines(self) -> dict:
        if not self.guideline_path.exists():
            return {"danger_signs": {"pregnancy_and_postpartum": [], "newborn_and_child": []}}
        with open(self.guideline_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def scan_text(self, text: str) -> List[DangerSignAlert]:
        """
        Scans transcribed text for maternal or neonatal danger signs.
        Uses normalized case-insensitive keyword and phrase matching.
        """
        if not text:
            return []

        normalized = text.lower()
        detected_alerts: List[DangerSignAlert] = []
        seen_ids = set()

        categories = [
            ("maternal", self.rules.get("danger_signs", {}).get("pregnancy_and_postpartum", [])),
            ("newborn", self.rules.get("danger_signs", {}).get("newborn_and_child", []))
        ]

        for category_name, rule_list in categories:
            for rule in rule_list:
                rule_id = rule.get("id")
                if rule_id in seen_ids:
                    continue

                keywords = rule.get("keywords", [])
                for kw in keywords:
                    pattern = r"\b" + re.escape(kw.lower()) + r"\b"
                    if re.search(pattern, normalized):
                        alert = DangerSignAlert(
                            id=rule_id,
                            name=rule.get("name"),
                            category=category_name,
                            action_required=rule.get("action", "Immediate referral to Primary Health Centre (PHC)")
                        )
                        detected_alerts.append(alert)
                        seen_ids.add(rule_id)
                        break

        return detected_alerts

    def generate_escalation_speech(self, alerts: List[DangerSignAlert], language: str = "hi-IN") -> str:
        """
        Generates spoken urgent referral message in the designated language.
        Strictly complies with MoHFW guidelines: referral only, no diagnosis.
        """
        if not alerts:
            return ""

        sign_names = ", ".join([a.name for a in alerts])
        lang_prefix = (language or "hi-IN").split("-")[0].lower()

        if lang_prefix == "hi":
            return (
                f"सावधान: मरीज में {sign_names} के लक्षण पाए गए हैं, जो MoHFW गाइडलाइंस के अनुसार गंभीर खतरे के संकेत हैं। "
                f"कृपया लाभार्थी को तुरंत नजदीकी प्राथमिक स्वास्थ्य केंद्र (PHC) ले जाएं! रिकॉर्ड को इमरजेंसी के साथ फ्लैग कर दिया गया है।"
            )
        elif lang_prefix == "kn":
            return (
                f"ಎಚ್ಚರಿಕೆ: ರೋಗಿಯಲ್ಲಿ {sign_names} ಲಕ್ಷಣಗಳು ಕಂಡುಬಂದಿವೆ. ಇದು MoHFW ಮಾರ್ಗಸೂಚಿಯ ಪ್ರಕಾರ ಗಂಭೀರ ಅಪಾಯದ ಲಕ್ಷಣವಾಗಿದೆ. "
                f"ದಯವಿಟ್ಟು ರೋಗಿಯನ್ನು ತಕ್ಷಣವೇ ಹತ್ತಿರದ ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರಕ್ಕೆ (PHC) ಕರೆದೊಯ್ಯಿರಿ! ದಾಖಲೆಯನ್ನು ತುರ್ತು ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ."
            )
        elif lang_prefix == "te":
            return (
                f"హెచ్చరిక: రోగిలో {sign_names} లక్షణాలు కనిపించాయి. ఇది MoHFW ప్రమాద సూచిక. "
                f"దయచేసి వెంటనే సమీప ప్రాథమిక ఆరోగ్య కేంద్రానికి (PHC) తరలించండి! రికార్డు అత్యవసరంగా గుర్తించబడింది."
            )
        elif lang_prefix == "ta":
            return (
                f"எச்சரிக்கை: {sign_names} என்பது MoHFW வழிகாட்டுதலின்படி ஆபத்தான அறிகுறியாகும். "
                f"உடனடியாக அருகிலுள்ள ஆரம்ப சுகாதார நிலையத்திற்கு (PHC) அழைத்துச் செல்லவும்! அவசரக் குறிப்பாகப் பதிவு செய்யப்பட்டுள்ளது."
            )
        else: # Default English code-mix
            return (
                f"Warning: Detected {sign_names}, which is a critical MoHFW danger sign. "
                f"Please refer the beneficiary to the nearest Primary Health Centre (PHC) immediately! The record is flagged for urgent referral."
            )

# Global singleton
detector = DangerSignDetector()
