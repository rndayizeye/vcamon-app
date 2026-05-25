export function LoadingState({ message = 'Loading…' }: { message?: string }) {
  return (
    <div className="panel panel-centered">
      <p className="muted">{message}</p>
    </div>
  )
}
