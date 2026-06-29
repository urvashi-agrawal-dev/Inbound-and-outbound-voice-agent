/** Vapi and API configuration from environment variables. */

export function getVapiConfig() {
  const publicKey =
    import.meta.env.VITE_VAPI_PUBLIC_KEY ||
    import.meta.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY ||
    ''
  const assistantId =
    import.meta.env.VITE_VAPI_ASSISTANT_ID ||
    import.meta.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID ||
    ''

  return {
    publicKey,
    assistantId,
    isConfigured: Boolean(publicKey && assistantId && !publicKey.startsWith('your-')),
  }
}

export function getApiBase() {
  return import.meta.env.VITE_API_BASE || '/api/v1'
}

export function getWsBase() {
  const wsUrl = import.meta.env.VITE_WS_URL
  if (wsUrl) return wsUrl.replace(/\/$/, '')
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_WS_HOST || window.location.host
  return `${proto}//${host}`
}

export const QUALIFICATION_STATES = [
  { state: 'COMPANY_INFO', label: 'Company Information' },
  { state: 'CALL_VOLUME', label: 'Call Volume' },
  { state: 'CURRENT_PROCESS', label: 'Current Process' },
  { state: 'PAIN_POINTS', label: 'Pain Points' },
  { state: 'BUDGET', label: 'Budget' },
  { state: 'TIMELINE', label: 'Timeline' },
]

export const FSM_FLOW = [
  'INTRO', 'PERMISSION', 'COMPANY_INFO', 'CALL_VOLUME', 'CURRENT_PROCESS',
  'PAIN_POINTS', 'BUDGET', 'TIMELINE', 'LEAD_SCORING', 'BOOKING', 'END_CALL',
]

export function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function recommendedAction(scoring) {
  if (!scoring) return 'Continue qualification'
  if (scoring.qualified_for_booking) return 'Schedule Demo'
  if (scoring.tier === 'Warm Lead') return 'Add to nurture campaign'
  if (scoring.tier === 'Priority Enterprise Lead') return 'Priority sales follow-up'
  return 'Log and review'
}
