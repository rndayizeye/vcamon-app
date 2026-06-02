import type { GhostingAnalysisResult } from '../types'

export function VerdictBanner({ verdict, compact }: { verdict: string; compact?: boolean }) {
  const up = verdict.toUpperCase()
  let color = '#e24b4a',
    bg = '#fdf0f0',
    border = '#e24b4a'
  if (up.includes('AMBIGUOUS') || up.includes('⚠') || up.includes('OVERLAP')) {
    color = '#8a6d00'
    bg = '#fef8ec'
    border = '#ef9f27'
  } else if (up.includes('SOURCE')) {
    color = '#1d9e75'
    bg = '#eafaf3'
    border = '#1d9e75'
  } else if (up.includes('SPREAD')) {
    color = '#378add'
    bg = '#e8f3fd'
    border = '#378add'
  }

  if (compact) {
    return (
      <span
        style={{
          padding: '2px 10px',
          borderRadius: '4px',
          background: bg,
          border: `1px solid ${border}`,
          color,
          fontSize: '0.8rem',
          fontWeight: 700,
          whiteSpace: 'nowrap',
        }}
      >
        {verdict}
      </span>
    )
  }
  return (
    <div
      style={{
        padding: '1rem 1.25rem',
        borderRadius: '8px',
        background: bg,
        border: `1.5px solid ${border}`,
        color,
      }}
    >
      <span
        style={{
          fontSize: '0.7rem',
          fontWeight: 700,
          letterSpacing: '0.08em',
          opacity: 0.7,
          display: 'block',
          marginBottom: '0.25rem',
        }}
      >
        SOURCE SPREAD ANALYSIS
      </span>
      <p style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>{verdict}</p>
    </div>
  )
}

export function VerdictContext({ result }: { result: GhostingAnalysisResult }) {
  const srcE = result.source_scenarios.range_data.expected
  const sprE = result.spread_scenarios.range_data.expected
  const srcL = result.source_scenarios.range_lesions.expected
  const sprL = result.spread_scenarios.range_lesions.expected
  const c1 = result.case1_name
  const c2 = result.case2_name

  type Item = { scenario: string; text: string }
  const passing: Item[] = []
  const failing: Item[] = []

  if (srcE.exposure.status === 'pass') passing.push({ scenario: 'Source', text: srcE.exposure.detail })
  else if (srcE.exposure.status === 'fail')
    failing.push({
      scenario: 'Source',
      text: `${c1} was likely not infected by ${c2} — exposure window does not overlap with ${c2}'s ghosted source lesion (${srcL.onset} → ${srcL.end}).`,
    })
  if (srcE.exposure_modality.status === 'pass')
    passing.push({ scenario: 'Source', text: srcE.exposure_modality.detail })
  else if (srcE.exposure_modality.status === 'fail')
    failing.push({
      scenario: 'Source',
      text: `Contact type is not compatible with the site of ${c1}'s ${result.case1_symptom.type}.`,
    })
  if (srcE.latency.status === 'pass') passing.push({ scenario: 'Source', text: srcE.latency.detail })
  else if (srcE.latency.status === 'fail') failing.push({ scenario: 'Source', text: srcE.latency.detail })
  if (srcE.natural_order.status === 'pass')
    passing.push({ scenario: 'Source', text: srcE.natural_order.detail })
  else if (srcE.natural_order.status === 'fail')
    failing.push({
      scenario: 'Source',
      text: `Ghosted source lesion would occur after ${c2}'s secondary lesion — primary must precede secondary.`,
    })

  if (sprE.exposure.status === 'pass') passing.push({ scenario: 'Spread', text: sprE.exposure.detail })
  else if (sprE.exposure.status === 'fail')
    failing.push({
      scenario: 'Spread',
      text: `${c2} was likely not infected by ${c1} — exposure window does not overlap with ${c1}'s infectious period (${sprL.onset} → ${sprL.end}).`,
    })
  if (sprE.exposure_modality.status === 'pass')
    passing.push({ scenario: 'Spread', text: sprE.exposure_modality.detail })
  else if (sprE.exposure_modality.status === 'fail')
    failing.push({
      scenario: 'Spread',
      text: `Contact type is not compatible with the site of ${c1}'s ${result.case1_symptom.type}. ${sprE.exposure_modality.detail}`,
    })
  if (sprE.latency.status === 'pass') passing.push({ scenario: 'Spread', text: sprE.latency.detail })
  else if (sprE.latency.status === 'fail') failing.push({ scenario: 'Spread', text: sprE.latency.detail })
  if (sprE.natural_order.status === 'pass')
    passing.push({ scenario: 'Spread', text: sprE.natural_order.detail })
  else if (sprE.natural_order.status === 'fail')
    failing.push({
      scenario: 'Spread',
      text: `Ghosted spread lesion would occur after ${c2}'s secondary lesion — primary must precede secondary.`,
    })

  return (
    <div
      style={{
        borderRadius: '6px',
        padding: '0.75rem 1rem',
        fontSize: '0.875rem',
        border: '1px solid #dde',
        background: '#f9f9fb',
      }}
    >
      <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>
        Why?
      </p>
      {passing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#1d9e75', marginBottom: '0.25rem' }}>
            Supporting evidence:
          </p>
          <ul
            style={{
              margin: 0,
              paddingLeft: '1.25rem',
              marginBottom: failing.length ? '0.75rem' : 0,
            }}
          >
            {passing.map((p, i) => (
              <li key={i} style={{ marginBottom: '0.35rem' }}>
                <strong style={{ color: '#1d9e75' }}>[{p.scenario}]</strong> {p.text}
              </li>
            ))}
          </ul>
        </>
      )}
      {failing.length > 0 && (
        <>
          <p style={{ fontWeight: 600, color: '#e24b4a', marginBottom: '0.25rem' }}>
            Limiting factors:
          </p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {failing.map((f, i) => (
              <li key={i} style={{ marginBottom: '0.35rem' }}>
                <strong style={{ color: '#c0392b' }}>[{f.scenario}]</strong> {f.text}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
