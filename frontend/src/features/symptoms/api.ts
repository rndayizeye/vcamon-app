import { apiFetch } from "../../lib/api-client";
import type { SymptomEntryRead, SymptomEntryWriteInput } from "./types";

function toApiPayload(symptom: SymptomEntryWriteInput) {
  return {
    symptom_type: symptom.symptom_type,
    onset_date: symptom.onset_date,
    date_kind: symptom.date_kind,
    duration_days: symptom.duration_days,
  };
}

export function listCaseSymptoms(caseId: number) {
  return apiFetch<SymptomEntryRead[]>(`/api/cases/${caseId}/symptoms`);
}

export function createCaseSymptom(caseId: number, symptom: SymptomEntryWriteInput) {
  return apiFetch<SymptomEntryRead>(`/api/cases/${caseId}/symptoms`, {
    method: "POST",
    body: JSON.stringify(toApiPayload(symptom)),
  });
}

export function listPartnerSymptoms(partnerId: number) {
  return apiFetch<SymptomEntryRead[]>(`/api/cases/partners/${partnerId}/symptoms`);
}

export function createPartnerSymptom(
  partnerId: number,
  symptom: SymptomEntryWriteInput,
) {
  return apiFetch<SymptomEntryRead>(`/api/cases/partners/${partnerId}/symptoms`, {
    method: "POST",
    body: JSON.stringify(toApiPayload(symptom)),
  });
}

export function updateSymptom(entryId: number, symptom: SymptomEntryWriteInput) {
  return apiFetch<SymptomEntryRead>(`/api/cases/symptoms/${entryId}`, {
    method: "PATCH",
    body: JSON.stringify(toApiPayload(symptom)),
  });
}

export function deleteSymptom(entryId: number) {
  return apiFetch<void>(`/api/cases/symptoms/${entryId}`, {
    method: "DELETE",
  });
}

export async function syncCaseSymptoms(
  caseId: number,
  existingSymptoms: SymptomEntryRead[],
  nextSymptoms: SymptomEntryWriteInput[],
) {
  const nextIds = new Set(
    nextSymptoms
      .map((symptom) => symptom.id)
      .filter((value): value is number => typeof value === "number"),
  );

  await Promise.all(
    existingSymptoms
      .filter((symptom) => !nextIds.has(symptom.id))
      .map((symptom) => deleteSymptom(symptom.id)),
  );

  const savedSymptoms: SymptomEntryRead[] = [];

  for (const symptom of nextSymptoms) {
    if (typeof symptom.id === "number") {
      savedSymptoms.push(await updateSymptom(symptom.id, symptom));
    } else {
      savedSymptoms.push(await createCaseSymptom(caseId, symptom));
    }
  }

  return savedSymptoms;
}

export async function syncPartnerSymptoms(
  partnerId: number,
  existingSymptoms: SymptomEntryRead[],
  nextSymptoms: SymptomEntryWriteInput[],
) {
  const nextIds = new Set(
    nextSymptoms
      .map((symptom) => symptom.id)
      .filter((value): value is number => typeof value === "number"),
  );

  await Promise.all(
    existingSymptoms
      .filter((symptom) => !nextIds.has(symptom.id))
      .map((symptom) => deleteSymptom(symptom.id)),
  );

  const savedSymptoms: SymptomEntryRead[] = [];

  for (const symptom of nextSymptoms) {
    if (typeof symptom.id === "number") {
      savedSymptoms.push(await updateSymptom(symptom.id, symptom));
    } else {
      savedSymptoms.push(await createPartnerSymptom(partnerId, symptom));
    }
  }

  return savedSymptoms;
}
