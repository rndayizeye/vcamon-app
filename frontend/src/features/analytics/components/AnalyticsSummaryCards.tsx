import type { AnalyticsSummaryRead } from '../types'

export function AnalyticsSummaryCards({
  summary,
}: {
  summary: AnalyticsSummaryRead
}) {
  return (
    <div className="card-grid">
      <article className="panel stack-xs">
        <p className="eyebrow">Nodes</p>
        <h2>{summary.node_count}</h2>
      </article>
      <article className="panel stack-xs">
        <p className="eyebrow">Edges</p>
        <h2>{summary.edge_count}</h2>
      </article>
      <article className="panel stack-xs">
        <p className="eyebrow">As of</p>
        <h2>{summary.as_of_date || 'All data'}</h2>
      </article>
    </div>
  )
}
