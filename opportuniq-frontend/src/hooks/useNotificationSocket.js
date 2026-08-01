import { useEffect } from 'react'
import { notificationFromSocketPayload } from '../utils/notifications'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
const RECONNECT_DELAY_MS = 2000

export function useNotificationSocket(profileId, onNotification) {
  useEffect(() => {
    if (!profileId) return undefined

    let cancelled = false
    let socket = null
    let reconnectTimeoutId = null

    function connect() {
      if (cancelled) return

      socket = new WebSocket(
        `${WS_BASE_URL}/ws/agent-trace?session_id=${encodeURIComponent(profileId)}`,
      )

      socket.onmessage = (messageEvent) => {
        if (cancelled) return

        let payload
        try {
          payload = JSON.parse(messageEvent.data)
        } catch {
          return
        }

        const notification = notificationFromSocketPayload(payload)
        if (notification) onNotification(notification)
      }

      socket.onerror = () => {
        socket?.close()
      }

      socket.onclose = () => {
        if (cancelled) return
        reconnectTimeoutId = window.setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()

    return () => {
      cancelled = true
      if (reconnectTimeoutId) window.clearTimeout(reconnectTimeoutId)
      socket?.close()
    }
  }, [profileId, onNotification])
}
