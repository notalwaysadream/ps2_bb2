"""
FastAPI Server Entry Point
Exposes WebSocket endpoints for real-time audio streaming from frontend
and REST endpoints for saved ASHA visit records.
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ASHA Voice Field Register API",
    description="Backend voice processing and structured register engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "asha-voice-register"}

@app.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint receiving audio chunks from frontend,
    piping to Gnani STT -> LLM -> Gnani TTS -> Client.
    """
    await websocket.accept()
    # Implementation pending
    await websocket.close()
