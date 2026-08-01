import apiClient from './client'

export async function getUnreadNotifications(profileId) {
  const response = await apiClient.get('/api/notifications', {
    params: {
      profile_id: profileId,
      unread: true,
      unread_only: true,
      limit: 5,
    },
  })

  return response.data
}

export async function markNotificationRead(notificationId) {
  const response = await apiClient.patch(
    `/api/notifications/${notificationId}/read`,
  )

  return response.data
}

export async function markAllNotificationsRead(profileId) {
  const response = await apiClient.patch('/api/notifications/read-all', null, {
    params: { profile_id: profileId },
  })

  return response.data
}

export function getNotificationsErrorMessage(error) {
  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (status === 404) {
    return 'Notification could not be found.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}
