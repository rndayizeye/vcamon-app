import { useFieldArray } from 'react-hook-form'
import { ANATOMICAL_SITES, EMPTY_SYMPTOM, SYMPTOM_TYPES } from '../types-local'

export function SymptomEditor({
  prefix,
  control,
  register,
}: {
  prefix: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
}) {
  const { fields, append, remove } = useFieldArray({ control, name: `${prefix}.symptoms` })
  return (
    <div className="stack-sm">
      <p className="eyebrow">Symptoms</p>
      {fields.length === 0 && (
        <p style={{ color: '#888', fontSize: '0.85rem', margin: 0 }}>
          No symptoms — click Add to enter one.
        </p>
      )}
      {fields.map((field, i) => (
        <div
          key={field.id}
          style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'flex-end' }}
        >
          <label className="field" style={{ margin: 0, flex: '2 1 140px', minWidth: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Type</span>}
            <select {...register(`${prefix}.symptoms.${i}.type`)}>
              {SYMPTOM_TYPES.map(t => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ margin: 0, flex: '1 1 130px', minWidth: 110 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Onset date</span>}
            <input type="date" {...register(`${prefix}.symptoms.${i}.onset`)} />
          </label>
          <label className="field" style={{ margin: 0, flex: '0 1 90px', minWidth: 70 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Duration (d)</span>}
            <input
              type="number"
              min={0}
              max={90}
              {...register(`${prefix}.symptoms.${i}.duration_days`, { valueAsNumber: true })}
            />
          </label>
          <label className="field" style={{ margin: 0, flex: '2 1 140px', minWidth: 0 }}>
            {i === 0 && <span style={{ fontSize: '0.75rem' }}>Anatomical site</span>}
            <select {...register(`${prefix}.symptoms.${i}.anatomical_site`)}>
              <option value="">— none —</option>
              {ANATOMICAL_SITES.map(s => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button"
            onClick={() => remove(i)}
            style={{ padding: '6px 10px', flex: '0 0 auto', alignSelf: 'flex-end' }}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className="button"
        style={{ alignSelf: 'flex-start' }}
        onClick={() => append({ ...EMPTY_SYMPTOM })}
      >
        + Add symptom
      </button>
    </div>
  )
}
