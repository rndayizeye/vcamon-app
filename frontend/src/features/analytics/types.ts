export type ArrowLinkCreate = {
  from_ref: string
  to_ref: string
}

export type ArrowLinkRead = {
  id: number
  case_id: number
  from_ref: string
  to_ref: string
}

export type AnalyticsNodeRead = {
  ref: string
  label: string
  entity_type: string
  case_id: number
  partner_id: number | null
  partner_number: number | null
  treated: boolean
  first_date: string | null
}

export type AnalyticsCentralityRead = {
  node_ref: string
  label: string
  in_degree: number
  out_degree: number
  betweenness: number
}

export type AnalyticsClusterRead = {
  components: string[][]
  cliques: string[][]
}

export type AnalyticsSummaryRead = {
  case_id: number
  as_of_date: string | null
  node_count: number
  edge_count: number
  nodes: AnalyticsNodeRead[]
  edges: ArrowLinkRead[]
  centralities: AnalyticsCentralityRead[]
  clusters: AnalyticsClusterRead
}
