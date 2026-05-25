import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useQueries } from '@tanstack/react-query'

import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
import { getCase } from '../cases/api'
import { getCasePartnerRelationship, getPartnersForCase } from '../partners/api'
import { listCaseSymptoms, listPartnerSymptoms } from '../symptoms/api'
import { listCaseGhostings } from './api'
import type { GhostingRecord, PartnerSummary, RelationshipSummary } from './types'
import type { CaseRead } from '../cases/types'
import type { SymptomEntryRead } from '../symptoms/types'

// ---------------------------------------------------------------------------
// Clinical constants (mirrored from app/utils/clinical.py)
// ---------------------------------------------------------------------------

const INCUBATION = { min: 10, avg: 21, max: 90 }
const PRIMARY = { min: 7, avg: 21, max: 35 }
const LATENCY = { min: 0, avg: 28, max: 70 }
const INTERVIEW_PERIOD_PRIMARY_DAYS = 125  // INCUBATION.max + PRIMARY.max
const INTERVIEW_PERIOD_SECONDARY_DAYS = 237

// ---------------------------------------------------------------------------
// Chart colors (matching Streamlit VCA training material convention)
// ---------------------------------------------------------------------------

const COLORS = {
  symptomOnset: '#E24B4A',
  symptomBar: '#E24B4A',
  exposurePartner: '#7F77DD',
  exposureOp: '#EF9F27',
  critical: '#1D9E75',
  inoculation: '#1D9E75',
  ghostedSource: '#EF9F27',
  ghostedSpread: '#D85A30',
  treatment: '#2C2C2A',
  interview: '#1D9E75',
  grid: 'rgba(180,178,169,0.25)',
  axis: '#999',
}

// ---------------------------------------------------------------------------
// Chart layout constants
// ---------------------------------------------------------------------------

const LEFT_MARGIN = 170
const RIGHT_MARGIN = 24
const TOP_MARGIN = 16
const BOTTOM_MARGIN = 56
const ROW_HEIGHT = 80

// ---------------------------------------------------------------------------
// Date utilities
// ---------------------------------------------------------------------------

function parseDate(s: string | null | undefined): Date | null {
  if (!s) return null
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

function addDays(d: Date, days: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + days)
  return r
}

function formatMonthYear(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

function getMonthTicks(minDate: Date, maxDate: Date): Date[] {
  const ticks: Date[] = []
  const cur = new Date(minDate.getFullYear(), minDate.getMonth(), 1)
  while (cur <= maxDate) {
    ticks.push(new Date(cur))
    cur.setMonth(cur.getMonth() + 1)
  }
  return ticks
}

// ---------------------------------------------------------------------------
// Symptom classification helpers
// ---------------------------------------------------------------------------

const PRIMARY_KEYWORDS = ['Anal', 'Oral', 'Vaginal', 'Penile', 'Rectal', 'LX']
const SECONDARY_KEYWORDS = ['Rash', 'Alopecia', 'Lata']

function classifySymptomType(symptomType: string): 'Primary Chancre' | 'Secondary Rash/Lesions' | null {
  if (PRIMARY_KEYWORDS.some((k) => symptomType.includes(k))) return 'Primary Chancre'
  if (SECONDARY_KEYWORDS.some((k) => symptomType.includes(k))) return 'Secondary Rash/Lesions'
  return null
}

function getInoculationPoints(
  chartType: string,
  onset: Date,
  durationDays: number,
): { min: Date; avg: Date; max: Date } | null {
  const dur = durationDays > 0 ? durationDays : PRIMARY.avg
  if (['Primary Chancre', 'Historical Primary', 'Ghosted Primary'].includes(chartType)) {
    return {
      min: addDays(onset, -INCUBATION.min),
      avg: addDays(onset, -INCUBATION.avg),
      max: addDays(onset, -INCUBATION.max),
    }
  }
  if (chartType === 'Secondary Rash/Lesions') {
    return {
      min: addDays(onset, -(INCUBATION.min + dur + LATENCY.min)),
      avg: addDays(onset, -(INCUBATION.avg + dur + LATENCY.avg)),
      max: addDays(onset, -(INCUBATION.max + dur + LATENCY.max)),
    }
  }
  return null
}

// Parse ghosted lesion date pair from the notes string saved by the engine
function parseGhostingDates(notes: string | null): [Date, Date] | null {
  if (!notes) return null
  const matches = notes.match(/\d{4}-\d{2}-\d{2}/g)
  if (!matches || matches.length < 2) return null
  const a = parseDate(matches[0])
  const b = parseDate(matches[1])
  return a && b ? [a, b] : null
}

// ---------------------------------------------------------------------------
// SVG marker helpers
// ---------------------------------------------------------------------------

function trianglePoints(cx: number, cy: number, r: number): string {
  return `${cx},${cy - r} ${cx - r},${cy + r} ${cx + r},${cy + r}`
}

function diamondPoints(cx: number, cy: number, r: number): string {
  return `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`
}

function starPath(cx: number, cy: number, r: number): string {
  const pts: string[] = []
  for (let i = 0; i < 10; i++) {
    const angle = (i * Math.PI) / 5 - Math.PI / 2
    const rad = i % 2 === 0 ? r : r * 0.42
    pts.push(`${cx + rad * Math.cos(angle)},${cy + rad * Math.sin(angle)}`)
  }
  return `M${pts.join('L')}Z`
}

// ---------------------------------------------------------------------------
// Chart data types
// ---------------------------------------------------------------------------

type PersonData = {
  label: string
  isOp: boolean
  symptomType: string | null
  symptomOnset: Date | null
  symptomDuration: number
  treatmentDate: Date | null
  firstExposure: Date | null
  lastExposure: Date | null
}

// ---------------------------------------------------------------------------
// SVG Timeline component
// ---------------------------------------------------------------------------

function VcaTimeline({
  people,
  ghostings,
  partnerRefMap,
  containerWidth,
  toggles,
}: {
  people: PersonData[]
  ghostings: GhostingRecord[]
  partnerRefMap: Record<string, string>
  containerWidth: number
  toggles: {
    showDurations: boolean
    showInoc: boolean
    showGhosted: boolean
    showCritical: boolean
    showInterview: boolean
  }
}) {
  // Date range
  const allDates: Date[] = []
  for (const p of people) {
    if (p.treatmentDate) allDates.push(p.treatmentDate)
    if (p.firstExposure) allDates.push(p.firstExposure)
    if (p.lastExposure) allDates.push(p.lastExposure)
    if (p.symptomOnset) {
      allDates.push(p.symptomOnset)
      if (p.symptomDuration > 0) allDates.push(addDays(p.symptomOnset, p.symptomDuration))
    }
  }
  for (const g of ghostings) {
    const dates = parseGhostingDates(g.notes)
    if (dates) allDates.push(...dates)
  }

  const today = new Date()
  const minDate = allDates.length > 0 ? addDays(new Date(Math.min(...allDates.map((d) => d.getTime()))), -45) : addDays(today, -180)
  const maxDate = allDates.length > 0 ? addDays(new Date(Math.max(...allDates.map((d) => d.getTime()))), 45) : addDays(today, 30)

  const chartW = containerWidth - LEFT_MARGIN - RIGHT_MARGIN
  const svgH = TOP_MARGIN + people.length * ROW_HEIGHT + BOTTOM_MARGIN

  function dateToX(d: Date): number {
    const span = maxDate.getTime() - minDate.getTime()
    if (span === 0) return LEFT_MARGIN
    return LEFT_MARGIN + ((d.getTime() - minDate.getTime()) / span) * chartW
  }

  function rowY(i: number): number {
    return TOP_MARGIN + i * ROW_HEIGHT + ROW_HEIGHT / 2
  }

  const xTicks = getMonthTicks(minDate, maxDate)
  // Reduce tick density if too many
  const tickStep = xTicks.length > 24 ? 3 : xTicks.length > 12 ? 2 : 1
  const visibleTicks = xTicks.filter((_, i) => i % tickStep === 0)

  return (
    <svg
      width={containerWidth}
      height={svgH}
      style={{ display: 'block', overflow: 'visible', fontFamily: 'inherit' }}
      aria-label="VCA Timeline chart"
    >
      {/* Grid lines + Y labels */}
      {people.map((p, i) => (
        <g key={`row-${i}`}>
          <line
            x1={LEFT_MARGIN}
            y1={rowY(i)}
            x2={LEFT_MARGIN + chartW}
            y2={rowY(i)}
            stroke={COLORS.grid}
            strokeWidth={1}
            strokeDasharray="3 5"
          />
          <text
            x={LEFT_MARGIN - 10}
            y={rowY(i)}
            textAnchor="end"
            dominantBaseline="middle"
            fontSize={12}
            fill="#132238"
            style={{ userSelect: 'none' }}
          >
            {p.label.length > 22 ? p.label.slice(0, 22) + '…' : p.label}
          </text>
        </g>
      ))}

      {/* Per-person chart elements */}
      {people.map((p, i) => {
        const y = rowY(i)
        const onset = p.symptomOnset
        const chartType = p.symptomType
        const dur = p.symptomDuration || PRIMARY.avg

        return (
          <g key={`person-${i}`}>
            {/* Symptom duration bar */}
            {toggles.showDurations && chartType && onset && (
              <line
                x1={dateToX(onset)}
                y1={y}
                x2={dateToX(addDays(onset, dur))}
                y2={y}
                stroke={COLORS.symptomBar}
                strokeWidth={7}
                strokeLinecap="round"
              >
                <title>
                  {p.label} — {chartType} · Onset {onset.toISOString().slice(0, 10)} · Est. end{' '}
                  {addDays(onset, dur).toISOString().slice(0, 10)}
                </title>
              </line>
            )}

            {/* Symptom onset marker (▲) */}
            {chartType && onset && (
              <polygon
                points={trianglePoints(dateToX(onset), y, 7)}
                fill={COLORS.symptomOnset}
              >
                <title>
                  {p.label} — Symptom onset: {onset.toISOString().slice(0, 10)} · {chartType}
                </title>
              </polygon>
            )}

            {/* Inoculation points (◆) */}
            {toggles.showInoc && chartType && onset && (() => {
              const pts = getInoculationPoints(chartType, onset, dur)
              if (!pts) return null
              return (
                <g>
                  {[
                    { d: pts.min, label: 'Min inoculation' },
                    { d: pts.avg, label: 'Avg inoculation' },
                    { d: pts.max, label: 'Max inoculation' },
                  ].map(({ d, label }) => (
                    <polygon
                      key={label}
                      points={diamondPoints(dateToX(d), y, 7)}
                      fill={COLORS.inoculation}
                    >
                      <title>
                        {p.label} — {label}: {d.toISOString().slice(0, 10)}
                      </title>
                    </polygon>
                  ))}
                </g>
              )
            })()}

            {/* Treatment marker (★) */}
            {p.treatmentDate && (
              <path
                d={starPath(dateToX(p.treatmentDate), y, 8)}
                fill={COLORS.treatment}
              >
                <title>
                  {p.label} — Treatment: {p.treatmentDate.toISOString().slice(0, 10)}
                </title>
              </path>
            )}

            {/* Exposure window */}
            {p.firstExposure && p.lastExposure && (() => {
              const color = p.isOp ? COLORS.exposureOp : COLORS.exposurePartner
              const dash = p.isOp ? '3 5' : '8 5'
              const label = p.isOp ? 'OP elicited exposure' : 'Partner reported exposure'
              return (
                <line
                  x1={dateToX(p.firstExposure)}
                  y1={y}
                  x2={dateToX(p.lastExposure)}
                  y2={y}
                  stroke={color}
                  strokeWidth={5}
                  strokeDasharray={dash}
                  strokeLinecap="round"
                >
                  <title>
                    {p.label} — {label}: {p.firstExposure.toISOString().slice(0, 10)} →{' '}
                    {p.lastExposure.toISOString().slice(0, 10)}
                  </title>
                </line>
              )
            })()}

            {/* Critical period (OP only) */}
            {toggles.showCritical && p.isOp && chartType && onset && (() => {
              const pts = getInoculationPoints(chartType, onset, dur)
              const critStart = pts ? pts.max : addDays(onset, -(INCUBATION.max + PRIMARY.max))
              const critEnd = p.treatmentDate ?? maxDate
              return (
                <line
                  x1={dateToX(critStart)}
                  y1={y - 14}
                  x2={dateToX(critEnd)}
                  y2={y - 14}
                  stroke={COLORS.critical}
                  strokeWidth={3}
                  strokeLinecap="round"
                >
                  <title>
                    Critical period: {critStart.toISOString().slice(0, 10)} →{' '}
                    {critEnd.toISOString().slice(0, 10)}
                  </title>
                </line>
              )
            })()}

            {/* Interview period (OP only) */}
            {toggles.showInterview && p.isOp && onset && (() => {
              const isPrimary = chartType === 'Primary Chancre'
              const days = isPrimary ? INTERVIEW_PERIOD_PRIMARY_DAYS : INTERVIEW_PERIOD_SECONDARY_DAYS
              const intStart = addDays(onset, -days)
              const intEnd = p.treatmentDate ?? maxDate
              return (
                <line
                  x1={dateToX(intStart)}
                  y1={y + 14}
                  x2={dateToX(intEnd)}
                  y2={y + 14}
                  stroke={COLORS.interview}
                  strokeWidth={2}
                  strokeDasharray="12 4"
                  strokeLinecap="round"
                >
                  <title>
                    Interview period: {intStart.toISOString().slice(0, 10)} →{' '}
                    {intEnd.toISOString().slice(0, 10)}
                  </title>
                </line>
              )
            })()}
          </g>
        )
      })}

      {/* Ghosted lesions */}
      {toggles.showGhosted &&
        ghostings.map((g, i) => {
          const dates = parseGhostingDates(g.notes)
          if (!dates) return null
          const [gOnset, gEnd] = dates
          const yRef = partnerRefMap[g.to_ref ?? ''] ?? g.to_ref ?? ''
          const personIdx = people.findIndex((p) => p.label === yRef)
          if (personIdx < 0) return null
          const y = rowY(personIdx)
          const isSource = (g.ghosting_type ?? '').toLowerCase().includes('source')
          const color = isSource ? COLORS.ghostedSource : COLORS.ghostedSpread
          const gLabel = isSource ? 'Ghosted source' : 'Ghosted spread'
          const fromLabel = partnerRefMap[g.from_ref ?? ''] ?? g.from_ref ?? '?'

          return (
            <g key={`ghost-${i}`}>
              <line
                x1={dateToX(gOnset)}
                y1={y + 20}
                x2={dateToX(gEnd)}
                y2={y + 20}
                stroke={color}
                strokeWidth={4}
                strokeDasharray="10 4 3 4"
                strokeLinecap="round"
              >
                <title>
                  {gLabel}: {gOnset.toISOString().slice(0, 10)} → {gEnd.toISOString().slice(0, 10)}{' '}
                  · From: {fromLabel}
                </title>
              </line>
              {[gOnset, gEnd].map((d, j) => (
                <circle
                  key={j}
                  cx={dateToX(d)}
                  cy={y + 20}
                  r={4}
                  fill="none"
                  stroke={color}
                  strokeWidth={1.5}
                />
              ))}
            </g>
          )
        })}

      {/* X-axis */}
      <g transform={`translate(0, ${TOP_MARGIN + people.length * ROW_HEIGHT})`}>
        <line
          x1={LEFT_MARGIN}
          y1={0}
          x2={LEFT_MARGIN + chartW}
          y2={0}
          stroke={COLORS.axis}
          strokeWidth={1}
        />
        {visibleTicks.map((tick) => {
          const x = dateToX(tick)
          return (
            <g key={tick.toISOString()}>
              <line x1={x} y1={0} x2={x} y2={6} stroke={COLORS.axis} strokeWidth={1} />
              <text
                x={x}
                y={20}
                textAnchor="middle"
                fontSize={11}
                fill="#666"
                style={{ userSelect: 'none' }}
              >
                {formatMonthYear(tick)}
              </text>
            </g>
          )
        })}
      </g>
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------

const LEGEND_ITEMS = [
  { label: 'Symptom onset', symbol: '▲', color: COLORS.symptomOnset },
  { label: 'Symptom duration', symbol: '━', color: COLORS.symptomBar },
  { label: 'Inoculation points', symbol: '◆', color: COLORS.inoculation },
  { label: 'Critical period', symbol: '━', color: COLORS.critical },
  { label: 'Interview period', symbol: '╌', color: COLORS.interview },
  { label: 'Partner exposure window', symbol: '╌', color: COLORS.exposurePartner },
  { label: 'OP elicited exposure', symbol: '·····', color: COLORS.exposureOp },
  { label: 'Treatment', symbol: '★', color: COLORS.treatment },
  { label: 'Ghosted source lesion', symbol: '╌·╌', color: COLORS.ghostedSource },
  { label: 'Ghosted spread lesion', symbol: '╌·╌', color: COLORS.ghostedSpread },
]

// ---------------------------------------------------------------------------
// VcaChartPage
// ---------------------------------------------------------------------------

export function VcaChartPage() {
  const { caseId } = useParams()
  const parsedCaseId = Number(caseId)

  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(900)

  const [showDurations, setShowDurations] = useState(true)
  const [showInoc, setShowInoc] = useState(true)
  const [showGhosted, setShowGhosted] = useState(true)
  const [showCritical, setShowCritical] = useState(true)
  const [showInterview, setShowInterview] = useState(true)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      setContainerWidth(entries[0].contentRect.width)
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // Base data: case + partners + ghostings + case symptoms
  const baseQuery = useQuery({
    queryKey: ['cases', parsedCaseId, 'vca-chart-base'],
    queryFn: async () => {
      const [caseData, partners, ghostings, caseSymptoms] = await Promise.all([
        getCase(parsedCaseId) as Promise<CaseRead>,
        getPartnersForCase(parsedCaseId) as Promise<PartnerSummary[]>,
        listCaseGhostings(parsedCaseId),
        listCaseSymptoms(parsedCaseId),
      ])
      return { caseData, partners, ghostings, caseSymptoms }
    },
    enabled: parsedCaseId > 0,
  })

  const partners = baseQuery.data?.partners ?? []

  // Per-partner data: relationship + symptoms
  const partnerDataQueries = useQueries({
    queries: partners.map((p) => ({
      queryKey: ['cases', parsedCaseId, 'partners', p.id, 'chart-data'],
      queryFn: async () => {
        const [relationship, symptoms] = await Promise.all([
          (getCasePartnerRelationship(parsedCaseId, p.id) as Promise<RelationshipSummary>).catch(
            () => null,
          ),
          listPartnerSymptoms(p.id) as Promise<SymptomEntryRead[]>,
        ])
        return { partnerId: p.id, relationship, symptoms }
      },
      enabled: !!baseQuery.data && partners.length > 0,
    })),
  })

  if (!Number.isInteger(parsedCaseId) || parsedCaseId <= 0) {
    return <ErrorState title="Invalid case" message="The case id is not valid." />
  }

  if (baseQuery.isLoading) {
    return <LoadingState message="Loading chart data…" />
  }

  if (baseQuery.isError) {
    return (
      <ErrorState
        title="Unable to load chart data"
        message={baseQuery.error instanceof Error ? baseQuery.error.message : 'Unknown error'}
        onRetry={() => void baseQuery.refetch()}
      />
    )
  }

  const { caseData, partners: loadedPartners, ghostings, caseSymptoms } = baseQuery.data!

  const partnerDataMap = new Map<
    number,
    { relationship: RelationshipSummary | null; symptoms: SymptomEntryRead[] }
  >()
  for (const q of partnerDataQueries) {
    if (q.data) {
      partnerDataMap.set(q.data.partnerId, {
        relationship: q.data.relationship,
        symptoms: q.data.symptoms,
      })
    }
  }

  // Helper: pick primary symptom entry for a person (last in list, matching Streamlit)
  function pickPrimarySymptom(symptoms: SymptomEntryRead[]): SymptomEntryRead | null {
    return symptoms.length > 0 ? symptoms[symptoms.length - 1] : null
  }

  // Build people array: OP first, partners in order
  const opSymptom = pickPrimarySymptom(caseSymptoms as SymptomEntryRead[])
  const opChartType = opSymptom ? classifySymptomType(opSymptom.symptom_type) : null

  const people: PersonData[] = [
    {
      label: `${caseData.patient_name} (OP)`,
      isOp: true,
      symptomType: opChartType,
      symptomOnset: parseDate(opSymptom?.onset_date),
      symptomDuration: opSymptom?.duration_days ?? 0,
      treatmentDate: parseDate(caseData.treatment_date),
      firstExposure: null,
      lastExposure: null,
    },
  ]

  const partnerRefMap: Record<string, string> = {
    OP: `${caseData.patient_name} (OP)`,
  }

  const dataGaps: string[] = []

  if (!opSymptom && !caseData.treatment_date) {
    dataGaps.push('OP has no symptoms or treatment date — timeline will be sparse')
  }

  for (const p of loadedPartners) {
    const pd = partnerDataMap.get(p.id)
    const pSym = pickPrimarySymptom(pd?.symptoms ?? [])
    const pChartType = pSym ? classifySymptomType(pSym.symptom_type) : null
    const rel = pd?.relationship ?? null
    const label = `P${p.partner_number} — ${p.name ?? 'Unnamed'}`

    partnerRefMap[String(p.partner_number)] = label

    let modalities: string[] = []
    if (rel?.exposure_modalities) {
      try {
        const parsed = JSON.parse(rel.exposure_modalities)
        if (Array.isArray(parsed)) modalities = parsed
      } catch {
        modalities = [rel.exposure_modalities]
      }
    }

    people.push({
      label,
      isOp: false,
      symptomType: pChartType,
      symptomOnset: parseDate(pSym?.onset_date),
      symptomDuration: pSym?.duration_days ?? 0,
      treatmentDate: parseDate(p.treatment_date),
      firstExposure: parseDate(rel?.exposure_first_date),
      lastExposure: parseDate(rel?.exposure_last_date),
    })

    if (!modalities.length) {
      // suppress — not always required
    }
    if (!rel?.exposure_first_date) {
      dataGaps.push(
        `P${p.partner_number} (${p.name ?? 'Unnamed'}) has no exposure dates — exposure window cannot be plotted`,
      )
    }
  }

  const partnerQueriesLoading = partnerDataQueries.some((q) => q.isLoading)

  return (
    <section className="stack-lg">
      <header className="panel stack-sm">
        <div>
          <p className="eyebrow">VCA Methodology</p>
          <h2>VCA Timeline</h2>
        </div>
        <p className="muted" style={{ fontSize: '0.875rem' }}>
          Case #{caseData.id} — {caseData.patient_name} ·{' '}
          {loadedPartners.length} partner{loadedPartners.length !== 1 ? 's' : ''} ·{' '}
          {ghostings.length} ghosting record{ghostings.length !== 1 ? 's' : ''}
        </p>
      </header>

      {/* Layer toggles */}
      <div
        className="panel"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1rem',
          alignItems: 'center',
          fontSize: '0.875rem',
        }}
      >
        <span style={{ fontWeight: 600, marginRight: '0.25rem' }}>Show:</span>
        {[
          { label: 'Symptom bars', value: showDurations, set: setShowDurations },
          { label: 'Inoculation points', value: showInoc, set: setShowInoc },
          { label: 'Ghosted lesions', value: showGhosted, set: setShowGhosted },
          { label: 'Critical period', value: showCritical, set: setShowCritical },
          { label: 'Interview period', value: showInterview, set: setShowInterview },
        ].map(({ label, value, set }) => (
          <label key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={value} onChange={(e) => set(e.target.checked)} />
            {label}
          </label>
        ))}
      </div>

      {/* SVG chart */}
      <div
        className="panel"
        style={{ padding: '1rem', overflowX: 'auto' }}
        ref={containerRef}
      >
        {partnerQueriesLoading ? (
          <LoadingState message="Loading partner data…" />
        ) : (
          <VcaTimeline
            people={people}
            ghostings={ghostings}
            partnerRefMap={partnerRefMap}
            containerWidth={Math.max(containerWidth - 32, 600)}
            toggles={{ showDurations, showInoc, showGhosted, showCritical, showInterview }}
          />
        )}
      </div>

      {/* Legend */}
      <div className="panel stack-sm">
        <p className="eyebrow">Chart legend</p>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '0.4rem',
          }}
        >
          {LEGEND_ITEMS.map(({ label, symbol, color }) => (
            <span key={label} style={{ fontSize: '0.85rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{ color, fontSize: '1rem', minWidth: '1.5rem', textAlign: 'center' }}>
                {symbol}
              </span>
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* Data gaps notice */}
      {dataGaps.length > 0 && (
        <div
          className="panel"
          style={{
            borderLeft: '3px solid #ef9f27',
            background: '#fef8ec',
            fontSize: '0.875rem',
          }}
        >
          <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
            {dataGaps.length} data gap{dataGaps.length !== 1 ? 's' : ''} affecting the chart
          </p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {dataGaps.map((g) => (
              <li key={g} style={{ color: '#666', marginBottom: '0.2rem' }}>
                {g}
              </li>
            ))}
          </ul>
          <p style={{ color: '#888', marginTop: '0.5rem', fontSize: '0.8rem' }}>
            Add missing data on the OP form, Partner form, or Ghosting Analysis page.
          </p>
        </div>
      )}
    </section>
  )
}
