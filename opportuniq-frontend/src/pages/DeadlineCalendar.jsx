import { Calendar } from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import listPlugin from '@fullcalendar/react/list'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { CalendarDays, LayoutGrid, List, Plus, RotateCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getDeadlines, getDeadlinesErrorMessage } from '../api/deadlines'
import DeadlineDetailPopup from '../components/calendar/DeadlineDetailPopup'
import DeadlineForm from '../components/calendar/DeadlineForm'
import ErrorBanner from '../components/common/ErrorBanner'
import { useAppContext } from '../contexts/AppContext'
import { mapDeadlineToEvent } from '../utils/deadlines'

const MONTH_VIEW = 'dayGridMonth'
const LIST_VIEW = 'listMonth'
const SKELETON_CELL_COUNT = 35

function CalendarSkeleton() {
  return (
    <div className="deadline-calendar-skeleton" aria-hidden="true">
      <div className="deadline-calendar-skeleton-weekdays">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
          <span key={day}>{day}</span>
        ))}
      </div>
      <div className="deadline-calendar-skeleton-grid">
        {Array.from({ length: SKELETON_CELL_COUNT }, (_, index) => (
          <span key={index} className="skeleton-block deadline-calendar-skeleton-cell" />
        ))}
      </div>
    </div>
  )
}

export default function DeadlineCalendar() {
  const { profileId } = useAppContext()
  const calendarRef = useRef(null)

  const [deadlines, setDeadlines] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [activeView, setActiveView] = useState(MONTH_VIEW)

  const [selectedDeadline, setSelectedDeadline] = useState(null)
  const [isPopupOpen, setIsPopupOpen] = useState(false)
  const [isFormOpen, setIsFormOpen] = useState(false)

  const fetchDeadlines = useCallback(async () => {
    if (!profileId) return
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

  const events = useMemo(() => (deadlines ?? []).map(mapDeadlineToEvent), [deadlines])

  function handleViewChange(view) {
    setActiveView(view)
    calendarRef.current?.getApi().changeView(view)
  }

  function handleEventClick(clickInfo) {
    setSelectedDeadline(clickInfo.event.extendedProps)
    setIsPopupOpen(true)
  }

  let content

  if (isLoading && deadlines === null) {
    content = <CalendarSkeleton />
  } else if (errorMessage && deadlines === null) {
    content = (
      <div className="dash-error-block">
        <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />
        <button
          type="button"
          className="dash-retry-btn"
          onClick={fetchDeadlines}
          aria-label="Retry loading deadlines"
        >
          <RotateCw size={14} aria-hidden="true" />
          Retry
        </button>
      </div>
    )
  } else if (deadlines !== null && deadlines.length === 0) {
    content = (
      <div className="dash-empty-state">
        <CalendarDays size={40} className="dash-empty-icon" aria-hidden="true" />
        <h2 className="dash-empty-title">No Deadlines Yet</h2>
        <p className="dash-empty-subtitle">
          Start adding important application deadlines so OpportunIQ can remind you before they
          expire.
        </p>
        <button
          type="button"
          className="dash-empty-btn"
          onClick={() => setIsFormOpen(true)}
          aria-label="Add first deadline"
        >
          <Plus size={16} aria-hidden="true" />
          Add First Deadline
        </button>
      </div>
    )
  } else if (deadlines !== null) {
    content = (
      <>
        {errorMessage && (
          <div className="dash-error-block">
            <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />
            <button
              type="button"
              className="dash-retry-btn"
              onClick={fetchDeadlines}
              aria-label="Retry loading deadlines"
            >
              <RotateCw size={14} aria-hidden="true" />
              Retry
            </button>
          </div>
        )}

        <div className="deadline-calendar-wrapper">
          <Calendar
            ref={calendarRef}
            plugins={[dayGridPlugin, interactionPlugin, listPlugin, classicThemePlugin]}
            initialView={MONTH_VIEW}
            headerToolbar={{ left: 'prev,next today', center: 'title', right: '' }}
            events={events}
            eventClick={handleEventClick}
            eventDisplay="list-item"
            height="auto"
            dayMaxEvents={3}
          />
        </div>
      </>
    )
  }

  return (
    <div className="deadline-calendar-page">
      <div className="deadline-calendar-header">
        <div>
          <h1 className="deadline-calendar-title">Deadline Calendar</h1>
          <p className="deadline-calendar-subtitle">
            Track all interviews, applications, hackathons and important events.
          </p>
        </div>

        <div className="deadline-calendar-actions">
          <div className="deadline-view-toggle" role="group" aria-label="Calendar view">
            <button
              type="button"
              className={`deadline-view-btn${activeView === MONTH_VIEW ? ' deadline-view-btn-active' : ''}`}
              onClick={() => handleViewChange(MONTH_VIEW)}
              aria-pressed={activeView === MONTH_VIEW}
              aria-label="Month view"
            >
              <LayoutGrid size={15} aria-hidden="true" />
              Month
            </button>
            <button
              type="button"
              className={`deadline-view-btn${activeView === LIST_VIEW ? ' deadline-view-btn-active' : ''}`}
              onClick={() => handleViewChange(LIST_VIEW)}
              aria-pressed={activeView === LIST_VIEW}
              aria-label="List view"
            >
              <List size={15} aria-hidden="true" />
              List
            </button>
          </div>

          <button
            type="button"
            className="dash-toolbar-btn dash-toolbar-btn-primary"
            onClick={() => setIsFormOpen(true)}
            aria-label="Add a new deadline"
          >
            <Plus size={16} aria-hidden="true" />
            Add Deadline
          </button>
        </div>
      </div>

      {content}

      <DeadlineDetailPopup
        deadline={selectedDeadline}
        isOpen={isPopupOpen}
        onClose={() => setIsPopupOpen(false)}
      />

      <DeadlineForm isOpen={isFormOpen} onClose={() => setIsFormOpen(false)} />
    </div>
  )
}
