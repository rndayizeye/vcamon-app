import { apiFetch } from '../../lib/api-client'
import type { AnalyticsSummaryRead, ArrowLinkCreate, ArrowLinkRead } from './types'

export function getCaseAnalytics(caseId: number, asOfDate?: string) {
  const query = new URLSearchParams()
  if (asOfDate) {
    query.set('as_of_date', asOfDate)
  }

  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiFetch<AnalyticsSummaryRead>(`/api/cases/${caseId}/analytics${suffix}`)
}

export function listCaseLinks(caseId: number) {
  return apiFetch<ArrowLinkRead[]>(`/api/cases/${caseId}/links`)
}

export function createCaseLink(caseId: number, payload: ArrowLinkCreate) {
  return apiFetch<ArrowLinkRead>(`/api/cases/${caseId}/links`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteCaseLink(linkId: number) {
  return apiFetch<void>(`/api/cases/links/${linkId}`, {
    method: 'DELETE',
  })
}
