import apiClient from './client'

export async function getReminderSettings(profileId) {
  const response = await apiClient.get('/api/settings/notifications', {
    params: { profile_id: profileId },
  })
  return response.data
}

export async function updateReminderSettings(profileId, updates) {
  const response = await apiClient.put('/api/settings/notifications', {
    profile_id: profileId,
    ...updates,
  })
  return response.data
}
