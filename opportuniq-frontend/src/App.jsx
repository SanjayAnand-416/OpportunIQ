import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import LoadingSpinner from './components/common/LoadingSpinner'
import { ROUTES } from './constants/routes'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const DeadlineCalendar = lazy(() => import('./pages/DeadlineCalendar'))
const Landing = lazy(() => import('./pages/Landing'))
const ManualForm = lazy(() => import('./pages/ManualForm'))
const Notifications = lazy(() => import('./pages/Notifications'))
const NotFound = lazy(() => import('./pages/NotFound'))
const ProfileReview = lazy(() => import('./pages/ProfileReview'))
const ResumeUpload = lazy(() => import('./pages/ResumeUpload'))
const SavedOpportunities = lazy(() => import('./pages/SavedOpportunities'))
const Settings = lazy(() => import('./pages/Settings'))

function App() {
  return (
    <Suspense
      fallback={
        <main className="route-loading">
          <LoadingSpinner message="Loading OpportunIQ..." size={28} />
        </main>
      }
    >
      <Routes>
        <Route path={ROUTES.LANDING} element={<Landing />} />
        <Route path={ROUTES.UPLOAD} element={<ResumeUpload />} />
        <Route path={ROUTES.MANUAL} element={<ManualForm />} />
        <Route path={ROUTES.PROFILE_REVIEW} element={<ProfileReview />} />
        <Route element={<AppLayout />}>
          <Route path={ROUTES.DASHBOARD} element={<Dashboard />} />
          <Route path={ROUTES.DEADLINES} element={<DeadlineCalendar />} />
          <Route path={ROUTES.SAVED} element={<SavedOpportunities />} />
          <Route path={ROUTES.NOTIFICATIONS} element={<Notifications />} />
          <Route path={ROUTES.SETTINGS} element={<Settings />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}

export default App
