import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { formatDate } from "../../lib/utils";
import { useCaseSymptoms } from "../symptoms/hooks";
import { resolveSymptomTiming } from "../symptoms/utils";
import { useCase } from "./hooks";

export function CaseOverviewPage() {
  const { caseId } = useParams();
  const parsedCaseId = Number(caseId);
  const safeCaseId =
    Number.isInteger(parsedCaseId) && parsedCaseId > 0 ? parsedCaseId : 0;
  const caseQuery = useCase(safeCaseId);
  const symptomsQuery = useCaseSymptoms(safeCaseId);

  const derivedSymptomRows = useMemo(() => {
    return (symptomsQuery.data || []).map((symptom) => {
      const timing = resolveSymptomTiming({
        symptom_type: symptom.symptom_type,
        onset_date: symptom.onset_date,
        date_kind: symptom.date_kind,
        duration_days: symptom.duration_days,
      });

      return {
        ...symptom,
        derived_onset_date: timing.derivedOnsetDate,
        effective_duration_days: timing.effectiveDurationDays,
      };
    });
  }, [symptomsQuery.data]);

  if (safeCaseId === 0) {
    return (
      <ErrorState title="Invalid case" message="The case id is not valid." />
    );
  }

  if (caseQuery.isLoading || symptomsQuery.isLoading) {
    return <LoadingState message="Loading case overview…" />;
  }

  if (caseQuery.isError) {
    return (
      <ErrorState
        title="Unable to load case overview"
        message={caseQuery.error.message}
        onRetry={() => void caseQuery.refetch()}
      />
    );
  }

  if (symptomsQuery.isError) {
    return (
      <ErrorState
        title="Unable to load case symptoms"
        message={symptomsQuery.error.message}
        onRetry={() => void symptomsQuery.refetch()}
      />
    );
  }

  if (!caseQuery.data) {
    return <EmptyState title="Case not found" />;
  }

  return (
    <section className="stack-lg">
      <section className="panel stack-md">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>{caseQuery.data.patient_name}</h2>
        </div>

        <dl className="metadata-grid">
          <div>
            <dt>Reason for exam</dt>
            <dd>{caseQuery.data.reason_for_exam || "—"}</dd>
          </div>
          <div>
            <dt>Treatment date</dt>
            <dd>{formatDate(caseQuery.data.treatment_date)}</dd>
          </div>
          <div>
            <dt>Historical primary</dt>
            <dd>{caseQuery.data.historical_primary_chancre ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt>Historical primary date</dt>
            <dd>{formatDate(caseQuery.data.historical_primary_date)}</dd>
          </div>
          <div>
            <dt>Medical info</dt>
            <dd>{caseQuery.data.medical_info || "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="panel stack-md">
        <div>
          <p className="eyebrow">Symptoms</p>
          <h3>Recorded symptom rows</h3>
        </div>

        {derivedSymptomRows.length === 0 ? (
          <p className="muted">
            No symptom rows have been recorded for this case yet.
          </p>
        ) : (
          <div className="table-panel">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Onset or observation</th>
                  <th>Date type</th>
                  <th>Derived onset</th>
                  <th>Duration</th>
                  <th>Duration source</th>
                  <th>Derived ongoing</th>
                </tr>
              </thead>
              <tbody>
                {derivedSymptomRows.map((symptom) => (
                  <tr key={symptom.id}>
                    <td>{symptom.symptom_type}</td>
                    <td>{formatDate(symptom.onset_date)}</td>
                    <td>{symptom.date_kind}</td>
                    <td>{formatDate(symptom.derived_onset_date)}</td>
                    <td>
                      {symptom.effective_duration_days === null
                        ? "—"
                        : `${symptom.effective_duration_days} days`}
                    </td>
                    <td>{symptom.duration_source}</td>
                    <td>{symptom.ongoing ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
