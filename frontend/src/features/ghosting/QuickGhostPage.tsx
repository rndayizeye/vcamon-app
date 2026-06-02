import { useEffect, useRef, useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'

import { runQuickGhostingAnalysis } from './api'
import type { GhostingSymptomInput } from './types'
import {
  CLINICAL_REF,
  type BodyPartValue,
  type NetworkEdge,
  type PairResult,
  type QuickGhostForm,
  defaultEpisodeLabel,
  makeEdge,
  makePersonDefaults,
} from './types-local'
import { ConnectionsPanel } from './components/ConnectionsPanel'
import { NetworkPreview } from './components/NetworkPreview'
import { PatientCard } from './components/PatientCard'
import { ResultsSection } from './components/ResultsSection'

function toSymptomInputs(rows: QuickGhostForm['people'][number]['symptoms']): GhostingSymptomInput[] {
  return rows
    .filter(r => r.type && r.onset)
    .map(r => ({
      type: r.type,
      onset: r.onset,
      duration_days: Number(r.duration_days) || 0,
      anatomical_site: r.anatomical_site || null,
    }))
}

function buildPayload(
  a: QuickGhostForm['people'][number],
  b: QuickGhostForm['people'][number],
  edge: NetworkEdge,
) {
  const exposure =
    edge.exp_first && edge.exp_last
      ? { first: edge.exp_first, last: edge.exp_last, exposure_modalities: [] }
      : null
  return {
    op_name: a.name.trim() || 'Patient A',
    op_symptoms: toSymptomInputs(a.symptoms),
    op_exposure: exposure,
    op_treatment_date: a.treatment_date || null,
    op_body_parts: edge.a_body_parts,
    partner_name: b.name.trim() || 'Patient B',
    partner_symptoms: toSymptomInputs(b.symptoms),
    partner_exposure: exposure,
    partner_treatment_date: b.treatment_date || null,
    partner_body_parts: edge.b_body_parts,
  }
}

export function QuickGhostPage() {
  const [edges, setEdges] = useState<NetworkEdge[]>([])
  const [resultMap, setResultMap] = useState<Map<string, PairResult>>(new Map())
  const [apiError, setApiError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const defaultPeople = [makePersonDefaults(1), makePersonDefaults(2)]

  const { register, control, getValues, reset, watch } = useForm<QuickGhostForm>({
    defaultValues: { people: defaultPeople },
  })

  const {
    fields: peopleFields,
    append: appendPerson,
    remove: removePerson,
  } = useFieldArray({ control, name: 'people' })

  const watchedPeople = watch('people')

  // Cleared when any analysis input changes so results don't silently go stale.
  const freshResultsRef = useRef(false)
  useEffect(() => {
    if (freshResultsRef.current) {
      setResultMap(new Map())
      freshResultsRef.current = false
    }
  }, [watchedPeople, edges])

  function handleAddPerson() {
    appendPerson(makePersonDefaults(peopleFields.length + 1))
  }

  function handleRemovePerson(idx: number) {
    const pid = getValues(`people.${idx}._pid`)
    setEdges(prev => prev.filter(e => e.aId !== pid && e.bId !== pid))
    removePerson(idx)
  }

  function handleAddEdge() {
    const people = getValues('people')
    if (people.length < 2) return
    const aId = people[0]._pid
    const bId = people[1]._pid
    setEdges(prev => [...prev, makeEdge(aId, bId, defaultEpisodeLabel(aId, bId, prev))])
  }

  function handleRemoveEdge(id: string) {
    setEdges(prev => prev.filter(e => e.id !== id))
  }

  function handleChangeEdgeA(id: string, pid: string) {
    setEdges(prev => prev.map(e => (e.id === id ? { ...e, aId: pid } : e)))
  }

  function handleChangeEdgeB(id: string, pid: string) {
    setEdges(prev => prev.map(e => (e.id === id ? { ...e, bId: pid } : e)))
  }

  function handleChangeExposure(edgeId: string, field: 'exp_first' | 'exp_last', value: string) {
    setEdges(prev => prev.map(e => (e.id === edgeId ? { ...e, [field]: value } : e)))
  }

  function handleChangeLabel(edgeId: string, label: string) {
    setEdges(prev => prev.map(e => (e.id === edgeId ? { ...e, label } : e)))
  }

  function handleToggleBodyPart(edgeId: string, person: 'a' | 'b', part: BodyPartValue) {
    setEdges(prev =>
      prev.map(e => {
        if (e.id !== edgeId) return e
        const key = person === 'a' ? 'a_body_parts' : 'b_body_parts'
        const current = e[key]
        const updated = current.includes(part)
          ? current.filter(p => p !== part)
          : [...current, part]
        return { ...e, [key]: updated }
      }),
    )
  }

  async function onRunAnalysis() {
    setApiError(null)
    setResultMap(new Map())
    setLoading(true)

    const validEdges = edges.filter(e => e.aId !== e.bId)
    if (validEdges.length === 0) {
      setApiError(
        'Add at least one valid connection (between two different patients) to run the analysis.',
      )
      setLoading(false)
      return
    }

    const people = getValues('people')
    const newMap = new Map<string, PairResult>()

    for (const edge of validEdges) {
      const personA = people.find(p => p._pid === edge.aId)
      const personB = people.find(p => p._pid === edge.bId)
      if (!personA || !personB) continue

      const idxA = people.indexOf(personA)
      const idxB = people.indexOf(personB)
      const nameA = personA.name.trim() || `Patient ${idxA + 1}`
      const nameB = personB.name.trim() || `Patient ${idxB + 1}`
      const label = `${nameA} ↔ ${nameB}`

      try {
        const result = await runQuickGhostingAnalysis(buildPayload(personA, personB, edge))
        newMap.set(edge.id, { label, result, error: null })
      } catch (err: unknown) {
        newMap.set(edge.id, {
          label,
          result: null,
          error: err instanceof Error ? err.message : 'Analysis failed.',
        })
      }
    }

    setResultMap(newMap)
    freshResultsRef.current = newMap.size > 0
    setLoading(false)
  }

  function handleClear() {
    freshResultsRef.current = false
    const fresh = [makePersonDefaults(1), makePersonDefaults(2)]
    reset({ people: fresh })
    setEdges([])
    setResultMap(new Map())
    setApiError(null)
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem' }}>
      <div className="stack-lg">
        <header className="panel stack-sm">
          <div>
            <p className="eyebrow">Tools</p>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Quick Ghosting Analysis</h1>
          </div>
          <p style={{ color: '#555', fontSize: '0.9rem', maxWidth: 720 }}>
            Add any number of patients, then draw connections between them. Each connection is one
            VCA analysis — the engine determines who is the anchor (&ldquo;OP&rdquo;) from the
            clinical data, so roles shift per pair rather than being fixed by form position.
          </p>
          <details style={{ marginTop: '0.25rem' }}>
            <summary
              style={{ cursor: 'pointer', fontSize: '0.85rem', color: '#444', fontWeight: 500 }}
            >
              Clinical reference constants
            </summary>
            <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
              {CLINICAL_REF.map(r => (
                <div key={r.phase}>
                  <p className="eyebrow" style={{ marginBottom: '2px' }}>
                    {r.phase}
                  </p>
                  <p style={{ fontSize: '0.85rem', fontWeight: 600 }}>{r.range}</p>
                </div>
              ))}
            </div>
          </details>
        </header>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 340px',
            gap: '1.5rem',
            alignItems: 'start',
          }}
        >
          <div className="stack-md">
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <p className="eyebrow" style={{ margin: 0 }}>
                Patients{' '}
                <span style={{ color: '#aaa', fontWeight: 400 }}>({peopleFields.length})</span>
              </p>
              <button
                type="button"
                className="button button-primary"
                onClick={handleAddPerson}
                style={{ fontSize: '0.85rem', padding: '4px 12px' }}
              >
                + Add patient
              </button>
            </div>
            <div className="stack-sm">
              {peopleFields.map((field, i) => (
                <PatientCard
                  key={field.id}
                  index={i}
                  control={control}
                  register={register}
                  onRemove={() => handleRemovePerson(i)}
                  canRemove={peopleFields.length > 2}
                />
              ))}
            </div>
          </div>

          <div>
            <NetworkPreview people={watchedPeople} edges={edges} resultMap={resultMap} />
          </div>
        </div>

        <ConnectionsPanel
          edges={edges}
          people={watchedPeople}
          onAdd={handleAddEdge}
          onRemove={handleRemoveEdge}
          onChangeA={handleChangeEdgeA}
          onChangeB={handleChangeEdgeB}
          onChangeExposure={handleChangeExposure}
          onToggleBodyPart={handleToggleBodyPart}
          onChangeLabel={handleChangeLabel}
        />

        <div
          style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}
        >
          <button
            className="button button-primary"
            type="button"
            onClick={onRunAnalysis}
            disabled={loading || edges.length === 0}
            style={{ minWidth: 200 }}
          >
            {loading ? 'Running…' : '▶ Run analysis'}
          </button>
          <button type="button" className="button" onClick={handleClear} disabled={loading}>
            Clear all
          </button>
          {apiError && (
            <p className="error-text" style={{ margin: 0 }}>
              {apiError}
            </p>
          )}
        </div>

        {resultMap.size > 0 && (
          <ResultsSection edges={edges} people={watchedPeople} resultMap={resultMap} />
        )}
      </div>
    </div>
  )
}
