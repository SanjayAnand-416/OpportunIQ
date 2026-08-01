import { Bell, CalendarClock, CheckCheck, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getNotificationsErrorMessage,
  getUnreadNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../api/notifications'
import ErrorBanner from '../common/ErrorBanner'
import { ROUTES } from '../../constants/routes'
import { useNotificationSocket } from '../../hooks/useNotificationSocket'
import {
  formatRelativeTime,
  getNotificationIcon,
  normalizeNotificationsResponse,
  sortNotifications,
} from '../../utils/notifications'

const MAX_VISIBLE_NOTIFICATIONS = 5

function formatBadgeCount(count) {
  if (count <= 0) return ''
  return count > 99 ? '99+' : String(count)
}

function NotificationSkeleton() {
  return (
    <div className="notification-skeleton" aria-hidden="true">
      <span />
      <div>
        <span />
        <span />
      </div>
    </div>
  )
}

function NotificationEmptyState() {
  return (
    <div className="notification-empty">
      <span className="notification-empty-icon">
        <Bell size={22} aria-hidden="true" />
      </span>
      <h3>You're all caught up</h3>
      <p>No notifications available.</p>
    </div>
  )
}

function NotificationItem({ notification, onMarkRead, itemRef, tabIndex, onKeyDown }) {
  const iconType = getNotificationIcon(notification)

  return (
    <li
      ref={itemRef}
      tabIndex={tabIndex}
      className={`notification-item${notification.read ? '' : ' notification-unread'}${
        notification.isNew ? ' notification-new' : ''
      }`}
      onKeyDown={onKeyDown}
    >
      <span className="notification-item-icon" aria-hidden="true">
        {iconType === 'deadline' ? <CalendarClock size={16} /> : <Bell size={16} />}
      </span>
      <div className="notification-item-body">
        <p>{notification.message}</p>
        <span>{formatRelativeTime(notification.timestamp)}</span>
      </div>
      {!notification.read && (
        <button
          type="button"
          className="notification-read-btn"
          onClick={() => onMarkRead(notification.id)}
          aria-label="Mark notification as read"
        >
          Mark Read
        </button>
      )}
    </li>
  )
}

export default function NotificationBell({ profileId }) {
  const navigate = useNavigate()
  const rootRef = useRef(null)
  const itemRefs = useRef([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifications, setNotifications] = useState([])

  const visibleNotifications = useMemo(
    () => sortNotifications(notifications).slice(0, MAX_VISIBLE_NOTIFICATIONS),
    [notifications],
  )

  const loadNotifications = useCallback(async () => {
    if (!profileId) {
      setNotifications([])
      setUnreadCount(0)
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const data = await getUnreadNotifications(profileId)
      const normalized = normalizeNotificationsResponse(data)
      setNotifications(normalized.notifications)
      setUnreadCount(normalized.count)
    } catch (requestError) {
      setError(getNotificationsErrorMessage(requestError))
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(loadNotifications)
  }, [loadNotifications])

  useNotificationSocket(
    profileId,
    useCallback((notification) => {
      setNotifications((current) =>
        sortNotifications([
          notification,
          ...current.filter((item) => item.id !== notification.id),
        ]),
      )
      setUnreadCount((current) => current + 1)
    }, []),
  )

  useEffect(() => {
    if (!isOpen) return undefined

    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) {
        setIsOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  async function handleMarkRead(notificationId) {
    const target = notifications.find((item) => item.id === notificationId)
    if (!target || target.read) return

    setNotifications((current) =>
      current.map((item) =>
        item.id === notificationId ? { ...item, read: true, isNew: false } : item,
      ),
    )
    setUnreadCount((current) => Math.max(0, current - 1))

    try {
      await markNotificationRead(notificationId)
    } catch (requestError) {
      setError(getNotificationsErrorMessage(requestError))
      setNotifications((current) =>
        current.map((item) =>
          item.id === notificationId ? { ...item, read: false } : item,
        ),
      )
      setUnreadCount((current) => current + 1)
    }
  }

  async function handleMarkAllRead() {
    if (!profileId || unreadCount === 0) return

    const previousNotifications = notifications
    const previousCount = unreadCount

    setNotifications((current) =>
      current.map((item) => ({ ...item, read: true, isNew: false })),
    )
    setUnreadCount(0)

    try {
      await markAllNotificationsRead(profileId)
    } catch (requestError) {
      setError(getNotificationsErrorMessage(requestError))
      setNotifications(previousNotifications)
      setUnreadCount(previousCount)
    }
  }

  function handleViewAll() {
    setIsOpen(false)
    navigate(ROUTES.NOTIFICATIONS)
  }

  function handleItemKeyDown(event, index) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      itemRefs.current[index + 1]?.focus()
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      itemRefs.current[index - 1]?.focus()
    }
  }

  return (
    <div className="notification-bell" ref={rootRef}>
      <button
        type="button"
        className="dash-icon-btn notification-trigger"
        aria-label="Open notifications"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
      >
        <Bell size={18} aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="notification-badge" aria-label={`${unreadCount} unread notifications`}>
            {formatBadgeCount(unreadCount)}
          </span>
        )}
      </button>

      {isOpen && (
        <section className="notification-dropdown" aria-label="Notifications">
          <div className="notification-dropdown-header">
            <div>
              <h2>Notifications</h2>
              <p>{unreadCount} unread</p>
            </div>
            <button
              type="button"
              className="notification-mark-all"
              onClick={handleMarkAllRead}
              disabled={unreadCount === 0}
              aria-label="Mark all notifications as read"
            >
              <CheckCheck size={15} aria-hidden="true" />
              Mark All Read
            </button>
          </div>

          {error && (
            <div className="notification-error">
              <ErrorBanner message={error} onDismiss={() => setError('')} />
              <button
                type="button"
                className="notification-retry"
                onClick={loadNotifications}
                aria-label="Retry loading notifications"
              >
                Retry
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="notification-loading" aria-label="Loading notifications">
              <Loader2 className="spinner" size={18} aria-hidden="true" />
              <NotificationSkeleton />
              <NotificationSkeleton />
              <NotificationSkeleton />
            </div>
          ) : visibleNotifications.length === 0 && !error ? (
            <NotificationEmptyState />
          ) : (
            <ul className="notification-list" aria-label="Recent notifications">
              {visibleNotifications.map((notification, index) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkRead={handleMarkRead}
                  itemRef={(node) => {
                    itemRefs.current[index] = node
                  }}
                  tabIndex={0}
                  onKeyDown={(event) => handleItemKeyDown(event, index)}
                />
              ))}
            </ul>
          )}

          <button
            type="button"
            className="notification-view-all"
            onClick={handleViewAll}
            aria-label="View all notifications"
          >
            View All Notifications
          </button>
        </section>
      )}
    </div>
  )
}
