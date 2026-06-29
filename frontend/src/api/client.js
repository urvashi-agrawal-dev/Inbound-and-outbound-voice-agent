import { getApiBase, getWsBase } from '../config'

const API = getApiBase()

export async function fetchDashboard(days = 30) {
  const res = await fetch(`${API}/analytics/dashboard?days=${days}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function createCall(metadata = {}) {
  const res = await fetch(`${API}/calls`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ metadata: { ...metadata, source: 'voice-live' } }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function endCall(callId, reason = 'completed') {
  const res = await fetch(`${API}/calls/${callId}/end`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

/** Sync user speech to backend FSM — returns state, score, qualified */
export async function sendTranscript(callId, text, { speaker = 'user', interrupted = false, vapiMode = true } = {}) {
  const res = await fetch(`${API}/vapi/transcript`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      call_id: callId,
      speaker,
      text,
      interrupted,
      vapi_mode: vapiMode,
    }),
  })
  if (!res.ok) throw new Error(`Transcript error: ${res.status}`)
  return res.json()
}

/** Log assistant transcript for analytics (no FSM processing) */
export async function sendAssistantTranscript(callId, text) {
  return sendTranscript(callId, text, { speaker: 'assistant', vapiMode: true })
}

export async function sendVapiEvent(callId, eventType, payload = {}) {
  const res = await fetch(`${API}/vapi/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ call_id: callId, event_type: eventType, payload }),
  })
  if (!res.ok) throw new Error(`Event error: ${res.status}`)
  return res.json()
}

export async function fetchCallLive(callId) {
  const res = await fetch(`${API}/calls/${callId}/live`)
  if (!res.ok) throw new Error(`Live fetch error: ${res.status}`)
  return res.json()
}

export async function fetchCallSummary(callId) {
  const res = await fetch(`${API}/calls/${callId}/summary`)
  if (!res.ok) throw new Error(`Summary error: ${res.status}`)
  return res.json()
}

export function createCallWebSocket(callId, { onMessage, onError, onStatusChange }) {
  const wsBase = getWsBase()
  const url = `${wsBase}/ws/calls/${callId}`
  let ws = null
  let reconnectAttempts = 0
  let closed = false
  let pingInterval = null
  let lastPong = Date.now()

  const setStatus = (status) => onStatusChange?.(status, { lastPong, reconnectAttempts })

  const connect = () => {
    setStatus(reconnectAttempts > 0 ? 'reconnecting' : 'connecting')
    ws = new WebSocket(url)

    ws.onopen = () => {
      reconnectAttempts = 0
      lastPong = Date.now()
      setStatus('connected')
      pingInterval = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 25000)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.event === 'pong') {
          lastPong = Date.now()
          return
        }
        onMessage?.(msg)
      } catch (e) {
        console.warn('WS parse error', e)
      }
    }

    ws.onerror = (err) => {
      setStatus('error')
      onError?.(err)
    }

    ws.onclose = () => {
      clearInterval(pingInterval)
      if (!closed && reconnectAttempts < 5) {
        reconnectAttempts += 1
        setStatus('reconnecting')
        setTimeout(connect, Math.min(1000 * reconnectAttempts, 5000))
      } else if (!closed) {
        setStatus('disconnected')
      }
    }
  }

  connect()

  return {
    close: () => {
      closed = true
      clearInterval(pingInterval)
      ws?.close()
      setStatus('disconnected')
    },
    getQuality: () => {
      const age = Date.now() - lastPong
      if (ws?.readyState !== WebSocket.OPEN) return 'offline'
      if (age < 30000) return 'excellent'
      if (age < 60000) return 'good'
      return 'degraded'
    },
  }
}

/** Request microphone permission before starting Vapi */
export async function requestMicrophonePermission() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Microphone not supported in this browser')
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })
  // Release preview stream — Vapi SDK will acquire its own
  stream.getTracks().forEach((t) => t.stop())
  return true
}
