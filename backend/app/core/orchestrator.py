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
import re
import time
from typing import Optional, List
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
        self.user_selected_language = False

        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.audio_handler = AudioStreamHandler()

        self.current_record = VisitRecord(language=self.language)
        self.agent_speaking = False
        self.active_tts_task: Optional[asyncio.Task] = None
        self._is_active = True

        self.accumulated_utterances: List[str] = []
        self.current_partial_transcript: str = ""
        self.last_speech_time: float = 0.0
        self.silence_timer_task: Optional[asyncio.Task] = None
        self.silence_timeout_sec: float = 4.0  # Natural pause tolerance for full conversation dictation

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

        try:
            # Client receiver drives the lifecycle of the session
            await self._receive_from_client()
        finally:
            self._is_active = False
            if self.silence_timer_task and not self.silence_timer_task.done():
                self.silence_timer_task.cancel()
            self.stt_client.stop()
            stt_task.cancel()
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
                    if analysis["speech_detected"]:
                        if self.agent_speaking:
                            await self._trigger_barge_in()
                        # If active transcription has begun, extend speech time
                        if self.accumulated_utterances or self.current_partial_transcript:
                            self.last_speech_time = time.time()

                    # Push to STT stream queue
                    await self.audio_queue.put(pcm_chunk)

                # 2. Text message = JSON control event
                elif "text" in message and message["text"]:
                    data = json.loads(message["text"])
                    event_type = data.get("event")

                    if event_type == "set_language":
                        new_lang = data.get("language", DEFAULT_LANGUAGE)
                        self.language = new_lang
                        self.user_selected_language = (new_lang != "indic-auto")
                        self.stt_client.language_code = new_lang
                        self.tts_client.language = "kn-IN" if new_lang in ("indic-auto", "", None) else new_lang
                        self.current_record.language = self.tts_client.language
                        logger.info(f"Switched session language to {new_lang} (user_selected={self.user_selected_language})")
                        await self._send_json({"event": "language_changed", "language": new_lang})

                    elif event_type == "barge_in":
                        await self._trigger_barge_in()

                    elif event_type in ("stop_recording", "conclude_utterance"):
                        # User pressed mic button to conclude dictation
                        fallback_text = data.get("text", "")
                        logger.info(f"Received stop_recording event (fallback_text='{fallback_text}'); concluding turn immediately.")
                        await self._conclude_and_process(fallback_text=fallback_text)

                    elif event_type in ("text_note", "transcript"):
                        # Support direct text dictation / preset test notes
                        text = data.get("text", "").strip()
                        if text:
                            if self.silence_timer_task and not self.silence_timer_task.done():
                                self.silence_timer_task.cancel()
                                self.silence_timer_task = None
                            self.accumulated_utterances = []
                            self.current_partial_transcript = ""
                            await self._process_text_utterance(text)

                    elif event_type == "clear_record":
                        self.accumulated_utterances = []
                        self.current_partial_transcript = ""
                        if self.silence_timer_task and not self.silence_timer_task.done():
                            self.silence_timer_task.cancel()
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

    async def _handle_transcript(self, text: str, is_final: bool, detected_lang: Optional[str] = None):
        """Callback invoked by Gnani STT client when transcript tokens arrive."""
        clean_text = text.strip()
        if not clean_text:
            return

        now = time.time()
        self.last_speech_time = now

        if is_final:
            self.accumulated_utterances.append(clean_text)
            self.current_partial_transcript = ""
            logger.info(f"Buffered final transcript segment: '{clean_text}' (total segments: {len(self.accumulated_utterances)})")
        else:
            self.current_partial_transcript = clean_text

        # Display running accumulation of the whole conversation so far
        all_parts = list(self.accumulated_utterances)
        if self.current_partial_transcript and (not all_parts or all_parts[-1] != self.current_partial_transcript):
            all_parts.append(self.current_partial_transcript)
        display_text = " ".join(all_parts).strip()

        await self._send_json({
            "event": "transcript",
            "text": display_text,
            "is_final": is_final
        })

        # Ensure silence countdown timer is active
        if self.silence_timer_task is None or self.silence_timer_task.done():
            self.silence_timer_task = asyncio.create_task(self._wait_for_silence_and_conclude())

    async def _wait_for_silence_and_conclude(self):
        """Waits for natural silence timeout after speech, then concludes the full conversation."""
        try:
            while self._is_active:
                elapsed = time.time() - self.last_speech_time
                remaining = self.silence_timeout_sec - elapsed
                if remaining <= 0:
                    break
                await asyncio.sleep(max(0.1, remaining))

            logger.info(f"Silence timeout ({self.silence_timeout_sec}s) reached after speech. Concluding full conversation.")
            await self._conclude_and_process()
        except asyncio.CancelledError:
            pass
        finally:
            self.silence_timer_task = None

    async def _conclude_and_process(self, fallback_text: Optional[str] = None):
        """Processes accumulated conversational notes through LLM and triggers read-back."""
        current_task = asyncio.current_task()
        if self.silence_timer_task and self.silence_timer_task != current_task and not self.silence_timer_task.done():
            self.silence_timer_task.cancel()
            self.silence_timer_task = None

        parts = list(self.accumulated_utterances)
        if self.current_partial_transcript:
            if not parts or parts[-1] != self.current_partial_transcript:
                parts.append(self.current_partial_transcript)

        combined_note = " ".join(parts).strip()

        # If combined note is empty, try fallback_text passed from client
        if not combined_note and fallback_text and fallback_text.strip():
            combined_note = fallback_text.strip()

        # Reset buffers for next turn
        self.accumulated_utterances = []
        self.current_partial_transcript = ""

        if not combined_note:
            logger.info("Conclude requested but no speech transcript recorded.")
            await self._send_json({
                "event": "no_speech_detected",
                "message": "No speech detected. Please tap mic and speak."
            })
            return

        logger.info(f"Processing accumulated visit note ({len(combined_note)} chars): '{combined_note}'")
        await self._process_text_utterance(combined_note)

    def _detect_language(self, text: str) -> str:
        """Detects whether utterance is in Kannada or Hindi, defaulting to Kannada+English."""
        if any('\u0C80' <= c <= '\u0CFF' for c in text):
            return "kn-IN"
        if any('\u0900' <= c <= '\u097F' for c in text):
            return "hi-IN"
        kannada_keywords = {
            "kannada", "namaskara", "makkalu", "magu", "maguvige", "haalu", "thale", "tale",
            "novu", "madidini", "kodi", "kottidini", "agide", "ide", "illa", "jwara",
            "rakta", "kudiyalla", "kudiyuttilla", "thumba", "tumba", "avara", "avaru"
        }
        words = set(re.findall(r"\b\w+\b", text.lower()))
        if words.intersection(kannada_keywords):
            return "kn-IN"
        hindi_keywords = {
            "hindi", "namaste", "bachha", "doodh", "pi", "raha", "bukhar",
            "sar", "dard", "khoon", "diya", "kiya", "theek", "agla"
        }
        if words.intersection(hindi_keywords) and not words.intersection(kannada_keywords):
            return "hi-IN"
        return "kn-IN"

    async def _process_text_utterance(self, text: str, detected_lang: Optional[str] = None):
        """Runs LLM extraction, checks MoHFW danger signs, and speaks response in matching language."""
        try:
            if self.user_selected_language:
                # User explicitly selected a language; ALWAYS honour user choice!
                active_lang = self.language
            elif self.language == "indic-auto":
                active_lang = detected_lang or self._detect_language(text)
            else:
                active_lang = self.language or "kn-IN"

            self.language = active_lang
            self.tts_client.language = active_lang
            self.current_record.language = active_lang

            result: ExtractionResult = await llm_service.process_utterance(
                spoken_text=text,
                current_record=self.current_record,
                language=active_lang
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
        except Exception as e:
            logger.error(f"Error processing text utterance: {e}", exc_info=True)
            await self._send_json({
                "event": "state_update",
                "record": self.current_record.model_dump(),
                "status": "ERROR"
            })

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
