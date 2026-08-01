import apiClient from './client'

export const GMAIL_CONNECT_URL = 'http://localhost:8000/api/gmail/connect'

export async function getGmailStatus(profileId) {
  const response = await apiClient.get('/api/gmail/status', {
    params: { profile_id: profileId },
  })

  return response.data
}

export async function scanGmailInbox(profileId) {
  const response = await apiClient.post('/api/gmail/scan', { profile_id: profileId })

  return response.data
}

export async function disconnectGmail(profileId) {
  const response = await apiClient.delete('/api/gmail/disconnect', {
    params: { profile_id: profileId },
  })

  return response.data
}

export function getGmailErrorMessage(error) {
  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (status === 404) {
    return 'Profile not found. Please refresh and try again.'
  }

  if (status === 409) {
    return detail || 'Gmail account is not connected.'
  }

  if (status === 503) {
    return detail || 'Gmail integration is temporarily unavailable.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}
