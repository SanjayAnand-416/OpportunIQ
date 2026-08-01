import { useEffect } from 'react'
import Toast from './Toast'

const TOAST_DURATION_MS = 4000

export default function ToastContainer({ toasts, onDismiss }) {
  useEffect(() => {
    if (!toasts.length) return undefined
    const timeoutIds = toasts.map((toast) =>
      window.setTimeout(() => onDismiss(toast.id), toast.duration ?? TOAST_DURATION_MS),
    )
    return () => timeoutIds.forEach(window.clearTimeout)
  }, [onDismiss, toasts])

  if (!toasts.length) return null

  return (
    <div className="toast-container" aria-live="polite" aria-relevant="additions removals">
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onDismiss={onDismiss} />
      ))}
    </div>
  )
}
