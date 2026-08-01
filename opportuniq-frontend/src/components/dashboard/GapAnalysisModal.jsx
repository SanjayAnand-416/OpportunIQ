import { BriefcaseBusiness, FileText, Sparkles, Target, X } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { GAP_ANALYSIS_MODES } from '../../utils/gapAnalysis'

const roleSuggestions = [
  'Machine Learning Engineer',
  'Software Engineer',
  'Data Scientist',
  'Backend Developer',
  'Frontend Developer',
  'Cloud Engineer',
]

const modeOptions = [
  {
    value: GAP_ANALYSIS_MODES.TARGET_ROLE,
    title: 'Profile vs Target Role',
    description: 'Compare your current skills with a career goal.',
    Icon: Target,
  },
  {
    value: GAP_ANALYSIS_MODES.SAVED_OPPORTUNITY,
    title: 'Profile vs Saved Opportunity',
    description: 'Analyze readiness for an opportunity you saved.',
    Icon: BriefcaseBusiness,
  },
  {
    value: GAP_ANALYSIS_MODES.JOB_DESCRIPTION,
    title: 'Profile vs Job Description',
    description: 'Paste a role description for a custom gap scan.',
    Icon: FileText,
  },
]

const defaultConfig = {
  mode: GAP_ANALYSIS_MODES.TARGET_ROLE,
  targetRole: '',
  opportunityId: '',
  jobDescription: '',
}

export default function GapAnalysisModal({
  isOpen,
  isSubmitting,
  savedOpportunities = [],
  initialConfig,
  onClose,
  onSubmit,
}) {
  const modalRef = useRef(null)
  const [config, setConfig] = useState(() => ({ ...defaultConfig, ...initialConfig }))

  useFocusTrap(modalRef, isOpen, isSubmitting ? undefined : onClose)

  const validationMessage = useMemo(() => getValidationMessage(config), [config])
  const isValid = !validationMessage

  function updateConfig(field, value) {
    setConfig((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (!isValid || isSubmitting) return
    onSubmit?.(config)
  }

  return (
    <>
      <div className="gap-modal-backdrop" onClick={isSubmitting ? undefined : onClose} aria-hidden="true" />
      <div
        ref={modalRef}
        className="gap-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="gap-modal-title"
      >
        <form className="gap-modal-card" onSubmit={handleSubmit}>
          <header className="gap-modal-header">
            <div>
              <span className="gap-modal-kicker">
                <Sparkles size={15} aria-hidden="true" />
                AI Gap Advisor
              </span>
              <h2 id="gap-modal-title">Run AI Gap Analysis</h2>
            </div>
            <button
              type="button"
              className="gap-modal-close"
              onClick={onClose}
              disabled={isSubmitting}
              aria-label="Close gap analysis configuration"
            >
              <X size={18} aria-hidden="true" />
            </button>
          </header>

          <fieldset className="gap-mode-grid" disabled={isSubmitting}>
            <legend>Choose analysis mode</legend>
            {modeOptions.map(({ value, title, description, Icon }) => (
              <label key={value} className="gap-mode-option">
                <input
                  type="radio"
                  name="gap-analysis-mode"
                  value={value}
                  checked={config.mode === value}
                  onChange={(event) => updateConfig('mode', event.target.value)}
                />
                <span aria-hidden="true">
                  <Icon size={17} />
                </span>
                <strong>{title}</strong>
                <small>{description}</small>
              </label>
            ))}
          </fieldset>

          {config.mode === GAP_ANALYSIS_MODES.TARGET_ROLE && (
            <div className="gap-form-group">
              <label htmlFor="gap-target-role">Target Role</label>
              <input
                id="gap-target-role"
                type="text"
                list="gap-target-role-suggestions"
                value={config.targetRole}
                onChange={(event) => updateConfig('targetRole', event.target.value)}
                placeholder="Machine Learning Engineer"
                disabled={isSubmitting}
                required
              />
              <datalist id="gap-target-role-suggestions">
                {roleSuggestions.map((role) => (
                  <option key={role} value={role} />
                ))}
              </datalist>
            </div>
          )}

          {config.mode === GAP_ANALYSIS_MODES.SAVED_OPPORTUNITY && (
            <div className="gap-form-group">
              <label htmlFor="gap-saved-opportunity">Saved Opportunity</label>
              <select
                id="gap-saved-opportunity"
                value={config.opportunityId}
                onChange={(event) => updateConfig('opportunityId', event.target.value)}
                disabled={isSubmitting || savedOpportunities.length === 0}
                required
              >
                <option value="">Select an opportunity</option>
                {savedOpportunities.map((opportunity) => (
                  <option key={opportunity.id || opportunity.savedId} value={opportunity.id}>
                    {[opportunity.company, opportunity.title].filter(Boolean).join(' - ')}
                  </option>
                ))}
              </select>
              {savedOpportunities.length === 0 && (
                <p className="gap-form-help">Save an opportunity first to use this mode.</p>
              )}
            </div>
          )}

          {config.mode === GAP_ANALYSIS_MODES.JOB_DESCRIPTION && (
            <div className="gap-form-group">
              <label htmlFor="gap-job-description">Job Description</label>
              <textarea
                id="gap-job-description"
                value={config.jobDescription}
                onChange={(event) => updateConfig('jobDescription', event.target.value)}
                placeholder="Paste the complete job description here."
                disabled={isSubmitting}
                rows={7}
                required
              />
              <p className="gap-form-help">{config.jobDescription.trim().length}/100 characters minimum</p>
            </div>
          )}

          {validationMessage && <p className="gap-validation-message">{validationMessage}</p>}

          <footer className="gap-modal-actions">
            <button
              type="button"
              className="gap-modal-secondary"
              onClick={onClose}
              disabled={isSubmitting}
              aria-label="Cancel gap analysis"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="gap-modal-primary"
              disabled={!isValid || isSubmitting}
              aria-label="Run AI gap analysis"
            >
              {isSubmitting ? 'Starting Analysis...' : 'Run Analysis'}
            </button>
          </footer>
        </form>
      </div>
    </>
  )
}

function getValidationMessage(config) {
  if (config.mode === GAP_ANALYSIS_MODES.TARGET_ROLE && !config.targetRole.trim()) {
    return 'Target role is required.'
  }

  if (config.mode === GAP_ANALYSIS_MODES.SAVED_OPPORTUNITY && !config.opportunityId) {
    return 'Choose a saved opportunity.'
  }

  if (
    config.mode === GAP_ANALYSIS_MODES.JOB_DESCRIPTION &&
    config.jobDescription.trim().length < 100
  ) {
    return 'Job description must be at least 100 characters.'
  }

  return ''
}
