import type { AnalyticsSummaryRead } from '../types'

export function AnalyticsSummaryCards({
  summary,
}: {
  summary: AnalyticsSummaryRead
}) {
  return (
    <div className="card-grid">
      <article className="panel stack-xs">
        <p className="eyebrow">People in network <span className="muted">(nodes)</span></p>
        <h2>{summary.node_count}</h2>
        <p className="muted text-sm">Total number of individuals — the index patient (OP) and all named partners — being tracked in this network.</p>
      </article>
      <article className="panel stack-xs">
        <p className="eyebrow">Reported contacts <span className="muted">(edges)</span></p>
        <h2>{summary.edge_count}</h2>
        <p className="muted text-sm">Total number of directional links between people — each link represents a reported sexual contact from one person to another.</p>
      </article>
      <article className="panel stack-xs">
        <p className="eyebrow">Data shown through</p>
        <h2>{summary.as_of_date || 'All dates'}</h2>
        <p className="muted text-sm">Only contacts and events on or before this date are included. Leave blank to include all recorded data.</p>
      </article>
    </div>
  )
}
