import {
  Bell,
  Clock,
  Loader2,
  Mail,
  RotateCw,
  Settings as SettingsIcon,
  ShieldAlert,
  UserRound,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { disconnectGmail, getGmailErrorMessage, getGmailStatus, GMAIL_CONNECT_URL } from '../api/gmail'
import { getProfile, getProfileErrorMessage, updateProfile } from '../api/profile'
import ErrorBanner from '../components/common/ErrorBanner'
import ConfirmationDialog from '../components/common/ConfirmationDialog'
import Toast from '../components/common/Toast'
import SkeletonCard from '../components/common/SkeletonCard'
import SettingCard from '../components/settings/SettingCard'
import SectionHeader from '../components/settings/SectionHeader'
import ToggleSwitch from '../components/settings/ToggleSwitch'
import TagInput from '../components/onboarding/TagInput'
import { useAppContext } from '../contexts/AppContext'
import { useLocalStorage } from '../hooks/useLocalStorage'
import { normalizeProfile, serializeProfile } from '../utils/helpers'
import {
  SETTINGS_STORAGE_KEY,
  getDefaultSettingsPreferences,
  resetLocalPreferences,
  validateProfile,
} from '../utils/settings'
import { formatLastScanned } from '../utils/gmail'

const PROFILE_FIELDS = [
  ['fullName', 'Full Name', 'text'],
  ['email', 'Email', 'email'],
  ['college', 'College', 'text'],
  ['degree', 'Degree', 'text'],
  ['yearOfStudy', 'Year', 'text'],
  ['preferredLocation', 'Preferred Location', 'text'],
  ['opportunityType', 'Opportunity Preference', 'text'],
]

const NOTIFICATION_TOGGLES = [
  ['deadlineReminders', 'Deadline Reminders'],
  ['interviewReminders', 'Interview Reminders'],
  ['opportunityAlerts', 'Opportunity Alerts'],
  ['weeklySummary', 'Weekly Summary'],
  ['emailNotifications', 'Email Notifications'],
]

const REMINDER_TIMINGS = ['1 Day Before', '2 Days Before', '3 Days Before', '1 Week Before']
const TIMEZONES = ['Asia/Kolkata', 'UTC', 'America/New_York', 'Europe/London', 'Asia/Singapore']

function SettingsSkeleton() {
  return (
    <div className="settings-grid" aria-label="Loading settings">
      {Array.from({ length: 5 }, (_, index) => (
        <SkeletonCard key={index} lines={3} />
      ))}
    </div>
  )
}

export default function Settings() {
  const { profileId, reloadProfile } = useAppContext()
  const [profile, setProfile] = useState(normalizeProfile())
  const [gmailStatus, setGmailStatus] = useState(null)
  const [preferences, setPreferences] = useLocalStorage(
    SETTINGS_STORAGE_KEY,
    getDefaultSettingsPreferences(),
  )
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isDisconnecting, setIsDisconnecting] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false)

  const loadSettings = useCallback(async () => {
    if (!profileId) {
      setError('Profile ID is missing. Complete onboarding before editing settings.')
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError('')
    try {
      const [profileData, gmailData] = await Promise.all([
        getProfile(profileId),
        getGmailStatus(profileId),
      ])
      setProfile(normalizeProfile(profileData.profile || profileData))
      setGmailStatus(gmailData)
    } catch (requestError) {
      setError(
        requestError?.config?.url?.includes('/gmail/')
          ? getGmailErrorMessage(requestError)
          : getProfileErrorMessage(requestError),
      )
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(loadSettings)
  }, [loadSettings])

  function updatePreference(key, value) {
    setPreferences((current) => ({
      ...current,
      notifications: {
        ...current.notifications,
        [key]: value,
      },
    }))
  }

  function updateReminderPreference(key, value) {
    setPreferences((current) => ({ ...current, [key]: value }))
  }

  function updateProfileField(fieldName, value) {
    setProfile((current) => ({ ...current, [fieldName]: value }))
  }

  async function handleSaveProfile(event) {
    event.preventDefault()
    if (!profileId || !validateProfile(profile) || isSaving) return

    setIsSaving(true)
    setError('')
    try {
      await updateProfile(profileId, serializeProfile(profile))
      await reloadProfile()
      setToast('Profile updated successfully.')
    } catch (requestError) {
      setError(getProfileErrorMessage(requestError))
    } finally {
      setIsSaving(false)
    }
  }

  function handleConnectGmail() {
    if (!profileId) return
    window.location.href = `${GMAIL_CONNECT_URL}?profile_id=${encodeURIComponent(profileId)}`
  }

  async function handleDisconnectGmail() {
    if (!profileId || isDisconnecting) return
    setIsDisconnecting(true)
    setError('')
    try {
      await disconnectGmail(profileId)
      const data = await getGmailStatus(profileId)
      setGmailStatus(data)
      setToast('Gmail disconnected.')
    } catch (requestError) {
      setError(getGmailErrorMessage(requestError))
    } finally {
      setIsDisconnecting(false)
    }
  }

  function handleResetPreferences() {
    setPreferences(resetLocalPreferences())
    setToast('Preferences reset.')
    setIsResetDialogOpen(false)
  }

  const isProfileValid = validateProfile(profile)

  return (
    <section className="settings-page" aria-labelledby="settings-title">
      <SectionHeader
        title="Settings"
        subtitle="Manage your OpportunIQ account and preferences."
      />

      {error && (
        <div className="settings-error">
          <ErrorBanner message={error} onDismiss={() => setError('')} />
          <button
            type="button"
            className="settings-retry-btn"
            onClick={loadSettings}
            aria-label="Retry loading settings"
          >
            <RotateCw size={14} aria-hidden="true" />
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <SettingsSkeleton />
      ) : (
        <div className="settings-grid">
          <SettingCard
            title="Profile"
            description="Keep your opportunity matching profile current."
            icon={UserRound}
          >
            <form className="settings-profile-form" onSubmit={handleSaveProfile}>
              {PROFILE_FIELDS.map(([field, label, type]) => (
                <label className="settings-field" key={field} htmlFor={`settings-${field}`}>
                  <span>{label}</span>
                  <input
                    id={`settings-${field}`}
                    type={type}
                    value={profile[field]}
                    onChange={(event) => updateProfileField(field, event.target.value)}
                    disabled={isSaving}
                  />
                </label>
              ))}
              <div className="settings-field">
                <span>Skills</span>
                <TagInput
                  id="settings-skills"
                  label="Skills"
                  value={profile.skills}
                  onChange={(value) => updateProfileField('skills', value)}
                  disabled={isSaving}
                />
              </div>
              <div className="settings-field">
                <span>Target Roles</span>
                <TagInput
                  id="settings-target-roles"
                  label="Target Roles"
                  value={profile.targetRoles}
                  onChange={(value) => updateProfileField('targetRoles', value)}
                  disabled={isSaving}
                />
              </div>
              <button
                type="submit"
                className="settings-primary-btn"
                disabled={!isProfileValid || isSaving}
                aria-label="Save profile changes"
              >
                {isSaving && <Loader2 className="spinner" size={16} aria-hidden="true" />}
                {isSaving ? 'Saving Changes...' : 'Save Changes'}
              </button>
            </form>
          </SettingCard>

          <SettingCard
            title="Notification Preferences"
            description="Choose how OpportunIQ keeps you informed."
            icon={Bell}
          >
            <div className="settings-toggle-list">
              {NOTIFICATION_TOGGLES.map(([key, label]) => (
                <ToggleSwitch
                  key={key}
                  id={`toggle-${key}`}
                  label={label}
                  checked={preferences.notifications[key]}
                  onChange={(value) => updatePreference(key, value)}
                />
              ))}
            </div>
          </SettingCard>

          <SettingCard
            title="Reminder Preferences"
            description="Configure reminder timing and timezone."
            icon={Clock}
          >
            <div className="settings-field-stack">
              <label className="settings-field" htmlFor="reminder-timing">
                <span>Reminder Timing</span>
                <select
                  id="reminder-timing"
                  value={preferences.reminderTiming}
                  onChange={(event) =>
                    updateReminderPreference('reminderTiming', event.target.value)
                  }
                >
                  {REMINDER_TIMINGS.map((timing) => (
                    <option key={timing}>{timing}</option>
                  ))}
                </select>
              </label>
              <label className="settings-field" htmlFor="settings-timezone">
                <span>Timezone</span>
                <select
                  id="settings-timezone"
                  value={preferences.timezone}
                  onChange={(event) =>
                    updateReminderPreference('timezone', event.target.value)
                  }
                >
                  {[...new Set([preferences.timezone, ...TIMEZONES])].map((timezone) => (
                    <option key={timezone}>{timezone}</option>
                  ))}
                </select>
              </label>
            </div>
          </SettingCard>

          <SettingCard
            title="Gmail Integration"
            description="Manage read-only Gmail deadline discovery."
            icon={Mail}
          >
            <dl className="settings-gmail-list">
              <div>
                <dt>Connected Email</dt>
                <dd>{gmailStatus?.email || 'Not Connected'}</dd>
              </div>
              <div>
                <dt>Last Scan</dt>
                <dd>{formatLastScanned(gmailStatus?.last_scanned)}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <span
                    className={`settings-status-badge ${
                      gmailStatus?.connected ? 'is-connected' : ''
                    }`}
                  >
                    {gmailStatus?.connected ? 'Connected' : 'Disconnected'}
                  </span>
                </dd>
              </div>
            </dl>
            {gmailStatus?.connected ? (
              <button
                type="button"
                className="settings-danger-outline-btn"
                onClick={handleDisconnectGmail}
                disabled={isDisconnecting}
                aria-label="Disconnect Gmail"
              >
                {isDisconnecting && (
                  <Loader2 className="spinner" size={16} aria-hidden="true" />
                )}
                Disconnect Gmail
              </button>
            ) : (
              <button
                type="button"
                className="settings-primary-btn"
                onClick={handleConnectGmail}
                aria-label="Connect Gmail"
              >
                Connect Gmail
              </button>
            )}
          </SettingCard>

          <SettingCard
            title="Account"
            description="Application details and local account actions."
            icon={SettingsIcon}
          >
            <dl className="settings-account-list">
              <div>
                <dt>Application Version</dt>
                <dd>0.0.0</dd>
              </div>
              <div>
                <dt>Current Theme</dt>
                <dd>Light</dd>
              </div>
              <div>
                <dt>Privacy Policy</dt>
                <dd>Available Soon</dd>
              </div>
              <div>
                <dt>Terms of Service</dt>
                <dd>Available Soon</dd>
              </div>
            </dl>
            <div className="settings-danger-zone">
              <span>
                <ShieldAlert size={16} aria-hidden="true" />
                Danger Zone
              </span>
              <button
                type="button"
                className="settings-danger-btn"
                onClick={() => setIsResetDialogOpen(true)}
                aria-label="Reset local preferences"
              >
                Reset Preferences
              </button>
            </div>
          </SettingCard>
        </div>
      )}

      <Toast message={toast} />
      <ConfirmationDialog
        isOpen={isResetDialogOpen}
        title="Reset Preferences"
        message="Reset local notification and reminder preferences?"
        confirmText="Reset Preferences"
        confirmVariant="warning"
        onCancel={() => setIsResetDialogOpen(false)}
        onConfirm={handleResetPreferences}
      />
    </section>
  )
}
