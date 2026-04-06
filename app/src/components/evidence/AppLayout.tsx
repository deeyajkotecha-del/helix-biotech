import { Outlet, useLocation, useNavigate } from 'react-router-dom'

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Search', icon: SearchIcon },
    { path: '/companies', label: 'Companies', icon: CompaniesIcon },
    { path: '/directory', label: 'Directory', icon: DirectoryIcon },
    { path: '/enrichment', label: 'Enrichment', icon: EnrichmentIcon },
    { path: '/global', label: 'Global', icon: GlobalIcon },
    { path: '/forecaster', label: 'Forecaster', icon: ForecasterIcon },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <div className="app-layout">
      {/* Left Sidebar */}
      <nav className="app-sidebar">
        <a href="/" className="app-sidebar-logo">
          Satya<span>Bio</span>
        </a>

        <div className="app-sidebar-nav">
          {navItems.map(item => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`app-nav-item ${isActive(item.path) ? 'active' : ''}`}
            >
              <span className="app-nav-icon">
                <item.icon />
              </span>
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        <div className="app-sidebar-divider"></div>

        <div className="app-sidebar-section-label">Recent Searches</div>
        <div className="app-sidebar-nav">
          {/* Placeholder for recent searches - can be populated later */}
          <div style={{ padding: '8px 12px', fontSize: '12px', color: 'var(--ev-text-light)' }}>
            No recent searches
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  )
}

// SVG Icons
function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8"></circle>
      <path d="m21 21-4.35-4.35"></path>
    </svg>
  )
}

function CompaniesIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7"></rect>
      <rect x="14" y="3" width="7" height="7"></rect>
      <rect x="3" y="14" width="7" height="7"></rect>
      <rect x="14" y="14" width="7" height="7"></rect>
    </svg>
  )
}

function DirectoryIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
      <circle cx="9" cy="7" r="4"></circle>
      <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
    </svg>
  )
}

function EnrichmentIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"></circle>
      <path d="M12 6v6l4 2"></path>
    </svg>
  )
}

function GlobalIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"></circle>
      <path d="M2 12h20"></path>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
    </svg>
  )
}

function ForecasterIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 3v18h18"></path>
      <path d="M7 16l4-8 4 4 4-10"></path>
    </svg>
  )
}
