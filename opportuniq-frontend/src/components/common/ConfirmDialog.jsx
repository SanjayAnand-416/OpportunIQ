import { Loader2, Trash2 } from 'lucide-react'

export default function ConfirmDialog({
  message,
  confirmLabel = 'Delete',
  isLoading = false,
  onCancel,
  onConfirm,
}) {
  return (
    <div className="confirm-dialog" role="alertdialog" aria-live="assertive">
      <p className="confirm-dialog-message">{message}</p>
      <div className="confirm-dialog-actions">
        <button
          type="button"
          className="drawer-action-btn drawer-action-secondary"
          onClick={onCancel}
          disabled={isLoading}
          aria-label="Cancel"
        >
          Cancel
        </button>
        <button
          type="button"
          className="confirm-dialog-confirm-btn"
          onClick={onConfirm}
          disabled={isLoading}
          aria-label={confirmLabel}
        >
          {isLoading ? (
            <Loader2 size={15} className="trace-icon-spin" aria-hidden="true" />
          ) : (
            <Trash2 size={15} aria-hidden="true" />
          )}
          {isLoading ? 'Deleting...' : confirmLabel}
        </button>
      </div>
    </div>
  )
}
