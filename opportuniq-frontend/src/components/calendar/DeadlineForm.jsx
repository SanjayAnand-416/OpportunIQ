import { CalendarPlus, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'

const EVENT_TYPES = ['Interview', 'Application', 'Hackathon', 'Offer', 'Other']
const DEFAULT_TIME = '23:59'

export default function DeadlineForm({ isOpen, onClose }) {
  const panelRef = useRef(null)

  useFocusTrap(panelRef, isOpen, onClose)

  const [title, setTitle] = useState('')
  const [organization, setOrganization] = useState('')
  const [date, setDate] = useState('')
  const [time, setTime] = useState(DEFAULT_TIME)
  const [eventType, setEventType] = useState(EVENT_TYPES[0])
  const [notes, setNotes] = useState('')

  return (
    <>
      <div
        className={`drawer-backdrop${isOpen ? ' drawer-backdrop-visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        ref={panelRef}
        className={`deadline-form-panel${isOpen ? ' deadline-form-panel-open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="deadline-form-title"
        aria-hidden={!isOpen}
        {...(!isOpen ? { inert: '' } : {})}
      >
        <header className="deadline-form-header">
          <button
            type="button"
            className="drawer-close-btn"
            onClick={onClose}
            aria-label="Close add deadline form"
          >
            <X size={20} aria-hidden="true" />
          </button>
          <h2 id="deadline-form-title" className="deadline-form-title">
            Add Deadline
          </h2>
        </header>

        <form className="deadline-form-body" onSubmit={(event) => event.preventDefault()}>
          <div className="deadline-form-field">
            <label htmlFor="deadline-form-title-input">Title</label>
            <input
              id="deadline-form-title-input"
              type="text"
              value={title}
              placeholder="e.g. Technical Interview"
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>

          <div className="deadline-form-field">
            <label htmlFor="deadline-form-org">Organization</label>
            <input
              id="deadline-form-org"
              type="text"
              value={organization}
              placeholder="e.g. Google"
              onChange={(event) => setOrganization(event.target.value)}
            />
          </div>

          <div className="deadline-form-row">
            <div className="deadline-form-field">
              <label htmlFor="deadline-form-date">Date</label>
              <input
                id="deadline-form-date"
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
              />
            </div>
            <div className="deadline-form-field">
              <label htmlFor="deadline-form-time">Time</label>
              <input
                id="deadline-form-time"
                type="time"
                value={time}
                onChange={(event) => setTime(event.target.value)}
              />
            </div>
          </div>

          <div className="deadline-form-field">
            <label htmlFor="deadline-form-type">Event Type</label>
            <select
              id="deadline-form-type"
              value={eventType}
              onChange={(event) => setEventType(event.target.value)}
            >
              {EVENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div className="deadline-form-field">
            <label htmlFor="deadline-form-notes">Notes</label>
            <textarea
              id="deadline-form-notes"
              rows={4}
              value={notes}
              placeholder="Optional notes"
              onChange={(event) => setNotes(event.target.value)}
            />
          </div>
        </form>

        <div className="deadline-form-actions">
          <button
            type="button"
            className="drawer-action-btn drawer-action-secondary"
            onClick={onClose}
            aria-label="Cancel adding deadline"
          >
            Cancel
          </button>
          <button
            type="button"
            className="drawer-action-btn drawer-action-primary"
            disabled
            aria-label="Save deadline, coming soon"
          >
            <CalendarPlus size={16} aria-hidden="true" />
            Save Deadline
          </button>
        </div>
      </aside>
    </>
  )
}
