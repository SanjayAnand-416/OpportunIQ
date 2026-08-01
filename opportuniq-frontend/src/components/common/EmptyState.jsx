export default function EmptyState({
  Icon,
  title,
  subtitle,
  primaryButton,
  secondaryButton,
  onPrimaryClick,
  onSecondaryClick,
}) {
  return (
    <div className="ui-empty-state">
      {Icon && (
        <span className="ui-state-icon" aria-hidden="true">
          <Icon size={30} />
        </span>
      )}
      <h2>{title}</h2>
      {subtitle && <p>{subtitle}</p>}
      {(primaryButton || secondaryButton) && (
        <div className="ui-state-actions">
          {primaryButton && (
            <button type="button" className="ui-btn ui-btn-primary" onClick={onPrimaryClick}>
              {primaryButton}
            </button>
          )}
          {secondaryButton && (
            <button type="button" className="ui-btn ui-btn-secondary" onClick={onSecondaryClick}>
              {secondaryButton}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

