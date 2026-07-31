import { BrainCircuit } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../constants/routes'

export default function Navbar() {
  return (
    <header className="navbar">
      <nav className="navbar__inner">
        <Link
          to={ROUTES.LANDING}
          className="navbar__brand"
          aria-label="OpportunIQ home"
        >
          <span className="navbar__icon">
            <BrainCircuit size={20} aria-hidden="true" />
          </span>
          OpportunIQ
        </Link>
        <Link to={ROUTES.DASHBOARD} className="navbar__link">
          Dashboard
        </Link>
      </nav>
    </header>
  )
}
