import apiClient from './client'

export async function getDeadlines(profileId) {
  const response = await apiClient.get('/api/deadlines', {
    params: { profile_id: profileId },
  })

  return response.data
}

export async function getDeadline(deadlineId) {
  const response = await apiClient.get(`/api/deadlines/${deadlineId}`)

  return response.data
}

export async function createDeadline(payload) {
  const response = await apiClient.post('/api/deadlines', payload)

  return response.data
}

export async function updateDeadline(deadlineId, payload) {
  const response = await apiClient.put(`/api/deadlines/${deadlineId}`, payload)

  return response.data
}

export async function deleteDeadline(deadlineId) {
  const response = await apiClient.delete(`/api/deadlines/${deadlineId}`)

  return response.data
}

export function getDeadlinesErrorMessage(error) {
  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (status === 404) {
    return 'The requested deadline could not be found. Please refresh and try again.'
  }

  if (status === 400 || status === 422) {
    return detail || 'Please check the form for invalid or missing fields.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}
