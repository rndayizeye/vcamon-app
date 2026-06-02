import { useDeferredValue, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ErrorState } from '../components/feedback/ErrorState'
import { LoadingState } from '../components/feedback/LoadingState'
import { useCase, useCases, useDashboardSummary, useLatestLab } from '../features/cases/hooks'
import { CaseDashboardTable } from '../features/cases/components/dashboard/CaseDashboardTable'
import { CaseQuickView } from '../features/cases/components/dashboard/CaseQuickView'
import { DashboardMetrics } from '../features/cases/components/dashboard/DashboardMetrics'
import { useDocumentTitle } from '../lib/useDocumentTitle'

export function DashboardPage() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)

  useDocumentTitle('Case Dashboard')
  const deferredSearch = useDeferredValue(searchQuery)

  const summaryQuery = useDashboardSummary()
  const casesQuery = useCases(deferredSearch)
  const caseDetailQuery = useCase(selectedCaseId ?? 0)
  const latestLabQuery = useLatestLab(selectedCaseId ?? 0)

  if (summaryQuery.isLoading) {
    return <LoadingState message="Loading dashboard…" />
  }

  if (summaryQuery.isError) {
    return (
      <ErrorState
        title="Unable to load dashboard"
        message={summaryQuery.error.message}
        onRetry={() => void summaryQuery.refetch()}
      />
    )
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

      {summaryQuery.data && <DashboardMetrics summary={summaryQuery.data} />}

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
              id="case-search"
              type="search"
              aria-label="Search patients by name"
              placeholder="Search patients by name…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </label>
          {casesQuery.isError ? (
            <ErrorState
              title="Unable to load cases"
              message={casesQuery.error.message}
              onRetry={() => void casesQuery.refetch()}
            />
          ) : (
            <CaseDashboardTable
              cases={casesQuery.data ?? []}
              selectedCaseId={selectedCaseId}
              onCaseSelect={setSelectedCaseId}
            />
          )}
        </div>

        <CaseQuickView
          caseData={caseDetailQuery.data ?? null}
          latestLab={latestLabQuery.data ?? null}
        />
      </div>
    </section>
  )
}
