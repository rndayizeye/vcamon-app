import { useQuery } from '@tanstack/react-query'
import { getTransmissionChain } from './api'

export function useTransmissionChain(enabled: boolean) {
  return useQuery({
    queryKey: ['transmission-chain'],
    queryFn: getTransmissionChain,
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}
