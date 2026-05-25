export type MAPItemDefinition = {
  item_number: number
  section: string
  label: string
}

export type MAPCatalog = {
  section_order: string[]
  items: MAPItemDefinition[]
}

export type MAPSheetItem = MAPItemDefinition & {
  p_value: boolean
  c_value: boolean
  notes: string
  high_priority: boolean
  updated_at: string | null
}

export type MAPSheetSummary = {
  total_items: number
  checked_p: number
  checked_c: number
  high_priority_flags: number
}

export type MAPSheet = {
  case_id: number
  partner_id: number | null
  subject_label: string
  section_order: string[]
  items: MAPSheetItem[]
  high_priority_comment: string
  summary: MAPSheetSummary
}

export type MAPSheetItemUpsert = {
  item_number: number
  p_value: boolean
  c_value: boolean
  notes: string
  high_priority: boolean
}

export type MAPSheetUpsert = {
  items: MAPSheetItemUpsert[]
  high_priority_comment: string | null
}
