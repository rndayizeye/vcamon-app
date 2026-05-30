import { apiFetch } from "../../lib/api-client";
import type {
  CasePartnerRelationshipCreate,
  CasePartnerRelationshipRead,
  CasePartnerRelationshipUpdate,
  PartnerCreateInput,
  PartnerRead,
  PartnerUpdateInput,
} from "./types";

export const getPartnersForCase = async (
  caseId: number,
): Promise<PartnerRead[]> => {
  return apiFetch(`/api/cases/${caseId}/partners`);
};

export const createPartner = async (
  caseId: number,
  data: PartnerCreateInput,
): Promise<PartnerRead> => {
  return apiFetch(`/api/cases/${caseId}/partners`, {
    method: "POST",
    body: JSON.stringify(data),
  });
};

export const getPartner = async (partnerId: number): Promise<PartnerRead> => {
  return apiFetch(`/api/cases/partners/${partnerId}`);
};

export const updatePartner = async (
  partnerId: number,
  data: PartnerUpdateInput,
): Promise<PartnerRead> => {
  return apiFetch(`/api/cases/partners/${partnerId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
};

export const linkPartnerToCase = async (
  partnerId: number,
  linkedCaseId: number | null,
): Promise<PartnerRead> => {
  return apiFetch(`/api/cases/partners/${partnerId}/link-case`, {
    method: "PATCH",
    body: JSON.stringify({ linked_case_id: linkedCaseId }),
  });
};

export const getCasePartnerRelationship = async (
  caseId: number,
  partnerId: number,
): Promise<CasePartnerRelationshipRead> => {
  return apiFetch(`/api/cases/${caseId}/partners/${partnerId}/relationship`);
};

export const createCasePartnerRelationship = async (
  caseId: number,
  partnerId: number,
  data: CasePartnerRelationshipCreate,
): Promise<CasePartnerRelationshipRead> => {
  return apiFetch(`/api/cases/${caseId}/partners/${partnerId}/relationship`, {
    method: "POST",
    body: JSON.stringify(data),
  });
};

export const updateCasePartnerRelationship = async (
  caseId: number,
  partnerId: number,
  data: CasePartnerRelationshipUpdate,
): Promise<CasePartnerRelationshipRead> => {
  return apiFetch(`/api/cases/${caseId}/partners/${partnerId}/relationship`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
};

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

export const getRelationshipReports = async (
  relationshipId: number,
): Promise<RelationshipReportRead[]> => {
  return apiFetch(`/api/cases/relationships/${relationshipId}/reports`, {
    method: "GET",
  });
};

export const createRelationshipReport = async (
  relationshipId: number,
  data: RelationshipReportCreate,
): Promise<RelationshipReportRead> => {
  return apiFetch(`/api/cases/relationships/${relationshipId}/reports`, {
    method: "POST",
    body: JSON.stringify(data),
  });
};

export const updateRelationshipReport = async (
  reportId: number,
  data: RelationshipReportUpdate,
): Promise<RelationshipReportRead> => {
  return apiFetch(`/api/cases/relationships/reports/${reportId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
};

export const deleteRelationshipReport = async (reportId: number) => {
  return apiFetch(`/api/cases/relationships/reports/${reportId}`, {
    method: "DELETE",
  });
};
