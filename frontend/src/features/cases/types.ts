export type CaseSummary = {
  id: number;
  patient_name: string;
  diagnosis_code: string | null;
  lot: string | null;
  case_manager: string | null;
  initial_contact_date: string | null;
  updated_at: string | null;
  reason_for_exam: string | null;
  treatment_date: string | null;
  partner_count: number;
};

export type DashboardSummary = {
  total_cases: number;
  total_partners: number;
  treated_count: number;
  untreated_count: number;
};

export type LabResultEntry = {
  id: number;
  test_category: string;
  test_type: string;
  collection_date: string;
  titer: string | null;
  result: string | null;
};

export type CaseWriteFields = {
  diagnosis_code?: string | null;
  case_manager?: string | null;
  initial_contact_date?: string | null;
  reason_for_exam?: string | null;
  treatment_date?: string | null;
  medical_info?: string | null;
  treatment?: string | null;
  historical_primary_chancre?: boolean | null;
  historical_primary_date?: string | null;
};

export type CaseCreateInput = CaseWriteFields & {
  patient_name: string;
};

export type CaseUpdateInput = Partial<
  CaseWriteFields & {
    patient_name: string;
  }
>;

export type CaseFormSubmission = {
  case: CaseCreateInput;
  symptoms: import("../symptoms/types").SymptomEntryWriteInput[];
  nontrepLabs: import("../labs/types").LabResultEntryWriteInput[];
  trepLabs: import("../labs/types").LabResultEntryWriteInput[];
};

export type CaseRead = {
  id: number;
  patient_name: string;
  diagnosis_code: string | null;
  lot: string | null;
  case_manager: string | null;
  initial_contact_date: string | null;
  reason_for_exam: string | null;
  treatment_date: string | null;
  medical_info: string | null;
  symptom_onset_date: string | null;
  historical_primary_chancre: boolean | null;
  historical_primary_date: string | null;
  created_at: string | null;
  updated_at: string | null;
};
