# Karta SDR — Architecture Documentation

## System Overview

Karta SDR is an AI voice agent platform designed for inbound lead qualification. Unlike free-form chatbots, it uses a **finite state machine (FSM)** to ensure reliable, repeatable qualification conversations with predictable outcomes.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Voice Layer                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │  Caller  │◄──►│ Vapi/LiveKit │◄──►│  Webhook Endpoints       │  │
│  └──────────┘    └──────────────┘    └──────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Processing Pipeline                             │
│                                                                      │
│  ┌─────────┐   ┌──────────────┐   ┌────────────┐   ┌────────────┐  │
│  │ Whisper │──►│ Conversation │──►│ Lead       │──►│ Edge TTS   │  │
│  │  (STT)  │   │ Manager+FSM  │   │ Scorer     │   │  (TTS)     │  │
│  └─────────┘   └──────┬───────┘   └────────────┘   └────────────┘  │
│                       │                                              │
│                  ┌────▼─────┐                                        │
│                  │  Gemini  │                                        │
│                  │   LLM    │                                        │
│                  └──────────┘                                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Business Logic Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Google Sheets│  │ Google       │  │ Summary Generator        │  │
│  │ CRM          │  │ Calendar     │  │ (Post-call)              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Data Layer                                      │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Supabase         │  │ Session Store│  │ Analytics Dashboard  │  │
│  │ PostgreSQL       │  │ (in-mem/Redis)│  │ (React)             │  │
│  └──────────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Finite State Machine (`core/fsm/`)

The FSM enforces a structured qualification flow. Each state has:
- A defined objective (what information to collect)
- Required fields before advancing
- Allowed transitions (including detours to FAQ or human handoff)

**Why FSM over free-form chat?**
- Predictable data collection (every call gathers the same fields)
- Measurable drop-off points per stage
- Reliable scoring (all inputs present before scoring)
- Lower latency (smaller, focused LLM prompts per state)

### 2. Conversation Manager (`core/conversation/`)

Orchestrates the full turn lifecycle:

1. Receive STT transcript
2. Detect intent (continue, FAQ, human handoff, end call)
3. Extract structured fields via Gemini
4. Evaluate FSM transition
5. Generate state-appropriate response via Gemini
6. Track metrics (latency, interruptions, tokens)

**Memory** retains full turn history with state annotations.
**Interruption handler** manages barge-in with TTS cancellation.
**FAQ handler** answers off-script questions and returns to flow.

### 3. Lead Scorer (`core/scoring/`)

Deterministic scoring based on four dimensions:
- Company size (employee count)
- Monthly call volume (inbound + outbound)
- Budget range
- Implementation timeline

Scoring is rule-based (not LLM-based) for consistency and auditability.

### 4. Voice Orchestration (`services/voice_orchestrator.py`)

Abstraction layer supporting two providers:
- **Vapi**: Managed telephony with webhook-based STT/TTS/LLM routing
- **LiveKit**: Real-time WebRTC rooms for browser/app-based calls

### 5. External Integrations

| Service | Purpose | Failure Mode |
|---------|---------|-------------|
| Gemini | Response generation, field extraction, summaries | Retry 3x with exponential backoff |
| Whisper | Speech-to-text | Falls back to local Whisper model |
| Edge TTS | Text-to-speech | Returns error, call continues text-only |
| Google Sheets | CRM record creation | Logged error, call data still in DB |
| Google Calendar | Demo booking | Returns available slots as fallback |

## Latency Budget

Target: **< 500ms** end-to-end per turn.

| Stage | Target | Strategy |
|-------|--------|----------|
| STT (Whisper) | 150ms | Streaming transcription where supported |
| Field extraction | 100ms | Small focused Gemini prompt |
| FSM transition | <1ms | Pure Python logic |
| Response generation | 200ms | Concise prompts, gemini-2.0-flash |
| TTS (Edge) | 50ms | Stream audio chunks for playback |

## Interruption Handling

```
Agent speaking ──► VAD detects caller speech ──► Cancel TTS (300ms grace)
                                                      │
                                                      ▼
                                              Buffer new utterance
                                                      │
                                                      ▼
                                              Process as interrupted turn
                                                      │
                                                      ▼
                                              Generate new response
```

Key design decisions:
- Grace period prevents false triggers from background noise
- Interrupted turns are flagged in analytics
- Agent acknowledges interruption naturally ("Sorry, go ahead...")

## Data Flow on Call End

1. Session removed from memory store
2. Final scoring computed
3. Gemini generates call summary
4. Call record updated in PostgreSQL
5. Lead record created
6. Google Sheets CRM row appended
7. If qualified + email present, calendar booking offered

## Security Considerations

- Webhook signature verification (Vapi)
- Service account credentials mounted read-only in Docker
- Supabase RLS policies restrict data access
- No PII in application logs (structured logging with call_id only)
- CORS restricted to configured origins

## Scalability

- Stateless API servers (session state in Redis when enabled)
- Async I/O throughout (FastAPI + asyncpg + httpx)
- Connection pooling for PostgreSQL (pool_size=10, max_overflow=20)
- Horizontal scaling via Docker replicas behind load balancer

## Deployment Topology

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (reverse   │
                    │   proxy)    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │                         │
       ┌──────▼──────┐          ┌───────▼──────┐
       │  Frontend   │          │   Backend    │
       │  (React)    │          │  (FastAPI)   │
       └─────────────┘          └───────┬──────┘
                                        │
                          ┌─────────────┼─────────────┐
                          │             │             │
                   ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
                   │ Postgres│  │  Redis  │  │ External│
                   │         │  │(optional)│  │  APIs   │
                   └─────────┘  └─────────┘  └─────────┘
```
