import { CheckCircle2 } from 'lucide-react'

export default function SuccessState({
  Icon = CheckCircle2,
  title,
  subtitle,
  actionButton,
  onAction,
}) {
  return (
    <div className="ui-success-state" role="status">
      <span className="ui-state-icon ui-state-icon-success" aria-hidden="true">
        <Icon size={30} />
      </span>
      <h2>{title}</h2>
      {subtitle && <p>{subtitle}</p>}
      {actionButton && (
        <button type="button" className="ui-btn ui-btn-primary" onClick={onAction}>
          {actionButton}
        </button>
      )}
    </div>
  )
}

