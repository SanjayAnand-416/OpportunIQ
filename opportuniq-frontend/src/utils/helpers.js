const ALLOWED_RESUME_EXTENSIONS = ['.pdf', '.doc', '.docx']
const MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024

export function formatFileSize(bytes) {
  if (!bytes) {
    return '0 KB'
  }

  const megabytes = bytes / (1024 * 1024)

  if (megabytes >= 1) {
    return `${megabytes.toFixed(1)} MB`
  }

  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function validateResumeFile(file) {
  if (!file) {
    return 'No file selected.'
  }

  const fileName = file.name.toLowerCase()
  const isAllowedType = ALLOWED_RESUME_EXTENSIONS.some((extension) =>
    fileName.endsWith(extension),
  )

  if (!isAllowedType) {
    return 'Unsupported file type. Please upload a PDF, DOC or DOCX resume.'
  }

  if (file.size > MAX_RESUME_SIZE_BYTES) {
    return 'Maximum file size exceeded (5 MB).'
  }

  return ''
}

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
}

export function hasValue(value) {
  if (Array.isArray(value)) {
    return value.length > 0
  }

  return Boolean(String(value ?? '').trim())
}

export function normalizeProfile(profile = {}) {
  return {
    fullName: profile.fullName || profile.full_name || profile.name || '',
    email: profile.email || '',
    degree: profile.degree || '',
    college: profile.college || profile.university || '',
    yearOfStudy: profile.yearOfStudy || profile.year_of_study || '',
    skills: profile.skills || [],
    targetRoles: profile.targetRoles || profile.target_roles || [],
    preferredLocation:
      profile.preferredLocation || profile.preferred_location || profile.location || '',
    opportunityType:
      profile.opportunityType || profile.opportunity_type || profile.preference || '',
  }
}

export function serializeProfile(profile) {
  return {
    name: profile.fullName,
    email: profile.email,
    degree: profile.degree,
    college: profile.college,
    year_of_study: profile.yearOfStudy,
    skills: profile.skills,
    target_roles: profile.targetRoles,
    location: profile.preferredLocation,
    opportunity_type: profile.opportunityType,
  }
}

export function isProfileComplete(profile) {
  return (
    hasValue(profile.fullName) &&
    isValidEmail(profile.email) &&
    hasValue(profile.degree) &&
    hasValue(profile.college) &&
    hasValue(profile.skills) &&
    hasValue(profile.targetRoles) &&
    hasValue(profile.preferredLocation) &&
    hasValue(profile.opportunityType)
  )
}
