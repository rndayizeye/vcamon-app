import { useEffect } from "react";
import { useForm } from "react-hook-form";
import {
  useCasePartnerRelationship,
  useSaveCasePartnerRelationship,
} from "../hooks";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { ErrorState } from "../../../components/feedback/ErrorState";

type RelationshipFormValues = {
  exposure_first_date: string;
  exposure_last_date: string;
  exposure_modalities: string;
};

export function RelationshipEditor({
  caseId,
  partnerId,
}: {
  caseId: number;
  partnerId: number;
}) {
  const query = useCasePartnerRelationship(caseId, partnerId);
  const saveMutation = useSaveCasePartnerRelationship();

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<RelationshipFormValues>({
    defaultValues: {
      exposure_first_date: "",
      exposure_last_date: "",
      exposure_modalities: "",
    },
  });

  useEffect(() => {
    if (query.data) {
      reset({
        exposure_first_date: query.data.exposure_first_date || "",
        exposure_last_date: query.data.exposure_last_date || "",
        exposure_modalities: query.data.exposure_modalities || "",
      });
    }
  }, [query.data, reset]);

  async function handleSave(values: RelationshipFormValues) {
    const isUpdate = !!query.data;
    const payload = {
      exposure_first_date: values.exposure_first_date || null,
      exposure_last_date: values.exposure_last_date || null,
      exposure_modalities: values.exposure_modalities || null,
    };

    await saveMutation.mutateAsync({
      caseId,
      partnerId,
      data: payload,
      isUpdate,
    });
  }

  if (query.isLoading) {
    return (
      <div className="panel stack-sm">
        <h2>Exposure Window</h2>
        <LoadingState message="Loading relationship data…" />
      </div>
    );
  }

  if (query.isError && (query.error as { status?: number })?.status !== 404) {
    return (
      <div className="panel stack-sm">
        <h2>Exposure Window</h2>
        <ErrorState
          title="Error"
          message={query.error?.message}
          onRetry={() => void query.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="panel stack-md">
      <div className="stack-sm">
        <h2>Exposure Window</h2>
        <p className="muted">
          Define the exposure dates for this specific OP ↔ Partner relationship.
        </p>
      </div>

      <form className="stack-md" onSubmit={handleSubmit(handleSave)}>
        <div className="two-column-grid">
          <label className="field">
            <span>Exposure First Date</span>
            <input type="date" {...register("exposure_first_date")} />
          </label>
          <label className="field">
            <span>Exposure Last Date</span>
            <input type="date" {...register("exposure_last_date")} />
          </label>
        </div>

        <label className="field">
          <span>Exposure Modalities</span>
          <textarea
            rows={3}
            placeholder="e.g., Vaginal, Anal, Oral"
            {...register("exposure_modalities")}
          />
        </label>

        {saveMutation.isError && (
          <p className="error-text">
            Failed to save relationship: {saveMutation.error?.message}
          </p>
        )}
        {saveMutation.isSuccess && (
          <p className="text-success">Exposure window saved successfully.</p>
        )}

        <div className="form-actions" style={{ justifyContent: "flex-start" }}>
          <button
            type="submit"
            className="button button-primary"
            disabled={isSubmitting || saveMutation.isPending}
          >
            {isSubmitting || saveMutation.isPending
              ? "Saving…"
              : "Save Exposure Window"}
          </button>
        </div>
      </form>
    </div>
  );
}
