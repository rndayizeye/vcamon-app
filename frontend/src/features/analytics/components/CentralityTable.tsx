import { formatNumber } from '../../../lib/utils'
import type { AnalyticsCentralityRead } from '../types'

const CENTRALITY_DEFINITIONS = [
  {
    term: 'Exposures received (in-degree)',
    definition:
      'How many people in the network reported sexual contact with this person. A high count suggests this person may have been exposed by multiple partners.',
  },
  {
    term: 'Exposures reported (out-degree)',
    definition:
      'How many people this person reported sexual contact with. A high count suggests this person may have exposed multiple partners.',
  },
  {
    term: 'Network bridge score (betweenness centrality)',
    definition:
      'How often this person appears as the connection between otherwise separate groups. A high score means this person links different clusters — removing them would disconnect parts of the network.',
  },
]

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
        <p className="eyebrow">Network influence <span className="muted">(centralities)</span></p>
        <h2>Who matters most in the transmission chain</h2>
        <p className="muted text-sm">Sorted by bridge score — people at the top connect the most otherwise-separate groups.</p>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Person</th>
            <th title="Number of people who reported contact with this person">Exposures received <span className="muted">(in-degree)</span></th>
            <th title="Number of people this person reported contact with">Exposures reported <span className="muted">(out-degree)</span></th>
            <th title="How often this person bridges otherwise-separate groups">Bridge score <span className="muted">(betweenness)</span></th>
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

      <details className="stack-xs">
        <summary className="muted text-sm" style={{ cursor: 'pointer' }}>How are these calculated?</summary>
        <dl className="stack-xs" style={{ marginTop: '0.5rem' }}>
          {CENTRALITY_DEFINITIONS.map(({ term, definition }) => (
            <div key={term}>
              <dt className="text-sm" style={{ fontWeight: 600 }}>{term}</dt>
              <dd className="muted text-sm" style={{ marginLeft: '1rem' }}>{definition}</dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  )
}
