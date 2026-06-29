# Karta SDR

**AI Voice Sales Development Representative** — a production-style voice agent that calls inbound leads, qualifies them through a finite state machine, scores leads, stores results in CRM, and books meetings for qualified prospects.

Built to demonstrate how modern AI calling platforms work: low latency, interruption handling, structured conversation flows, and full post-call automation.

## Architecture

```
Caller → STT (Whisper) → Conversation Engine (FSM) → Business Logic → CRM + Calendar → TTS (Edge TTS) → Caller
                              ↑
                         Gemini LLM
                              ↑
                    Vapi / LiveKit (Voice Orchestration)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (async) |
| Database | Supabase PostgreSQL |
| LLM | Google Gemini API |
| Speech-to-Text | OpenAI Whisper |
| Text-to-Speech | Microsoft Edge TTS |
| Voice Orchestration | Vapi or LiveKit |
| CRM | Google Sheets |
| Calendar | Google Calendar API |
| Frontend | React + Recharts |
| Deployment | Docker Compose |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- API keys: Gemini, Whisper (OpenAI), Vapi or LiveKit
- Google Cloud service account for Sheets + Calendar

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

Place your Google service account JSON at `./credentials.json`.

### 2. Run with Docker

```bash
cd docker
docker compose up --build
```

- **API**: http://localhost:8000
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### 3. Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Conversation Flow (FSM)

The agent follows a strict finite state machine — not a free-form chatbot:

```
INTRO → PERMISSION → COMPANY_INFO → CALL_VOLUME → CURRENT_PROCESS
  → PAIN_POINTS → BUDGET → TIMELINE → LEAD_SCORING → BOOKING → END_CALL
```

Detours: `FAQ_DETOUR` (product/pricing questions), `HUMAN_HANDOFF` (caller requests a person).

## Lead Scoring

| Dimension | Scoring |
|-----------|---------|
| Company Size (1-10 / 11-50 / 51-200 / 200+) | 5 / 15 / 25 / 40 pts |
| Monthly Call Volume (<1K / 1-10K / 10-50K / 50K+) | 5 / 20 / 35 / 50 pts |
| Budget (<$500 / $500-2K / $2K-10K / $10K+) | 0 / 15 / 30 / 40 pts |
| Timeline (12mo+ / 6mo / 3mo / immediate) | 0 / 10 / 20 / 30 pts |

**Tiers:** 0-40 Unqualified · 41-80 Warm · 81-120 SQL · 120+ Enterprise

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/calls` | Initiate a new call |
| `POST` | `/api/v1/calls/{id}/utterance` | Process caller speech (text) |
| `POST` | `/api/v1/calls/{id}/audio` | Process caller speech (audio) |
| `POST` | `/api/v1/calls/{id}/end` | End call, generate summary, sync CRM |
| `GET` | `/api/v1/calls/{id}` | Get call details |
| `GET` | `/api/v1/calls` | List calls (paginated) |
| `GET` | `/api/v1/analytics/dashboard` | Dashboard metrics |
| `GET` | `/api/v1/leads` | List qualified leads |
| `POST` | `/api/v1/webhooks/vapi/events` | Vapi webhook handler |
| `POST` | `/api/v1/webhooks/booking` | Book a demo meeting |
| `GET` | `/api/v1/health` | Health check |

See [docs/api-examples.md](docs/api-examples.md) for request/response examples.

## Key Features

- **Barge-in handling** — detects caller speech during TTS, cancels playback within 300ms grace period
- **Conversation memory** — full turn-level context retention across the call
- **FAQ detours** — answers pricing/product questions, then returns to qualification flow
- **Human handoff detection** — recognizes requests for a live representative
- **Post-call summary** — Gemini-generated CRM-ready summaries
- **Automatic CRM sync** — creates Google Sheets records on call completion
- **Demo booking** — Google Calendar integration for qualified leads
- **Analytics dashboard** — qualification rate, booking rate, latency, drop-off stages, cost per conversation
- **Live Voice Dashboard** (`/voice-live`) — Vapi Web SDK integration with real-time FSM, scoring, and transcript updates via WebSocket

## Live Voice Dashboard

Open **http://localhost:3001/voice-live** (or http://localhost:5173/voice-live in dev) for the operations console.

### Features

- Start/end live voice calls from the browser (Vapi Web SDK)
- Real-time transcript panel (AI + Lead)
- FSM state visualization and qualification checklist
- Live lead score and tier updates
- Cost and latency tracking
- Post-call summary and qualification result card
- **Demo mode** — automatically simulates a full qualification call when Vapi keys are not configured

### Vapi Configuration

Add to `.env` (root) or `frontend/.env`:

```env
VITE_VAPI_PUBLIC_KEY=your-vapi-public-key
VITE_VAPI_ASSISTANT_ID=your-vapi-assistant-id
```

Also supported: `NEXT_PUBLIC_VAPI_PUBLIC_KEY` and `NEXT_PUBLIC_VAPI_ASSISTANT_ID`.

### Data Flow

```
User microphone → Vapi Web SDK → POST /api/v1/vapi/transcript
  → FSM + Lead Scoring → WebSocket broadcast → Dashboard UI
```

WebSocket endpoint: `ws://localhost:8001/ws/calls/{call_id}`

### API Endpoints (Live Voice)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/vapi/transcript` | Process transcript through FSM |
| `POST` | `/api/v1/vapi/events` | Vapi lifecycle events |
| `GET` | `/api/v1/calls/{id}/live` | Current live call state |
| `GET` | `/api/v1/calls/{id}/summary` | Call summary (live or completed) |
| `WS` | `/ws/calls/{call_id}` | Real-time updates |

See [docs/voice-live.md](docs/voice-live.md) for full integration details.

## Project Structure

```
backend/          FastAPI application
  app/
    api/routes/   REST endpoints
    core/fsm/     Finite state machine
    core/conversation/  Memory, interruptions, FAQ
    core/scoring/ Lead scoring engine
    services/     External integrations
    models/       SQLAlchemy ORM
    schemas/      Pydantic models
frontend/         React analytics dashboard
database/         PostgreSQL schema & migrations
docker/           Docker Compose configuration
docs/             Architecture, diagrams, prompts, API examples
```

## Documentation

- [Architecture](docs/architecture.md)
- [Sequence Diagrams](docs/sequence-diagrams.md)
- [Example Prompts](docs/prompts.md)
- [API Examples](docs/api-examples.md)

## Simulating a Call (without Vapi)

```bash
# Create a call
curl -X POST http://localhost:8000/api/v1/calls \
  -H "Content-Type: application/json" \
  -d '{}'

# Send utterances (use the call_id from above)
curl -X POST http://localhost:8000/api/v1/calls/{call_id}/utterance \
  -H "Content-Type: application/json" \
  -d '{"text": "Hi, my name is Sarah Johnson"}'

curl -X POST http://localhost:8000/api/v1/calls/{call_id}/utterance \
  -H "Content-Type: application/json" \
  -d '{"text": "Yes, now is a good time"}'

curl -X POST http://localhost:8000/api/v1/calls/{call_id}/utterance \
  -H "Content-Type: application/json" \
  -d '{"text": "We are TechFlow Inc, a SaaS company with about 75 employees"}'

# End the call
curl -X POST http://localhost:8000/api/v1/calls/{call_id}/end \
  -H "Content-Type: application/json" \
  -d '{"reason": "completed"}'
```

## License

MIT
