import { Link } from 'react-router-dom'
import EmptyState from '../components/common/EmptyState'
import { ROUTES } from '../constants/routes'
import { SearchX } from 'lucide-react'

export default function NotFound() {
  return (
    <main className="not-found-page">
      <EmptyState
        Icon={SearchX}
        title="Page Not Found"
        subtitle="The page you are looking for does not exist or may have moved."
      />
      <div className="not-found-actions">
        <Link className="ui-btn ui-btn-primary" to={ROUTES.LANDING}>
          Go Home
        </Link>
        <Link className="ui-btn ui-btn-secondary" to={ROUTES.DASHBOARD}>
          Open Dashboard
        </Link>
      </div>
    </main>
  )
}

