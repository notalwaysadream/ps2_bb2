import os
from dotenv import load_dotenv

load_dotenv()

GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_STT_WS_URL = os.getenv("GNANI_STT_WS_URL", "wss://api.gnani.ai/v1/stt/stream")
GNANI_TTS_WS_URL = os.getenv("GNANI_TTS_WS_URL", "wss://api.gnani.ai/v1/tts/stream")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
