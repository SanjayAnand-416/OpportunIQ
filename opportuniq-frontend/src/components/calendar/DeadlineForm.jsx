import { Loader2, Save, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { createDeadline, getDeadlinesErrorMessage, updateDeadline } from '../../api/deadlines'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import {
  DEFAULT_DEADLINE_TIME,
  combineDateAndTime,
  getTodayDateString,
  isDateStringInPast,
  splitDeadlineDatetime,
} from '../../utils/deadlines'
import ErrorBanner from '../common/ErrorBanner'

const EVENT_TYPES = [
  'Interview',
  'Submission',
  'Offer Acceptance',
  'Assessment',
  'Hackathon',
  'Other',
]

const EMPTY_FORM = {
  title: '',
  organization: '',
  date: '',
  time: DEFAULT_DEADLINE_TIME,
  eventType: EVENT_TYPES[0],
  notes: '',
}

function buildInitialFormState(deadline) {
  if (!deadline) return EMPTY_FORM

  const { date, time } = splitDeadlineDatetime(deadline.deadline_datetime)
  return {
    title: deadline.title || '',
    organization: deadline.organization || '',
    date,
    time: time || DEFAULT_DEADLINE_TIME,
    eventType: deadline.event_type || EVENT_TYPES[0],
    notes: deadline.notes || '',
  }
}

function validateForm(form) {
  const errors = {}
  if (!form.title.trim()) errors.title = 'Title is required.'
  if (!form.organization.trim()) errors.organization = 'Organization is required.'
  if (!form.date) {
    errors.date = 'Date is required.'
  } else if (isDateStringInPast(form.date)) {
    errors.date = 'Date cannot be in the past.'
  }
  if (!form.time) errors.time = 'Time is required.'
  if (!form.eventType) errors.eventType = 'Event type is required.'
  return errors
}

export default function DeadlineForm({ isOpen, deadline, profileId, onClose, onSuccess }) {
  const panelRef = useRef(null)

  useFocusTrap(panelRef, isOpen, onClose)

  const isEditMode = Boolean(deadline?.id)

  const [form, setForm] = useState(() => buildInitialFormState(deadline))
  const [touched, setTouched] = useState({})
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const [wasOpen, setWasOpen] = useState(false)
  if (isOpen !== wasOpen) {
    setWasOpen(isOpen)
    if (isOpen) {
      setForm(buildInitialFormState(deadline))
      setTouched({})
      setHasAttemptedSubmit(false)
      setErrorMessage('')
    }
  }

  const errors = validateForm(form)
  const isValid = Object.keys(errors).length === 0

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function handleBlur(field) {
    setTouched((prev) => ({ ...prev, [field]: true }))
  }

  function fieldError(field) {
    return touched[field] || hasAttemptedSubmit ? errors[field] : ''
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setHasAttemptedSubmit(true)
    if (!isValid || isSubmitting) return

    setIsSubmitting(true)
    setErrorMessage('')

    const payload = {
      profile_id: profileId,
      title: form.title.trim(),
      organization: form.organization.trim(),
      deadline_datetime: combineDateAndTime(form.date, form.time),
      event_type: form.eventType,
      notes: form.notes.trim() || null,
    }

    try {
      if (isEditMode) {
        await updateDeadline(deadline.id, payload)
      } else {
        await createDeadline(payload)
      }
      onSuccess?.(isEditMode ? 'edit' : 'create')
    } catch (error) {
      setErrorMessage(getDeadlinesErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <div
        className={`drawer-backdrop${isOpen ? ' drawer-backdrop-visible' : ''}`}
        onClick={isSubmitting ? undefined : onClose}
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
            disabled={isSubmitting}
            aria-label={`Close ${isEditMode ? 'edit' : 'add'} deadline form`}
          >
            <X size={20} aria-hidden="true" />
          </button>
          <h2 id="deadline-form-title" className="deadline-form-title">
            {isEditMode ? 'Edit Deadline' : 'Add Deadline'}
          </h2>
        </header>

        <form
          id="deadline-form-element"
          className="deadline-form-body"
          onSubmit={handleSubmit}
          noValidate
        >
          {errorMessage && (
            <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />
          )}

          <fieldset className="deadline-form-fieldset" disabled={isSubmitting}>
            <div className="deadline-form-field">
              <label htmlFor="deadline-form-title-input">
                Title <span aria-hidden="true">*</span>
              </label>
              <input
                id="deadline-form-title-input"
                type="text"
                value={form.title}
                placeholder="e.g. Technical Interview"
                aria-required="true"
                aria-invalid={Boolean(fieldError('title'))}
                aria-describedby={fieldError('title') ? 'deadline-form-title-error' : undefined}
                onChange={(event) => updateField('title', event.target.value)}
                onBlur={() => handleBlur('title')}
              />
              {fieldError('title') && (
                <p id="deadline-form-title-error" className="deadline-form-error">
                  {fieldError('title')}
                </p>
              )}
            </div>

            <div className="deadline-form-field">
              <label htmlFor="deadline-form-org">
                Organization <span aria-hidden="true">*</span>
              </label>
              <input
                id="deadline-form-org"
                type="text"
                value={form.organization}
                placeholder="e.g. Google"
                aria-required="true"
                aria-invalid={Boolean(fieldError('organization'))}
                aria-describedby={
                  fieldError('organization') ? 'deadline-form-org-error' : undefined
                }
                onChange={(event) => updateField('organization', event.target.value)}
                onBlur={() => handleBlur('organization')}
              />
              {fieldError('organization') && (
                <p id="deadline-form-org-error" className="deadline-form-error">
                  {fieldError('organization')}
                </p>
              )}
            </div>

            <div className="deadline-form-row">
              <div className="deadline-form-field">
                <label htmlFor="deadline-form-date">
                  Date <span aria-hidden="true">*</span>
                </label>
                <input
                  id="deadline-form-date"
                  type="date"
                  value={form.date}
                  min={getTodayDateString()}
                  aria-required="true"
                  aria-invalid={Boolean(fieldError('date'))}
                  aria-describedby={fieldError('date') ? 'deadline-form-date-error' : undefined}
                  onChange={(event) => updateField('date', event.target.value)}
                  onBlur={() => handleBlur('date')}
                />
                {fieldError('date') && (
                  <p id="deadline-form-date-error" className="deadline-form-error">
                    {fieldError('date')}
                  </p>
                )}
              </div>
              <div className="deadline-form-field">
                <label htmlFor="deadline-form-time">
                  Time <span aria-hidden="true">*</span>
                </label>
                <input
                  id="deadline-form-time"
                  type="time"
                  value={form.time}
                  aria-required="true"
                  aria-invalid={Boolean(fieldError('time'))}
                  aria-describedby={fieldError('time') ? 'deadline-form-time-error' : undefined}
                  onChange={(event) => updateField('time', event.target.value)}
                  onBlur={() => handleBlur('time')}
                />
                {fieldError('time') && (
                  <p id="deadline-form-time-error" className="deadline-form-error">
                    {fieldError('time')}
                  </p>
                )}
              </div>
            </div>

            <div className="deadline-form-field">
              <label htmlFor="deadline-form-type">
                Event Type <span aria-hidden="true">*</span>
              </label>
              <select
                id="deadline-form-type"
                value={form.eventType}
                aria-required="true"
                onChange={(event) => updateField('eventType', event.target.value)}
                onBlur={() => handleBlur('eventType')}
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
                value={form.notes}
                placeholder="Optional notes"
                onChange={(event) => updateField('notes', event.target.value)}
              />
            </div>
          </fieldset>
        </form>

        <div className="deadline-form-actions">
          <button
            type="button"
            className="drawer-action-btn drawer-action-secondary"
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Cancel"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="deadline-form-element"
            className="drawer-action-btn drawer-action-primary"
            disabled={!isValid || isSubmitting}
            aria-label={isEditMode ? 'Save changes' : 'Save deadline'}
          >
            {isSubmitting ? (
              <Loader2 size={16} className="trace-icon-spin" aria-hidden="true" />
            ) : (
              <Save size={16} aria-hidden="true" />
            )}
            {isSubmitting ? 'Saving...' : 'Save Deadline'}
          </button>
        </div>
      </aside>
    </>
  )
}
