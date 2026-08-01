import { ArrowRight, Clock, Target } from 'lucide-react'

const statusClassNames = {
  Completed: 'gap-status-completed',
  Running: 'gap-status-running',
  Failed: 'gap-status-failed',
  Pending: 'gap-status-pending',
}

export default function GapAnalysisCard({
  title = 'Frontend Readiness Analysis',
  target = 'Target Role / Opportunity',
  readiness = '72%',
  status = 'Pending',
  lastUpdated = 'Not run yet',
  actionLabel = 'View Details',
  onAction,
}) {
  return (
    <article className="gap-analysis-card" tabIndex={0}>
      <div className="gap-analysis-card-main">
        <span className="gap-card-icon" aria-hidden="true">
          <Target size={18} />
        </span>
        <div>
          <h3>{title}</h3>
          <p>{target}</p>
        </div>
      </div>

      <div className="gap-card-meta">
        <div>
          <span>Overall Readiness</span>
          <strong>{readiness}</strong>
        </div>
        <span className={`gap-status-badge ${statusClassNames[status] || statusClassNames.Pending}`}>
          {status}
        </span>
      </div>

      <div className="gap-card-footer">
        <span>
          <Clock size={14} aria-hidden="true" />
          {lastUpdated}
        </span>
        <button
          type="button"
          className="gap-card-action"
          onClick={onAction}
          aria-label={`${actionLabel} for ${title}`}
        >
          {actionLabel}
          <ArrowRight size={14} aria-hidden="true" />
        </button>
      </div>
    </article>
  )
}

