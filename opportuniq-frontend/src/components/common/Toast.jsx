import { AlertCircle, CheckCircle2, Info, TriangleAlert, X } from 'lucide-react'

const icons = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: TriangleAlert,
  info: Info,
}

export default function Toast({
  id,
  message,
  title,
  description,
  type = 'info',
  onDismiss,
}) {
  const contentTitle = title || message
  if (!contentTitle) return null

  const Icon = icons[type] || Info

  return (
    <div
      className={`toast toast-${type}${onDismiss ? '' : ' toast-standalone'}`}
      role={type === 'error' ? 'alert' : 'status'}
    >
      <Icon size={18} aria-hidden="true" />
      <div className="toast-body">
        <strong>{contentTitle}</strong>
        {description && <span>{description}</span>}
      </div>
      {onDismiss && (
        <button type="button" onClick={() => onDismiss(id)} aria-label="Dismiss toast">
          <X size={16} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
