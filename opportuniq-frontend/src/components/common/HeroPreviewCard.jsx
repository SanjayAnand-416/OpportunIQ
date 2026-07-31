import { CalendarClock, CheckCircle2, Sparkles } from 'lucide-react'
import Badge from './Badge'

const skills = ['Python', 'React', 'Machine Learning']
const skillVariants = ['blue', 'indigo', 'default']

export default function HeroPreviewCard() {
  return (
    <aside
      className="preview-card"
      aria-label="Opportunity match preview"
    >
      <div className="preview-shell">
        <div className="preview-header">
          <div className="preview-title-row">
            <div className="preview-icon">
              <Sparkles size={20} aria-hidden="true" />
            </div>
            <div>
              <p className="preview-label">Opportunity Match</p>
              <h2 className="preview-title">
                Google STEP Internship
              </h2>
            </div>
          </div>
          <Badge variant="green">92% Match</Badge>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">
              <CalendarClock size={16} aria-hidden="true" />
              Deadline
            </div>
            <p className="stat-value">3 days left</p>
          </div>
          <div className="stat-card">
            <div className="stat-label">
              <CheckCircle2 size={16} aria-hidden="true" />
              Fit Signal
            </div>
            <p className="stat-value stat-value-indigo">Strong</p>
          </div>
        </div>

        <div className="preview-panel">
          <p className="skills-title">Skills</p>
          <div className="skills-row">
            {skills.map((skill, index) => (
              <Badge key={skill} variant={skillVariants[index]}>
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </aside>
  )
}
