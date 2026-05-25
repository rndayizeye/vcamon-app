import { Link } from 'react-router-dom'
import type { CaseSummary } from '../../types'

export function CaseDashboardTable({
  cases,
  selectedCaseId,
  onCaseSelect,
}: {
  cases: CaseSummary[]
  selectedCaseId: number | null
  onCaseSelect: (id: number) => void
}) {
  return (
    <div className="panel table-panel">
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Patient</th>
            <th>Diagnosis</th>
            <th>Manager</th>
            <th>Reason</th>
            <th>Treated</th>
            <th>Partners</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {cases.map(c => (
            <tr
              key={c.id}
              onClick={() => onCaseSelect(c.id)}
              style={{
                cursor: 'pointer',
                background:
                  selectedCaseId === c.id
                    ? '#ddeeff'
                    : !c.treatment_date
                    ? 'rgba(251,191,36,0.07)'
                    : undefined,
              }}
            >
              <td>
                <Link
                  to={`/cases/${c.id}/overview`}
                  className="table-link"
                  onClick={e => e.stopPropagation()}
                >
                  #{c.id}
                </Link>
              </td>
              <td style={{ fontWeight: 500 }}>{c.patient_name}</td>
              <td>{c.diagnosis_code || '—'}</td>
              <td>{c.case_manager || '—'}</td>
              <td>{c.reason_for_exam || '—'}</td>
              <td>
                {c.treatment_date ?? (
                  <span style={{ color: '#854F0B', fontWeight: 600 }}>Pending</span>
                )}
              </td>
              <td>{c.partner_count}</td>
              <td className="muted small-text">
                {c.updated_at ? new Date(c.updated_at).toLocaleDateString() : '—'}
              </td>
            </tr>
          ))}
          {cases.length === 0 && (
            <tr>
              <td
                colSpan={8}
                style={{
                  textAlign: 'center',
                  color: '#5b6f82',
                  fontStyle: 'italic',
                  padding: '2rem 0.75rem',
                }}
              >
                No cases found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
