import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/use-auth";
import { formatDate, formatDateTime } from "../../../lib/utils";
import type { CaseRead } from "../types";

export function CaseHeader({ caseData }: { caseData: CaseRead }) {
  const { permissions } = useAuth();

  return (
    <section className="panel stack-md">
      <div className="case-header-row">
        <div>
          <p className="eyebrow">Case</p>
          <h1>{caseData.patient_name}</h1>
        </div>

        {permissions.can_write ? (
          <Link className="button" to={`/cases/${caseData.id}/edit`}>
            Edit case
          </Link>
        ) : null}
      </div>

      <dl className="metadata-grid">
        <div>
          <dt>Diagnosis</dt>
          <dd>{caseData.diagnosis_code || caseData.lot || "—"}</dd>
        </div>
        <div>
          <dt>Case manager</dt>
          <dd>{caseData.case_manager || "—"}</dd>
        </div>
        <div>
          <dt>Initial contact</dt>
          <dd>{formatDate(caseData.initial_contact_date)}</dd>
        </div>
        <div>
          <dt>Treatment date</dt>
          <dd>{formatDate(caseData.treatment_date)}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatDateTime(caseData.created_at)}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>{formatDateTime(caseData.updated_at)}</dd>
        </div>
      </dl>
    </section>
  );
}
