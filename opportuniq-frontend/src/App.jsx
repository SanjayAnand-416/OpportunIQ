import { Route, Routes } from 'react-router-dom'
import { ROUTES } from './constants/routes'
import Dashboard from './pages/Dashboard'
import DeadlineCalendar from './pages/DeadlineCalendar'
import Landing from './pages/Landing'
import ManualForm from './pages/ManualForm'
import Notifications from './pages/Notifications'
import ProfileReview from './pages/ProfileReview'
import ResumeUpload from './pages/ResumeUpload'
import SavedOpportunities from './pages/SavedOpportunities'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path={ROUTES.LANDING} element={<Landing />} />
      <Route path={ROUTES.UPLOAD} element={<ResumeUpload />} />
      <Route path={ROUTES.MANUAL} element={<ManualForm />} />
      <Route path={ROUTES.PROFILE_REVIEW} element={<ProfileReview />} />
      <Route path={ROUTES.DASHBOARD} element={<Dashboard />} />
      <Route path={ROUTES.DEADLINES} element={<DeadlineCalendar />} />
      <Route path={ROUTES.SAVED} element={<SavedOpportunities />} />
      <Route path={ROUTES.NOTIFICATIONS} element={<Notifications />} />
      <Route path={ROUTES.SETTINGS} element={<Settings />} />
    </Routes>
  )
}

export default App

