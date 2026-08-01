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

export function normalizeGapAnalysisResult(data) {
  const raw = data?.analysis || data?.result || data
  if (!raw || Object.keys(raw).length === 0) return null

  const base = normalizeGapAnalysis(raw)
  const required = normalizeSkillList(raw.required_skills || raw.requiredSkills || raw.skills_required)
  const existing = normalizeSkillList(raw.existing_skills || raw.existingSkills || raw.matched_skills)
  const missing = normalizeSkillList(raw.missing_skills || raw.missingSkills)
  const partial = normalizeSkillList(raw.partial_skills || raw.partialSkills)
  const resources = normalizeResources(raw.recommended_learning_resources || raw.learning_resources || raw.resources)

  return {
    ...base,
    readinessScore: parseReadinessScore(raw.readiness_score ?? raw.readinessScore ?? raw.overall_readiness ?? raw.overallReadiness),
    requiredSkills: required,
    existingSkills: existing,
    missingSkills: missing,
    partialSkills: partial,
    skillMatrix: buildSkillMatrix({ required, existing, missing, partial, rawSkills: raw.skill_gap_matrix || raw.skillMatrix || raw.skills }),
    roadmap: normalizeRoadmap(raw.learning_roadmap || raw.roadmap || raw.learningRoadmap),
    suggestedProjects: normalizeProjects(raw.suggested_projects || raw.projects || raw.recommended_projects),
    resources,
    summary: raw.analysis_summary || raw.summary || raw.ai_summary || '',
  }
}

export function calculateReadinessColor(score) {
  if (score >= 80) return 'green'
  if (score >= 60) return 'amber'
  return 'red'
}

export function getReadinessInterpretation(score) {
  if (score >= 85) return 'Excellent Match'
  if (score >= 70) return 'Good Match'
  if (score >= 55) return 'Needs Improvement'
  return 'Significant Skill Gap'
}

export function groupSkillsByPriority(skills) {
  return {
    High: skills.filter((skill) => skill.priority === 'High'),
    Medium: skills.filter((skill) => skill.priority === 'Medium'),
    Low: skills.filter((skill) => skill.priority === 'Low'),
  }
}

export function groupSkillsByStatus(skills) {
  return {
    Matched: skills.filter((skill) => skill.status === 'Matched'),
    Partial: skills.filter((skill) => skill.status === 'Partial'),
    Missing: skills.filter((skill) => skill.status === 'Missing'),
  }
}

export function formatDuration(value) {
  if (!value) return 'Not Provided'
  return String(value)
}

function normalizeSkillList(skills = []) {
  return (skills || []).map((skill) => {
    if (typeof skill === 'string') {
      return {
        name: skill,
        status: 'Matched',
        priority: 'Medium',
        evidence: 'Unknown',
      }
    }

    return {
      name: skill.name || skill.skill || skill.title || 'Unnamed Skill',
      status: normalizeSkillStatus(skill.status),
      priority: normalizePriority(skill.priority || skill.level),
      evidence: normalizeEvidence(skill.evidence || skill.confidence || skill.evidence_level || skill.evidenceLevel),
    }
  })
}

function buildSkillMatrix({ required, existing, missing, partial, rawSkills }) {
  if (rawSkills?.length) return normalizeSkillList(rawSkills)

  const matchedRows = existing.map((skill) => ({ ...skill, status: 'Matched' }))
  const partialRows = partial.map((skill) => ({ ...skill, status: 'Partial' }))
  const missingRows = missing.map((skill) => ({ ...skill, status: 'Missing' }))
  const knownNames = new Set([...matchedRows, ...partialRows, ...missingRows].map((skill) => skill.name.toLowerCase()))
  const unknownRequired = required
    .filter((skill) => !knownNames.has(skill.name.toLowerCase()))
    .map((skill) => ({ ...skill, status: 'Missing' }))

  return [...matchedRows, ...partialRows, ...missingRows, ...unknownRequired]
}

function normalizeRoadmap(steps = []) {
  return (steps || []).map((step, index) => ({
    id: step.id || step.step || index + 1,
    stepNumber: step.step_number || step.stepNumber || index + 1,
    skill: step.skill || step.title || `Step ${index + 1}`,
    duration: formatDuration(step.estimated_duration || step.estimatedDuration || step.duration),
    description: step.description || step.summary || 'Not Provided',
    completed: Boolean(step.completed || step.is_completed || step.isCompleted),
  }))
}

function normalizeProjects(projects = []) {
  return (projects || []).map((project, index) => ({
    id: project.id || project.name || index,
    name: project.name || project.title || 'Suggested Project',
    difficulty: project.difficulty || project.level || 'Not Provided',
    skills: normalizeNameList(project.skills_covered || project.skillsCovered || project.skills),
    duration: formatDuration(project.estimated_duration || project.estimatedDuration || project.duration),
    description: project.description || project.summary || 'Not Provided',
  }))
}

function normalizeResources(resources = []) {
  return (resources || []).map((resource, index) => ({
    id: resource.id || resource.url || resource.title || index,
    title: resource.title || resource.name || 'Learning Resource',
    provider: resource.provider || resource.source || 'Not Provided',
    type: titleCase(resource.type || resource.resource_type || 'Resource'),
    duration: formatDuration(resource.estimated_duration || resource.estimatedDuration || resource.duration),
    url: resource.url || resource.link || '',
  }))
}

function normalizeNameList(values = []) {
  return (values || []).map((value) => (typeof value === 'string' ? value : value.name || value.skill || value.title)).filter(Boolean)
}

function parseReadinessScore(value) {
  if (value === null || value === undefined || value === '') return 0
  const numeric = typeof value === 'number' ? value : Number(String(value).replace('%', ''))
  if (!Number.isFinite(numeric)) return 0
  return Math.round(numeric <= 1 ? numeric * 100 : numeric)
}

function normalizeSkillStatus(status) {
  const normalized = String(status || '').trim().toLowerCase()
  if (normalized === 'matched' || normalized === 'existing' || normalized === 'present') return 'Matched'
  if (normalized === 'partial' || normalized === 'partially matched') return 'Partial'
  return 'Missing'
}

function normalizePriority(priority) {
  const normalized = String(priority || '').trim().toLowerCase()
  if (normalized === 'high' || normalized === 'critical') return 'High'
  if (normalized === 'low') return 'Low'
  return 'Medium'
}

function normalizeEvidence(evidence) {
  const normalized = String(evidence || '').trim().toLowerCase()
  if (normalized.includes('strong') || normalized === 'high') return 'Strong Evidence'
  if (normalized.includes('moderate') || normalized === 'medium') return 'Moderate Evidence'
  if (normalized.includes('weak') || normalized === 'low') return 'Weak Evidence'
  return 'Unknown'
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
