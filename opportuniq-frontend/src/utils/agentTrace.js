const AGENT_LABELS = {
  profile: 'Profile Agent',
  jobspy: 'JobSpy Search',
  tavily: 'Tavily Search',
  groq: 'Structured Extraction',
  ranker: 'Deduplication & Ranking',
  persistence: 'Persistence',
  pipeline: 'Pipeline',
  cache: 'Cache',
}

function toTitleCase(value) {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function getAgentLabel(agent) {
  if (!agent) return 'Agent'
  return AGENT_LABELS[agent.trim().toLowerCase()] ?? toTitleCase(agent)
}

export function getStatusTone(status) {
  const normalized = (status || '').trim().toLowerCase()
  if (normalized === 'error') return 'red'
  if (normalized === 'complete' || normalized === 'completed') return 'green'
  return 'blue'
}

// The backend only ever tags the pipeline's own final success/failure event
// with agent "pipeline" — every intermediate step (profile, jobspy, tavily,
// groq, ranker, persistence...) uses its own agent name, so this is the
// reliable signal that the whole run has finished (not just one step).
export function isTerminalCompletion(event) {
  if (!event) return false
  const status = (event.status || '').trim().toLowerCase()
  const agent = (event.agent || '').trim().toLowerCase()
  return agent === 'pipeline' && (status === 'complete' || status === 'completed')
}

export function formatEventTimestamp(timestamp) {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatElapsed(ms) {
  if (!Number.isFinite(ms) || ms < 0) return '0s'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes === 0) return `${seconds}s`
  return `${minutes}m ${String(seconds).padStart(2, '0')}s`
}

export function buildEventKey(event) {
  return `${event?.timestamp}|${event?.agent}|${event?.status}|${event?.message}`
}
