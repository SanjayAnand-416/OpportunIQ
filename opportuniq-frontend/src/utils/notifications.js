export function formatRelativeTime(timestamp) {
  const date = new Date(timestamp)
  const time = date.getTime()

  if (!Number.isFinite(time)) {
    return 'Just now'
  }

  const diffMs = Date.now() - time
  const diffMinutes = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) {
    return `${diffMinutes} ${diffMinutes === 1 ? 'minute' : 'minutes'} ago`
  }
  if (diffHours < 24) {
    return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`
  }
  if (diffDays === 1) return 'Yesterday'

  return `${diffDays} days ago`
}

export function sortNotifications(notifications) {
  return [...notifications].sort((a, b) => {
    const aTime = new Date(a.timestamp).getTime()
    const bTime = new Date(b.timestamp).getTime()
    return (Number.isFinite(bTime) ? bTime : 0) - (Number.isFinite(aTime) ? aTime : 0)
  })
}

export function normalizeNotification(notification) {
  const message = notification.message || notification.body || notification.subject || ''
  const type = notification.type || notification.category || getNotificationType({ message })

  return {
    id: notification.id || notification.notification_id,
    message,
    type: normalizeNotificationType(type),
    timestamp:
      notification.timestamp ||
      notification.created_at ||
      notification.createdAt ||
      new Date().toISOString(),
    read: Boolean(notification.read ?? notification.is_read),
    isNew: Boolean(notification.isNew),
  }
}

export function normalizeNotificationsResponse(data) {
  const notifications = Array.isArray(data)
    ? data
    : data?.notifications || data?.recent || []

  return {
    count: data?.unread_count ?? data?.count ?? notifications.length,
    notifications: sortNotifications(notifications.map(normalizeNotification)),
  }
}

export function notificationFromSocketPayload(payload) {
  if (payload?.type === 'notification' && payload.notification) {
    return normalizeNotification({ ...payload.notification, isNew: true })
  }

  if (payload?.agent === 'notifier' || payload?.status === 'notification') {
    return normalizeNotification({
      id: payload.metadata?.notification_id || `${payload.timestamp}-${payload.message}`,
      message: payload.message,
      timestamp: payload.timestamp,
      read: false,
      isNew: true,
    })
  }

  return null
}

export function getNotificationIcon(notification) {
  const type = getNotificationType(notification)

  if (type === 'Reminder') return 'reminder'
  if (type === 'Deadline') return 'deadline'
  if (type === 'Interview') return 'interview'
  if (type === 'Offer') return 'offer'
  if (type === 'Hackathon') return 'hackathon'
  if (type === 'System') return 'system'

  return 'notification'
}

export function normalizeNotificationType(type) {
  const normalized = String(type || '').trim().toLowerCase()

  if (normalized === 'reminder') return 'Reminder'
  if (normalized === 'deadline') return 'Deadline'
  if (normalized === 'interview') return 'Interview'
  if (normalized === 'offer') return 'Offer'
  if (normalized === 'hackathon') return 'Hackathon'
  if (normalized === 'system') return 'System'

  return ''
}

export function getNotificationType(notification) {
  if (notification.type) {
    const normalized = normalizeNotificationType(notification.type)
    if (normalized) return normalized
  }

  const message = String(notification.message || '').toLowerCase()

  if (message.includes('interview')) return 'Interview'
  if (message.includes('offer')) return 'Offer'
  if (message.includes('hackathon')) return 'Hackathon'
  if (message.includes('deadline')) return 'Deadline'
  if (message.includes('reminder')) return 'Reminder'
  if (message.includes('system')) return 'System'

  return 'System'
}

export function filterNotifications(notifications, { query, type, tab }) {
  const normalizedQuery = query.trim().toLowerCase()

  return notifications.filter((notification) => {
    const notificationType = getNotificationType(notification)
    const matchesTab = tab === 'all' || !notification.read
    const matchesType = type === 'All' || notificationType === type
    const matchesQuery =
      !normalizedQuery ||
      notification.message.toLowerCase().includes(normalizedQuery) ||
      notificationType.toLowerCase().includes(normalizedQuery)

    return matchesTab && matchesType && matchesQuery
  })
}
