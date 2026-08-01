import { AlertTriangle, CheckCircle2, Loader2, X } from 'lucide-react'
import { useRef } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'

export default function ConfirmationDialog({
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'primary',
  isOpen = true,
  isLoading = false,
  onConfirm,
  onCancel,
}) {
  const dialogRef = useRef(null)
  useFocusTrap(dialogRef, isOpen, onCancel)

  if (!isOpen) return null

  const Icon = confirmVariant === 'danger' || confirmVariant === 'warning' ? AlertTriangle : CheckCircle2

  return (
    <div className="ui-dialog-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="ui-confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirmation-title"
        aria-describedby="confirmation-message"
        ref={dialogRef}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="ui-dialog-close"
          onClick={onCancel}
          disabled={isLoading}
          aria-label="Close confirmation dialog"
        >
          <X size={18} aria-hidden="true" />
        </button>
        <span className={`ui-dialog-icon ui-dialog-${confirmVariant}`} aria-hidden="true">
          <Icon size={24} />
        </span>
        <h2 id="confirmation-title">{title}</h2>
        <p id="confirmation-message">{message}</p>
        <div className="ui-dialog-actions">
          <button
            type="button"
            className="ui-btn ui-btn-secondary"
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={`ui-btn ui-btn-${confirmVariant}`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading && <Loader2 className="spinner" size={16} aria-hidden="true" />}
            {confirmText}
          </button>
        </div>
      </section>
    </div>
  )
}

