export default function GapSummaryCard({ icon: Icon, label, value }) {
  return (
    <section className="gap-summary-card" aria-label={label}>
      <span aria-hidden="true">
        <Icon size={20} />
      </span>
      <div>
        <strong>{value}</strong>
        <p>{label}</p>
      </div>
    </section>
  )
}

