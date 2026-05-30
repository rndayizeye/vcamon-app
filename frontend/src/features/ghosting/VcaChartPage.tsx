import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useQueries } from '@tanstack/react-query'

import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
import { formatDate } from '../../lib/utils'
import { getCase } from '../cases/api'
import { getCasePartnerRelationship, getPartnersForCase } from '../partners/api'
import { listCaseSymptoms, listPartnerSymptoms } from '../symptoms/api'
import { listCaseLabs, listPartnerLabs } from '../labs/api'
import { listCaseGhostings } from './api'
import type { GhostingRecord, PartnerSummary, RelationshipSummary } from './types'
import type { CaseRead } from '../cases/types'
import type { SymptomEntryRead } from '../symptoms/types'
import type { LabResultEntryRead } from '../labs/types'

// ---------------------------------------------------------------------------
// Clinical constants (mirrored from app/utils/clinical.py)
// ---------------------------------------------------------------------------

const INCUBATION = { min: 10, avg: 21, max: 90 }
const PRIMARY = { min: 7, avg: 21, max: 35 }
const LATENCY = { min: 0, avg: 28, max: 70 }
const INTERVIEW_PERIOD_PRIMARY_DAYS = 125
const INTERVIEW_PERIOD_SECONDARY_DAYS = 237

// ---------------------------------------------------------------------------
// Chart colors
// ---------------------------------------------------------------------------

const COLORS = {
  primaryOnset: '#E24B4A',
  primaryBar: '#E24B4A',
  secondaryOnset: '#7F77DD',
  secondaryBar: '#7F77DD',
  exposurePartner: '#7F77DD',
  exposureOp: '#EF9F27',
  critical: '#1D9E75',
  inoculation: '#1D9E75',
  infectiousWindow: '#1D9E75',
  ghostedSource: '#EF9F27',
  ghostedSpread: '#D85A30',
  treatment: '#2C2C2A',
  interview: '#1D9E75',
  nonReactiveLab: '#9E7BC4',
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
const ROW_HEIGHT = 100
const MIN_CHART_SPAN_MS = 365 * 24 * 60 * 60 * 1000

// Sub-track offsets relative to row center y
const Y_EXPOSURE = -28
const Y_SYMPTOM = 0
const Y_INOC = 24
const Y_GHOST = 38

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

function addMonths(d: Date, months: number): Date {
  const r = new Date(d)
  r.setMonth(r.getMonth() + months)
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
// Symptom helpers
// ---------------------------------------------------------------------------

type SymptomChartType = 'Primary Chancre' | 'Secondary Rash/Lesions' | 'Historical Primary'

type SymptomBar = {
  chartType: SymptomChartType
  onset: Date
  durationDays: number
  typeName: string
}

function classificationToChartType(classification: string | null): SymptomChartType | null {
  if (classification === 'Primary') return 'Primary Chancre'
  if (classification === 'Secondary') return 'Secondary Rash/Lesions'
  return null
}

function buildSymptomBars(
  entries: SymptomEntryRead[],
  historicalPrimaryChancre: boolean | null,
  historicalPrimaryDate: string | null,
): SymptomBar[] {
  const bars: SymptomBar[] = []
  for (const entry of entries) {
    if (!entry.onset_date) continue
    const chartType = classificationToChartType(entry.classification)
    if (!chartType) continue
    const onset = parseDate(entry.onset_date)
    if (!onset) continue
    bars.push({
      chartType,
      onset,
      durationDays: entry.duration_days ?? 0,
      typeName: entry.symptom_type,
    })
  }
  if (historicalPrimaryChancre && historicalPrimaryDate) {
    const onset = parseDate(historicalPrimaryDate)
    if (onset) {
      bars.push({ chartType: 'Historical Primary', onset, durationDays: 0, typeName: 'Historical Primary' })
    }
  }
  return bars
}

function getInoculationPoints(
  chartType: SymptomChartType,
  onset: Date,
  durationDays: number,
): { min: Date; avg: Date; max: Date } | null {
  const dur = durationDays > 0 ? durationDays : PRIMARY.avg
  if (chartType === 'Primary Chancre' || chartType === 'Historical Primary') {
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

// Pick the single key symptom for inoculation: primary > historical > first secondary
function getPersonKeySymptom(symptoms: SymptomBar[]): SymptomBar | null {
  return (
    symptoms.find((s) => s.chartType === 'Primary Chancre') ??
    symptoms.find((s) => s.chartType === 'Historical Primary') ??
    symptoms.find((s) => s.chartType === 'Secondary Rash/Lesions') ??
    null
  )
}

function symptomColor(chartType: SymptomChartType): { onset: string; bar: string } {
  if (chartType === 'Secondary Rash/Lesions') {
    return { onset: COLORS.secondaryOnset, bar: COLORS.secondaryBar }
  }
  return { onset: COLORS.primaryOnset, bar: COLORS.primaryBar }
}

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

// ▲ upward (symptom onset)
function upTrianglePoints(cx: number, cy: number, r: number): string {
  return `${cx},${cy - r} ${cx - r},${cy + r} ${cx + r},${cy + r}`
}

// ► right-pointing (max inoculation — earliest calendar date)
function rightTrianglePoints(cx: number, cy: number, r: number): string {
  return `${cx + r},${cy} ${cx - r},${cy - r} ${cx - r},${cy + r}`
}

// ◄ left-pointing (min inoculation — latest calendar date)
function leftTrianglePoints(cx: number, cy: number, r: number): string {
  return `${cx - r},${cy} ${cx + r},${cy - r} ${cx + r},${cy + r}`
}

// ---------------------------------------------------------------------------
// Chart data types
// ---------------------------------------------------------------------------

type PersonData = {
  label: string
  isOp: boolean
  symptoms: SymptomBar[]
  labs: LabResultEntryRead[]
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
    showGhostedMap: Record<number, boolean>
    showCritical: boolean
    showInterview: boolean
    showLabLines: boolean
  }
}) {
  const allDates: Date[] = []
  for (const p of people) {
    if (p.treatmentDate) allDates.push(p.treatmentDate)
    if (p.firstExposure) allDates.push(p.firstExposure)
    if (p.lastExposure) allDates.push(p.lastExposure)
    for (const sym of p.symptoms) {
      allDates.push(sym.onset)
      const dur = sym.durationDays > 0 ? sym.durationDays : PRIMARY.avg
      allDates.push(addDays(sym.onset, dur))
    }
    const keySym = getPersonKeySymptom(p.symptoms)
    if (keySym) {
      const dur = keySym.durationDays > 0 ? keySym.durationDays : PRIMARY.avg
      const inoc = getInoculationPoints(keySym.chartType, keySym.onset, dur)
      if (inoc) allDates.push(inoc.max)
    }
    // Labs render at their x position but don't anchor the axis range
  }
  for (const g of ghostings) {
    const dates = parseGhostingDates(g.notes)
    if (dates) allDates.push(...dates)
  }

  const today = new Date()
  const rawMin =
    allDates.length > 0
      ? addDays(new Date(Math.min(...allDates.map((d) => d.getTime()))), -30)
      : addDays(today, -365)
  const rawMax =
    allDates.length > 0
      ? addDays(new Date(Math.max(...allDates.map((d) => d.getTime()))), 30)
      : today

  let minDate = rawMin
  let maxDate = rawMax
  const rawSpan = rawMax.getTime() - rawMin.getTime()
  if (rawSpan < MIN_CHART_SPAN_MS) {
    const midMs = (rawMin.getTime() + rawMax.getTime()) / 2
    minDate = new Date(midMs - MIN_CHART_SPAN_MS / 2)
    maxDate = new Date(midMs + MIN_CHART_SPAN_MS / 2)
  }

  // When a treatment date exists, ensure the axis covers 9 months before → 3 months after it
  const txDate = people.find((p) => p.isOp)?.treatmentDate ?? people.find((p) => p.treatmentDate)?.treatmentDate ?? null
  if (txDate) {
    minDate = new Date(Math.min(minDate.getTime(), addMonths(txDate, -9).getTime()))
    maxDate = new Date(Math.max(maxDate.getTime(), addMonths(txDate, 3).getTime()))
  }

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
        const yExp = y + Y_EXPOSURE
        const yInoc = y + Y_INOC
        const keySym = getPersonKeySymptom(p.symptoms)

        return (
          <g key={`person-${i}`}>
            {/* Non-reactive lab vertical lines */}
            {toggles.showLabLines &&
              p.labs
                .filter((l) => l.titer === 'Non-Reactive' || l.result === 'Non-reactive')
                .map((lab, li) => {
                  const d = parseDate(lab.collection_date)
                  if (!d) return null
                  return (
                    <line
                      key={`lab-nr-${li}`}
                      x1={dateToX(d)}
                      y1={y - ROW_HEIGHT / 2 + 6}
                      x2={dateToX(d)}
                      y2={y + ROW_HEIGHT / 2 - 6}
                      stroke={COLORS.nonReactiveLab}
                      strokeWidth={1.5}
                      strokeDasharray="3 3"
                      opacity={0.7}
                    >
                      <title>
                        {p.label} — Non-reactive {lab.test_type}:{' '}
                        {d.toISOString().slice(0, 10)}
                      </title>
                    </line>
                  )
                })}

            {/* Exposure window (Y_EXPOSURE sub-track) */}
            {p.firstExposure &&
              p.lastExposure &&
              (() => {
                const color = p.isOp ? COLORS.exposureOp : COLORS.exposurePartner
                const dash = p.isOp ? '3 5' : '8 5'
                const label = p.isOp ? 'OP elicited exposure' : 'Partner reported exposure'
                return (
                  <line
                    x1={dateToX(p.firstExposure)}
                    y1={yExp}
                    x2={dateToX(p.lastExposure)}
                    y2={yExp}
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

            {/* Symptom bars (on the inoculation track) */}
            {toggles.showDurations && p.symptoms.map((sym, si) => {
              const dur = sym.durationDays > 0 ? sym.durationDays : PRIMARY.avg
              const { bar: barColor } = symptomColor(sym.chartType)
              const xOnset = dateToX(sym.onset)
              const xEnd = dateToX(addDays(sym.onset, dur))
              const barPx = xEnd - xOnset
              const stageLabel = sym.chartType === 'Secondary Rash/Lesions' ? '2°' : '1°'
              return (
                <g key={`sym-${si}`}>
                  <line
                    x1={xOnset}
                    y1={yInoc}
                    x2={xEnd}
                    y2={yInoc}
                    stroke={barColor}
                    strokeWidth={7}
                    strokeLinecap="round"
                  >
                    <title>
                      {p.label} — {sym.typeName} ({sym.chartType}) · Onset{' '}
                      {sym.onset.toISOString().slice(0, 10)} · Est. end{' '}
                      {addDays(sym.onset, dur).toISOString().slice(0, 10)}
                    </title>
                  </line>
                  {barPx > 18 && (
                    <text
                      x={xOnset + 3}
                      y={yInoc + 3}
                      fontSize={7}
                      fontWeight={700}
                      fill="white"
                      style={{ userSelect: 'none', pointerEvents: 'none' }}
                    >
                      {stageLabel}
                    </text>
                  )}
                </g>
              )
            })}

            {/* Treatment date: vertical line spanning row + "Rx" label */}
            {p.treatmentDate &&
              (() => {
                const xTx = dateToX(p.treatmentDate)
                const halfH = ROW_HEIGHT / 2 - 6
                return (
                  <g>
                    <line
                      x1={xTx}
                      y1={y - halfH}
                      x2={xTx}
                      y2={y + halfH}
                      stroke={COLORS.treatment}
                      strokeWidth={2}
                    >
                      <title>
                        {p.label} — Treatment: {p.treatmentDate.toISOString().slice(0, 10)}
                      </title>
                    </line>
                    <text
                      x={xTx + 3}
                      y={y - halfH + 10}
                      fontSize={9}
                      fontWeight={700}
                      fill={COLORS.treatment}
                      style={{ userSelect: 'none', pointerEvents: 'none' }}
                    >
                      Rx
                    </text>
                  </g>
                )
              })()}

            {/* Inoculation: one set per person at Y_INOC sub-track */}
            {toggles.showInoc &&
              keySym &&
              (() => {
                const dur = keySym.durationDays > 0 ? keySym.durationDays : PRIMARY.avg
                const pts = getInoculationPoints(keySym.chartType, keySym.onset, dur)
                if (!pts) return null
                const isPrimary = keySym.chartType !== 'Secondary Rash/Lesions'

                return (
                  <g>
                    {/* Infectious window: max inoculation → treatment date */}
                    {p.treatmentDate && (
                      <line
                        x1={dateToX(pts.max)}
                        y1={yInoc}
                        x2={dateToX(p.treatmentDate)}
                        y2={yInoc}
                        stroke={COLORS.infectiousWindow}
                        strokeWidth={2}
                        strokeDasharray="6 3"
                        opacity={0.4}
                      >
                        <title>
                          Infectious window: {pts.max.toISOString().slice(0, 10)} →{' '}
                          {p.treatmentDate.toISOString().slice(0, 10)}
                        </title>
                      </line>
                    )}

                    {/* ▲ avg inoculation (always shown) */}
                    <polygon
                      points={upTrianglePoints(dateToX(pts.avg), yInoc, 7)}
                      fill={COLORS.inoculation}
                    >
                      <title>
                        {p.label} — {keySym.typeName}: Avg inoculation:{' '}
                        {pts.avg.toISOString().slice(0, 10)}
                      </title>
                    </polygon>

                    {/* ► max and ◄ min (primary only) */}
                    {isPrimary && (
                      <>
                        <polygon
                          points={rightTrianglePoints(dateToX(pts.max), yInoc, 7)}
                          fill={COLORS.inoculation}
                          opacity={0.75}
                        >
                          <title>
                            {p.label} — Max inoculation (earliest):{' '}
                            {pts.max.toISOString().slice(0, 10)}
                          </title>
                        </polygon>
                        <polygon
                          points={leftTrianglePoints(dateToX(pts.min), yInoc, 7)}
                          fill={COLORS.inoculation}
                          opacity={0.75}
                        >
                          <title>
                            {p.label} — Min inoculation (latest):{' '}
                            {pts.min.toISOString().slice(0, 10)}
                          </title>
                        </polygon>
                      </>
                    )}
                  </g>
                )
              })()}

            {/* Critical period */}
            {toggles.showCritical &&
              keySym &&
              (() => {
                const dur = keySym.durationDays > 0 ? keySym.durationDays : PRIMARY.avg
                const pts = getInoculationPoints(keySym.chartType, keySym.onset, dur)
                const critStart = pts
                  ? pts.max
                  : addDays(keySym.onset, -(INCUBATION.max + PRIMARY.max))
                const critEnd = p.treatmentDate ?? maxDate
                const x1 = dateToX(critStart)
                const x2 = dateToX(critEnd)
                const lineY = y - 14
                return (
                  <g>
                    <line
                      x1={x1}
                      y1={lineY}
                      x2={x2}
                      y2={lineY}
                      stroke={COLORS.critical}
                      strokeWidth={3}
                      strokeLinecap="round"
                    >
                      <title>
                        {p.label} — Critical period: {critStart.toISOString().slice(0, 10)} →{' '}
                        {critEnd.toISOString().slice(0, 10)}
                      </title>
                    </line>
                    {/* End-cap ticks */}
                    <line x1={x1} y1={lineY - 4} x2={x1} y2={lineY + 4} stroke={COLORS.critical} strokeWidth={1.5} />
                    <line x1={x2} y1={lineY - 4} x2={x2} y2={lineY + 4} stroke={COLORS.critical} strokeWidth={1.5} />
                    {(x2 - x1) > 50 && (
                      <text
                        x={x1 + 3}
                        y={lineY + 11}
                        fontSize={7}
                        fill={COLORS.critical}
                        opacity={0.85}
                        style={{ userSelect: 'none', pointerEvents: 'none' }}
                      >
                        Critical
                      </text>
                    )}
                  </g>
                )
              })()}

            {/* Interview period */}
            {toggles.showInterview &&
              keySym &&
              (() => {
                const isPrimary =
                  keySym.chartType === 'Primary Chancre' ||
                  keySym.chartType === 'Historical Primary'
                const days = isPrimary
                  ? INTERVIEW_PERIOD_PRIMARY_DAYS
                  : INTERVIEW_PERIOD_SECONDARY_DAYS
                const intStart = addDays(keySym.onset, -days)
                const intEnd = p.treatmentDate ?? maxDate
                const x1 = dateToX(intStart)
                const x2 = dateToX(intEnd)
                const lineY = y + 14
                return (
                  <g>
                    <line
                      x1={x1}
                      y1={lineY}
                      x2={x2}
                      y2={lineY}
                      stroke={COLORS.interview}
                      strokeWidth={2}
                      strokeDasharray="12 4"
                      strokeLinecap="round"
                    >
                      <title>
                        {p.label} — Interview period: {intStart.toISOString().slice(0, 10)} →{' '}
                        {intEnd.toISOString().slice(0, 10)}
                      </title>
                    </line>
                    {/* End-cap ticks */}
                    <line x1={x1} y1={lineY - 4} x2={x1} y2={lineY + 4} stroke={COLORS.interview} strokeWidth={1.5} />
                    <line x1={x2} y1={lineY - 4} x2={x2} y2={lineY + 4} stroke={COLORS.interview} strokeWidth={1.5} />
                    {(x2 - x1) > 50 && (
                      <text
                        x={x1 + 3}
                        y={lineY - 6}
                        fontSize={7}
                        fill={COLORS.interview}
                        opacity={0.85}
                        style={{ userSelect: 'none', pointerEvents: 'none' }}
                      >
                        Interview
                      </text>
                    )}
                  </g>
                )
              })()}
          </g>
        )
      })}

      {/* Ghosted lesions (on the Y_INOC symptom track, transparent) */}
      {ghostings.map((g, gi) => {
          if (!toggles.showGhostedMap[gi]) return null
          const dates = parseGhostingDates(g.notes)
          if (!dates) return null
          const [gOnset, gEnd] = dates
          const yRef = partnerRefMap[g.to_ref ?? ''] ?? g.to_ref ?? ''
          const personIdx = people.findIndex((p) => p.label === yRef)
          if (personIdx < 0) return null
          const yGhost = rowY(personIdx) + Y_INOC
          const isSource = (g.ghosting_type ?? '').toLowerCase().includes('source')
          const color = isSource ? COLORS.ghostedSource : COLORS.ghostedSpread
          const gLabel = isSource ? 'Ghosted source' : 'Ghosted spread'
          const fromLabel = partnerRefMap[g.from_ref ?? ''] ?? g.from_ref ?? '?'

          return (
            <g key={`ghost-${gi}`} opacity={0.45}>
              <line
                x1={dateToX(gOnset)}
                y1={yGhost}
                x2={dateToX(gEnd)}
                y2={yGhost}
                stroke={color}
                strokeWidth={4}
                strokeDasharray="10 4 3 4"
                strokeLinecap="round"
              >
                <title>
                  {gLabel}: {gOnset.toISOString().slice(0, 10)} →{' '}
                  {gEnd.toISOString().slice(0, 10)} · From: {fromLabel}
                </title>
              </line>
              {[gOnset, gEnd].map((d, j) => (
                <circle
                  key={j}
                  cx={dateToX(d)}
                  cy={yGhost}
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
  { label: 'Primary symptom', symbol: '━', color: COLORS.primaryBar },
  { label: 'Secondary symptom', symbol: '━', color: COLORS.secondaryBar },
  { label: 'Inoculation avg (▲), max (►), min (◄)', symbol: '▲', color: COLORS.inoculation },
  { label: 'Infectious window (max inoc → Rx)', symbol: '╌', color: COLORS.infectiousWindow },
  { label: 'Treatment date', symbol: '│', color: COLORS.treatment },
  { label: 'Critical period (max inoc → Rx)', symbol: '━', color: COLORS.critical },
  { label: 'Interview period (onset − days → Rx)', symbol: '╌', color: COLORS.interview },
  { label: 'Partner exposure window', symbol: '╌', color: COLORS.exposurePartner },
  { label: 'OP elicited exposure', symbol: '·····', color: COLORS.exposureOp },
  { label: 'Ghosted source lesion', symbol: '╌·╌', color: COLORS.ghostedSource },
  { label: 'Ghosted spread lesion', symbol: '╌·╌', color: COLORS.ghostedSpread },
  { label: 'Non-reactive lab', symbol: '╎', color: COLORS.nonReactiveLab },
]

// ---------------------------------------------------------------------------
// VcaChartPage
// ---------------------------------------------------------------------------

export function VcaChartPage() {
  const { caseId } = useParams()
  const parsedCaseId = Number(caseId)

  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(() =>
    typeof window !== 'undefined' ? Math.max(window.innerWidth - 260, 600) : 900,
  )

  const [showDurations, setShowDurations] = useState(true)
  const [showInoc, setShowInoc] = useState(true)
  const [ghostingToggles, setGhostingToggles] = useState<Record<number, boolean>>({})
  const [showCritical, setShowCritical] = useState(true)
  const [showInterview, setShowInterview] = useState(true)
  const [showLabLines, setShowLabLines] = useState(true)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      setContainerWidth(entries[0].contentRect.width)
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const baseQuery = useQuery({
    queryKey: ['cases', parsedCaseId, 'vca-chart-base'],
    queryFn: async () => {
      const [caseData, partners, ghostings, caseSymptoms, caseLabs] = await Promise.all([
        getCase(parsedCaseId) as Promise<CaseRead>,
        getPartnersForCase(parsedCaseId) as Promise<PartnerSummary[]>,
        listCaseGhostings(parsedCaseId),
        listCaseSymptoms(parsedCaseId),
        listCaseLabs(parsedCaseId) as Promise<LabResultEntryRead[]>,
      ])
      return { caseData, partners, ghostings, caseSymptoms, caseLabs }
    },
    enabled: parsedCaseId > 0,
  })

  const partners = baseQuery.data?.partners ?? []

  const loadedGhostings = baseQuery.data?.ghostings
  useEffect(() => {
    if (!loadedGhostings) return
    setGhostingToggles((prev) => {
      const next = { ...prev }
      loadedGhostings.forEach((_, i) => {
        if (!(i in next)) next[i] = true
      })
      return next
    })
  }, [loadedGhostings])

  const partnerDataQueries = useQueries({
    queries: partners.map((p) => ({
      queryKey: ['cases', parsedCaseId, 'partners', p.id, 'chart-data'],
      queryFn: async () => {
        const [relationship, symptoms, labs] = await Promise.all([
          (getCasePartnerRelationship(parsedCaseId, p.id) as Promise<RelationshipSummary>).catch(
            () => null,
          ),
          listPartnerSymptoms(p.id) as Promise<SymptomEntryRead[]>,
          listPartnerLabs(p.id) as Promise<LabResultEntryRead[]>,
        ])
        return { partnerId: p.id, relationship, symptoms, labs }
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

  const { caseData, partners: loadedPartners, ghostings, caseSymptoms, caseLabs } = baseQuery.data!

  const partnerDataMap = new Map<
    number,
    {
      relationship: RelationshipSummary | null
      symptoms: SymptomEntryRead[]
      labs: LabResultEntryRead[]
    }
  >()
  for (const q of partnerDataQueries) {
    if (q.data) {
      partnerDataMap.set(q.data.partnerId, {
        relationship: q.data.relationship,
        symptoms: q.data.symptoms,
        labs: q.data.labs,
      })
    }
  }

  const opSymptomBars = buildSymptomBars(
    caseSymptoms as SymptomEntryRead[],
    caseData.historical_primary_chancre ?? null,
    caseData.historical_primary_date ?? null,
  )

  const people: PersonData[] = [
    {
      label: `${caseData.patient_name} (OP)`,
      isOp: true,
      symptoms: opSymptomBars,
      labs: caseLabs,
      treatmentDate: parseDate(caseData.treatment_date),
      firstExposure: null,
      lastExposure: null,
    },
  ]

  const partnerRefMap: Record<string, string> = {
    OP: `${caseData.patient_name} (OP)`,
  }

  const dataGaps: string[] = []

  if (opSymptomBars.length === 0 && !caseData.treatment_date) {
    dataGaps.push('OP has no symptoms or treatment date — timeline will be sparse')
  }

  for (const p of loadedPartners) {
    const pd = partnerDataMap.get(p.id)
    const rel = pd?.relationship ?? null
    const label = `P${p.partner_number} — ${p.name ?? 'Unnamed'}`

    partnerRefMap[String(p.partner_number)] = label

    const partnerSymptomBars = buildSymptomBars(
      pd?.symptoms ?? [],
      p.historical_primary_chancre ?? null,
      p.historical_primary_date ?? null,
    )

    people.push({
      label,
      isOp: false,
      symptoms: partnerSymptomBars,
      labs: pd?.labs ?? [],
      treatmentDate: parseDate(p.treatment_date),
      firstExposure: parseDate(rel?.exposure_first_date),
      lastExposure: parseDate(rel?.exposure_last_date),
    })

    if (!rel?.exposure_first_date) {
      dataGaps.push(
        `P${p.partner_number} (${p.name ?? 'Unnamed'}) has no exposure dates — exposure window cannot be plotted`,
      )
    }
  }

  const partnerQueriesLoading = partnerDataQueries.some((q) => q.isLoading)

  const totalPrimary = people.reduce(
    (n, p) => n + p.symptoms.filter((s) => s.chartType !== 'Secondary Rash/Lesions').length,
    0,
  )
  const totalSecondary = people.reduce(
    (n, p) => n + p.symptoms.filter((s) => s.chartType === 'Secondary Rash/Lesions').length,
    0,
  )

  return (
    <section className="stack-lg">
      <header className="panel stack-sm">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <p className="eyebrow">VCA Methodology</p>
            <h2>VCA Timeline</h2>
          </div>
          <button
            className="button no-print"
            type="button"
            onClick={() => window.print()}
            style={{ flexShrink: 0 }}
          >
            Print / Export PDF
          </button>
        </div>

        {/* Print-only case summary — hidden on screen, rendered in PDF header */}
        <dl
          className="print-only"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, auto)',
            gap: '0 2.5rem',
            fontSize: '0.9rem',
            borderTop: '1px solid #ccc',
            paddingTop: '0.6rem',
            marginTop: '0.25rem',
          }}
        >
          <div>
            <dt style={{ fontWeight: 600 }}>Patient</dt>
            <dd>{caseData.patient_name}</dd>
          </div>
          <div>
            <dt style={{ fontWeight: 600 }}>Diagnosis (LOT)</dt>
            <dd>{caseData.lot || '—'}</dd>
          </div>
          <div>
            <dt style={{ fontWeight: 600 }}>Treatment date</dt>
            <dd>{formatDate(caseData.treatment_date)}</dd>
          </div>
          <div>
            <dt style={{ fontWeight: 600 }}>Partners</dt>
            <dd>{loadedPartners.length}</dd>
          </div>
        </dl>
      </header>

      {/* Layer toggles */}
      <div
        className="panel no-print"
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
          { label: 'Symptoms', value: showDurations, set: setShowDurations },
          { label: 'Inoculation points', value: showInoc, set: setShowInoc },
          { label: 'Critical period', value: showCritical, set: setShowCritical },
          { label: 'Interview period', value: showInterview, set: setShowInterview },
          { label: 'Non-reactive labs', value: showLabLines, set: setShowLabLines },
        ].map(({ label, value, set }) => (
          <label
            key={label}
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}
          >
            <input type="checkbox" checked={value} onChange={(e) => set(e.target.checked)} />
            {label}
          </label>
        ))}
        {ghostings.map((g, gi) => {
          const isSource = (g.ghosting_type ?? '').toLowerCase().includes('source')
          const gType = isSource ? 'source' : 'spread'
          const fromLabel = partnerRefMap[g.from_ref ?? ''] ?? g.from_ref ?? '?'
          const toLabel = partnerRefMap[g.to_ref ?? ''] ?? g.to_ref ?? '?'
          return (
            <label
              key={`ghost-toggle-${gi}`}
              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}
            >
              <input
                type="checkbox"
                checked={ghostingToggles[gi] ?? true}
                onChange={(e) =>
                  setGhostingToggles((prev) => ({ ...prev, [gi]: e.target.checked }))
                }
              />
              Ghost {gType}: {fromLabel} → {toLabel}
            </label>
          )
        })}
      </div>

      {/* SVG chart — breaks out of page-content padding to use the full body width */}
      <div
        className="panel vca-chart-panel"
        style={{ padding: '0.5rem 0', margin: '0 -1.5rem', borderRadius: 0, overflowX: 'auto' }}
        ref={containerRef}
      >
        {partnerQueriesLoading ? (
          <LoadingState message="Loading partner data…" />
        ) : (
          <VcaTimeline
            people={people}
            ghostings={ghostings}
            partnerRefMap={partnerRefMap}
            containerWidth={Math.max(containerWidth, 600)}
            toggles={{
              showDurations,
              showInoc,
              showGhostedMap: ghostingToggles,
              showCritical,
              showInterview,
              showLabLines,
            }}
          />
        )}
      </div>

      {/* Legend */}
      <div className="panel stack-sm no-print">
        <p className="eyebrow">Chart legend</p>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '0.4rem',
          }}
        >
          {LEGEND_ITEMS.map(({ label, symbol, color }) => (
            <span
              key={label}
              style={{ fontSize: '0.85rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}
            >
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
          className="panel no-print"
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
