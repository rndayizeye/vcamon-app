import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createTimelineEvent, deleteTimelineEvent, getTimelineEvents } from './api'
import type { TimelineEventCreate } from './types'

export function useTimelineEvents(caseId: number) {
  return useQuery({
    queryKey: ['cases', caseId, 'timeline'],
    queryFn: () => getTimelineEvents(caseId),
    enabled: caseId > 0,
  })
}

export function useCreateTimelineEvent(caseId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TimelineEventCreate) => createTimelineEvent(caseId, data),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['cases', caseId, 'timeline'] }),
  })
}

export function useDeleteTimelineEvent(caseId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (eventId: number) => deleteTimelineEvent(eventId),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['cases', caseId, 'timeline'] }),
  })
}
