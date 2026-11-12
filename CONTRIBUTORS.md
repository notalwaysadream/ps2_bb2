# Team Contribution Guide

This guide explains how our team of three will work together without stepping on each other's files.

---

## Team Division of Work

| Name / Role | Main Folder | Tasks |
|---|---|---|
| Member 1 (Lead - Backend) | `backend/` | Gnani STT and TTS streaming, Groq LLM extraction, MoHFW danger signs check, database, WebSocket endpoint. |
| Member 2 (Frontend) | `frontend/` | Web interface, microphone recording, live transcript display, visit form preview, red alert banner. |
| Member 3 (Pitch and Docs) | `docs/` | Pitch deck, presentation script, live demo test cases, guideline notes, submission video. |

Rule: Only edit files inside your own assigned folder.

---

## How to Push Changes (For Team Members)

### 1. Clone the repository
```bash
git clone https://github.com/<team-lead-username>/asha-vani.git
cd asha-vani
```

### 2. Make your own branch
Do not push directly to main. Create a branch for your work:
```bash
# If you are doing frontend:
git checkout -b feat/frontend-ui

# If you are doing docs or presentation:
git checkout -b docs/pitch-deck
```

### 3. Work only in your folder
- Frontend person edits only inside `frontend/`.
- Docs person edits only inside `docs/`.
- Backend person edits only inside `backend/`.

### 4. Commit and push your branch
```bash
git add frontend/    # or git add docs/
git commit -m "Add voice recording button and live transcript card"
git push origin <your-branch-name>
```

### 5. Open a Pull Request on GitHub
1. Go to the repository page on GitHub.
2. Click the green "Compare & pull request" button.
3. Write a short note describing what you changed.
4. Click "Create pull request".
5. Ask the Team Lead to review and merge it into main.

---

## How to Keep Your Branch Updated

Before starting new work, pull the latest changes from main:
```bash
git checkout main
git pull origin main
git checkout <your-branch-name>
git merge main
```
