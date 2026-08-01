import { useEffect, useState } from 'react'

const TOAST_DURATION_MS = 4000

export function useToast() {
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!message) return undefined
    const timeoutId = window.setTimeout(() => setMessage(''), TOAST_DURATION_MS)
    return () => window.clearTimeout(timeoutId)
  }, [message])

  return [message, setMessage]
}
