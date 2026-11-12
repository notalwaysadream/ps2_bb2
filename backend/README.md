# Backend - ASHA Voice Field Register

Owner: Backend Lead

## Responsibilities
- Gnani Prisma v3.0 Streaming STT integration (WebSocket)
- Gnani Timbre v3.0 Streaming TTS integration (WebSocket)
- LLM prompt engineering for structured health record extraction & conversational confirmation
- Danger sign escalation engine (detects MoHFW maternal/newborn danger signs & flags records)
- Audio streaming WebSocket pipeline with low latency and barge-in support

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # Add your keys
uvicorn app.main:app --reload --port 8000
```
