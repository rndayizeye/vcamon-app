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

// A partner has their own clinical data plus a list of their own contacts,
// who are analyzed as: [this partner] vs [each contact].
type PartnerEntry = PersonFields & {
  contacts: PersonFields[]
}

type QuickGhostForm = {
  op: PersonFields
  partners: PartnerEntry[]
}

type PairResult = {
  label: string
  description: string
  result: GhostingAnalysisResult | null
  error: string | null
}

const EMPTY_SYMPTOM: SymptomRow = {
  type: SYMPTOM_TYPES[0],
  onset: '',
  duration_days: 0,
  anatomical_site: '',
}

const EMPTY_PERSON: PersonFields = {
  name: '',
  symptoms: [],
  exp_first: '',
  exp_last: '',
  body_parts: [],
  treatment_date: '',
}

const EMPTY_PARTNER: PartnerEntry = {
  ...EMPTY_PERSON,
  contacts: [],
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
  const opHasExposure = op.exp_first && op.exp_last
  const partnerHasExposure = partner.exp_first && partner.exp_last
  return {
    op_name: op.name.trim() || 'OP',
    op_symptoms: toSymptomInputs(op.symptoms),
    op_exposure: opHasExposure
      ? { first: op.exp_first, last: op.exp_last, exposure_modalities: [] }
      : null,
    op_treatment_date: op.treatment_date || null,
    op_body_parts: op.body_parts,
    partner_name: partner.name.trim() || 'Partner',
    partner_symptoms: toSymptomInputs(partner.symptoms),
    partner_exposure: partnerHasExposure
      ? { first: partner.exp_first, last: partner.exp_last, exposure_modalities: [] }
      : null,
    partner_treatment_date: partner.treatment_date || null,
    partner_body_parts: partner.body_parts,
  }
}

async function runPair(
  op: PersonFields,
  partner: PersonFields,
  label: string,
  description: string,
): Promise<PairResult> {
  try {
    const result = await runQuickGhostingAnalysis(buildPayload(op, partner))
    return { label, description, result, error: null }
  } catch (err: unknown) {
    return { label, description, result: null, error: err instanceof Error ? err.message : 'Analysis failed.' }
  }
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
            style={{ padding: '6px 10px', flex: '0 0 auto', alignSelf: 'flex-end' }} title="Remove symptom">
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
// Person clinical data fields (reused for OP, partners, and contacts)
// ---------------------------------------------------------------------------

function PersonClinicalFields({
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
// Contact card — compact sub-panel used inside a partner's contacts section
// ---------------------------------------------------------------------------

function ContactCard({
  prefix,
  index,
  control,
  register,
  onRemove,
}: {
  prefix: string
  index: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
  onRemove: () => void
}) {
  const [open, setOpen] = useState(true)

  return (
    <div style={{
      border: '1px solid #d8d3cb',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.5rem 0.75rem',
        background: '#f4f2ec',
        borderBottom: open ? '1px solid #d8d3cb' : 'none',
      }}>
        <button type="button" onClick={() => setOpen(o => !o)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: '0.8rem', color: '#666' }}>
          {open ? '▼' : '▶'}
        </button>
        <label className="field" style={{ margin: 0, flex: 1 }}>
          <input type="text" {...register(`${prefix}.name`)}
            placeholder={`Contact ${index + 1}`}
            style={{ fontSize: '0.85rem', padding: '3px 6px' }} />
        </label>
        <button type="button" className="button" onClick={onRemove}
          style={{ padding: '3px 8px', fontSize: '0.8rem' }}>
          Remove
        </button>
      </div>
      {open && (
        <div className="stack-md" style={{ padding: '0.75rem' }}>
          <PersonClinicalFields prefix={prefix} control={control} register={register} />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Partner panel — includes their own contacts sub-section
// ---------------------------------------------------------------------------

function PartnerPanel({
  partnerIdx,
  control,
  register,
  onRemove,
}: {
  partnerIdx: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
  onRemove?: () => void
}) {
  const prefix = `partners.${partnerIdx}`
  const [contactsOpen, setContactsOpen] = useState(false)

  const { fields: contactFields, append: appendContact, remove: removeContact } = useFieldArray({
    control,
    name: `${prefix}.contacts`,
  })

  return (
    <div className="panel stack-md">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <p className="eyebrow">Partner {partnerIdx + 1}</p>
          <label className="field" style={{ marginTop: '0.5rem' }}>
            <span>Name / identifier</span>
            <input type="text" {...register(`${prefix}.name`)} placeholder={`Partner ${partnerIdx + 1}`} />
          </label>
        </div>
        {onRemove && (
          <button type="button" className="button" onClick={onRemove}
            style={{ marginLeft: '0.75rem', padding: '4px 10px', fontSize: '0.8rem' }}>
            Remove
          </button>
        )}
      </div>

      {/* Clinical data */}
      <PersonClinicalFields prefix={prefix} control={control} register={register} />

      {/* This partner's contacts — the next level of the transmission network */}
      <div style={{
        borderTop: '1px solid #e0dbd2',
        paddingTop: '0.75rem',
        marginTop: '0.25rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: contactsOpen || contactFields.length > 0 ? '0.75rem' : 0 }}>
          <button
            type="button"
            onClick={() => setContactsOpen(o => !o)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: '0.8rem', color: '#555', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            {contactsOpen || contactFields.length > 0 ? '▼' : '▶'}
            <span style={{ fontWeight: 500, fontSize: '0.8rem' }}>
              This partner's contacts
              {contactFields.length > 0 && (
                <span style={{ color: '#888', fontWeight: 400 }}> ({contactFields.length})</span>
              )}
            </span>
          </button>
          <span style={{ fontSize: '0.75rem', color: '#888' }}>
            — analyzed as: [this partner] vs [each contact]
          </span>
        </div>

        {(contactsOpen || contactFields.length > 0) && (
          <div className="stack-sm">
            {contactFields.length === 0 && (
              <p style={{ fontSize: '0.82rem', color: '#999', margin: 0 }}>
                No contacts entered for this partner yet.
              </p>
            )}
            {contactFields.map((field, ci) => (
              <ContactCard
                key={field.id}
                prefix={`${prefix}.contacts.${ci}`}
                index={ci}
                control={control}
                register={register}
                onRemove={() => removeContact(ci)}
              />
            ))}
            <button
              type="button"
              className="button"
              style={{ alignSelf: 'flex-start', fontSize: '0.82rem' }}
              onClick={() => {
                setContactsOpen(true)
                appendContact({ ...EMPTY_PERSON })
              }}
            >
              + Add contact for this partner
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Verdict / criteria display components
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
  const upper = verdict.toUpperCase()
  let color = '#e24b4a'
  let bg = '#fdf0f0'
  let border = '#e24b4a'
  if (upper.includes('UNRELATED')) { color = '#e24b4a'; bg = '#fdf0f0'; border = '#e24b4a' }
  else if (upper.includes('AMBIGUOUS')) { color = '#8a6d00'; bg = '#fef8ec'; border = '#ef9f27' }
  else if (upper.includes('⚠') || upper.includes('OVERLAP')) { color = '#8a6d00'; bg = '#fef8ec'; border = '#ef9f27' }
  else if (upper.includes('SOURCE')) { color = '#1d9e75'; bg = '#eafaf3'; border = '#1d9e75' }
  else if (upper.includes('SPREAD')) { color = '#378add'; bg = '#e8f3fd'; border = '#378add' }

  if (compact) {
    return (
      <span style={{
        padding: '2px 10px', borderRadius: '4px', background: bg, border: `1px solid ${border}`,
        color, fontSize: '0.8rem', fontWeight: 700, whiteSpace: 'nowrap',
      }}>
        {verdict}
      </span>
    )
  }

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
              <li key={i} style={{ marginBottom: '0.35rem' }}>
                <strong style={{ color: '#1d9e75' }}>[{p.scenario}]</strong>{' '}{p.text}
              </li>
            ))}
          </ul>
        </>
      )}
      {failing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#e24b4a', marginBottom: '0.25rem' }}>Limiting factors — criteria that failed:</p>
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

// ---------------------------------------------------------------------------
// Single-pair results
// ---------------------------------------------------------------------------

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
          <strong>{result.case1_name}</strong> · {result.case1_symptom.type} · Onset {result.case1_symptom.onset}
          {result.case1_symptom.duration_days > 0 ? ` · Duration ${result.case1_symptom.duration_days}d` : ''}
          {' · '}Avg inoculation date: <strong>{computeInoculationAvg(result.case1_symptom)}</strong>
        </p>
        <p style={{ fontSize: '0.85rem', color: '#888' }}>Comparison patient: {result.case2_name}</p>
      </div>

      <div className="panel stack-md">
        <nav className="tab-nav" aria-label="Scenario">
          <button type="button"
            className={scenarioTab === 'source' ? 'tab-link tab-link-active' : 'tab-link'}
            onClick={() => setScenarioTab('source')}>
            Source scenario
          </button>
          <button type="button"
            className={scenarioTab === 'spread' ? 'tab-link tab-link-active' : 'tab-link'}
            onClick={() => setScenarioTab('spread')}>
            Spread scenario
          </button>
        </nav>
        <div style={{ background: '#f8f9fa', borderLeft: '3px solid #378add', padding: '0.75rem 1rem', fontSize: '0.875rem', borderRadius: '0 4px 4px 0' }}>
          <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>What this scenario tests</p>
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
// Results: grouped by transmission level
// ---------------------------------------------------------------------------

type ResultGroup = {
  heading: string
  subheading: string
  pairs: PairResult[]
}

function ResultsSection({ groups }: { groups: ResultGroup[] }) {
  const [openPairs, setOpenPairs] = useState<Record<string, boolean>>({})
  const toggle = (key: string) => setOpenPairs(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <section className="stack-lg" style={{ marginTop: '1.5rem' }}>
      <div style={{ borderTop: '2px solid #E8E5DF', paddingTop: '1.5rem' }}>
        <p className="eyebrow">Transmission network — analysis results</p>
      </div>

      {groups.map((group, gi) => (
        <div key={gi} className="stack-md">
          <div>
            <p style={{ fontWeight: 700, fontSize: '1rem', margin: 0 }}>{group.heading}</p>
            <p style={{ fontSize: '0.82rem', color: '#777', margin: '2px 0 0' }}>{group.subheading}</p>
          </div>

          {group.pairs.map((pair, pi) => {
            const key = `${gi}-${pi}`
            const isOpen = !!openPairs[key]
            return (
              <div key={pi} className="panel stack-sm" style={{ padding: '0.75rem 1rem' }}>
                <button
                  type="button"
                  onClick={() => toggle(key)}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    background: 'none', border: 'none', padding: 0, cursor: 'pointer', width: '100%', textAlign: 'left', gap: '1rem',
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{pair.label}</span>
                    <span style={{ fontSize: '0.8rem', color: '#888', marginLeft: '0.5rem' }}>{pair.description}</span>
                  </div>
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
        </div>
      ))}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function QuickGhostPage() {
  const [resultGroups, setResultGroups] = useState<ResultGroup[]>([])
  const [apiError, setApiError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { register, control, handleSubmit, reset } = useForm<QuickGhostForm>({
    defaultValues: {
      op: { ...EMPTY_PERSON, name: 'OP' },
      partners: [{ ...EMPTY_PARTNER, name: 'Partner 1' }],
    },
  })

  const { fields: partnerFields, append: appendPartner, remove: removePartner } = useFieldArray({
    control,
    name: 'partners',
  })

  // Run OP vs all partners — answers "who is the OP's source / who did OP infect?"
  async function runAllPairs(values: QuickGhostForm): Promise<ResultGroup[]> {
    const opName = values.op.name.trim() || 'OP'

    // Level 1: OP vs each partner
    const level1Pairs: PairResult[] = []
    for (let i = 0; i < values.partners.length; i++) {
      const p = values.partners[i]
      const pName = p.name.trim() || `Partner ${i + 1}`
      level1Pairs.push(
        await runPair(
          values.op,
          p,
          `${opName} ↔ ${pName}`,
          `Did ${pName} infect ${opName}, or did ${opName} infect ${pName}?`,
        )
      )
    }

    // Level 2: each partner vs their own contacts
    const level2Groups: ResultGroup[] = []
    for (let i = 0; i < values.partners.length; i++) {
      const p = values.partners[i]
      const pName = p.name.trim() || `Partner ${i + 1}`
      if (!p.contacts || p.contacts.length === 0) continue

      const pairs: PairResult[] = []
      for (let ci = 0; ci < p.contacts.length; ci++) {
        const contact = p.contacts[ci]
        const cName = contact.name.trim() || `Contact ${ci + 1}`
        pairs.push(
          await runPair(
            p,
            contact,
            `${pName} ↔ ${cName}`,
            `Did ${cName} infect ${pName}, or did ${pName} infect ${cName}?`,
          )
        )
      }

      if (pairs.length > 0) {
        level2Groups.push({
          heading: `${pName}'s transmission network`,
          subheading: `${pName} analyzed as OP against their own contacts`,
          pairs,
        })
      }
    }

    const groups: ResultGroup[] = [
      {
        heading: `${opName}'s partners`,
        subheading: `Source/spread analysis for ${opName} against each partner`,
        pairs: level1Pairs,
      },
      ...level2Groups,
    ]

    return groups
  }

  async function onSubmit(values: QuickGhostForm) {
    setApiError(null)
    setResultGroups([])
    setLoading(true)

    const opSymptoms = toSymptomInputs(values.op.symptoms)
    const allPartnerSymptoms = values.partners.flatMap(p => [
      ...toSymptomInputs(p.symptoms),
      ...(p.contacts ?? []).flatMap(c => toSymptomInputs(c.symptoms)),
    ])

    if (opSymptoms.length === 0 && allPartnerSymptoms.length === 0) {
      setApiError('At least one person must have a symptom entered.')
      setLoading(false)
      return
    }

    try {
      const groups = await runAllPairs(values)
      setResultGroups(groups)
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : 'Analysis failed.')
    } finally {
      setLoading(false)
    }
  }

  function handleClear() {
    setResultGroups([])
    setApiError(null)
    reset({
      op: { ...EMPTY_PERSON, name: 'OP' },
      partners: [{ ...EMPTY_PARTNER, name: 'Partner 1' }],
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
          <p style={{ color: '#555', fontSize: '0.9rem', maxWidth: 720 }}>
            Enter the OP and all their partners. For any partner who is also infected, expand
            their <strong>contacts</strong> section to enter their own network — those pairs are
            analyzed as [that partner] vs [their contact], building the full transmission network.
            Click <strong>Run network analysis</strong> to run all pairs at once.
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
          {/* OP */}
          <div className="panel stack-md">
            <div>
              <p className="eyebrow">Index patient (OP)</p>
              <label className="field" style={{ marginTop: '0.5rem' }}>
                <span>Name / identifier</span>
                <input type="text" {...register('op.name')} placeholder="OP" />
              </label>
            </div>
            <PersonClinicalFields prefix="op" control={control} register={register} />
          </div>

          {/* Partners */}
          <div className="stack-md" style={{ marginTop: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <p className="eyebrow" style={{ margin: 0 }}>OP's partners</p>
              <button
                type="button"
                className="button button-primary"
                onClick={() => appendPartner({
                  ...EMPTY_PARTNER,
                  name: `Partner ${partnerFields.length + 1}`,
                })}
                style={{ fontSize: '0.85rem', padding: '4px 12px' }}
              >
                + Add partner
              </button>
            </div>

            {partnerFields.length === 0 && (
              <p style={{ color: '#888', fontSize: '0.875rem' }}>
                No partners yet — click Add partner.
              </p>
            )}

            <div style={{
              display: 'grid',
              gridTemplateColumns: partnerFields.length > 1 ? '1fr 1fr' : '1fr',
              gap: '1.5rem',
            }}>
              {partnerFields.map((field, i) => (
                <PartnerPanel
                  key={field.id}
                  partnerIdx={i}
                  control={control}
                  register={register}
                  onRemove={partnerFields.length > 1 ? () => removePartner(i) : undefined}
                />
              ))}
            </div>
          </div>

          {/* How the analysis works callout */}
          {partnerFields.length > 0 && (
            <div style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              background: '#f4f2ec',
              borderRadius: '6px',
              fontSize: '0.82rem',
              color: '#555',
            }}>
              <strong>What will be analyzed:</strong>{' '}
              OP vs each of the {partnerFields.length} partner{partnerFields.length > 1 ? 's' : ''} above.
              Partners that have contacts entered will also be analyzed against each of their contacts
              (as the OP in those sub-analyses), growing the network.
            </div>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className="button button-primary"
              type="submit"
              disabled={loading}
              style={{ minWidth: 200 }}
            >
              {loading ? 'Running…' : '▶ Run network analysis'}
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
        {resultGroups.length > 0 && <ResultsSection groups={resultGroups} />}
      </div>
    </div>
  )
}
