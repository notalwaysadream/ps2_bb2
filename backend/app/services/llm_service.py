"""
LLM Extraction & Conversational Agent Service
Extracts structured ASHA visit details (beneficiary ID, visit type, weight, vaccines, next visit date),
checks against danger signs, and generates natural confirmation/read-back responses.
"""

class LLMService:
    def __init__(self, provider: str = "groq"):
        self.provider = provider

    async def extract_and_generate_response(self, spoken_text: str, current_state: dict):
        """Processes worker speech, updates state, and streams conversational reply."""
        pass
