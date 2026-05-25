import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../auth/use-auth";
import { ErrorState } from "../../components/feedback/ErrorState";
import { syncCaseSymptoms } from "../symptoms/api";
import { syncCaseLabs } from "../labs/api";
import type { CaseFormSubmission } from "./types";
import { CaseForm } from "./components/CaseForm";
import { useCreateCase } from "./hooks";

export function CaseCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const createMutation = useCreateCase();
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (!permissions.can_write) {
    return (
      <ErrorState
        title="Write access required"
        message="You do not have permission to create cases."
      />
    );
  }

  async function handleCreate(payload: CaseFormSubmission) {
    setSubmitError(null);

    try {
      const createdCase = await createMutation.mutateAsync(payload.case);
      await Promise.all([
        syncCaseSymptoms(createdCase.id, [], payload.symptoms),
        syncCaseLabs(createdCase.id, [], [...payload.nontrepLabs, ...payload.trepLabs]),
      ]);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["cases", createdCase.id, "symptoms"] }),
        queryClient.invalidateQueries({ queryKey: ["cases", createdCase.id, "labs"] }),
      ]);
      navigate(`/cases/${createdCase.id}/overview`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to create case.";
      setSubmitError(message);
      throw error;
    }
  }

  return (
    <section className="stack-lg">
      <header className="stack-sm">
        <div>
          <p className="eyebrow">Cases</p>
          <h1>Create case</h1>
        </div>
        <p className="muted">
          Start a new case using <code>diagnosis_code</code>. Pair-specific
          exposure dates will live on the OP-partner relationship, not on this
          case form.
        </p>
      </header>

      <CaseForm
        mode="create"
        onSubmit={handleCreate}
        submitting={createMutation.isPending}
        errorMessage={
          submitError ??
          (createMutation.isError ? createMutation.error.message : null)
        }
        cancelTo="/cases"
      />
    </section>
  );
}
