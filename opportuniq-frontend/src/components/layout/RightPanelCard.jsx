export default function RightPanelCard({ title, icon: Icon, children }) {
  return (
    <section className="right-panel-card" aria-label={title}>
      <div className="right-panel-card-header">
        {Icon && (
          <span className="right-panel-card-icon" aria-hidden="true">
            <Icon size={16} />
          </span>
        )}
        <h2 className="right-panel-card-title">{title}</h2>
      </div>
      <div className="right-panel-card-body">{children}</div>
    </section>
  )
}
