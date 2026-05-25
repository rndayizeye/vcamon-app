import { formatNumber } from '../../../lib/utils'
import type { AnalyticsCentralityRead } from '../types'

export function CentralityTable({
  rows,
}: {
  rows: AnalyticsCentralityRead[]
}) {
  const sortedRows = [...rows].sort((left, right) => {
    return right.betweenness - left.betweenness
  })

  return (
    <div className="panel table-panel stack-sm">
      <div>
        <p className="eyebrow">Centralities</p>
        <h2>Node influence</h2>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Label</th>
            <th>In-degree</th>
            <th>Out-degree</th>
            <th>Betweenness</th>
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => (
            <tr key={row.node_ref}>
              <td>{row.label}</td>
              <td>{formatNumber(row.in_degree)}</td>
              <td>{formatNumber(row.out_degree)}</td>
              <td>{formatNumber(row.betweenness)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
