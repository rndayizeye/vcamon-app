export type TimelineEventCreate = {
  event_date: string
  event_type: string
  notes?: string | null
  partner_id?: number | null
}

export type TimelineEventRead = {
  id: number
  case_id: number
  event_date: string
  event_type: string
  notes: string | null
  partner_id: number | null
}
