const MS_PER_DAY = 24 * 60 * 60 * 1000
const UPCOMING_WINDOW_DAYS = 7
export const DEFAULT_DEADLINE_TIME = '23:59'

export function calculateDaysLeft(deadlineDatetime) {
  const deadline = new Date(deadlineDatetime)
  if (Number.isNaN(deadline.getTime())) return null

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  deadline.setHours(0, 0, 0, 0)

  return Math.round((deadline.getTime() - today.getTime()) / MS_PER_DAY)
}

export function getUrgencyColor(daysLeft) {
  if (typeof daysLeft !== 'number' || Number.isNaN(daysLeft)) return 'gray'
  if (daysLeft <= 3) return 'red'
  if (daysLeft <= 7) return 'amber'
  return 'green'
}

function hasExplicitTime(rawValue) {
  return typeof rawValue === 'string' && rawValue.includes('T')
}

export function formatDeadlineTime(deadlineDatetime) {
  if (!hasExplicitTime(deadlineDatetime)) return null
  const date = new Date(deadlineDatetime)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

export function formatFullDate(deadlineDatetime) {
  const date = new Date(deadlineDatetime)
  if (Number.isNaN(date.getTime())) return 'Not available'
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function formatDeadlineDate(deadlineDatetime) {
  const date = new Date(deadlineDatetime)
  const daysLeft = calculateDaysLeft(deadlineDatetime)

  if (daysLeft === null || Number.isNaN(date.getTime())) {
    return { label: '', time: null }
  }

  let label
  if (daysLeft === 0) {
    label = 'Today'
  } else if (daysLeft === 1) {
    label = 'Tomorrow'
  } else if (daysLeft > 1 && daysLeft <= 6) {
    label = date.toLocaleDateString(undefined, { weekday: 'long' })
  } else {
    label = date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
  }

  return { label, time: formatDeadlineTime(deadlineDatetime) }
}

export function getDeadlineSummaryLine(deadlineDatetime) {
  const daysLeft = calculateDaysLeft(deadlineDatetime)
  if (daysLeft === null) return ''
  if (daysLeft < 0) return 'Overdue'

  const { label, time } = formatDeadlineDate(deadlineDatetime)

  if (daysLeft === 0 || daysLeft === 1) {
    return time ? `${label} • ${time}` : label
  }

  return `${daysLeft} days left`
}

export function isWithinUpcomingWindow(deadlineDatetime) {
  const daysLeft = calculateDaysLeft(deadlineDatetime)
  return daysLeft !== null && daysLeft >= 0 && daysLeft <= UPCOMING_WINDOW_DAYS
}

// Alias matching the calendar spec's requested helper name — same calculation,
// no need for a second implementation.
export const calculateDaysRemaining = calculateDaysLeft

const URGENCY_HEX = {
  red: { background: '#dc2626', border: '#b91c1c' },
  amber: { background: '#d97706', border: '#b45309' },
  green: { background: '#16a34a', border: '#15803d' },
  gray: { background: '#94a3b8', border: '#64748b' },
}

export function getDeadlineColor(daysLeft) {
  return URGENCY_HEX[getUrgencyColor(daysLeft)]
}

export function mapDeadlineToEvent(deadline) {
  const daysLeft = calculateDaysLeft(deadline.deadline_datetime)
  const { background, border } = getDeadlineColor(daysLeft)

  return {
    id: String(deadline.id),
    title: deadline.title,
    start: deadline.deadline_datetime,
    backgroundColor: background,
    borderColor: border,
    extendedProps: { ...deadline, daysLeft },
  }
}

export function isPastDeadline(deadlineDatetime) {
  const date = new Date(deadlineDatetime)
  if (Number.isNaN(date.getTime())) return false
  return date.getTime() <= Date.now()
}

// Distinct from getDeadlineSummaryLine: this drops to hour/minute precision on
// the deadline's own day (more useful than a static "Today" once you're that
// close) and reports a hard "Expired" state instead of "Overdue".
export function calculateRemainingTime(deadlineDatetime) {
  const date = new Date(deadlineDatetime)
  if (Number.isNaN(date.getTime())) return ''

  const diffMs = date.getTime() - Date.now()
  if (diffMs <= 0) return 'Expired'

  const daysLeft = calculateDaysLeft(deadlineDatetime)

  if (daysLeft === 0) {
    const diffHours = diffMs / (1000 * 60 * 60)
    if (diffHours < 1) {
      const minutes = Math.max(1, Math.round(diffMs / (1000 * 60)))
      return `${minutes} minute${minutes === 1 ? '' : 's'} left`
    }
    const hours = Math.round(diffHours)
    return `${hours} hour${hours === 1 ? '' : 's'} left`
  }

  if (daysLeft === 1) return 'Tomorrow'
  return `${daysLeft} days left`
}

export function getTodayDateString() {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

export function isDateStringInPast(dateString) {
  if (!dateString) return false
  const [year, month, day] = dateString.split('-').map(Number)
  const selected = new Date(year, month - 1, day)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return selected.getTime() < today.getTime()
}

export function splitDeadlineDatetime(deadlineDatetime) {
  const date = new Date(deadlineDatetime)
  if (!deadlineDatetime || Number.isNaN(date.getTime())) {
    return { date: '', time: DEFAULT_DEADLINE_TIME }
  }

  const pad = (value) => String(value).padStart(2, '0')
  const datePart = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  const timePart = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  return { date: datePart, time: timePart }
}

export function combineDateAndTime(datePart, timePart) {
  if (!datePart) return null

  const [hours, minutes] = (timePart || DEFAULT_DEADLINE_TIME).split(':').map(Number)
  const combined = new Date(`${datePart}T00:00:00`)
  combined.setHours(hours, minutes, 0, 0)
  return combined.toISOString()
}
