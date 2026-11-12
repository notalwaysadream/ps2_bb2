# Frontend Setup and Guide

This folder contains the web interface for the ASHA Voice Register.

---

## Requirements
- Node.js 18+ and npm

---

## Setup Steps

1. Install packages:
   ```bash
   cd frontend
   npm install
   ```

2. Start development server:
   ```bash
   npm run dev
   ```
   Open http://localhost:3000 in your browser.

---

## What the Frontend Needs to Do
- Record microphone audio and stream 16kHz linear PCM bytes to `ws://localhost:8000/ws/audio`.
- Show live transcript as the worker speaks.
- Display extracted visit details (Beneficiary ID, visit type, weight, vaccines, next date).
- Play back agent audio responses.
- Show a red emergency alert banner whenever a danger sign is flagged.
- Let the worker tap "Confirm and Save" or say "Yes, save it".
