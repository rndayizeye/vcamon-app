import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createCaseGhosting,
  deleteCaseGhosting,
  listCaseGhostings,
  runCasePartnerGhostingAnalysis,
} from './api'
import type { GhostingCaseAnalysisRequest, GhostingCreate } from './types'

export function useCaseGhostings(caseId: number) {
  return useQuery({
    queryKey: ['cases', caseId, 'ghostings'],
    queryFn: () => listCaseGhostings(caseId),
    enabled: caseId > 0,
  })
}

export function useRunGhostingAnalysis() {
  return useMutation({
    mutationFn: ({
      caseId,
      partnerId,
      payload,
    }: {
      caseId: number
      partnerId: number
      payload: GhostingCaseAnalysisRequest
    }) => runCasePartnerGhostingAnalysis(caseId, partnerId, payload),
  })
}

export function useCreateGhosting(caseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: GhostingCreate) => createCaseGhosting(caseId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'ghostings'] })
    },
  })
}

export function useDeleteGhosting(caseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ghostingId: number) => deleteCaseGhosting(ghostingId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'ghostings'] })
    },
  })
}
