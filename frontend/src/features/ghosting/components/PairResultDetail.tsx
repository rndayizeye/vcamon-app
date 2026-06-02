import { useState } from 'react'
import type { PairResult } from '../types-local'
import { EnhancedCriteriaTable } from './EnhancedCriteriaTable'
import { VerdictBanner, VerdictContext } from './VerdictDisplay'

function isoAddDays(iso: string, days: number): string {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function computeInoculationAvg(onset: string): string {
  return isoAddDays(onset, -21)
}

export function PairResultDetail({ pair }: { pair: PairResult }) {
  const [logOpen, setLogOpen] = useState(false)
  const [scenarioTab, setScenarioTab] = useState<'source' | 'spread'>('source')
  const { result } = pair

  if (!result) {
    return <p className="error-text">{pair.error}</p>
  }

  const srcLesion = result.source_scenarios.range_lesions.expected
  const sprLesion = result.spread_scenarios.range_lesions.expected
  const activeScenario = scenarioTab === 'source' ? result.source_scenarios : result.spread_scenarios
  const activeGhostedLesion =
    scenarioTab === 'source' ? result.ghosted_source : result.ghosted_spread

  return (
    <div className="stack-lg">
      <VerdictBanner verdict={result.verdict} />
      <VerdictContext result={result} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
        {[
          { label: 'Ghosted source onset', val: srcLesion.onset },
          { label: 'Ghosted source end', val: srcLesion.end },
          { label: 'Ghosted spread onset', val: sprLesion.onset },
          { label: 'Ghosted spread end', val: sprLesion.end },
        ].map(({ label, val }) => (
          <div key={label} className="panel stack-xs">
            <p className="eyebrow">{label}</p>
            <p style={{ fontWeight: 700, fontSize: '1.05rem' }}>{val}</p>
          </div>
        ))}
      </div>

      <div className="panel stack-xs">
        <p className="eyebrow">Anchor symptom (engine-selected OP)</p>
        <p style={{ fontSize: '0.9rem' }}>
          <strong>{result.case1_name}</strong> · {result.case1_symptom.type} · Onset{' '}
          {result.case1_symptom.onset}
          {result.case1_symptom.duration_days > 0
            ? ` · Duration ${result.case1_symptom.duration_days}d`
            : ''}
          {' · '}Avg inoculation:{' '}
          <strong>{computeInoculationAvg(result.case1_symptom.onset)}</strong>
        </p>
        <p style={{ fontSize: '0.82rem', color: '#888' }}>
          Comparison patient: {result.case2_name}
        </p>
      </div>

      <div className="panel stack-md">
        <nav className="tab-nav" aria-label="Scenario">
          {(['source', 'spread'] as const).map(tab => (
            <button
              key={tab}
              type="button"
              className={scenarioTab === tab ? 'tab-link tab-link-active' : 'tab-link'}
              onClick={() => setScenarioTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)} scenario
            </button>
          ))}
        </nav>
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
            Hypothesis
          </p>
          <p>
            {scenarioTab === 'source'
              ? `Whether ${result.case2_name} was the source who infected ${result.case1_name}.`
              : `Whether ${result.case1_name} spread the infection to ${result.case2_name}.`}
          </p>
        </div>
        <div style={{ fontSize: '0.82rem', color: '#555' }}>
          Confidence: <strong>{activeScenario.confidence}</strong>
          &nbsp;·&nbsp;Criteria passed: {activeScenario.pass_count} / 4
        </div>
        <EnhancedCriteriaTable
          aggressive={activeScenario.range_data.aggressive}
          expected={activeScenario.range_data.expected}
          conservative={activeScenario.range_data.conservative}
          case1Symptom={result.case1_symptom}
          ghostedLesion={activeGhostedLesion}
          case1Name={result.case1_name}
        />
      </div>

      <div className="panel stack-sm">
        <button
          type="button"
          className="button"
          onClick={() => setLogOpen(o => !o)}
          style={{ alignSelf: 'flex-start' }}
        >
          {logOpen ? '▲ Hide' : '▼ Show'} step-by-step log
        </button>
        {logOpen && (
          <pre
            style={{
              background: '#F4F2EC',
              padding: '0.75rem',
              borderRadius: '4px',
              fontSize: '0.8rem',
              lineHeight: 1.6,
              overflowX: 'auto',
              margin: 0,
            }}
          >
            {result.log.join('\n')}
          </pre>
        )}
      </div>
    </div>
  )
}
