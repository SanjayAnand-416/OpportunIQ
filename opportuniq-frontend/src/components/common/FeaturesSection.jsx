import { BellRing, Search, Sparkles } from 'lucide-react'
import FeatureCard from './FeatureCard'

const FEATURES = [
  {
    icon: Search,
    title: 'Discover Opportunities',
    description: 'Find internships, jobs and hackathons from multiple platforms.',
  },
  {
    icon: Sparkles,
    title: 'AI Skill Matching',
    description: 'Rank opportunities according to your profile and skills.',
  },
  {
    icon: BellRing,
    title: 'Deadline Guardian',
    description:
      'Track important application deadlines and receive smart reminders.',
  },
]

export default function FeaturesSection() {
  return (
    <section className="features">
      <div className="features__inner">
        <h2 className="features__title">Everything You Need</h2>
        <div className="features__grid">
          {FEATURES.map((feature) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
