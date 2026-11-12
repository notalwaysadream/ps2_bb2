import os
import inspect
from pathlib import Path
from dotenv import load_dotenv
import websockets

# Load .env from backend directory or project root
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

def is_valid_key(key: str) -> bool:
    """Returns True only if key is non-empty and not a placeholder."""
    if not key:
        return False
    val = key.strip().lower()
    if not val or val.startswith("your_") or "api_key_here" in val or val in ("none", "null", "placeholder"):
        return False
    return True

# Gnani Voice Platform
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "").strip()
GNANI_STT_WS_URL = os.getenv("GNANI_STT_WS_URL", "wss://api.vachana.ai/stt/v3/stream")
GNANI_TTS_WS_URL = os.getenv("GNANI_TTS_WS_URL", "wss://api.vachana.ai/api/v1/tts")

# LLM Configuration (Groq Llama 3.3 / 3.1)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# Default voice settings
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "Shivani")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "hi-IN")

# Database & Storage
DATA_DIR = backend_dir / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "records.db"))

# Server Host & Port
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Simulation mode (active when Gnani key is missing or placeholder)
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "auto").lower()
def is_simulation_mode() -> bool:
    if SIMULATION_MODE in ("true", "1", "yes"):
        return True
    if SIMULATION_MODE in ("false", "0", "no"):
        return False
    # Auto: simulate if GNANI_API_KEY is not a valid real key
    return not is_valid_key(GNANI_API_KEY)

def get_ws_connect_kwargs(headers: dict) -> dict:
    """Compatible connect headers for websockets library across versions."""
    sig = inspect.signature(websockets.connect)
    if "additional_headers" in sig.parameters:
        return {"additional_headers": headers}
    return {"extra_headers": headers}
