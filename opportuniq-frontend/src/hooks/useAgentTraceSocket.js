import { useEffect, useRef, useState } from 'react'
import { buildEventKey } from '../utils/agentTrace'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
const RECONNECT_DELAY_MS = 2000

export function useAgentTraceSocket(sessionId, isOpen) {
  const [events, setEvents] = useState([])
  const [connectionStatus, setConnectionStatus] = useState('idle')
  const seenKeysRef = useRef(new Set())

  const [lastSessionId, setLastSessionId] = useState(sessionId)
  if (sessionId !== lastSessionId) {
    setLastSessionId(sessionId)
    setEvents([])
  }

  useEffect(() => {
    seenKeysRef.current = new Set()
  }, [sessionId])

  useEffect(() => {
    if (!sessionId || !isOpen) return undefined

    let cancelled = false
    let socket = null
    let reconnectTimeoutId = null
    let closedIntentionally = false

    function connect() {
      if (cancelled) return

      closedIntentionally = false
      socket = new WebSocket(
        `${WS_BASE_URL}/ws/agent-trace?session_id=${encodeURIComponent(sessionId)}`,
      )

      socket.onopen = () => {
        if (!cancelled) setConnectionStatus('connected')
      }

      socket.onmessage = (messageEvent) => {
        if (cancelled) return

        let payload
        try {
          payload = JSON.parse(messageEvent.data)
        } catch {
          return
        }

        const key = buildEventKey(payload)
        if (seenKeysRef.current.has(key)) return
        seenKeysRef.current.add(key)
        setEvents((prev) => [...prev, payload])
      }

      socket.onerror = () => {
        socket?.close()
      }

      socket.onclose = () => {
        if (cancelled || closedIntentionally) return
        setConnectionStatus('reconnecting')
        reconnectTimeoutId = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()

    return () => {
      cancelled = true
      closedIntentionally = true
      if (reconnectTimeoutId) clearTimeout(reconnectTimeoutId)
      socket?.close()
    }
  }, [sessionId, isOpen])

  return {
    events,
    connectionStatus: !sessionId || !isOpen ? 'idle' : connectionStatus,
  }
}
