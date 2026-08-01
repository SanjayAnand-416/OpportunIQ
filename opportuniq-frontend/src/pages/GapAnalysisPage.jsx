import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  ListChecks,
  Map,
  Target,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getGapAnalyses, getGapAnalysisErrorMessage, runGapAnalysis } from '../api/gapAnalysis'
import { getSavedOpportunities } from '../api/opportunities'
import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import Toast from '../components/common/Toast'
import AgentTracePanel from '../components/dashboard/AgentTracePanel'
import GapAnalysisCard from '../components/dashboard/GapAnalysisCard'
import GapAnalysisModal from '../components/dashboard/GapAnalysisModal'
import { GapAnalysisSkeleton, SummaryCardSkeleton } from '../components/dashboard/GapAnalysisSkeleton'
import GapQuickActions from '../components/dashboard/GapQuickActions'
import GapSummaryCard from '../components/dashboard/GapSummaryCard'
import { useAppContext } from '../contexts/AppContext'
import { useToast } from '../hooks/useToast'
import {
  filterGapAnalyses,
  GAP_ANALYSIS_STATUS_OPTIONS,
  normalizeGapAnalysesResponse,
  serializeGapRunPayload,
} from '../utils/gapAnalysis'
import { normalizeSavedOpportunities } from '../utils/savedOpportunities'

const summaryCards = [
  { label: 'Completed Analyses', value: 0, icon: CheckCircle2 },
  { label: 'Skills Identified', value: 0, icon: ListChecks },
  { label: 'Critical Skill Gaps', value: 0, icon: AlertTriangle },
  { label: 'Recommended Learning Paths', value: 0, icon: Map },
]

export default function GapAnalysisPage() {
  const navigate = useNavigate()
  const { profileId } = useAppContext()
  const [analyses, setAnalyses] = useState([])
  const [savedOpportunities, setSavedOpportunities] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [activeStatus, setActiveStatus] = useState('All')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalInitialConfig, setModalInitialConfig] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [traceSessionId, setTraceSessionId] = useState('')
  const [isTraceOpen, setIsTraceOpen] = useState(false)
  const [toastMessage, setToastMessage] = useToast()

  const loadAnalyses = useCallback(async () => {
    if (!profileId) {
      setAnalyses([])
      setError('Profile ID is missing. Please complete onboarding before running a gap analysis.')
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError('')
    try {
      const [gapData, savedData] = await Promise.all([
        getGapAnalyses(profileId),
        getSavedOpportunities(profileId),
      ])
      setAnalyses(normalizeGapAnalysesResponse(gapData))
      setSavedOpportunities(normalizeSavedOpportunities(savedData))
    } catch (requestError) {
      setError(getGapAnalysisErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(loadAnalyses)
  }, [loadAnalyses])

  const filteredAnalyses = useMemo(
    () => filterGapAnalyses(analyses, { query, status: activeStatus }),
    [activeStatus, analyses, query],
  )

  const recentAnalyses = filteredAnalyses.slice(0, 3)
  const summaryValues = useMemo(() => {
    const completed = analyses.filter((analysis) => analysis.status === 'Completed').length
    return {
      'Completed Analyses': completed,
      'Skills Identified': 0,
      'Critical Skill Gaps': 0,
      'Recommended Learning Paths': 0,
    }
  }, [analyses])

  function openAnalysisModal(initialConfig = null) {
    setModalInitialConfig(initialConfig)
    setIsModalOpen(true)
  }

  function closeAnalysisModal() {
    if (isSubmitting) return
    setIsModalOpen(false)
    setModalInitialConfig(null)
  }

  async function handleRunAnalysis(config) {
    if (!profileId) {
      setError('Profile ID is missing. Please complete onboarding before running a gap analysis.')
      return
    }

    setIsSubmitting(true)
    try {
      const payload = serializeGapRunPayload({ profileId, ...config })
      const response = await runGapAnalysis(payload)
      setToastMessage('Gap Analysis Started')
      setIsModalOpen(false)
      setTraceSessionId(response.session_id || response.sessionId)
      setIsTraceOpen(Boolean(response.session_id || response.sessionId))
    } catch (requestError) {
      setError(getGapAnalysisErrorMessage(requestError))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleTraceComplete = useCallback(() => {
    setToastMessage('Gap Analysis Completed')
    Promise.resolve().then(loadAnalyses)
  }, [loadAnalyses, setToastMessage])

  function handleRetryAnalysis(analysis) {
    openAnalysisModal({
      mode: analysis.analysisType,
      targetRole: analysis.targetRole || '',
      opportunityId: analysis.opportunityId || '',
      jobDescription: analysis.jobDescription || '',
    })
  }

  if (error) {
    return (
      <section className="gap-page" aria-labelledby="gap-error-title">
        <ErrorState
          title="Unable to load gap analyses."
          message={error}
          retryButton="Retry"
          onRetry={loadAnalyses}
        />
      </section>
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
        {isLoading
          ? summaryCards.map((card) => <SummaryCardSkeleton key={card.label} />)
          : summaryCards.map((card) => (
              <GapSummaryCard
                key={card.label}
                icon={card.icon}
                label={card.label}
                value={summaryValues[card.label] ?? card.value}
              />
            ))}
      </div>

      <div className="gap-toolbar" aria-label="Gap analysis search and filters">
        <label className="gap-search" htmlFor="gap-analysis-search">
          <span>Search analyses</span>
          <input
            id="gap-analysis-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by target, opportunity or type"
          />
        </label>
        <div className="gap-filter-chips" aria-label="Filter gap analyses by status">
          {GAP_ANALYSIS_STATUS_OPTIONS.map((status) => (
            <button
              key={status}
              type="button"
              className={activeStatus === status ? 'active' : ''}
              onClick={() => setActiveStatus(status)}
              aria-pressed={activeStatus === status}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      <div className="gap-main-grid">
        <section className="gap-section" aria-labelledby="recent-analyses-title">
          <div className="gap-section-header">
            <h2 id="recent-analyses-title">Recent Analyses</h2>
          </div>
          {isLoading ? (
            <div className="gap-analysis-list">
              <GapAnalysisSkeleton />
              <GapAnalysisSkeleton />
              <GapAnalysisSkeleton />
            </div>
          ) : recentAnalyses.length > 0 ? (
            <div className="gap-analysis-list">
              {recentAnalyses.map((analysis) => (
                <GapAnalysisCard
                  key={analysis.id || analysis.title}
                  {...analysis}
                  onRetry={() => handleRetryAnalysis(analysis)}
                  onViewAnalysis={() => navigate(`/dashboard/gap-analysis/${analysis.id}`)}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              Icon={Target}
              title="No Gap Analyses Yet"
              subtitle="Run your first AI-powered gap analysis to discover missing skills, learning priorities and personalized recommendations."
              primaryButton="Run First Analysis"
              onPrimaryClick={() => openAnalysisModal()}
            />
          )}
        </section>

        <GapQuickActions onRunAnalysis={() => openAnalysisModal()} />
      </div>

      <section className="gap-section" aria-labelledby="analysis-history-title">
        <div className="gap-section-header">
          <h2 id="analysis-history-title">Analysis History</h2>
        </div>
        {isLoading ? (
          <div className="gap-analysis-list">
            <GapAnalysisSkeleton />
            <GapAnalysisSkeleton />
          </div>
        ) : filteredAnalyses.length > 0 ? (
          <div className="gap-analysis-list">
            {filteredAnalyses.map((analysis) => (
              <GapAnalysisCard
                key={analysis.id || analysis.title}
                {...analysis}
                onRetry={() => handleRetryAnalysis(analysis)}
                onViewAnalysis={() => navigate(`/dashboard/gap-analysis/${analysis.id}`)}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            Icon={BrainCircuit}
            title="No Matching Analyses"
            subtitle="Adjust your search or filters to view previous gap analyses."
            primaryButton="Run First Analysis"
            onPrimaryClick={() => openAnalysisModal()}
          />
        )}
      </section>

      {isModalOpen && (
        <GapAnalysisModal
          isOpen={isModalOpen}
          isSubmitting={isSubmitting}
          savedOpportunities={savedOpportunities}
          initialConfig={modalInitialConfig}
          onClose={closeAnalysisModal}
          onSubmit={handleRunAnalysis}
        />
      )}
      <AgentTracePanel
        sessionId={traceSessionId}
        isOpen={isTraceOpen}
        onClose={() => setIsTraceOpen(false)}
        onComplete={handleTraceComplete}
      />
      <Toast message={toastMessage} type="success" />
    </section>
  )
}
