import { useAppContext } from '../../contexts/AppContext'
import DeadlineMiniCalendar from '../dashboard/DeadlineMiniCalendar'
import GmailConnectCard from '../dashboard/GmailConnectCard'

export default function RightPanel() {
  const { profileId } = useAppContext()

  if (!profileId) {
    return null
  }

  return (
    <aside className="right-panel" aria-label="Utility panel">
      <GmailConnectCard profileId={profileId} />
      <DeadlineMiniCalendar profileId={profileId} />
    </aside>
  )
}
