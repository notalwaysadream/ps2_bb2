"""
Gnani Prisma v3.0 Streaming Speech-to-Text (STT) Client
Connects via WebSocket to Gnani STT streaming endpoint.
Transcribes Indic speech with English code-mix (Hinglish/Kanglish)
and optimizes recognition with keyterms word-boosting for healthcare jargon.
"""
import asyncio
import json
import logging
import websockets
from typing import Callable, Coroutine, Optional, List
from app.config import (
    GNANI_API_KEY,
    GNANI_STT_WS_URL,
    DEFAULT_LANGUAGE,
    is_simulation_mode,
    is_valid_key,
    get_ws_connect_kwargs
)

logger = logging.getLogger("gnani_stt")

# Context boosting for health terms per Hackathon PS1
DEFAULT_HEALTH_KEYTERMS = [
    "TT injection",
    "ANC checkup",
    "IFA goli",
    "IFA tablet",
    "PNC checkup",
    "BCG vaccine",
    "OPV drops",
    "Pentavalent",
    "Rotavirus",
    "Measles",
    "Vitamin A",
    "ORS",
    "Zinc",
    "kilo",
    "beneficiary",
    "haemoglobin",
    "malnutrition",
    "bleeding",
    "tez bukhar",
    "doodh nahi pi raha",
    "pasli chalna"
]

class GnaniSTTClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        ws_url: Optional[str] = None,
        language_code: Optional[str] = None,
        keyterms: Optional[List[str]] = None
    ):
        self.api_key = api_key or GNANI_API_KEY
        self.ws_url = ws_url or GNANI_STT_WS_URL
        self.language_code = language_code or DEFAULT_LANGUAGE
        self.keyterms = keyterms or DEFAULT_HEALTH_KEYTERMS
        self._is_running = False

    def get_connection_headers(self) -> dict:
        """Constructs Gnani Prisma v3.0 WebSocket upgrade headers."""
        headers = {
            "x-api-key-id": self.api_key,
            "language_code": self.language_code,
            "model": "prisma-v3.0",
            "format": "transcribe"
        }
        if self.keyterms:
            headers["keyterms"] = json.dumps(self.keyterms)
        return headers

    async def stream_audio_session(
        self,
        audio_queue: asyncio.Queue,
        on_transcript: Callable
    ):
        """
        Main loop:
        Pulls raw 16-bit PCM chunks from audio_queue and streams to Gnani Prisma STT.
        Concurrently reads transcripts from Gnani and invokes on_transcript(text, is_final, detected_lang).
        Automatically reconnects if the remote socket drops during the session.
        """
        self._is_running = True

        if is_simulation_mode() or not is_valid_key(self.api_key):
            logger.info("Gnani STT running in SIMULATION mode.")
            await self._run_simulation_loop(audio_queue, on_transcript)
            return

        consecutive_failures = 0
        try:
            while self._is_running:
                headers = self.get_connection_headers()
                connect_kwargs = get_ws_connect_kwargs(headers)
                logger.info(f"Connecting to Gnani Prisma STT at {self.ws_url} with language={self.language_code}")

                try:
                    async with websockets.connect(self.ws_url, **connect_kwargs) as ws:
                        logger.info("Successfully connected to Gnani Prisma v3.0 STT WebSocket.")
                        consecutive_failures = 0

                        async def sender():
                            """Sends incoming PCM audio chunks to Gnani."""
                            try:
                                while self._is_running:
                                    chunk = await audio_queue.get()
                                    if chunk is None:  # Sentinel to close
                                        break
                                    if isinstance(chunk, bytes) and len(chunk) > 0:
                                        await ws.send(chunk)
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                logger.error(f"Error sending audio to Gnani STT: {e}")

                        async def receiver():
                            """Receives transcript JSON from Gnani STT."""
                            try:
                                while self._is_running:
                                    message = await ws.recv()
                                    if isinstance(message, str):
                                        data = json.loads(message)
                                        msg_type = data.get("type")
                                        if msg_type == "error":
                                            logger.error(f"Gnani STT returned error: {data.get('message')}")
                                        text = data.get("text", "").strip()
                                        is_final = data.get("is_final", False)
                                        detected_lang = data.get("detected_language_code")
                                        if text:
                                            logger.info(f"STT Transcript: '{text}' (is_final={is_final}, detected_lang={detected_lang})")
                                            try:
                                                # Accept on_transcript with 3 or 2 arguments
                                                await on_transcript(text, is_final, detected_lang)
                                            except TypeError:
                                                await on_transcript(text, is_final)
                            except asyncio.CancelledError:
                                pass
                            except websockets.exceptions.ConnectionClosed as cc:
                                logger.info(f"Gnani STT WebSocket connection closed by remote: {cc}")
                            except Exception as e:
                                logger.error(f"Error receiving from Gnani STT: {e}")

                        sender_task = asyncio.create_task(sender())
                        receiver_task = asyncio.create_task(receiver())

                        done, pending = await asyncio.wait(
                            [sender_task, receiver_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in pending:
                            task.cancel()

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"Gnani STT WebSocket error (failure {consecutive_failures}): {e}")
                    if consecutive_failures >= 3:
                        logger.warning("Multiple Gnani STT connection failures; falling back to simulation loop.")
                        await self._run_simulation_loop(audio_queue, on_transcript)
                        break
                    await asyncio.sleep(1.0)
        finally:
            self._is_running = False

    async def _run_simulation_loop(
        self,
        audio_queue: asyncio.Queue,
        on_transcript: Callable[[str, bool], Coroutine]
    ):
        """Simulation fallback loop when testing without live API keys."""
        try:
            while self._is_running:
                item = await audio_queue.get()
                if item is None:
                    break
                # If a mock text command or string is delivered through the queue
                if isinstance(item, str):
                    await on_transcript(item, True)
                elif isinstance(item, bytes):
                    # Drain audio bytes without crashing
                    pass
        except asyncio.CancelledError:
            pass

    def stop(self):
        self._is_running = False
