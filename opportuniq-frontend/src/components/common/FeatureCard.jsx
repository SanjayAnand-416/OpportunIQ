export default function FeatureCard({ icon: Icon, title, description }) {
  return (
    <article className="feature-card">
      <div className="feature-card__icon">
        <Icon size={24} aria-hidden="true" />
      </div>
      <h3 className="feature-card__title">{title}</h3>
      <p className="feature-card__description">{description}</p>
    </article>
  )
}
