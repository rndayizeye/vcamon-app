import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { LoadingState } from '../components/feedback/LoadingState'
import { getCaseLatestLab, getDashboardSummary, getCase, listCases } from '../features/cases/api'
import { CaseDashboardTable } from '../features/cases/components/dashboard/CaseDashboardTable'
import { CaseQuickView } from '../features/cases/components/dashboard/CaseQuickView'
import { DashboardMetrics } from '../features/cases/components/dashboard/DashboardMetrics'
import type { CaseRead, CaseSummary, DashboardSummary, LabResultEntry } from '../features/cases/types'

export function DashboardPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<CaseSummary[]>([])
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [selectedCaseData, setSelectedCaseData] = useState<CaseRead | null>(null)
  const [latestLab, setLatestLab] = useState<LabResultEntry | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Initial load
  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      try {
        const [summaryData, casesData] = await Promise.all([getDashboardSummary(), listCases('')])
        setSummary(summaryData)
        setCases(casesData)
      } catch (err) {
        console.error('Dashboard load error:', err)
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      void listCases(searchQuery.trim()).then(setCases).catch(console.error)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Case detail fetch when selection changes
  useEffect(() => {
    const loadDetail = async () => {
      if (!selectedCaseId) {
        setSelectedCaseData(null)
        setLatestLab(null)
        return
      }
      try {
        const [caseData, labData] = await Promise.all([
          getCase(selectedCaseId),
          getCaseLatestLab(selectedCaseId),
        ])
        setSelectedCaseData(caseData)
        setLatestLab(labData)
      } catch (err) {
        console.error('Case detail load error:', err)
      }
    }
    void loadDetail()
  }, [selectedCaseId])

  if (isLoading) {
    return <LoadingState message="Loading dashboard…" />
  }

  return (
    <section className="stack-lg">
      <header className="panel page-header-row">
        <div>
          <p className="eyebrow">VCA Monitor</p>
          <h1>Case Dashboard</h1>
          <p className="muted small-text">Manage cases and monitor treatment status.</p>
        </div>
        <button className="button button-primary" onClick={() => navigate('/cases/new')}>
          + New Case
        </button>
      </header>

      {summary && <DashboardMetrics summary={summary} />}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) 300px',
          gap: '1.25rem',
          alignItems: 'start',
        }}
      >
        <div className="stack-sm">
          <label className="field">
            <input
              type="search"
              placeholder="Search patients by name…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </label>
          <CaseDashboardTable
            cases={cases}
            selectedCaseId={selectedCaseId}
            onCaseSelect={setSelectedCaseId}
          />
        </div>

        <CaseQuickView caseData={selectedCaseData} latestLab={latestLab} />
      </div>
    </section>
  )
}
