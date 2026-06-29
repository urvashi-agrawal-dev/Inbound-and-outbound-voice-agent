# API Examples

## Health Check

**Request:**
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Karta SDR",
  "version": "1.0.0",
  "active_sessions": 2
}
```

---

## Create Call

**Request:**
```http
POST /api/v1/calls
Content-Type: application/json

{
  "phone_number": "+15551234567",
  "metadata": {
    "source": "website_form",
    "campaign": "q1_inbound"
  }
}
```

**Response:**
```json
{
  "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "external_call_id": "vapi-call-abc123",
  "provider": "vapi",
  "status": "queued",
  "connection": null
}
```

---

## Process Utterance (Text)

**Request:**
```http
POST /api/v1/calls/a1b2c3d4-e5f6-7890-abcd-ef1234567890/utterance
Content-Type: application/json

{
  "text": "Hi, my name is Sarah Johnson. I run a SaaS company called TechFlow with about 75 employees.",
  "interrupted": false
}
```

**Response:**
```json
{
  "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "response_text": "Great to meet you, Sarah! TechFlow sounds like an exciting company. I'd love to learn more about your call operations. Do you have about 5 minutes for a quick chat?",
  "state": "PERMISSION",
  "lead_data": {
    "name": "Sarah Johnson",
    "company_name": "TechFlow",
    "industry": "SaaS",
    "employee_count": 75,
    "monthly_inbound_calls": null,
    "monthly_outbound_calls": null,
    "existing_solution": null,
    "pain_points": [],
    "budget_range": null,
    "timeline": null,
    "email": null,
    "phone": null,
    "permission_to_continue": null,
    "wants_human": false,
    "booking_scheduled": false
  },
  "scoring": null,
  "latency_ms": 342.5,
  "should_end": false,
  "should_book": false,
  "human_handoff": false,
  "audio_url": null
}
```

---

## Process Utterance (With Interruption)

**Request:**
```http
POST /api/v1/calls/a1b2c3d4-e5f6-7890-abcd-ef1234567890/utterance
Content-Type: application/json

{
  "text": "Actually, how much does your platform cost?",
  "interrupted": true
}
```

**Response:**
```json
{
  "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "response_text": "Great question! Our plans start at $499 per month for up to 1,000 calls, with Growth at $1,999 and Enterprise at $9,999 plus. Now, to make sure I can recommend the right fit — what budget range are you working with for an AI voice solution?",
  "state": "FAQ_DETOUR",
  "lead_data": {
    "name": "Sarah Johnson",
    "company_name": "TechFlow",
    "industry": "SaaS",
    "employee_count": 75
  },
  "scoring": null,
  "latency_ms": 287.3,
  "should_end": false,
  "should_book": false,
  "human_handoff": false
}
```

---

## End Call

**Request:**
```http
POST /api/v1/calls/a1b2c3d4-e5f6-7890-abcd-ef1234567890/end
Content-Type: application/json

{
  "reason": "completed"
}
```

**Response:**
```json
{
  "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "summary": {
    "summary": "Qualified call with Sarah Johnson, VP Sales at TechFlow Inc (SaaS, 75 employees). Currently using manual SDR team with pain points around cost and inconsistent qualification. Monthly volume: 7,000 calls (5K inbound, 2K outbound). Budget: $2,000-$10,000/month. Timeline: 3 months. Lead scored 95/160 — Sales Qualified Lead. Demo booked for Tuesday 2pm.",
    "key_findings": [
      "Company: TechFlow Inc",
      "Size: 75 employees",
      "Call volume: 7000/month",
      "Pain points: high cost per lead, inconsistent qualification",
      "Score: 95 (Sales Qualified Lead)"
    ],
    "next_steps": [
      "Demo scheduled for 2026-06-30T14:00:00-04:00"
    ],
    "metrics": {
      "duration_seconds": 285.4,
      "turn_count": 18,
      "interruption_count": 1,
      "avg_latency_ms": 312.7,
      "estimated_cost_usd": 0.42
    }
  },
  "scoring": {
    "total_score": 95,
    "tier": "Sales Qualified Lead",
    "breakdown": {
      "company_size": 25,
      "call_volume": 20,
      "budget": 30,
      "timeline": 20
    },
    "qualified_for_booking": true
  },
  "metrics": {
    "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "duration_seconds": 285.4,
    "turn_count": 18,
    "interruption_count": 1,
    "avg_latency_ms": 312.7,
    "completion_percentage": 100.0,
    "final_state": "END_CALL",
    "tokens_used": 4250,
    "estimated_cost_usd": 0.42
  }
}
```

---

## Get Call Details

**Request:**
```http
GET /api/v1/calls/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "external_call_id": "vapi-call-abc123",
  "phone_number": "+15551234567",
  "provider": "vapi",
  "status": "completed",
  "current_state": "END_CALL",
  "duration_seconds": 285.4,
  "transcript": "Agent: Hi there! This is Alex from Karta SDR...\nCaller: Hi, I'm Sarah Johnson...",
  "summary": "Qualified call with Sarah Johnson...",
  "lead_data": { "name": "Sarah Johnson", "company_name": "TechFlow Inc" },
  "scoring": { "total_score": 95, "tier": "Sales Qualified Lead" },
  "qualified": true,
  "booked": true,
  "human_handoff": false,
  "cost_usd": 0.42,
  "avg_latency_ms": 312.7,
  "created_at": "2026-06-27T10:00:00Z",
  "ended_at": "2026-06-27T10:04:45Z"
}
```

---

## Analytics Dashboard

**Request:**
```http
GET /api/v1/analytics/dashboard?days=30
```

**Response:**
```json
{
  "metrics": {
    "total_calls": 147,
    "qualification_rate": 34.0,
    "booking_rate": 18.4,
    "avg_duration_seconds": 245.3,
    "avg_latency_ms": 328.7,
    "completion_rate": 72.1,
    "drop_off_stages": {
      "PERMISSION": 12,
      "COMPANY_INFO": 8,
      "BUDGET": 15,
      "TIMELINE": 6
    },
    "cost_per_conversation": 0.38,
    "active_sessions": 3
  },
  "time_series": [
    {
      "date": "2026-06-27",
      "calls": 8,
      "qualified": 3,
      "booked": 2,
      "avg_latency_ms": 305.2
    }
  ],
  "recent_calls": []
}
```

---

## Book Demo Meeting

**Request:**
```http
POST /api/v1/webhooks/booking
Content-Type: application/json

{
  "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "attendee_email": "sarah@techflow.io",
  "attendee_name": "Sarah Johnson",
  "company_name": "TechFlow Inc",
  "preferred_time": "2026-06-30T14:00:00-04:00"
}
```

**Response:**
```json
{
  "status": "booked",
  "event_id": "google-cal-event-xyz789",
  "start": "2026-06-30T14:00:00-04:00",
  "end": "2026-06-30T14:30:00-04:00",
  "html_link": "https://calendar.google.com/calendar/event?eid=..."
}
```

---

## List Leads

**Request:**
```http
GET /api/v1/leads?tier=Sales%20Qualified%20Lead&limit=10
```

**Response:**
```json
[
  {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "call_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Sarah Johnson",
    "company_name": "TechFlow Inc",
    "industry": "SaaS",
    "employee_count": 75,
    "email": "sarah@techflow.io",
    "phone": null,
    "lead_score": 95,
    "lead_tier": "Sales Qualified Lead",
    "crm_synced": true,
    "created_at": "2026-06-27T10:04:45Z"
  }
]
```

---

## Error Responses

**404 — Call Not Found:**
```json
{
  "detail": "Call not found"
}
```

**400 — Booking Failed:**
```json
{
  "detail": "No available slots"
}
```

**401 — Invalid Webhook:**
```json
{
  "detail": "Invalid webhook signature"
}
```
