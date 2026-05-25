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

function CriteriaTable({ criteria }: { criteria: GhostingScenarioCriteria }) {
  const rows = [
    { name: 'Exposure', check: criteria.exposure },
    { name: 'Exposure Modality', check: criteria.exposure_modality },
    { name: 'Latency', check: criteria.latency },
    { name: 'Natural Order', check: criteria.natural_order },
  ]
  return (
    <table className="data-table" style={{ width: '100%' }}>
      <thead>
        <tr>
          <th>Criterion</th>
          <th>Result</th>
          <th>Detail</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.name}>
            <td>{row.name}</td>
            <td>
              <StatusBadge check={row.check} />
            </td>
            <td style={{ fontSize: '0.875rem', color: 'var(--color-text-muted, #666)' }}>
              {row.check.detail}
            </td>
          </tr>
        ))}
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

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="panel"
      style={{ padding: '1rem', minWidth: 0 }}
    >
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

  // Default to the first partner once the list loads (deferred via timeout to avoid
  // triggering the cascading-setState lint rule for synchronous effect setState).
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
  const activeExpectedCriteria = activeScenario?.range_data.expected
  const activeExpectedLesion = activeScenario?.range_lesions.expected

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
            <p
              className="muted"
              style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}
            >
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

          {/* Anchor symptom used */}
          <div className="panel stack-xs" style={{ fontSize: '0.875rem' }}>
            <p className="eyebrow">Anchor symptom (P1)</p>
            <p>
              <strong>{result.case1_name}</strong> was assigned as P1 ·{' '}
              {result.case1_symptom.type} · Onset {result.case1_symptom.onset}
              {result.case1_symptom.duration_days > 0
                ? ` · Duration ${result.case1_symptom.duration_days}d`
                : ''}
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

            {activeScenario && activeExpectedLesion && activeExpectedCriteria && (
              <div className="stack-md">
                <div
                  style={{
                    display: 'flex',
                    gap: '1.5rem',
                    alignItems: 'center',
                    fontSize: '0.9rem',
                  }}
                >
                  <div>
                    <p className="eyebrow">Expected lesion window</p>
                    <p style={{ fontWeight: 600 }}>
                      {activeExpectedLesion.onset} → {activeExpectedLesion.end}
                    </p>
                    <p className="muted" style={{ fontSize: '0.8rem' }}>
                      Assigned to {activeExpectedLesion.assigned_to} · derived from{' '}
                      {activeExpectedLesion.derived_from_symptom}
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

                <p className="eyebrow">Criteria — expected range</p>
                <CriteriaTable criteria={activeExpectedCriteria} />
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
