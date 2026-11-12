"""
Voice Pipeline Orchestrator
Coordinates full duplex WebSocket streaming:
Browser Mic -> AudioWorklet (16kHz PCM) -> Gnani Prisma STT
-> MoHFW Danger Sign Guardrails -> Groq Llama-3.3 Extraction
-> Gnani Timbre TTS -> Browser Speaker Playback
"""
import asyncio
import json
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect

from app.models.visit_record import VisitRecord, ExtractionResult
from app.services.gnani_stt import GnaniSTTClient
from app.services.gnani_tts import GnaniTTSClient
from app.services.llm_service import llm_service
from app.services.database import save_record
from app.core.audio_stream import AudioStreamHandler
from app.config import DEFAULT_LANGUAGE, DEFAULT_VOICE

logger = logging.getLogger("orchestrator")

class SessionOrchestrator:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.language = DEFAULT_LANGUAGE
        self.voice = DEFAULT_VOICE

        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.audio_handler = AudioStreamHandler()

        self.current_record = VisitRecord(language=self.language)
        self.agent_speaking = False
        self.active_tts_task: Optional[asyncio.Task] = None
        self._is_active = True

        self.stt_client = GnaniSTTClient(language_code=self.language)
        self.tts_client = GnaniTTSClient(voice=self.voice, language=self.language)

    async def start(self):
        """Starts concurrent WebSocket listener and STT streaming worker."""
        stt_task = asyncio.create_task(
            self.stt_client.stream_audio_session(
                self.audio_queue,
                self._handle_transcript
            )
        )
        receiver_task = asyncio.create_task(self._receive_from_client())

        try:
            done, pending = await asyncio.wait(
                [receiver_task, stt_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
        finally:
            self._is_active = False
            self.stt_client.stop()
            if self.active_tts_task and not self.active_tts_task.done():
                self.active_tts_task.cancel()

    async def _receive_from_client(self):
        """Listens for raw PCM audio chunks or JSON control messages from frontend."""
        try:
            while self._is_active:
                message = await self.ws.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                # 1. Binary message = Raw 16kHz PCM audio chunk from microphone
                if "bytes" in message and message["bytes"]:
                    pcm_chunk = message["bytes"]

                    # Check for acoustic barge-in
                    analysis = self.audio_handler.process_chunk(pcm_chunk)
                    if analysis["speech_detected"] and self.agent_speaking:
                        await self._trigger_barge_in()

                    # Push to STT stream queue
                    await self.audio_queue.put(pcm_chunk)

                # 2. Text message = JSON control event
                elif "text" in message and message["text"]:
                    data = json.loads(message["text"])
                    event_type = data.get("event")

                    if event_type == "set_language":
                        new_lang = data.get("language", DEFAULT_LANGUAGE)
                        self.language = new_lang
                        self.stt_client.language_code = new_lang
                        self.tts_client.language = new_lang
                        self.current_record.language = new_lang
                        logger.info(f"Switched session language to {new_lang}")
                        await self._send_json({"event": "language_changed", "language": new_lang})

                    elif event_type == "barge_in":
                        await self._trigger_barge_in()

                    elif event_type == "text_note":
                        # Support direct text dictation / testing fallback
                        text = data.get("text", "")
                        if text:
                            await self._process_text_utterance(text)

                    elif event_type == "clear_record":
                        self.current_record = VisitRecord(language=self.language)
                        await self._send_json({
                            "event": "state_update",
                            "record": self.current_record.model_dump(),
                            "status": "RESET"
                        })

                    elif event_type == "confirm_record":
                        self.current_record.is_confirmed = True
                        saved = await save_record(self.current_record)
                        await self._send_json({
                            "event": "record_saved",
                            "record": saved.model_dump()
                        })

        except WebSocketDisconnect:
            logger.info("Client WebSocket disconnected.")
        except RuntimeError as e:
            if "disconnect" in str(e).lower():
                pass
            else:
                logger.error(f"Runtime error in client receiver: {e}")
        except Exception as e:
            logger.error(f"Error in client receiver: {e}")
        finally:
            self._is_active = False

    async def _handle_transcript(self, text: str, is_final: bool):
        """Callback invoked by Gnani STT client when transcript tokens arrive."""
        await self._send_json({
            "event": "transcript",
            "text": text,
            "is_final": is_final
        })

        if is_final and text.strip():
            # Process the finalized utterance through LLM & Guardrails
            await self._process_text_utterance(text)

    async def _process_text_utterance(self, text: str):
        """Runs LLM extraction, checks MoHFW danger signs, and speaks response."""
        result: ExtractionResult = await llm_service.process_utterance(
            spoken_text=text,
            current_record=self.current_record,
            language=self.language
        )
        self.current_record = result.record

        # 1. Emit state update to frontend
        await self._send_json({
            "event": "state_update",
            "record": self.current_record.model_dump(),
            "status": result.status
        })

        # 2. Emit danger alert if flagged
        if result.danger_detected:
            await self._send_json({
                "event": "danger_alert",
                "alert": result.spoken_response,
                "signs": [alert.model_dump() for alert in result.danger_alerts]
            })

        # 3. If confirmed, save to SQLite database
        if self.current_record.is_confirmed:
            saved = await save_record(self.current_record)
            await self._send_json({
                "event": "record_saved",
                "record": saved.model_dump()
            })

        # 4. Trigger TTS Voice Read-back to Client
        if result.spoken_response:
            if self.active_tts_task and not self.active_tts_task.done():
                self.active_tts_task.cancel()
            self.active_tts_task = asyncio.create_task(
                self._speak_text(result.spoken_response)
            )

    async def _speak_text(self, text: str):
        """Synthesizes text via Gnani Timbre and streams audio to client."""
        self.agent_speaking = True
        await self._send_json({
            "event": "agent_speech_start",
            "text": text
        })

        async def send_audio_chunk(chunk_bytes: bytes, is_final: bool):
            if chunk_bytes and len(chunk_bytes) > 0 and self.agent_speaking:
                try:
                    await self.ws.send_bytes(chunk_bytes)
                except Exception as e:
                    logger.error(f"Error sending audio chunk to client: {e}")

        try:
            await self.tts_client.synthesize_stream(
                text=text,
                on_audio_chunk=send_audio_chunk,
                voice=self.voice,
                language=self.language
            )
        except asyncio.CancelledError:
            logger.info("TTS playback cancelled due to barge-in.")
        finally:
            self.agent_speaking = False
            await self._send_json({"event": "agent_speech_end"})

    async def _trigger_barge_in(self):
        """Interrupts current agent speech immediately when user begins speaking."""
        if self.agent_speaking:
            logger.info("Barge-in triggered! Stopping agent speech.")
            self.agent_speaking = False
            if self.active_tts_task and not self.active_tts_task.done():
                self.active_tts_task.cancel()
            await self._send_json({"event": "barge_in_detected"})

    async def _send_json(self, payload: dict):
        """Safely sends JSON message to client WebSocket."""
        try:
            await self.ws.send_text(json.dumps(payload))
        except Exception:
            pass
