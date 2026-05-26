import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import {
  useCasePartnerRelationship,
  useSaveCasePartnerRelationship,
} from "../hooks";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { ErrorState } from "../../../components/feedback/ErrorState";

const BODY_PARTS = [
  { value: "penis", label: "Penis" },
  { value: "vagina", label: "Vagina / Vulva" },
  { value: "anus", label: "Anus / Rectum" },
  { value: "mouth", label: "Mouth" },
] as const;

type BodyPart = (typeof BODY_PARTS)[number]["value"];

type RelationshipFormValues = {
  exposure_first_date: string;
  exposure_last_date: string;
  op_body_parts: BodyPart[];
  partner_body_parts: BodyPart[];
};

function BodyPartsGrid({
  opParts,
  partnerParts,
  onOpChange,
  onPartnerChange,
}: {
  opParts: BodyPart[];
  partnerParts: BodyPart[];
  onOpChange: (parts: BodyPart[]) => void;
  onPartnerChange: (parts: BodyPart[]) => void;
}) {
  function toggle(current: BodyPart[], part: BodyPart): BodyPart[] {
    return current.includes(part)
      ? current.filter((p) => p !== part)
      : [...current, part];
  }

  return (
    <fieldset className="field">
      <legend>Reported sexual contact</legend>
      <p className="muted" style={{ marginBottom: "0.75rem", fontSize: "0.875rem" }}>
        Select the body parts each person reported using during contact.
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", paddingBottom: "0.5rem", width: "50%" }} />
            <th style={{ textAlign: "center", paddingBottom: "0.5rem", width: "25%", fontWeight: 600 }}>
              OP
            </th>
            <th style={{ textAlign: "center", paddingBottom: "0.5rem", width: "25%", fontWeight: 600 }}>
              Partner
            </th>
          </tr>
        </thead>
        <tbody>
          {BODY_PARTS.map(({ value, label }) => (
            <tr key={value} style={{ borderTop: "1px solid var(--border, #e5e7eb)" }}>
              <td style={{ padding: "0.5rem 0", fontSize: "0.9rem" }}>{label}</td>
              <td style={{ textAlign: "center" }}>
                <input
                  type="checkbox"
                  checked={opParts.includes(value)}
                  onChange={() => onOpChange(toggle(opParts, value))}
                />
              </td>
              <td style={{ textAlign: "center" }}>
                <input
                  type="checkbox"
                  checked={partnerParts.includes(value)}
                  onChange={() => onPartnerChange(toggle(partnerParts, value))}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </fieldset>
  );
}

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
    control,
    formState: { isSubmitting },
  } = useForm<RelationshipFormValues>({
    defaultValues: {
      exposure_first_date: "",
      exposure_last_date: "",
      op_body_parts: [],
      partner_body_parts: [],
    },
  });

  useEffect(() => {
    if (query.data) {
      reset({
        exposure_first_date: query.data.exposure_first_date || "",
        exposure_last_date: query.data.exposure_last_date || "",
        op_body_parts: (query.data.op_body_parts ?? []) as BodyPart[],
        partner_body_parts: (query.data.partner_body_parts ?? []) as BodyPart[],
      });
    }
  }, [query.data, reset]);

  async function handleSave(values: RelationshipFormValues) {
    const isUpdate = !!query.data;
    const payload = {
      exposure_first_date: values.exposure_first_date || null,
      exposure_last_date: values.exposure_last_date || null,
      op_body_parts: values.op_body_parts,
      partner_body_parts: values.partner_body_parts,
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
          Define the exposure dates and sexual contact for this OP ↔ Partner relationship.
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

        <Controller
          control={control}
          name="op_body_parts"
          render={({ field: opField }) => (
            <Controller
              control={control}
              name="partner_body_parts"
              render={({ field: partnerField }) => (
                <BodyPartsGrid
                  opParts={opField.value}
                  partnerParts={partnerField.value}
                  onOpChange={opField.onChange}
                  onPartnerChange={partnerField.onChange}
                />
              )}
            />
          )}
        />

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
            {isSubmitting || saveMutation.isPending ? "Saving…" : "Save Exposure Window"}
          </button>
        </div>
      </form>
    </div>
  );
}
