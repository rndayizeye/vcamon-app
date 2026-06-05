import type { GhostingScenarioCriteria, GhostingCriteriaCheck } from '../types'
import { CRITERIA_META } from '../types-local'

const STATUS_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  pass: { label: '✓ Pass',  color: '#1d9e75', bg: '#eafaf3' },
  fail: { label: '✗ Fail',  color: '#c0392b', bg: '#fdf0f0' },
  warn: { label: '⚠ Warn',  color: '#8a6d00', bg: '#fef8ec' },
  na:   { label: '— N/A',   color: '#666',    bg: '#f5f5f5' },
}

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

type Props = {
  rangeData: Record<string, GhostingScenarioCriteria>
  scenario: 'source' | 'spread'
}

export function CriteriaCards({ rangeData, scenario }: Props) {
  const expected = rangeData['expected']
  if (!expected) return null

  const criteriaKeys = Object.keys(expected) as (keyof GhostingScenarioCriteria)[]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {criteriaKeys.map((key) => {
        const check = expected[key]
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
