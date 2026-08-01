import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  ListChecks,
  Map,
  Target,
} from 'lucide-react'
import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import GapAnalysisCard from '../components/dashboard/GapAnalysisCard'
import GapQuickActions from '../components/dashboard/GapQuickActions'
import GapSummaryCard from '../components/dashboard/GapSummaryCard'

const summaryCards = [
  { label: 'Completed Analyses', value: 0, icon: CheckCircle2 },
  { label: 'Skills Identified', value: 0, icon: ListChecks },
  { label: 'Critical Skill Gaps', value: 0, icon: AlertTriangle },
  { label: 'Recommended Learning Paths', value: 0, icon: Map },
]

const placeholderAnalyses = [
  {
    title: 'Frontend Developer Readiness',
    target: 'Target Role: Frontend Engineer',
    readiness: 'Pending',
    status: 'Pending',
    lastUpdated: 'Awaiting first run',
  },
  {
    title: 'AI/ML Internship Skill Map',
    target: 'Opportunity: AI Research Internship',
    readiness: 'Pending',
    status: 'Pending',
    lastUpdated: 'Awaiting first run',
  },
  {
    title: 'Hackathon Profile Gap Scan',
    target: 'Goal: National-level hackathons',
    readiness: 'Pending',
    status: 'Pending',
    lastUpdated: 'Awaiting first run',
  },
]

export default function GapAnalysisPage() {
  const isLoading = false
  const error = ''
  const analyses = placeholderAnalyses

  if (error) {
    return (
      <ErrorState
        title="Unable to load gap analyses."
        message="Please retry when the Gap Analysis API is available."
        onRetry={() => {}}
      />
    )
  }

  return (
    <section className="gap-page" aria-labelledby="gap-page-title">
      <header className="gap-page-header">
        <div>
          <h1 id="gap-page-title">Gap Advisor</h1>
          <p>
            Analyze your current skills, identify missing competencies and
            receive AI-generated learning recommendations tailored to your career
            goals.
          </p>
        </div>
        <span className="gap-page-icon" aria-hidden="true">
          <BrainCircuit size={28} />
        </span>
      </header>

      <div className="gap-summary-grid">
        {summaryCards.map((card) => (
          <GapSummaryCard
            key={card.label}
            icon={card.icon}
            label={card.label}
            value={card.value}
          />
        ))}
      </div>

      <div className="gap-main-grid">
        <section className="gap-section" aria-labelledby="recent-analyses-title">
          <div className="gap-section-header">
            <h2 id="recent-analyses-title">Recent Analyses</h2>
          </div>
          {isLoading ? null : analyses.length > 0 ? (
            <div className="gap-analysis-list">
              {analyses.map((analysis) => (
                <GapAnalysisCard key={analysis.title} {...analysis} />
              ))}
            </div>
          ) : (
            <EmptyState
              Icon={Target}
              title="No Gap Analyses Yet"
              subtitle="Run your first AI-powered gap analysis to discover missing skills, learning priorities and personalized recommendations."
              primaryButton="Run First Analysis"
            />
          )}
        </section>

        <GapQuickActions />
      </div>

      <section className="gap-section" aria-labelledby="analysis-history-title">
        <div className="gap-section-header">
          <h2 id="analysis-history-title">Analysis History</h2>
        </div>
        <EmptyState
          Icon={BrainCircuit}
          title="History Coming Soon"
          subtitle="Completed analyses will appear here once the Gap Analysis Agent is connected."
        />
      </section>
    </section>
  )
}
