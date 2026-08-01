import { Bell, Bookmark, CalendarClock, Compass, Settings } from 'lucide-react'
import { ROUTES } from './routes'

export const NAV_ITEMS = [
  {
    label: 'Discover',
    path: ROUTES.DASHBOARD,
    icon: Compass,
    title: 'Discover Opportunities',
    end: true,
  },
  {
    label: 'Saved',
    path: ROUTES.SAVED,
    icon: Bookmark,
    title: 'Saved Opportunities',
  },
  {
    label: 'Deadlines',
    path: ROUTES.DEADLINES,
    icon: CalendarClock,
    title: 'Deadline Calendar',
  },
  {
    label: 'Notifications',
    path: ROUTES.NOTIFICATIONS,
    icon: Bell,
    title: 'Notifications',
  },
  {
    label: 'Settings',
    path: ROUTES.SETTINGS,
    icon: Settings,
    title: 'Settings',
  },
]
