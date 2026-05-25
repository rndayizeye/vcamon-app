import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useCreatePartner } from "./hooks";
import { syncPartnerSymptoms } from "../symptoms/api";
import {
  PartnerForm,
  type PartnerFormSubmission,
} from "./components/PartnerForm";

export function PartnerCreatePage() {
  const { caseId } = useParams();
  const safeCaseId = Number(caseId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createPartner = useCreatePartner(safeCaseId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function handleSubmit(payload: PartnerFormSubmission) {
    setSubmitError(null);
    try {
      // 1. Create partner
      const newPartner = await createPartner.mutateAsync(payload.partner);

      // 2. Save symptoms for this partner
      await syncPartnerSymptoms(newPartner.id, [], payload.symptoms);
      await queryClient.invalidateQueries({
        queryKey: ["partners", newPartner.id, "symptoms"],
      });

      // 3. Navigate back to partner list
      navigate(`/cases/${safeCaseId}/partners`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to create partner.";
      setSubmitError(message);
      throw error;
    }
  }

  return (
    <div className="stack-lg">
      <PartnerForm
        mode="create"
        onSubmit={handleSubmit}
        submitting={createPartner.isPending}
        errorMessage={
          submitError ??
          (createPartner.isError ? createPartner.error.message : null)
        }
        cancelTo={`/cases/${safeCaseId}/partners`}
      />
    </div>
  );
}
