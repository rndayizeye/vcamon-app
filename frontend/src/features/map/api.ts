import { apiFetch } from '../../lib/api-client'
import type { MAPCatalog, MAPSheet, MAPSheetUpsert } from './types'

export function getMapCatalog() {
  return apiFetch<MAPCatalog>('/api/map/items')
}

export function getCaseMapSheet(caseId: number) {
  return apiFetch<MAPSheet>(`/api/cases/${caseId}/map`)
}

export function getPartnerMapSheet(caseId: number, partnerId: number) {
  return apiFetch<MAPSheet>(`/api/cases/${caseId}/partners/${partnerId}/map`)
}

export function saveCaseMapSheet(caseId: number, payload: MAPSheetUpsert) {
  return apiFetch<MAPSheet>(`/api/cases/${caseId}/map`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function savePartnerMapSheet(
  caseId: number,
  partnerId: number,
  payload: MAPSheetUpsert,
) {
  return apiFetch<MAPSheet>(`/api/cases/${caseId}/partners/${partnerId}/map`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function clearCaseMapSheet(caseId: number) {
  return apiFetch<void>(`/api/cases/${caseId}/map`, {
    method: 'DELETE',
  })
}

export function clearPartnerMapSheet(caseId: number, partnerId: number) {
  return apiFetch<void>(`/api/cases/${caseId}/partners/${partnerId}/map`, {
    method: 'DELETE',
  })
}
