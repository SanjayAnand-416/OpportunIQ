import { BookOpen, Sparkles } from 'lucide-react'

export default function GapQuickActions({ onRunAnalysis }) {
  return (
    <section className="gap-quick-actions" aria-labelledby="gap-quick-actions-title">
      <h2 id="gap-quick-actions-title">Quick Actions</h2>
      <p>Available in the next update</p>
      <div className="gap-quick-action-list">
        <button type="button" onClick={onRunAnalysis} aria-label="Run new gap analysis">
          <Sparkles size={16} aria-hidden="true" />
          Run New Analysis
          <span>Start</span>
        </button>
        <button type="button" disabled aria-label="View learning resources coming soon">
          <BookOpen size={16} aria-hidden="true" />
          View Learning Resources
          <span>Coming Soon</span>
        </button>
      </div>
    </section>
  )
}
