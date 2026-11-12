"""
Pipeline Orchestrator
Coordinates the flow:
Incoming Mic Audio -> Gnani Prisma STT (WebSocket)
-> LLM (Structured extraction / Guardrail check / Voice readback generator)
-> Gnani Timbre TTS (WebSocket) -> Client Audio Playback
"""

class PipelineOrchestrator:
    def __init__(self):
        pass

    async def process_session(self, client_ws):
        """Manages the full duplex voice session with the client."""
        pass
