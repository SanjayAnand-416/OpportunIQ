import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createManualProfile, getProfileErrorMessage } from '../api/profile'
import ErrorBanner from '../components/common/ErrorBanner'
import ProfileReviewForm from '../components/onboarding/ProfileReviewForm'
import ProfileSummaryCard from '../components/onboarding/ProfileSummaryCard'
import { ROUTES } from '../constants/routes'
import { useAppContext } from '../contexts/AppContext'
import { isProfileComplete, normalizeProfile, serializeProfile } from '../utils/helpers'

export default function ManualForm() {
  const navigate = useNavigate()
  const { setProfileId } = useAppContext()
  const [profile, setProfile] = useState(normalizeProfile())
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  function handleFieldChange(fieldName, value) {
    setProfile((current) => ({ ...current, [fieldName]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!isProfileComplete(profile) || isSubmitting) return
    setIsSubmitting(true)
    setError('')
    try {
      const response = await createManualProfile(serializeProfile(profile))
      setProfileId(response.profile_id)
      navigate(ROUTES.DASHBOARD)
    } catch (requestError) {
      setError(getProfileErrorMessage(requestError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="profile-review-page">
      <div className="profile-review-grid">
        <div>
          <ErrorBanner message={error} onDismiss={() => setError('')} />
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
