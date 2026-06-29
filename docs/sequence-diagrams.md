# Sequence Diagrams

## 1. Inbound Call Lifecycle

```mermaid
sequenceDiagram
    participant Caller
    participant Vapi as Vapi/LiveKit
    participant API as FastAPI Backend
    participant STT as Whisper STT
    participant FSM as Conversation Engine
    participant LLM as Gemini LLM
    participant TTS as Edge TTS
    participant DB as PostgreSQL
    participant CRM as Google Sheets

    Caller->>Vapi: Inbound call connected
    Vapi->>API: POST /webhooks/vapi/events (call.started)
    API->>FSM: Create session (INTRO state)
    FSM->>LLM: Generate opening message
    LLM-->>FSM: "Hi, this is Alex from Karta SDR..."
    FSM->>TTS: Synthesize speech
    TTS-->>Vapi: Audio stream
    Vapi-->>Caller: Agent speaks

    loop Qualification Loop
        Caller->>Vapi: Speaks
        Vapi->>API: POST /webhooks/vapi/events (transcript)
        API->>STT: Transcribe (if audio)
        STT-->>API: Text transcript
        API->>FSM: process_utterance(text)
        FSM->>LLM: Extract fields + generate response
        LLM-->>FSM: Structured data + response text
        FSM->>FSM: Evaluate FSM transition
        FSM->>TTS: Synthesize response
        TTS-->>Vapi: Audio stream
        Vapi-->>Caller: Agent speaks
    end

    Caller->>Vapi: Hangs up / call ends
    Vapi->>API: POST /webhooks/vapi/events (end-of-call)
    API->>FSM: End session
    FSM->>LLM: Generate call summary
    LLM-->>FSM: Summary text
    API->>DB: Save call record + lead
    API->>CRM: Create lead record
    CRM-->>API: Confirmation
```

## 2. Barge-In / Interruption Handling

```mermaid
sequenceDiagram
    participant Caller
    participant VAD as Voice Activity Detection
    participant IH as Interruption Handler
    participant TTS as Edge TTS
    participant FSM as Conversation Engine

    Note over TTS: Agent is speaking
    TTS->>Caller: Audio playback active

    Caller->>VAD: Starts speaking (barge-in)
    VAD->>IH: on_speech_start()
    
    alt Barge-in enabled & agent speaking
        IH->>IH: Set INTERRUPTED state
        IH->>TTS: Cancel event triggered
        TTS--xCaller: Playback stops (within 300ms)
    end

    Caller->>VAD: Stops speaking
    VAD->>IH: on_speech_end(transcript)
    IH->>FSM: process_utterance(text, interrupted=true)
    FSM-->>Caller: "Sorry, go ahead..." + continue flow
```

## 3. FAQ Detour and Return

```mermaid
sequenceDiagram
    participant Caller
    participant FSM as FSM Engine
    participant FAQ as FAQ Handler
    participant LLM as Gemini LLM

    Note over FSM: Current state: BUDGET
    Caller->>FSM: "How much does your platform cost?"
    FSM->>FSM: detect_intent() → "faq"
    FSM->>FSM: Save previous state (BUDGET)
    FSM->>FAQ: build_faq_prompt(question, return_state=BUDGET)
    FAQ->>LLM: Generate FAQ answer + transition
    LLM-->>FAQ: "Our plans start at $499/mo... Now, regarding budget..."
    FAQ-->>Caller: Response

    Note over FSM: FAQ turn count < max (3)
    Caller->>FSM: "What about integrations?"
    FSM->>FAQ: Answer + transition
    FAQ-->>Caller: Response

    Note over FSM: FAQ turn count >= max
    FSM->>FSM: Return to BUDGET state
    FSM-->>Caller: "So, what budget range are you working with?"
```

## 4. Lead Scoring and Booking

```mermaid
sequenceDiagram
    participant FSM as FSM Engine
    participant Scorer as Lead Scorer
    participant LLM as Gemini LLM
    participant Cal as Google Calendar
    participant CRM as Google Sheets
    participant DB as PostgreSQL

    Note over FSM: All qualification states complete
    FSM->>Scorer: score(lead_data)
    Scorer-->>FSM: Score: 95, Tier: SQL

    alt Score > 40 (Qualified)
        FSM->>LLM: Generate booking offer
        LLM-->>FSM: "I'd love to schedule a demo..."
        FSM->>Cal: get_available_slots()
        Cal-->>FSM: Available times
        FSM-->>Caller: Offer time slots

        Caller->>FSM: "Tuesday at 2pm works"
        FSM->>Cal: book_meeting(email, time)
        Cal-->>FSM: Event created
        FSM->>DB: Update lead (booked=true)
        FSM->>CRM: Sync with booking details
    else Score <= 40 (Unqualified)
        FSM->>LLM: Generate polite close
        LLM-->>FSM: "Thank you for your time..."
    end
```

## 5. Post-Call Processing

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant Session as Session Store
    participant Summary as Summary Service
    participant LLM as Gemini LLM
    participant DB as PostgreSQL
    participant CRM as Google Sheets

    API->>Session: remove_session(call_id)
    Session-->>API: ConversationManager (with full memory)

    API->>Summary: generate_summary(transcript, lead_data, scoring)
    Summary->>LLM: Generate CRM summary
    LLM-->>Summary: Summary text + key findings

    API->>DB: Update CallRecord (transcript, summary, metrics)
    API->>DB: Create LeadRecord

    API->>CRM: create_lead_record(call_id, data, summary)
    CRM-->>API: Row appended

    API-->>API: Return call completion response
```

## 6. Analytics Dashboard Data Flow

```mermaid
sequenceDiagram
    participant UI as React Dashboard
    participant API as FastAPI
    participant DB as PostgreSQL

    UI->>API: GET /analytics/dashboard?days=30
    API->>DB: Query completed calls (last 30 days)
    DB-->>API: Call records

    API->>API: Compute metrics
    Note over API: qualification_rate, booking_rate,<br/>avg_latency, drop_off_stages,<br/>cost_per_conversation

    API->>API: Build time series (daily buckets)
    API->>DB: Query recent calls (limit 10)
    DB-->>API: Recent call records

    API-->>UI: AnalyticsResponse JSON
    UI->>UI: Render metrics cards, charts, table
```
