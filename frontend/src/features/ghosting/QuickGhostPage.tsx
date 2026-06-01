import { useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'

import { runQuickGhostingAnalysis } from './api'
import type {
  GhostingAnalysisResult,
  GhostingCriteriaCheck,
  GhostingScenarioCriteria,
  GhostingSymptomInput,
  GhostedLesion,
} from './types'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SYMPTOM_TYPES = [
  'Primary Chancre',
  'Historical Primary',
  'Ghosted Primary',
  'Secondary Rash/Lesions',
]

const ANATOMICAL_SITES = [
  'Anal LX',
  'Oral LX',
  'Vaginal LX',
  'Penile LX',
  'Rectal LX',
  'Non-genital LX',
  'LX',
]

const BODY_PARTS = [
  { value: 'penis', label: 'Penis' },
  { value: 'vagina', label: 'Vagina / Vulva' },
  { value: 'anus', label: 'Anus / Rectum' },
  { value: 'mouth', label: 'Mouth' },
] as const

type BodyPartValue = (typeof BODY_PARTS)[number]['value']

const CLINICAL_REF = [
  { phase: 'Incubation', range: '10–21–90 d' },
  { phase: 'Primary chancre', range: '7–21–35 d' },
  { phase: 'Latency', range: '0–28–70 d' },
  { phase: 'Secondary', range: '14–28–42 d' },
]

// Verdict → edge color in the SVG preview
const VERDICT_COLORS: Record<string, string> = {
  SOURCE: '#1d9e75',
  SPREAD: '#378add',
  AMBIGUOUS: '#ef9f27',
  UNRELATED: '#e24b4a',
}

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

type SymptomRow = {
  type: string
  onset: string
  duration_days: number
  anatomical_site: string
}

// Each patient in the investigation — _pid is a stable local ID used by edges.
type NetworkPerson = {
  _pid: string
  name: string
  symptoms: SymptomRow[]
  exp_first: string
  exp_last: string
  body_parts: BodyPartValue[]
  treatment_date: string
}

// A connection between two patients — referenced by their _pid.
// "OP" and "Partner" are analytical roles derived by the engine, not by position here.
type NetworkEdge = {
  id: string
  aId: string
  bId: string
}

// The form only owns the patient list. Edges live in plain state so they can
// cross-reference patients by _pid without being part of a nested form structure.
type QuickGhostForm = {
  people: NetworkPerson[]
}

type PairResult = {
  label: string
  result: GhostingAnalysisResult | null
  error: string | null
}

const EMPTY_SYMPTOM: SymptomRow = {
  type: SYMPTOM_TYPES[0],
  onset: '',
  duration_days: 0,
  anatomical_site: '',
}

function makePersonDefaults(n: number): NetworkPerson {
  return {
    _pid: crypto.randomUUID(),
    name: `Patient ${n}`,
    symptoms: [],
    exp_first: '',
    exp_last: '',
    body_parts: [],
    treatment_date: '',
  }
}

function makeEdge(aId: string, bId: string): NetworkEdge {
  return { id: crypto.randomUUID(), aId, bId }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toSymptomInputs(rows: SymptomRow[]): GhostingSymptomInput[] {
  return rows
    .filter(r => r.type && r.onset)
    .map(r => ({
      type: r.type,
      onset: r.onset,
      duration_days: Number(r.duration_days) || 0,
      anatomical_site: r.anatomical_site || null,
    }))
}

function buildPayload(a: NetworkPerson, b: NetworkPerson) {
  const aHasExposure = a.exp_first && a.exp_last
  const bHasExposure = b.exp_first && b.exp_last
  return {
    op_name: a.name.trim() || 'Patient A',
    op_symptoms: toSymptomInputs(a.symptoms),
    op_exposure: aHasExposure
      ? { first: a.exp_first, last: a.exp_last, exposure_modalities: [] }
      : null,
    op_treatment_date: a.treatment_date || null,
    op_body_parts: a.body_parts,
    partner_name: b.name.trim() || 'Patient B',
    partner_symptoms: toSymptomInputs(b.symptoms),
    partner_exposure: bHasExposure
      ? { first: b.exp_first, last: b.exp_last, exposure_modalities: [] }
      : null,
    partner_treatment_date: b.treatment_date || null,
    partner_body_parts: b.body_parts,
  }
}

function isoAddDays(iso: string, days: number): string {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function dateInRange(d: string, start: string, end: string): boolean {
  return d >= start && d <= end
}

function computeInoculationAvg(symptom: GhostingSymptomInput): string {
  return isoAddDays(symptom.onset, -21)
}

function verdictEdgeColor(verdict: string | undefined): string {
  if (!verdict) return '#cccccc'
  const up = verdict.toUpperCase()
  if (up.includes('SOURCE')) return VERDICT_COLORS.SOURCE
  if (up.includes('SPREAD')) return VERDICT_COLORS.SPREAD
  if (up.includes('AMBIGUOUS') || up.includes('OVERLAP') || up.includes('⚠')) return VERDICT_COLORS.AMBIGUOUS
  if (up.includes('UNRELATED')) return VERDICT_COLORS.UNRELATED
  return '#cccccc'
}

// ---------------------------------------------------------------------------
// Symptom editor
// ---------------------------------------------------------------------------

function SymptomEditor({
  prefix,
  control,
  register,
}: {
  prefix: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
}) {
  const { fields, append, remove } = useFieldArray({ control, name: `${prefix}.symptoms` })
  return (
    <div className="stack-sm">
      <p className="eyebrow">Symptoms</p>
      {fields.length === 0 && (
        <p style={{ color: '#888', fontSize: '0.85rem', margin: 0 }}>
          No symptoms — click Add to enter one.
        </p>
      )}
      {fields.map((field, i) => (
        <div key={field.id} style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'flex-end' }}>
          <label className="field" style={{ margin: 0, flex: '2 1 140px', minWidth: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Type</span>}
            <select {...register(`${prefix}.symptoms.${i}.type`)}>
              {SYMPTOM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="field" style={{ margin: 0, flex: '1 1 130px', minWidth: 110 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Onset date</span>}
            <input type="date" {...register(`${prefix}.symptoms.${i}.onset`)} />
          </label>
          <label className="field" style={{ margin: 0, flex: '0 1 90px', minWidth: 70 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Duration (d)</span>}
            <input type="number" min={0} max={90}
              {...register(`${prefix}.symptoms.${i}.duration_days`, { valueAsNumber: true })} />
          </label>
          <label className="field" style={{ margin: 0, flex: '2 1 140px', minWidth: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Anatomical site</span>}
            <select {...register(`${prefix}.symptoms.${i}.anatomical_site`)}>
              <option value="">— none —</option>
              {ANATOMICAL_SITES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <button type="button" className="button" onClick={() => remove(i)}
            style={{ padding: '6px 10px', flex: '0 0 auto', alignSelf: 'flex-end' }}>
            ✕
          </button>
        </div>
      ))}
      <button type="button" className="button" style={{ alignSelf: 'flex-start' }}
        onClick={() => append({ ...EMPTY_SYMPTOM })}>
        + Add symptom
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Body parts checkboxes
// ---------------------------------------------------------------------------

function BodyPartsCheckboxes({
  prefix,
  register,
}: {
  prefix: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
}) {
  return (
    <div className="stack-xs">
      <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>Body parts used during contact</p>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {BODY_PARTS.map(({ value, label }) => (
          <label key={value}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem', cursor: 'pointer' }}>
            <input type="checkbox" value={value} {...register(`${prefix}.body_parts`)} />
            {label}
          </label>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Patient clinical data fields (shared by all patients)
// ---------------------------------------------------------------------------

function PatientClinicalFields({
  prefix,
  control,
  register,
}: {
  prefix: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
}) {
  return (
    <>
      <SymptomEditor prefix={prefix} control={control} register={register} />
      <div className="stack-sm">
        <p className="eyebrow">Exposure window</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <label className="field">
            <span>First exposure</span>
            <input type="date" {...register(`${prefix}.exp_first`)} />
          </label>
          <label className="field">
            <span>Last exposure</span>
            <input type="date" {...register(`${prefix}.exp_last`)} />
          </label>
        </div>
        <BodyPartsCheckboxes prefix={prefix} register={register} />
      </div>
      <label className="field">
        <span>Treatment date</span>
        <input type="date" {...register(`${prefix}.treatment_date`)} />
      </label>
    </>
  )
}

// ---------------------------------------------------------------------------
// Patient card (collapsible — expands to show clinical data)
// ---------------------------------------------------------------------------

function PatientCard({
  index,
  control,
  register,
  onRemove,
  canRemove,
}: {
  index: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
  onRemove: () => void
  canRemove: boolean
}) {
  const [open, setOpen] = useState(false)
  const prefix = `people.${index}`

  return (
    <div style={{ border: '1px solid #d8d3cb', borderRadius: '6px', overflow: 'hidden' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.75rem',
        padding: '0.5rem 0.75rem', background: '#f4f2ec',
        borderBottom: open ? '1px solid #d8d3cb' : 'none',
      }}>
        <button
          type="button"
          onClick={() => setOpen(o => !o)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: '0.8rem', color: '#666', flexShrink: 0 }}
          title={open ? 'Collapse' : 'Expand clinical data'}
        >
          {open ? '▼' : '▶'}
        </button>
        {/* Name inline in header for quick scanning */}
        <label className="field" style={{ margin: 0, flex: 1 }}>
          <input
            type="text"
            {...register(`${prefix}.name`)}
            placeholder={`Patient ${index + 1}`}
            style={{ fontWeight: 500, background: 'transparent', border: '1px solid transparent', borderRadius: '4px' }}
            onFocus={e => (e.currentTarget.style.borderColor = '#6b6459')}
            onBlur={e => (e.currentTarget.style.borderColor = 'transparent')}
          />
        </label>
        <span style={{ fontSize: '0.72rem', color: '#aaa', flexShrink: 0 }}>Patient {index + 1}</span>
        {canRemove && (
          <button type="button" className="button" onClick={onRemove}
            style={{ padding: '3px 8px', fontSize: '0.8rem', flexShrink: 0 }}>
            Remove
          </button>
        )}
      </div>
      {open && (
        <div className="stack-md" style={{ padding: '0.75rem 1rem' }}>
          <PatientClinicalFields prefix={prefix} control={control} register={register} />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Connections panel
// ---------------------------------------------------------------------------

function ConnectionsPanel({
  edges,
  people,
  onAdd,
  onRemove,
  onChangeA,
  onChangeB,
}: {
  edges: NetworkEdge[]
  people: { _pid: string; name: string }[]
  onAdd: () => void
  onRemove: (id: string) => void
  onChangeA: (id: string, pid: string) => void
  onChangeB: (id: string, pid: string) => void
}) {
  function displayName(pid: string): string {
    const idx = people.findIndex(p => p._pid === pid)
    const p = people[idx]
    if (!p) return '(removed)'
    return p.name.trim() || `Patient ${idx + 1}`
  }

  return (
    <div className="panel stack-md">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div>
          <p className="eyebrow" style={{ margin: 0 }}>Connections</p>
          <p style={{ fontSize: '0.8rem', color: '#888', margin: '2px 0 0' }}>
            Each connection is one VCA analysis. "OP" and "Partner" roles are determined by the engine, not by order here.
          </p>
        </div>
        <button
          type="button"
          className="button button-primary"
          onClick={onAdd}
          disabled={people.length < 2}
          style={{ fontSize: '0.85rem', padding: '4px 14px', flexShrink: 0 }}
          title={people.length < 2 ? 'Add at least 2 patients first' : undefined}
        >
          + Add connection
        </button>
      </div>

      {edges.length === 0 ? (
        <p style={{ color: '#888', fontSize: '0.875rem' }}>
          No connections yet. Add patients above, then connect them here.
        </p>
      ) : (
        <div className="stack-sm">
          {edges.map(edge => {
            const selfLoop = edge.aId === edge.bId
            return (
              <div key={edge.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <select
                  value={edge.aId}
                  onChange={e => onChangeA(edge.id, e.target.value)}
                  style={{ flex: '1 1 130px', padding: '5px 6px', borderRadius: '4px', border: '1px solid #ccc', fontSize: '0.875rem' }}
                >
                  {people.map((p, i) => (
                    <option key={p._pid} value={p._pid}>
                      {p.name.trim() || `Patient ${i + 1}`}
                    </option>
                  ))}
                </select>
                <span style={{ color: '#888', fontSize: '1rem', flexShrink: 0 }}>↔</span>
                <select
                  value={edge.bId}
                  onChange={e => onChangeB(edge.id, e.target.value)}
                  style={{ flex: '1 1 130px', padding: '5px 6px', borderRadius: '4px', border: '1px solid #ccc', fontSize: '0.875rem' }}
                >
                  {people.map((p, i) => (
                    <option key={p._pid} value={p._pid}>
                      {p.name.trim() || `Patient ${i + 1}`}
                    </option>
                  ))}
                </select>
                {selfLoop && (
                  <span style={{ fontSize: '0.78rem', color: '#e24b4a', flexShrink: 0 }}>
                    ⚠ Same person
                  </span>
                )}
                <button
                  type="button"
                  className="button"
                  onClick={() => onRemove(edge.id)}
                  style={{ padding: '4px 10px', fontSize: '0.8rem', flexShrink: 0 }}
                  title={`Remove connection: ${displayName(edge.aId)} ↔ ${displayName(edge.bId)}`}
                >
                  ×
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// SVG network preview
// ---------------------------------------------------------------------------

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

function NetworkPreview({
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
      <div className="panel" style={{ padding: '0.75rem', minHeight: 80, display: 'flex', alignItems: 'center' }}>
        <p style={{ color: '#aaa', fontSize: '0.82rem', margin: 0 }}>
          Add at least 2 patients to see the network preview.
        </p>
      </div>
    )
  }

  return (
    <div className="panel stack-sm" style={{ padding: '0.75rem' }}>
      <p className="eyebrow" style={{ margin: 0 }}>Network preview</p>
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        aria-label="Patient network preview"
      >
        {/* Edges */}
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
              x1={from.x + ux * NODE_R} y1={from.y + uy * NODE_R}
              x2={to.x - ux * NODE_R} y2={to.y - uy * NODE_R}
              stroke={color}
              strokeWidth={3}
              strokeLinecap="round"
            />
          )
        })}
        {/* Nodes */}
        {nodes.map(node => (
          <g key={node.pid}>
            <circle cx={node.x} cy={node.y} r={NODE_R} fill="#6b6459" />
            <text
              x={node.x} y={node.y}
              textAnchor="middle" dominantBaseline="central"
              fontSize={9} fontWeight={700} fill="#fff"
              style={{ userSelect: 'none', pointerEvents: 'none' }}
            >
              {node.label.slice(0, 5)}
            </text>
          </g>
        ))}
      </svg>
      {/* Legend */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {Object.entries(VERDICT_COLORS).map(([v, c]) => (
          <div key={v} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem' }}>
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

// ---------------------------------------------------------------------------
// Results: verdict + criteria display
// ---------------------------------------------------------------------------

function StatusBadge({ check }: { check: GhostingCriteriaCheck }) {
  const styles: Record<string, string> = {
    pass: 'badge badge-pass', fail: 'badge badge-fail', warn: 'badge badge-warn', na: 'badge badge-na',
  }
  const labels: Record<string, string> = {
    pass: '✓ Pass', fail: '✗ Fail', warn: '⚠ Warn', na: '— N/A',
  }
  return <span className={styles[check.status] ?? 'badge'}>{labels[check.status] ?? check.status}</span>
}

function EnhancedCriteriaTable({
  aggressive, expected, conservative, case1Symptom, ghostedLesion, case1Name,
}: {
  aggressive: GhostingScenarioCriteria
  expected: GhostingScenarioCriteria
  conservative: GhostingScenarioCriteria
  case1Symptom: GhostingSymptomInput
  ghostedLesion: GhostedLesion
  case1Name: string
}) {
  const inocAvg = computeInoculationAvg(case1Symptom)
  const inocInWindow = dateInRange(inocAvg, ghostedLesion.onset, ghostedLesion.end)
  const tdMuted: React.CSSProperties = { fontSize: '0.875rem', color: '#555' }
  return (
    <table className="data-table" style={{ width: '100%' }}>
      <thead>
        <tr><th>Criterion</th><th>Range</th><th>Result</th><th>Detail</th></tr>
      </thead>
      <tbody>
        <tr>
          <td rowSpan={2} style={{ fontWeight: 500, verticalAlign: 'middle' }}>Exposure</td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td><StatusBadge check={expected.exposure} /></td>
          <td style={tdMuted}>{expected.exposure.detail}</td>
        </tr>
        <tr style={{ background: 'rgba(0,0,0,0.02)' }}>
          <td style={{ fontSize: '0.78rem', color: '#888', paddingLeft: '1rem' }}>↳ Inoculation date</td>
          <td>
            <span className={inocInWindow ? 'badge badge-pass' : 'badge badge-fail'}>
              {inocInWindow ? '✓ In window' : '✗ Outside'}
            </span>
          </td>
          <td style={{ fontSize: '0.78rem', color: '#666' }}>
            {case1Name}'s avg inoculation ({inocAvg}) —{' '}
            {inocInWindow
              ? `within ghosted lesion (${ghostedLesion.onset} → ${ghostedLesion.end})`
              : `outside ghosted lesion (${ghostedLesion.onset} → ${ghostedLesion.end})`}
          </td>
        </tr>
        <tr>
          <td style={{ fontWeight: 500 }}>Exposure modality</td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td><StatusBadge check={expected.exposure_modality} /></td>
          <td style={tdMuted}>{expected.exposure_modality.detail}</td>
        </tr>
        <tr>
          <td rowSpan={3} style={{ fontWeight: 500, verticalAlign: 'middle' }}>Latency</td>
          <td style={{ fontSize: '0.8rem', color: '#888' }}>Optimistic (min)</td>
          <td><StatusBadge check={aggressive.latency} /></td>
          <td style={tdMuted}>{aggressive.latency.detail}</td>
        </tr>
        <tr style={{ background: 'rgba(0,0,0,0.02)' }}>
          <td style={{ fontSize: '0.8rem', fontWeight: 600 }}>Expected (avg)</td>
          <td><StatusBadge check={expected.latency} /></td>
          <td style={tdMuted}>{expected.latency.detail}</td>
        </tr>
        <tr>
          <td style={{ fontSize: '0.8rem', color: '#888' }}>Conservative (max)</td>
          <td><StatusBadge check={conservative.latency} /></td>
          <td style={tdMuted}>{conservative.latency.detail}</td>
        </tr>
        <tr>
          <td style={{ fontWeight: 500 }}>Natural order</td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td><StatusBadge check={expected.natural_order} /></td>
          <td style={tdMuted}>{expected.natural_order.detail}</td>
        </tr>
      </tbody>
    </table>
  )
}

function VerdictBanner({ verdict, compact }: { verdict: string; compact?: boolean }) {
  const up = verdict.toUpperCase()
  let color = '#e24b4a', bg = '#fdf0f0', border = '#e24b4a'
  if (up.includes('AMBIGUOUS') || up.includes('⚠') || up.includes('OVERLAP')) { color = '#8a6d00'; bg = '#fef8ec'; border = '#ef9f27' }
  else if (up.includes('SOURCE')) { color = '#1d9e75'; bg = '#eafaf3'; border = '#1d9e75' }
  else if (up.includes('SPREAD')) { color = '#378add'; bg = '#e8f3fd'; border = '#378add' }

  if (compact) {
    return (
      <span style={{ padding: '2px 10px', borderRadius: '4px', background: bg, border: `1px solid ${border}`, color, fontSize: '0.8rem', fontWeight: 700, whiteSpace: 'nowrap' }}>
        {verdict}
      </span>
    )
  }
  return (
    <div style={{ padding: '1rem 1.25rem', borderRadius: '8px', background: bg, border: `1.5px solid ${border}`, color }}>
      <span style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.08em', opacity: 0.7, display: 'block', marginBottom: '0.25rem' }}>SOURCE SPREAD ANALYSIS</span>
      <p style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>{verdict}</p>
    </div>
  )
}

function VerdictContext({ result }: { result: GhostingAnalysisResult }) {
  const srcE = result.source_scenarios.range_data.expected
  const sprE = result.spread_scenarios.range_data.expected
  const srcL = result.source_scenarios.range_lesions.expected
  const sprL = result.spread_scenarios.range_lesions.expected
  const c1 = result.case1_name
  const c2 = result.case2_name

  type Item = { scenario: string; text: string }
  const passing: Item[] = []
  const failing: Item[] = []

  if (srcE.exposure.status === 'pass') passing.push({ scenario: 'Source', text: srcE.exposure.detail })
  else if (srcE.exposure.status === 'fail') failing.push({ scenario: 'Source', text: `${c1} was likely not infected by ${c2} — exposure window does not overlap with ${c2}'s ghosted source lesion (${srcL.onset} → ${srcL.end}).` })
  if (srcE.exposure_modality.status === 'pass') passing.push({ scenario: 'Source', text: srcE.exposure_modality.detail })
  else if (srcE.exposure_modality.status === 'fail') failing.push({ scenario: 'Source', text: `Contact type is not compatible with the site of ${c1}'s ${result.case1_symptom.type}.` })
  if (srcE.latency.status === 'pass') passing.push({ scenario: 'Source', text: srcE.latency.detail })
  else if (srcE.latency.status === 'fail') failing.push({ scenario: 'Source', text: srcE.latency.detail })
  if (srcE.natural_order.status === 'pass') passing.push({ scenario: 'Source', text: srcE.natural_order.detail })
  else if (srcE.natural_order.status === 'fail') failing.push({ scenario: 'Source', text: `Ghosted source lesion would occur after ${c2}'s secondary lesion — primary must precede secondary.` })

  if (sprE.exposure.status === 'pass') passing.push({ scenario: 'Spread', text: sprE.exposure.detail })
  else if (sprE.exposure.status === 'fail') failing.push({ scenario: 'Spread', text: `${c2} was likely not infected by ${c1} — exposure window does not overlap with ${c1}'s infectious period (${sprL.onset} → ${sprL.end}).` })
  if (sprE.exposure_modality.status === 'pass') passing.push({ scenario: 'Spread', text: sprE.exposure_modality.detail })
  else if (sprE.exposure_modality.status === 'fail') failing.push({ scenario: 'Spread', text: `Contact type is not compatible with the site of ${c1}'s ${result.case1_symptom.type}. ${sprE.exposure_modality.detail}` })
  if (sprE.latency.status === 'pass') passing.push({ scenario: 'Spread', text: sprE.latency.detail })
  else if (sprE.latency.status === 'fail') failing.push({ scenario: 'Spread', text: sprE.latency.detail })
  if (sprE.natural_order.status === 'pass') passing.push({ scenario: 'Spread', text: sprE.natural_order.detail })
  else if (sprE.natural_order.status === 'fail') failing.push({ scenario: 'Spread', text: `Ghosted spread lesion would occur after ${c2}'s secondary lesion — primary must precede secondary.` })

  return (
    <div style={{ borderRadius: '6px', padding: '0.75rem 1rem', fontSize: '0.875rem', border: '1px solid #dde', background: '#f9f9fb' }}>
      <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Why?</p>
      {passing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#1d9e75', marginBottom: '0.25rem' }}>Supporting evidence:</p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem', marginBottom: failing.length ? '0.75rem' : 0 }}>
            {passing.map((p, i) => (
              <li key={i} style={{ marginBottom: '0.35rem' }}>
                <strong style={{ color: '#1d9e75' }}>[{p.scenario}]</strong>{' '}{p.text}
              </li>
            ))}
          </ul>
        </>
      )}
      {failing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#e24b4a', marginBottom: '0.25rem' }}>Limiting factors:</p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {failing.map((f, i) => (
              <li key={i} style={{ marginBottom: '0.35rem' }}>
                <strong style={{ color: '#c0392b' }}>[{f.scenario}]</strong>{' '}{f.text}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function PairResultDetail({ pair }: { pair: PairResult }) {
  const [logOpen, setLogOpen] = useState(false)
  const [scenarioTab, setScenarioTab] = useState<'source' | 'spread'>('source')
  const { result } = pair

  if (!result) {
    return <p className="error-text">{pair.error}</p>
  }

  const srcLesion = result.source_scenarios.range_lesions.expected
  const sprLesion = result.spread_scenarios.range_lesions.expected
  const activeScenario = scenarioTab === 'source' ? result.source_scenarios : result.spread_scenarios
  const activeGhostedLesion = scenarioTab === 'source' ? result.ghosted_source : result.ghosted_spread

  return (
    <div className="stack-lg">
      <VerdictBanner verdict={result.verdict} />
      <VerdictContext result={result} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        {[
          { label: 'Ghosted source onset', val: srcLesion.onset },
          { label: 'Ghosted source end', val: srcLesion.end },
          { label: 'Ghosted spread onset', val: sprLesion.onset },
          { label: 'Ghosted spread end', val: sprLesion.end },
        ].map(({ label, val }) => (
          <div key={label} className="panel stack-xs">
            <p className="eyebrow">{label}</p>
            <p style={{ fontWeight: 700, fontSize: '1.05rem' }}>{val}</p>
          </div>
        ))}
      </div>

      <div className="panel stack-xs">
        <p className="eyebrow">Anchor symptom (engine-selected OP)</p>
        <p style={{ fontSize: '0.9rem' }}>
          <strong>{result.case1_name}</strong> · {result.case1_symptom.type} · Onset {result.case1_symptom.onset}
          {result.case1_symptom.duration_days > 0 ? ` · Duration ${result.case1_symptom.duration_days}d` : ''}
          {' · '}Avg inoculation: <strong>{computeInoculationAvg(result.case1_symptom)}</strong>
        </p>
        <p style={{ fontSize: '0.82rem', color: '#888' }}>
          Comparison patient: {result.case2_name}
        </p>
      </div>

      <div className="panel stack-md">
        <nav className="tab-nav" aria-label="Scenario">
          {(['source', 'spread'] as const).map(tab => (
            <button key={tab} type="button"
              className={scenarioTab === tab ? 'tab-link tab-link-active' : 'tab-link'}
              onClick={() => setScenarioTab(tab)}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)} scenario
            </button>
          ))}
        </nav>
        <div style={{ background: '#f8f9fa', borderLeft: '3px solid #378add', padding: '0.75rem 1rem', fontSize: '0.875rem', borderRadius: '0 4px 4px 0' }}>
          <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>Hypothesis</p>
          <p>
            {scenarioTab === 'source'
              ? `Whether ${result.case2_name} was the source who infected ${result.case1_name}.`
              : `Whether ${result.case1_name} spread the infection to ${result.case2_name}.`}
          </p>
        </div>
        <div style={{ fontSize: '0.82rem', color: '#555' }}>
          Confidence: <strong>{activeScenario.confidence}</strong>
          &nbsp;·&nbsp;Criteria passed: {activeScenario.pass_count} / 4
        </div>
        <EnhancedCriteriaTable
          aggressive={activeScenario.range_data.aggressive}
          expected={activeScenario.range_data.expected}
          conservative={activeScenario.range_data.conservative}
          case1Symptom={result.case1_symptom}
          ghostedLesion={activeGhostedLesion}
          case1Name={result.case1_name}
        />
      </div>

      <div className="panel stack-sm">
        <button type="button" className="button" onClick={() => setLogOpen(o => !o)} style={{ alignSelf: 'flex-start' }}>
          {logOpen ? '▲ Hide' : '▼ Show'} step-by-step log
        </button>
        {logOpen && (
          <pre style={{ background: '#F4F2EC', padding: '0.75rem', borderRadius: '4px', fontSize: '0.8rem', lineHeight: 1.6, overflowX: 'auto', margin: 0 }}>
            {result.log.join('\n')}
          </pre>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Results section — one card per edge
// ---------------------------------------------------------------------------

function ResultsSection({
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
          {resultMap.size} pair{resultMap.size !== 1 ? 's' : ''} analyzed — click any row to expand details.
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
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                background: 'none', border: 'none', padding: 0, cursor: 'pointer', width: '100%', textAlign: 'left', gap: '1rem',
              }}
            >
              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                {displayName(edge.aId)} ↔ {displayName(edge.bId)}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
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

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function QuickGhostPage() {
  const [edges, setEdges] = useState<NetworkEdge[]>([])
  const [resultMap, setResultMap] = useState<Map<string, PairResult>>(new Map())
  const [apiError, setApiError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const defaultPeople = [makePersonDefaults(1), makePersonDefaults(2)]

  const { register, control, getValues, reset, watch } = useForm<QuickGhostForm>({
    defaultValues: { people: defaultPeople },
  })

  const { fields: peopleFields, append: appendPerson, remove: removePerson } = useFieldArray({
    control,
    name: 'people',
  })

  // Reactive people list for dropdowns and SVG preview
  const watchedPeople = watch('people')

  function handleAddPerson() {
    appendPerson(makePersonDefaults(peopleFields.length + 1))
  }

  function handleRemovePerson(idx: number) {
    const pid = getValues(`people.${idx}._pid`)
    // Drop any edges that referenced the removed person
    setEdges(prev => prev.filter(e => e.aId !== pid && e.bId !== pid))
    removePerson(idx)
  }

  function handleAddEdge() {
    const people = getValues('people')
    if (people.length < 2) return
    // Default: first two people, or first unused pair
    setEdges(prev => [...prev, makeEdge(people[0]._pid, people[1]._pid)])
  }

  function handleRemoveEdge(id: string) {
    setEdges(prev => prev.filter(e => e.id !== id))
  }

  function handleChangeEdgeA(id: string, pid: string) {
    setEdges(prev => prev.map(e => e.id === id ? { ...e, aId: pid } : e))
  }

  function handleChangeEdgeB(id: string, pid: string) {
    setEdges(prev => prev.map(e => e.id === id ? { ...e, bId: pid } : e))
  }

  async function onRunAnalysis() {
    setApiError(null)
    setResultMap(new Map())
    setLoading(true)

    const validEdges = edges.filter(e => e.aId !== e.bId)
    if (validEdges.length === 0) {
      setApiError('Add at least one valid connection (between two different patients) to run the analysis.')
      setLoading(false)
      return
    }

    const people = getValues('people')
    const newMap = new Map<string, PairResult>()

    for (const edge of validEdges) {
      const personA = people.find(p => p._pid === edge.aId)
      const personB = people.find(p => p._pid === edge.bId)
      if (!personA || !personB) continue

      const idxA = people.indexOf(personA)
      const idxB = people.indexOf(personB)
      const nameA = personA.name.trim() || `Patient ${idxA + 1}`
      const nameB = personB.name.trim() || `Patient ${idxB + 1}`
      const label = `${nameA} ↔ ${nameB}`

      try {
        const result = await runQuickGhostingAnalysis(buildPayload(personA, personB))
        newMap.set(edge.id, { label, result, error: null })
      } catch (err: unknown) {
        newMap.set(edge.id, { label, result: null, error: err instanceof Error ? err.message : 'Analysis failed.' })
      }
    }

    setResultMap(newMap)
    setLoading(false)
  }

  function handleClear() {
    const fresh = [makePersonDefaults(1), makePersonDefaults(2)]
    reset({ people: fresh })
    setEdges([])
    setResultMap(new Map())
    setApiError(null)
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem' }}>
      <div className="stack-lg">

        {/* Header */}
        <header className="panel stack-sm">
          <div>
            <p className="eyebrow">Tools</p>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Quick Ghosting Analysis</h1>
          </div>
          <p style={{ color: '#555', fontSize: '0.9rem', maxWidth: 720 }}>
            Add any number of patients, then draw connections between them.
            Each connection is one VCA analysis — the engine determines who is the
            anchor ("OP") from the clinical data, so roles shift per pair rather than
            being fixed by form position.
          </p>
          <details style={{ marginTop: '0.25rem' }}>
            <summary style={{ cursor: 'pointer', fontSize: '0.85rem', color: '#444', fontWeight: 500 }}>
              Clinical reference constants
            </summary>
            <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
              {CLINICAL_REF.map(r => (
                <div key={r.phase}>
                  <p className="eyebrow" style={{ marginBottom: '2px' }}>{r.phase}</p>
                  <p style={{ fontSize: '0.85rem', fontWeight: 600 }}>{r.range}</p>
                </div>
              ))}
            </div>
          </details>
        </header>

        {/* Two-column layout: patients left, network preview right */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.5rem', alignItems: 'start' }}>

          {/* Left: patients */}
          <div className="stack-md">
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <p className="eyebrow" style={{ margin: 0 }}>
                Patients{' '}
                <span style={{ color: '#aaa', fontWeight: 400 }}>({peopleFields.length})</span>
              </p>
              <button
                type="button"
                className="button button-primary"
                onClick={handleAddPerson}
                style={{ fontSize: '0.85rem', padding: '4px 12px' }}
              >
                + Add patient
              </button>
            </div>
            <div className="stack-sm">
              {peopleFields.map((field, i) => (
                <PatientCard
                  key={field.id}
                  index={i}
                  control={control}
                  register={register}
                  onRemove={() => handleRemovePerson(i)}
                  canRemove={peopleFields.length > 2}
                />
              ))}
            </div>
          </div>

          {/* Right: network preview */}
          <div>
            <NetworkPreview
              people={watchedPeople}
              edges={edges}
              resultMap={resultMap}
            />
          </div>
        </div>

        {/* Connections */}
        <ConnectionsPanel
          edges={edges}
          people={watchedPeople}
          onAdd={handleAddEdge}
          onRemove={handleRemoveEdge}
          onChangeA={handleChangeEdgeA}
          onChangeB={handleChangeEdgeB}
        />

        {/* Actions */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="button button-primary"
            type="button"
            onClick={onRunAnalysis}
            disabled={loading || edges.length === 0}
            style={{ minWidth: 200 }}
          >
            {loading ? 'Running…' : '▶ Run analysis'}
          </button>
          <button type="button" className="button" onClick={handleClear} disabled={loading}>
            Clear all
          </button>
          {apiError && <p className="error-text" style={{ margin: 0 }}>{apiError}</p>}
        </div>

        {/* Results */}
        {resultMap.size > 0 && (
          <ResultsSection
            edges={edges}
            people={watchedPeople}
            resultMap={resultMap}
          />
        )}

      </div>
    </div>
  )
}
