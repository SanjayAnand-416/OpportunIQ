export default function StatusChip({ children, variant = 'neutral' }) {
  return <span className={`ui-status-chip ui-status-${variant}`}>{children}</span>
}

