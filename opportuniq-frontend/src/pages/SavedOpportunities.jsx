import {
  BriefcaseBusiness,
  Building2,
  CalendarClock,
  ExternalLink,
  Gift,
  MessageSquareText,
  Search,
  Star,
  Trash2,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getOpportunitiesErrorMessage,
  getSavedOpportunities,
  removeSavedOpportunity,
  updateOpportunityStatus,
} from '../api/opportunities'
import ErrorBanner from '../components/common/ErrorBanner'
import ConfirmationDialog from '../components/common/ConfirmationDialog'
import EmptyState from '../components/common/EmptyState'
import SkeletonTable from '../components/common/SkeletonTable'
import { ROUTES } from '../constants/routes'
import { useAppContext } from '../contexts/AppContext'
import {
  SAVED_STATUS_OPTIONS,
  calculateStatistics,
  filterSavedOpportunities,
  formatSavedDeadline,
  normalizeSavedOpportunities,
  sortSavedOpportunities,
} from '../utils/savedOpportunities'

const TYPE_FILTERS = ['All', 'Internships', 'Jobs', 'Hackathons', 'Scholarships', 'Research']
const STATUS_FILTERS = ['All', ...SAVED_STATUS_OPTIONS]
const SORT_OPTIONS = [
  { value: 'deadline', label: 'Deadline' },
  { value: 'company', label: 'Company' },
  { value: 'match', label: 'Match Score' },
  { value: 'recent', label: 'Recently Saved' },
]

function StatusChip({ status }) {
  return <span className={`saved-status status-${status.toLowerCase()}`}>{status}</span>
}

function StatCard({ icon: Icon, count, label }) {
  return (
    <div className="saved-stat-card">
      <span aria-hidden="true">
        <Icon size={18} />
      </span>
      <div>
        <strong>{count}</strong>
        <p>{label}</p>
      </div>
    </div>
  )
}

function StatusSelect({ opportunity, onStatusChange }) {
  return (
    <label className="saved-status-select">
      <span className="sr-only">Update status for {opportunity.title}</span>
      <select
        value={opportunity.status}
        onChange={(event) => onStatusChange(opportunity, event.target.value)}
        aria-label={`Update status for ${opportunity.title}`}
      >
        {SAVED_STATUS_OPTIONS.map((status) => (
          <option value={status} key={status}>
            {status}
          </option>
        ))}
      </select>
    </label>
  )
}

function SavedActions({ opportunity, onRemove }) {
  return (
    <div className="saved-actions">
      {opportunity.url ? (
        <a
          href={opportunity.url}
          target="_blank"
          rel="noopener noreferrer"
          className="saved-open-btn"
          aria-label={`Open ${opportunity.title}, opens in a new tab`}
        >
          Open
          <ExternalLink size={14} aria-hidden="true" />
        </a>
      ) : (
        <button type="button" className="saved-open-btn" disabled>
          Open
        </button>
      )}
      <button
        type="button"
        className="saved-remove-btn"
        onClick={() => onRemove(opportunity)}
        aria-label={`Remove ${opportunity.title} from saved opportunities`}
      >
        <Trash2 size={14} aria-hidden="true" />
        Remove
      </button>
    </div>
  )
}

function SavedTableRow({ opportunity, onRemove, onStatusChange }) {
  return (
    <tr>
      <td>
        <div className="saved-company-cell">
          <span aria-hidden="true">{opportunity.company?.[0] || '?'}</span>
          <strong>{opportunity.company || 'Not Provided'}</strong>
        </div>
      </td>
      <td>
        <div className="saved-opportunity-cell">
          <strong>{opportunity.title || 'Untitled Opportunity'}</strong>
          <span>{opportunity.location || 'Location not listed'}</span>
        </div>
      </td>
      <td>{opportunity.platform || 'Not Provided'}</td>
      <td>{formatSavedDeadline(opportunity.deadline)}</td>
      <td>
        <div className="saved-status-stack">
          <StatusChip status={opportunity.status} />
          <StatusSelect opportunity={opportunity} onStatusChange={onStatusChange} />
        </div>
      </td>
      <td>
        <SavedActions opportunity={opportunity} onRemove={onRemove} />
      </td>
    </tr>
  )
}

function SavedMobileCard({ opportunity, onRemove, onStatusChange }) {
  return (
    <article className="saved-mobile-card">
      <div>
        <p>{opportunity.company || 'Not Provided'}</p>
        <h2>{opportunity.title || 'Untitled Opportunity'}</h2>
      </div>
      <div className="saved-mobile-meta">
        <span>
          <CalendarClock size={14} aria-hidden="true" />
          {formatSavedDeadline(opportunity.deadline)}
        </span>
        <StatusChip status={opportunity.status} />
      </div>
      <StatusSelect opportunity={opportunity} onStatusChange={onStatusChange} />
      <SavedActions opportunity={opportunity} onRemove={onRemove} />
    </article>
  )
}

export default function SavedOpportunities() {
  const navigate = useNavigate()
  const { profileId } = useAppContext()
  const [opportunities, setOpportunities] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [sortBy, setSortBy] = useState('deadline')
  const [pendingRemove, setPendingRemove] = useState(null)

  const loadSavedOpportunities = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const data = await getSavedOpportunities(profileId)
      setOpportunities(normalizeSavedOpportunities(data))
    } catch (requestError) {
      setError(getOpportunitiesErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(loadSavedOpportunities)
  }, [loadSavedOpportunities])

  const statistics = useMemo(() => calculateStatistics(opportunities), [opportunities])

  const visibleOpportunities = useMemo(() => {
    const filtered = filterSavedOpportunities(opportunities, {
      query: searchQuery,
      type: typeFilter,
      status: statusFilter,
    })
    return sortSavedOpportunities(filtered, sortBy)
  }, [opportunities, searchQuery, sortBy, statusFilter, typeFilter])

  async function handleStatusChange(opportunity, nextStatus) {
    if (opportunity.status === nextStatus) return

    const previousOpportunities = opportunities
    setOpportunities((current) =>
      current.map((item) =>
        item.id === opportunity.id ? { ...item, status: nextStatus } : item,
      ),
    )

    try {
      await updateOpportunityStatus(opportunity.savedId, nextStatus)
    } catch (requestError) {
      setError(getOpportunitiesErrorMessage(requestError))
      setOpportunities(previousOpportunities)
    }
  }

  async function confirmRemove() {
    if (!pendingRemove) return
    try {
      await removeSavedOpportunity(pendingRemove.savedId)
      setPendingRemove(null)
      await loadSavedOpportunities()
    } catch (requestError) {
      setError(getOpportunitiesErrorMessage(requestError))
    }
  }

  const hasSavedOpportunities = opportunities.length > 0

  return (
    <section className="saved-page" aria-labelledby="saved-title">
      <div className="saved-header">
        <div>
          <h1 id="saved-title">Saved Opportunities</h1>
          <p>
            Keep track of every opportunity you're interested in and monitor your
            application progress.
          </p>
        </div>
        <div className="saved-stats" aria-label="Saved opportunity statistics">
          <StatCard icon={Star} count={statistics.saved} label="Saved" />
          <StatCard icon={BriefcaseBusiness} count={statistics.applied} label="Applied" />
          <StatCard icon={MessageSquareText} count={statistics.interview} label="Interview Scheduled" />
          <StatCard icon={Gift} count={statistics.offer} label="Offer Received" />
        </div>
      </div>

      <div className="saved-toolbar">
        <div className="saved-search">
          <Search size={16} aria-hidden="true" />
          <label htmlFor="saved-search" className="sr-only">
            Search saved opportunities
          </label>
          <input
            id="saved-search"
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search by title, company, platform or location..."
          />
        </div>
        <label className="saved-select">
          <span>Sort</span>
          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
            aria-label="Sort saved opportunities"
          >
            {SORT_OPTIONS.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="saved-select">
          <span>Status</span>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            aria-label="Filter by status"
          >
            {STATUS_FILTERS.map((status) => (
              <option value={status} key={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="saved-filter-chips" aria-label="Opportunity type filters">
        {TYPE_FILTERS.map((type) => (
          <button
            type="button"
            className={typeFilter === type ? 'is-active' : ''}
            onClick={() => setTypeFilter(type)}
            key={type}
            aria-pressed={typeFilter === type}
          >
            {type}
          </button>
        ))}
      </div>

      {error && (
        <div className="saved-error">
          <ErrorBanner message={error} onDismiss={() => setError('')} />
          <button
            type="button"
            className="saved-retry-btn"
            onClick={loadSavedOpportunities}
            aria-label="Retry loading saved opportunities"
          >
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <SkeletonTable rows={5} columns={6} />
      ) : visibleOpportunities.length > 0 ? (
        <>
          <div className="saved-table-wrap">
            <table className="saved-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Opportunity</th>
                  <th>Platform</th>
                  <th>Deadline</th>
                  <th>Current Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleOpportunities.map((opportunity) => (
                  <SavedTableRow
                    key={opportunity.id}
                    opportunity={opportunity}
                    onRemove={setPendingRemove}
                    onStatusChange={handleStatusChange}
                  />
                ))}
              </tbody>
            </table>
          </div>
          <div className="saved-mobile-list">
            {visibleOpportunities.map((opportunity) => (
              <SavedMobileCard
                key={opportunity.id}
                opportunity={opportunity}
                onRemove={setPendingRemove}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        </>
      ) : (
        <EmptyState
          Icon={Building2}
          title={hasSavedOpportunities ? 'No Matching Opportunities' : 'No Saved Opportunities'}
          subtitle={
            hasSavedOpportunities
              ? 'Try changing your search, filters or sort option.'
              : 'Save interesting opportunities from the dashboard to keep track of them here.'
          }
          primaryButton={hasSavedOpportunities ? undefined : 'Explore Opportunities'}
          onPrimaryClick={() => navigate(ROUTES.DASHBOARD)}
        />
      )}
      <ConfirmationDialog
        isOpen={Boolean(pendingRemove)}
        title="Remove Opportunity"
        message={`Remove "${pendingRemove?.title}" from saved opportunities?`}
        confirmText="Remove"
        confirmVariant="danger"
        onCancel={() => setPendingRemove(null)}
        onConfirm={confirmRemove}
      />
    </section>
  )
}
