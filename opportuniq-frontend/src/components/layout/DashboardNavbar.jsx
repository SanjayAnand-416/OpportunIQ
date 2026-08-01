import { Bell, Menu, Search } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { NAV_ITEMS } from '../../constants/navigation'

function usePageTitle() {
  const { pathname } = useLocation()
  const activeItem = NAV_ITEMS.find((item) => item.path === pathname)
  return activeItem?.title ?? 'Dashboard'
}

export default function DashboardNavbar({ onMenuClick, searchQuery, onSearchQueryChange }) {
  const title = usePageTitle()

  return (
    <header className="dash-navbar">
      <div className="dash-navbar-left">
        <button
          type="button"
          className="dash-navbar-menu-btn"
          aria-label="Open menu"
          aria-controls="dashboard-sidebar"
          onClick={onMenuClick}
        >
          <Menu size={20} aria-hidden="true" />
        </button>
        <h1 className="dash-navbar-title">{title}</h1>
      </div>

      <div className="dash-navbar-right">
        <div className="dash-search">
          <Search className="dash-search-icon" size={16} aria-hidden="true" />
          <label htmlFor="dashboard-search" className="sr-only">
            Search opportunities
          </label>
          <input
            id="dashboard-search"
            type="search"
            className="dash-search-input"
            placeholder="Search opportunities..."
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
          />
        </div>

        <button
          type="button"
          className="dash-icon-btn"
          aria-label="Notifications"
        >
          <Bell size={18} aria-hidden="true" />
        </button>

        <span className="dash-navbar-avatar" aria-hidden="true">
          AJ
        </span>
      </div>
    </header>
  )
}
