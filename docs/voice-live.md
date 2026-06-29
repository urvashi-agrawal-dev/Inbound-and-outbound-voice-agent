# Live Voice Dashboard — Vapi Integration

## Overview

The Live Voice dashboard (`/voice-live`) connects the Karta SDR frontend to Vapi for browser-based voice calls while syncing all qualification data through the existing FSM and lead scoring engine.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  VoiceAgent     │────►│  Vapi Cloud  │────►│  User Mic/Speaker│
│  (@vapi-ai/web)│     └──────────────┘     └─────────────────┘
└────────┬────────┘
         │ POST /vapi/transcript (user speech)
         │ POST /vapi/events (lifecycle)
         ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  FastAPI        │────►│  FSM Engine  │────►│  Lead Scorer    │
│  Backend        │     └──────────────┘     └─────────────────┘
└────────┬────────┘
         │ WebSocket broadcast
         ▼
┌─────────────────┐
│  VoiceLive UI   │
│  (real-time)    │
└─────────────────┘
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_VAPI_PUBLIC_KEY` | Vapi public API key for Web SDK |
| `VITE_VAPI_ASSISTANT_ID` | Your existing Vapi assistant ID |
| `NEXT_PUBLIC_VAPI_PUBLIC_KEY` | Alias (Next.js convention, also supported) |
| `NEXT_PUBLIC_VAPI_ASSISTANT_ID` | Alias for assistant ID |

## Demo Mode

When Vapi keys are missing or connection fails:

1. Dashboard shows "Demo Mode" badge
2. A scripted qualification call runs automatically
3. Each user utterance is sent to the backend FSM via `/vapi/transcript`
4. WebSocket broadcasts update the UI in real time
5. Final score, tier, and summary match production behavior

This ensures the system is always demonstrable in interviews.

## WebSocket Events

Clients connect to `ws://HOST/ws/calls/{call_id}` and receive JSON messages:

```json
{
  "event": "utterance_processed",
  "data": {
    "call_id": "...",
    "current_state": "CALL_VOLUME",
    "scoring": { "total_score": 45, "tier": "Warm Lead" },
    "transcript": [...],
    "qualification_checklist": [...],
    "duration_seconds": 42.5,
    "cost_usd": 0.06,
    "avg_latency_ms": 5.2
  }
}
```

Event types: `connected`, `transcript`, `utterance_processed`, `call-start`, `call-end`, `speech-start`, `speech-end`, `call_ended`, `error`.

## Vapi SDK Events Handled

| Vapi Event | Action |
|------------|--------|
| `call-start` | Set connection status, start timer |
| `call-end` | End call, fetch summary |
| `speech-start` | Show speaking indicator |
| `speech-end` | Clear speaking indicator |
| `message` (transcript) | Display + sync to backend |
| `error` | Show error, optional demo fallback |

## Docker

WebSocket proxy is configured in `frontend/nginx.conf`. Rebuild frontend with Vapi build args:

```bash
cd docker
VITE_VAPI_PUBLIC_KEY=pk_xxx VITE_VAPI_ASSISTANT_ID=asst_xxx docker compose up --build
```

## Local Development

```bash
# Terminal 1 — Backend
cd backend && uvicorn app.main:app --reload --port 8001

# Terminal 2 — Frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5173/voice-live
