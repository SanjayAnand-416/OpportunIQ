import { AlertCircle, X } from 'lucide-react'

export default function ErrorBanner({ message, onDismiss }) {
  if (!message) {
    return null
  }

  return (
    <div className="error-banner" role="alert">
      <AlertCircle size={20} aria-hidden="true" />
      <p>{message}</p>
      <button
        type="button"
        className="error-dismiss"
        onClick={onDismiss}
        aria-label="Dismiss error"
      >
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  )
}
