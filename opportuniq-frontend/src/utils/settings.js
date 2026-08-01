import { isProfileComplete } from './helpers'

export const SETTINGS_STORAGE_KEY = 'opportuniq:settingsPreferences'

export const DEFAULT_NOTIFICATION_PREFERENCES = {
  deadlineReminders: true,
  interviewReminders: true,
  opportunityAlerts: true,
  weeklySummary: false,
  emailNotifications: true,
}

export function getBrowserTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata'
}

export function getDefaultSettingsPreferences() {
  return {
    notifications: DEFAULT_NOTIFICATION_PREFERENCES,
    reminderTiming: '3 Days Before',
    timezone: getBrowserTimezone(),
  }
}

export function validateProfile(profile) {
  return isProfileComplete(profile)
}

export function resetLocalPreferences() {
  const defaults = getDefaultSettingsPreferences()
  window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(defaults))
  return defaults
}
