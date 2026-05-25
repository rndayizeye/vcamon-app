import type { DashboardSummary } from '../../types'

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string
  value: number
  accent?: 'green' | 'amber'
}) {
  return (
    <div
      className="panel stack-xs"
      style={{
        background: accent === 'green' ? '#edf9f0' : accent === 'amber' ? '#fffbeb' : undefined,
        borderColor:
          accent === 'green' ? '#a7f3d0' : accent === 'amber' ? '#fde68a' : undefined,
      }}
    >
      <p className="eyebrow">{label}</p>
      <p
        style={{
          fontSize: '2rem',
          fontWeight: 700,
          color:
            accent === 'green'
              ? '#0a7a38'
              : accent === 'amber' && value > 0
              ? '#854F0B'
              : undefined,
        }}
      >
        {value}
      </p>
    </div>
  )
}

export function DashboardMetrics({ summary }: { summary: DashboardSummary }) {
  return (
    <div className="card-grid">
      <MetricCard label="Total Cases" value={summary.total_cases} />
      <MetricCard label="Total Partners" value={summary.total_partners} />
      <MetricCard label="Treated" value={summary.treated_count} accent="green" />
      <MetricCard
        label="Pending Treatment"
        value={summary.untreated_count}
        accent={summary.untreated_count > 0 ? 'amber' : undefined}
      />
    </div>
  )
}
