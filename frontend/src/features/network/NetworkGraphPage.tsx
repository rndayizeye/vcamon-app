import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { EmptyState } from '../../components/feedback/EmptyState'
import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
import { CreateLinkForm } from '../analytics/components/CreateLinkForm'
import { LinkList } from '../analytics/components/LinkList'
import { useCaseAnalytics, useCaseLinks } from '../analytics/hooks'
import type { AnalyticsNodeRead, ArrowLinkRead } from '../analytics/types'

// ---------------------------------------------------------------------------
// Color constants (matching Streamlit page)
// ---------------------------------------------------------------------------

const COLOR_OP = '#D85A30'
const COLOR_TREATED = '#1D9E75'
const COLOR_UNTREATED = '#EF9F27'
const COLOR_EDGE = '#534AB7'

const OP_R = 28
const PARTNER_R = 22
const RING_RADIUS = 155
const SVG_W = 700
const SVG_H = 420
const CX = SVG_W / 2
const CY = SVG_H / 2

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type NodePos = { x: number; y: number; r: number }

// ---------------------------------------------------------------------------
// Layout helpers
// ---------------------------------------------------------------------------

function buildPositions(nodes: AnalyticsNodeRead[]): Map<string, NodePos> {
  const pos = new Map<string, NodePos>()
  const opNode = nodes.find(n => n.ref === 'OP')
  const partnerNodes = nodes.filter(n => n.ref !== 'OP')
  const N = partnerNodes.length

  if (opNode) {
    pos.set('OP', { x: CX, y: CY, r: OP_R })
  }

  partnerNodes.forEach((p, i) => {
    const angle = N === 1 ? -Math.PI / 2 : (2 * Math.PI * i) / N - Math.PI / 2
    pos.set(p.ref, {
      x: CX + RING_RADIUS * Math.cos(angle),
      y: CY + RING_RADIUS * Math.sin(angle),
      r: PARTNER_R,
    })
  })

  return pos
}

function nodeColor(node: AnalyticsNodeRead): string {
  if (node.ref === 'OP') return COLOR_OP
  return node.treated ? COLOR_TREATED : COLOR_UNTREATED
}

// ---------------------------------------------------------------------------
// SVG sub-components
// ---------------------------------------------------------------------------

function EdgeArrow({ edge, positions }: { edge: ArrowLinkRead; positions: Map<string, NodePos> }) {
  const from = positions.get(edge.from_ref)
  const to = positions.get(edge.to_ref)
  if (!from || !to) return null

  const dx = to.x - from.x
  const dy = to.y - from.y
  const dist = Math.sqrt(dx * dx + dy * dy)
  if (dist < 1) return null

  const ux = dx / dist
  const uy = dy / dist
  const x1 = from.x + ux * (from.r + 4)
  const y1 = from.y + uy * (from.r + 4)
  const x2 = to.x - ux * (to.r + 12)
  const y2 = to.y - uy * (to.r + 12)

  return (
    <line
      x1={x1} y1={y1} x2={x2} y2={y2}
      stroke={COLOR_EDGE}
      strokeWidth={2}
      markerEnd="url(#arrow)"
    />
  )
}

function NodeCircle({ node, pos }: { node: AnalyticsNodeRead; pos: NodePos }) {
  const [hovered, setHovered] = useState(false)
  const color = nodeColor(node)
  const shortLabel = node.ref === 'OP' ? 'OP' : `P${node.partner_number ?? node.ref}`
  const tooltipWidth = Math.max(node.label.length * 6.5, 70)

  // Clamp tooltip so it doesn't go off canvas
  let ttX = pos.x + pos.r + 6
  if (ttX + tooltipWidth > SVG_W - 10) ttX = pos.x - pos.r - 6 - tooltipWidth

  return (
    <g
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ cursor: 'default' }}
    >
      <circle cx={pos.x} cy={pos.y} r={pos.r} fill={color} />
      <text
        x={pos.x}
        y={pos.y}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={11}
        fontWeight={700}
        fill="#fff"
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        {shortLabel}
      </text>
      {hovered && (
        <g>
          <rect
            x={ttX - 4}
            y={pos.y - 14}
            width={tooltipWidth + 8}
            height={22}
            rx={4}
            fill="rgba(0,0,0,0.78)"
          />
          <text
            x={ttX}
            y={pos.y + 3}
            fontSize={11}
            fill="#fff"
            style={{ pointerEvents: 'none' }}
          >
            {node.label}
          </text>
        </g>
      )}
    </g>
  )
}

// ---------------------------------------------------------------------------
// Full SVG graph
// ---------------------------------------------------------------------------

function NetworkSvg({ nodes, edges }: { nodes: AnalyticsNodeRead[]; edges: ArrowLinkRead[] }) {
  const positions = buildPositions(nodes)

  return (
    <svg
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      style={{ width: '100%', height: 'auto', display: 'block' }}
      aria-label="Transmission network graph"
    >
      <defs>
        <marker
          id="arrow"
          markerWidth="8"
          markerHeight="6"
          refX="6"
          refY="3"
          orient="auto"
        >
          <polygon points="0 0, 8 3, 0 6" fill={COLOR_EDGE} />
        </marker>
      </defs>

      {/* Edges drawn before nodes so nodes appear on top */}
      {edges.map(edge => (
        <EdgeArrow key={edge.id} edge={edge} positions={positions} />
      ))}

      {nodes.map(node => {
        const pos = positions.get(node.ref)
        if (!pos) return null
        return <NodeCircle key={node.ref} node={node} pos={pos} />
      })}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
      <div style={{ width: 13, height: 13, borderRadius: '50%', background: color, flexShrink: 0 }} />
      <span style={{ fontSize: '0.82rem', color: '#444' }}>{label}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function NetworkGraphPage() {
  const { caseId } = useParams()
  const parsedCaseId = Number(caseId)
  const [asOfDate, setAsOfDate] = useState('')

  const analyticsQuery = useCaseAnalytics(parsedCaseId, asOfDate || undefined)
  const linksQuery = useCaseLinks(parsedCaseId)

  if (!Number.isInteger(parsedCaseId) || parsedCaseId <= 0) {
    return <ErrorState title="Invalid case" message="The case id is not valid." />
  }

  if (analyticsQuery.isLoading) {
    return <LoadingState message="Loading network…" />
  }

  if (analyticsQuery.isError) {
    return (
      <ErrorState
        title="Unable to load network"
        message={analyticsQuery.error.message}
        onRetry={() => void analyticsQuery.refetch()}
      />
    )
  }

  if (!analyticsQuery.data) {
    return <EmptyState title="No network data" />
  }

  const { nodes, edges } = analyticsQuery.data

  return (
    <section className="stack-lg">
      {/* Header */}
      <header className="panel stack-md">
        <div>
          <p className="eyebrow">Network</p>
          <h2>Transmission network</h2>
          <p className="muted small-text">
            This network maps transmission relationships between the index patient and all contacts.
          </p>
        </div>
        <label className="field field-inline">
          <span>As-of date</span>
          <input
            type="date"
            value={asOfDate}
            onChange={e => setAsOfDate(e.target.value)}
          />
        </label>
      </header>

      {/* Legend */}
      <div className="panel" style={{ paddingBlock: '0.75rem' }}>
        <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap' }}>
          <LegendDot color={COLOR_OP} label="Original patient (OP)" />
          <LegendDot color={COLOR_TREATED} label="Partner — treated" />
          <LegendDot color={COLOR_UNTREATED} label="Partner — untreated" />
          <LegendDot color={COLOR_EDGE} label="Transmission link" />
        </div>
      </div>

      {/* Graph */}
      <div className="panel">
        {nodes.length === 0 ? (
          <EmptyState title="No nodes" message="No parties visible for the selected date." />
        ) : nodes.length === 1 ? (
          <>
            <NetworkSvg nodes={nodes} edges={edges} />
            <p style={{ textAlign: 'center', color: '#888', fontSize: '0.85rem', marginTop: '0.5rem' }}>
              Add partners to this case to see the transmission network.
            </p>
          </>
        ) : (
          <NetworkSvg nodes={nodes} edges={edges} />
        )}
      </div>

      {/* Summary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
        <div className="panel stack-xs">
          <p className="eyebrow">Nodes</p>
          <p style={{ fontSize: '1.75rem', fontWeight: 700 }}>{nodes.length}</p>
        </div>
        <div className="panel stack-xs">
          <p className="eyebrow">Transmission links</p>
          <p style={{ fontSize: '1.75rem', fontWeight: 700 }}>{edges.length}</p>
        </div>
        <div className="panel stack-xs">
          <p className="eyebrow">Untreated partners</p>
          <p style={{ fontSize: '1.75rem', fontWeight: 700 }}>
            {nodes.filter(n => n.ref !== 'OP' && !n.treated).length}
          </p>
        </div>
      </div>

      {/* Link management */}
      <div className="two-column-grid analytics-actions-grid">
        <CreateLinkForm caseId={parsedCaseId} nodes={nodes} />
        {linksQuery.data ? (
          <LinkList caseId={parsedCaseId} links={linksQuery.data} />
        ) : null}
      </div>
    </section>
  )
}
