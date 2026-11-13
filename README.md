# ASHA Voice Field Register
Gnani Voice Hackathon - Problem Statement 1 (Healthcare Track)

A voice tool that lets an ASHA worker speak home-visit notes in Hindi, Kannada, Telugu, or Tamil mixed with English, and saves a structured record with zero typing.

Built on the Gnani API Platform using Prisma v3.0 (Speech-to-Text) and Timbre v3.0 (Text-to-Speech) over streaming WebSockets.

---

## How to Run

### Automatic Run (One Click)

#### On macOS or Linux:
Open your terminal in the project folder and run:
```bash
./run.sh
```
This script will:
1. Automatically free up ports 8000 and 3000 if they are still held from an earlier run.
2. Set up the Python virtual environment and install backend requirements.
3. Install frontend packages.
4. Start the backend and frontend simultaneously.
5. Automatically open the application at http://localhost:3000 in your default browser.

#### On Windows:
Double-click `run.bat`, or run it in Command Prompt:
```cmd
run.bat
```
This automatically sets up dependencies, opens backend and frontend terminals, and launches http://localhost:3000 in your default browser.

---

### Manual Run

If you prefer to start services yourself:

#### 1. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # On Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
- Backend address: http://localhost:8000
- API documentation: http://localhost:8000/docs
- WebSocket address: ws://localhost:8000/ws/audio

#### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
- Frontend address: http://localhost:3000

---

## How to Test the Backend

You can test the voice pipeline right now in your terminal without opening a browser:

1. Start the backend:
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

2. Open another terminal and run the interactive test tool:
   ```bash
   cd backend
   source .venv/bin/activate
   python test_cli.py
   ```
   This gives you a menu to test:
   - Normal ANC home visit note
   - Voice correction ("No, weight is 54 kilo")
   - Voice confirmation ("Yes, save it")
   - Newborn danger sign escalation (high fever, not feeding)
   - Pregnancy danger sign escalation (bleeding)
   - Viewing saved records in the SQLite database

3. Run automated tests:
   ```bash
   PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/ -v
   ```
   All 11 tests check danger signs, database operations, and WebSocket messages.

---

## Team Responsibilities

To avoid overlapping work during the hackathon, each person works in their own folder:

- Backend Lead: Works in `backend/` (FastAPI, Gnani STT/TTS connections, Groq LLM extraction, database).
- Frontend Lead: Works in `frontend/` (User interface, microphone capture, form preview, emergency banner).
- Presentation and Documentation Lead: Works in `docs/` (Slides, pitch script, demo test cases, guideline notes).

For Git branch and pull request steps, read [CONTRIBUTORS.md](CONTRIBUTORS.md).

---

## Danger Signs Guideline Reference

Per the hackathon rules, danger signs are taken directly from public health guidelines:

- Source: National Health Mission, Ministry of Health and Family Welfare (MoHFW), Government of India.
- Document: Home Based Newborn Care and Maternal Health Danger Signs (ASHA Modules 6 and 7).
- Behavior: When spoken notes mention any danger sign from the list (such as bleeding during pregnancy or high fever in a newborn), the system tells the worker to refer the patient to the Primary Health Centre (PHC) immediately, and flags the record. It never gives medical diagnosis or treatment advice.
- Full details: See [docs/guidelines/mohfw_danger_signs.md](docs/guidelines/mohfw_danger_signs.md).
