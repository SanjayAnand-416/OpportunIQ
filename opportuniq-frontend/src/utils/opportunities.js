function toMatchPercentage(matchScore) {
  if (typeof matchScore !== 'number' || Number.isNaN(matchScore)) return undefined
  return Math.round(matchScore * 100)
}

// The backend persists opportunities with opportunity_id/skills_required/match_score
// (a 0-1 float) and has no per-opportunity "which of my skills matched" list — it only
// stores an aggregate match_score. OpportunityCard/OpportunityDetailDrawer were built
// against a simpler { id, match_percentage, required_skills, matched_skills } shape, so
// this adapter bridges the two: it renames fields, converts the score to a 0-100
// percentage, and derives matched_skills by cross-referencing the student's own
// profile skills against each opportunity's required skills.
export function normalizeOpportunity(raw, studentSkills = []) {
  const requiredSkills = raw.skills_required ?? raw.required_skills ?? []
  const normalizedStudentSkills = new Set(
    studentSkills.map((skill) => String(skill).trim().toLowerCase()),
  )
  const matchedSkills = requiredSkills.filter((skill) =>
    normalizedStudentSkills.has(String(skill).trim().toLowerCase()),
  )

  return {
    id: raw.opportunity_id ?? raw.id,
    sessionId: raw.session_id,
    title: raw.title,
    company: raw.company,
    platform: raw.platform,
    location: raw.location,
    deadline: raw.deadline,
    url: raw.url,
    description: raw.description,
    also_on: raw.also_on ?? [],
    required_skills: requiredSkills,
    matched_skills: matchedSkills,
    match_percentage: toMatchPercentage(raw.match_score ?? raw.match_percentage),
    saved: raw.saved ?? false,
    opportunity_type: raw.opportunity_type,
    source: raw.source,
  }
}

export function normalizeOpportunities(rawList, studentSkills = []) {
  return (rawList ?? []).map((raw) => normalizeOpportunity(raw, studentSkills))
}
