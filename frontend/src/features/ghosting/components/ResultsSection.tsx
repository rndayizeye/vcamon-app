import { useState } from 'react'
import type { NetworkEdge, PairResult } from '../types-local'
import { PairResultDetail } from './PairResultDetail'
import { VerdictBanner } from './VerdictDisplay'

export function ResultsSection({
  edges,
  people,
  resultMap,
}: {
  edges: NetworkEdge[]
  people: { _pid: string; name: string }[]
  resultMap: Map<string, PairResult>
}) {
  const [openEdge, setOpenEdge] = useState<string | null>(null)

  function displayName(pid: string): string {
    const idx = people.findIndex(p => p._pid === pid)
    const p = people[idx]
    return p ? (p.name.trim() || `Patient ${idx + 1}`) : '(removed)'
  }

  return (
    <section className="stack-lg" style={{ marginTop: '1.5rem' }}>
      <div style={{ borderTop: '2px solid #E8E5DF', paddingTop: '1.5rem' }}>
        <p className="eyebrow">Analysis results</p>
        <p style={{ fontSize: '0.82rem', color: '#777', marginTop: '2px' }}>
          {resultMap.size} pair{resultMap.size !== 1 ? 's' : ''} analyzed — click any row to expand
          details.
        </p>
      </div>
      {edges.map(edge => {
        const pair = resultMap.get(edge.id)
        if (!pair) return null
        const isOpen = openEdge === edge.id
        return (
          <div key={edge.id} className="panel" style={{ padding: '0.75rem 1rem' }}>
            <button
              type="button"
              onClick={() => setOpenEdge(isOpen ? null : edge.id)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'none',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                width: '100%',
                textAlign: 'left',
                gap: '1rem',
              }}
            >
              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                {displayName(edge.aId)} ↔ {displayName(edge.bId)}
                {edge.label && (
                  <span
                    style={{ fontWeight: 400, fontSize: '0.8rem', color: '#777', marginLeft: '0.6rem' }}
                  >
                    {edge.label}
                  </span>
                )}
              </span>
              <div
                style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}
              >
                {pair.result && <VerdictBanner verdict={pair.result.verdict} compact />}
                {pair.error && <span className="badge badge-fail">Error</span>}
                <span style={{ fontSize: '0.8rem', color: '#888' }}>{isOpen ? '▲' : '▼'}</span>
              </div>
            </button>
            {isOpen && (
              <div style={{ marginTop: '1rem', borderTop: '1px solid #eee', paddingTop: '1rem' }}>
                <PairResultDetail pair={pair} />
              </div>
            )}
          </div>
        )
      })}
    </section>
  )
}
