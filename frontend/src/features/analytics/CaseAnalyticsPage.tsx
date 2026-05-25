import { useState } from 'react'
import { useParams } from 'react-router-dom'

import { EmptyState } from '../../components/feedback/EmptyState'
import { ErrorState } from '../../components/feedback/ErrorState'
import { LoadingState } from '../../components/feedback/LoadingState'
import { AnalyticsSummaryCards } from './components/AnalyticsSummaryCards'
import { CentralityTable } from './components/CentralityTable'
import { ClusterPanel } from './components/ClusterPanel'
import { CreateLinkForm } from './components/CreateLinkForm'
import { LinkList } from './components/LinkList'
import { useCaseAnalytics, useCaseLinks } from './hooks'

export function CaseAnalyticsPage() {
  const { caseId } = useParams()
  const parsedCaseId = Number(caseId)
  const [asOfDate, setAsOfDate] = useState('')

  const analyticsQuery = useCaseAnalytics(parsedCaseId, asOfDate || undefined)
  const linksQuery = useCaseLinks(parsedCaseId)

  if (!Number.isInteger(parsedCaseId) || parsedCaseId <= 0) {
    return <ErrorState title="Invalid case" message="The case id is not valid." />
  }

  if (analyticsQuery.isLoading || linksQuery.isLoading) {
    return <LoadingState message="Loading analytics…" />
  }

  if (analyticsQuery.isError) {
    return (
      <ErrorState
        title="Unable to load analytics"
        message={analyticsQuery.error.message}
        onRetry={() => void analyticsQuery.refetch()}
      />
    )
  }

  if (linksQuery.isError) {
    return (
      <ErrorState
        title="Unable to load links"
        message={linksQuery.error.message}
        onRetry={() => void linksQuery.refetch()}
      />
    )
  }

  if (!analyticsQuery.data || !linksQuery.data) {
    return <EmptyState title="Analytics unavailable" />
  }

  return (
    <section className="stack-lg">
      <header className="panel stack-md">
        <div>
          <p className="eyebrow">Analytics</p>
          <h2>Network summary</h2>
        </div>

        <label className="field field-inline">
          <span>As-of date</span>
          <input
            type="date"
            value={asOfDate}
            onChange={(event) => setAsOfDate(event.target.value)}
          />
        </label>
      </header>

      <AnalyticsSummaryCards summary={analyticsQuery.data} />

      <section className="panel table-panel stack-sm">
        <div>
          <p className="eyebrow">Nodes</p>
          <h2>Visible nodes</h2>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Ref</th>
              <th>Label</th>
              <th>Type</th>
              <th>Treated</th>
              <th>First date</th>
            </tr>
          </thead>
          <tbody>
            {analyticsQuery.data.nodes.map((node) => (
              <tr key={node.ref}>
                <td>{node.ref}</td>
                <td>{node.label}</td>
                <td>{node.entity_type}</td>
                <td>{node.treated ? 'Yes' : 'No'}</td>
                <td>{node.first_date || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <CentralityTable rows={analyticsQuery.data.centralities} />
      <ClusterPanel clusters={analyticsQuery.data.clusters} />

      <div className="two-column-grid analytics-actions-grid">
        <CreateLinkForm caseId={parsedCaseId} nodes={analyticsQuery.data.nodes} />
        <LinkList caseId={parsedCaseId} links={linksQuery.data} />
      </div>
    </section>
  )
}
