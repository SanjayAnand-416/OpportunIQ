import { normalizeOpportunity } from './opportunities'

const TYPE_LABELS = {
  internships: 'Internships',
  internship: 'Internships',
  jobs: 'Jobs',
  job: 'Jobs',
  hackathons: 'Hackathons',
  hackathon: 'Hackathons',
  scholarships: 'Scholarships',
  scholarship: 'Scholarships',
  research: 'Research',
}

export const SAVED_STATUS_OPTIONS = [
  'Not Applied',
  'Applied',
  'Interview Scheduled',
  'Offer Received',
  'Rejected',
]

export function normalizeSavedOpportunity(raw) {
  const opportunity = normalizeOpportunity(raw.opportunity ?? raw)
  const status = raw.status || raw.application_status || raw.current_status || 'Saved'

  return {
    ...opportunity,
    savedId: raw.saved_id || raw.savedId || raw.id || opportunity.id,
    status: normalizeSavedStatus(status),
    savedAt: raw.saved_at || raw.savedAt || raw.created_at || raw.createdAt || '',
    opportunity_type: opportunity.opportunity_type || raw.type || raw.category || '',
  }
}

export function normalizeSavedOpportunities(rawList) {
  return (rawList ?? []).map(normalizeSavedOpportunity)
}

export function normalizeSavedStatus(status) {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'applied') return 'Applied'
  if (normalized === 'interview' || normalized === 'interview scheduled') return 'Interview Scheduled'
  if (normalized === 'offer' || normalized === 'offer received') return 'Offer Received'
  if (normalized === 'rejected') return 'Rejected'
  return 'Not Applied'
}

export function getOpportunityType(opportunity) {
  const rawType = String(opportunity.opportunity_type || opportunity.type || '').trim().toLowerCase()
  return TYPE_LABELS[rawType] || 'Jobs'
}

export function calculateStatistics(opportunities) {
  return {
    saved: opportunities.length,
    applied: opportunities.filter((item) => item.status === 'Applied').length,
    interview: opportunities.filter((item) => item.status === 'Interview Scheduled').length,
    offer: opportunities.filter((item) => item.status === 'Offer Received').length,
  }
}

export function filterSavedOpportunities(opportunities, { query, type, status }) {
  const normalizedQuery = query.trim().toLowerCase()

  return opportunities.filter((opportunity) => {
    const matchesQuery =
      !normalizedQuery ||
      [opportunity.title, opportunity.company, opportunity.platform, opportunity.location]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(normalizedQuery))
    const matchesType = type === 'All' || getOpportunityType(opportunity) === type
    const matchesStatus = status === 'All' || opportunity.status === status

    return matchesQuery && matchesType && matchesStatus
  })
}

export function sortSavedOpportunities(opportunities, sortBy) {
  return [...opportunities].sort((a, b) => {
    if (sortBy === 'company') {
      return String(a.company || '').localeCompare(String(b.company || ''))
    }

    if (sortBy === 'match') {
      return (b.match_percentage ?? 0) - (a.match_percentage ?? 0)
    }

    if (sortBy === 'recent') {
      return dateValue(b.savedAt) - dateValue(a.savedAt)
    }

    return dateValue(a.deadline) - dateValue(b.deadline)
  })
}

function dateValue(value) {
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : Number.MAX_SAFE_INTEGER
}

export function formatSavedDeadline(deadline) {
  if (!deadline) return 'Not Provided'
  const date = new Date(deadline)
  if (Number.isNaN(date.getTime())) return deadline
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}
