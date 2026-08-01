import { ArrowRight, Clock, RotateCcw, Target } from 'lucide-react'
import { formatGapTimestamp } from '../../utils/gapAnalysis'

const statusClassNames = {
  Completed: 'gap-status-completed',
  Running: 'gap-status-running',
  Failed: 'gap-status-failed',
  Pending: 'gap-status-pending',
}

export default function GapAnalysisCard({
  analysisTypeLabel = 'Profile vs Target Role',
  title = 'Frontend Readiness Analysis',
  target = 'Target Role / Opportunity',
  readiness = '72%',
  status = 'Pending',
  startedAt = '',
  completedAt = '',
  onRetry,
  onViewAnalysis,
}) {
  const isCompleted = status === 'Completed'
  const isFailed = status === 'Failed'
  const actionLabel = isFailed ? 'Retry' : isCompleted ? 'View Analysis' : status === 'Running' ? 'In Progress' : 'Queued'
  const isActionDisabled = !isCompleted && !isFailed
  const handleAction = isFailed ? onRetry : onViewAnalysis

  return (
    <article className="gap-analysis-card" tabIndex={0}>
      <div className="gap-analysis-card-main">
        <span className="gap-card-icon" aria-hidden="true">
          <Target size={18} />
        </span>
        <div>
          <h3>{title}</h3>
          <p>{target}</p>
          <span className="gap-analysis-type">{analysisTypeLabel}</span>
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

      <dl className="gap-analysis-times">
        <div>
          <dt>Started</dt>
          <dd>{formatGapTimestamp(startedAt)}</dd>
        </div>
        <div>
          <dt>Completed</dt>
          <dd>{formatGapTimestamp(completedAt)}</dd>
        </div>
      </dl>

      <div className="gap-card-footer">
        <span>
          <Clock size={14} aria-hidden="true" />
          {status}
        </span>
        <button
          type="button"
          className="gap-card-action"
          onClick={handleAction}
          disabled={isActionDisabled}
          aria-label={`${actionLabel} for ${title}`}
        >
          {isFailed && <RotateCcw size={14} aria-hidden="true" />}
          {actionLabel}
          {!isFailed && <ArrowRight size={14} aria-hidden="true" />}
        </button>
      </div>
    </article>
  )
}
