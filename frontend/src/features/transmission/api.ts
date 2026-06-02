import { apiFetch } from '../../lib/api-client'
import type { TransmissionChainResult } from './types'

export function getTransmissionChain() {
  return apiFetch<TransmissionChainResult>('/api/transmission-chain')
}
