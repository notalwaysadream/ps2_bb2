# Backend Setup and Guide

This folder contains the voice processing server, STT/TTS connections, and database for the ASHA Voice Register.

---

## Requirements
- Python 3.10+
- Virtual environment tool (`python3 -m venv`)

---

## Setup Steps

1. Create and activate a virtual environment:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate       # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Setup environment variables:
   ```bash
   cp .env.example .env            # On Windows: copy .env.example .env
   ```
   Add your Gnani and Groq keys if you have them. If keys are missing, the server runs in simulation mode so the rest of the application can still be tested.

4. Start the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

## How to Test

### 1. Interactive Terminal Tester
Run this in a separate terminal while the server is active:
```bash
python test_cli.py
```
This lets you test dictating visit notes, correcting values by voice, and triggering danger sign alerts.

### 2. Automated Test Suite
```bash
PYTHONPATH=backend pytest tests/ -v
```
Runs 11 automated tests covering danger signs, SQLite storage, and WebSocket streaming.

---

## API Endpoints

- `WebSocket /ws/audio`: Real-time audio streaming connection.
- `GET /records`: Returns all saved visit records from SQLite.
- `GET /records/{id}`: Returns a single visit record.
- `POST /records`: Adds or updates a visit record.
- `DELETE /records/{id}`: Deletes a visit record.
- `DELETE /records`: Clears all visit records.
- `GET /health`: Service health check.
- `GET /danger-signs`: Returns the list of MoHFW danger signs.
