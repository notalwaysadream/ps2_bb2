# Frontend - ASHA Voice Field Register

Owner: Frontend Lead

## Responsibilities
- Mobile-first Web UI optimized for field conditions (simple high-contrast, large tap targets)
- WebSocket audio streaming from browser microphone to `/ws/audio`
- Real-time live transcript and streaming read-back audio player
- Live visit card preview showing extracted fields (Beneficiary ID, Weight, Vaccines, Visit Type)
- Danger sign alert banner (red high-priority PHC referral banner)
- Barge-in visual feedback (indicates when agent is listening vs speaking)

## Setup
```bash
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000)
