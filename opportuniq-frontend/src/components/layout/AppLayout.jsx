import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import DashboardNavbar from './DashboardNavbar'
import PageContainer from './PageContainer'
import RightPanel from './RightPanel'
import Sidebar from './Sidebar'

export default function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div className="dashboard-shell">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      <div className="dashboard-main-column">
        <DashboardNavbar
          onMenuClick={() => setIsSidebarOpen(true)}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
        />

        <div className="dashboard-content-row">
          <main className="dashboard-main" id="main-content">
            <PageContainer>
              <Outlet context={{ searchQuery }} />
            </PageContainer>
          </main>

          <RightPanel />
        </div>
      </div>
    </div>
  )
}
