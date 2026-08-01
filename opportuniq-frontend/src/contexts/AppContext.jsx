import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getProfile, getProfileErrorMessage } from '../api/profile'
import { useLocalStorage } from '../hooks/useLocalStorage'

const PROFILE_ID_STORAGE_KEY = 'opportuniq:profileId'

export const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [profileId, setProfileId] = useLocalStorage(PROFILE_ID_STORAGE_KEY, null)
  const [profile, setProfile] = useState(null)
  const [isProfileLoading, setIsProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState('')

  const loadProfile = useCallback(async () => {
    if (!profileId) {
      setProfile(null)
      setProfileError('')
      return
    }

    setIsProfileLoading(true)
    setProfileError('')
    try {
      const data = await getProfile(profileId)
      setProfile(data)
    } catch (error) {
      setProfileError(getProfileErrorMessage(error))
    } finally {
      setIsProfileLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(loadProfile)
  }, [loadProfile])

  const value = {
    profileId,
    setProfileId,
    profile,
    isProfileLoading,
    profileError,
    reloadProfile: loadProfile,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useAppContext() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider')
  }
  return context
}
