import type { MAPSheetSummary } from '../types'

export function MapSummaryCards({ summary }: { summary: MAPSheetSummary }) {
  return (
    <div className="card-grid">
      <article className="panel stack-xs">
        <p className="eyebrow">Items</p>
        <h2>{summary.total_items}</h2>
      </article>
      <article className="panel stack-xs">
        <p className="eyebrow">P checked</p>
        <h2>{summary.checked_p}</h2>
      </article>
      <article className="panel stack-xs">
        <p className="eyebrow">C checked</p>
        <h2>{summary.checked_c}</h2>
      </article>
      <article className="panel stack-xs">
        <p className="eyebrow">High priority</p>
        <h2>{summary.high_priority_flags}</h2>
      </article>
    </div>
  )
}
