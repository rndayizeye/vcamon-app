import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { usePartner, useLinkPartnerToCase, useUpdatePartner } from "./hooks";
import { usePartnerSymptoms } from "../symptoms/hooks";
import { syncPartnerSymptoms } from "../symptoms/api";
import { syncPartnerLabs } from "./labs-api";
import { usePartnerLabs } from "./labs-hooks";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import {
  PartnerForm,
  type PartnerFormSubmission,
} from "./components/PartnerForm";
import { RelationshipEditor } from "./components/RelationshipEditor";

export function PartnerEditPage() {
  const { caseId, partnerId } = useParams();
  const safeCaseId = Number(caseId);
  const safePartnerId = Number(partnerId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const partnerQuery = usePartner(safePartnerId);
  const symptomsQuery = usePartnerSymptoms(safePartnerId);
  const labsQuery = usePartnerLabs(safePartnerId);
  const updatePartner = useUpdatePartner();
  const linkPartner = useLinkPartnerToCase();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [linkedCaseInput, setLinkedCaseInput] = useState("")
  const [linkError, setLinkError] = useState<string | null>(null);

  const initialSymptoms = useMemo(() => symptomsQuery.data ?? [], [symptomsQuery.data]);
  const initialNontrepLabs = useMemo(
    () => labsQuery.data?.filter(l => l.test_category === "Non-treponemal") ?? [],
    [labsQuery.data],
  );
  const initialTrepLabs = useMemo(
    () => labsQuery.data?.filter(l => l.test_category === "Treponemal") ?? [],
    [labsQuery.data],
  );

  if (partnerQuery.isLoading || symptomsQuery.isLoading || labsQuery.isLoading) {
    return <LoadingState message="Loading partner data…" />;
  }

  if (partnerQuery.isError || symptomsQuery.isError || labsQuery.isError) {
    return (
      <ErrorState
        title="Failed to load partner"
        message={
          partnerQuery.error?.message ||
          symptomsQuery.error?.message ||
          labsQuery.error?.message ||
          "Unknown error"
        }
      />
    );
  }

  if (!partnerQuery.data) {
    return (
      <ErrorState
        title="Partner not found"
        message="The requested partner could not be found."
      />
    );
  }

  async function handleSubmit(payload: PartnerFormSubmission) {
    setSubmitError(null);
    try {
      // 1. Update partner
      await updatePartner.mutateAsync({
        partnerId: safePartnerId,
        data: payload.partner,
      });

      // 2. Save symptoms and labs in parallel
      await Promise.all([
        syncPartnerSymptoms(
          safePartnerId,
          symptomsQuery.data ?? [],
          payload.symptoms,
        ),
        syncPartnerLabs(
          safePartnerId,
          labsQuery.data ?? [],
          [...payload.nontrepLabs, ...payload.trepLabs],
        ),
      ]);

      await queryClient.invalidateQueries({
        queryKey: ["partners", safePartnerId, "symptoms"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["partners", safePartnerId, "labs"],
      });

      // 3. Navigate back
      navigate(`/cases/${safeCaseId}/partners`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to save partner.";
      setSubmitError(message);
      throw error;
    }
  }

  return (
    <div className="stack-lg">
      <PartnerForm
        mode="edit"
        initialPartner={partnerQuery.data}
        initialSymptoms={initialSymptoms}
        initialNontrepLabs={initialNontrepLabs}
        initialTrepLabs={initialTrepLabs}
        onSubmit={handleSubmit}
        submitting={updatePartner.isPending}
        errorMessage={
          submitError ??
          (updatePartner.isError ? updatePartner.error.message : null)
        }
        cancelTo={`/cases/${safeCaseId}/partners`}
      />

      <RelationshipEditor caseId={safeCaseId} partnerId={safePartnerId} />

      <div className="card stack-md">
        <h3>Linked Case</h3>
        {partnerQuery.data?.linked_case_id ? (
          <div className="cluster" style={{ alignItems: "center", gap: "var(--spacing-md)" }}>
            <span>
              Linked to{" "}
              <a href={`/cases/${partnerQuery.data.linked_case_id}`} style={{ fontWeight: 600 }}>
                Case #{partnerQuery.data.linked_case_id}
              </a>
            </span>
            <button
              className="button button-secondary"
              style={{ fontSize: "0.8rem" }}
              disabled={linkPartner.isPending}
              onClick={() => {
                setLinkError(null);
                linkPartner.mutate(
                  { partnerId: safePartnerId, linkedCaseId: null },
                  { onError: (e) => setLinkError(e instanceof Error ? e.message : "Failed to unlink") },
                );
              }}
            >
              Unlink
            </button>
          </div>
        ) : (
          <div className="cluster" style={{ alignItems: "flex-end", gap: "var(--spacing-md)" }}>
            <div className="stack-sm" style={{ flex: 1 }}>
              <label htmlFor="linked-case-id" style={{ fontWeight: 500 }}>
                Link to Case ID
              </label>
              <input
                id="linked-case-id"
                type="number"
                className="input"
                placeholder="Enter case ID…"
                value={linkedCaseInput}
                onChange={(e) => setLinkedCaseInput(e.target.value)}
              />
            </div>
            <button
              className="button button-primary"
              disabled={!linkedCaseInput || linkPartner.isPending}
              onClick={() => {
                setLinkError(null);
                const id = parseInt(linkedCaseInput, 10);
                if (!id) return;
                linkPartner.mutate(
                  { partnerId: safePartnerId, linkedCaseId: id },
                  {
                    onSuccess: () => setLinkedCaseInput(""),
                    onError: (e) => setLinkError(e instanceof Error ? e.message : "Failed to link"),
                  },
                );
              }}
            >
              {linkPartner.isPending ? "Linking…" : "Link"}
            </button>
          </div>
        )}
        {linkError && <p style={{ color: "var(--color-error, red)", fontSize: "0.85rem" }}>{linkError}</p>}
        <p className="text-secondary" style={{ fontSize: "0.8rem" }}>
          When this partner has their own case record, link it here to track transmission relationships across cases.
        </p>
      </div>
    </div>
  );
}
