import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useFieldArray, useForm } from "react-hook-form";

import { normalizeSymptomDrafts, toSymptomDraft } from "../../symptoms/utils";
import { SymptomEntriesEditor } from "../../cases/components/SymptomEntriesEditor";
import { LabResultsEditor } from "../../cases/components/LabResultsEditor";
import {
  REASON_FOR_EXAM_OPTIONS,
  TREATMENT_OPTIONS,
} from "../../labs/constants";
import type {
  PartnerCreateInput,
  PartnerRead,
  PartnerUpdateInput,
} from "../types";
import type { SymptomEntryWriteInput } from "../../symptoms/types";
import type { LabResultEntryWriteInput } from "../../labs/types";

export type PartnerFormSubmission = {
  partner: PartnerCreateInput | PartnerUpdateInput;
  symptoms: SymptomEntryWriteInput[];
  nontrepLabs: LabResultEntryWriteInput[];
  trepLabs: LabResultEntryWriteInput[];
};

type PartnerFormValues = {
  partner_number: number | null;
  name: string;
  reason_for_exam: string;
  treatment_date: string;
  treatment: string;
  medical_info: string;
  historical_primary_chancre: boolean;
  historical_primary_date: string;
  exposure_first_date: string;
  exposure_last_date: string;
  exposure_modalities: string;
  symptoms: any[];
  nontrepLabs: any[];
  trepLabs: any[];
};

const EMPTY_FORM_VALUES: PartnerFormValues = {
  partner_number: null,
  name: "",
  reason_for_exam: "",
  treatment_date: "",
  treatment: "",
  medical_info: "",
  historical_primary_chancre: false,
  historical_primary_date: "",
  exposure_first_date: "",
  exposure_last_date: "",
  exposure_modalities: "",
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

function toFormValues(
  partnerData?: Partial<PartnerRead> | null,
  symptoms: any[] = [],
  nontrepLabs: any[] = [],
  trepLabs: any[] = [],
  relationship?: any,
): PartnerFormValues {
  if (!partnerData) {
    return {
      ...EMPTY_FORM_VALUES,
      symptoms: symptoms.map(toSymptomDraft),
      nontrepLabs,
      trepLabs,
    };
  }

  return {
    partner_number: partnerData.partner_number ?? null,
    name: partnerData.name || "",
    reason_for_exam: partnerData.reason_for_exam || "",
    treatment_date: partnerData.treatment_date || "",
    treatment: partnerData.treatment || "",
    medical_info: partnerData.medical_info || "",
    historical_primary_chancre: partnerData.historical_primary_chancre ?? false,
    historical_primary_date: partnerData.historical_primary_date || "",
    exposure_first_date: relationship?.exposure_first_date || "",
    exposure_last_date: relationship?.exposure_last_date || "",
    exposure_modalities: relationship?.exposure_modalities || "",
    symptoms: symptoms.map(toSymptomDraft),
    nontrepLabs,
    trepLabs,
  };
}

function toPartnerPayload(values: PartnerFormValues): PartnerCreateInput {
  return {
    partner_number: values.partner_number
      ? Number(values.partner_number)
      : null,
    name: normalizeText(values.name),
    reason_for_exam: normalizeText(values.reason_for_exam),
    treatment_date: normalizeDate(values.treatment_date),
    treatment: normalizeText(values.treatment),
    medical_info: normalizeText(values.medical_info),
    historical_primary_chancre: values.historical_primary_chancre,
    historical_primary_date: normalizeDate(values.historical_primary_date),
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
  initialSymptoms?: any[];
  initialNontrepLabs?: any[];
  initialTrepLabs?: any[];
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
    defaultValues: toFormValues(initialPartner, initialSymptoms, initialNontrepLabs, initialTrepLabs),
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "symptoms",
    keyName: "formId",
  });

  useEffect(() => {
    reset(toFormValues(initialPartner, initialSymptoms, initialNontrepLabs, initialTrepLabs));
  }, [initialPartner, initialSymptoms, initialNontrepLabs, initialTrepLabs, reset]);

  async function handleFormSubmit(values: PartnerFormValues) {
    clearErrors("root");

    try {
      const normalizedSymptoms = normalizeSymptomDrafts(values.symptoms);
      await onSubmit({
        partner: toPartnerPayload(values),
        symptoms: normalizedSymptoms,
        nontrepLabs: values.nontrepLabs,
        trepLabs: values.trepLabs,
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
      </div>

      <div className="two-column-grid">
        <label className="field">
          <span>Partner number</span>
          <input
            type="number"
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
          <span>Treatment date</span>
          <input type="date" {...register("treatment_date")} />
        </label>

        <label className="field">
          <span>Reason for exam</span>
          <select {...register("reason_for_exam")}>
            <option value="">Select reason</option>
            {REASON_FOR_EXAM_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </label>
      </div>

      <div className="two-column-grid">
        <label className="field">
          <span>Treatment given</span>
          <select {...register("treatment")}>
            <option value="">Select...</option>
            {TREATMENT_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </label>

        <label className="field">
          <span>Historical Primary Chancre?</span>
          <select {...register("historical_primary_chancre")}>
            <option value="">Select...</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </label>

        <label className="field">
          <span>Historical Primary Date</span>
          <input type="date" {...register("historical_primary_date")} />
        </label>
      </div>

      <div className="stack-md panel p-4 bg-gray-50 rounded-lg border">
        <h3 className="font-bold">Exposure Window</h3>
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
        <label className="field mt-4">
          <span>Exposure Modalities</span>
          <input
            type="text"
            placeholder="e.g., Anal, Oral"
            {...register("exposure_modalities")}
          />
          <span className="muted small-text">Comma separated list of modalities.</span>
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

      <div className="stack-md">
        <h3 className="font-bold">Symptoms</h3>
        <SymptomEntriesEditor
          fields={fields}
          append={append}
          remove={remove}
          register={register as Parameters<typeof SymptomEntriesEditor>[0]["register"]}
          disabled={submitting}
        />
      </div>

      <div className="stack-md">
        <h3 className="font-bold">Lab Results</h3>
        <LabResultsEditor
          control={control as Parameters<typeof LabResultsEditor>[0]["control"]}
          nontrepName="nontrepLabs"
          trepName="trepLabs"
        />
      </div>

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
