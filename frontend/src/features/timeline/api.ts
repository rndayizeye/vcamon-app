import { apiFetch } from '../../lib/api-client'
import type { TimelineEventCreate, TimelineEventRead } from './types'

export function getTimelineEvents(caseId: number) {
  return apiFetch<TimelineEventRead[]>(`/api/cases/${caseId}/timeline`)
}

export function createTimelineEvent(caseId: number, data: TimelineEventCreate) {
  return apiFetch<TimelineEventRead>(`/api/cases/${caseId}/timeline`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function deleteTimelineEvent(eventId: number) {
  return apiFetch<void>(`/api/cases/timeline/${eventId}`, { method: 'DELETE' })
}
