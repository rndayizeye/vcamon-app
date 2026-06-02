import { useState } from 'react'
import { SymptomEditor } from './SymptomEditor'

function PatientClinicalFields({
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
  return (
    <>
      <SymptomEditor prefix={prefix} control={control} register={register} />
      <label className="field">
        <span>Treatment date</span>
        <input type="date" {...register(`${prefix}.treatment_date`)} />
      </label>
    </>
  )
}

export function PatientCard({
  index,
  control,
  register,
  onRemove,
  canRemove,
}: {
  index: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any
  onRemove: () => void
  canRemove: boolean
}) {
  const [open, setOpen] = useState(false)
  const prefix = `people.${index}`

  return (
    <div style={{ border: '1px solid #d8d3cb', borderRadius: '6px', overflow: 'hidden' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '0.5rem 0.75rem',
          background: '#f4f2ec',
          borderBottom: open ? '1px solid #d8d3cb' : 'none',
        }}
      >
        <button
          type="button"
          onClick={() => setOpen(o => !o)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            fontSize: '0.8rem',
            color: '#666',
            flexShrink: 0,
          }}
          title={open ? 'Collapse' : 'Expand clinical data'}
        >
          {open ? '▼' : '▶'}
        </button>
        <label className="field" style={{ margin: 0, flex: 1 }}>
          <input
            type="text"
            {...register(`${prefix}.name`)}
            placeholder={`Patient ${index + 1}`}
            style={{
              fontWeight: 500,
              background: 'transparent',
              border: '1px solid transparent',
              borderRadius: '4px',
            }}
            onFocus={e => (e.currentTarget.style.borderColor = '#6b6459')}
            onBlur={e => (e.currentTarget.style.borderColor = 'transparent')}
          />
        </label>
        <span style={{ fontSize: '0.72rem', color: '#aaa', flexShrink: 0 }}>Patient {index + 1}</span>
        {canRemove && (
          <button
            type="button"
            className="button"
            onClick={onRemove}
            style={{ padding: '3px 8px', fontSize: '0.8rem', flexShrink: 0 }}
          >
            Remove
          </button>
        )}
      </div>
      {open && (
        <div className="stack-md" style={{ padding: '0.75rem 1rem' }}>
          <PatientClinicalFields prefix={prefix} control={control} register={register} />
        </div>
      )}
    </div>
  )
}
