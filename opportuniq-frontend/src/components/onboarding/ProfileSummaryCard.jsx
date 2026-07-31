import { GraduationCap, MapPin, Target, UserRound } from 'lucide-react'
import Badge from '../common/Badge'

const fallback = 'Not Provided'

function SummaryRow({ icon: Icon, label, value }) {
  return (
    <div className="summary-row">
      <Icon size={18} aria-hidden="true" />
      <div>
        <p>{label}</p>
        <span>{value || fallback}</span>
      </div>
    </div>
  )
}

export default function ProfileSummaryCard({ profile }) {
  const initials = profile.fullName
    ? profile.fullName
        .split(' ')
        .map((part) => part[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : 'OI'

  return (
    <aside className="profile-summary-card" aria-labelledby="summary-title">
      <div className="profile-avatar" aria-hidden="true">
        {initials}
      </div>
      <h2 id="summary-title">{profile.fullName || fallback}</h2>
      <p className="summary-subtitle">
        {[profile.degree, profile.college].filter(Boolean).join(' · ') ||
          fallback}
      </p>

      <div className="summary-stack">
        <SummaryRow icon={GraduationCap} label="Degree" value={profile.degree} />
        <SummaryRow icon={UserRound} label="College" value={profile.college} />
        <SummaryRow
          icon={MapPin}
          label="Location"
          value={profile.preferredLocation}
        />
        <SummaryRow
          icon={Target}
          label="Opportunity Preference"
          value={profile.opportunityType}
        />
      </div>

      <div className="summary-tags">
        <p>Skills</p>
        <div>
          {profile.skills.length > 0
            ? profile.skills.map((skill) => (
                <Badge key={skill} variant="blue">
                  {skill}
                </Badge>
              ))
            : fallback}
        </div>
      </div>

      <div className="summary-tags">
        <p>Target Roles</p>
        <div>
          {profile.targetRoles.length > 0
            ? profile.targetRoles.map((role) => (
                <Badge key={role} variant="indigo">
                  {role}
                </Badge>
              ))
            : fallback}
        </div>
      </div>
    </aside>
  )
}
