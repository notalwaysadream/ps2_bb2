# Pitch Outline and Presentation Guide

This document outlines the slide deck and speaking points for the hackathon presentation.

---

## Slide Outline (3 to 5 Minutes)

### Slide 1: The Problem
- Over 1 million ASHA workers visit 25 to 30 rural households every day.
- They have to write down notes in paper registers or type on small phones while walking between houses.
- Because typing takes time, records are often delayed, incomplete, or filled out late at night.

### Slide 2: The Solution
- A hands-free voice field register built on the Gnani API platform.
- The worker speaks her notes in her local language mixed with English (e.g. Hindi, Kannada, Telugu, Tamil).
- The system extracts all fields automatically, reads them back aloud, and saves them.

### Slide 3: Technical Setup
- Speech to Text: Gnani Prisma v3.0 WebSocket streaming with healthcare word hints.
- Text to Speech: Gnani Timbre v3.0 WebSocket streaming with natural Indic voices.
- Fast Extraction: Groq Llama-3.3 for quick response times under one second.
- Low Latency: Direct streaming from browser microphone to audio playback with barge-in support.

### Slide 4: Safety Guardrails (MoHFW Guidelines)
- Built using official National Health Mission guidelines (Modules 6 and 7).
- If the worker mentions danger signs (like bleeding during pregnancy or high fever in a newborn), the system flags the case immediately.
- It tells the worker in her own language to refer the patient to the Primary Health Centre (PHC) right away.
- It never gives medical advice or diagnoses.

### Slide 5: Live Demo and Impact
- Live test: Speaking a visit note, correcting a field by voice, and demonstrating danger sign escalation.
- Impact: Saves 1 to 2 hours of typing per day for every field worker.
