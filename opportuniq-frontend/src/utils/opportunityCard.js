const PLATFORM_INFO = {
  linkedin: { label: 'LinkedIn', tone: 'blue' },
  naukri: { label: 'Naukri', tone: 'teal' },
  unstop: { label: 'Unstop', tone: 'purple' },
  devfolio: { label: 'Devfolio', tone: 'indigo' },
  hackerearth: { label: 'HackerEarth', tone: 'green' },
  indeed: { label: 'Indeed', tone: 'orange' },
  'google jobs': { label: 'Google Jobs', tone: 'gray' },
}

const AVATAR_TONES = ['blue', 'indigo', 'teal', 'purple', 'green', 'orange']

const MS_PER_DAY = 24 * 60 * 60 * 1000

export function getPlatformInfo(platform) {
  if (!platform) {
    return { label: 'Unknown', tone: 'gray' }
  }

  const known = PLATFORM_INFO[platform.trim().toLowerCase()]
  return known ?? { label: platform, tone: 'gray' }
}

export function getPlatformColor(platform) {
  return getPlatformInfo(platform).tone
}

export function getMatchColor(matchPercentage) {
  if (typeof matchPercentage !== 'number' || Number.isNaN(matchPercentage)) {
    return 'gray'
  }
  if (matchPercentage >= 70) return 'green'
  if (matchPercentage >= 40) return 'amber'
  return 'red'
}

export function getDeadlineInfo(deadline) {
  if (!deadline) {
    return { label: 'No deadline', tone: 'gray' }
  }

  const deadlineDate = new Date(deadline)
  if (Number.isNaN(deadlineDate.getTime())) {
    return { label: 'No deadline', tone: 'gray' }
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  deadlineDate.setHours(0, 0, 0, 0)

  const daysLeft = Math.round((deadlineDate.getTime() - today.getTime()) / MS_PER_DAY)

  if (daysLeft < 0) {
    return { label: 'Deadline passed', tone: 'red' }
  }
  if (daysLeft === 0) {
    return { label: 'Due today', tone: 'red' }
  }
  if (daysLeft <= 3) {
    return { label: `${daysLeft} day${daysLeft === 1 ? '' : 's'} left`, tone: 'red' }
  }
  if (daysLeft <= 7) {
    return { label: `${daysLeft} days left`, tone: 'amber' }
  }
  return { label: `${daysLeft} days left`, tone: 'green' }
}

export function getDeadlineColor(deadline) {
  return getDeadlineInfo(deadline).tone
}

export function getCompanyInitial(name) {
  return name?.trim()?.charAt(0)?.toUpperCase() || '?'
}

export function getAvatarTone(name) {
  if (!name) return 'gray'
  const sum = [...name].reduce((total, char) => total + char.charCodeAt(0), 0)
  return AVATAR_TONES[sum % AVATAR_TONES.length]
}
