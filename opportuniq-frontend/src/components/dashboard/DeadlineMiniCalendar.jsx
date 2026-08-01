import { Calendar, ChevronRight, Loader2, RotateCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getDeadlines, getDeadlinesErrorMessage } from '../../api/deadlines'
import { ROUTES } from '../../constants/routes'
import {
  calculateDaysLeft,
  getDeadlineSummaryLine,
  getUrgencyColor,
  isWithinUpcomingWindow,
} from '../../utils/deadlines'
import ErrorBanner from '../common/ErrorBanner'

const MAX_VISIBLE_DEADLINES = 5
const SKELETON_ROWS = 3

function DeadlineSkeleton() {
  return (
    <ul className="mini-deadline-list" aria-hidden="true">
      {Array.from({ length: SKELETON_ROWS }, (_, index) => (
        <li key={index} className="mini-deadline-skeleton-row">
          <span className="mini-deadline-skeleton-dot" />
          <div className="mini-deadline-skeleton-lines">
            <span className="mini-deadline-skeleton-line mini-deadline-skeleton-line-wide" />
            <span className="mini-deadline-skeleton-line mini-deadline-skeleton-line-narrow" />
          </div>
        </li>
      ))}
    </ul>
  )
}

function DeadlineRow({ deadline }) {
  const daysLeft = calculateDaysLeft(deadline.deadline_datetime)
  const tone = getUrgencyColor(daysLeft)
  const summaryLine = getDeadlineSummaryLine(deadline.deadline_datetime)

  return (
    <li className="mini-deadline-row">
      <span className={`mini-deadline-dot tone-${tone}`} aria-hidden="true" />
      <div className="mini-deadline-info">
        <p className="mini-deadline-title">{deadline.title}</p>
        {deadline.organization && <p className="mini-deadline-org">{deadline.organization}</p>}
        <p className={`mini-deadline-time tone-${tone}`}>{summaryLine}</p>
      </div>
    </li>
  )
}

export default function DeadlineMiniCalendar({ profileId }) {
  const navigate = useNavigate()
  const [deadlines, setDeadlines] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')

  const fetchDeadlines = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage('')
    try {
      const data = await getDeadlines(profileId)
      setDeadlines(Array.isArray(data) ? data : [])
    } catch (error) {
      setErrorMessage(getDeadlinesErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(fetchDeadlines)
  }, [fetchDeadlines])

  const upcoming = (deadlines ?? [])
    .filter((deadline) => isWithinUpcomingWindow(deadline.deadline_datetime))
    .sort((a, b) => new Date(a.deadline_datetime) - new Date(b.deadline_datetime))
    .slice(0, MAX_VISIBLE_DEADLINES)

  function handleAddDeadline() {
    navigate(ROUTES.DEADLINES)
  }

  return (
    <section className="mini-deadline-card" aria-label="Upcoming deadlines">
      <div className="mini-deadline-header">
        <h3 className="mini-deadline-title-heading">Upcoming Deadlines</h3>
        <Link
          to={ROUTES.DEADLINES}
          className="mini-deadline-view-all"
          aria-label="View all deadlines"
        >
          View All
          <ChevronRight size={14} aria-hidden="true" />
        </Link>
      </div>

      {isLoading && deadlines === null && <DeadlineSkeleton />}

      {errorMessage && (
        <div className="mini-deadline-error">
          <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />
          <button
            type="button"
            className="mini-deadline-retry-btn"
            onClick={fetchDeadlines}
            disabled={isLoading}
            aria-label="Retry loading deadlines"
          >
            {isLoading ? (
              <Loader2 size={14} className="trace-icon-spin" aria-hidden="true" />
            ) : (
              <RotateCw size={14} aria-hidden="true" />
            )}
            Retry
          </button>
        </div>
      )}

      {deadlines !== null &&
        (upcoming.length === 0 ? (
          <div className="mini-deadline-empty">
            <Calendar size={28} className="mini-deadline-empty-icon" aria-hidden="true" />
            <p className="mini-deadline-empty-title">No upcoming deadlines.</p>
            <p className="mini-deadline-empty-subtitle">You&apos;re all caught up.</p>
            <button
              type="button"
              className="mini-deadline-add-btn"
              onClick={handleAddDeadline}
              aria-label="Add a new deadline"
            >
              Add Deadline
            </button>
          </div>
        ) : (
          <ul className="mini-deadline-list">
            {upcoming.map((deadline) => (
              <DeadlineRow key={deadline.id} deadline={deadline} />
            ))}
          </ul>
        ))}
    </section>
  )
}
