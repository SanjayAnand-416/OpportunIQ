import {
  Bell,
  BellRing,
  BriefcaseBusiness,
  CalendarClock,
  CheckCircle2,
  Gift,
  Laptop,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getNotifications,
  getNotificationsErrorMessage,
  markAllNotificationsRead,
  markNotificationRead,
} from '../api/notifications'
import ErrorBanner from '../components/common/ErrorBanner'
import { useAppContext } from '../contexts/AppContext'
import {
  filterNotifications,
  formatRelativeTime,
  getNotificationIcon,
  getNotificationType,
  normalizeNotificationsResponse,
  sortNotifications,
} from '../utils/notifications'

const TABS = [
  { id: 'unread', label: 'Unread' },
  { id: 'all', label: 'All' },
]

const FILTER_TYPES = [
  'All',
  'Reminder',
  'Deadline',
  'Interview',
  'Offer',
  'Hackathon',
  'System',
]

function NotificationTypeIcon({ type }) {
  if (type === 'reminder') return <BellRing size={18} aria-hidden="true" />
  if (type === 'deadline') return <CalendarClock size={18} aria-hidden="true" />
  if (type === 'interview') return <BriefcaseBusiness size={18} aria-hidden="true" />
  if (type === 'offer') return <Gift size={18} aria-hidden="true" />
  if (type === 'hackathon') return <Laptop size={18} aria-hidden="true" />
  if (type === 'system') return <Settings size={18} aria-hidden="true" />
  return <Bell size={18} aria-hidden="true" />
}

function NotificationCard({ notification, onMarkRead }) {
  const notificationType = getNotificationType(notification)
  const iconType = getNotificationIcon(notification)

  return (
    <article
      className={`notifications-card${
        notification.read ? '' : ' notifications-card-unread'
      }`}
    >
      <div className={`notifications-card-icon icon-${iconType}`}>
        <NotificationTypeIcon type={iconType} />
      </div>
      <div className="notifications-card-body">
        <div className="notifications-card-top">
          <span className="notifications-type">{notificationType}</span>
          <span className="notifications-time">
            {formatRelativeTime(notification.timestamp)}
          </span>
        </div>
        <p>{notification.message}</p>
        <span className={`notifications-status ${notification.read ? 'is-read' : ''}`}>
          {notification.read ? 'Read' : 'Unread'}
        </span>
      </div>
      {!notification.read && (
        <button
          type="button"
          className="notifications-mark-read"
          onClick={() => onMarkRead(notification.id)}
          aria-label="Mark notification as read"
        >
          Mark Read
        </button>
      )}
    </article>
  )
}

function NotificationSkeletonList() {
  return (
    <div className="notifications-list" aria-label="Loading notifications">
      {Array.from({ length: 5 }, (_, index) => (
        <div className="notifications-skeleton-card" key={index} aria-hidden="true">
          <span />
          <div>
            <span />
            <span />
            <span />
          </div>
        </div>
      ))}
    </div>
  )
}

function NotificationsEmptyState({ hasNotifications }) {
  return (
    <div className="notifications-empty">
      <span>
        <Bell size={28} aria-hidden="true" />
      </span>
      <h2>{hasNotifications ? 'No Matching Notifications' : 'No Notifications Yet'}</h2>
      <p>
        {hasNotifications
          ? 'Try changing your search, tab or type filter.'
          : "You'll see reminders and important updates here."}
      </p>
    </div>
  )
}

export default function Notifications() {
  const { profileId } = useAppContext()
  const [notifications, setNotifications] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('unread')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState('All')

  const loadNotifications = useCallback(async () => {
    if (!profileId) {
      setNotifications([])
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const data = await getNotifications(profileId)
      const normalized = normalizeNotificationsResponse(data)
      setNotifications(sortNotifications(normalized.notifications))
    } catch (requestError) {
      setError(getNotificationsErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(loadNotifications)
  }, [loadNotifications])

  const unreadCount = useMemo(
    () => notifications.filter((notification) => !notification.read).length,
    [notifications],
  )

  const filteredNotifications = useMemo(
    () =>
      filterNotifications(notifications, {
        query: searchQuery,
        type: selectedType,
        tab: activeTab,
      }),
    [activeTab, notifications, searchQuery, selectedType],
  )

  async function handleMarkRead(notificationId) {
    const previousNotifications = notifications

    setNotifications((current) =>
      current.map((notification) =>
        notification.id === notificationId
          ? { ...notification, read: true, isNew: false }
          : notification,
      ),
    )

    try {
      await markNotificationRead(notificationId)
    } catch (requestError) {
      setError(getNotificationsErrorMessage(requestError))
      setNotifications(previousNotifications)
    }
  }

  async function handleMarkAllRead() {
    if (unreadCount === 0 || !profileId) return

    const previousNotifications = notifications
    setNotifications((current) =>
      current.map((notification) => ({
        ...notification,
        read: true,
        isNew: false,
      })),
    )

    try {
      await markAllNotificationsRead(profileId)
    } catch (requestError) {
      setError(getNotificationsErrorMessage(requestError))
      setNotifications(previousNotifications)
    }
  }

  return (
    <section className="notifications-page" aria-labelledby="notifications-title">
      <div className="notifications-header">
        <div>
          <p className="notifications-eyebrow">
            <Sparkles size={14} aria-hidden="true" />
            Activity Center
          </p>
          <h1 id="notifications-title">Notifications</h1>
          <p>
            Stay updated with reminders, interviews, deadlines and system
            activity.
          </p>
        </div>
        <button
          type="button"
          className="notifications-mark-all"
          onClick={handleMarkAllRead}
          disabled={unreadCount === 0}
          aria-label="Mark all notifications as read"
        >
          <CheckCircle2 size={17} aria-hidden="true" />
          Mark All Read
        </button>
      </div>

      <div className="notifications-toolbar">
        <div className="notifications-tabs" role="tablist" aria-label="Notification filters">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={activeTab === tab.id ? 'tab-active' : ''}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              {tab.id === 'unread' && <span>{unreadCount}</span>}
            </button>
          ))}
        </div>

        <div className="notifications-controls">
          <div className="notifications-search">
            <Search size={16} aria-hidden="true" />
            <label htmlFor="notifications-search" className="sr-only">
              Search notifications
            </label>
            <input
              id="notifications-search"
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search notifications..."
            />
          </div>
          <label className="notifications-filter">
            <span className="sr-only">Filter notification type</span>
            <select
              value={selectedType}
              onChange={(event) => setSelectedType(event.target.value)}
              aria-label="Filter notification type"
            >
              {FILTER_TYPES.map((type) => (
                <option value={type} key={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {error && (
        <div className="notifications-error">
          <ErrorBanner message={error} onDismiss={() => setError('')} />
          <button
            type="button"
            className="notifications-retry"
            onClick={loadNotifications}
            aria-label="Retry loading notifications"
          >
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <NotificationSkeletonList />
      ) : filteredNotifications.length > 0 ? (
        <div className="notifications-list">
          {filteredNotifications.map((notification) => (
            <NotificationCard
              key={notification.id}
              notification={notification}
              onMarkRead={handleMarkRead}
            />
          ))}
        </div>
      ) : (
        <NotificationsEmptyState hasNotifications={notifications.length > 0} />
      )}
    </section>
  )
}
