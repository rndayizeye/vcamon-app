export const PRIMARY_SYMPTOM_TYPE_OPTIONS = [
  "Anal LX",
  "Non-genital LX",
  "LX",
  "Oral LX",
  "Penile LX",
  "Rectal LX",
  "Vaginal LX",
] as const;

export const SECONDARY_SYMPTOM_TYPE_OPTIONS = [
  "Rash",
  "PP Rash",
  "GB Rash",
  "C-lata",
  "Alopecia",
] as const;

export const SYMPTOM_TYPE_OPTIONS = [
  ...PRIMARY_SYMPTOM_TYPE_OPTIONS,
  ...SECONDARY_SYMPTOM_TYPE_OPTIONS,
] as const;

export const SYMPTOM_DATE_KIND_OPTIONS = [
  "Onset reported",
  "Observed during exam (onset unknown)",
] as const;

export const SYMPTOM_DURATION_SOURCE_OPTIONS = [
  "Reported",
  "Assumed max",
  "Unknown",
] as const;

export type SymptomDateKind = (typeof SYMPTOM_DATE_KIND_OPTIONS)[number];
export type SymptomDurationSource =
  (typeof SYMPTOM_DURATION_SOURCE_OPTIONS)[number];

export type SymptomEntryRead = {
  id: number;
  case_id: number | null;
  partner_id: number | null;
  symptom_type: string;
  classification: string | null;
  onset_date: string | null;
  date_kind: SymptomDateKind;
  duration_days: number | null;
  duration_source: SymptomDurationSource;
  ongoing: boolean;
};

export type SymptomEntryWriteInput = {
  id?: number;
  symptom_type: string;
  onset_date: string | null;
  date_kind: SymptomDateKind;
  duration_days: number | null;
};

export type SymptomEntryDraft = {
  id?: number;
  symptom_type: string;
  onset_date: string;
  date_kind: SymptomDateKind;
  duration_days: string;
};

export const EMPTY_SYMPTOM_DRAFT: SymptomEntryDraft = {
  symptom_type: "",
  onset_date: "",
  date_kind: "Onset reported",
  duration_days: "",
};
