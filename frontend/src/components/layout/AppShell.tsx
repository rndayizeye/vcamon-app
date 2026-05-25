import { Outlet } from 'react-router-dom'

import { AuthStatusBanner } from '../../auth/AuthStatusBanner'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function AppShell() {
  return (
    <div className="app-shell">
      <TopBar />
      <div className="app-body">
        <Sidebar />
        <main className="page-content stack-lg">
          <AuthStatusBanner />
          <Outlet />
        </main>
      </div>
    </div>
  )
}
