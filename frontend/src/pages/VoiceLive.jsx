import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import VoiceAgent from '../components/VoiceAgent'
import {
  StateVisualization,
  QualificationChecklist,
  LeadScoreCard,
  QualificationResult,
  LiveMetrics,
  TranscriptPanel,
  CallSummaryPanel,
} from '../components/VoiceLivePanels'
import { useCallWebSocket } from '../hooks/useCallWebSocket'
import { createCall, endCall, fetchCallSummary } from '../api/client'
import { QUALIFICATION_STATES } from '../config'

const DEFAULT_LIVE = {
  current_state: 'INTRO',
  transcript: [],
  qualification_checklist: QUALIFICATION_STATES.map((s) => ({
    ...s,
    complete: false,
  })),
  scoring: null,
  duration_seconds: 0,
  cost_usd: 0,
  avg_latency_ms: 0,
  tokens_used: 0,
}

const WS_LABELS = {
  idle: 'WebSocket Idle',
  connecting: 'WebSocket Connecting',
  connected: 'WebSocket Connected',
  reconnecting: 'WebSocket Reconnecting',
  disconnected: 'WebSocket Disconnected',
  error: 'WebSocket Error',
}

const QUALITY_LABELS = {
  excellent: 'Excellent',
  good: 'Good',
  degraded: 'Degraded',
  offline: 'Offline',
}

export default function VoiceLive() {
  const [callId, setCallId] = useState(null)
  const [live, setLive] = useState(DEFAULT_LIVE)
  const [callActive, setCallActive] = useState(false)
  const [callEnded, setCallEnded] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [mode, setMode] = useState('idle')

  useEffect(() => {
    createCall({ channel: 'voice-live-dashboard' })
      .then((res) => setCallId(res.call_id))
      .catch((e) => setError(e.message))
  }, [])

  const handleLiveUpdate = useCallback((data, event) => {
    setLive((prev) => {
      const mergedTranscript = data.transcript?.length
        ? data.transcript
        : prev.transcript
      return {
        ...prev,
        ...data,
        transcript: mergedTranscript,
        scoring: data.scoring ?? prev.scoring,
        current_state: data.current_state ?? prev.current_state,
        qualification_checklist: data.qualification_checklist ?? prev.qualification_checklist,
      }
    })
  }, [])

  const { wsStatus, connectionQuality } = useCallWebSocket(callId, Boolean(callId), handleLiveUpdate)

  const handleBackendSync = useCallback((data) => {
    setLive((prev) => ({
      ...prev,
      current_state: data.state ?? prev.current_state,
      scoring: data.scoring ?? (data.score != null ? {
        total_score: data.score,
        tier: data.tier,
        qualified_for_booking: data.qualified,
      } : prev.scoring),
      qualification_checklist: data.qualification_checklist ?? prev.qualification_checklist,
      lead_data: data.lead_data ?? prev.lead_data,
    }))
  }, [])

  const handleTranscript = useCallback((entry) => {
    setLive((prev) => {
      const exists = prev.transcript.some(
        (t) => t.role === entry.role && t.text === entry.text,
      )
      if (exists) return prev
      return {
        ...prev,
        transcript: [
          ...prev.transcript,
          {
            role: entry.role,
            text: entry.text,
            timestamp: new Date().toISOString(),
          },
        ],
        current_state: entry.state || prev.current_state,
      }
    })
  }, [])

  const handleCallEnd = useCallback(async () => {
    setCallActive(false)
    setCallEnded(true)
    if (!callId) return
    try {
      const endResult = await endCall(callId)
      setSummary(endResult.summary ? {
        summary: endResult.summary.summary,
        key_findings: endResult.summary.key_findings,
        next_steps: endResult.summary.next_steps,
        recommended_action: endResult.scoring?.qualified_for_booking
          ? 'Schedule Demo'
          : 'Review lead',
        scoring: endResult.scoring,
      } : null)
      if (endResult.scoring) {
        setLive((prev) => ({ ...prev, scoring: endResult.scoring }))
      }
    } catch {
      const s = await fetchCallSummary(callId)
      setSummary(s)
      if (s.scoring) {
        setLive((prev) => ({ ...prev, scoring: s.scoring }))
      }
    }
  }, [callId])

  return (
    <div className="voice-live-page">
      <header className="dashboard-header">
        <div>
          <h1>Karta SDR</h1>
          <p className="subtitle">Live Voice Operations</p>
        </div>
        <nav className="top-nav">
          <Link to="/">Analytics</Link>
          <Link to="/voice-live" className="active">Live Voice</Link>
        </nav>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button type="button" className="error-dismiss" onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="connection-bar">
        <span className={`ws-badge ws-${wsStatus}`}>{WS_LABELS[wsStatus] || wsStatus}</span>
        <span className={`quality-badge quality-${connectionQuality}`}>
          Connection: {QUALITY_LABELS[connectionQuality] || connectionQuality}
        </span>
      </div>

      <div className="voice-live-grid">
        <section className="voice-live-col controls-col">
          <div className="chart-card">
            <VoiceAgent
              callId={callId}
              onCallStart={() => { setCallActive(true); setCallEnded(false); setSummary(null); setError(null) }}
              onCallEnd={handleCallEnd}
              onTranscript={handleTranscript}
              onBackendSync={handleBackendSync}
              onModeChange={setMode}
              onError={(e) => setError(String(e))}
            />
          </div>
          <div className="chart-card">
            <StateVisualization currentState={live.current_state} />
          </div>
          <div className="chart-card">
            <LeadScoreCard scoring={live.scoring} compact />
          </div>
          <div className="chart-card">
            <LiveMetrics live={live} />
          </div>
        </section>

        <section className="voice-live-col transcript-col">
          <div className="chart-card full-height">
            <TranscriptPanel transcript={live.transcript} />
          </div>
        </section>

        <section className="voice-live-col side-col">
          <div className="chart-card">
            <QualificationChecklist checklist={live.qualification_checklist} />
          </div>
          {(callEnded || live.scoring) && (
            <div className="chart-card">
              <QualificationResult scoring={live.scoring} summary={summary} />
            </div>
          )}
          <div className="chart-card">
            <CallSummaryPanel summary={summary} visible={callEnded} />
          </div>
        </section>
      </div>

      {mode === 'demo' && callActive && (
        <div className="demo-banner">
          Vapi connection failed — running demo fallback with live FSM and scoring updates.
        </div>
      )}
    </div>
  )
}
