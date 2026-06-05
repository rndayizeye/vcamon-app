import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
import { useTransmissionChain } from './hooks'
import type { TransmissionEdge, TransmissionNode } from './types'

// ---------------------------------------------------------------------------
// Color constants
// ---------------------------------------------------------------------------
const COLOR_CASE = '#D85A30'
const COLOR_PARTNER = '#EF9F27'
const CONFIDENCE_COLORS: Record<string, string> = {
  Robust: '#1D9E75',
  Likely: '#4CAF50',
  Possible: '#F5A623',
  Weak: '#f59e0b',
  Unlikely: '#ef4444',
  Ambiguous: '#9C27B0',
}
const CONFIDENCE_ORDER = ['Robust', 'Likely', 'Possible', 'Weak', 'Unlikely', 'Ambiguous', 'Unrelated']

const SVG_W = 900
const SVG_H = 600
const NODE_R = 24
const PADDING = NODE_R + 10

// ---------------------------------------------------------------------------
// Spring-force layout (Fruchterman-Reingold simplified)
// ---------------------------------------------------------------------------
type Vec2 = { x: number; y: number }

function computeLayout(
  nodes: TransmissionNode[],
  edges: TransmissionEdge[],
): Map<string, Vec2> {
  const pos = new Map<string, Vec2>()
  const N = nodes.length
  if (N === 0) return pos

  // Circular seed positions
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / N - Math.PI / 2
    pos.set(n.id, {
      x: SVG_W / 2 + (SVG_W * 0.38) * Math.cos(angle),
      y: SVG_H / 2 + (SVG_H * 0.38) * Math.sin(angle),
    })
  })

  const k = Math.sqrt((SVG_W * SVG_H) / Math.max(N, 1))
  const iterations = 120

  for (let iter = 0; iter < iterations; iter++) {
    const forces = new Map<string, Vec2>()
    nodes.forEach(n => forces.set(n.id, { x: 0, y: 0 }))

    // Repulsion between every pair
    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const pi = pos.get(nodes[i].id)!
        const pj = pos.get(nodes[j].id)!
        const dx = pi.x - pj.x
        const dy = pi.y - pj.y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const mag = (k * k) / dist
        const fx = (dx / dist) * mag
        const fy = (dy / dist) * mag
        forces.get(nodes[i].id)!.x += fx
        forces.get(nodes[i].id)!.y += fy
        forces.get(nodes[j].id)!.x -= fx
        forces.get(nodes[j].id)!.y -= fy
      }
    }

    // Attraction along edges
    edges.forEach(e => {
      const pi = pos.get(e.from_node_id)
      const pj = pos.get(e.to_node_id)
      if (!pi || !pj) return
      const dx = pj.x - pi.x
      const dy = pj.y - pi.y
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      const mag = (dist * dist) / k
      const fx = (dx / dist) * mag
      const fy = (dy / dist) * mag
      forces.get(e.from_node_id)!.x += fx
      forces.get(e.from_node_id)!.y += fy
      forces.get(e.to_node_id)!.x -= fx
      forces.get(e.to_node_id)!.y -= fy
    })

    // Apply with cooling temperature
    const temp = SVG_W * 0.08 * (1 - iter / iterations)
    nodes.forEach(n => {
      const f = forces.get(n.id)!
      const fMag = Math.sqrt(f.x * f.x + f.y * f.y)
      if (fMag < 0.001) return
      const move = Math.min(fMag, temp)
      const p = pos.get(n.id)!
      p.x = Math.max(PADDING, Math.min(SVG_W - PADDING, p.x + (f.x / fMag) * move))
      p.y = Math.max(PADDING, Math.min(SVG_H - PADDING, p.y + (f.y / fMag) * move))
    })
  }

  return pos
}

// ---------------------------------------------------------------------------
// Arrow marker IDs per confidence level
// ---------------------------------------------------------------------------
function markerId(confidence: string) {
  return `arrow-${confidence.toLowerCase()}`
}

// ---------------------------------------------------------------------------
// Edge path with offset to stop at node boundary
// ---------------------------------------------------------------------------
function edgePath(
  fromPos: Vec2,
  toPos: Vec2,
): { x1: number; y1: number; x2: number; y2: number } {
  const dx = toPos.x - fromPos.x
  const dy = toPos.y - fromPos.y
  const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
  const nx = dx / dist
  const ny = dy / dist
  const arrowBackoff = NODE_R + 8
  return {
    x1: fromPos.x + nx * NODE_R,
    y1: fromPos.y + ny * NODE_R,
    x2: toPos.x - nx * arrowBackoff,
    y2: toPos.y - ny * arrowBackoff,
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function TransmissionChainPage() {
  const [run, setRun] = useState(false)
  const [hoveredEdge, setHoveredEdge] = useState<TransmissionEdge | null>(null)
  const [hoveredNode, setHoveredNode] = useState<TransmissionNode | null>(null)
  const [showSkipped, setShowSkipped] = useState(false)

  const query = useTransmissionChain(run)

  const positions = useMemo(() => {
    if (!query.data) return new Map<string, Vec2>()
    return computeLayout(query.data.nodes, query.data.edges)
  }, [query.data])

  const confidencesPresent = useMemo(() => {
    if (!query.data) return []
    const seen = new Set(query.data.edges.map(e =>
      e.is_ambiguous ? 'Ambiguous' : e.dominant_confidence
    ))
    return CONFIDENCE_ORDER.filter(c => seen.has(c))
  }, [query.data])

  return (
    <div className="stack-lg" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '1rem', flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>
          Transmission Chain
        </h1>
        <span style={{ color: '#888', fontSize: '0.875rem' }}>
          VCA analysis across all case-partner pairs
        </span>
      </div>

      {!run && (
        <div className="stack-sm" style={{ maxWidth: 480 }}>
          <p style={{ margin: 0, color: '#555', fontSize: '0.9rem', lineHeight: 1.5 }}>
            Runs the VCA ghosting pipeline on every recorded case-partner pair
            and renders a directed graph of plausible transmission links.
            Unrelated pairs and pairs with insufficient clinical data are excluded.
          </p>
          <button
            className="btn btn-primary"
            onClick={() => setRun(true)}
            style={{ width: 'fit-content' }}
          >
            Run Analysis
          </button>
        </div>
      )}

      {run && query.isLoading && (
        <LoadingState message="Analyzing all case-partner pairs…" />
      )}

      {run && query.isError && (
        <ErrorState
          title="Analysis failed"
          message={query.error.message}
          onRetry={() => void query.refetch()}
        />
      )}

      {query.data && (
        <div className="stack-md">
          {/* Summary bar */}
          <div
            style={{
              display: 'flex',
              gap: '2rem',
              flexWrap: 'wrap',
              fontSize: '0.875rem',
              color: '#444',
              padding: '0.75rem 1rem',
              background: '#f8f8f8',
              borderRadius: 6,
              border: '1px solid #e8e8e8',
            }}
          >
            <span><strong>{query.data.nodes.length}</strong> subjects</span>
            <span><strong>{query.data.edges.length}</strong> plausible link{query.data.edges.length !== 1 ? 's' : ''}</span>
            <span><strong>{query.data.total_pairs_analyzed}</strong> pairs analyzed</span>
            {query.data.total_pairs_skipped > 0 && (
              <button
                style={{
                  background: 'none',
                  border: 'none',
                  padding: 0,
                  cursor: 'pointer',
                  color: '#888',
                  fontSize: '0.875rem',
                  textDecoration: 'underline',
                }}
                onClick={() => setShowSkipped(s => !s)}
              >
                {query.data.total_pairs_skipped} skipped
              </button>
            )}
            <button
              className="btn btn-secondary"
              style={{ marginLeft: 'auto', fontSize: '0.8rem', padding: '0.25rem 0.75rem' }}
              onClick={() => {
                setRun(false)
                setTimeout(() => setRun(true), 0)
              }}
            >
              Re-run
            </button>
          </div>

          {showSkipped && query.data.skipped.length > 0 && (
            <details open style={{ fontSize: '0.8rem', color: '#666' }}>
              <summary style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>
                Skipped pairs
              </summary>
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #ddd', textAlign: 'left' }}>
                    <th style={{ padding: '4px 8px' }}>Case</th>
                    <th style={{ padding: '4px 8px' }}>Partner</th>
                    <th style={{ padding: '4px 8px' }}>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.skipped.map((s, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '4px 8px' }}>
                        <Link to={`/cases/${s.case_id}`} style={{ color: COLOR_CASE }}>
                          Case {s.case_id}
                        </Link>
                      </td>
                      <td style={{ padding: '4px 8px' }}>{s.partner_label}</td>
                      <td style={{ padding: '4px 8px' }}>{s.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}

          {query.data.edges.length === 0 && (
            <p style={{ color: '#888', fontStyle: 'italic', fontSize: '0.9rem' }}>
              No plausible transmission links found. All analyzed pairs are unrelated
              or insufficient data was available.
            </p>
          )}

          {query.data.edges.length > 0 && (
            <div style={{ position: 'relative' }}>
              {/* Legend */}
              <div
                style={{
                  display: 'flex',
                  gap: '1rem',
                  flexWrap: 'wrap',
                  fontSize: '0.8rem',
                  marginBottom: '0.5rem',
                  alignItems: 'center',
                }}
              >
                <span style={{ color: '#888' }}>Confidence:</span>
                {confidencesPresent.map(c => (
                  <span key={c} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <svg width={20} height={4}>
                      <line
                        x1={0} y1={2} x2={20} y2={2}
                        stroke={CONFIDENCE_COLORS[c] ?? '#aaa'}
                        strokeWidth={3}
                        strokeDasharray={c === 'Possible' ? '4,2' : undefined}
                      />
                    </svg>
                    {c}
                  </span>
                ))}
                <span style={{ marginLeft: '1.5rem', color: '#888' }}>Nodes:</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <svg width={14} height={14}>
                    <circle cx={7} cy={7} r={6} fill={COLOR_CASE} />
                  </svg>
                  Case
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <svg width={14} height={14}>
                    <circle cx={7} cy={7} r={6} fill={COLOR_PARTNER} />
                  </svg>
                  Partner
                </span>
              </div>

              <svg
                width={SVG_W}
                height={SVG_H}
                style={{
                  display: 'block',
                  border: '1px solid #e8e8e8',
                  borderRadius: 8,
                  background: '#fafafa',
                  maxWidth: '100%',
                }}
                viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              >
                <defs>
                  {Object.entries(CONFIDENCE_COLORS).map(([conf, color]) => (
                    <marker
                      key={conf}
                      id={markerId(conf)}
                      markerWidth={8}
                      markerHeight={8}
                      refX={6}
                      refY={3}
                      orient="auto"
                    >
                      <path d="M0,0 L0,6 L8,3 z" fill={color} />
                    </marker>
                  ))}
                </defs>

                {/* Edges */}
                {query.data.edges.map((edge, i) => {
                  const fromPos = positions.get(edge.from_node_id)
                  const toPos = positions.get(edge.to_node_id)
                  if (!fromPos || !toPos) return null
                  const { x1, y1, x2, y2 } = edgePath(fromPos, toPos)
                  const conf = edge.is_ambiguous ? 'Ambiguous' : edge.dominant_confidence
                  const color = CONFIDENCE_COLORS[conf] ?? '#aaa'
                  const isHovered = hoveredEdge === edge
                  return (
                    <line
                      key={i}
                      x1={x1} y1={y1} x2={x2} y2={y2}
                      stroke={color}
                      strokeWidth={isHovered ? 3.5 : 2}
                      strokeDasharray={conf === 'Possible' ? '6,3' : undefined}
                      markerEnd={`url(#${markerId(conf)})`}
                      opacity={isHovered ? 1 : 0.8}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setHoveredEdge(edge)}
                      onMouseLeave={() => setHoveredEdge(null)}
                    />
                  )
                })}

                {/* Nodes */}
                {query.data.nodes.map(node => {
                  const p = positions.get(node.id)
                  if (!p) return null
                  const isHovered = hoveredNode === node
                  const fill = node.type === 'case' ? COLOR_CASE : COLOR_PARTNER
                  const words = node.label.split(' ')
                  const line1 = words.slice(0, Math.ceil(words.length / 2)).join(' ')
                  const line2 = words.slice(Math.ceil(words.length / 2)).join(' ')
                  return (
                    <g
                      key={node.id}
                      style={{ cursor: node.case_id ? 'pointer' : 'default' }}
                      onMouseEnter={() => setHoveredNode(node)}
                      onMouseLeave={() => setHoveredNode(null)}
                    >
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={NODE_R}
                        fill={fill}
                        stroke={isHovered ? '#222' : '#fff'}
                        strokeWidth={isHovered ? 2.5 : 1.5}
                        opacity={0.92}
                      />
                      {line2 ? (
                        <>
                          <text
                            x={p.x}
                            y={p.y - 5}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={9}
                            fontWeight={600}
                            fill="#fff"
                            style={{ pointerEvents: 'none', userSelect: 'none' }}
                          >
                            {line1}
                          </text>
                          <text
                            x={p.x}
                            y={p.y + 7}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={9}
                            fontWeight={600}
                            fill="#fff"
                            style={{ pointerEvents: 'none', userSelect: 'none' }}
                          >
                            {line2}
                          </text>
                        </>
                      ) : (
                        <text
                          x={p.x}
                          y={p.y}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontSize={9}
                          fontWeight={600}
                          fill="#fff"
                          style={{ pointerEvents: 'none', userSelect: 'none' }}
                        >
                          {line1}
                        </text>
                      )}
                    </g>
                  )
                })}
              </svg>

              {/* Hover tooltip */}
              {(hoveredEdge || hoveredNode) && (
                <div
                  style={{
                    marginTop: '0.75rem',
                    padding: '0.75rem 1rem',
                    background: '#fff',
                    border: '1px solid #ddd',
                    borderRadius: 6,
                    fontSize: '0.85rem',
                    maxWidth: 560,
                    lineHeight: 1.5,
                  }}
                >
                  {hoveredEdge && (
                    <>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>
                        {hoveredEdge.verdict}
                      </div>
                      <div style={{ color: '#666' }}>
                        Source confidence: <strong>{hoveredEdge.source_confidence}</strong>
                        {' · '}
                        Spread confidence: <strong>{hoveredEdge.spread_confidence}</strong>
                        {hoveredEdge.is_ambiguous && (
                          <span style={{ marginLeft: 6, color: CONFIDENCE_COLORS.Ambiguous }}>
                            (ambiguous direction)
                          </span>
                        )}
                      </div>
                    </>
                  )}
                  {hoveredNode && !hoveredEdge && (
                    <>
                      <div style={{ fontWeight: 600 }}>{hoveredNode.label}</div>
                      <div style={{ color: '#666' }}>
                        {hoveredNode.type === 'case'
                          ? `Case ID: ${hoveredNode.case_id}`
                          : `Partner in case ${hoveredNode.case_id}`}
                        {hoveredNode.linked_case_id && (
                          <span> · linked to case {hoveredNode.linked_case_id}</span>
                        )}
                      </div>
                      {hoveredNode.case_id && (
                        <Link
                          to={`/cases/${hoveredNode.case_id}/ghosting`}
                          style={{ color: COLOR_CASE, fontSize: '0.8rem' }}
                        >
                          Open ghosting →
                        </Link>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
