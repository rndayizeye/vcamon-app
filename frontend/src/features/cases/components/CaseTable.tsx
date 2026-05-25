import { Link } from "react-router-dom";

import { formatDate, formatDateTime } from "../../../lib/utils";
import type { CaseSummary } from "../types";

export function CaseTable({ cases }: { cases: CaseSummary[] }) {
  return (
    <div className="panel table-panel">
      <table className="data-table">
        <thead>
          <tr>
            <th>Patient</th>
            <th>Diagnosis</th>
            <th>Case manager</th>
            <th>Initial contact</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((caseItem) => (
            <tr key={caseItem.id}>
              <td>
                <Link
                  className="table-link"
                  to={`/cases/${caseItem.id}/analytics`}
                >
                  {caseItem.patient_name}
                </Link>
              </td>
              <td>{caseItem.diagnosis_code || caseItem.lot || "—"}</td>
              <td>{caseItem.case_manager || "—"}</td>
              <td>{formatDate(caseItem.initial_contact_date)}</td>
              <td>{formatDateTime(caseItem.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
