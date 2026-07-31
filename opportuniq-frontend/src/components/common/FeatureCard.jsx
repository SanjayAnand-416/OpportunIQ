export default function FeatureCard({ icon: Icon, title, description, accent }) {
  return (
    <article className="feature-card">
      <div className={`feature-icon ${accent}`}>
        <Icon size={24} aria-hidden="true" />
      </div>
      <h3 className="feature-title">{title}</h3>
      <p className="feature-description">{description}</p>
    </article>
  )
}
