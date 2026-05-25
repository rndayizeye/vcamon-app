import { apiFetch } from '../../lib/api-client'
import type {
  GhostingAnalysisRequest,
  GhostingAnalysisResult,
  GhostingCaseAnalysisRequest,
  GhostingCreate,
  GhostingRecord,
} from './types'

export function runQuickGhostingAnalysis(payload: GhostingAnalysisRequest) {
  return apiFetch<GhostingAnalysisResult>('/api/ghosting/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function runCasePartnerGhostingAnalysis(
  caseId: number,
  partnerId: number,
  payload: GhostingCaseAnalysisRequest = {},
) {
  return apiFetch<GhostingAnalysisResult>(
    `/api/cases/${caseId}/partners/${partnerId}/ghosting-analysis`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export function listCaseGhostings(caseId: number) {
  return apiFetch<GhostingRecord[]>(`/api/cases/${caseId}/ghostings`)
}

export function createCaseGhosting(caseId: number, payload: GhostingCreate) {
  return apiFetch<GhostingRecord>(`/api/cases/${caseId}/ghostings`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteCaseGhosting(ghostingId: number) {
  return apiFetch<void>(`/api/cases/ghostings/${ghostingId}`, { method: 'DELETE' })
}
