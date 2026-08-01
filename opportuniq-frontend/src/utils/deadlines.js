const MS_PER_DAY = 24 * 60 * 60 * 1000
const UPCOMING_WINDOW_DAYS = 7

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

  const time = hasExplicitTime(deadlineDatetime)
    ? date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
    : null

  return { label, time }
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
