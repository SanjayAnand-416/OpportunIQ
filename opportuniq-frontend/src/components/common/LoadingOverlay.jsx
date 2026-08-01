import LoadingSpinner from './LoadingSpinner'

export default function LoadingOverlay({ visible, message = 'Loading...' }) {
  if (!visible) return null

  return (
    <div className="ui-loading-overlay" role="status" aria-live="polite">
      <LoadingSpinner message={message} size={30} />
    </div>
  )
}

