import { CalendarClock, Mail } from 'lucide-react'
import RightPanelCard from './RightPanelCard'

export default function RightPanel() {
  return (
    <aside className="right-panel" aria-label="Utility panel">
      <RightPanelCard title="Gmail Integration" icon={Mail}>
        <p className="right-panel-placeholder">Component Coming Next</p>
      </RightPanelCard>

      <RightPanelCard title="Upcoming Deadlines" icon={CalendarClock}>
        <p className="right-panel-placeholder">Component Coming Next</p>
      </RightPanelCard>
    </aside>
  )
}
