"""
Gnani Timbre v3.0 Streaming Text-to-Speech (TTS) Client
Connects via WebSocket to Gnani TTS streaming endpoint.
Synthesizes Indic speech with expressive audio delivery across
Hindi, Kannada, Telugu, and Tamil.
"""
import asyncio
import base64
import json
import logging
import websockets
from typing import Callable, Coroutine, Optional
from app.config import (
    GNANI_API_KEY,
    GNANI_TTS_WS_URL,
    DEFAULT_VOICE,
    DEFAULT_LANGUAGE,
    is_simulation_mode,
    is_valid_key,
    get_ws_connect_kwargs
)

logger = logging.getLogger("gnani_tts")

class GnaniTTSClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        ws_url: Optional[str] = None,
        voice: Optional[str] = None,
        language: Optional[str] = None
    ):
        self.api_key = api_key or GNANI_API_KEY
        self.ws_url = ws_url or GNANI_TTS_WS_URL
        self.voice = voice or DEFAULT_VOICE
        self.language = language or DEFAULT_LANGUAGE

    def get_connection_headers(self) -> dict:
        """Constructs Gnani Timbre upgrade headers."""
        return {
            "X-API-Key-ID": self.api_key
        }

    async def synthesize_stream(
        self,
        text: str,
        on_audio_chunk: Callable[[bytes, bool], Coroutine],
        voice: Optional[str] = None,
        language: Optional[str] = None
    ):
        """
        Synthesizes text into streaming audio chunks via Timbre WebSocket.
        Invokes on_audio_chunk(audio_bytes, is_final) for each incoming chunk.
        """
        if not text or not text.strip():
            return

        active_voice = voice or self.voice
        active_lang = language or self.language
        if active_lang in ("indic-auto", "", None):
            active_lang = "hi-IN"

        if is_simulation_mode() or not is_valid_key(self.api_key):
            logger.info(f"Gnani TTS in SIMULATION mode: Synthesizing '{text[:40]}...'")
            silence_chunk = b"\x00" * 3200
            await on_audio_chunk(silence_chunk, True)
            return

        headers = self.get_connection_headers()
        connect_kwargs = get_ws_connect_kwargs(headers)
        payload = {
            "text": text,
            "voice": active_voice,
            "model": "timbre-v3.0",
            "language": active_lang,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": 16000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "raw"
            }
        }

        logger.info(f"Sending synthesis request to Timbre TTS ({active_lang}, voice={active_voice}): '{text[:40]}...'")

        try:
            async with websockets.connect(self.ws_url, **connect_kwargs) as ws:
                await ws.send(json.dumps(payload))

                while True:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for audio from Gnani TTS.")
                        await on_audio_chunk(b"", True)
                        break
                    if isinstance(message, str):
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "audio":
                            audio_payload = data.get("data", {})
                            audio_b64 = audio_payload.get("audio", "") if isinstance(audio_payload, dict) else data.get("audio", "")
                            if audio_b64:
                                audio_bytes = base64.b64decode(audio_b64)
                                await on_audio_chunk(audio_bytes, False)

                        elif msg_type in ("complete", "end"):
                            await on_audio_chunk(b"", True)
                            break

                        elif data.get("is_final"):
                            await on_audio_chunk(b"", True)
                            break
                    elif isinstance(message, bytes):
                        # Some versions stream binary audio directly
                        await on_audio_chunk(message, False)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Gnani TTS connection closed normally.")
        except Exception as e:
            logger.error(f"Error during Gnani Timbre TTS streaming: {e}")
            # Fallback to empty chunk to not block client
            await on_audio_chunk(b"", True)
