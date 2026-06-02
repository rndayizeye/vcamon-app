import type { GhostingCriteriaCheck, GhostingScenarioCriteria, GhostingSymptomInput, GhostedLesion } from '../types'

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
    <span className={styles[check.status] ?? 'badge'}>{labels[check.status] ?? check.status}</span>
  )
}

export function EnhancedCriteriaTable({
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
          <td rowSpan={2} style={{ fontWeight: 500, verticalAlign: 'middle' }}>
            Exposure
          </td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td>
            <StatusBadge check={expected.exposure} />
          </td>
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
            {case1Name}&apos;s avg inoculation ({inocAvg}) —{' '}
            {inocInWindow
              ? `within ghosted lesion (${ghostedLesion.onset} → ${ghostedLesion.end})`
              : `outside ghosted lesion (${ghostedLesion.onset} → ${ghostedLesion.end})`}
          </td>
        </tr>
        <tr>
          <td style={{ fontWeight: 500 }}>Exposure modality</td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td>
            <StatusBadge check={expected.exposure_modality} />
          </td>
          <td style={tdMuted}>{expected.exposure_modality.detail}</td>
        </tr>
        <tr>
          <td rowSpan={3} style={{ fontWeight: 500, verticalAlign: 'middle' }}>
            Latency
          </td>
          <td style={{ fontSize: '0.8rem', color: '#888' }}>Optimistic (min)</td>
          <td>
            <StatusBadge check={aggressive.latency} />
          </td>
          <td style={tdMuted}>{aggressive.latency.detail}</td>
        </tr>
        <tr style={{ background: 'rgba(0,0,0,0.02)' }}>
          <td style={{ fontSize: '0.8rem', fontWeight: 600 }}>Expected (avg)</td>
          <td>
            <StatusBadge check={expected.latency} />
          </td>
          <td style={tdMuted}>{expected.latency.detail}</td>
        </tr>
        <tr>
          <td style={{ fontSize: '0.8rem', color: '#888' }}>Conservative (max)</td>
          <td>
            <StatusBadge check={conservative.latency} />
          </td>
          <td style={tdMuted}>{conservative.latency.detail}</td>
        </tr>
        <tr>
          <td style={{ fontWeight: 500 }}>Natural order</td>
          <td style={{ ...tdMuted, fontSize: '0.8rem' }}>Expected</td>
          <td>
            <StatusBadge check={expected.natural_order} />
          </td>
          <td style={tdMuted}>{expected.natural_order.detail}</td>
        </tr>
      </tbody>
    </table>
  )
}
