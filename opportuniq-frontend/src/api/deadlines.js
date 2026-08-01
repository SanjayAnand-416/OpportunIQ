import apiClient from './client'

export async function getDeadlines(profileId) {
  const response = await apiClient.get('/api/deadlines', {
    params: { profile_id: profileId },
  })

  return response.data
}

export function getDeadlinesErrorMessage(error) {
  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (status === 404) {
    return 'Profile not found. Please refresh and try again.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}
