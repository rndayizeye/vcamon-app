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
  person_b: PersonFields
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

// ---------------------------------------------------------------------------
// Symptom editor sub-component  (flex-wrap fixes the overlap bug)
// ---------------------------------------------------------------------------

function SymptomEditor({
  prefix,
  control,
  register,
}: {
  prefix: 'person_a' | 'person_b'
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
// Body parts checkboxes (penis / vagina / anus / mouth — matches RelationshipEditor)
// ---------------------------------------------------------------------------

function BodyPartsCheckboxes({
  prefix,
  register,
}: {
  prefix: 'person_a' | 'person_b'
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
        {/* Exposure */}
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

        {/* Exposure modality */}
        <tr>
          <td style={{ fontWeight: 500 }}>Exposure modality</td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td><StatusBadge check={expected.exposure_modality} /></td>
          <td style={tdMuted}>{expected.exposure_modality.detail}</td>
        </tr>

        {/* Latency — 3 rows */}
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

        {/* Natural order */}
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
  const cls = verdict.includes('SOURCE') && !verdict.includes('UNRELATED') && !verdict.includes('AMBIGUOUS')
    ? 'badge badge-pass'
    : verdict.includes('SPREAD') && !verdict.includes('UNRELATED')
      ? 'badge badge-pass'
      : verdict.includes('AMBIGUOUS')
        ? 'badge badge-warn'
        : 'badge badge-fail'

  return (
    <div style={{ padding: '1rem', borderRadius: '6px', background: 'rgba(0,0,0,0.03)', border: '1px solid #ddd' }}>
      <p className="eyebrow">Verdict</p>
      <p style={{ fontSize: '1.2rem', fontWeight: 700, marginTop: '0.25rem' }}>
        <span className={cls}>{verdict}</span>
      </p>
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

  type Explanation = { scenario: string; text: string }
  const failures: Explanation[] = []

  if (srcExpected.exposure.status === 'fail') {
    failures.push({
      scenario: 'Source',
      text: `${c1} was likely not infected by ${c2} because the exposure window does not overlap with ${c2}'s ghosted source lesion (${srcLesion.onset} → ${srcLesion.end}). ${c2} would not have been infectious during the recorded contact.`,
    })
  }
  if (srcExpected.exposure_modality.status === 'fail') {
    failures.push({
      scenario: 'Source',
      text: `The type of sexual contact is not compatible with the site of ${c1}'s ${result.case1_symptom.type}. Transmission requires contact with the infected anatomical site.`,
    })
  }
  if (srcExpected.latency.status === 'fail') {
    failures.push({
      scenario: 'Source',
      text: `The timeline between ${c2}'s ghosted source lesion and their secondary symptoms does not fit natural syphilis progression. ${srcExpected.latency.detail}`,
    })
  }
  if (srcExpected.natural_order.status === 'fail') {
    failures.push({
      scenario: 'Source',
      text: `The ghosted source lesion would have occurred after ${c2}'s existing secondary lesion — primary must precede secondary. ${srcExpected.natural_order.detail}`,
    })
  }

  if (sprExpected.exposure.status === 'fail') {
    failures.push({
      scenario: 'Spread',
      text: `${c2} was likely not infected by ${c1} because the exposure window does not overlap with ${c1}'s infectious period (${sprLesion.onset} → ${sprLesion.end}).`,
    })
  }
  if (sprExpected.exposure_modality.status === 'fail') {
    failures.push({
      scenario: 'Spread',
      text: `The type of sexual contact is not compatible with the site of ${c1}'s ${result.case1_symptom.type}. ${sprExpected.exposure_modality.detail}`,
    })
  }
  if (sprExpected.latency.status === 'fail') {
    failures.push({
      scenario: 'Spread',
      text: `The time between ${c1}'s infectious period and ${c2}'s secondary symptoms does not fit natural syphilis progression. ${sprExpected.latency.detail}`,
    })
  }
  if (sprExpected.natural_order.status === 'fail') {
    failures.push({
      scenario: 'Spread',
      text: `The ghosted spread lesion would have occurred after ${c2}'s existing secondary lesion — primary must precede secondary. ${sprExpected.natural_order.detail}`,
    })
  }

  if (failures.length === 0) {
    return (
      <div style={{ background: '#eafaf3', borderRadius: '6px', padding: '0.75rem 1rem', fontSize: '0.875rem', border: '1px solid #1d9e75' }}>
        <p className="eyebrow">Why this verdict?</p>
        <p style={{ color: '#1d9e75', marginTop: '0.25rem' }}>
          All key criteria passed — the verdict is well-supported by the clinical data entered.
        </p>
      </div>
    )
  }

  return (
    <div style={{ background: '#fdf0f0', borderRadius: '6px', padding: '0.75rem 1rem', fontSize: '0.875rem', border: '1px solid #e24b4a' }}>
      <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Why this verdict? — criteria that failed</p>
      <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
        {failures.map((f, i) => (
          <li key={i} style={{ marginBottom: '0.5rem' }}>
            <strong style={{ color: '#c0392b' }}>[{f.scenario}]</strong>{' '}{f.text}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Results section
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
    const srcAssigned = result.ghosted_source.assigned_to
    const sprAssigned = result.ghosted_spread.assigned_to
    if (tab === 'source') {
      return `Hypothesis: ${srcAssigned} infected ${result.case1_name}. ` +
        `This scenario back-calculates when ${srcAssigned} would have had an active primary chancre ` +
        `(ghosted source lesion: ${result.ghosted_source.onset} → ${result.ghosted_source.end}) ` +
        `that could have been transmitted to ${result.case1_name} during the exposure window. ` +
        `For this to hold, the exposure must overlap with that infectious window, ` +
        `and ${result.case1_name}'s back-calculated inoculation date must fall within it.`
    }
    return `Hypothesis: ${result.case1_name} infected ${sprAssigned}. ` +
      `This scenario calculates when ${result.case1_name} would have been contagious ` +
      `(ghosted spread lesion: ${result.ghosted_spread.onset} → ${result.ghosted_spread.end}) ` +
      `and whether that infectious period overlaps with the reported contact with ${sprAssigned}.`
  }

  return (
    <section className="stack-lg" style={{ marginTop: '1.5rem' }}>
      <div style={{ borderTop: '2px solid #E8E5DF', paddingTop: '1.5rem' }}>
        <p className="eyebrow">Analysis results</p>
      </div>

      <VerdictBanner verdict={result.verdict} />
      <VerdictContext result={result} />

      {/* Ghosted date metrics */}
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

      {/* Case1 anchor info */}
      <div className="panel stack-xs">
        <p className="eyebrow">Analysis roles</p>
        <p style={{ fontSize: '0.9rem' }}>
          <strong>Case 1 (anchor):</strong> {result.case1_name} &nbsp;·&nbsp;
          <strong>Case 2:</strong> {result.case2_name}
        </p>
        <p style={{ fontSize: '0.85rem', color: '#666' }}>
          Anchor symptom: {result.case1_symptom.type} — onset {result.case1_symptom.onset} ·
          avg inoculation date: <strong>{computeInoculationAvg(result.case1_symptom)}</strong>
        </p>
      </div>

      {/* Scenario criteria */}
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

        {/* Hypothesis */}
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

      {/* Step-by-step log */}
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
    </section>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function QuickGhostPage() {
  const [result, setResult] = useState<GhostingAnalysisResult | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { register, control, handleSubmit, reset } = useForm<QuickGhostForm>({
    defaultValues: {
      person_a: { ...DEFAULT_PERSON, name: 'OP' },
      person_b: { ...DEFAULT_PERSON, name: 'Partner' },
    },
  })

  async function onSubmit(values: QuickGhostForm) {
    setApiError(null)
    setResult(null)
    setLoading(true)

    const aSymptoms = toSymptomInputs(values.person_a.symptoms)
    const bSymptoms = toSymptomInputs(values.person_b.symptoms)

    if (aSymptoms.length === 0 && bSymptoms.length === 0) {
      setApiError('At least one person must have a symptom entered.')
      setLoading(false)
      return
    }

    const aHasExposure = values.person_a.exp_first && values.person_a.exp_last
    const bHasExposure = values.person_b.exp_first && values.person_b.exp_last

    try {
      const res = await runQuickGhostingAnalysis({
        op_name: values.person_a.name.trim() || 'Person A',
        op_symptoms: aSymptoms,
        op_exposure: aHasExposure
          ? { first: values.person_a.exp_first, last: values.person_a.exp_last, exposure_modalities: [] }
          : null,
        op_treatment_date: values.person_a.treatment_date || null,
        op_body_parts: values.person_a.body_parts,
        partner_name: values.person_b.name.trim() || 'Person B',
        partner_symptoms: bSymptoms,
        partner_exposure: bHasExposure
          ? { first: values.person_b.exp_first, last: values.person_b.exp_last, exposure_modalities: [] }
          : null,
        partner_treatment_date: values.person_b.treatment_date || null,
        partner_body_parts: values.person_b.body_parts,
      })
      setResult(res)
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : 'Analysis failed.')
    } finally {
      setLoading(false)
    }
  }

  function handleClear() {
    setResult(null)
    setApiError(null)
    reset({
      person_a: { ...DEFAULT_PERSON, name: 'OP' },
      person_b: { ...DEFAULT_PERSON, name: 'Partner' },
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
          <p style={{ color: '#555', fontSize: '0.9rem', maxWidth: 620 }}>
            Run the VCA ghosting engine on any two people — no case required.
            Enter dates and symptoms, then click Run.
          </p>

          {/* Clinical reference */}
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
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            {/* Person A */}
            <div className="panel stack-md">
              <div>
                <p className="eyebrow">Person A</p>
                <label className="field" style={{ marginTop: '0.5rem' }}>
                  <span>Name / identifier</span>
                  <input type="text" {...register('person_a.name')} placeholder="OP" />
                </label>
              </div>

              <SymptomEditor prefix="person_a" control={control} register={register} />

              <div className="stack-sm">
                <p className="eyebrow">Exposure window</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <label className="field">
                    <span>First exposure</span>
                    <input type="date" {...register('person_a.exp_first')} />
                  </label>
                  <label className="field">
                    <span>Last exposure</span>
                    <input type="date" {...register('person_a.exp_last')} />
                  </label>
                </div>
                <BodyPartsCheckboxes prefix="person_a" register={register} />
              </div>

              <label className="field">
                <span>Treatment date</span>
                <input type="date" {...register('person_a.treatment_date')} />
              </label>
            </div>

            {/* Person B */}
            <div className="panel stack-md">
              <div>
                <p className="eyebrow">Person B</p>
                <label className="field" style={{ marginTop: '0.5rem' }}>
                  <span>Name / identifier</span>
                  <input type="text" {...register('person_b.name')} placeholder="Partner" />
                </label>
              </div>

              <SymptomEditor prefix="person_b" control={control} register={register} />

              <div className="stack-sm">
                <p className="eyebrow">Exposure window</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <label className="field">
                    <span>First exposure</span>
                    <input type="date" {...register('person_b.exp_first')} />
                  </label>
                  <label className="field">
                    <span>Last exposure</span>
                    <input type="date" {...register('person_b.exp_last')} />
                  </label>
                </div>
                <BodyPartsCheckboxes prefix="person_b" register={register} />
              </div>

              <label className="field">
                <span>Treatment date</span>
                <input type="date" {...register('person_b.treatment_date')} />
              </label>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className="button button-primary"
              type="submit"
              disabled={loading}
              style={{ minWidth: 140 }}
            >
              {loading ? 'Running…' : '▶ Run analysis'}
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
        {result && <Results result={result} />}
      </div>
    </div>
  )
}
