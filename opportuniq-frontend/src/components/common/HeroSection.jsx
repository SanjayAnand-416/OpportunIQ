import { ArrowRight, FileText, PenLine } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../constants/routes'
import HeroPreviewCard from './HeroPreviewCard'

export default function HeroSection() {
  return (
    <section className="hero-section">
      <div className="hero-grid">
        <div className="hero-copy">
          <p className="eyebrow">
            AI-powered opportunity discovery
          </p>
          <h1 className="hero-title">
            Personalized{' '}
            <span className="gradient-text">
              Opportunity Intelligence
            </span>{' '}
            for Every Student
          </h1>
          <p className="hero-subtitle">
            A unified AI platform that discovers internships, jobs and hackathons
            while intelligently tracking every important application deadline.
          </p>
          <div className="hero-actions">
            <Link
              to={ROUTES.UPLOAD}
              className="cta-button cta-primary"
              aria-label="Get started by uploading a resume"
            >
              <FileText size={16} aria-hidden="true" />
              Get Started with Resume
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <Link
              to={ROUTES.MANUAL}
              className="cta-button cta-secondary"
              aria-label="Set up profile manually"
            >
              <PenLine size={16} aria-hidden="true" />
              Set Up Manually
            </Link>
          </div>
        </div>
        <div className="preview-wrap">
          <HeroPreviewCard />
        </div>
      </div>
    </section>
  )
}
