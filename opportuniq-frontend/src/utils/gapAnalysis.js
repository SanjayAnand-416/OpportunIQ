export const GAP_ANALYSIS_STATUS_OPTIONS = ['All', 'Completed', 'Running', 'Failed', 'Pending']

export const GAP_ANALYSIS_MODES = {
  TARGET_ROLE: 'target_role',
  SAVED_OPPORTUNITY: 'saved_opportunity',
  JOB_DESCRIPTION: 'job_description',
}

const ANALYSIS_TYPE_LABELS = {
  target_role: 'Profile vs Target Role',
  saved_opportunity: 'Profile vs Saved Opportunity',
  job_description: 'Profile vs Job Description',
}

export function normalizeGapAnalysesResponse(data) {
  const list = Array.isArray(data) ? data : data?.analyses || data?.gap_analyses || data?.items || []
  return sortGapAnalyses(list.map(normalizeGapAnalysis))
}

export function normalizeGapAnalysis(raw) {
  const analysisType = raw.analysis_type || raw.analysisType || GAP_ANALYSIS_MODES.TARGET_ROLE
  const status = normalizeGapStatus(raw.status)
  const opportunityTitle =
    raw.opportunity_title || raw.opportunityTitle || raw.opportunity?.title || raw.title
  const company = raw.company || raw.opportunity?.company || ''
  const targetRole = raw.target_role || raw.targetRole || ''
  const jobDescription = raw.job_description || raw.jobDescription || ''
  const startedAt = raw.started_at || raw.startedAt || raw.created_at || raw.createdAt || ''
  const completedAt = raw.completed_at || raw.completedAt || ''

  return {
    id: raw.analysis_id || raw.analysisId || raw.id,
    title: raw.title || buildAnalysisTitle(analysisType, targetRole, opportunityTitle),
    analysisType,
    analysisTypeLabel: ANALYSIS_TYPE_LABELS[analysisType] || titleCase(analysisType),
    target: buildTargetLabel({ analysisType, targetRole, opportunityTitle, company, jobDescription }),
    targetRole,
    opportunityId: raw.opportunity_id || raw.opportunityId || raw.opportunity?.id || '',
    opportunityTitle,
    company,
    jobDescription,
    status,
    startedAt,
    completedAt,
    readiness: formatReadiness(raw.overall_readiness ?? raw.overallReadiness ?? raw.readiness),
    raw,
  }
}

export function filterGapAnalyses(analyses, { query, status }) {
  const normalizedQuery = query.trim().toLowerCase()

  return analyses.filter((analysis) => {
    const matchesStatus = status === 'All' || analysis.status === status
    const matchesQuery =
      !normalizedQuery ||
      [analysis.targetRole, analysis.target, analysis.opportunityTitle, analysis.analysisTypeLabel]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(normalizedQuery))

    return matchesStatus && matchesQuery
  })
}

export function sortGapAnalyses(analyses) {
  return [...analyses].sort((a, b) => dateValue(b.startedAt || b.completedAt) - dateValue(a.startedAt || a.completedAt))
}

export function serializeGapRunPayload({
  profileId,
  mode,
  targetRole,
  opportunityId,
  jobDescription,
}) {
  return {
    profile_id: profileId,
    analysis_type: mode,
    target_role: mode === GAP_ANALYSIS_MODES.TARGET_ROLE ? targetRole.trim() : '',
    opportunity_id: mode === GAP_ANALYSIS_MODES.SAVED_OPPORTUNITY ? opportunityId : '',
    job_description: mode === GAP_ANALYSIS_MODES.JOB_DESCRIPTION ? jobDescription.trim() : '',
  }
}

export function formatGapTimestamp(value) {
  if (!value) return 'Not Provided'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function normalizeGapStatus(status) {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'completed' || normalized === 'complete') return 'Completed'
  if (normalized === 'running' || normalized === 'in_progress') return 'Running'
  if (normalized === 'failed' || normalized === 'error') return 'Failed'
  return 'Pending'
}

function formatReadiness(value) {
  if (value === null || value === undefined || value === '') return 'Pending'
  if (typeof value === 'number') {
    const percentage = value <= 1 ? value * 100 : value
    return `${Math.round(percentage)}%`
  }
  return String(value).includes('%') ? String(value) : String(value)
}

function buildAnalysisTitle(analysisType, targetRole, opportunityTitle) {
  if (analysisType === GAP_ANALYSIS_MODES.TARGET_ROLE && targetRole) {
    return `${targetRole} Readiness`
  }
  if (analysisType === GAP_ANALYSIS_MODES.SAVED_OPPORTUNITY && opportunityTitle) {
    return `${opportunityTitle} Gap Analysis`
  }
  if (analysisType === GAP_ANALYSIS_MODES.JOB_DESCRIPTION) {
    return 'Job Description Gap Analysis'
  }
  return 'Gap Analysis'
}

function buildTargetLabel({ analysisType, targetRole, opportunityTitle, company, jobDescription }) {
  if (analysisType === GAP_ANALYSIS_MODES.TARGET_ROLE) return targetRole || 'Target Role'
  if (analysisType === GAP_ANALYSIS_MODES.SAVED_OPPORTUNITY) {
    return [company, opportunityTitle].filter(Boolean).join(' - ') || 'Saved Opportunity'
  }
  if (analysisType === GAP_ANALYSIS_MODES.JOB_DESCRIPTION) {
    return jobDescription ? 'Custom Job Description' : 'Job Description'
  }
  return targetRole || opportunityTitle || 'Not Provided'
}

function titleCase(value) {
  return String(value || 'Gap Analysis')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function dateValue(value) {
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : 0
}
