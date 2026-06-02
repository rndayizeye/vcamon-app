export type TransmissionNode = {
  id: string
  label: string
  type: 'case' | 'partner'
  case_id: number | null
  partner_id: number | null
  linked_case_id: number | null
}

export type TransmissionEdge = {
  from_node_id: string
  to_node_id: string
  verdict: string
  source_confidence: string
  spread_confidence: string
  dominant_confidence: string
  is_ambiguous: boolean
}

export type TransmissionSkipped = {
  case_id: number
  partner_id: number
  partner_label: string
  reason: string
}

export type TransmissionChainResult = {
  nodes: TransmissionNode[]
  edges: TransmissionEdge[]
  skipped: TransmissionSkipped[]
  total_pairs_analyzed: number
  total_pairs_skipped: number
}
