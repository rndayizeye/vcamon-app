import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useFieldArray, useForm } from "react-hook-form";

import type { SymptomEntryDraft, SymptomEntryRead } from "../../symptoms/types";
import {
  deriveHistoricalPrimary,
  normalizeSymptomDrafts,
  toSymptomDraft,
} from "../../symptoms/utils";
import type { LabResultEntryRead, LabResultEntryWriteInput } from "../../labs/types";
import {
  REASON_FOR_EXAM_OPTIONS,
  TREATMENT_OPTIONS,
} from "../../labs/constants";
import type { CaseCreateInput, CaseFormSubmission, CaseRead } from "../types";
import { LabResultsEditor } from "./LabResultsEditor";
import { SymptomEntriesEditor } from "./SymptomEntriesEditor";

const DIAGNOSIS_CODE_OPTIONS = ["700", "710", "720", "730", "755"] as const;

type LabDraft = Partial<LabResultEntryWriteInput>;

type CaseFormValues = {
  patient_name: string;
  diagnosis_code: string;
  case_manager: string;
  treatment_date: string;
  medical_info: string;
  reason_for_exam: string;
  treatment: string;
  symptoms: SymptomEntryDraft[];
  nontrepLabs: LabDraft[];
  trepLabs: LabDraft[];
};

const EMPTY_FORM_VALUES: CaseFormValues = {
  patient_name: "",
  diagnosis_code: "",
  case_manager: "",
  treatment_date: "",
  medical_info: "",
  reason_for_exam: "",
  treatment: "",
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
  caseData?: Partial<CaseRead> | null,
  symptoms: SymptomEntryRead[] = [],
  initialNontrepLabs: LabResultEntryRead[] = [],
  initialTrepLabs: LabResultEntryRead[] = [],
): CaseFormValues {
  if (!caseData) {
    return {
      ...EMPTY_FORM_VALUES,
      symptoms: symptoms.map(toSymptomDraft),
      nontrepLabs: initialNontrepLabs.map(toLabDraft),
      trepLabs: initialTrepLabs.map(toLabDraft),
    };
  }

  return {
    patient_name: caseData.patient_name || "",
    diagnosis_code: caseData.diagnosis_code || caseData.lot || "",
    case_manager: caseData.case_manager || "",
    treatment_date: caseData.treatment_date || "",
    medical_info: caseData.medical_info || "",
    reason_for_exam: caseData.reason_for_exam || "",
    treatment: "",
    symptoms: symptoms.map(toSymptomDraft),
    nontrepLabs: initialNontrepLabs.map(toLabDraft),
    trepLabs: initialTrepLabs.map(toLabDraft),
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

function toCasePayload(
  values: CaseFormValues,
  symptoms: CaseFormSubmission["symptoms"],
): CaseCreateInput {
  const treatmentDate = normalizeDate(values.treatment_date);
  const historicalPrimary = deriveHistoricalPrimary(symptoms, treatmentDate);

  return {
    patient_name: values.patient_name.trim(),
    diagnosis_code: normalizeText(values.diagnosis_code),
    case_manager: normalizeText(values.case_manager),
    treatment_date: treatmentDate,
    medical_info: normalizeText(values.medical_info),
    reason_for_exam: normalizeText(values.reason_for_exam),
    treatment: normalizeText(values.treatment),
    historical_primary_chancre: historicalPrimary.historical_primary_chancre,
    historical_primary_date: historicalPrimary.historical_primary_date,
  };
}

export function CaseForm({
  mode,
  initialCase,
  initialSymptoms = [],
  initialNontrepLabs = [],
  initialTrepLabs = [],
  onSubmit,
  submitting,
  errorMessage,
  cancelTo,
}: {
  mode: "create" | "edit";
  initialCase?: Partial<CaseRead> | null;
  initialSymptoms?: SymptomEntryRead[];
  initialNontrepLabs?: LabResultEntryRead[];
  initialTrepLabs?: LabResultEntryRead[];
  onSubmit: (payload: CaseFormSubmission) => Promise<void> | void;
  submitting: boolean;
  errorMessage?: string | null;
  cancelTo: string;
}) {
  const currentDiagnosisCode =
    initialCase?.diagnosis_code || initialCase?.lot || "";
  const diagnosisOptions = currentDiagnosisCode
    ? Array.from(new Set([currentDiagnosisCode, ...DIAGNOSIS_CODE_OPTIONS]))
    : [...DIAGNOSIS_CODE_OPTIONS];

  const {
    control,
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm<CaseFormValues>({
    defaultValues: toFormValues(initialCase, initialSymptoms, initialNontrepLabs, initialTrepLabs),
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "symptoms",
    keyName: "formId",
  });

  useEffect(() => {
    reset(toFormValues(initialCase, initialSymptoms, initialNontrepLabs, initialTrepLabs));
  }, [initialCase, initialSymptoms, initialNontrepLabs, initialTrepLabs, reset]);

  async function handleFormSubmit(values: CaseFormValues) {
    clearErrors("root");

    try {
      const normalizedSymptoms = normalizeSymptomDrafts(values.symptoms);
      const normalizedNontrepLabs = normalizeLabDrafts(values.nontrepLabs, "Non-treponemal");
      const normalizedTrepLabs = normalizeLabDrafts(values.trepLabs, "Treponemal");
      await onSubmit({
        case: toCasePayload(values, normalizedSymptoms),
        symptoms: normalizedSymptoms,
        nontrepLabs: normalizedNontrepLabs,
        trepLabs: normalizedTrepLabs,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unable to save the case.";
      setError("root", { type: "validate", message });
    }
  }

  return (
    <form className="panel stack-md" onSubmit={handleSubmit(handleFormSubmit)}>
      <div className="stack-sm">
        <div>
          <p className="eyebrow">
            {mode === "create" ? "New case" : "Edit case"}
          </p>
          <h2>{mode === "create" ? "Create case" : "Update case"}</h2>
        </div>
        <p className="muted">
          New React case forms should use <code>diagnosis_code</code>. Exposure
          dates are not collected here because they belong to each OP-partner
          relationship, not the case record itself.
        </p>
      </div>

      <div className="two-column-grid">
        <label className="field">
          <span>Patient name</span>
          <input
            type="text"
            placeholder="Doe, Jane"
            {...register("patient_name", {
              required: "Patient name is required.",
              validate: (value) =>
                value.trim().length > 0 || "Patient name is required.",
            })}
          />
          {errors.patient_name?.message ? (
            <span className="error-text">{errors.patient_name.message}</span>
          ) : null}
        </label>

        <label className="field">
          <span>Diagnosis code</span>
          <select {...register("diagnosis_code")}>
            <option value="">Select a diagnosis code</option>
            {diagnosisOptions.map((option) => (
              <option key={option} value={option}>
                {DIAGNOSIS_CODE_OPTIONS.includes(
                  option as (typeof DIAGNOSIS_CODE_OPTIONS)[number],
                )
                  ? option
                  : `${option} (legacy value)`}
              </option>
            ))}
          </select>
          <span className="muted small-text">
            Allowed values currently include 700, 710, 720, 730, and 755.
          </span>
        </label>

        <label className="field">
          <span>Case manager</span>
          <input
            type="text"
            placeholder="Taylor"
            {...register("case_manager")}
          />
        </label>

        <label className="field">
          <span>Treatment date</span>
          <input type="date" {...register("treatment_date")} />
        </label>

        <label className="field">
          <span>Reason for exam</span>
          <select {...register("reason_for_exam")}>
            <option value="">Select...</option>
            {REASON_FOR_EXAM_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Treatment given</span>
          <select {...register("treatment")}>
            <option value="">Select...</option>
            {TREATMENT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
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
        <SymptomEntriesEditor
          fields={fields}
          append={append}
          remove={remove}
          register={register as any}
          disabled={submitting}
        />
      </div>

      <div className="stack-md">
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
              ? "Create case"
              : "Save changes"}
        </button>
        <Link className="button" to={cancelTo}>
          Cancel
        </Link>
      </div>
    </form>
  );
}
