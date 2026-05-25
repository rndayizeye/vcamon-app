import { apiFetch } from "../../lib/api-client";
import type { LabResultEntryRead, LabResultEntryWriteInput } from "./types";

export function listCaseLabs(caseId: number) {
  return apiFetch<LabResultEntryRead[]>(`/api/cases/${caseId}/labs`);
}

export function listPartnerLabs(partnerId: number) {
  return apiFetch<LabResultEntryRead[]>(`/api/cases/partners/${partnerId}/labs`);
}

export function createCaseLab(caseId: number, lab: LabResultEntryWriteInput) {
  return apiFetch<LabResultEntryRead>(`/api/cases/${caseId}/labs`, {
    method: "POST",
    body: JSON.stringify(lab),
  });
}

export function createPartnerLab(partnerId: number, lab: LabResultEntryWriteInput) {
  return apiFetch<LabResultEntryRead>(`/api/cases/partners/${partnerId}/labs`, {
    method: "POST",
    body: JSON.stringify(lab),
  });
}

export function updateLab(entryId: number, lab: LabResultEntryWriteInput) {
  return apiFetch<LabResultEntryRead>(`/api/cases/labs/${entryId}`, {
    method: "PATCH",
    body: JSON.stringify(lab),
  });
}

export function deleteLab(entryId: number) {
  return apiFetch<void>(`/api/cases/labs/${entryId}`, {
    method: "DELETE",
  });
}

export async function syncCaseLabs(
  caseId: number,
  existingLabs: LabResultEntryRead[],
  nextLabs: LabResultEntryWriteInput[],
) {
  const nextIds = new Set(
    nextLabs
      .map((lab) => lab.id)
      .filter((value): value is number => typeof value === "number"),
  );

  await Promise.all(
    existingLabs
      .filter((lab) => !nextIds.has(lab.id))
      .map((lab) => deleteLab(lab.id)),
  );

  const savedLabs: LabResultEntryRead[] = [];
  for (const lab of nextLabs) {
    if (typeof lab.id === "number") {
      savedLabs.push(await updateLab(lab.id, lab));
    } else {
      savedLabs.push(await createCaseLab(caseId, lab));
    }
  }
  return savedLabs;
}

export async function syncPartnerLabs(
  partnerId: number,
  existingLabs: LabResultEntryRead[],
  nextLabs: LabResultEntryWriteInput[],
) {
  const nextIds = new Set(
    nextLabs
      .map((lab) => lab.id)
      .filter((value): value is number => typeof value === "number"),
  );

  await Promise.all(
    existingLabs
      .filter((lab) => !nextIds.has(lab.id))
      .map((lab) => deleteLab(lab.id)),
  );

  const savedLabs: LabResultEntryRead[] = [];
  for (const lab of nextLabs) {
    if (typeof lab.id === "number") {
      savedLabs.push(await updateLab(lab.id, lab));
    } else {
      savedLabs.push(await createPartnerLab(partnerId, lab));
    }
  }
  return savedLabs;
}
