import apiClient from './client'

export async function getGapAnalyses(profileId) {
  const response = await apiClient.get(`/api/gap-analysis/${profileId}`)
  return response.data
}

export async function runGapAnalysis(payload) {
  const response = await apiClient.post('/api/gap-analysis/run', payload)
  return response.data
}

export function getGapAnalysisErrorMessage(error) {
  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (status === 404) {
    return 'Profile not found. Please complete onboarding before running a gap analysis.'
  }

  if (status === 422) {
    return detail || 'Please review the analysis configuration and try again.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Unable to complete the gap analysis request. Please try again.'
}
