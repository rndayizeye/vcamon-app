import { useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'

import { runQuickGhostingAnalysis } from './api'
import type {
  GhostingAnalysisResult,
  GhostingCriteriaCheck,
  GhostingScenarioCriteria,
  GhostingSymptomInput,
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

const SEX_TYPES = ['Anal LX', 'Oral LX', 'Vaginal LX', 'Penile LX', 'Rectal LX']

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
  sex_types: string[]
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
  sex_types: [],
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

// ---------------------------------------------------------------------------
// Symptom editor sub-component
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
        <p style={{ color: '#888', fontSize: '0.85rem', margin: 0 }}>No symptoms — click Add to enter one.</p>
      )}
      {fields.map((field, i) => (
        <div
          key={field.id}
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 120px 80px 1fr auto',
            gap: '0.5rem',
            alignItems: 'end',
          }}
        >
          <label className="field" style={{ margin: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Type</span>}
            <select {...register(`${prefix}.symptoms.${i}.type`)}>
              {SYMPTOM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="field" style={{ margin: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Onset date</span>}
            <input type="date" {...register(`${prefix}.symptoms.${i}.onset`)} />
          </label>
          <label className="field" style={{ margin: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Duration (d)</span>}
            <input type="number" min={0} max={90} {...register(`${prefix}.symptoms.${i}.duration_days`, { valueAsNumber: true })} />
          </label>
          <label className="field" style={{ margin: 0 }}>
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
            style={{ padding: '6px 10px', alignSelf: 'flex-end' }}
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
// Sex-type checkboxes
// ---------------------------------------------------------------------------

function SexTypeCheckboxes({
  prefix,
  register,
}: {
  prefix: 'person_a' | 'person_b'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
}) {
  return (
    <div className="stack-xs">
      <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>Sex type(s)</p>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {SEX_TYPES.map(st => (
          <label key={st} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              value={st}
              {...register(`${prefix}.sex_types`)}
            />
            {st.replace(' LX', '')}
          </label>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Verdict banner
// ---------------------------------------------------------------------------

function verdictClass(verdict: string): string {
  if (verdict.includes('SOURCE') && !verdict.includes('UNRELATED') && !verdict.includes('AMBIGUOUS')) return 'badge badge-pass'
  if (verdict.includes('SPREAD') && !verdict.includes('UNRELATED')) return 'badge badge-pass'
  if (verdict.includes('AMBIGUOUS')) return 'badge badge-warn'
  return 'badge badge-fail'
}

function VerdictBanner({ verdict }: { verdict: string }) {
  const cls = verdictClass(verdict)

  return (
    <div style={{ padding: '1rem', borderRadius: '6px', background: 'rgba(0,0,0,0.03)', border: '1px solid #ddd' }}>
      <p className="eyebrow">Verdict</p>
      <p style={{ fontSize: '1.2rem', fontWeight: 700, marginTop: '0.25rem' }}>
        <span className={cls}>{verdict}</span>
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Criteria table
// ---------------------------------------------------------------------------

function CriteriaRow({ name, check }: { name: string; check: GhostingCriteriaCheck }) {
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
    <tr>
      <td style={{ fontWeight: 500 }}>{name}</td>
      <td><span className={styles[check.status] ?? 'badge'}>{labels[check.status] ?? check.status}</span></td>
      <td style={{ color: '#555', fontSize: '0.85rem' }}>{check.detail}</td>
    </tr>
  )
}

function CriteriaTable({ label, criteria }: { label: string; criteria: GhostingScenarioCriteria }) {
  return (
    <div className="stack-sm">
      <p className="eyebrow">{label}</p>
      <table className="data-table">
        <thead>
          <tr>
            <th>Criterion</th>
            <th>Result</th>
            <th>Detail</th>
          </tr>
        </thead>
        <tbody>
          <CriteriaRow name="Exposure" check={criteria.exposure} />
          <CriteriaRow name="Exposure modality" check={criteria.exposure_modality} />
          <CriteriaRow name="Latency" check={criteria.latency} />
          <CriteriaRow name="Natural order" check={criteria.natural_order} />
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Results section
// ---------------------------------------------------------------------------

function Results({ result }: { result: GhostingAnalysisResult }) {
  const [logOpen, setLogOpen] = useState(false)
  const [scenarioTab, setScenarioTab] = useState<'source' | 'spread'>('source')
  const srcExpected = result.source_scenarios.range_data.expected
  const sprExpected = result.spread_scenarios.range_data.expected
  const srcLesion = result.source_scenarios.range_lesions.expected
  const sprLesion = result.spread_scenarios.range_lesions.expected

  return (
    <section className="stack-lg" style={{ marginTop: '1.5rem' }}>
      <div style={{ borderTop: '2px solid #E8E5DF', paddingTop: '1.5rem' }}>
        <p className="eyebrow">Analysis results</p>
      </div>

      <VerdictBanner verdict={result.verdict} />

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

      {/* Case1/Case2 labels */}
      <div className="panel stack-xs">
        <p className="eyebrow">Analysis roles</p>
        <p style={{ fontSize: '0.9rem' }}>
          <strong>Case 1 (anchor):</strong> {result.case1_name} &nbsp;·&nbsp;
          <strong>Case 2:</strong> {result.case2_name}
        </p>
        <p style={{ fontSize: '0.85rem', color: '#666' }}>
          Anchor symptom: {result.case1_symptom.type} — onset {result.case1_symptom.onset}
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

        {scenarioTab === 'source' && (
          <div className="stack-sm">
            <CriteriaTable label="Expected range — source" criteria={srcExpected} />
            <p style={{ fontSize: '0.82rem', color: '#555' }}>
              Confidence: <strong>{result.source_scenarios.confidence}</strong> &nbsp;·&nbsp;
              Pass count: {result.source_scenarios.pass_count}
            </p>
          </div>
        )}
        {scenarioTab === 'spread' && (
          <div className="stack-sm">
            <CriteriaTable label="Expected range — spread" criteria={sprExpected} />
            <p style={{ fontSize: '0.82rem', color: '#555' }}>
              Confidence: <strong>{result.spread_scenarios.confidence}</strong> &nbsp;·&nbsp;
              Pass count: {result.spread_scenarios.pass_count}
            </p>
          </div>
        )}
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
          ? {
              first: values.person_a.exp_first,
              last: values.person_a.exp_last,
              exposure_modalities: values.person_a.sex_types,
            }
          : null,
        op_treatment_date: values.person_a.treatment_date || null,
        partner_name: values.person_b.name.trim() || 'Person B',
        partner_symptoms: bSymptoms,
        partner_exposure: bHasExposure
          ? {
              first: values.person_b.exp_first,
              last: values.person_b.exp_last,
              exposure_modalities: values.person_b.sex_types,
            }
          : null,
        partner_treatment_date: values.person_b.treatment_date || null,
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
                <p className="eyebrow">Exposure window (A's account of contact with B)</p>
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
                <SexTypeCheckboxes prefix="person_a" register={register} />
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
                <p className="eyebrow">Exposure window (B's account of contact with A)</p>
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
                <SexTypeCheckboxes prefix="person_b" register={register} />
              </div>

              <label className="field">
                <span>Treatment date</span>
                <input type="date" {...register('person_b.treatment_date')} />
              </label>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem', alignItems: 'center' }}>
            <button
              className="button button-primary"
              type="submit"
              disabled={loading}
              style={{ minWidth: 140 }}
            >
              {loading ? 'Running…' : '▶ Run analysis'}
            </button>
            <button
              type="button"
              className="button"
              onClick={handleClear}
              disabled={loading}
            >
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
