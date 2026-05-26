import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
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
  if (upper.includes('SOURCE') && !upper.includes('UNRELATED')) cls = 'verdict-success'
  else if (upper.includes('SPREAD') && !upper.includes('UNRELATED')) cls = 'verdict-info'
  else if (upper.includes('AMBIGUOUS')) cls = 'verdict-warning'

  const style: Record<string, string> = {
    'verdict-success': '#1d9e75',
    'verdict-info': '#378add',
    'verdict-warning': '#ef9f27',
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
        border: `1.5px solid ${style[cls]}`,
        background: bg[cls],
        fontWeight: 600,
        fontSize: '1rem',
        color: style[cls],
      }}
    >
      Verdict: {verdict}
    </div>
  )
}

/** Plain-language explanation of each failing criterion. */
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
      text: `${c1} was likely not infected by ${c2} because the reported exposure window does not overlap with ${c2}'s ghosted source lesion (${srcLesion.onset} → ${srcLesion.end}). ${c2} would not have been infectious during the recorded contact.`,
    })
  }
  if (srcExpected.exposure_modality.status === 'fail') {
    failures.push({
      scenario: 'Source',
      text: `The type of sexual contact between ${c1} and ${c2} is not compatible with the site of ${c1}'s ${result.case1_symptom.type}. Transmission requires contact with the infected anatomical site.`,
    })
  }
  if (srcExpected.latency.status === 'fail') {
    failures.push({
      scenario: 'Source',
      text: `The timeline between ${c2}'s ghosted source lesion and their secondary symptoms does not fit the expected syphilis progression (requires ≥0 days latency). ${srcExpected.latency.detail}`,
    })
  }
  if (srcExpected.natural_order.status === 'fail') {
    failures.push({
      scenario: 'Source',
      text: `The ghosted source lesion would have occurred after ${c2}'s existing secondary lesion — this violates the biological order of syphilis stages (primary must precede secondary). ${srcExpected.natural_order.detail}`,
    })
  }

  if (sprExpected.exposure.status === 'fail') {
    failures.push({
      scenario: 'Spread',
      text: `${c2} was likely not infected by ${c1} because the reported exposure window does not overlap with ${c1}'s infectious period (${sprLesion.onset} → ${sprLesion.end}). ${c1} would not have been contagious during the recorded contact.`,
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
      text: `The ghosted spread lesion would have occurred after ${c2}'s existing secondary lesion — this violates the biological order of syphilis stages. ${sprExpected.natural_order.detail}`,
    })
  }

  if (failures.length === 0) {
    return (
      <div className="panel stack-xs" style={{ fontSize: '0.875rem' }}>
        <p className="eyebrow">Why this verdict?</p>
        <p style={{ color: '#1d9e75' }}>
          All key criteria passed — the verdict above is well-supported by the clinical data on file.
        </p>
      </div>
    )
  }

  return (
    <div className="panel stack-sm" style={{ fontSize: '0.875rem' }}>
      <p className="eyebrow">Why this verdict? — criteria that failed</p>
      <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
        {failures.map((f, i) => (
          <li key={i} style={{ marginBottom: '0.6rem' }}>
            <span
              style={{
                fontWeight: 600,
                color: '#e24b4a',
                marginRight: '0.4rem',
              }}
            >
              [{f.scenario}]
            </span>
            {f.text}
          </li>
        ))}
      </ul>
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
    const toSave = result.suggested_records.filter(
      (r) =>
        (r.ghosting_type === 'SOURCE' && saveSource) ||
        (r.ghosting_type === 'SPREAD' && saveSpread),
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

  // Build hypothesis text for the active tab
  function buildHypothesis(tab: 'source' | 'spread', r: GhostingAnalysisResult): string {
    const srcAssigned = r.ghosted_source.assigned_to
    const sprAssigned = r.ghosted_spread.assigned_to
    if (tab === 'source') {
      return `Hypothesis: ${srcAssigned} infected ${r.case1_name}. ` +
        `This scenario back-calculates when ${srcAssigned} would have had an active primary chancre ` +
        `(ghosted source lesion: ${r.ghosted_source.onset} → ${r.ghosted_source.end}) ` +
        `that could have been transmitted to ${r.case1_name} during the exposure window. ` +
        `For this to hold, the exposure must overlap with that infectious window, ` +
        `and ${r.case1_name}'s back-calculated inoculation date must fall within it.`
    }
    return `Hypothesis: ${r.case1_name} infected ${sprAssigned}. ` +
      `This scenario calculates when ${r.case1_name} would have been contagious ` +
      `(ghosted spread lesion: ${r.ghosted_spread.onset} → ${r.ghosted_spread.end}) ` +
      `and whether that infectious period overlaps with the reported contact with ${sprAssigned}.`
  }

  return (
    <section className="stack-lg">
      <header className="panel stack-sm">
        <div>
          <p className="eyebrow">VCA Methodology</p>
          <h2>Ghosting Analysis</h2>
        </div>
        <p className="muted" style={{ fontSize: '0.875rem' }}>
          Case #{caseData.id} — {caseData.patient_name} · NCSDDC Visual Case Analysis (2022)
        </p>
      </header>

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
            <span>Compare {caseData.patient_name} (OP) against</span>
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
          The analysis uses symptoms and exposure dates saved on both the OP and the selected
          partner. Ensure those records are complete before running.
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
            <p className="eyebrow">Anchor symptom (P1)</p>
            <p>
              <strong>{result.case1_name}</strong> was assigned as P1 ·{' '}
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
            <MetricCard label="Ghosted source onset" value={result.ghosted_source.onset} />
            <MetricCard label="Ghosted source end" value={result.ghosted_source.end} />
            <MetricCard label="Ghosted spread onset" value={result.ghosted_spread.onset} />
            <MetricCard label="Ghosted spread end" value={result.ghosted_spread.end} />
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
                    <p className="eyebrow">Ghosted lesion window (expected)</p>
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

      {/* No result yet + no partners prompt */}
      {!result && !runAnalysis.isPending && selectedPartner && (
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
