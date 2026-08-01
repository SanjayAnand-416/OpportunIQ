import { AlertCircle } from 'lucide-react'

export default function ErrorState({
  Icon = AlertCircle,
  title = 'Something went wrong',
  message,
  retryButton = 'Retry',
  secondaryButton,
  onRetry,
  onSecondaryClick,
}) {
  return (
    <div className="ui-error-state" role="alert">
      <span className="ui-state-icon ui-state-icon-error" aria-hidden="true">
        <Icon size={30} />
      </span>
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      <div className="ui-state-actions">
        {onRetry && (
          <button type="button" className="ui-btn ui-btn-primary" onClick={onRetry}>
            {retryButton}
          </button>
        )}
        {secondaryButton && (
          <button type="button" className="ui-btn ui-btn-secondary" onClick={onSecondaryClick}>
            {secondaryButton}
          </button>
        )}
      </div>
    </div>
  )
}

