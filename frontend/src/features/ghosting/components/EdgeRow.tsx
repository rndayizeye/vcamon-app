import { useState } from 'react'
import { type BodyPartValue, type NetworkEdge } from '../types-local'
import { BodyPartsCheckboxes } from './BodyPartsCheckboxes'

const selectStyle: React.CSSProperties = {
  flex: '1 1 130px',
  padding: '5px 6px',
  borderRadius: '4px',
  border: '1px solid #ccc',
  fontSize: '0.875rem',
}

export function EdgeRow({
  edge,
  people,
  onChangeA,
  onChangeB,
  onRemove,
  onChangeExposure,
  onToggleBodyPart,
  onChangeLabel,
}: {
  edge: NetworkEdge
  people: { _pid: string; name: string }[]
  onChangeA: (pid: string) => void
  onChangeB: (pid: string) => void
  onRemove: () => void
  onChangeExposure: (field: 'exp_first' | 'exp_last', value: string) => void
  onToggleBodyPart: (person: 'a' | 'b', part: BodyPartValue) => void
  onChangeLabel: (label: string) => void
}) {
  const [open, setOpen] = useState(false)
  const selfLoop = edge.aId === edge.bId

  function nameOf(pid: string): string {
    const idx = people.findIndex(p => p._pid === pid)
    const p = people[idx]
    return p ? (p.name.trim() || `Patient ${idx + 1}`) : '(removed)'
  }

  return (
    <div style={{ border: '1px solid #d8d3cb', borderRadius: '6px', overflow: 'hidden' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          flexWrap: 'wrap',
          padding: '0.5rem 0.75rem',
          background: '#f9f8f5',
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
          title={open ? 'Collapse' : 'Expand exposure & body parts'}
        >
          {open ? '▼' : '▶'}
        </button>
        <select value={edge.aId} onChange={e => onChangeA(e.target.value)} style={selectStyle}>
          {people.map((p, i) => (
            <option key={p._pid} value={p._pid}>
              {p.name.trim() || `Patient ${i + 1}`}
            </option>
          ))}
        </select>
        <span style={{ color: '#888', fontSize: '1rem', flexShrink: 0 }}>↔</span>
        <select value={edge.bId} onChange={e => onChangeB(e.target.value)} style={selectStyle}>
          {people.map((p, i) => (
            <option key={p._pid} value={p._pid}>
              {p.name.trim() || `Patient ${i + 1}`}
            </option>
          ))}
        </select>
        {selfLoop && (
          <span style={{ fontSize: '0.78rem', color: '#e24b4a', flexShrink: 0 }}>⚠ Same person</span>
        )}
        {!open &&
          (edge.exp_first || edge.a_body_parts.length > 0 || edge.b_body_parts.length > 0) && (
            <span style={{ fontSize: '0.75rem', color: '#888', flexShrink: 0 }}>
              {edge.exp_first ? `${edge.exp_first} → ${edge.exp_last || '?'}` : ''}
              {edge.a_body_parts.length > 0 || edge.b_body_parts.length > 0
                ? ' · body parts set'
                : ''}
            </span>
          )}
        <input
          type="text"
          value={edge.label}
          onChange={e => onChangeLabel(e.target.value)}
          placeholder="Episode label"
          style={{
            fontSize: '0.75rem',
            padding: '3px 10px',
            border: '1px solid #d0cbc3',
            borderRadius: '12px',
            background: '#eee9e0',
            color: '#555',
            width: '120px',
            flexShrink: 0,
            marginLeft: 'auto',
            outline: 'none',
          }}
          onFocus={e => (e.currentTarget.style.borderColor = '#6b6459')}
          onBlur={e => (e.currentTarget.style.borderColor = '#d0cbc3')}
        />
        <button
          type="button"
          className="button"
          onClick={onRemove}
          style={{ padding: '4px 10px', fontSize: '0.8rem', flexShrink: 0 }}
          title={`Remove: ${nameOf(edge.aId)} ↔ ${nameOf(edge.bId)}`}
        >
          ×
        </button>
      </div>

      {open && (
        <div className="stack-md" style={{ padding: '0.75rem 1rem' }}>
          <div className="stack-sm">
            <p className="eyebrow">Exposure window (when this pair had contact)</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <label className="field">
                <span>First contact</span>
                <input
                  type="date"
                  value={edge.exp_first}
                  onChange={e => onChangeExposure('exp_first', e.target.value)}
                />
              </label>
              <label className="field">
                <span>Last contact</span>
                <input
                  type="date"
                  value={edge.exp_last}
                  onChange={e => onChangeExposure('exp_last', e.target.value)}
                />
              </label>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <BodyPartsCheckboxes
              heading={`${nameOf(edge.aId)}'s body parts`}
              checked={edge.a_body_parts}
              onToggle={part => onToggleBodyPart('a', part)}
            />
            <BodyPartsCheckboxes
              heading={`${nameOf(edge.bId)}'s body parts`}
              checked={edge.b_body_parts}
              onToggle={part => onToggleBodyPart('b', part)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
