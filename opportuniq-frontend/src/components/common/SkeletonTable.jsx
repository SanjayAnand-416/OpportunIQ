export default function SkeletonTable({ rows = 5, columns = 4 }) {
  return (
    <div className="ui-skeleton-table" aria-label="Loading table">
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div className="ui-skeleton-table-row" key={rowIndex} aria-hidden="true">
          {Array.from({ length: columns }, (_, columnIndex) => (
            <span className="ui-skeleton" key={columnIndex} />
          ))}
        </div>
      ))}
    </div>
  )
}

