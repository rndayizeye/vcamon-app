export function EmptyState({
  title,
  description,
}: {
  title: string
  description?: string
}) {
  return (
    <div className="panel panel-centered stack-sm">
      <h2>{title}</h2>
      {description ? <p className="muted">{description}</p> : null}
    </div>
  )
}
