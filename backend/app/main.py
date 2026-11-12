"""
FastAPI Application Entry Point
Exposes WebSocket endpoints for real-time streaming audio and REST endpoints
for visit records persistence, health checks, and MoHFW guidelines.
"""
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, WebSocket, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.services.database import (
    init_db,
    save_record,
    get_records,
    get_record_by_id,
    delete_record,
    clear_all_records
)
from app.models.visit_record import VisitRecord
from app.core.orchestrator import SessionOrchestrator
from app.health_guardrails.danger_signs import detector
from app.config import is_simulation_mode, DEFAULT_LANGUAGE, DEFAULT_VOICE

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite schema
    await init_db()
    yield

app = FastAPI(
    title="ASHA-Vani Voice Field Register API",
    description="Low-latency voice processing pipeline for ASHA field notes using Gnani Prisma & Timbre",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint displaying engine and simulation status."""
    return {
        "status": "healthy",
        "service": "asha-vani-backend",
        "simulation_mode": is_simulation_mode(),
        "default_language": DEFAULT_LANGUAGE,
        "default_voice": DEFAULT_VOICE,
        "guideline": "MoHFW / NHM ASHA Modules 6 & 7"
    }

@app.get("/records", response_model=List[VisitRecord])
async def list_records(limit: int = Query(50, ge=1, le=200)):
    """Fetches recently saved ASHA field visit records from SQLite."""
    return await get_records(limit=limit)

@app.get("/records/{record_id}", response_model=VisitRecord)
async def get_record(record_id: str):
    """Fetches a specific visit record by ID."""
    record = await get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Visit record not found")
    return record

@app.post("/records", response_model=VisitRecord)
async def create_or_update_record(record: VisitRecord):
    """Manually creates or updates a visit record."""
    return await save_record(record)

@app.delete("/records/{record_id}")
async def remove_record(record_id: str):
    """Deletes a visit record by ID."""
    success = await delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Visit record not found")
    return {"status": "deleted", "id": record_id}

@app.delete("/records")
async def clear_records():
    """Clears all records for a clean hackathon demo run."""
    await clear_all_records()
    return {"status": "all_records_cleared"}

@app.get("/danger-signs")
async def get_danger_signs_guidelines():
    """Returns MoHFW maternal and neonatal danger-sign definitions and citation."""
    return detector.rules

@app.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket):
    """
    Full duplex WebSocket connection for real-time voice streaming.
    Receives 16kHz PCM audio chunks -> Gnani STT -> Groq LLM -> Gnani TTS -> Audio Playback.
    """
    await websocket.accept()
    orchestrator = SessionOrchestrator(websocket)
    await orchestrator.start()
