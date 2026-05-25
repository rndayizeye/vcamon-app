export type PartnerRead = {
  id: number;
  case_id: number;
  partner_number: number;
  name: string | null;
  reason_for_exam: string | null;
  treatment_date: string | null;
  medical_info: string | null;
  treatment: string | null;
  historical_primary_chancre: boolean | null;
  historical_primary_date: string | null;
  created_at: string | null;
};

export type PartnerCreateInput = {
  name?: string | null;
  partner_number?: number | null;
  reason_for_exam?: string | null;
  treatment_date?: string | null;
  medical_info?: string | null;
  treatment?: string | null;
  historical_primary_chancre?: boolean | null;
  historical_primary_date?: string | null;
};

export type PartnerUpdateInput = Partial<PartnerCreateInput>;

export type CasePartnerRelationshipRead = {
  id: number;
  case_id: number;
  partner_id: number;
  exposure_first_date: string | null;
  exposure_last_date: string | null;
  exposure_modalities: string | null;
};

export type CasePartnerRelationshipCreate = {
  exposure_first_date?: string | null;
  exposure_last_date?: string | null;
  exposure_modalities?: string | null;
};

export type CasePartnerRelationshipUpdate = Partial<CasePartnerRelationshipCreate>;

export type RelationshipReportRead = {
  id: number;
  relationship_id: number;
  reporter: string;
  exposure_first_date: string | null;
  exposure_last_date: string | null;
  exposure_modalities: string | null;
  created_at: string | null;
};

export type RelationshipReportCreate = {
  reporter: string;
  exposure_first_date?: string | null;
  exposure_last_date?: string | null;
  exposure_modalities?: string | null;
};

export type RelationshipReportUpdate = Partial<RelationshipReportCreate>;

export type RelationshipReportWriteInput = RelationshipReportCreate & {
  id?: number;
};
