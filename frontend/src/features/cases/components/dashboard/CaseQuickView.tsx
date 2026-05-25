import { Link } from 'react-router-dom'
import type { CaseRead, LabResultEntry } from '../../types'

export function CaseQuickView({
  caseData,
  latestLab,
}: {
  caseData: CaseRead | null
  latestLab: LabResultEntry | null
}) {
  if (!caseData) {
    return (
      <div className="panel panel-centered">
        <p className="muted">Select a case from the table to view details.</p>
      </div>
    )
  }

  return (
    <div className="panel stack-md">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
        <div>
          <p className="eyebrow">Selected case</p>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginTop: '0.2rem' }}>
            {caseData.patient_name}
          </h3>
          <p className="muted small-text">Case #{caseData.id}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
          <Link
            to={`/cases/${caseData.id}/edit`}
            className="button button-primary"
            style={{ padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
          >
            Edit
          </Link>
          <Link
            to={`/cases/${caseData.id}/partners`}
            className="button"
            style={{ padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
          >
            Partners
          </Link>
        </div>
      </div>

      <dl className="metadata-grid">
        <div>
          <dt>Diagnosis</dt>
          <dd>{caseData.diagnosis_code || '—'}</dd>
        </div>
        <div>
          <dt>Manager</dt>
          <dd>{caseData.case_manager || '—'}</dd>
        </div>
        <div>
          <dt>Reason for exam</dt>
          <dd>{caseData.reason_for_exam || '—'}</dd>
        </div>
        <div>
          <dt>Treatment</dt>
          <dd style={{ color: caseData.treatment_date ? undefined : '#854F0B' }}>
            {caseData.treatment_date || 'Pending'}
          </dd>
        </div>
      </dl>

      <div>
        <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Latest lab result</p>
        {latestLab ? (
          <div className="entry-card">
            <strong>
              {latestLab.test_type}: {latestLab.result}
            </strong>
            <p className="muted small-text" style={{ marginTop: '0.2rem' }}>
              {latestLab.titer ? `Titer: ${latestLab.titer} · ` : ''}
              Collected: {latestLab.collection_date}
            </p>
          </div>
        ) : (
          <p className="muted small-text">No lab results recorded.</p>
        )}
      </div>

      {caseData.medical_info && (
        <div>
          <p className="eyebrow" style={{ marginBottom: '0.5rem' }}>Medical info</p>
          <p style={{ fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>{caseData.medical_info}</p>
        </div>
      )}
    </div>
  )
}
