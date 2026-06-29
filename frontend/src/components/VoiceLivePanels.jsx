import { useEffect, useRef } from 'react'
import { FSM_FLOW } from '../config'

export function StateVisualization({ currentState }) {
  const idx = FSM_FLOW.indexOf(currentState)

  return (
    <div className="state-viz">
      <h3>Current State</h3>
      <div className="current-state-badge">{currentState || 'INTRO'}</div>
      <div className="state-flow">
        {FSM_FLOW.map((state, i) => (
          <div
            key={state}
            className={`state-step ${i < idx ? 'done' : ''} ${i === idx ? 'active' : ''}`}
            title={state}
          >
            <span className="state-dot" />
            <span className="state-label">{state.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function QualificationChecklist({ checklist = [] }) {
  return (
    <div className="qualification-checklist">
      <h3>Qualification Progress</h3>
      <ul>
        {checklist.map((item) => (
          <li key={item.state} className={item.complete ? 'complete' : ''}>
            <span className="check">{item.complete ? '✓' : '□'}</span>
            {item.label}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function LeadScoreCard({ scoring, compact = false }) {
  if (!scoring) {
    return (
      <div className="lead-score-card empty">
        <h3>{compact ? 'Score' : 'Lead Score'}</h3>
        <p className="score-placeholder">Collecting data…</p>
      </div>
    )
  }

  const tierClass = (scoring.tier || '').toLowerCase().replace(/\s+/g, '-')

  return (
    <div className={`lead-score-card tier-${tierClass}`}>
      <h3>{compact ? 'Live Score' : 'Lead Score'}</h3>
      <div className="score-value">{scoring.total_score}</div>
      <div className="score-tier">{scoring.tier}</div>
      {scoring.breakdown && (
        <div className="score-breakdown">
          {Object.entries(scoring.breakdown).map(([k, v]) => (
            <span key={k}>{k.replace('_', ' ')}: {v}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export function QualificationResult({ scoring, summary }) {
  if (!scoring) return null

  const action = summary?.recommended_action ||
    (scoring.qualified_for_booking ? 'Schedule Demo' : 'Review lead')

  return (
    <div className="qualification-result">
      <h3>Qualification Result</h3>
      <div className="result-grid">
        <div>
          <span className="result-label">Lead Score</span>
          <span className="result-value">{scoring.total_score}</span>
        </div>
        <div>
          <span className="result-label">Qualification</span>
          <span className="result-value">{scoring.tier}</span>
        </div>
        <div className="result-full">
          <span className="result-label">Recommended Action</span>
          <span className="result-action">{action}</span>
        </div>
      </div>
    </div>
  )
}

export function LiveMetrics({ live }) {
  if (!live) return null
  return (
    <div className="live-metrics">
      <h3>Live Metrics</h3>
      <div className="metrics-row">
        <div className="metric-mini">
          <span>Duration</span>
          <strong>{Math.round(live.duration_seconds || 0)}s</strong>
        </div>
        <div className="metric-mini">
          <span>Cost</span>
          <strong>${(live.cost_usd || 0).toFixed(4)}</strong>
        </div>
        <div className="metric-mini">
          <span>Avg Latency</span>
          <strong>{live.avg_latency_ms || 0}ms</strong>
        </div>
        <div className="metric-mini">
          <span>Tokens</span>
          <strong>{live.tokens_used || 0}</strong>
        </div>
      </div>
    </div>
  )
}

export function TranscriptPanel({ transcript = [] }) {
  const endRef = useRef(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript.length])

  return (
    <div className="transcript-panel">
      <h3>Live Transcript</h3>
      <div className="transcript-body">
        {transcript.length === 0 && (
          <p className="transcript-empty">Transcript will appear when the call starts…</p>
        )}
        {transcript.map((entry, i) => (
          <div key={i} className={`transcript-line role-${entry.role}`}>
            <span className="transcript-speaker">
              {entry.role === 'user' ? 'Lead' : 'AI'}:
            </span>
            <span className="transcript-text">{entry.text}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}

export function CallSummaryPanel({ summary, visible }) {
  if (!visible || !summary) return null

  return (
    <div className="call-summary-panel">
      <h3>Call Summary</h3>
      {summary.summary && <p className="summary-text">{summary.summary}</p>}
      {summary.key_findings?.length > 0 && (
        <div className="summary-section">
          <h4>Key Findings</h4>
          <ul>
            {summary.key_findings.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}
      {summary.next_steps?.length > 0 && (
        <div className="summary-section">
          <h4>Next Steps</h4>
          <ul>
            {summary.next_steps.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
