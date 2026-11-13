# ASHA Dhwani (ಆಶಾ ಧ್ವನಿ)
### Hands-Free Voice Field Register for ASHA Workers
**Problem Statement 1: Healthcare Track &bull; Gnani Voice Hackathon 2026**

[![Live Cloud Demo](https://img.shields.io/badge/Live_Demo-asha--dhwani.onrender.com-success?style=for-the-badge&logo=render)](https://asha-dhwani.onrender.com/)
[![Tests](https://img.shields.io/badge/Pytest-16%20Passed-brightgreen?style=for-the-badge)](https://github.com/notalwaysadream/ps2_bb2)
[![STT / TTS](https://img.shields.io/badge/Gnani_Voice-Prisma_v3_+_Timbre_v3-blue?style=for-the-badge)](https://gnani.ai/)

---

## Live Cloud Demo

You can try the live application right now in your mobile or desktop browser:

👉 **[https://asha-dhwani.onrender.com/](https://asha-dhwani.onrender.com/)**

> [!WARNING]
> **First-Load Wake-Up Notice**: This application is hosted on Render's free tier. If the instance has been inactive for more than 15 minutes, Render spins down the container. On your first visit, it may take **30 to 50 seconds** to wake up. Once initialized, the application responds instantly in real-time.

---

## The Problem

Accredited Social Health Activists (ASHAs) are the primary healthcare lifeline for over 100 million rural mothers and newborns across India. During daily field visits, an ASHA worker must log:
- Antenatal Care (ANC) progress, gestational weights, tetanus injections (TT), and iron-folic acid (IFA) supplies.
- Home-Based Newborn Care (HBNC) checks across days 3, 7, 14, 21, 28, and 42.
- Critical danger signs requiring emergency hospital referrals.

Today, workers are forced to juggle paper registers or tiny smartphone keyboards while walking between houses in noisy village environments. Typing complex dates, names, and medical details eats into direct patient care, leads to delayed entries, and causes critical health alerts to be missed.

---

## Our Solution: ASHA Dhwani

**ASHA Dhwani** turns spoken field notes into a structured clinical record and an actionable follow-up schedule—with **zero typing**. 

The worker speaks naturally in her local language mixed with English (*Kannada Kanglish* or *Hindi Hinglish*), and within seconds, the system:
1. Filters ambient background noise and captures multi-field spoken notes end-to-end.
2. Extracts beneficiary details, vitals, immunisations, and next visit dates into a structured digital record.
3. Automatically scans for maternal and neonatal danger signs per Ministry of Health and Family Welfare (MoHFW) protocols.
4. Reads the record back aloud over voice in her language for confirmation.
5. Accepts hands-free voice corrections (*"No, weight is 2.8 kilo"* or *"Make the next visit 28th November"*) before final persistence.

---

## Key Features & Evaluation Criteria Alignment

| Evaluation Criterion | Implementation Details in ASHA Dhwani |
| :--- | :--- |
| **Live Judge Test** *(30%)* | **Sub-second audio latency**, accurate extraction of Indic names (*Sunita Devi*, *Priya Gowda*, *Kavita*) and numerical vitals (*54.5 kg*, *2.85 kg*), and robust ambient noise rejection (`1200 RMS threshold`). |
| **Speech-Layer Depth** *(20%)* | Full-duplex WebSocket streaming (`16kHz PCM16`) using **Gnani Prisma v3.0** STT and **Timbre v3.0** TTS; conversational pause buffer (`4.0s`) for natural pacing between sentences; instant barge-in interruption; and immediate tap-to-conclude support. |
| **Fit for Target User** *(20%)* | Works on low-cost Android smartphones in any standard browser without requiring app store installation; high-contrast cards, large tap targets, and clear Indic voice prompts. |
| **Workflow Innovation** *(10%)* | Goes beyond a basic chatbot: structured live card previews, interactive spoken read-back, automatic follow-up schedule generation, and one-tap emergency referral banners. |
| **Responsible AI & Compliance** *(10%)* | **Zero diagnostic or prescription hallucination**; strictly follows MoHFW Modules 6 & 7 danger-sign referral protocols; uses synthetic beneficiary IDs only; and includes mandatory 2-second AI identity disclosure. |
| **Demo & Documentation** *(10%)* | Fully functional live cloud deployment, comprehensive test suite (16/16 unit and integration tests passing), and turnkey local setup scripts for both macOS/Linux and Windows. |

---

## MoHFW Clinical Danger-Sign Protocols (Public Health Guideline Citation)

> [!IMPORTANT]
> **Hackathon Track-Specific Requirement**:
> *"Track-specific guardrails. Synthetic beneficiaries only. Teams build their danger-sign list from a public health guideline and cite it in the README."*

Per the hackathon guidelines, danger-sign escalation in ASHA Dhwani is strictly grounded in official Government of India public health guidelines:
- **Source**: National Health Mission (NHM), Ministry of Health and Family Welfare (MoHFW), Government of India.
- **Official Document**: *ASHA Training Modules 6 & 7: Skills That Save Lives - Home Based Newborn Care & Maternal Health Danger Signs*.
- **Official Guideline Portal**: [https://nhm.gov.in](https://nhm.gov.in)
- **Detailed Clinical Mapping & Citation Documentation**: [docs/guidelines/mohfw_danger_signs.md](docs/guidelines/mohfw_danger_signs.md)

The system monitors spoken notes against two clinical symptom categories:

### 1. Maternal Danger Signs (Module 6)
- Vaginal bleeding during pregnancy or postpartum (*raktasrava*, *bleeding*).
- Severe headache with blurred vision (*tivre thale novu*, *sar dard* - sign of pre-eclampsia/eclampsia).
- Convulsions or loss of consciousness (*fits*, *moorchhe*).
- High fever with chills or foul-smelling discharge.

### 2. Newborn & Infant Danger Signs (Module 7)
- Inability to suck or feed (*haalu kudiyala*, *doodh nahi pee raha*).
- High fever (>38.5°C) or baby cold to touch (<35.5°C / hypothermia).
- Severe chest indrawing or fast breathing (>60 breaths/min).
- Jaundice / yellowness of palms and soles within 24 hours of birth.
- Redness, pus, or foul discharge from the umbilical cord (*naabhi*).

> **Clinical Guardrail**: When any danger sign from the MoHFW list is detected, ASHA Dhwani immediately advises referral to the Primary Health Centre (PHC) or First Referral Unit (FRU) in the worker's spoken language (*"Yeh gambhir lakshan hai. Beneficiary ko turant nazdiki PHC le jayein."*) and marks the record with an emergency badge. **The system never provides medical diagnosis or drug prescriptions.**
> 
> See the complete guideline reference at [docs/guidelines/mohfw_danger_signs.md](docs/guidelines/mohfw_danger_signs.md).

---

## Pre-Loaded Clinical Sample Records

To ensure the system is fully verifiable upon first launch (even before dictating new visits), the database automatically seeds five realistic synthetic records covering the problem statement requirements:

1. **Sunita Devi** (`KA-BLR-4408`) &bull; *ANC 3rd Checkup*  
   - Spoken in Kannada code-mix. Weight: 54.5 kg, TT-2 injection completed, 100 IFA tablets issued. Next visit: 28 Nov 2026. (Routine / Normal).
2. **Priya Gowda** (`KA-MYS-8821`) &bull; *ANC 4th Checkup (Emergency Referral)*  
   - Spoken in Kannada. Severe headache, blurred vision, and bleeding flagged. Emergency referral to PHC triggered immediately.
3. **Baby of Lakshmi** (`KA-BLR-1042`) &bull; *HBNC Day 7 Visit*  
   - Spoken in Kannada. Weight: 2.85 kg. BCG, OPV-0, and Hep-B birth doses verified. Normal cord and active feeding. Next visit: Day 14.
4. **Baby of Rekha** (`KA-MYS-9014`) &bull; *HBNC Day 14 (High-Risk Referral)*  
   - Spoken in Kannada. Severe chest indrawing, high fever, and refusal to feed. Urgent referral to District Hospital flagged.
5. **Kavita Devi** (`UP-LKO-3312`) &bull; *ANC 2nd Checkup*  
   - Spoken in Hindi code-mix (*"60 IFA goli di, TT-1 ho gaya, wazan 49 kilo"*). Routine visit saved.

---

## Quickstart: Running Locally

### Prerequisites
- **Python**: 3.10 to 3.14
- **Node.js**: v18 or later
- **Operating System**: macOS, Linux, or Windows 10/11

---

### Option A: One-Click Launch (Recommended)

#### On macOS or Linux:
Open your terminal in the repository folder and execute:
```bash
chmod +x run.sh
./run.sh
```
*The script automatically frees ports 8000/3000 if held, creates the Python virtual environment, installs packages, and launches http://localhost:3000 in your browser.*

#### On Windows:
Double-click `run.bat` or run it from Command Prompt / PowerShell:
```cmd
run.bat
```

---

### Option B: Manual Step-by-Step Setup

If you prefer running services manually across two terminals:

#### Terminal 1: Backend (FastAPI + WebSocket Server)
```bash
cd backend

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment keys
cp .env.example .env            # On Windows: copy .env.example .env
```

Edit `backend/.env` to include your API keys:
```env
GNANI_API_KEY=your_gnani_api_key_here
GROQ_API_KEY=your_groq_api_key_here
DEFAULT_LANGUAGE=kn-IN
DEFAULT_VOICE=Shivani
```
*(If a Gnani key is not provided, the backend automatically operates in fallback simulation mode so the application remains testable).*

Start the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- REST API & Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- WebSocket Endpoint: `ws://localhost:8000/ws/audio`
- Standalone Direct Interface: [http://localhost:8000](http://localhost:8000)

#### Terminal 2: Frontend (Vite + React)
```bash
cd frontend
npm install
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## Running the Automated Test Suite

The test suite validates WebSocket lifecycles, streaming audio chunks, Groq LLM extraction, Indic name preservation, Beneficiary ID priority readback, next visit date extraction, and MoHFW danger-sign guardrails:

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

Expected result:
```text
tests/test_api.py::test_health_endpoint PASSED                           [  6%]
tests/test_api.py::test_danger_signs_endpoint PASSED                     [ 12%]
tests/test_api.py::test_records_rest_flow PASSED                         [ 18%]
tests/test_backend.py::test_danger_signs_pregnancy_bleeding PASSED       [ 25%]
tests/test_backend.py::test_danger_signs_newborn_fever_and_poor_feeding PASSED [ 31%]
tests/test_backend.py::test_normal_anc_no_danger_signs PASSED            [ 37%]
tests/test_backend.py::test_database_crud PASSED                         [ 43%]
tests/test_backend.py::test_extraction_and_voice_correction PASSED       [ 50%]
tests/test_backend.py::test_kannada_extraction_and_readback PASSED       [ 56%]
tests/test_backend.py::test_audio_rms_and_vad PASSED                     [ 62%]
tests/test_backend.py::test_indic_name_extraction_and_ai_disclosure PASSED [ 68%]
tests/test_backend.py::test_readback_beneficiary_id_before_name_and_next_visit PASSED [ 75%]
tests/test_websocket.py::test_websocket_text_flow_and_readback PASSED    [ 81%]
tests/test_websocket.py::test_websocket_danger_sign_escalation PASSED    [ 87%]
tests/test_websocket.py::test_websocket_binary_audio_streaming PASSED    [ 93%]
tests/test_websocket.py::test_websocket_stop_recording_flow PASSED       [100%]

======================== 16 passed in ~0.14s =========================
```

---

## Interactive Terminal CLI Tool

You can test the entire extraction and voice correction flow directly in your terminal without opening a browser:

```bash
cd backend
source .venv/bin/activate
python test_cli.py
```
This tool provides a guided menu to test:
- Normal ANC routine dictation in Kannada and Hindi.
- Voice correction (*"No, weight is 54 kilo"*).
- Neonatal danger sign escalation (*"Baby has high fever and chest indrawing"*).
- Maternal danger sign escalation (*"Patient has severe bleeding"*).
- Inspecting saved records in SQLite.

---

## System Architecture

```text
  [ ASHA Worker ]
        │  (Speech in Kannada / Hindi + English)
        ▼
┌────────────────────────────────────────────────────────┐
│  Mobile Browser Client (HTML5 Audio / WebSockets)      │
│  - Captures 16kHz PCM audio via ScriptProcessor        │
│  - Real-time client-side RMS level meter               │
│  - Automatic reconnection & port detection             │
└───────────────────────┬────────────────────────────────┘
                        │ wss://<domain>/ws/audio
                        ▼
┌────────────────────────────────────────────────────────┐
│  FastAPI Backend Orchestrator (app/core/)              │
│  - VAD Energy Gate (Filters ambient room hiss >1200)   │
│  - Natural pause buffering (4.0s conversational timer) │
│  - Spoken barge-in detection & cancellation            │
└───────┬───────────────────────────────┬────────────────┘
        │                               │
        ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│  Gnani Prisma v3 STT      │   │  Danger Sign Detector     │
│  - Streaming transcription│   │  - MoHFW Modules 6 & 7    │
│  - Code-mixed Indic terms │   │  - Strict keyword lookup  │
└───────┬───────────────────┘   └───────────────┬───────────┘
        │                                       │
        ▼                                       ▼
┌────────────────────────────────────────────────────────┐
│  Groq LLM Service (qwen/qwen3.8-27b)                   │
│  - Zero diagnostic hallucination prompt                │
│  - Dual Indic extraction (beneficiary_name + ID)       │
│  - Mandatory 2-second AI identity disclosure prefix    │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  Gnani Timbre v3 TTS                                   │
│  - Conversational readback in chosen language          │
│  - Streams PCM audio chunks back to worker's phone     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│  SQLite Database Persistence (aiosqlite)               │
│  - Stores visit records, vitals, & referral flags      │
│  - Immediate multi-device sync (phone & laptop)        │
└────────────────────────────────────────────────────────┘
```

---

## REST Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status and simulation mode indicator |
| `GET` | `/records` | Returns all saved visit records ordered by most recent |
| `POST` | `/records` | Manually inserts or updates a visit record |
| `DELETE` | `/records` | Clears all visit records (used for demo resets) |
| `GET` | `/danger-signs`| Complete JSON catalog of MoHFW Modules 6 & 7 danger signs |
| `GET` | `/follow-ups` | Aggregated list of upcoming visits and pending immunisations |
| `WS` | `/ws/audio` | Full-duplex WebSocket stream for live speech processing |

---

## Responsible AI & Ethical Guardrails

1. **Track-Specific Clinical Guardrails & Public Health Guideline Citation**:
   - In accordance with the hackathon specifications (*"Track-specific guardrails. Synthetic beneficiaries only. Teams build their danger-sign list from a public health guideline and cite it in the README."*), danger signs are strictly compiled from the official Ministry of Health and Family Welfare (MoHFW) / National Health Mission (NHM) guidelines:
     - Document: *Home Based Newborn Care and Maternal Health Danger Signs (ASHA Modules 6 and 7)*.
     - Public Health Reference: [https://nhm.gov.in](https://nhm.gov.in)
     - Complete clinical mapping and referral protocol documentation: [docs/guidelines/mohfw_danger_signs.md](docs/guidelines/mohfw_danger_signs.md).
   - Behavior: When spoken notes mention any danger sign from the list (such as bleeding during pregnancy or high fever and refusal to feed in a newborn), the system interrupts to direct the worker to refer the beneficiary to the Primary Health Centre (PHC) immediately, and flags the record with an emergency badge.

2. **Synthetic Beneficiaries Only**:
   - All beneficiary names (*Sunita Devi*, *Priya Gowda*, *Baby of Lakshmi*, *Baby of Rekha*, *Kavita Devi*), identification numbers (`KA-BLR-4408`, `KA-MYS-8821`, `UP-LKO-3312`), and clinical visit notes in this repository and the live demonstration are purely synthetic. No real patient data or protected health information (PHI) is ever used.

3. **Zero Diagnostic or Prescription Hallucination**:
   - The assistant is strictly an administrative voice field documentation tool. It never provides medical diagnoses, predicts pathology, or prescribes medication or dosages. All critical cases are escalated to the nearest government Primary Health Centre.

4. **Transparent AI Identity Disclosure**:
   - In adherence to responsible AI standards, the agent announces that it is an automated AI assistant (*"Naanu ondu AI sahayaka..."* in Kannada, *"Main ek AI sahayak hoon..."* in Hindi, *"I am an AI assistant..."* in English) before reading back patient details.

5. **Spoken Readback Format (Beneficiary ID First)**:
   - Spoken read-backs always announce the Beneficiary ID first, followed by the name (*"Beneficiary ID 4408, Shantala..."*), preventing identification confusion in rural field settings where common names recur.

6. **Privacy & Ephemeral Audio**:
   - Audio streams are processed purely in memory for real-time STT streaming and are never persisted or stored to disk.

---

## Project Repository Layout

```text
ps2_bb2/
├── backend/
│   ├── app/
│   │   ├── config.py              # Environment variables & runtime settings
│   │   ├── main.py                # FastAPI app lifecycle & endpoints
│   │   ├── core/
│   │   │   ├── orchestrator.py    # WebSocket event manager & turn timer
│   │   │   └── audio_stream.py    # VAD audio thresholding & chunking
│   │   ├── services/
│   │   │   ├── gnani_stt.py       # Gnani Prisma v3 STT streaming client
│   │   │   ├── gnani_tts.py       # Gnani Timbre v3 TTS streaming client
│   │   │   ├── llm_service.py     # Groq extraction & AI identity prefix
│   │   │   └── database.py        # aiosqlite CRUD & synthetic seed data
│   │   ├── health_guardrails/
│   │   │   └── danger_signs.py    # MoHFW Modules 6 & 7 clinical rules
│   │   └── models/
│   │       └── visit_record.py    # Pydantic schemas for visits & alerts
│   ├── tests/                     # 16 backend unit and integration tests
│   └── test_cli.py                # Guided terminal testing menu
├── frontend/
│   ├── index.html                 # Production single-file web client
│   ├── asha-voice-system.html     # Mirror copy for direct FastAPI serving
│   ├── package.json               # Node.js dependencies
│   └── src/
│       ├── App.jsx                # React single-component UI
│       └── index.css              # Responsive styles & design tokens
├── run.sh                         # macOS/Linux one-click launcher
├── run.bat                        # Windows one-click launcher
├── README.md                      # Project documentation
└── convo1.md                      # Persistent context tracking across sessions
```
