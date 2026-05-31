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

// ---------------------------------------------------------------------------
// Form types
// ---------------------------------------------------------------------------

type SymptomRow = {
  type: string
  onset: string
  duration_days: number
  anatomical_site: string
}

type PersonFields = {
  name: string
  symptoms: SymptomRow[]
  exp_first: string
  exp_last: string
  body_parts: BodyPartValue[]
  treatment_date: string
}

type QuickGhostForm = {
  person_a: PersonFields
  partners: PersonFields[]
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

const DEFAULT_PERSON: PersonFields = {
  name: '',
  symptoms: [],
  exp_first: '',
  exp_last: '',
  body_parts: [],
  treatment_date: '',
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

function buildPayload(op: PersonFields, partner: PersonFields) {
  const opSymptoms = toSymptomInputs(op.symptoms)
  const partnerSymptoms = toSymptomInputs(partner.symptoms)
  const opHasExposure = op.exp_first && op.exp_last
  const partnerHasExposure = partner.exp_first && partner.exp_last
  return {
    op_name: op.name.trim() || 'Person A',
    op_symptoms: opSymptoms,
    op_exposure: opHasExposure
      ? { first: op.exp_first, last: op.exp_last, exposure_modalities: [] }
      : null,
    op_treatment_date: op.treatment_date || null,
    op_body_parts: op.body_parts,
    partner_name: partner.name.trim() || 'Partner',
    partner_symptoms: partnerSymptoms,
    partner_exposure: partnerHasExposure
      ? { first: partner.exp_first, last: partner.exp_last, exposure_modalities: [] }
      : null,
    partner_treatment_date: partner.treatment_date || null,
    partner_body_parts: partner.body_parts,
  }
}

// ---------------------------------------------------------------------------
// Symptom editor sub-component
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
  const { fields, append, remove } = useFieldArray({
    control,
    name: `${prefix}.symptoms`,
  })

  return (
    <div className="stack-sm">
      <p className="eyebrow">Symptoms</p>
      {fields.length === 0 && (
        <p style={{ color: '#888', fontSize: '0.85rem', margin: 0 }}>
          No symptoms — click Add to enter one.
        </p>
      )}
      {fields.map((field, i) => (
        <div
          key={field.id}
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.5rem',
            alignItems: 'flex-end',
          }}
        >
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
            <input
              type="number"
              min={0}
              max={90}
              {...register(`${prefix}.symptoms.${i}.duration_days`, { valueAsNumber: true })}
            />
          </label>
          <label className="field" style={{ margin: 0, flex: '2 1 140px', minWidth: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Anatomical site</span>}
            <select {...register(`${prefix}.symptoms.${i}.anatomical_site`)}>
              <option value="">— none —</option>
              {ANATOMICAL_SITES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <button
            type="button"
            className="button"
            onClick={() => remove(i)}
            style={{ padding: '6px 10px', flex: '0 0 auto', alignSelf: 'flex-end' }}
            title="Remove symptom"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className="button"
        style={{ alignSelf: 'flex-start' }}
        onClick={() => append({ ...EMPTY_SYMPTOM })}
      >
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
      <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>
        Body parts used during contact
      </p>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {BODY_PARTS.map(({ value, label }) => (
          <label
            key={value}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem', cursor: 'pointer' }}
          >
            <input type="checkbox" value={value} {...register(`${prefix}.body_parts`)} />
            {label}
          </label>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Person panel (reusable for OP and each partner)
// ---------------------------------------------------------------------------

function PersonPanel({
  prefix,
  label,
  control,
  register,
  onRemove,
}: {
  prefix: string
  label: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
  onRemove?: () => void
}) {
  return (
    <div className="panel stack-md">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <p className="eyebrow">{label}</p>
          <label className="field" style={{ marginTop: '0.5rem' }}>
            <span>Name / identifier</span>
            <input type="text" {...register(`${prefix}.name`)} placeholder={label} />
          </label>
        </div>
        {onRemove && (
          <button
            type="button"
            className="button"
            onClick={onRemove}
            style={{ marginLeft: '0.75rem', padding: '4px 10px', fontSize: '0.8rem' }}
            title="Remove this partner"
          >
            Remove
          </button>
        )}
      </div>

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
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared criteria / verdict components
// ---------------------------------------------------------------------------

function StatusBadge({ check }: { check: GhostingCriteriaCheck }) {
  const styles: Record<string, string> = {
    pass: 'badge badge-pass',
    fail: 'badge badge-fail',
    warn: 'badge badge-warn',
    na: 'badge badge-na',
  }
  const labels: Record<string, string> = {
    pass: '✓ Pass',
    fail: '✗ Fail',
    warn: '⚠ Warn',
    na: '— N/A',
  }
  return (
    <span className={styles[check.status] ?? 'badge'}>
      {labels[check.status] ?? check.status}
    </span>
  )
}

function EnhancedCriteriaTable({
  aggressive,
  expected,
  conservative,
  case1Symptom,
  ghostedLesion,
  case1Name,
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
        <tr>
          <th>Criterion</th>
          <th>Range</th>
          <th>Result</th>
          <th>Detail</th>
        </tr>
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

function VerdictBanner({ verdict }: { verdict: string }) {
  const upper = verdict.toUpperCase()
  let color = '#e24b4a'
  let bg = '#fdf0f0'
  let border = '#e24b4a'
  if (upper.includes('UNRELATED')) { color = '#e24b4a'; bg = '#fdf0f0'; border = '#e24b4a' }
  else if (upper.includes('AMBIGUOUS')) { color = '#8a6d00'; bg = '#fef8ec'; border = '#ef9f27' }
  else if (upper.includes('⚠') || upper.includes('OVERLAP')) { color = '#8a6d00'; bg = '#fef8ec'; border = '#ef9f27' }
  else if (upper.includes('SOURCE')) { color = '#1d9e75'; bg = '#eafaf3'; border = '#1d9e75' }
  else if (upper.includes('SPREAD')) { color = '#378add'; bg = '#e8f3fd'; border = '#378add' }

  return (
    <div style={{ padding: '1rem 1.25rem', borderRadius: '8px', background: bg, border: `1.5px solid ${border}`, color }}>
      <span style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.08em', opacity: 0.7, display: 'block', marginBottom: '0.25rem' }}>
        SOURCE SPREAD ANALYSIS
      </span>
      <p style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>{verdict}</p>
    </div>
  )
}

function VerdictContext({ result }: { result: GhostingAnalysisResult }) {
  const srcExpected = result.source_scenarios.range_data.expected
  const sprExpected = result.spread_scenarios.range_data.expected
  const srcLesion = result.source_scenarios.range_lesions.expected
  const sprLesion = result.spread_scenarios.range_lesions.expected
  const c1 = result.case1_name
  const c2 = result.case2_name

  type Item = { scenario: string; text: string }
  const passing: Item[] = []
  const failing: Item[] = []

  if (srcExpected.exposure.status === 'pass') passing.push({ scenario: 'Source', text: srcExpected.exposure.detail })
  else if (srcExpected.exposure.status === 'fail') failing.push({ scenario: 'Source', text: `${c1} was likely not infected by ${c2} — the exposure window does not overlap with ${c2}'s ghosted source lesion (${srcLesion.onset} → ${srcLesion.end}).` })
  if (srcExpected.exposure_modality.status === 'pass') passing.push({ scenario: 'Source', text: srcExpected.exposure_modality.detail })
  else if (srcExpected.exposure_modality.status === 'fail') failing.push({ scenario: 'Source', text: `The type of sexual contact is not compatible with the site of ${c1}'s ${result.case1_symptom.type}.` })
  if (srcExpected.latency.status === 'pass') passing.push({ scenario: 'Source', text: srcExpected.latency.detail })
  else if (srcExpected.latency.status === 'fail') failing.push({ scenario: 'Source', text: srcExpected.latency.detail })
  if (srcExpected.natural_order.status === 'pass') passing.push({ scenario: 'Source', text: srcExpected.natural_order.detail })
  else if (srcExpected.natural_order.status === 'fail') failing.push({ scenario: 'Source', text: `The ghosted source lesion would have occurred after ${c2}'s existing secondary lesion — primary must precede secondary.` })

  if (sprExpected.exposure.status === 'pass') passing.push({ scenario: 'Spread', text: sprExpected.exposure.detail })
  else if (sprExpected.exposure.status === 'fail') failing.push({ scenario: 'Spread', text: `${c2} was likely not infected by ${c1} — the exposure window does not overlap with ${c1}'s infectious period (${sprLesion.onset} → ${sprLesion.end}).` })
  if (sprExpected.exposure_modality.status === 'pass') passing.push({ scenario: 'Spread', text: sprExpected.exposure_modality.detail })
  else if (sprExpected.exposure_modality.status === 'fail') failing.push({ scenario: 'Spread', text: `The type of sexual contact is not compatible with the site of ${c1}'s ${result.case1_symptom.type}. ${sprExpected.exposure_modality.detail}` })
  if (sprExpected.latency.status === 'pass') passing.push({ scenario: 'Spread', text: sprExpected.latency.detail })
  else if (sprExpected.latency.status === 'fail') failing.push({ scenario: 'Spread', text: sprExpected.latency.detail })
  if (sprExpected.natural_order.status === 'pass') passing.push({ scenario: 'Spread', text: sprExpected.natural_order.detail })
  else if (sprExpected.natural_order.status === 'fail') failing.push({ scenario: 'Spread', text: `The ghosted spread lesion would have occurred after ${c2}'s existing secondary lesion — primary must precede secondary.` })

  return (
    <div style={{ borderRadius: '6px', padding: '0.75rem 1rem', fontSize: '0.875rem', border: '1px solid #dde', background: '#f9f9fb' }}>
      <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Why?</p>
      {passing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#1d9e75', marginBottom: '0.25rem' }}>Supporting evidence — criteria that passed:</p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem', marginBottom: failing.length > 0 ? '0.75rem' : 0 }}>
            {passing.map((p, i) => (
              <li key={i} style={{ marginBottom: '0.35rem' }}><strong style={{ color: '#1d9e75' }}>[{p.scenario}]</strong>{' '}{p.text}</li>
            ))}
          </ul>
        </>
      )}
      {failing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#e24b4a', marginBottom: '0.25rem' }}>Limiting factors — criteria that failed:</p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {failing.map((f, i) => (
              <li key={i} style={{ marginBottom: '0.35rem' }}><strong style={{ color: '#c0392b' }}>[{f.scenario}]</strong>{' '}{f.text}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Single-pair results section
// ---------------------------------------------------------------------------

function Results({ result }: { result: GhostingAnalysisResult }) {
  const [logOpen, setLogOpen] = useState(false)
  const [scenarioTab, setScenarioTab] = useState<'source' | 'spread'>('source')
  const srcLesion = result.source_scenarios.range_lesions.expected
  const sprLesion = result.spread_scenarios.range_lesions.expected

  const activeScenario =
    scenarioTab === 'source' ? result.source_scenarios : result.spread_scenarios
  const activeGhostedLesion =
    scenarioTab === 'source' ? result.ghosted_source : result.ghosted_spread

  function buildHypothesis(tab: 'source' | 'spread'): string {
    if (tab === 'source') {
      return `This scenario tests whether ${result.case2_name} infected ${result.case1_name}.`
    }
    return `This scenario tests whether ${result.case1_name} infected ${result.case2_name}.`
  }

  return (
    <div className="stack-lg">
      <VerdictBanner verdict={result.verdict} />
      <VerdictContext result={result} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        <div className="panel stack-xs">
          <p className="eyebrow">Ghosted source onset</p>
          <p style={{ fontWeight: 700, fontSize: '1.05rem' }}>{srcLesion.onset}</p>
        </div>
        <div className="panel stack-xs">
          <p className="eyebrow">Ghosted source end</p>
          <p style={{ fontWeight: 700, fontSize: '1.05rem' }}>{srcLesion.end}</p>
        </div>
        <div className="panel stack-xs">
          <p className="eyebrow">Ghosted spread onset</p>
          <p style={{ fontWeight: 700, fontSize: '1.05rem' }}>{sprLesion.onset}</p>
        </div>
        <div className="panel stack-xs">
          <p className="eyebrow">Ghosted spread end</p>
          <p style={{ fontWeight: 700, fontSize: '1.05rem' }}>{sprLesion.end}</p>
        </div>
      </div>

      <div className="panel stack-xs">
        <p className="eyebrow">Anchor symptom</p>
        <p style={{ fontSize: '0.9rem' }}>
          <strong>{result.case1_name}</strong> ·{' '}
          {result.case1_symptom.type} · Onset {result.case1_symptom.onset}
          {result.case1_symptom.duration_days > 0
            ? ` · Duration ${result.case1_symptom.duration_days}d`
            : ''}
          {' · '}Avg inoculation date: <strong>{computeInoculationAvg(result.case1_symptom)}</strong>
        </p>
        <p style={{ fontSize: '0.85rem', color: '#888' }}>
          Comparison patient: {result.case2_name}
        </p>
      </div>

      <div className="panel stack-md">
        <nav className="tab-nav" aria-label="Scenario">
          <button
            type="button"
            className={scenarioTab === 'source' ? 'tab-link tab-link-active' : 'tab-link'}
            onClick={() => setScenarioTab('source')}
          >
            Source scenario
          </button>
          <button
            type="button"
            className={scenarioTab === 'spread' ? 'tab-link tab-link-active' : 'tab-link'}
            onClick={() => setScenarioTab('spread')}
          >
            Spread scenario
          </button>
        </nav>

        <div
          style={{
            background: '#f8f9fa',
            borderLeft: '3px solid #378add',
            padding: '0.75rem 1rem',
            fontSize: '0.875rem',
            borderRadius: '0 4px 4px 0',
          }}
        >
          <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>What this scenario tests</p>
          <p>{buildHypothesis(scenarioTab)}</p>
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
        <button
          type="button"
          className="button"
          onClick={() => setLogOpen(o => !o)}
          style={{ alignSelf: 'flex-start' }}
        >
          {logOpen ? '▲ Hide' : '▼ Show'} step-by-step log
        </button>
        {logOpen && (
          <pre style={{
            background: '#F4F2EC',
            padding: '0.75rem',
            borderRadius: '4px',
            fontSize: '0.8rem',
            lineHeight: 1.6,
            overflowX: 'auto',
            margin: 0,
          }}>
            {result.log.join('\n')}
          </pre>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Multi-pair results display
// ---------------------------------------------------------------------------

function MultiResults({ pairs }: { pairs: PairResult[] }) {
  const [openIdx, setOpenIdx] = useState<number>(0)

  return (
    <section className="stack-lg" style={{ marginTop: '1.5rem' }}>
      <div style={{ borderTop: '2px solid #E8E5DF', paddingTop: '1.5rem' }}>
        <p className="eyebrow">Analysis results</p>
      </div>
      {pairs.map((pair, i) => (
        <div key={i} className="panel stack-md">
          <button
            type="button"
            onClick={() => setOpenIdx(openIdx === i ? -1 : i)}
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
            }}
          >
            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{pair.label}</span>
            {pair.result && (
              <VerdictBanner verdict={pair.result.verdict} />
            )}
            <span style={{ fontSize: '0.8rem', color: '#888', marginLeft: '0.75rem' }}>
              {openIdx === i ? '▲' : '▼'}
            </span>
          </button>
          {openIdx === i && (
            <>
              {pair.error && (
                <p className="error-text">{pair.error}</p>
              )}
              {pair.result && <Results result={pair.result} />}
            </>
          )}
        </div>
      ))}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function QuickGhostPage() {
  const [pairResults, setPairResults] = useState<PairResult[]>([])
  const [apiError, setApiError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { register, control, handleSubmit, reset, getValues } = useForm<QuickGhostForm>({
    defaultValues: {
      person_a: { ...DEFAULT_PERSON, name: 'OP' },
      partners: [{ ...DEFAULT_PERSON, name: 'Partner 1' }],
    },
  })

  const { fields: partnerFields, append: appendPartner, remove: removePartner } = useFieldArray({
    control,
    name: 'partners',
  })

  // Run OP vs each partner independently
  async function runAllPairs(values: QuickGhostForm) {
    const results: PairResult[] = []
    for (let i = 0; i < values.partners.length; i++) {
      const partnerName = values.partners[i].name.trim() || `Partner ${i + 1}`
      const opName = values.person_a.name.trim() || 'OP'
      const label = `${opName} ↔ ${partnerName}`
      try {
        const res = await runQuickGhostingAnalysis(buildPayload(values.person_a, values.partners[i]))
        results.push({ label, result: res, error: null })
      } catch (err: unknown) {
        results.push({ label, result: null, error: err instanceof Error ? err.message : 'Analysis failed.' })
      }
    }
    return results
  }

  // Run chain: (OP, P1), (P1, P2), (P2, P3), …
  async function runChain(values: QuickGhostForm) {
    const all = [values.person_a, ...values.partners]
    const results: PairResult[] = []
    for (let i = 0; i < all.length - 1; i++) {
      const aName = all[i].name.trim() || (i === 0 ? 'OP' : `Partner ${i}`)
      const bName = all[i + 1].name.trim() || `Partner ${i + 1}`
      const label = `${aName} → ${bName}`
      try {
        const res = await runQuickGhostingAnalysis(buildPayload(all[i], all[i + 1]))
        results.push({ label, result: res, error: null })
      } catch (err: unknown) {
        results.push({ label, result: null, error: err instanceof Error ? err.message : 'Analysis failed.' })
      }
    }
    return results
  }

  async function onSubmit(values: QuickGhostForm) {
    setApiError(null)
    setPairResults([])
    setLoading(true)

    const aSymptoms = toSymptomInputs(values.person_a.symptoms)
    const allPartnerSymptoms = values.partners.flatMap(p => toSymptomInputs(p.symptoms))
    if (aSymptoms.length === 0 && allPartnerSymptoms.length === 0) {
      setApiError('At least one person must have a symptom entered.')
      setLoading(false)
      return
    }

    try {
      const results = await runAllPairs(values)
      setPairResults(results)
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : 'Analysis failed.')
    } finally {
      setLoading(false)
    }
  }

  async function handleChain() {
    setApiError(null)
    setPairResults([])
    setLoading(true)
    const values = getValues()

    const all = [values.person_a, ...values.partners]
    if (all.length < 2) {
      setApiError('Chain analysis requires at least 2 people (OP + 1 partner).')
      setLoading(false)
      return
    }

    try {
      const results = await runChain(values)
      setPairResults(results)
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : 'Chain analysis failed.')
    } finally {
      setLoading(false)
    }
  }

  function handleClear() {
    setPairResults([])
    setApiError(null)
    reset({
      person_a: { ...DEFAULT_PERSON, name: 'OP' },
      partners: [{ ...DEFAULT_PERSON, name: 'Partner 1' }],
    })
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem' }}>
      <div className="stack-lg">
        {/* Page header */}
        <header className="panel stack-sm">
          <div>
            <p className="eyebrow">Tools</p>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Quick Ghosting Analysis</h1>
          </div>
          <p style={{ color: '#555', fontSize: '0.9rem', maxWidth: 700 }}>
            Run the VCA ghosting engine on any group of people — no case required.
            Add partners, then use <strong>Run all pairs</strong> to compare OP against each partner,
            or <strong>Run chain</strong> to trace OP → P1 → P2 → … in sequence.
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

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Person A (OP) */}
          <PersonPanel
            prefix="person_a"
            label="Person A (OP)"
            control={control}
            register={register}
          />

          {/* Partners */}
          <div className="stack-md" style={{ marginTop: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <p className="eyebrow" style={{ margin: 0 }}>Partners</p>
              <button
                type="button"
                className="button button-primary"
                onClick={() =>
                  appendPartner({ ...DEFAULT_PERSON, name: `Partner ${partnerFields.length + 1}` })
                }
                style={{ fontSize: '0.85rem', padding: '4px 12px' }}
              >
                + Add partner
              </button>
            </div>

            {partnerFields.length === 0 && (
              <p style={{ color: '#888', fontSize: '0.875rem' }}>
                No partners yet — click Add partner to add one.
              </p>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: partnerFields.length > 1 ? '1fr 1fr' : '1fr', gap: '1.5rem' }}>
              {partnerFields.map((field, i) => (
                <PersonPanel
                  key={field.id}
                  prefix={`partners.${i}`}
                  label={`Partner ${i + 1}`}
                  control={control}
                  register={register}
                  onRemove={partnerFields.length > 1 ? () => removePartner(i) : undefined}
                />
              ))}
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className="button button-primary"
              type="submit"
              disabled={loading}
              style={{ minWidth: 160 }}
            >
              {loading ? 'Running…' : '▶ Run all pairs'}
            </button>
            <button
              type="button"
              className="button"
              onClick={handleChain}
              disabled={loading}
              style={{ minWidth: 140 }}
              title="Run chain: OP → P1 → P2 → … treating each person as the source for the next"
            >
              ⛓ Run chain
            </button>
            <button type="button" className="button" onClick={handleClear} disabled={loading}>
              Clear
            </button>
            {apiError && (
              <p className="error-text" style={{ margin: 0 }}>{apiError}</p>
            )}
          </div>
        </form>

        {/* Results */}
        {pairResults.length > 0 && <MultiResults pairs={pairResults} />}
      </div>
    </div>
  )
}
