import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  clearCaseMapSheet,
  clearPartnerMapSheet,
  getCaseMapSheet,
  getMapCatalog,
  getPartnerMapSheet,
  saveCaseMapSheet,
  savePartnerMapSheet,
} from './api'
import type { MAPSheet, MAPSheetUpsert } from './types'

function mapSheetQueryKey(caseId: number, partnerId?: number | null) {
  return ['cases', caseId, 'map', partnerId ?? 'case']
}

export function useMapCatalog() {
  return useQuery({
    queryKey: ['map', 'catalog'],
    queryFn: getMapCatalog,
  })
}

export function useMapSheet(caseId: number, partnerId?: number | null) {
  return useQuery({
    queryKey: mapSheetQueryKey(caseId, partnerId),
    queryFn: () =>
      partnerId
        ? getPartnerMapSheet(caseId, partnerId)
        : getCaseMapSheet(caseId),
    enabled: caseId > 0,
  })
}

export function useSaveMapSheet(caseId: number, partnerId?: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: MAPSheetUpsert) =>
      partnerId
        ? savePartnerMapSheet(caseId, partnerId, payload)
        : saveCaseMapSheet(caseId, payload),
    onSuccess: async (sheet: MAPSheet) => {
      queryClient.setQueryData(mapSheetQueryKey(caseId, partnerId), sheet)
      await queryClient.invalidateQueries({
        queryKey: mapSheetQueryKey(caseId, partnerId),
      })
    },
  })
}

export function useClearMapSheet(caseId: number, partnerId?: number | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      partnerId
        ? clearPartnerMapSheet(caseId, partnerId)
        : clearCaseMapSheet(caseId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: mapSheetQueryKey(caseId, partnerId),
      })
    },
  })
}
