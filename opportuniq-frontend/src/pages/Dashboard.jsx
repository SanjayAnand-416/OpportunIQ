import { Loader2, RefreshCw, RotateCw, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useOutletContext } from 'react-router-dom'
import {
  getOpportunitiesByProfile,
  getOpportunitiesBySession,
  getOpportunitiesErrorMessage,
  searchOpportunities,
} from '../api/opportunities'
import AgentTracePanel from '../components/dashboard/AgentTracePanel'
import OpportunityCardSkeleton from '../components/dashboard/OpportunityCardSkeleton'
import OpportunityCard from '../components/dashboard/OpportunityCard'
import OpportunityDetailDrawer from '../components/dashboard/OpportunityDetailDrawer'
import ErrorBanner from '../components/common/ErrorBanner'
import Toast from '../components/common/Toast'
import { ROUTES } from '../constants/routes'
import { useAppContext } from '../contexts/AppContext'
import { useToast } from '../hooks/useToast'
import { normalizeOpportunities } from '../utils/opportunities'

const SKELETON_COUNT = 6

function matchesQuery(opportunity, query) {
  return [opportunity.title, opportunity.company, opportunity.location, opportunity.platform]
    .filter(Boolean)
    .some((field) => field.toLowerCase().includes(query))
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { searchQuery } = useOutletContext() ?? { searchQuery: '' }
  const { profileId, profile, profileError, reloadProfile } = useAppContext()

  const [rawOpportunities, setRawOpportunities] = useState(null)
  const [isLoadingOpportunities, setIsLoadingOpportunities] = useState(true)
  const [opportunitiesError, setOpportunitiesError] = useState('')

  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [isTraceOpen, setIsTraceOpen] = useState(false)

  const [selectedOpportunity, setSelectedOpportunity] = useState(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  const [toastMessage, setToastMessage] = useToast()
  const [dismissedProfileError, setDismissedProfileError] = useState('')

  const loadOpportunities = useCallback(
    async (bySessionId) => {
      setIsLoadingOpportunities(true)
      setOpportunitiesError('')
      try {
        const data = bySessionId
          ? await getOpportunitiesBySession(bySessionId)
          : await getOpportunitiesByProfile(profileId)
        setRawOpportunities(data)
      } catch (error) {
        setOpportunitiesError(getOpportunitiesErrorMessage(error))
      } finally {
        setIsLoadingOpportunities(false)
      }
    },
    [profileId],
  )

  useEffect(() => {
    if (!profileId) return
    Promise.resolve().then(() => loadOpportunities())
  }, [profileId, loadOpportunities])

  const opportunities = useMemo(
    () => (rawOpportunities ? normalizeOpportunities(rawOpportunities, profile?.skills) : null),
    [rawOpportunities, profile],
  )

  const filteredOpportunities = useMemo(() => {
    if (!opportunities) return []
    const query = searchQuery.trim().toLowerCase()
    if (!query) return opportunities
    return opportunities.filter((opportunity) => matchesQuery(opportunity, query))
  }, [opportunities, searchQuery])

  async function handleFindOpportunities() {
    if (!profileId || isSearching) return

    setIsSearching(true)
    setSearchError('')
    try {
      const response = await searchOpportunities(profileId)
      setSessionId(response.session_id)

      if (response.status === 'complete' || response.cached) {
        await loadOpportunities(response.session_id)
      } else {
        setIsTraceOpen(true)
      }
    } catch (error) {
      setSearchError(getOpportunitiesErrorMessage(error))
    } finally {
      setIsSearching(false)
    }
  }

  function handleTraceComplete() {
    if (sessionId) loadOpportunities(sessionId)
  }

  function handleCardClick(opportunity) {
    setSelectedOpportunity(opportunity)
    setIsDrawerOpen(true)
  }

  function handleApply(opportunity) {
    if (opportunity?.url) {
      window.open(opportunity.url, '_blank', 'noopener,noreferrer')
    }
  }

  function handleSave() {
    setToastMessage('Coming Soon')
  }

  function handleAddDeadline() {
    setIsDrawerOpen(false)
    navigate(ROUTES.DEADLINES)
  }

  const isBusy = isLoadingOpportunities || isSearching

  let content

  if (!profileId) {
    content = (
      <div className="dash-empty-state">
        <Search size={40} className="dash-empty-icon" aria-hidden="true" />
        <h2 className="dash-empty-title">Complete your profile to get started</h2>
        <p className="dash-empty-subtitle">
          OpportunIQ needs your profile before it can search for opportunities tailored to you.
        </p>
        <button
          type="button"
          className="dash-empty-btn"
          onClick={() => navigate(ROUTES.UPLOAD)}
          aria-label="Start onboarding"
        >
          Complete Profile
        </button>
      </div>
    )
  } else if (opportunities === null && isLoadingOpportunities) {
    content = (
      <div className="opportunity-grid">
        {Array.from({ length: SKELETON_COUNT }, (_, index) => (
          <OpportunityCardSkeleton key={index} />
        ))}
      </div>
    )
  } else if (opportunities === null && opportunitiesError) {
    content = (
      <div className="dash-error-block">
        <ErrorBanner message={opportunitiesError} onDismiss={() => setOpportunitiesError('')} />
        <button
          type="button"
          className="dash-retry-btn"
          onClick={() => loadOpportunities()}
          aria-label="Retry loading opportunities"
        >
          <RotateCw size={14} aria-hidden="true" />
          Retry
        </button>
      </div>
    )
  } else if (opportunities !== null) {
    content = (
      <>
        {opportunitiesError && (
          <div className="dash-error-block">
            <ErrorBanner message={opportunitiesError} onDismiss={() => setOpportunitiesError('')} />
            <button
              type="button"
              className="dash-retry-btn"
              onClick={() => loadOpportunities()}
              aria-label="Retry loading opportunities"
            >
              <RotateCw size={14} aria-hidden="true" />
              Retry
            </button>
          </div>
        )}

        {opportunities.length === 0 ? (
          <div className="dash-empty-state">
            <Search size={40} className="dash-empty-icon" aria-hidden="true" />
            <h2 className="dash-empty-title">No Opportunities Yet</h2>
            <p className="dash-empty-subtitle">
              Run your first AI-powered opportunity search to discover internships, jobs and
              hackathons tailored to your profile.
            </p>
            <button
              type="button"
              className="dash-empty-btn"
              onClick={handleFindOpportunities}
              disabled={isSearching}
              aria-label="Find opportunities"
            >
              {isSearching ? (
                <Loader2 size={16} className="trace-icon-spin" aria-hidden="true" />
              ) : (
                <Search size={16} aria-hidden="true" />
              )}
              {isSearching ? 'Searching Opportunities...' : 'Find Opportunities'}
            </button>
          </div>
        ) : (
          <>
            <div className="dash-toolbar">
              <button
                type="button"
                className="dash-toolbar-btn dash-toolbar-btn-secondary"
                onClick={() => loadOpportunities()}
                disabled={isBusy}
                aria-label="Refresh opportunities"
              >
                <RefreshCw
                  size={15}
                  className={isLoadingOpportunities ? 'trace-icon-spin' : ''}
                  aria-hidden="true"
                />
                Refresh
              </button>
              <button
                type="button"
                className="dash-toolbar-btn dash-toolbar-btn-primary"
                onClick={handleFindOpportunities}
                disabled={isBusy}
                aria-label="Find opportunities"
              >
                {isSearching ? (
                  <Loader2 size={15} className="trace-icon-spin" aria-hidden="true" />
                ) : (
                  <Search size={15} aria-hidden="true" />
                )}
                {isSearching ? 'Searching Opportunities...' : 'Find Opportunities'}
              </button>
            </div>

            {searchError && (
              <div className="dash-error-block">
                <ErrorBanner message={searchError} onDismiss={() => setSearchError('')} />
              </div>
            )}

            {filteredOpportunities.length === 0 ? (
              <p className="dash-no-matches">No opportunities match your search.</p>
            ) : (
              <div className="opportunity-grid">
                {filteredOpportunities.map((opportunity) => (
                  <OpportunityCard
                    key={opportunity.id}
                    opportunity={opportunity}
                    onCardClick={handleCardClick}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </>
    )
  }

  return (
    <div className="dashboard-page">
      {profileError && profileError !== dismissedProfileError && (
        <div className="dash-error-block">
          <ErrorBanner
            message={profileError}
            onDismiss={() => setDismissedProfileError(profileError)}
          />
          <button
            type="button"
            className="dash-retry-btn"
            onClick={reloadProfile}
            aria-label="Retry loading profile"
          >
            <RotateCw size={14} aria-hidden="true" />
            Retry
          </button>
        </div>
      )}

      {content}

      <AgentTracePanel
        sessionId={sessionId}
        isOpen={isTraceOpen}
        onClose={() => setIsTraceOpen(false)}
        onComplete={handleTraceComplete}
      />

      <OpportunityDetailDrawer
        isOpen={isDrawerOpen}
        opportunity={selectedOpportunity}
        onClose={() => setIsDrawerOpen(false)}
        onApply={handleApply}
        onSave={handleSave}
        onAddDeadline={handleAddDeadline}
      />

      <Toast message={toastMessage} />
    </div>
  )
}
