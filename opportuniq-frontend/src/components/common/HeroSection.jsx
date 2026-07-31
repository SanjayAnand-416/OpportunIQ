import { ArrowRight, FileText, PenLine } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../constants/routes'

export default function HeroSection() {
  return (
    <section className="hero">
      <div className="hero__inner">
        <div className="hero__eyebrow">
          AI-powered opportunity discovery
        </div>
        <h1 className="hero__title">
          Personalized Opportunity Intelligence for Students
        </h1>
        <p className="hero__subtitle">
          Discover internships, jobs and hackathons tailored to your skills
          while never missing an important deadline.
        </p>
        <div className="hero__actions">
          <Link to={ROUTES.UPLOAD} className="button button--primary">
            <FileText size={16} aria-hidden="true" />
            Get Started with Resume
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
          <Link to={ROUTES.MANUAL} className="button button--secondary">
            <PenLine size={16} aria-hidden="true" />
            Set Up Manually
          </Link>
        </div>
        <div className="hero__illustration">
          <div className="hero__illustration-inner">
            AI Illustration Coming Soon
          </div>
        </div>
      </div>
    </section>
  )
}
