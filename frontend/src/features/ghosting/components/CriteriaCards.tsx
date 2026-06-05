import type { GhostingScenarioCriteria, GhostingCriteriaCheck } from '../types'
import { CRITERIA_META, SCENARIO_LABELS } from '../types-local'

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  pass: { label: '✓ Pass',  color: '#1d9e75', bg: '#eafaf3' },
  fail: { label: '✗ Fail',  color: '#c0392b', bg: '#fdf0f0' },
  warn: { label: '⚠ Warn',  color: '#8a6d00', bg: '#fef8ec' },
  na:   { label: '— N/A',   color: '#666',    bg: '#f5f5f5' },
}

const TIER_ORDER = [
  'aggressive',
  'expected',
  'conservative',
  'fast_infection_slow_disease',
  'slow_infection_fast_disease',
]

function CriteriaBadge({ check }: { check: GhostingCriteriaCheck }) {
  const s = STATUS_BADGE[check.status] ?? STATUS_BADGE.na
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: '0.78rem',
        fontWeight: 700,
        color: s.color,
        background: s.bg,
        border: `1px solid ${s.color}`,
        whiteSpace: 'nowrap',
      }}
    >
      {s.label}
    </span>
  )
}

function CriteriaList({ tierCriteria }: { tierCriteria: GhostingScenarioCriteria }) {
  const criteriaKeys = Object.keys(tierCriteria) as (keyof GhostingScenarioCriteria)[]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {criteriaKeys.map((key) => {
        const check = tierCriteria[key]
        const meta = CRITERIA_META[key] ?? { label: key, description: '' }
        const isOpen = check.status === 'fail' || check.status === 'warn'

        return (
          <details
            key={key}
            open={isOpen}
            style={{
              border: '1px solid #e0e0e0',
              borderRadius: 6,
              overflow: 'hidden',
            }}
          >
            <summary
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                padding: '0.6rem 0.9rem',
                cursor: 'pointer',
                background: '#fafafa',
                fontSize: '0.9rem',
                fontWeight: 500,
                listStyle: 'none',
                userSelect: 'none',
              }}
            >
              <CriteriaBadge check={check} />
              <span>{meta.label}</span>
            </summary>

            <div style={{ padding: '0.75rem 0.9rem', fontSize: '0.875rem' }}>
              {meta.description && (
                <p style={{ color: '#555', marginBottom: '0.6rem', lineHeight: 1.5 }}>
                  {meta.description}
                </p>
              )}
              <hr style={{ border: 'none', borderTop: '1px solid #eee', margin: '0.5rem 0' }} />
              <p style={{ color: '#444', margin: 0, lineHeight: 1.5 }}>
                <strong>Engine output:</strong> {check.detail}
              </p>
            </div>
          </details>
        )
      })}
    </div>
  )
}

type Props = {
  rangeData: Record<string, GhostingScenarioCriteria>
  mode: 'traditional' | 'comprehensive'
}

export function CriteriaCards({ rangeData, mode }: Props) {
  if (mode === 'traditional') {
    const expected = rangeData['expected']
    if (!expected) return null
    return <CriteriaList tierCriteria={expected} />
  }

  const tiers = TIER_ORDER.filter(k => rangeData[k] != null)
  if (tiers.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {tiers.map(tierKey => {
        const tierCriteria = rangeData[tierKey]
        const label = SCENARIO_LABELS[tierKey] ?? tierKey
        const keys = Object.keys(tierCriteria) as (keyof GhostingScenarioCriteria)[]
        const passed = keys.every(k => tierCriteria[k].status !== 'fail')
        return (
          <div
            key={tierKey}
            style={{
              border: `1px solid ${passed ? '#c3e6cb' : '#f5c6cb'}`,
              borderRadius: 6,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '0.5rem 0.9rem',
                background: passed ? '#eafaf3' : '#fdf0f0',
                fontSize: '0.8rem',
                fontWeight: 700,
                color: passed ? '#1d9e75' : '#c0392b',
              }}
            >
              {passed ? '✓' : '✗'} {label}
            </div>
            <div style={{ padding: '0.5rem 0.9rem' }}>
              <CriteriaList tierCriteria={tierCriteria} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
