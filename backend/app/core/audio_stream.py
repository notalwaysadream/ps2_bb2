"""
Audio Streaming Utilities: Framing, Energy VAD, and Barge-in Detection
Optimized for 16kHz, 16-bit linear PCM audio.
"""
import math
import struct
import time
from typing import Optional

class AudioStreamHandler:
    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold: float = 500.0,
        silence_timeout_sec: float = 1.3
    ):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_timeout_sec = silence_timeout_sec

        self.is_speaking = False
        self.last_speech_time: Optional[float] = None
        self.speech_start_time: Optional[float] = None

    def calculate_rms(self, pcm_chunk: bytes) -> float:
        """Calculates Root Mean Square (RMS) energy of 16-bit PCM chunk."""
        if len(pcm_chunk) < 2:
            return 0.0
        # Number of 16-bit samples
        num_samples = len(pcm_chunk) // 2
        try:
            samples = struct.unpack(f"<{num_samples}h", pcm_chunk[:num_samples * 2])
            sum_squares = sum(s * s for s in samples)
            return math.sqrt(sum_squares / num_samples)
        except Exception:
            return 0.0

    def process_chunk(self, pcm_chunk: bytes) -> dict:
        """
        Analyzes audio chunk for speech presence, endpointing, and barge-in.
        Returns dict with keys:
          - rms: float
          - speech_detected: bool
          - utterance_completed: bool (silence after speech)
        """
        rms = self.calculate_rms(pcm_chunk)
        now = time.time()
        speech_detected = rms > self.energy_threshold
        utterance_completed = False

        if speech_detected:
            if not self.is_speaking:
                self.is_speaking = True
                self.speech_start_time = now
            self.last_speech_time = now
        elif self.is_speaking and self.last_speech_time:
            # Check if silence timeout has passed
            if (now - self.last_speech_time) >= self.silence_timeout_sec:
                self.is_speaking = False
                utterance_completed = True
                self.last_speech_time = None
                self.speech_start_time = None

        return {
            "rms": rms,
            "speech_detected": speech_detected,
            "utterance_completed": utterance_completed
        }

    def reset(self):
        self.is_speaking = False
        self.last_speech_time = None
        self.speech_start_time = None
