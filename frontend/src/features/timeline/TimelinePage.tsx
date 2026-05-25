import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { EmptyState } from '../../components/feedback/EmptyState'
import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
import { useCase } from '../cases/hooks'
import { useCasePartners } from '../partners/hooks'
import { useCreateTimelineEvent, useDeleteTimelineEvent, useTimelineEvents } from './hooks'
import type { TimelineEventRead } from './types'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EVENT_TYPES = [
  'Treatment',
  'Lab work',
  'Interview',
  'Re-interview',
  'Field visit',
  'Phone contact',
  'Other',
]

const EVENT_COLORS: Record<string, string> = {
  Treatment: '#1D9E75',
  'Lab work': '#378ADD',
  Interview: '#534AB7',
  'Re-interview': '#7F77DD',
  'Field visit': '#D85A30',
  'Phone contact': '#BA7517',
  Other: '#888780',
}

function eventColor(type: string): string {
  return EVENT_COLORS[type] ?? '#888780'
}

// ---------------------------------------------------------------------------
// SVG Scatter Timeline
// ---------------------------------------------------------------------------

const CHART_MARGIN = { top: 20, right: 30, bottom: 40, left: 30 }

function ScatterTimeline({
  events,
  subjectLabels,
}: {
  events: TimelineEventRead[]
  subjectLabels: Map<number | null, string>
}) {
  const subjects = Array.from(subjectLabels.values())
  const H = Math.max(200, subjects.length * 60 + CHART_MARGIN.top + CHART_MARGIN.bottom + 20)
  const W = 760

  const allDates = events.map(e => new Date(e.event_date).getTime())
  const minTs = Math.min(...allDates)
  const maxTs = Math.max(...allDates)
  const rangeTs = maxTs - minTs || 1

  const xLeft = CHART_MARGIN.left
  const xRight = W - CHART_MARGIN.right
  const xWidth = xRight - xLeft

  function tsToX(ts: number): number {
    return xLeft + ((ts - minTs) / rangeTs) * xWidth
  }

  function subjectToY(label: string): number {
    const i = subjects.indexOf(label)
    return CHART_MARGIN.top + 30 + i * 60
  }

  const axisDates = [minTs, (minTs + maxTs) / 2, maxTs]

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: '100%', height: 'auto', display: 'block' }}
      aria-label="Event timeline scatter chart"
    >
      {/* Y axis subject labels */}
      {subjects.map((label, i) => {
        const y = CHART_MARGIN.top + 30 + i * 60
        return (
          <g key={label}>
            <line
              x1={xLeft} y1={y} x2={xRight} y2={y}
              stroke="rgba(0,0,0,0.06)"
              strokeWidth={1}
            />
            <text
              x={xLeft - 6}
              y={y}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={11}
              fill="#555"
            >
              {label.length > 18 ? label.slice(0, 16) + '…' : label}
            </text>
          </g>
        )
      })}

      {/* X axis ticks */}
      {axisDates.map(ts => {
        const x = tsToX(ts)
        const label = new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
        return (
          <g key={ts}>
            <line x1={x} y1={H - CHART_MARGIN.bottom} x2={x} y2={H - CHART_MARGIN.bottom + 5} stroke="#999" strokeWidth={1} />
            <text x={x} y={H - CHART_MARGIN.bottom + 16} textAnchor="middle" fontSize={10} fill="#777">
              {label}
            </text>
          </g>
        )
      })}

      {/* X axis baseline */}
      <line
        x1={xLeft} y1={H - CHART_MARGIN.bottom}
        x2={xRight} y2={H - CHART_MARGIN.bottom}
        stroke="#ccc"
        strokeWidth={1}
      />

      {/* Events */}
      {events.map(event => {
        const subject = subjectLabels.get(event.partner_id ?? null) ?? 'OP'
        const x = tsToX(new Date(event.event_date).getTime())
        const y = subjectToY(subject)
        const color = eventColor(event.event_type)
        return (
          <g key={event.id}>
            <circle cx={x} cy={y} r={8} fill={color} opacity={0.85}>
              <title>{`${event.event_date} — ${event.event_type}${event.notes ? `: ${event.notes}` : ''}`}</title>
            </circle>
          </g>
        )
      })}
    </svg>
  )
}

// ---------------------------------------------------------------------------
// Monthly Heatmap
// ---------------------------------------------------------------------------

function MonthlyHeatmap({
  events,
  subjectLabels,
}: {
  events: TimelineEventRead[]
  subjectLabels: Map<number | null, string>
}) {
  // Build month × subject count grid
  const counts = new Map<string, number>() // key: `${subject}|${yearMonth}`
  const allMonths = new Set<string>()
  const subjects = Array.from(subjectLabels.values())

  events.forEach(event => {
    const subject = subjectLabels.get(event.partner_id ?? null) ?? 'OP'
    const ym = event.event_date.slice(0, 7) // YYYY-MM
    allMonths.add(ym)
    const key = `${subject}|${ym}`
    counts.set(key, (counts.get(key) ?? 0) + 1)
  })

  const sortedMonths = Array.from(allMonths).sort()
  const maxCount = Math.max(1, ...Array.from(counts.values()))

  // white → teal scale
  function cellColor(count: number): string {
    if (count === 0) return '#f5f5f0'
    const t = Math.min(count / maxCount, 1)
    const r = Math.round(241 - t * (241 - 8))
    const g = Math.round(239 - t * (239 - 80))
    const b = Math.round(232 - t * (232 - 65))
    return `rgb(${r},${g},${b})`
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table" style={{ minWidth: sortedMonths.length * 60 + 160 }}>
        <thead>
          <tr>
            <th style={{ minWidth: 140 }}>Subject</th>
            {sortedMonths.map(ym => (
              <th key={ym} style={{ minWidth: 56, textAlign: 'center' }}>
                {ym.replace('-', '‑')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {subjects.map(subject => (
            <tr key={subject}>
              <td style={{ fontWeight: 500, fontSize: '0.85rem' }}>{subject}</td>
              {sortedMonths.map(ym => {
                const count = counts.get(`${subject}|${ym}`) ?? 0
                return (
                  <td
                    key={ym}
                    style={{
                      textAlign: 'center',
                      background: cellColor(count),
                      fontWeight: count > 0 ? 600 : 400,
                      color: count > 0 ? '#082e26' : '#bbb',
                      fontSize: '0.85rem',
                    }}
                    title={`${subject} — ${ym}: ${count} event${count !== 1 ? 's' : ''}`}
                  >
                    {count || '·'}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Add Event Form
// ---------------------------------------------------------------------------

function AddEventForm({
  caseId,
  subjectLabels,
}: {
  caseId: number
  subjectLabels: Map<number | null, string>
}) {
  const createMutation = useCreateTimelineEvent(caseId)
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [partnerId, setPartnerId] = useState<string>('null')
  const [eventType, setEventType] = useState(EVENT_TYPES[0])
  const [notes, setNotes] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await createMutation.mutateAsync({
      event_date: date,
      event_type: eventType,
      notes: notes.trim() || null,
      partner_id: partnerId === 'null' ? null : Number(partnerId),
    })
    setNotes('')
  }

  const subjectOptions = Array.from(subjectLabels.entries())

  return (
    <form className="panel stack-md" onSubmit={handleSubmit}>
      <div>
        <p className="eyebrow">Add event</p>
      </div>

      <label className="field">
        <span>Date</span>
        <input type="date" value={date} onChange={e => setDate(e.target.value)} required />
      </label>

      <label className="field">
        <span>Subject</span>
        <select value={partnerId} onChange={e => setPartnerId(e.target.value)}>
          {subjectOptions.map(([id, label]) => (
            <option key={String(id)} value={String(id)}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Event type</span>
        <select value={eventType} onChange={e => setEventType(e.target.value)}>
          {EVENT_TYPES.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Notes</span>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={3}
          placeholder="Optional…"
        />
      </label>

      {createMutation.isError && (
        <p className="error-text">{createMutation.error.message}</p>
      )}

      <button
        className="button button-primary"
        type="submit"
        disabled={createMutation.isPending}
      >
        {createMutation.isPending ? 'Adding…' : '+ Add event'}
      </button>

      <div style={{ borderTop: '1px solid #eee', paddingTop: '0.75rem' }}>
        <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Event types</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {Object.entries(EVENT_COLORS).map(([type, color]) => (
            <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: 12, height: 12, borderRadius: '50%', background: color, flexShrink: 0 }} />
              <span style={{ fontSize: '0.8rem' }}>{type}</span>
            </div>
          ))}
        </div>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export function TimelinePage() {
  const { caseId } = useParams()
  const parsedCaseId = Number(caseId)
  const [activeTab, setActiveTab] = useState<'chart' | 'table'>('chart')

  const caseQuery = useCase(parsedCaseId)
  const partnersQuery = useCasePartners(parsedCaseId)
  const eventsQuery = useTimelineEvents(parsedCaseId)
  const deleteMutation = useDeleteTimelineEvent(parsedCaseId)
  const createMutation = useCreateTimelineEvent(parsedCaseId)

  if (!Number.isInteger(parsedCaseId) || parsedCaseId <= 0) {
    return <ErrorState title="Invalid case" message="The case id is not valid." />
  }

  if (eventsQuery.isLoading || caseQuery.isLoading || partnersQuery.isLoading) {
    return <LoadingState message="Loading timeline…" />
  }

  if (eventsQuery.isError) {
    return <ErrorState title="Unable to load timeline" message={eventsQuery.error.message} onRetry={() => void eventsQuery.refetch()} />
  }

  const caseData = caseQuery.data
  const partners = partnersQuery.data ?? []
  const events = eventsQuery.data ?? []

  // Build subject label map: partner_id (null = OP) → display label
  const subjectLabels = new Map<number | null, string>()
  subjectLabels.set(null, `OP — ${caseData?.patient_name ?? 'Unknown'}`)
  partners.forEach(p => {
    subjectLabels.set(p.id, `Partner ${p.partner_number} — ${p.name ?? 'Unnamed'}`)
  })

  // Summary metrics
  const allDates = events.map(e => e.event_date).sort()
  const earliest = allDates[0] ?? null
  const latest = allDates[allDates.length - 1] ?? null
  const spanDays =
    earliest && latest
      ? Math.round((new Date(latest).getTime() - new Date(earliest).getTime()) / 86400000)
      : null

  // Auto-seed helper: create treatment-date events from case + partners
  async function handleSeedTreatmentDates() {
    const seedJobs: Array<{ event_date: string; partner_id: number | null }> = []
    if (caseData?.treatment_date) {
      seedJobs.push({ event_date: caseData.treatment_date, partner_id: null })
    }
    partners.forEach(p => {
      if (p.treatment_date) seedJobs.push({ event_date: p.treatment_date, partner_id: p.id })
    })
    for (const job of seedJobs) {
      await createMutation.mutateAsync({
        event_date: job.event_date,
        event_type: 'Treatment',
        notes: 'Imported from case record',
        partner_id: job.partner_id,
      })
    }
  }

  return (
    <section className="stack-lg">
      {/* Header */}
      <header className="panel stack-sm">
        <div>
          <p className="eyebrow">Timeline</p>
          <h2>Case timeline</h2>
        </div>
        {events.length === 0 && (caseData?.treatment_date || partners.some(p => p.treatment_date)) && (
          <button
            className="button"
            onClick={handleSeedTreatmentDates}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? 'Importing…' : 'Import treatment dates'}
          </button>
        )}
      </header>

      {/* Summary metrics */}
      {events.length > 0 && (
        <div className="two-column-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
          <div className="panel stack-xs">
            <p className="eyebrow">Total events</p>
            <p style={{ fontSize: '1.75rem', fontWeight: 700 }}>{events.length}</p>
          </div>
          <div className="panel stack-xs">
            <p className="eyebrow">Earliest</p>
            <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>{earliest ?? '—'}</p>
          </div>
          <div className="panel stack-xs">
            <p className="eyebrow">Latest</p>
            <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>{latest ?? '—'}</p>
          </div>
          <div className="panel stack-xs">
            <p className="eyebrow">Span (days)</p>
            <p style={{ fontSize: '1.75rem', fontWeight: 700 }}>{spanDays ?? '—'}</p>
          </div>
        </div>
      )}

      {/* Main content: chart + form */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '1.5rem', alignItems: 'start' }}>
        {/* Left: chart / table */}
        <div className="stack-md">
          {events.length === 0 ? (
            <div className="panel">
              <EmptyState
                title="No timeline events"
                message="Add the first event using the form, or import treatment dates above."
              />
            </div>
          ) : (
            <>
              {/* Tab bar */}
              <nav className="tab-nav" aria-label="Timeline views">
                {(['chart', 'table'] as const).map(tab => (
                  <button
                    key={tab}
                    className={activeTab === tab ? 'tab-link tab-link-active' : 'tab-link'}
                    onClick={() => setActiveTab(tab)}
                    type="button"
                  >
                    {tab === 'chart' ? 'Timeline view' : 'Event table'}
                  </button>
                ))}
              </nav>

              {activeTab === 'chart' && (
                <div className="panel stack-sm">
                  <p className="eyebrow">Events over time</p>
                  <ScatterTimeline events={events} subjectLabels={subjectLabels} />
                  <div style={{ marginTop: '1rem' }}>
                    <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Monthly activity</p>
                    <MonthlyHeatmap events={events} subjectLabels={subjectLabels} />
                  </div>
                </div>
              )}

              {activeTab === 'table' && (
                <div className="panel table-panel stack-sm">
                  <p className="eyebrow">All events</p>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Subject</th>
                        <th>Event type</th>
                        <th>Notes</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...events]
                        .sort((a, b) => a.event_date.localeCompare(b.event_date))
                        .map(event => {
                          const subject = subjectLabels.get(event.partner_id ?? null) ?? 'OP'
                          return (
                            <tr key={event.id}>
                              <td style={{ whiteSpace: 'nowrap' }}>{event.event_date}</td>
                              <td>{subject}</td>
                              <td>
                                <span
                                  style={{
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    borderRadius: 4,
                                    background: eventColor(event.event_type),
                                    color: '#fff',
                                    fontSize: '0.8rem',
                                  }}
                                >
                                  {event.event_type}
                                </span>
                              </td>
                              <td style={{ color: '#666', fontSize: '0.85rem' }}>{event.notes ?? '—'}</td>
                              <td>
                                <button
                                  className="button"
                                  style={{ padding: '2px 8px', fontSize: '0.8rem' }}
                                  onClick={() => void deleteMutation.mutateAsync(event.id)}
                                  disabled={deleteMutation.isPending}
                                >
                                  Remove
                                </button>
                              </td>
                            </tr>
                          )
                        })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>

        {/* Right: add event form */}
        <AddEventForm caseId={parsedCaseId} subjectLabels={subjectLabels} />
      </div>

      {/* Partner treatment status */}
      {partners.length > 0 && (
        <div className="panel table-panel stack-sm">
          <div>
            <p className="eyebrow">Partners</p>
            <h3>Treatment status</h3>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>Treatment date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {partners.map(p => {
                const treated = Boolean(p.treatment_date)
                return (
                  <tr key={p.id}>
                    <td>{p.partner_number}</td>
                    <td>{p.name ?? '—'}</td>
                    <td>{p.treatment_date ?? 'Pending'}</td>
                    <td>
                      <span style={{
                        color: treated ? '#0F6E56' : '#854F0B',
                        fontWeight: 500,
                      }}>
                        {treated ? 'Treated' : 'Pending'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {partners.some(p => !p.treatment_date) && (
            <p style={{ color: '#854F0B', fontSize: '0.875rem' }}>
              {partners.filter(p => !p.treatment_date).length} partner(s) still pending treatment.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
