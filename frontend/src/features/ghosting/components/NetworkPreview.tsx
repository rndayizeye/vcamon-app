import { type NetworkEdge, type PairResult, VERDICT_COLORS, verdictEdgeColor } from '../types-local'

type SvgNodePos = { pid: string; label: string; x: number; y: number }

const SVG_W = 400
const SVG_H = 280
const NODE_R = 22

function buildNodePositions(people: { _pid: string; name: string }[]): SvgNodePos[] {
  const N = people.length
  if (N === 0) return []
  const cx = SVG_W / 2
  const cy = SVG_H / 2
  const ringR = N <= 1 ? 0 : N === 2 ? 90 : N <= 4 ? 100 : 115
  return people.map((p, i) => {
    const angle = N === 1 ? -Math.PI / 2 : (2 * Math.PI * i) / N - Math.PI / 2
    return {
      pid: p._pid,
      label: p.name.trim() || `P${i + 1}`,
      x: cx + ringR * Math.cos(angle),
      y: cy + ringR * Math.sin(angle),
    }
  })
}

export function NetworkPreview({
  people,
  edges,
  resultMap,
}: {
  people: { _pid: string; name: string }[]
  edges: NetworkEdge[]
  resultMap: Map<string, PairResult>
}) {
  const nodes = buildNodePositions(people)
  const nodeMap = new Map(nodes.map(n => [n.pid, n]))

  if (people.length < 2) {
    return (
      <div
        className="panel"
        style={{ padding: '0.75rem', minHeight: 80, display: 'flex', alignItems: 'center' }}
      >
        <p style={{ color: '#aaa', fontSize: '0.82rem', margin: 0 }}>
          Add at least 2 patients to see the network preview.
        </p>
      </div>
    )
  }

  return (
    <div className="panel stack-sm" style={{ padding: '0.75rem' }}>
      <p className="eyebrow" style={{ margin: 0 }}>
        Network preview
      </p>
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        aria-label="Patient network preview"
      >
        {edges.map(edge => {
          if (edge.aId === edge.bId) return null
          const from = nodeMap.get(edge.aId)
          const to = nodeMap.get(edge.bId)
          if (!from || !to) return null
          const dx = to.x - from.x
          const dy = to.y - from.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 1) return null
          const ux = dx / dist
          const uy = dy / dist
          const pr = resultMap.get(edge.id)
          const color = verdictEdgeColor(pr?.result?.verdict)
          return (
            <line
              key={edge.id}
              x1={from.x + ux * NODE_R}
              y1={from.y + uy * NODE_R}
              x2={to.x - ux * NODE_R}
              y2={to.y - uy * NODE_R}
              stroke={color}
              strokeWidth={3}
              strokeLinecap="round"
            />
          )
        })}
        {nodes.map(node => (
          <g key={node.pid}>
            <circle cx={node.x} cy={node.y} r={NODE_R} fill="#6b6459" />
            <text
              x={node.x}
              y={node.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={9}
              fontWeight={700}
              fill="#fff"
              style={{ userSelect: 'none', pointerEvents: 'none' }}
            >
              {node.label.slice(0, 5)}
            </text>
          </g>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {Object.entries(VERDICT_COLORS).map(([v, c]) => (
          <div
            key={v}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem' }}
          >
            <div style={{ width: 20, height: 3, background: c, borderRadius: 2 }} />
            <span style={{ color: '#555' }}>{v}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem' }}>
          <div style={{ width: 20, height: 3, background: '#ccc', borderRadius: 2 }} />
          <span style={{ color: '#888' }}>Not yet run</span>
        </div>
      </div>
    </div>
  )
}
