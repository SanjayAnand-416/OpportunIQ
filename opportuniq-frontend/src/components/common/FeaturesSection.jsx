import { BellRing, Search, Sparkles } from 'lucide-react'
import FeatureCard from './FeatureCard'

const FEATURES = [
  {
    icon: Search,
    title: 'Discover Opportunities',
    description: 'Find internships, jobs and hackathons from multiple platforms.',
    accent: 'accent-blue',
  },
  {
    icon: Sparkles,
    title: 'AI Skill Matching',
    description: 'Rank opportunities according to your profile and skills.',
    accent: 'accent-indigo',
  },
  {
    icon: BellRing,
    title: 'Deadline Guardian',
    description:
      'Track important application deadlines and receive smart reminders.',
    accent: 'accent-sky',
  },
]

export default function FeaturesSection() {
  return (
    <section className="features-section">
      <div className="section-inner">
        <div className="section-heading">
          <h2 className="section-title">
            Everything You Need
          </h2>
          <p className="section-subtitle">
            Discover opportunities, understand your skill match and never miss
            an important deadline.
          </p>
        </div>
        <div className="features-grid">
          {FEATURES.map((feature) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
              accent={feature.accent}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
