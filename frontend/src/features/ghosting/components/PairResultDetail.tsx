import { useState, useMemo } from 'react'
import type { PairResult } from '../types-local'
import { CriteriaCards } from './CriteriaCards'
import { VerdictBanner, VerdictContext } from './VerdictDisplay'
import { NH_CONSTANTS } from '../types-local'

function isoAddDays(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00')
  d.setDate(d.getDate() + days)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function computeInoculationAvg(onset: string): string {
  return isoAddDays(onset, -21)
}

export function PairResultDetail({ pair }: { pair: PairResult }) {
  const [logOpen, setLogOpen] = useState(false)
  const [scenarioTab, setScenarioTab] = useState<'source' | 'spread'>('source')
  const [mode, setMode] = useState<'traditional' | 'comprehensive'>('traditional')
  const { result } = pair

  const importantDates = useMemo(() => {
    if (!result) return null
    const sym = result.case1_symptom
    const isPrimary = sym.type === 'Primary Chancre' || sym.type === 'Historical Primary' || sym.type === 'Ghosted Primary'
    const d1Offset = isPrimary
      ? NH_CONSTANTS.INCUBATION.avg
      : NH_CONSTANTS.INCUBATION.avg + NH_CONSTANTS.PRIMARY.avg + NH_CONSTANTS.LATENCY.avg
    const ipDays = isPrimary ? NH_CONSTANTS.INTERVIEW_PRIMARY : NH_CONSTANTS.INTERVIEW_SECONDARY
    const d1 = isoAddDays(sym.onset, -d1Offset)
    const elicit = isoAddDays(sym.onset, -ipDays)
    return { d1, elicitBack: elicit, sourceOnset: result.ghosted_source.onset, sourceEnd: result.ghosted_source.end }
  }, [result])

  if (!result) {
    return <p className="error-text">{pair.error}</p>
  }

  const srcLesion = result.source_scenarios.range_lesions['expected']
  const sprLesion = result.spread_scenarios.range_lesions['expected']
  const activeScenario = scenarioTab === 'source' ? result.source_scenarios : result.spread_scenarios
  const activeGhostedLesion =
    scenarioTab === 'source' ? result.ghosted_source : result.ghosted_spread

  return (
    <div className="stack-lg">
      {/* Mode toggle */}
      <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', border: '1px solid #d0d0d0', alignSelf: 'flex-start' }} className="no-print">
        {(['traditional', 'comprehensive'] as const).map(m => (
          <button key={m} type="button" onClick={() => setMode(m)} style={{ padding: '0.3rem 0.75rem', fontSize: '0.8rem', fontWeight: mode === m ? 700 : 400, background: mode === m ? '#1d9e75' : '#fff', color: mode === m ? '#fff' : '#444', border: 'none', cursor: 'pointer' }}>
            {m === 'traditional' ? 'Traditional VCA' : 'Comprehensive'}
          </button>
        ))}
      </div>

      <VerdictBanner verdict={result.verdict} />
      <VerdictContext result={result} />

      {/* Important Dates */}
      {importantDates && (
        <div className="panel stack-xs" style={{ fontSize: '0.875rem' }}>
          <p className="eyebrow">Important Dates</p>
          <ul style={{ margin: 0, paddingLeft: '1.25rem', lineHeight: 1.8 }}>
            <li><strong>{result.case1_name} was likely infected on:</strong> {importantDates.d1}</li>
            <li><strong>Elicit contacts back to:</strong> {importantDates.elicitBack}</li>
            <li><strong>The likely source was infectious between:</strong> {importantDates.sourceOnset} and {importantDates.sourceEnd}</li>
          </ul>
        </div>
      )}

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
          &nbsp;·&nbsp;Tiers passed: {activeScenario.pass_count} / 5
        </div>
        <CriteriaCards
          rangeData={activeScenario.range_data}
          mode={mode}
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
