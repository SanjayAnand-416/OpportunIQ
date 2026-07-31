export default function Badge({ children, variant = 'default' }) {
  const variants = {
    default: '',
    blue: 'badge-blue',
    indigo: 'badge-indigo',
    green: 'badge-green',
  }

  return (
    <span className={`badge ${variants[variant]}`}>
      {children}
    </span>
  )
}
