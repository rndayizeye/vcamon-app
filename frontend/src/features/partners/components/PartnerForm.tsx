import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useFieldArray, useForm } from "react-hook-form";

import type {
  SymptomEntryDraft,
  SymptomEntryRead,
  SymptomEntryWriteInput,
} from "../../symptoms/types";
import { deriveHistoricalPrimary, normalizeSymptomDrafts, toSymptomDraft } from "../../symptoms/utils";
import { SymptomEntriesEditor } from "../../cases/components/SymptomEntriesEditor";
import { LabResultsEditor } from "../../cases/components/LabResultsEditor";
import { REASON_FOR_EXAM_OPTIONS, TREATMENT_OPTIONS } from "../../labs/constants";
import type { LabResultEntryRead, LabResultEntryWriteInput } from "../../labs/types";
import type { PartnerCreateInput, PartnerRead, PartnerUpdateInput } from "../types";

export type PartnerFormSubmission = {
  partner: PartnerCreateInput | PartnerUpdateInput;
  symptoms: SymptomEntryWriteInput[];
  nontrepLabs: LabResultEntryWriteInput[];
  trepLabs: LabResultEntryWriteInput[];
};

type LabDraft = Partial<LabResultEntryWriteInput>;

type PartnerFormValues = {
  partner_number: string;
  name: string;
  reason_for_exam: string;
  treatment_date: string;
  treatment: string;
  medical_info: string;
  symptoms: SymptomEntryDraft[];
  nontrepLabs: LabDraft[];
  trepLabs: LabDraft[];
};

const EMPTY_FORM_VALUES: PartnerFormValues = {
  partner_number: "",
  name: "",
  reason_for_exam: "",
  treatment_date: "",
  treatment: "",
  medical_info: "",
  symptoms: [],
  nontrepLabs: [],
  trepLabs: [],
};

function normalizeText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function normalizeDate(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function toLabDraft(lab: LabResultEntryRead): LabDraft {
  return {
    id: lab.id,
    test_type: lab.test_type,
    titer: lab.titer ?? "",
    result: lab.result ?? "",
    collection_date: lab.collection_date,
  };
}

function toFormValues(
  partnerData?: Partial<PartnerRead> | null,
  symptoms: SymptomEntryRead[] = [],
  nontrepLabs: LabResultEntryRead[] = [],
  trepLabs: LabResultEntryRead[] = [],
): PartnerFormValues {
  return {
    partner_number:
      partnerData?.partner_number != null
        ? String(partnerData.partner_number)
        : "",
    name: partnerData?.name || "",
    reason_for_exam: partnerData?.reason_for_exam || "",
    treatment_date: partnerData?.treatment_date || "",
    treatment: partnerData?.treatment || "",
    medical_info: partnerData?.medical_info || "",
    symptoms: symptoms.map(toSymptomDraft),
    nontrepLabs: nontrepLabs.map(toLabDraft),
    trepLabs: trepLabs.map(toLabDraft),
  };
}

function normalizeLabDrafts(
  drafts: LabDraft[],
  testCategory: string,
): LabResultEntryWriteInput[] {
  return drafts
    .filter((d) => d.test_type && d.test_type.trim())
    .map((d) => ({
      ...d,
      test_category: testCategory,
      test_type: d.test_type!.trim(),
      collection_date: d.collection_date || "",
    }));
}

function toPartnerPayload(
  values: PartnerFormValues,
  symptoms: SymptomEntryWriteInput[],
): PartnerCreateInput {
  const partnerNumber = values.partner_number.trim();
  const historicalPrimary = deriveHistoricalPrimary(
    symptoms,
    values.treatment_date || null,
  );

  return {
    partner_number: partnerNumber ? Number(partnerNumber) : null,
    name: normalizeText(values.name),
    reason_for_exam: normalizeText(values.reason_for_exam),
    treatment_date: normalizeDate(values.treatment_date),
    treatment: normalizeText(values.treatment),
    medical_info: normalizeText(values.medical_info),
    historical_primary_chancre: historicalPrimary.historical_primary_chancre,
    historical_primary_date: historicalPrimary.historical_primary_date,
  };
}

export function PartnerForm({
  mode,
  initialPartner,
  initialSymptoms = [],
  initialNontrepLabs = [],
  initialTrepLabs = [],
  onSubmit,
  submitting,
  errorMessage,
  cancelTo,
}: {
  mode: "create" | "edit";
  initialPartner?: Partial<PartnerRead> | null;
  initialSymptoms?: SymptomEntryRead[];
  initialNontrepLabs?: LabResultEntryRead[];
  initialTrepLabs?: LabResultEntryRead[];
  onSubmit: (payload: PartnerFormSubmission) => Promise<void> | void;
  submitting: boolean;
  errorMessage?: string | null;
  cancelTo: string;
}) {
  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm<PartnerFormValues>({
    defaultValues: toFormValues(
      initialPartner,
      initialSymptoms,
      initialNontrepLabs,
      initialTrepLabs,
    ),
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "symptoms",
    keyName: "formId",
  });

  useEffect(() => {
    reset(
      toFormValues(
        initialPartner,
        initialSymptoms,
        initialNontrepLabs,
        initialTrepLabs,
      ),
    );
  }, [initialPartner, initialSymptoms, initialNontrepLabs, initialTrepLabs, reset]);

  async function handleFormSubmit(values: PartnerFormValues) {
    clearErrors("root");
    try {
      const normalizedSymptoms = normalizeSymptomDrafts(values.symptoms);
      const normalizedNontrepLabs = normalizeLabDrafts(
        values.nontrepLabs,
        "Non-treponemal",
      );
      const normalizedTrepLabs = normalizeLabDrafts(
        values.trepLabs,
        "Treponemal",
      );
      await onSubmit({
        partner: toPartnerPayload(values, normalizedSymptoms),
        symptoms: normalizedSymptoms,
        nontrepLabs: normalizedNontrepLabs,
        trepLabs: normalizedTrepLabs,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to save the partner.";
      setError("root", { type: "validate", message });
    }
  }

  return (
    <form className="panel stack-md" onSubmit={handleSubmit(handleFormSubmit)}>
      <div className="stack-sm">
        <div>
          <p className="eyebrow">
            {mode === "create" ? "New partner" : "Edit partner"}
          </p>
          <h2>{mode === "create" ? "Create partner" : "Update partner"}</h2>
        </div>
        <p className="muted">
          Exposure dates belong to the OP ↔ Partner relationship, not the
          partner record. Set them in the Exposure Window section below after
          saving.
        </p>
      </div>

      <div className="two-column-grid">
        <label className="field">
          <span>Partner number</span>
          <input
            type="number"
            min="1"
            placeholder="e.g., 1"
            {...register("partner_number")}
          />
          <span className="muted small-text">
            Leave blank to auto-assign the next number.
          </span>
        </label>

        <label className="field">
          <span>Name</span>
          <input type="text" placeholder="Smith, John" {...register("name")} />
        </label>

        <label className="field">
          <span>Reason for exam</span>
          <select {...register("reason_for_exam")}>
            <option value="">Select reason</option>
            {REASON_FOR_EXAM_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Treatment given</span>
          <select {...register("treatment")}>
            <option value="">Select...</option>
            {TREATMENT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Treatment date</span>
          <input type="date" {...register("treatment_date")} />
        </label>

      </div>

      <label className="field">
        <span>Medical info</span>
        <textarea
          rows={5}
          placeholder="Add relevant medical notes or treatment context"
          {...register("medical_info")}
        />
      </label>

      <SymptomEntriesEditor
        fields={fields}
        append={append}
        remove={remove}
        register={
          register as Parameters<typeof SymptomEntriesEditor>[0]["register"]
        }
        disabled={submitting}
      />

      <LabResultsEditor
        control={control as Parameters<typeof LabResultsEditor>[0]["control"]}
        nontrepName="nontrepLabs"
        trepName="trepLabs"
      />

      {errors.root?.message ? (
        <p className="error-text">{errors.root.message}</p>
      ) : null}
      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      <div className="form-actions">
        <button
          className="button button-primary"
          type="submit"
          disabled={submitting}
        >
          {submitting
            ? mode === "create"
              ? "Creating…"
              : "Saving…"
            : mode === "create"
              ? "Create partner"
              : "Save changes"}
        </button>
        <Link className="button" to={cancelTo}>
          Cancel
        </Link>
      </div>
    </form>
  );
}
