import { Bookmark, Clock, ExternalLink, MapPin } from 'lucide-react'
import {
  getAvatarTone,
  getCompanyInitial,
  getDeadlineInfo,
  getMatchColor,
  getPlatformInfo,
} from '../../utils/opportunityCard'

const MAX_VISIBLE_SKILLS = 3

function stopPropagation(event) {
  event.stopPropagation()
}

export default function OpportunityCard({ opportunity, onCardClick }) {
  const {
    title,
    company,
    platform,
    location,
    match_percentage: matchPercentage,
    deadline,
    url,
    also_on: alsoOn = [],
    required_skills: requiredSkills = [],
    saved = false,
  } = opportunity

  const platformInfo = getPlatformInfo(platform)
  const deadlineInfo = getDeadlineInfo(deadline)
  const matchTone = getMatchColor(matchPercentage)
  const avatarTone = getAvatarTone(company)
  const hasMatch = typeof matchPercentage === 'number' && !Number.isNaN(matchPercentage)

  const visibleSkills = requiredSkills.slice(0, MAX_VISIBLE_SKILLS)
  const hiddenSkillCount = requiredSkills.length - visibleSkills.length

  function handleCardClick() {
    onCardClick?.(opportunity)
  }

  function handleKeyDown(event) {
    if (event.target !== event.currentTarget) return
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onCardClick?.(opportunity)
    }
  }

  return (
    <article
      className="opportunity-card"
      role="button"
      tabIndex={0}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      aria-label={`View details for ${title} at ${company}`}
    >
      <div className="opp-card-top">
        <span
          className={`opp-avatar tone-${avatarTone}`}
          role="img"
          aria-label={`${company} avatar`}
        >
          {getCompanyInitial(company)}
        </span>

        <div className="opp-card-heading">
          <h3 className="opp-card-title">{title}</h3>
          <p className="opp-card-company">{company}</p>
        </div>

        {hasMatch && (
          <span
            className={`opp-match-badge tone-${matchTone}`}
            aria-label={`Match score ${Math.round(matchPercentage)} percent`}
          >
            {Math.round(matchPercentage)}%
          </span>
        )}
      </div>

      <div className="opp-card-meta">
        {location && (
          <span className="opp-chip">
            <MapPin size={14} aria-hidden="true" />
            {location}
          </span>
        )}

        <span className={`opp-badge tone-${platformInfo.tone}`}>{platformInfo.label}</span>

        <span className={`opp-badge tone-${deadlineInfo.tone}`}>
          <Clock size={14} aria-hidden="true" />
          {deadlineInfo.label}
        </span>
      </div>

      {visibleSkills.length > 0 && (
        <div className="opp-card-skills">
          {visibleSkills.map((skill) => (
            <span key={skill} className="opp-chip opp-chip-skill">
              {skill}
            </span>
          ))}
          {hiddenSkillCount > 0 && (
            <span className="opp-chip opp-chip-skill opp-chip-more">+{hiddenSkillCount}</span>
          )}
        </div>
      )}

      {alsoOn.length > 0 && (
        <div className="opp-card-also-on">
          <span className="opp-also-on-label">Also on:</span>
          {alsoOn.map((altPlatform) => {
            const altInfo = getPlatformInfo(altPlatform)
            return (
              <span key={altPlatform} className={`opp-badge opp-badge-sm tone-${altInfo.tone}`}>
                {altInfo.label}
              </span>
            )
          })}
        </div>
      )}

      <div className="opp-card-actions">
        <button
          type="button"
          className="opp-bookmark-btn"
          aria-label={saved ? `Remove ${title} from saved opportunities` : `Save ${title}`}
          aria-pressed={saved}
          onClick={stopPropagation}
        >
          <Bookmark size={16} aria-hidden="true" fill={saved ? 'currentColor' : 'none'} />
        </button>

        {url ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="opp-apply-btn"
            aria-label={`Apply to ${title} at ${company}, opens in a new tab`}
            onClick={stopPropagation}
          >
            Apply Now
            <ExternalLink size={14} aria-hidden="true" />
          </a>
        ) : (
          <button
            type="button"
            className="opp-apply-btn"
            disabled
            aria-label="Apply link unavailable"
            onClick={stopPropagation}
          >
            Apply Now
          </button>
        )}
      </div>
    </article>
  )
}
