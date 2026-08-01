import { Building2, Calendar, Clock, FileText, Pencil, Tag, Trash2, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { deleteDeadline, getDeadlinesErrorMessage } from '../../api/deadlines'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import {
  calculateRemainingTime,
  formatDeadlineTime,
  formatFullDate,
  isPastDeadline,
} from '../../utils/deadlines'
import ConfirmDialog from '../common/ConfirmDialog'
import ErrorBanner from '../common/ErrorBanner'

export default function DeadlineDetailPopup({ deadline, isOpen, onClose, onEdit, onDeleted }) {
  const popupRef = useRef(null)

  useFocusTrap(popupRef, isOpen, onClose)

  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const [wasOpen, setWasOpen] = useState(false)
  if (isOpen !== wasOpen) {
    setWasOpen(isOpen)
    if (isOpen) {
      setIsConfirmingDelete(false)
      setIsDeleting(false)
      setErrorMessage('')
    }
  }

  if (!deadline) {
    return null
  }

  const {
    id,
    title,
    organization,
    deadline_datetime: deadlineDatetime,
    event_type: eventType,
    notes,
  } = deadline

  const remaining = calculateRemainingTime(deadlineDatetime)
  const expired = isPastDeadline(deadlineDatetime)

  async function handleConfirmDelete() {
    setIsDeleting(true)
    setErrorMessage('')
    try {
      await deleteDeadline(id)
      onDeleted?.(id)
    } catch (error) {
      setErrorMessage(getDeadlinesErrorMessage(error))
      setIsDeleting(false)
    }
  }

  return (
    <>
      <div
        className={`drawer-backdrop${isOpen ? ' drawer-backdrop-visible' : ''}`}
        onClick={isDeleting ? undefined : onClose}
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
          disabled={isDeleting}
          aria-label="Close deadline details"
        >
          <X size={18} aria-hidden="true" />
        </button>

        <h2 id="deadline-popup-title" className="deadline-popup-title">
          {title}
        </h2>

        {errorMessage && (
          <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />
        )}

        {isConfirmingDelete ? (
          <ConfirmDialog
            message="Are you sure you want to delete this deadline?"
            confirmLabel="Delete"
            isLoading={isDeleting}
            onCancel={() => setIsConfirmingDelete(false)}
            onConfirm={handleConfirmDelete}
          />
        ) : (
          <>
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
                {formatFullDate(deadlineDatetime)}
              </span>
              <span className="deadline-popup-row">
                <Clock size={14} aria-hidden="true" />
                {formatDeadlineTime(deadlineDatetime) || 'No specific time'}
              </span>
              <span
                className={`deadline-popup-row deadline-popup-remaining${
                  expired ? ' deadline-popup-remaining-expired' : ''
                }`}
              >
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

            <div className="deadline-popup-actions">
              <button
                type="button"
                className="drawer-action-btn drawer-action-secondary"
                onClick={() => onEdit?.(deadline)}
                aria-label="Edit deadline"
              >
                <Pencil size={15} aria-hidden="true" />
                Edit
              </button>
              <button
                type="button"
                className="deadline-popup-delete-btn"
                onClick={() => setIsConfirmingDelete(true)}
                aria-label="Delete deadline"
              >
                <Trash2 size={15} aria-hidden="true" />
                Delete
              </button>
              <button
                type="button"
                className="drawer-action-btn drawer-action-secondary"
                onClick={onClose}
                aria-label="Close"
              >
                Close
              </button>
            </div>
          </>
        )}
      </div>
    </>
  )
}
