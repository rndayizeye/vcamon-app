export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
}: {
  title?: string
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="panel stack-sm">
      <h2>{title}</h2>
      <p className="error-text">{message}</p>
      {onRetry ? (
        <button className="button" type="button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  )
}
