export default function SkeletonCard({ lines = 3 }) {
  return (
    <div className="ui-skeleton-card" aria-hidden="true">
      <span className="ui-skeleton ui-skeleton-icon" />
      {Array.from({ length: lines }, (_, index) => (
        <span className="ui-skeleton ui-skeleton-line" key={index} />
      ))}
    </div>
  )
}

