import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../auth/use-auth";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { syncCaseSymptoms } from "../symptoms/api";
import { useCaseSymptoms } from "../symptoms/hooks";
import { syncCaseLabs } from "../labs/api";
import { useCaseLabs } from "../labs/hooks";
import type { CaseFormSubmission } from "./types";
import { CaseForm } from "./components/CaseForm";
import { useCase, useUpdateCase } from "./hooks";

export function CaseEditPage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const parsedCaseId = Number(caseId);
  const safeCaseId =
    Number.isInteger(parsedCaseId) && parsedCaseId > 0 ? parsedCaseId : 0;

  const caseQuery = useCase(safeCaseId);
  const symptomsQuery = useCaseSymptoms(safeCaseId);
  const labsQuery = useCaseLabs(safeCaseId);
  const updateMutation = useUpdateCase(safeCaseId);

  const initialSymptoms = useMemo(() => symptomsQuery.data ?? [], [symptomsQuery.data]);
  const initialNontrepLabs = useMemo(
    () => labsQuery.data?.filter(l => l.test_category === "Non-treponemal") ?? [],
    [labsQuery.data],
  );
  const initialTrepLabs = useMemo(
    () => labsQuery.data?.filter(l => l.test_category === "Treponemal") ?? [],
    [labsQuery.data],
  );

  if (!permissions.can_write) {
    return (
      <ErrorState
        title="Write access required"
        message="You do not have permission to edit cases."
      />
    );
  }

  if (safeCaseId === 0) {
    return (
      <ErrorState title="Invalid case" message="The case id is not valid." />
    );
  }

  if (caseQuery.isLoading || symptomsQuery.isLoading || labsQuery.isLoading) {
    return <LoadingState message="Loading case for editing…" />;
  }

  if (caseQuery.isError) {
    return (
      <ErrorState
        title="Unable to load case"
        message={caseQuery.error.message}
        onRetry={() => void caseQuery.refetch()}
      />
    );
  }

  if (symptomsQuery.isError) {
    return (
      <ErrorState
        title="Unable to load symptoms"
        message={symptomsQuery.error.message}
        onRetry={() => void symptomsQuery.refetch()}
      />
    );
  }

  if (labsQuery.isError) {
    return (
      <ErrorState
        title="Unable to load labs"
        message={labsQuery.error.message}
        onRetry={() => void labsQuery.refetch()}
      />
    );
  }

  if (!caseQuery.data) {
    return (
      <ErrorState title="Case not found" message="No case was returned." />
    );
  }

  async function handleUpdate(payload: CaseFormSubmission) {
    setSubmitError(null);

    try {
      const updatedCase = await updateMutation.mutateAsync(payload.case);

      await Promise.all([
        syncCaseSymptoms(
          updatedCase.id,
          symptomsQuery.data || [],
          payload.symptoms,
        ),
        syncCaseLabs(
          updatedCase.id,
          labsQuery.data || [],
          [...payload.nontrepLabs, ...payload.trepLabs],
        ),
      ]);

      await queryClient.invalidateQueries({
        queryKey: ["cases", updatedCase.id, "symptoms"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["cases", updatedCase.id, "labs"],
      });

      navigate(`/cases/${updatedCase.id}/overview`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to update case.";
      setSubmitError(message);
      throw error;
    }
  }

  return (
    <section className="stack-lg">
      <header className="stack-sm">
        <div>
          <p className="eyebrow">Cases</p>
          <h1>Edit case</h1>
        </div>
        <p className="muted">
          Update the case record. Exposure dates with sexual contacts are recorded separately on each partner relationship.
        </p>
      </header>

      <CaseForm
        mode="edit"
        initialCase={caseQuery.data}
        initialSymptoms={initialSymptoms}
        initialNontrepLabs={initialNontrepLabs}
        initialTrepLabs={initialTrepLabs}
        onSubmit={handleUpdate}
        submitting={updateMutation.isPending}
        errorMessage={
          submitError ??
          (updateMutation.isError ? updateMutation.error.message : null)
        }
        cancelTo={`/cases/${caseQuery.data.id}/overview`}
      />
    </section>
  );
}
