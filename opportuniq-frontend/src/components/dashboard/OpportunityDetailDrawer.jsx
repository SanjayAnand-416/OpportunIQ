import {
  Briefcase,
  Building2,
  Calendar,
  CalendarPlus,
  CheckCircle,
  Clock,
  ExternalLink,
  Globe,
  Layers,
  Link as LinkIcon,
  MapPin,
  Send,
  X,
  XCircle,
  Bookmark,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import {
  formatDeadlineDate,
  getAvatarTone,
  getCompanyInitial,
  getDeadlineInfo,
  getMatchColor,
  getPlatformInfo,
} from '../../utils/opportunityCard'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input, textarea, select, [tabindex]:not([tabindex="-1"])'

const NOT_AVAILABLE = 'Not Available'

function DetailRow({ icon: Icon, label, children }) {
  return (
    <div className="drawer-detail-row">
      <span className="drawer-detail-icon" aria-hidden="true">
        <Icon size={16} />
      </span>
      <div className="drawer-detail-text">
        <p className="drawer-detail-label">{label}</p>
        <div className="drawer-detail-value">{children}</div>
      </div>
    </div>
  )
}

function MatchProgressBar({ percentage, tone }) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const frame = requestAnimationFrame(() => setWidth(percentage))
    return () => cancelAnimationFrame(frame)
  }, [percentage])

  return (
    <div
      className="drawer-progress-track"
      role="progressbar"
      aria-valuenow={Math.round(percentage)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Overall match percentage"
    >
      <div className={`drawer-progress-fill tone-${tone}`} style={{ width: `${width}%` }} />
    </div>
  )
}

function SkillMatchItem({ skill, matched }) {
  return (
    <li className={`drawer-skill-item${matched ? ' drawer-skill-matched' : ' drawer-skill-missing'}`}>
      {matched ? (
        <CheckCircle size={16} aria-hidden="true" />
      ) : (
        <XCircle size={16} aria-hidden="true" />
      )}
      <span>{skill}</span>
      <span className="sr-only">{matched ? 'matched' : 'not matched'}</span>
    </li>
  )
}

export default function OpportunityDetailDrawer({
  isOpen,
  opportunity,
  onClose,
  onApply,
  onSave,
  onAddDeadline,
}) {
  const drawerRef = useRef(null)
  const closeButtonRef = useRef(null)

  const matchPercentage = opportunity?.match_percentage
  const hasMatch = typeof matchPercentage === 'number' && !Number.isNaN(matchPercentage)

  useEffect(() => {
    if (!isOpen) return undefined

    const previouslyFocused = document.activeElement
    closeButtonRef.current?.focus()
    document.body.classList.add('no-scroll')

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose?.()
        return
      }

      if (event.key !== 'Tab') return

      const focusable = drawerRef.current?.querySelectorAll(FOCUSABLE_SELECTOR)
      if (!focusable || focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.classList.remove('no-scroll')
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus()
    }
  }, [isOpen, onClose])

  if (!opportunity) {
    return null
  }

  const {
    title,
    company,
    platform,
    location,
    deadline,
    url,
    also_on: alsoOn = [],
    required_skills: requiredSkills = [],
    matched_skills: matchedSkills = [],
    description,
    opportunity_type: opportunityType,
    source,
  } = opportunity

  const platformInfo = getPlatformInfo(platform)
  const deadlineInfo = getDeadlineInfo(deadline)
  const matchTone = getMatchColor(matchPercentage)
  const avatarTone = getAvatarTone(company)
  const formattedDeadline = formatDeadlineDate(deadline)

  const normalizedMatched = new Set(
    matchedSkills.map((skill) => skill.trim().toLowerCase()),
  )
  const matchedCount = requiredSkills.filter((skill) =>
    normalizedMatched.has(skill.trim().toLowerCase()),
  ).length

  return (
    <>
      <div
        className={`drawer-backdrop${isOpen ? ' drawer-backdrop-visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        ref={drawerRef}
        className={`opportunity-drawer${isOpen ? ' opportunity-drawer-open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        aria-hidden={!isOpen}
        {...(!isOpen ? { inert: '' } : {})}
      >
        <header className="drawer-header">
          <button
            type="button"
            className="drawer-close-btn"
            aria-label="Close opportunity details"
            onClick={onClose}
            ref={closeButtonRef}
            tabIndex={isOpen ? 0 : -1}
          >
            <X size={20} aria-hidden="true" />
          </button>

          <div className="drawer-header-top">
            <span
              className={`opp-avatar drawer-avatar tone-${avatarTone}`}
              role="img"
              aria-label={`${company} avatar`}
            >
              {getCompanyInitial(company)}
            </span>
            <div>
              <h2 id="drawer-title" className="drawer-title">
                {title}
              </h2>
              <p className="drawer-company">{company}</p>
            </div>
          </div>

          <div className="drawer-header-badges">
            <span className={`opp-badge tone-${platformInfo.tone}`}>{platformInfo.label}</span>
            {location && (
              <span className="opp-chip">
                <MapPin size={14} aria-hidden="true" />
                {location}
              </span>
            )}
            <span className={`opp-badge tone-${deadlineInfo.tone}`}>
              <Clock size={14} aria-hidden="true" />
              {deadlineInfo.label}
            </span>
            {hasMatch && (
              <span
                className={`opp-match-badge drawer-match-badge tone-${matchTone}`}
                aria-label={`Match score ${Math.round(matchPercentage)} percent`}
              >
                {Math.round(matchPercentage)}%
              </span>
            )}
          </div>
        </header>

        <div className="drawer-body">
          <section aria-labelledby="drawer-description-heading" className="drawer-section">
            <h3 id="drawer-description-heading" className="drawer-section-title">
              Job Description
            </h3>
            <div className="drawer-description">
              {description || 'No description provided for this opportunity.'}
            </div>
          </section>

          {hasMatch && (
            <section aria-labelledby="drawer-progress-heading" className="drawer-section">
              <h3 id="drawer-progress-heading" className="drawer-section-title">
                Match Progress
              </h3>
              {isOpen && <MatchProgressBar percentage={matchPercentage} tone={matchTone} />}
            </section>
          )}

          <section aria-labelledby="drawer-skills-heading" className="drawer-section">
            <h3 id="drawer-skills-heading" className="drawer-section-title">
              Skill Match Analysis
            </h3>
            {requiredSkills.length > 0 ? (
              <>
                <p className="drawer-skills-summary">
                  {matchedCount} of {requiredSkills.length} required skills matched.
                </p>
                <ul className="drawer-skills-list">
                  {requiredSkills.map((skill) => (
                    <SkillMatchItem
                      key={skill}
                      skill={skill}
                      matched={normalizedMatched.has(skill.trim().toLowerCase())}
                    />
                  ))}
                </ul>
              </>
            ) : (
              <p className="drawer-skills-summary">No skill data available.</p>
            )}
          </section>

          <section aria-labelledby="drawer-details-heading" className="drawer-section">
            <h3 id="drawer-details-heading" className="drawer-section-title">
              Details
            </h3>
            <div className="drawer-details-grid">
              <DetailRow icon={Layers} label="Platform">
                {platform || NOT_AVAILABLE}
              </DetailRow>
              <DetailRow icon={MapPin} label="Location">
                {location || NOT_AVAILABLE}
              </DetailRow>
              <DetailRow icon={Briefcase} label="Opportunity Type">
                {opportunityType || NOT_AVAILABLE}
              </DetailRow>
              <DetailRow icon={Calendar} label="Application Deadline">
                {formattedDeadline || NOT_AVAILABLE}
              </DetailRow>
              <DetailRow icon={Building2} label="Company">
                {company || NOT_AVAILABLE}
              </DetailRow>
              <DetailRow icon={Globe} label="Source">
                {source || NOT_AVAILABLE}
              </DetailRow>
              <DetailRow icon={LinkIcon} label="Website">
                {url ? (
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="drawer-detail-link"
                  >
                    Visit posting
                    <ExternalLink size={13} aria-hidden="true" />
                  </a>
                ) : (
                  NOT_AVAILABLE
                )}
              </DetailRow>
            </div>
          </section>

          {alsoOn.length > 0 && (
            <section aria-labelledby="drawer-also-on-heading" className="drawer-section">
              <h3 id="drawer-also-on-heading" className="drawer-section-title">
                Available on
              </h3>
              <div className="drawer-also-on">
                {alsoOn.map((altPlatform) => {
                  const altInfo = getPlatformInfo(altPlatform)
                  return (
                    <span
                      key={altPlatform}
                      className={`opp-badge opp-badge-sm tone-${altInfo.tone}`}
                    >
                      {altInfo.label}
                    </span>
                  )
                })}
              </div>
            </section>
          )}
        </div>

        <div className="drawer-actions">
          <button
            type="button"
            className="drawer-action-btn drawer-action-secondary"
            aria-label={`Save ${title}`}
            onClick={() => onSave?.(opportunity)}
          >
            <Bookmark size={16} aria-hidden="true" />
            Save Opportunity
          </button>
          <button
            type="button"
            className="drawer-action-btn drawer-action-outline"
            aria-label={`Add deadline reminder for ${title}`}
            onClick={() => onAddDeadline?.(opportunity)}
          >
            <CalendarPlus size={16} aria-hidden="true" />
            Add Deadline
          </button>
          <button
            type="button"
            className="drawer-action-btn drawer-action-primary"
            aria-label={`Apply to ${title} at ${company}`}
            onClick={() => onApply?.(opportunity)}
          >
            <Send size={16} aria-hidden="true" />
            Apply Now
          </button>
        </div>
      </aside>
    </>
  )
}
