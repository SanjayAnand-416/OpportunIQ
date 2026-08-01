import ConfirmationDialog from './ConfirmationDialog'

export default function ConfirmDialog({
  message,
  confirmLabel = 'Delete',
  isLoading = false,
  onCancel,
  onConfirm,
}) {
  return (
    <ConfirmationDialog
      title={confirmLabel}
      message={message}
      confirmText={isLoading ? 'Deleting...' : confirmLabel}
      confirmVariant="danger"
      isLoading={isLoading}
      onCancel={onCancel}
      onConfirm={onConfirm}
    />
  )
}
