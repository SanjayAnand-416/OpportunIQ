import { Activity, AlertCircle, CheckCircle2, Loader2, Timer, WifiOff, X } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'
import { useAgentTraceSocket } from '../../hooks/useAgentTraceSocket'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import {
  formatElapsed,
  formatEventTimestamp,
  getAgentLabel,
  getStatusTone,
  isTerminalCompletion,
} from '../../utils/agentTrace'

const AUTO_HIDE_DELAY_MS = 3000

function StatusIcon({ status }) {
  const normalized = (status || '').trim().toLowerCase()

  if (normalized === 'error') {
    return <AlertCircle size={16} aria-hidden="true" />
  }
  if (normalized === 'complete' || normalized === 'completed') {
    return <CheckCircle2 size={16} aria-hidden="true" />
  }
  return <Loader2 size={16} className="trace-icon-spin" aria-hidden="true" />
}

function TraceRow({ event, startTime }) {
  const tone = getStatusTone(event.status)
  const eventTime = new Date(event.timestamp).getTime()
  const elapsedMs =
    Number.isFinite(eventTime) && Number.isFinite(startTime) ? eventTime - startTime : 0

  return (
    <li className={`trace-row tone-${tone}`}>
      <span className={`trace-row-icon tone-${tone}`} aria-hidden="true">
        <StatusIcon status={event.status} />
      </span>
      <div className="trace-row-body">
        <div className="trace-row-top">
          <span className="trace-row-agent">{getAgentLabel(event.agent)}</span>
          <span className="trace-row-time">{formatEventTimestamp(event.timestamp)}</span>
        </div>
        <p className="trace-row-message">{event.message}</p>
        <span className="trace-row-elapsed">
          <Timer size={12} aria-hidden="true" />
          {formatElapsed(elapsedMs)}
        </span>
      </div>
    </li>
  )
}

export default function AgentTracePanel({ sessionId, isOpen, onComplete, onClose }) {
  const panelRef = useRef(null)
  const listEndRef = useRef(null)
  const completionTimeoutRef = useRef(null)
  const hasTriggeredCompletionRef = useRef(false)

  const { events, connectionStatus } = useAgentTraceSocket(sessionId, isOpen)

  useFocusTrap(panelRef, isOpen, onClose)

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [events.length])

  useEffect(() => {
    hasTriggeredCompletionRef.current = false
    if (completionTimeoutRef.current) {
      clearTimeout(completionTimeoutRef.current)
      completionTimeoutRef.current = null
    }
  }, [sessionId])

  useEffect(() => {
    if (hasTriggeredCompletionRef.current) return undefined

    const latestEvent = events[events.length - 1]
    if (!isTerminalCompletion(latestEvent)) return undefined

    hasTriggeredCompletionRef.current = true
    completionTimeoutRef.current = setTimeout(() => {
      onClose?.()
      onComplete?.()
    }, AUTO_HIDE_DELAY_MS)

    return () => {
      if (completionTimeoutRef.current) {
        clearTimeout(completionTimeoutRef.current)
        completionTimeoutRef.current = null
      }
    }
  }, [events, onClose, onComplete])

  const startTime = useMemo(() => {
    const first = events[0]
    if (!first) return null
    const parsed = new Date(first.timestamp).getTime()
    return Number.isFinite(parsed) ? parsed : null
  }, [events])

  return (
    <>
      <div
        className={`drawer-backdrop${isOpen ? ' drawer-backdrop-visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        ref={panelRef}
        className={`agent-trace-panel${isOpen ? ' agent-trace-panel-open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="trace-panel-title"
        aria-hidden={!isOpen}
        {...(!isOpen ? { inert: '' } : {})}
      >
        <header className="trace-header">
          <button
            type="button"
            className="drawer-close-btn"
            aria-label="Close agent pipeline panel"
            onClick={onClose}
          >
            <X size={20} aria-hidden="true" />
          </button>

          <div className="trace-header-top">
            <span className="trace-header-icon" aria-hidden="true">
              <Activity size={18} />
            </span>
            <div>
              <h2 id="trace-panel-title" className="trace-title">
                AI Agent Pipeline
              </h2>
              <p className="trace-subtitle">Real-time opportunity discovery progress</p>
            </div>
          </div>
        </header>

        <div className="trace-body">
          {connectionStatus === 'reconnecting' && (
            <div className="trace-connection-banner" role="status">
              <WifiOff size={16} aria-hidden="true" />
              <div>
                <p className="trace-connection-title">Connection lost</p>
                <p className="trace-connection-subtitle">Attempting to reconnect...</p>
              </div>
            </div>
          )}

          {events.length === 0 ? (
            <p className="trace-empty-state">Waiting for pipeline to start...</p>
          ) : (
            <ul className="trace-list">
              {events.map((event, index) => (
                <TraceRow
                  key={`${event.timestamp}-${event.agent}-${index}`}
                  event={event}
                  startTime={startTime}
                />
              ))}
              <li ref={listEndRef} aria-hidden="true" className="trace-scroll-anchor" />
            </ul>
          )}
        </div>
      </aside>
    </>
  )
}
