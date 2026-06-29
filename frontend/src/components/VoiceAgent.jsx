import { useCallback, useEffect, useRef, useState } from 'react'
import Vapi from '@vapi-ai/web'
import {
  requestMicrophonePermission,
  sendTranscript,
  sendAssistantTranscript,
  sendVapiEvent,
} from '../api/client'
import { getVapiConfig } from '../config'
import { runDemoCall } from '../hooks/useDemoCall'

const STATUS_LABELS = {
  idle: 'Ready',
  connecting: 'Connecting',
  connected: 'Connected',
  disconnected: 'Disconnected',
  error: 'Error',
}

const PUBLIC_KEY = import.meta.env.VITE_VAPI_PUBLIC_KEY
const ASSISTANT_ID = import.meta.env.VITE_VAPI_ASSISTANT_ID

export default function VoiceAgent({
  callId,
  onCallStart,
  onCallEnd,
  onSpeakingChange,
  onTranscript,
  onBackendSync,
  onError,
  onModeChange,
  onMicActiveChange,
}) {
  const [status, setStatus] = useState('idle')
  const [assistantSpeaking, setAssistantSpeaking] = useState(false)
  const [userSpeaking, setUserSpeaking] = useState(false)
  const [micActive, setMicActive] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [mode, setMode] = useState('idle')
  const vapiRef = useRef(null)
  const demoStopRef = useRef(null)
  const timerRef = useRef(null)
  const endingRef = useRef(false)
  const processedTranscriptsRef = useRef(new Set())
  const config = getVapiConfig()

  const updateMic = useCallback((active) => {
    setMicActive(active)
    onMicActiveChange?.(active)
  }, [onMicActiveChange])

  const updateSpeaking = useCallback((assistant, user) => {
    setAssistantSpeaking(assistant)
    setUserSpeaking(user)
    if (assistant) onSpeakingChange?.('assistant')
    else if (user) onSpeakingChange?.('user')
    else onSpeakingChange?.(null)
  }, [onSpeakingChange])

  const startTimer = useCallback(() => {
    const start = Date.now()
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)
  }, [])

  const stopTimer = useCallback(() => {
    clearInterval(timerRef.current)
  }, [])

  const transcriptKey = (role, text) => `${role}:${text.trim().toLowerCase()}`

  const handleTranscriptMessage = useCallback(async (message) => {
    if (!callId || message.type !== 'transcript') return

    const text = (message.transcript || message.text || '').trim()
    if (!text) return

    const isFinal = message.transcriptType === 'final' || message.transcriptType === undefined
    const role = message.role === 'user' ? 'user' : 'assistant'

    if (role === 'user' && !isFinal) {
      updateSpeaking(false, true)
      return
    }

    if (!isFinal) return

    const key = transcriptKey(role, text)
    if (processedTranscriptsRef.current.has(key)) return
    processedTranscriptsRef.current.add(key)

    updateSpeaking(false, false)
    onTranscript?.({ role, text })

    try {
      if (role === 'user') {
        const result = await sendTranscript(callId, text, { speaker: 'user', vapiMode: true })
        onBackendSync?.({
          state: result.state,
          score: result.score,
          qualified: result.qualified,
          tier: result.tier,
          scoring: result.score != null ? {
            total_score: result.score,
            tier: result.tier,
            qualified_for_booking: result.qualified,
          } : null,
          qualification_checklist: result.qualification_checklist,
          lead_data: result.lead_data,
        })
      } else {
        await sendAssistantTranscript(callId, text)
      }
    } catch (e) {
      console.warn('Backend sync failed', e)
      onError?.(e.message || String(e))
    }
  }, [callId, onBackendSync, onError, onTranscript, updateSpeaking])

  const destroyVapi = useCallback(() => {
    if (vapiRef.current) {
      try {
        vapiRef.current.stop()
      } catch {
        /* ignore */
      }
      vapiRef.current = null
    }
  }, [])

  const setupVapi = useCallback(() => {
    const publicKey = PUBLIC_KEY || config.publicKey
    const vapi = new Vapi(publicKey)
    vapiRef.current = vapi

    vapi.on('call-start', async () => {
      setStatus('connected')
      updateMic(true)
      startTimer()
      await sendVapiEvent(callId, 'call-start', {})
      onCallStart?.()
    })

    vapi.on('call-end', async () => {
      if (endingRef.current) return
      endingRef.current = true
      setStatus('disconnected')
      updateMic(false)
      updateSpeaking(false, false)
      stopTimer()
      await sendVapiEvent(callId, 'call-end', {})
      onCallEnd?.()
      endingRef.current = false
    })

    vapi.on('speech-start', async () => {
      setAssistantSpeaking(true)
      setUserSpeaking(false)
      onSpeakingChange?.('assistant')
      await sendVapiEvent(callId, 'speech-start', { role: 'assistant' })
    })

    vapi.on('speech-end', async () => {
      setAssistantSpeaking(false)
      onSpeakingChange?.(null)
      await sendVapiEvent(callId, 'speech-end', { role: 'assistant' })
    })

    vapi.on('message', (message) => {
      handleTranscriptMessage(message)
    })

    vapi.on('transcript', (message) => {
      handleTranscriptMessage(message)
    })

    vapi.on('error', async (err) => {
      console.error('Vapi error', err)
      setStatus('error')
      updateMic(false)
      onError?.(err?.message || String(err))
      await sendVapiEvent(callId, 'error', { message: String(err) })
    })

    return vapi
  }, [callId, config.publicKey, handleTranscriptMessage, onCallEnd, onCallStart, onError, onSpeakingChange, startTimer, stopTimer, updateMic, updateSpeaking])

  const startDemo = useCallback(() => {
    setMode('demo')
    onModeChange?.('demo')
    setStatus('connected')
    updateMic(true)
    startTimer()
    onCallStart?.()

    demoStopRef.current = runDemoCall({
      callId,
      onStep: (step) => onTranscript?.(step),
      onSpeakingChange: (role) => {
        updateSpeaking(role === 'assistant', role === 'user')
      },
      sendTranscript: (id, _role, text) => sendTranscript(id, text, { speaker: 'user' }).then((r) => {
        onBackendSync?.({
          state: r.state,
          score: r.score,
          qualified: r.qualified,
          tier: r.tier,
          scoring: { total_score: r.score, tier: r.tier, qualified_for_booking: r.qualified },
          qualification_checklist: r.qualification_checklist,
        })
        return r
      }),
      sendEvent: (type, payload) => sendVapiEvent(callId, type, payload),
      onComplete: () => {
        setStatus('disconnected')
        updateMic(false)
        updateSpeaking(false, false)
        stopTimer()
        onCallEnd?.()
      },
    })
  }, [callId, onBackendSync, onCallEnd, onCallStart, onModeChange, onTranscript, startTimer, stopTimer, updateMic, updateSpeaking])

  const startCall = useCallback(async () => {
    if (!callId) return

    if (!config.isConfigured) {
      onError?.('Vapi credentials not configured. Set VITE_VAPI_PUBLIC_KEY and VITE_VAPI_ASSISTANT_ID.')
      return
    }

    setElapsed(0)
    setStatus('connecting')
    endingRef.current = false
    processedTranscriptsRef.current.clear()
    await sendVapiEvent(callId, 'connecting', {})

    try {
      await requestMicrophonePermission()
    } catch (err) {
      setStatus('error')
      onError?.(`Microphone permission denied: ${err.message}`)
      return
    }

    try {
      setMode('vapi')
      onModeChange?.('vapi')
      destroyVapi()
      const vapi = setupVapi()
      const assistantId = ASSISTANT_ID || config.assistantId
      await vapi.start(assistantId, {
        metadata: { call_id: callId, source: 'karta-dashboard' },
      })
    } catch (err) {
      console.warn('Vapi connection failed, falling back to demo', err)
      destroyVapi()
      onError?.(`Vapi connection failed — switching to demo mode: ${err.message || err}`)
      startDemo()
    }
  }, [callId, config, destroyVapi, onError, onModeChange, setupVapi, startDemo])

  const endCall = useCallback(async () => {
    if (endingRef.current) return
    endingRef.current = true

    demoStopRef.current?.()
    demoStopRef.current = null

    if (vapiRef.current) {
      try {
        await vapiRef.current.stop()
      } catch (e) {
        console.warn('Vapi stop error', e)
      }
    }

    setStatus('disconnected')
    updateMic(false)
    updateSpeaking(false, false)
    stopTimer()
    await sendVapiEvent(callId, 'call-end', {})
    onCallEnd?.()
    endingRef.current = false
  }, [callId, onCallEnd, stopTimer, updateMic, updateSpeaking])

  useEffect(() => () => {
    demoStopRef.current?.()
    destroyVapi()
    stopTimer()
  }, [destroyVapi, stopTimer])

  const isActive = status === 'connected' || status === 'connecting'
  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60

  return (
    <div className="voice-agent">
      <div className="voice-agent-header">
        <div className="voice-status-row">
          <span className={`status-dot status-${status}`} />
          <span className="status-label">{STATUS_LABELS[status] || status}</span>
          {mode === 'vapi' && (
            <span className="mode-badge mode-vapi">Live (Vapi)</span>
          )}
          {mode === 'demo' && (
            <span className="mode-badge mode-demo">Demo Fallback</span>
          )}
        </div>
        <div className="call-timer">
          {mins}:{secs.toString().padStart(2, '0')}
        </div>
      </div>

      <div className="indicator-grid">
        <div className={`indicator ${micActive ? 'active' : ''}`}>
          <span className="indicator-icon">🎤</span>
          <span>{micActive ? 'Mic Active' : 'Mic Off'}</span>
        </div>
        <div className={`indicator ${assistantSpeaking ? 'active assistant' : ''}`}>
          <span className="indicator-icon">🤖</span>
          <span>{assistantSpeaking ? 'AI Speaking' : 'AI Idle'}</span>
        </div>
        <div className={`indicator ${userSpeaking ? 'active user' : ''}`}>
          <span className="indicator-icon">👤</span>
          <span>{userSpeaking ? 'You Speaking' : 'You Idle'}</span>
        </div>
      </div>

      <div className="voice-controls">
        {!isActive ? (
          <button
            type="button"
            className="btn btn-start"
            onClick={startCall}
            disabled={!callId || !config.isConfigured}
          >
            Start Call
          </button>
        ) : (
          <button type="button" className="btn btn-end" onClick={endCall}>
            End Call
          </button>
        )}
      </div>

      {!config.isConfigured && status === 'idle' && (
        <p className="voice-hint voice-hint-error">
          Set VITE_VAPI_PUBLIC_KEY and VITE_VAPI_ASSISTANT_ID to enable live voice.
        </p>
      )}
    </div>
  )
}
