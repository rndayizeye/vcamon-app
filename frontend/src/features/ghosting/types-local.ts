export const SYMPTOM_TYPES = [
  'Primary Chancre',
  'Historical Primary',
  'Ghosted Primary',
  'Secondary Rash/Lesions',
]

export const ANATOMICAL_SITES = [
  'Anal LX',
  'Oral LX',
  'Vaginal LX',
  'Penile LX',
  'Rectal LX',
  'Non-genital LX',
  'LX',
]

export const BODY_PARTS = [
  { value: 'penis', label: 'Penis' },
  { value: 'vagina', label: 'Vagina / Vulva' },
  { value: 'anus', label: 'Anus / Rectum' },
  { value: 'mouth', label: 'Mouth' },
] as const

export type BodyPartValue = (typeof BODY_PARTS)[number]['value']

export const CLINICAL_REF = [
  { phase: 'Incubation', range: '10–21–90 d' },
  { phase: 'Primary chancre', range: '7–21–35 d' },
  { phase: 'Latency', range: '0–28–70 d' },
  { phase: 'Secondary', range: '14–28–42 d' },
]

export const VERDICT_COLORS: Record<string, string> = {
  SOURCE: '#1d9e75',
  SPREAD: '#378add',
  AMBIGUOUS: '#ef9f27',
  UNRELATED: '#e24b4a',
}

export type SymptomRow = {
  type: string
  onset: string
  duration_days: number
  anatomical_site: string
}

// Each patient in the investigation — _pid is a stable local ID used by edges.
// Only intrinsic clinical facts live here; encounter-specific data lives on NetworkEdge.
export type NetworkPerson = {
  _pid: string
  name: string
  symptoms: SymptomRow[]
  treatment_date: string
}

// A connection between two patients — holds all encounter-specific data so the
// same person can have different exposure windows and body parts per relationship.
export type NetworkEdge = {
  id: string
  aId: string
  bId: string
  label: string
  exp_first: string
  exp_last: string
  a_body_parts: BodyPartValue[]
  b_body_parts: BodyPartValue[]
}

// The form only owns the patient list. Edges live in plain state so they can
// cross-reference patients by _pid without being part of a nested form structure.
export type QuickGhostForm = {
  people: NetworkPerson[]
}

export type PairResult = {
  label: string
  result: import('./types').GhostingAnalysisResult | null
  error: string | null
}

export const EMPTY_SYMPTOM: SymptomRow = {
  type: SYMPTOM_TYPES[0],
  onset: '',
  duration_days: 0,
  anatomical_site: '',
}

export function makePersonDefaults(n: number): NetworkPerson {
  return {
    _pid: crypto.randomUUID(),
    name: `Patient ${n}`,
    symptoms: [],
    treatment_date: '',
  }
}

export function makeEdge(aId: string, bId: string, label: string): NetworkEdge {
  return {
    id: crypto.randomUUID(),
    aId,
    bId,
    label,
    exp_first: '',
    exp_last: '',
    a_body_parts: [],
    b_body_parts: [],
  }
}

// Returns "Episode 1" for a new pair, "Episode 2" for the second edge between the same two people, etc.
export function defaultEpisodeLabel(
  aId: string,
  bId: string,
  existingEdges: NetworkEdge[],
): string {
  const n = existingEdges.filter(
    e => (e.aId === aId && e.bId === bId) || (e.aId === bId && e.bId === aId),
  ).length
  return `Episode ${n + 1}`
}

export function verdictEdgeColor(verdict: string | undefined): string {
  if (!verdict) return '#cccccc'
  const up = verdict.toUpperCase()
  if (up.includes('SOURCE')) return VERDICT_COLORS.SOURCE
  if (up.includes('SPREAD')) return VERDICT_COLORS.SPREAD
  if (up.includes('AMBIGUOUS') || up.includes('OVERLAP') || up.includes('⚠'))
    return VERDICT_COLORS.AMBIGUOUS
  if (up.includes('UNRELATED')) return VERDICT_COLORS.UNRELATED
  return '#cccccc'
}
