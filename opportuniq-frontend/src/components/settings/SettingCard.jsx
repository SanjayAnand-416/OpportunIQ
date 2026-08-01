export default function SettingCard({ title, description, icon: Icon, children }) {
  return (
    <section className="settings-card" aria-labelledby={`${title}-settings-title`}>
      <div className="settings-card-header">
        {Icon && (
          <span className="settings-card-icon" aria-hidden="true">
            <Icon size={18} />
          </span>
        )}
        <div>
          <h2 id={`${title}-settings-title`}>{title}</h2>
          {description && <p>{description}</p>}
        </div>
      </div>
      <div className="settings-card-body">{children}</div>
    </section>
  )
}

