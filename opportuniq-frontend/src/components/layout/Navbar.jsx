import { BrainCircuit } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../constants/routes'

export default function Navbar() {
  return (
    <header className="navbar">
      <nav className="navbar-inner" aria-label="Primary navigation">
        <Link
          to={ROUTES.LANDING}
          className="brand-link"
          aria-label="OpportunIQ home"
        >
          <span className="brand-icon">
            <BrainCircuit size={20} aria-hidden="true" />
          </span>
          OpportunIQ
        </Link>
        <Link
          to={ROUTES.DASHBOARD}
          className="nav-button"
          aria-label="Open dashboard"
        >
          Dashboard
        </Link>
      </nav>
    </header>
  )
}
