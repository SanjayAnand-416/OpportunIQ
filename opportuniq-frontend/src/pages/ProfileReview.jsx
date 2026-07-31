import { Loader2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  getProfile,
  getProfileErrorMessage,
  isAxiosUploadError,
  updateProfile,
} from '../api/profile'
import ErrorBanner from '../components/common/ErrorBanner'
import ProfileReviewForm from '../components/onboarding/ProfileReviewForm'
import ProfileSummaryCard from '../components/onboarding/ProfileSummaryCard'
import { ROUTES } from '../constants/routes'
import {
  isProfileComplete,
  normalizeProfile,
  serializeProfile,
} from '../utils/helpers'

export default function ProfileReview() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const profileId = searchParams.get('profile_id')
  const [profile, setProfile] = useState(normalizeProfile())
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [saveError, setSaveError] = useState('')

  const loadProfile = useCallback(async () => {
    if (!profileId) {
      setLoadError('Profile ID is missing. Please upload your resume again.')
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setLoadError('')

    try {
      const data = await getProfile(profileId)
      setProfile(normalizeProfile(data.profile || data))
    } catch (error) {
      const message = isAxiosUploadError(error)
        ? getProfileErrorMessage(error)
        : 'Unexpected server error. Please try again later.'

      setLoadError(message)
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(loadProfile)
  }, [loadProfile])

  const handleFieldChange = (fieldName, value) => {
    setProfile((currentProfile) => ({
      ...currentProfile,
      [fieldName]: value,
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!profileId || !isProfileComplete(profile) || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setSaveError('')

    try {
      await updateProfile(profileId, serializeProfile(profile))
      navigate(ROUTES.DASHBOARD)
    } catch (error) {
      const message = isAxiosUploadError(error)
        ? getProfileErrorMessage(error)
        : 'Unexpected server error. Please try again later.'

      setSaveError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <main className="profile-loading" aria-live="polite">
        <Loader2 className="spinner" size={28} aria-hidden="true" />
        <p>Loading your profile...</p>
      </main>
    )
  }

  if (loadError) {
    return (
      <main className="profile-error-page">
        <div className="profile-error-card">
          <ErrorBanner message={loadError} onDismiss={() => setLoadError('')} />
          <div className="profile-error-actions">
            <button
              type="button"
              className="upload-primary-button"
              onClick={loadProfile}
              aria-label="Retry loading profile"
            >
              Retry
            </button>
            <button
              type="button"
              className="upload-secondary-button"
              onClick={() => navigate(ROUTES.UPLOAD)}
              aria-label="Go back to resume upload"
            >
              Go Back
            </button>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="profile-review-page">
      <div className="profile-review-grid">
        <div>
          <ErrorBanner
            message={saveError}
            onDismiss={() => setSaveError('')}
          />
          <ProfileReviewForm
            isSubmitting={isSubmitting}
            isSubmitDisabled={!isProfileComplete(profile) || isSubmitting}
            profile={profile}
            onChange={handleFieldChange}
            onSubmit={handleSubmit}
          />
        </div>
        <ProfileSummaryCard profile={profile} />
      </div>
    </main>
  )
}
