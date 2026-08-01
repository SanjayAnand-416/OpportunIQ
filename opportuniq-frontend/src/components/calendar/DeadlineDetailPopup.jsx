import { Building2, Calendar, Clock, FileText, Tag, X } from 'lucide-react'
import { useRef } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { formatDeadlineDate, getDeadlineSummaryLine } from '../../utils/deadlines'

export default function DeadlineDetailPopup({ deadline, isOpen, onClose }) {
  const popupRef = useRef(null)

  useFocusTrap(popupRef, isOpen, onClose)

  if (!deadline) {
    return null
  }

  const {
    title,
    organization,
    deadline_datetime: deadlineDatetime,
    event_type: eventType,
    notes,
  } = deadline

  const { label, time } = formatDeadlineDate(deadlineDatetime)
  const remaining = getDeadlineSummaryLine(deadlineDatetime)

  return (
    <>
      <div
        className={`drawer-backdrop${isOpen ? ' drawer-backdrop-visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={popupRef}
        className={`deadline-popup${isOpen ? ' deadline-popup-open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="deadline-popup-title"
        aria-hidden={!isOpen}
        {...(!isOpen ? { inert: '' } : {})}
      >
        <button
          type="button"
          className="deadline-popup-close"
          onClick={onClose}
          aria-label="Close deadline details"
        >
          <X size={18} aria-hidden="true" />
        </button>

        <h2 id="deadline-popup-title" className="deadline-popup-title">
          {title}
        </h2>

        <div className="deadline-popup-meta">
          {organization && (
            <span className="deadline-popup-row">
              <Building2 size={14} aria-hidden="true" />
              {organization}
            </span>
          )}
          {eventType && (
            <span className="deadline-popup-row">
              <Tag size={14} aria-hidden="true" />
              {eventType}
            </span>
          )}
          <span className="deadline-popup-row">
            <Calendar size={14} aria-hidden="true" />
            {label}
            {time ? ` • ${time}` : ''}
          </span>
          <span className="deadline-popup-row">
            <Clock size={14} aria-hidden="true" />
            {remaining}
          </span>
        </div>

        {notes && (
          <div className="deadline-popup-notes">
            <h3 className="deadline-popup-notes-title">
              <FileText size={14} aria-hidden="true" />
              Notes
            </h3>
            <p>{notes}</p>
          </div>
        )}
      </div>
    </>
  )
}
