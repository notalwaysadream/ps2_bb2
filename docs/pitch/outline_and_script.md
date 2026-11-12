# Pitch Deck Outline & Presentation Guide

Owner: Presentation & Documentation Lead

## Presentation Structure (3-5 Minutes Hackathon Pitch)

### Slide 1: The Problem
- **The Ground Reality**: India has 1M+ ASHA workers visiting 25-30 homes daily.
- **The Friction**: Juggling physical registers and small-screen mobile apps while walking between rural homes. Records are delayed, inaccurate, or skipped.

### Slide 2: The Solution: Voice-First Field Register
- A low-latency voice agent built on **Gnani Prisma v3.0 STT** and **Timbre v3.0 TTS**.
- Works in **code-mixed Indic languages** (Hindi/Kannada/English).
- Natural voice confirmation and instant voice-driven corrections.

### Slide 3: Technical Architecture & Innovation
- End-to-end WebSocket streaming pipeline (Sub-second Time to First Audio).
- Noise resilience (household & street noise tolerance).
- Local health vocabulary handling (`ANC checkup`, `TT injection`, `IFA goli`).

### Slide 4: Responsible AI & Safety Guardrail (Double-Scored Feature)
- MoHFW-aligned danger sign detection (PPH, newborn hypothermia, sepsis).
- Zero diagnostic hallucination — triggers immediate PHC referral protocols.

### Slide 5: Live Demo & Social Impact
- Live walkthrough scenario: Dictating visit notes, correcting a weight value by voice, triggering a simulated danger sign.
- Next steps: Offline caching, regional dialect expansions.
