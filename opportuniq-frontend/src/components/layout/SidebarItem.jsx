import { NavLink } from 'react-router-dom'

export default function SidebarItem({ path, label, icon: Icon, end, onNavigate }) {
  return (
    <li className="sidebar-item">
      <NavLink
        to={path}
        end={end}
        onClick={onNavigate}
        className={({ isActive }) =>
          `sidebar-link${isActive ? ' sidebar-link-active' : ''}`
        }
      >
        <Icon className="sidebar-link-icon" size={20} aria-hidden="true" />
        <span className="sidebar-link-label">{label}</span>
      </NavLink>
    </li>
  )
}
