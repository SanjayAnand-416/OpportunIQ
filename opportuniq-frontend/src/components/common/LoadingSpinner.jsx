import { Loader2 } from 'lucide-react'

export default function LoadingSpinner({ message, size = 22 }) {
  return (
    <div className="ui-loading-spinner" role="status" aria-live="polite">
      <Loader2 className="spinner" size={size} aria-hidden="true" />
      {message && <span>{message}</span>}
    </div>
  )
}

