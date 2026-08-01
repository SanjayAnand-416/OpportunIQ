import { BrainCircuit, X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { NAV_ITEMS } from '../../constants/navigation'
import { ROUTES } from '../../constants/routes'
import SidebarItem from './SidebarItem'

const STUDENT_NAME = 'Alex Johnson'
const STUDENT_EMAIL = 'alex.johnson@example.edu'

function getInitials(name) {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export default function Sidebar({ isOpen, onClose }) {
  const closeButtonRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return undefined

    closeButtonRef.current?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  return (
    <>
      <div
        className={`sidebar-backdrop${isOpen ? ' sidebar-backdrop-visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        id="dashboard-sidebar"
        className={`sidebar${isOpen ? ' sidebar-open' : ''}`}
      >
        <div className="sidebar-header">
          <Link
            to={ROUTES.DASHBOARD}
            className="sidebar-brand"
            aria-label="OpportunIQ home"
          >
            <span className="sidebar-brand-icon">
              <BrainCircuit size={20} aria-hidden="true" />
            </span>
            <span className="sidebar-brand-name">OpportunIQ</span>
          </Link>
          <button
            type="button"
            className="sidebar-close-btn"
            aria-label="Close menu"
            onClick={onClose}
            ref={closeButtonRef}
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Primary">
          <ul className="sidebar-nav-list">
            {NAV_ITEMS.map((item) => (
              <SidebarItem
                key={item.path}
                path={item.path}
                label={item.label}
                icon={item.icon}
                end={item.end}
                onNavigate={onClose}
              />
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <span className="sidebar-user-avatar" aria-hidden="true">
              {getInitials(STUDENT_NAME)}
            </span>
            <span className="sidebar-user-info">
              <span className="sidebar-user-name">{STUDENT_NAME}</span>
              <span className="sidebar-user-email">{STUDENT_EMAIL}</span>
            </span>
          </div>
        </div>
      </aside>
    </>
  )
}
