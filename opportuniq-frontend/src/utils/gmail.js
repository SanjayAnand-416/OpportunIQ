export function formatLastScanned(lastScanned) {
  if (!lastScanned) return 'Never scanned'

  const date = new Date(lastScanned)
  if (Number.isNaN(date.getTime())) return 'Never scanned'

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}
