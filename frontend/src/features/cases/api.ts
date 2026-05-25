import { apiFetch } from "../../lib/api-client";
import type { PartnerRead } from "../partners/types";
import type {
  CaseCreateInput,
  CaseRead,
  CaseSummary,
  CaseUpdateInput,
  DashboardSummary,
  LabResultEntry,
} from "./types";

export function listCases(search?: string) {
  const query = new URLSearchParams();
  if (search?.trim()) {
    query.set("search", search.trim());
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<CaseSummary[]>(`/api/cases/${suffix}`);
}

export function getDashboardSummary() {
  return apiFetch<DashboardSummary>("/api/cases/summary");
}

export function getCaseLatestLab(caseId: number) {
  return apiFetch<LabResultEntry>(`/api/cases/${caseId}/latest-lab`);
}

export function getCase(caseId: number) {
  return apiFetch<CaseRead>(`/api/cases/${caseId}`);
}

export function createCase(payload: CaseCreateInput) {
  return apiFetch<CaseRead>("/api/cases/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCase(caseId: number, payload: CaseUpdateInput) {
  return apiFetch<CaseRead>(`/api/cases/${caseId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function listCasePartners(caseId: number) {
  return apiFetch<PartnerRead[]>(`/api/cases/${caseId}/partners`);
}
