import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
import { GlossaryPanel } from '../../components/GlossaryPanel'
import { useCase } from '../cases/hooks'
import { getPartnersForCase } from '../partners/api'
import { useQuery } from '@tanstack/react-query'
import type {
  GhostingAnalysisResult,
  GhostingScenarioCriteria,
  GhostingCriteriaCheck,
  GhostingRecord,
  GhostedLesion,
  GhostingSymptomInput,
  PartnerSummary,
} from './types'
import {
  useCaseGhostings,
  useCreateGhosting,
  useDeleteGhosting,
  useRunGhostingAnalysis,
} from './hooks'

// ---------------------------------------------------------------------------
// Clinical reference table data
// ---------------------------------------------------------------------------

const CLINICAL_REF = [
  { phase: 'Incubation', min: '10d', avg: '21d', max: '90d' },
  { phase: 'Primary chancre', min: '7d', avg: '21d', max: '35d' },
  { phase: 'Latency', min: '0d', avg: '28d', max: '70d' },
  { phase: 'Secondary', min: '14d', avg: '28d', max: '42d' },
]

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

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
// Sub-components
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

/**
 * Criteria table with:
 * - Latency shown in 3 rows (optimistic / expected / conservative range)
 * - All other criteria shown once (expected range only)
 * - Sub-row under exposure showing whether the likely inoculation date falls
 *   within the ghosted lesion window
 */
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
  const tdMuted: React.CSSProperties = { fontSize: '0.875rem', color: 'var(--color-text-muted, #666)' }

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
        {/* Exposure — expected range + inoculation sub-row */}
        <tr>
          <td rowSpan={2} style={{ fontWeight: 500, verticalAlign: 'middle' }}>
            Exposure
          </td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td><StatusBadge check={expected.exposure} /></td>
          <td style={tdMuted}>{expected.exposure.detail}</td>
        </tr>
        <tr style={{ background: 'rgba(0,0,0,0.02)' }}>
          <td style={{ fontSize: '0.78rem', color: '#888', paddingLeft: '1rem' }}>
            ↳ Inoculation date
          </td>
          <td>
            <span className={inocInWindow ? 'badge badge-pass' : 'badge badge-fail'}>
              {inocInWindow ? '✓ In window' : '✗ Outside'}
            </span>
          </td>
          <td style={{ fontSize: '0.78rem', color: '#666' }}>
            {case1Name}'s avg inoculation date ({inocAvg}) —{' '}
            {inocInWindow
              ? `falls within ghosted lesion (${ghostedLesion.onset} → ${ghostedLesion.end})`
              : `does not fall within ghosted lesion (${ghostedLesion.onset} → ${ghostedLesion.end})`}
          </td>
        </tr>

        {/* Exposure modality — expected only */}
        <tr>
          <td style={{ fontWeight: 500 }}>Exposure modality</td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td><StatusBadge check={expected.exposure_modality} /></td>
          <td style={tdMuted}>{expected.exposure_modality.detail}</td>
        </tr>

        {/* Latency — 3 rows (optimistic / expected / conservative) */}
        <tr>
          <td rowSpan={3} style={{ fontWeight: 500, verticalAlign: 'middle' }}>
            Latency
          </td>
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

        {/* Natural order — expected only */}
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
  let cls = 'verdict-error'
  if (upper.includes('UNRELATED')) cls = 'verdict-error'
  else if (upper.includes('AMBIGUOUS')) cls = 'verdict-warning'
  else if (upper.includes('⚠') || upper.includes('OVERLAP')) cls = 'verdict-warning'
  else if (upper.includes('SOURCE')) cls = 'verdict-success'
  else if (upper.includes('SPREAD')) cls = 'verdict-info'

  const color: Record<string, string> = {
    'verdict-success': '#1d9e75',
    'verdict-info': '#378add',
    'verdict-warning': '#8a6d00',
    'verdict-error': '#e24b4a',
  }
  const bg: Record<string, string> = {
    'verdict-success': '#eafaf3',
    'verdict-info': '#e8f3fd',
    'verdict-warning': '#fef8ec',
    'verdict-error': '#fdf0f0',
  }

  return (
    <div
      style={{
        padding: '1rem 1.25rem',
        borderRadius: '8px',
        border: `1.5px solid ${color[cls]}`,
        background: bg[cls],
        fontWeight: 600,
        fontSize: '1rem',
        color: color[cls],
      }}
    >
      <span style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.08em', opacity: 0.7, display: 'block', marginBottom: '0.25rem' }}>
        TRANSMISSION ANALYSIS
      </span>
      {verdict}
    </div>
  )
}

/** Supporting evidence (passing criteria) and any failures that limit confidence. */
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

  // Source scenario
  if (srcExpected.exposure.status === 'pass') {
    passing.push({ scenario: 'Source', text: srcExpected.exposure.detail })
  } else if (srcExpected.exposure.status === 'fail') {
    failing.push({ scenario: 'Source', text: `${c1} was likely not infected by ${c2} because the reported exposure window does not overlap with ${c2}'s ghosted source lesion (${srcLesion.onset} → ${srcLesion.end}).` })
  }
  if (srcExpected.exposure_modality.status === 'pass') {
    passing.push({ scenario: 'Source', text: srcExpected.exposure_modality.detail })
  } else if (srcExpected.exposure_modality.status === 'fail') {
    failing.push({ scenario: 'Source', text: `The type of sexual contact between ${c1} and ${c2} is not compatible with the site of ${c1}'s ${result.case1_symptom.type}.` })
  }
  if (srcExpected.latency.status === 'pass') {
    passing.push({ scenario: 'Source', text: srcExpected.latency.detail })
  } else if (srcExpected.latency.status === 'fail') {
    failing.push({ scenario: 'Source', text: srcExpected.latency.detail })
  }
  if (srcExpected.natural_order.status === 'pass') {
    passing.push({ scenario: 'Source', text: srcExpected.natural_order.detail })
  } else if (srcExpected.natural_order.status === 'fail') {
    failing.push({ scenario: 'Source', text: `The ghosted source lesion would have occurred after ${c2}'s existing secondary lesion — primary must precede secondary. ${srcExpected.natural_order.detail}` })
  }

  // Spread scenario
  if (sprExpected.exposure.status === 'pass') {
    passing.push({ scenario: 'Spread', text: sprExpected.exposure.detail })
  } else if (sprExpected.exposure.status === 'fail') {
    failing.push({ scenario: 'Spread', text: `${c2} was likely not infected by ${c1} because the reported exposure window does not overlap with ${c1}'s infectious period (${sprLesion.onset} → ${sprLesion.end}).` })
  }
  if (sprExpected.exposure_modality.status === 'pass') {
    passing.push({ scenario: 'Spread', text: sprExpected.exposure_modality.detail })
  } else if (sprExpected.exposure_modality.status === 'fail') {
    failing.push({ scenario: 'Spread', text: `The type of sexual contact is not compatible with the site of ${c1}'s ${result.case1_symptom.type}. ${sprExpected.exposure_modality.detail}` })
  }
  if (sprExpected.latency.status === 'pass') {
    passing.push({ scenario: 'Spread', text: sprExpected.latency.detail })
  } else if (sprExpected.latency.status === 'fail') {
    failing.push({ scenario: 'Spread', text: sprExpected.latency.detail })
  }
  if (sprExpected.natural_order.status === 'pass') {
    passing.push({ scenario: 'Spread', text: sprExpected.natural_order.detail })
  } else if (sprExpected.natural_order.status === 'fail') {
    failing.push({ scenario: 'Spread', text: `The ghosted spread lesion would have occurred after ${c2}'s existing secondary lesion — primary must precede secondary. ${sprExpected.natural_order.detail}` })
  }

  return (
    <div className="panel stack-sm" style={{ fontSize: '0.875rem' }}>
      <p className="eyebrow">Why?</p>
      {passing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#1d9e75', marginBottom: '0.25rem' }}>Supporting evidence — criteria that passed:</p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {passing.map((p, i) => (
              <li key={i} style={{ marginBottom: '0.4rem' }}>
                <span style={{ fontWeight: 600, color: '#1d9e75', marginRight: '0.4rem' }}>[{p.scenario}]</span>
                {p.text}
              </li>
            ))}
          </ul>
        </>
      )}
      {failing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#e24b4a', marginBottom: '0.25rem', marginTop: passing.length > 0 ? '0.75rem' : 0 }}>Limiting factors — criteria that failed:</p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {failing.map((f, i) => (
              <li key={i} style={{ marginBottom: '0.4rem' }}>
                <span style={{ fontWeight: 600, color: '#e24b4a', marginRight: '0.4rem' }}>[{f.scenario}]</span>
                {f.text}
              </li>
            ))}
          </ul>
        </>
      )}
      {passing.length === 0 && failing.length === 0 && (
        <p style={{ color: '#888' }}>No criteria detail available.</p>
      )}
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel" style={{ padding: '1rem', minWidth: 0 }}>
      <p className="eyebrow" style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>
        {label}
      </p>
      <p style={{ fontWeight: 600, fontSize: '1.1rem', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </p>
    </div>
  )
}

function GhostingRecordsTable({
  records,
  partners,
  caseName,
  onDelete,
  deleting,
}: {
  records: GhostingRecord[]
  partners: PartnerSummary[]
  caseName: string
  onDelete: (id: number) => void
  deleting: boolean
}) {
  const refMap: Record<string, string> = { OP: caseName }
  for (const p of partners) {
    refMap[String(p.partner_number)] = p.name ?? `Partner ${p.partner_number}`
  }

  return (
    <div className="panel table-panel stack-sm">
      <div>
        <p className="eyebrow">Saved records</p>
        <h3>Ghosting records</h3>
      </div>
      <table className="data-table" style={{ width: '100%' }}>
        <thead>
          <tr>
            <th>Type</th>
            <th>From</th>
            <th>To</th>
            <th>Notes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {records.map((g) => (
            <tr key={g.id}>
              <td>
                <span
                  style={{
                    fontWeight: 600,
                    color: g.ghosting_type === 'SOURCE' ? '#ef9f27' : '#d85a30',
                  }}
                >
                  {g.ghosting_type}
                </span>
              </td>
              <td>{refMap[g.from_ref ?? ''] ?? g.from_ref ?? '—'}</td>
              <td>{refMap[g.to_ref ?? ''] ?? g.to_ref ?? '—'}</td>
              <td
                style={{
                  fontSize: '0.8rem',
                  color: 'var(--color-text-muted, #666)',
                  maxWidth: '320px',
                }}
              >
                {(g.notes ?? '').slice(0, 100)}
                {(g.notes?.length ?? 0) > 100 ? '…' : ''}
              </td>
              <td>
                <button
                  className="button button-danger"
                  style={{ fontSize: '0.8rem', padding: '0.2rem 0.6rem' }}
                  onClick={() => onDelete(g.id)}
                  disabled={deleting}
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function GhostingPage() {
  const { caseId } = useParams()
  const parsedCaseId = Number(caseId)

  const caseQuery = useCase(parsedCaseId)
  const partnersQuery = useQuery({
    queryKey: ['cases', parsedCaseId, 'partners'],
    queryFn: () => getPartnersForCase(parsedCaseId) as Promise<PartnerSummary[]>,
    enabled: parsedCaseId > 0,
  })
  const ghostingsQuery = useCaseGhostings(parsedCaseId)
  const runAnalysis = useRunGhostingAnalysis()
  const createGhosting = useCreateGhosting(parsedCaseId)
  const deleteGhosting = useDeleteGhosting(parsedCaseId)

  const [selectedPartnerId, setSelectedPartnerId] = useState<number | null>(null)
  const [result, setResult] = useState<GhostingAnalysisResult | null>(null)
  const [activeTab, setActiveTab] = useState<'source' | 'spread'>('source')
  const [saveSource, setSaveSource] = useState(true)
  const [saveSpread, setSaveSpread] = useState(true)
  const [showLog, setShowLog] = useState(false)
  const [showRef, setShowRef] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [savedOk, setSavedOk] = useState(false)

  useEffect(() => {
    const partners = partnersQuery.data
    if (!partners || partners.length === 0 || selectedPartnerId) return
    const id = setTimeout(() => setSelectedPartnerId(partners[0].id), 0)
    return () => clearTimeout(id)
  }, [partnersQuery.data, selectedPartnerId])

  if (!Number.isInteger(parsedCaseId) || parsedCaseId <= 0) {
    return <ErrorState title="Invalid case" message="The case id is not valid." />
  }

  if (caseQuery.isLoading || partnersQuery.isLoading) {
    return <LoadingState message="Loading case data…" />
  }

  if (caseQuery.isError) {
    return (
      <ErrorState
        title="Unable to load case"
        message={caseQuery.error.message}
        onRetry={() => void caseQuery.refetch()}
      />
    )
  }

  const caseData = caseQuery.data
  const partners = (partnersQuery.data as PartnerSummary[] | undefined) ?? []

  if (!caseData) {
    return <ErrorState title="Case not found" message="No case was returned." />
  }

  const selectedPartner = partners.find((p) => p.id === selectedPartnerId) ?? null
  const partnerLabel = (p: PartnerSummary) =>
    `Partner ${p.partner_number} — ${p.name ?? 'Unnamed'}`

  async function handleRunAnalysis() {
    if (!selectedPartnerId) return
    setResult(null)
    setSaveError(null)
    setSavedOk(false)
    try {
      const res = await runAnalysis.mutateAsync({
        caseId: parsedCaseId,
        partnerId: selectedPartnerId,
        payload: {},
      })
      setResult(res)
    } catch {
      // error shown via mutation state
    }
  }

  async function handleSave() {
    if (!result) return
    setSaveError(null)
    setSavedOk(false)
    const toSave = result.suggested_records.filter(
      (r) =>
        (r.ghosting_type === 'Ghosting a Source' && saveSource) ||
        (r.ghosting_type === 'Ghosting a Spread' && saveSpread) ||
        (r.ghosting_type === 'Ghosting a Spread Ghost' && saveSpread),
    )
    try {
      for (const r of toSave) {
        await createGhosting.mutateAsync({
          ghosting_type: r.ghosting_type,
          from_ref: r.from_ref,
          to_ref: r.to_ref,
          notes: r.notes,
        })
      }
      setSavedOk(true)
      setResult(null)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save records.')
    }
  }

  const activeScenario =
    activeTab === 'source' ? result?.source_scenarios : result?.spread_scenarios
  const activeGhostedLesion =
    activeTab === 'source'
      ? result?.ghosted_source
      : result?.ghosted_spread

  function buildHypothesis(tab: 'source' | 'spread', r: GhostingAnalysisResult): string {
    if (tab === 'source') {
      return `This scenario tests whether ${r.case2_name} infected ${r.case1_name}.`
    }
    return `This scenario tests whether ${r.case1_name} infected ${r.case2_name}.`
  }

  return (
    <section className="stack-lg">
      <header className="panel stack-sm">
        <div>
          <p className="eyebrow">VCA Methodology</p>
          <h2>Ghosting Analysis</h2>
        </div>
      </header>

      <GlossaryPanel />

      {/* Clinical reference */}
      <div>
        <button
          className="button"
          style={{ fontSize: '0.85rem' }}
          onClick={() => setShowRef((v) => !v)}
        >
          {showRef ? '▾' : '▸'} Clinical reference — syphilis natural history
        </button>
        {showRef && (
          <div className="panel" style={{ marginTop: '0.5rem' }}>
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Phase</th>
                  <th>Min</th>
                  <th>Avg</th>
                  <th>Max</th>
                </tr>
              </thead>
              <tbody>
                {CLINICAL_REF.map((row) => (
                  <tr key={row.phase}>
                    <td>{row.phase}</td>
                    <td>{row.min}</td>
                    <td>{row.avg}</td>
                    <td>{row.max}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
              Interview period — Primary: 125 days before chancre onset. Secondary: 237 days before
              secondary onset.
            </p>
          </div>
        )}
      </div>

      {/* Step 1: Select partner */}
      <div className="panel stack-sm">
        <div>
          <p className="eyebrow">Step 1</p>
          <h3>Select partner</h3>
        </div>

        {partners.length === 0 ? (
          <p className="muted">No partners on file. Add partners on the Partners tab first.</p>
        ) : (
          <label className="field">
            <span>Compare {caseData.patient_name} (index patient) against</span>
            <select
              value={selectedPartnerId ?? ''}
              onChange={(e) => {
                setSelectedPartnerId(Number(e.target.value))
                setResult(null)
              }}
            >
              {partners.map((p) => (
                <option key={p.id} value={p.id}>
                  {partnerLabel(p)}
                </option>
              ))}
            </select>
          </label>
        )}

        <p className="muted" style={{ fontSize: '0.8rem' }}>
          The analysis uses symptom and exposure data saved for both patients. Ensure those records are complete before running.
        </p>

        <div>
          <button
            className="button button-primary"
            onClick={() => void handleRunAnalysis()}
            disabled={!selectedPartnerId || runAnalysis.isPending || partners.length === 0}
          >
            {runAnalysis.isPending ? 'Running…' : 'Run ghosting analysis'}
          </button>
        </div>

        {runAnalysis.isError && (
          <p style={{ color: '#e24b4a', fontSize: '0.875rem' }}>
            {runAnalysis.error instanceof Error
              ? runAnalysis.error.message
              : 'Analysis failed. Check that both parties have symptom data on file.'}
          </p>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          <VerdictBanner verdict={result.verdict} />
          <VerdictContext result={result} />

          {/* Anchor symptom used */}
          <div className="panel stack-xs" style={{ fontSize: '0.875rem' }}>
            <p className="eyebrow">Anchor symptom — {result.case1_name}</p>
            <p>
              <strong>{result.case1_name}</strong> ·{' '}
              {result.case1_symptom.type} · Onset {result.case1_symptom.onset}
              {result.case1_symptom.duration_days > 0
                ? ` · Duration ${result.case1_symptom.duration_days}d`
                : ''}
              {' · '}Avg inoculation date: <strong>{computeInoculationAvg(result.case1_symptom)}</strong>
            </p>
          </div>

          {/* 4 metric cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '0.75rem',
            }}
          >
            <MetricCard label="Source lesion onset" value={result.ghosted_source.onset} />
            <MetricCard label="Source lesion end" value={result.ghosted_source.end} />
            <MetricCard label="Spread lesion onset" value={result.ghosted_spread.onset} />
            <MetricCard label="Spread lesion end" value={result.ghosted_spread.end} />
          </div>

          {/* Scenario tabs */}
          <div className="panel stack-md">
            <nav className="tab-nav" aria-label="Scenario">
              <button
                className={activeTab === 'source' ? 'tab-link tab-link-active' : 'tab-link'}
                onClick={() => setActiveTab('source')}
              >
                Source scenario
              </button>
              <button
                className={activeTab === 'spread' ? 'tab-link tab-link-active' : 'tab-link'}
                onClick={() => setActiveTab('spread')}
              >
                Spread scenario
              </button>
            </nav>

            {activeScenario && activeGhostedLesion && (
              <div className="stack-md">
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
                  <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>
                    What this scenario tests
                  </p>
                  <p>{buildHypothesis(activeTab, result)}</p>
                </div>

                {/* Lesion window + confidence */}
                <div
                  style={{
                    display: 'flex',
                    gap: '1.5rem',
                    alignItems: 'center',
                    fontSize: '0.9rem',
                    flexWrap: 'wrap',
                  }}
                >
                  <div>
                    <p className="eyebrow">Calculated lesion window (expected)</p>
                    <p style={{ fontWeight: 600 }}>
                      {activeGhostedLesion.onset} → {activeGhostedLesion.end}
                    </p>
                    <p className="muted" style={{ fontSize: '0.8rem' }}>
                      Assigned to {activeGhostedLesion.assigned_to} · derived from{' '}
                      {activeGhostedLesion.derived_from_symptom}
                    </p>
                  </div>
                  <div>
                    <p className="eyebrow">Confidence</p>
                    <p style={{ fontWeight: 600 }}>{activeScenario.confidence}</p>
                  </div>
                  <div>
                    <p className="eyebrow">Criteria passed</p>
                    <p style={{ fontWeight: 600 }}>{activeScenario.pass_count} / 4</p>
                  </div>
                </div>

                <p className="eyebrow">
                  Criteria — latency shown across all 3 ranges (optimistic / expected / conservative)
                </p>
                <EnhancedCriteriaTable
                  aggressive={activeScenario.range_data.aggressive}
                  expected={activeScenario.range_data.expected}
                  conservative={activeScenario.range_data.conservative}
                  case1Symptom={result.case1_symptom}
                  ghostedLesion={activeGhostedLesion}
                  case1Name={result.case1_name}
                />
              </div>
            )}
          </div>

          {/* Step log */}
          <div>
            <button
              className="button"
              style={{ fontSize: '0.85rem' }}
              onClick={() => setShowLog((v) => !v)}
            >
              {showLog ? '▾' : '▸'} Step-by-step analysis log
            </button>
            {showLog && (
              <pre
                className="panel"
                style={{
                  marginTop: '0.5rem',
                  fontSize: '0.78rem',
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.6,
                  background: '#f8f9fa',
                }}
              >
                {result.log.join('\n')}
              </pre>
            )}
          </div>

          {/* Save section */}
          <div className="panel stack-md">
            <div>
              <p className="eyebrow">Step 2</p>
              <h3>Save ghosted lesions</h3>
              <p className="muted" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
                Saved lesions appear in the VCA chart and network graph.
              </p>
            </div>

            <div className="stack-xs">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={saveSource}
                  onChange={(e) => setSaveSource(e.target.checked)}
                />
                <span>
                  Save ghosted <strong>SOURCE</strong> lesion (
                  {result.ghosted_source.onset} → {result.ghosted_source.end}) — assigned to{' '}
                  {result.ghosted_source.assigned_to}
                </span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={saveSpread}
                  onChange={(e) => setSaveSpread(e.target.checked)}
                />
                <span>
                  Save ghosted <strong>SPREAD</strong> lesion (
                  {result.ghosted_spread.onset} → {result.ghosted_spread.end}) — assigned to{' '}
                  {result.ghosted_spread.assigned_to}
                </span>
              </label>
            </div>

            {saveError && (
              <p style={{ color: '#e24b4a', fontSize: '0.875rem' }}>{saveError}</p>
            )}

            <div>
              <button
                className="button button-primary"
                onClick={() => void handleSave()}
                disabled={(!saveSource && !saveSpread) || createGhosting.isPending}
              >
                {createGhosting.isPending ? 'Saving…' : 'Save selected lesions'}
              </button>
            </div>
          </div>
        </>
      )}

      {/* Save success confirmation */}
      {savedOk && !result && (
        <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', background: '#eafaf3', border: '1.5px solid #1d9e75', color: '#1d9e75', fontWeight: 600, fontSize: '0.9rem' }}>
          ✓ Ghosted lesions saved. They will appear in the VCA chart and network graph.
        </div>
      )}

      {/* No result yet + no partners prompt */}
      {!result && !runAnalysis.isPending && selectedPartner && !savedOk && (
        <div
          className="panel"
          style={{
            textAlign: 'center',
            padding: '2.5rem',
            color: 'var(--color-text-muted, #888)',
          }}
        >
          <p>Select a partner and run the analysis to see results.</p>
          <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Analysis uses symptom and exposure data already saved for both parties.
          </p>
        </div>
      )}

      {/* Existing ghosting records */}
      {ghostingsQuery.data && ghostingsQuery.data.length > 0 && (
        <GhostingRecordsTable
          records={ghostingsQuery.data}
          partners={partners}
          caseName={caseData.patient_name}
          onDelete={(id) => void deleteGhosting.mutateAsync(id)}
          deleting={deleteGhosting.isPending}
        />
      )}
    </section>
  )
}
