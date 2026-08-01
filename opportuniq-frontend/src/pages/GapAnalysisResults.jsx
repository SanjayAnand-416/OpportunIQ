import {
  ArrowLeft,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  ListChecks,
  RefreshCw,
  TriangleAlert,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getGapAnalysis, getGapAnalysisErrorMessage } from '../api/gapAnalysis'
import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import LoadingOverlay from '../components/common/LoadingOverlay'
import SkeletonCard from '../components/common/SkeletonCard'
import {
  calculateReadinessColor,
  formatGapTimestamp,
  groupSkillsByPriority,
  normalizeGapAnalysisResult,
  getReadinessInterpretation,
} from '../utils/gapAnalysis'

function ResultsHeader({ analysis, onRefresh, isRefreshing }) {
  return (
    <header className="gap-results-header">
      <button
        type="button"
        className="gap-back-button"
        onClick={onRefresh.goBack}
        aria-label="Return to Gap Advisor"
      >
        <ArrowLeft size={16} aria-hidden="true" />
        Gap Advisor
      </button>
      <div className="gap-results-title-row">
        <div>
          <h1 id="gap-results-title">{analysis.title}</h1>
          <p>{analysis.target}</p>
          <div className="gap-results-meta">
            <span>{analysis.analysisTypeLabel}</span>
            <span>{formatGapTimestamp(analysis.startedAt)}</span>
            <span className={`gap-status-badge gap-status-${analysis.status.toLowerCase()}`}>
              {analysis.status}
            </span>
          </div>
        </div>
        <div className="gap-results-actions">
          <button
            type="button"
            className="gap-card-action"
            onClick={onRefresh.reload}
            disabled={isRefreshing}
            aria-label="Refresh gap analysis results"
          >
            <RefreshCw size={15} aria-hidden="true" />
            Refresh
          </button>
          <button
            type="button"
            className="gap-card-action"
            disabled
            aria-label="Download report coming soon"
          >
            <Download size={15} aria-hidden="true" />
            Coming Soon
          </button>
        </div>
      </div>
    </header>
  )
}

function ReadinessScore({ score }) {
  const tone = calculateReadinessColor(score)

  return (
    <section className="gap-readiness-card" aria-labelledby="readiness-title">
      <span className={`gap-score-circle score-${tone}`} aria-label={`Overall readiness ${score}%`}>
        {score}%
      </span>
      <div>
        <h2 id="readiness-title">Overall Readiness</h2>
        <strong>{getReadinessInterpretation(score)}</strong>
        <p>Your profile alignment based on matched, partial and missing skills.</p>
      </div>
    </section>
  )
}

function ResultSummaryCards({ analysis }) {
  const cards = [
    { label: 'Skills Matched', value: analysis.existingSkills.length, Icon: CheckCircle2 },
    { label: 'Skills Missing', value: analysis.missingSkills.length, Icon: TriangleAlert },
    { label: 'Partial Skills', value: analysis.partialSkills.length, Icon: ListChecks },
    { label: 'Learning Resources', value: analysis.resources.length, Icon: BookOpen },
  ]

  return (
    <div className="gap-result-summary-grid">
      {cards.map(({ label, value, Icon }) => (
        <article className="gap-summary-card" key={label}>
          <span aria-hidden="true">
            <Icon size={18} />
          </span>
          <div>
            <strong>{value}</strong>
            <p>{label}</p>
          </div>
        </article>
      ))}
    </div>
  )
}

function SkillStatusChip({ status }) {
  return <span className={`gap-skill-chip gap-skill-${status.toLowerCase()}`}>{status}</span>
}

function PriorityChip({ priority }) {
  return <span className={`gap-priority-chip priority-${priority.toLowerCase()}`}>{priority}</span>
}

function EvidenceBadge({ evidence }) {
  return <span className="gap-evidence-badge">{evidence}</span>
}

function SkillMatrix({ skills }) {
  return (
    <section className="gap-section" aria-labelledby="skill-matrix-title">
      <div className="gap-section-header">
        <h2 id="skill-matrix-title">Skill Gap Matrix</h2>
      </div>
      <div className="gap-skill-matrix">
        <div className="gap-skill-row gap-skill-row-header">
          <span>Skill</span>
          <span>Status</span>
          <span>Priority</span>
          <span>Evidence</span>
        </div>
        {skills.map((skill) => (
          <div className="gap-skill-row" key={`${skill.name}-${skill.status}`}>
            <strong>{skill.name}</strong>
            <SkillStatusChip status={skill.status} />
            <PriorityChip priority={skill.priority} />
            <EvidenceBadge evidence={skill.evidence} />
          </div>
        ))}
      </div>
    </section>
  )
}

function PrioritySkills({ skills }) {
  const grouped = useMemo(() => groupSkillsByPriority(skills), [skills])

  return (
    <section className="gap-section" aria-labelledby="priority-skills-title">
      <div className="gap-section-header">
        <h2 id="priority-skills-title">Priority Skills</h2>
      </div>
      <div className="gap-priority-groups">
        {Object.entries(grouped).map(([priority, items]) => (
          <div key={priority}>
            <h3>{priority} Priority</h3>
            <div className="gap-chip-list">
              {items.length > 0 ? (
                items.map((skill) => (
                  <span key={skill.name} className={`gap-priority-chip priority-${priority.toLowerCase()}`}>
                    {skill.name}
                  </span>
                ))
              ) : (
                <span className="gap-muted-text">No skills</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function LearningRoadmap({ steps }) {
  return (
    <section className="gap-section" aria-labelledby="learning-roadmap-title">
      <div className="gap-section-header">
        <h2 id="learning-roadmap-title">Learning Roadmap</h2>
      </div>
      <ol className="gap-roadmap">
        {steps.map((step) => (
          <li key={step.id}>
            <span className={step.completed ? 'completed' : ''}>{step.stepNumber}</span>
            <div>
              <h3>{step.skill}</h3>
              <strong>{step.duration}</strong>
              <p>{step.description}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

function SuggestedProjects({ projects }) {
  return (
    <section className="gap-section" aria-labelledby="suggested-projects-title">
      <div className="gap-section-header">
        <h2 id="suggested-projects-title">Suggested Projects</h2>
      </div>
      <div className="gap-project-grid">
        {projects.map((project) => (
          <article className="gap-project-card" key={project.id}>
            <h3>{project.name}</h3>
            <div className="gap-project-meta">
              <span>{project.difficulty}</span>
              <span>{project.duration}</span>
            </div>
            <p>{project.description}</p>
            <div className="gap-chip-list">
              {project.skills.map((skill) => (
                <span className="gap-skill-chip gap-skill-matched" key={skill}>
                  {skill}
                </span>
              ))}
            </div>
            <button type="button" className="gap-card-action" aria-label={`View details for ${project.name}`}>
              View Details
            </button>
          </article>
        ))}
      </div>
    </section>
  )
}

function LearningResources({ resources }) {
  return (
    <section className="gap-section" aria-labelledby="learning-resources-title">
      <div className="gap-section-header">
        <h2 id="learning-resources-title">Learning Resources</h2>
      </div>
      <div className="gap-resource-list">
        {resources.map((resource) => (
          <article className="gap-resource-card" key={resource.id}>
            <span className="gap-card-icon" aria-hidden="true">
              <FileText size={17} />
            </span>
            <div>
              <h3>{resource.title}</h3>
              <p>{resource.provider}</p>
              <div className="gap-project-meta">
                <span>{resource.type}</span>
                <span>{resource.duration}</span>
              </div>
            </div>
            <button
              type="button"
              className="gap-card-action"
              onClick={() => window.open(resource.url, '_blank', 'noopener,noreferrer')}
              disabled={!resource.url}
              aria-label={`Open ${resource.title}`}
            >
              Open Resource
              <ExternalLink size={14} aria-hidden="true" />
            </button>
          </article>
        ))}
      </div>
    </section>
  )
}

function SkillDistribution({ analysis }) {
  const total = Math.max(analysis.skillMatrix.length, 1)
  const rows = [
    ['Matched Skills', analysis.existingSkills.length],
    ['Partial Skills', analysis.partialSkills.length],
    ['Missing Skills', analysis.missingSkills.length],
  ]

  return (
    <section className="gap-section" aria-labelledby="skill-distribution-title">
      <div className="gap-section-header">
        <h2 id="skill-distribution-title">Skill Distribution</h2>
      </div>
      <div className="gap-progress-list">
        {rows.map(([label, value]) => (
          <label key={label}>
            <span>{label}</span>
            <progress value={value} max={total}>
              {value}
            </progress>
          </label>
        ))}
      </div>
    </section>
  )
}

function ResultsSkeleton() {
  return (
    <section className="gap-page" aria-label="Loading gap analysis results">
      <SkeletonCard lines={4} />
      <div className="gap-results-top-grid">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={3} />
      </div>
      <div className="gap-results-two-column">
        <SkeletonCard lines={6} />
        <SkeletonCard lines={6} />
      </div>
      <div className="gap-results-two-column">
        <SkeletonCard lines={5} />
        <SkeletonCard lines={5} />
      </div>
      <SkeletonCard lines={6} />
    </section>
  )
}

export default function GapAnalysisResults() {
  const { analysisId } = useParams()
  const navigate = useNavigate()
  const [analysis, setAnalysis] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState('')

  const loadAnalysis = useCallback(async ({ refreshing = false } = {}) => {
    if (!analysisId) {
      setAnalysis(null)
      setError('The requested gap analysis could not be found.')
      setIsLoading(false)
      return
    }

    if (refreshing) setIsRefreshing(true)
    else setIsLoading(true)
    setError('')

    try {
      const data = await getGapAnalysis(analysisId)
      setAnalysis(normalizeGapAnalysisResult(data))
    } catch (requestError) {
      setError(getGapAnalysisErrorMessage(requestError))
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [analysisId])

  useEffect(() => {
    Promise.resolve().then(loadAnalysis)
  }, [loadAnalysis])

  if (isLoading) return <ResultsSkeleton />

  if (error) {
    return (
      <section className="gap-page">
        <ErrorState
          title="Unable to load analysis results."
          message={error}
          retryButton="Retry"
          secondaryButton="Return to Gap Advisor"
          onRetry={loadAnalysis}
          onSecondaryClick={() => navigate('/dashboard/gap-analysis')}
        />
      </section>
    )
  }

  if (!analysis) {
    return (
      <section className="gap-page">
        <EmptyState
          Icon={BrainCircuit}
          title="Analysis Not Available"
          subtitle="The requested gap analysis could not be found."
          primaryButton="Return to Gap Advisor"
          onPrimaryClick={() => navigate('/dashboard/gap-analysis')}
        />
      </section>
    )
  }

  return (
    <section className="gap-page gap-results-page" aria-labelledby="gap-results-title">
      <ResultsHeader
        analysis={analysis}
        isRefreshing={isRefreshing}
        onRefresh={{
          reload: () => loadAnalysis({ refreshing: true }),
          goBack: () => navigate('/dashboard/gap-analysis'),
        }}
      />

      <div className="gap-results-top-grid">
        <ReadinessScore score={analysis.readinessScore} />
        <ResultSummaryCards analysis={analysis} />
      </div>

      <div className="gap-results-two-column">
        <SkillMatrix skills={analysis.skillMatrix} />
        <PrioritySkills skills={analysis.missingSkills} />
      </div>

      <SkillDistribution analysis={analysis} />

      <div className="gap-results-two-column">
        <LearningRoadmap steps={analysis.roadmap} />
        <SuggestedProjects projects={analysis.suggestedProjects} />
      </div>

      <LearningResources resources={analysis.resources} />

      <section className="gap-section" aria-labelledby="analysis-summary-title">
        <div className="gap-section-header">
          <h2 id="analysis-summary-title">Analysis Summary</h2>
        </div>
        <p className="gap-analysis-summary">{analysis.summary || 'Not Provided'}</p>
      </section>

      <LoadingOverlay visible={isRefreshing} message="Refreshing gap analysis..." />
    </section>
  )
}
