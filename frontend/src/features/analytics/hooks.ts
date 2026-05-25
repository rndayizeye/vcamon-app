import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createCaseLink,
  deleteCaseLink,
  getCaseAnalytics,
  listCaseLinks,
} from './api'
import type { ArrowLinkCreate } from './types'

export function useCaseAnalytics(caseId: number, asOfDate?: string) {
  return useQuery({
    queryKey: ['cases', caseId, 'analytics', asOfDate ?? null],
    queryFn: () => getCaseAnalytics(caseId, asOfDate),
    enabled: caseId > 0,
  })
}

export function useCaseLinks(caseId: number) {
  return useQuery({
    queryKey: ['cases', caseId, 'links'],
    queryFn: () => listCaseLinks(caseId),
    enabled: caseId > 0,
  })
}

export function useCreateCaseLink(caseId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ArrowLinkCreate) => createCaseLink(caseId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'links'] }),
        queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'analytics'] }),
      ])
    },
  })
}

export function useDeleteCaseLink(caseId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (linkId: number) => deleteCaseLink(linkId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'links'] }),
        queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'analytics'] }),
      ])
    },
  })
}
