export default function FieldStatusBadge({ status }) {
  const isConfirmed = status === 'confirmed'

  return (
    <span
      className={`field-status-badge ${
        isConfirmed ? 'field-status-confirmed' : 'field-status-needed'
      }`}
    >
      {isConfirmed ? 'Confirmed' : 'Needs Input'}
    </span>
  )
}
