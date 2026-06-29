import { useEffect, useRef, useCallback, useState } from 'react'
import { createCallWebSocket, fetchCallLive } from '../api/client'

export function useCallWebSocket(callId, enabled, onUpdate) {
  const wsRef = useRef(null)
  const onUpdateRef = useRef(onUpdate)
  onUpdateRef.current = onUpdate
  const [wsStatus, setWsStatus] = useState('idle')
  const [connectionQuality, setConnectionQuality] = useState('offline')

  const handleMessage = useCallback((msg) => {
    if (msg.data) {
      onUpdateRef.current(msg.data, msg.event)
    }
  }, [])

  useEffect(() => {
    if (!callId || !enabled) {
      setWsStatus('idle')
      setConnectionQuality('offline')
      return
    }

    fetchCallLive(callId)
      .then((data) => onUpdateRef.current(data, 'initial'))
      .catch(console.warn)

    wsRef.current = createCallWebSocket(callId, {
      onMessage: handleMessage,
      onError: console.warn,
      onStatusChange: (status) => {
        setWsStatus(status)
        setConnectionQuality(wsRef.current?.getQuality?.() || 'offline')
      },
    })

    const qualityTimer = setInterval(() => {
      setConnectionQuality(wsRef.current?.getQuality?.() || 'offline')
    }, 5000)

    return () => {
      clearInterval(qualityTimer)
      wsRef.current?.close()
    }
  }, [callId, enabled, handleMessage])

  return { wsStatus, connectionQuality }
}
