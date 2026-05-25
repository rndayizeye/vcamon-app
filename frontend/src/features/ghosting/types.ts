export type GhostingSymptomInput = {
  type: string
  onset: string  // YYYY-MM-DD
  duration_days: number
  anatomical_site?: string | null
}

export type GhostingExposureInput = {
  first: string  // YYYY-MM-DD
  last: string   // YYYY-MM-DD
  exposure_modalities: string[]
}

export type GhostingCriteriaCheck = {
  status: 'pass' | 'fail' | 'warn' | 'na'
  detail: string
}

export type GhostingScenarioCriteria = {
  exposure: GhostingCriteriaCheck
  exposure_modality: GhostingCriteriaCheck
  latency: GhostingCriteriaCheck
  natural_order: GhostingCriteriaCheck
}

export type GhostedLesion = {
  lesion_type: string
  onset: string  // YYYY-MM-DD
  end: string    // YYYY-MM-DD
  derived_from_symptom: string
  assigned_to: string
}

export type GhostingScenarioLesions = {
  aggressive: GhostedLesion
  expected: GhostedLesion
  conservative: GhostedLesion
}

export type GhostingScenarioRanges = {
  aggressive: GhostingScenarioCriteria
  expected: GhostingScenarioCriteria
  conservative: GhostingScenarioCriteria
}

export type GhostingScenario = {
  range_data: GhostingScenarioRanges
  range_lesions: GhostingScenarioLesions
  confidence: string
  pass_count: number
}

export type SuggestedGhostingRecord = {
  ghosting_type: 'SOURCE' | 'SPREAD'
  from_ref: string
  to_ref: string
  notes: string
}

export type GhostingAnalysisResult = {
  case1_name: string
  case2_name: string
  case1_ref: string | null
  case2_ref: string | null
  case1_symptom: GhostingSymptomInput
  ghosted_source: GhostedLesion
  ghosted_spread: GhostedLesion
  source_scenarios: GhostingScenario
  spread_scenarios: GhostingScenario
  verdict: string
  log: string[]
  suggested_records: SuggestedGhostingRecord[]
}

export type GhostingRecord = {
  id: number
  case_id: number
  ghosting_type: 'SOURCE' | 'SPREAD'
  from_ref: string | null
  to_ref: string | null
  notes: string | null
}

export type GhostingCreate = {
  ghosting_type: 'SOURCE' | 'SPREAD'
  from_ref?: string | null
  to_ref?: string | null
  notes?: string | null
}

export type GhostingCaseAnalysisRequest = {
  op_symptoms?: GhostingSymptomInput[]
  op_exposure?: GhostingExposureInput | null
  op_treatment_date?: string | null
  partner_symptoms?: GhostingSymptomInput[]
  partner_exposure?: GhostingExposureInput | null
  partner_treatment_date?: string | null
}

// Minimal partner shape needed for chart and ghosting pages
export type PartnerSummary = {
  id: number
  case_id: number
  partner_number: number
  name: string | null
  treatment_date: string | null
  historical_primary_chancre: boolean | null
  historical_primary_date: string | null
}

// Minimal relationship shape needed for chart
export type RelationshipSummary = {
  id: number
  case_id: number
  partner_id: number
  exposure_first_date: string | null
  exposure_last_date: string | null
  exposure_modalities: string | null
}
