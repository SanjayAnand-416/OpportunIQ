import apiClient from './client'

export async function searchOpportunities(profileId) {
  const response = await apiClient.post('/api/opportunities/search', {
    profile_id: profileId,
  })

  return response.data
}

export async function getOpportunitiesByProfile(profileId) {
  const response = await apiClient.get('/api/opportunities', {
    params: { profile_id: profileId },
  })

  return response.data.opportunities
}

export async function getOpportunitiesBySession(sessionId) {
  const response = await apiClient.get('/api/opportunities', {
    params: { session_id: sessionId },
  })

  return response.data.opportunities
}

export function getOpportunitiesErrorMessage(error) {
  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (status === 404) {
    return 'Profile not found. Please refresh and try again.'
  }

  if (status === 422) {
    return detail || 'Your profile needs target roles before OpportunIQ can search for you.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}
