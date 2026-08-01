export default function SkeletonForm({ fields = 6 }) {
  return (
    <div className="ui-skeleton-form" aria-label="Loading form">
      {Array.from({ length: fields }, (_, index) => (
        <div className="ui-skeleton-form-field" key={index} aria-hidden="true">
          <span className="ui-skeleton ui-skeleton-label" />
          <span className="ui-skeleton ui-skeleton-input" />
        </div>
      ))}
    </div>
  )
}

