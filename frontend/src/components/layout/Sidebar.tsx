import { NavLink } from 'react-router-dom'

export function Sidebar() {
  return (
    <aside className="sidebar">
      <nav className="stack-xs" aria-label="Primary navigation">
        <NavLink
          to="/cases"
          className={({ isActive }) =>
            isActive ? 'sidebar-link sidebar-link-active' : 'sidebar-link'
          }
        >
          Cases
        </NavLink>
        <NavLink
          to="/quick-ghost"
          className={({ isActive }) =>
            isActive ? 'sidebar-link sidebar-link-active' : 'sidebar-link'
          }
        >
          Quick Ghost
        </NavLink>
        <NavLink
          to="/transmission-chain"
          className={({ isActive }) =>
            isActive ? 'sidebar-link sidebar-link-active' : 'sidebar-link'
          }
        >
          Transmission Chain
        </NavLink>
      </nav>
    </aside>
  )
}
