import { BODY_PARTS, type BodyPartValue } from '../types-local'

export function BodyPartsCheckboxes({
  heading,
  checked,
  onToggle,
}: {
  heading: string
  checked: BodyPartValue[]
  onToggle: (part: BodyPartValue) => void
}) {
  return (
    <div className="stack-xs">
      <p className="eyebrow" style={{ marginBottom: '0.25rem' }}>
        {heading}
      </p>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {BODY_PARTS.map(({ value, label }) => (
          <label
            key={value}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            <input
              type="checkbox"
              checked={checked.includes(value)}
              onChange={() => onToggle(value)}
            />
            {label}
          </label>
        ))}
      </div>
    </div>
  )
}
