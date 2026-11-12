"""
Gnani Prisma v3.0 STT Client
Connects via WebSocket to Gnani STT streaming endpoint.
Handles Indic language + English code-mixed speech recognition.
"""

class GnaniSTTClient:
    def __init__(self, api_key: str, ws_url: str):
        self.api_key = api_key
        self.ws_url = ws_url

    async def connect_and_stream(self, audio_generator, on_transcript_callback):
        """Streams raw audio chunks to Gnani and invokes callback on transcript tokens."""
        pass
