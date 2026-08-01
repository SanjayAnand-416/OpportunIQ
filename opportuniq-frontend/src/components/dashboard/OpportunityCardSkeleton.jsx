export default function OpportunityCardSkeleton() {
  return (
    <div className="opportunity-card opportunity-card-skeleton" aria-hidden="true">
      <div className="opp-card-top">
        <span className="skeleton-block skeleton-avatar" />
        <div className="opp-card-heading">
          <span className="skeleton-block skeleton-line skeleton-line-title" />
          <span className="skeleton-block skeleton-line skeleton-line-company" />
        </div>
        <span className="skeleton-block skeleton-match" />
      </div>

      <div className="opp-card-meta">
        <span className="skeleton-block skeleton-chip" />
        <span className="skeleton-block skeleton-chip" />
        <span className="skeleton-block skeleton-chip" />
      </div>

      <div className="opp-card-skills">
        <span className="skeleton-block skeleton-chip skeleton-chip-sm" />
        <span className="skeleton-block skeleton-chip skeleton-chip-sm" />
        <span className="skeleton-block skeleton-chip skeleton-chip-sm" />
      </div>

      <div className="opp-card-actions">
        <span className="skeleton-block skeleton-btn-icon" />
        <span className="skeleton-block skeleton-btn" />
      </div>
    </div>
  )
}
