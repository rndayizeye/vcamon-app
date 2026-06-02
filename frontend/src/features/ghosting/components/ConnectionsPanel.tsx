import { type BodyPartValue, type NetworkEdge } from '../types-local'
import { EdgeRow } from './EdgeRow'

export function ConnectionsPanel({
  edges,
  people,
  onAdd,
  onRemove,
  onChangeA,
  onChangeB,
  onChangeExposure,
  onToggleBodyPart,
  onChangeLabel,
}: {
  edges: NetworkEdge[]
  people: { _pid: string; name: string }[]
  onAdd: () => void
  onRemove: (id: string) => void
  onChangeA: (id: string, pid: string) => void
  onChangeB: (id: string, pid: string) => void
  onChangeExposure: (id: string, field: 'exp_first' | 'exp_last', value: string) => void
  onToggleBodyPart: (id: string, person: 'a' | 'b', part: BodyPartValue) => void
  onChangeLabel: (id: string, label: string) => void
}) {
  return (
    <div className="panel stack-md">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div>
          <p className="eyebrow" style={{ margin: 0 }}>
            Connections
          </p>
          <p style={{ fontSize: '0.8rem', color: '#888', margin: '2px 0 0' }}>
            Expand each connection to set the exposure window and body parts for that specific
            relationship.
          </p>
        </div>
        <button
          type="button"
          className="button button-primary"
          onClick={onAdd}
          disabled={people.length < 2}
          style={{ fontSize: '0.85rem', padding: '4px 14px', flexShrink: 0 }}
          title={people.length < 2 ? 'Add at least 2 patients first' : undefined}
        >
          + Add connection
        </button>
      </div>

      {edges.length === 0 ? (
        <p style={{ color: '#888', fontSize: '0.875rem' }}>
          No connections yet. Add patients above, then connect them here.
        </p>
      ) : (
        <div className="stack-sm">
          {edges.map(edge => (
            <EdgeRow
              key={edge.id}
              edge={edge}
              people={people}
              onChangeA={pid => onChangeA(edge.id, pid)}
              onChangeB={pid => onChangeB(edge.id, pid)}
              onRemove={() => onRemove(edge.id)}
              onChangeExposure={(field, value) => onChangeExposure(edge.id, field, value)}
              onToggleBodyPart={(person, part) => onToggleBodyPart(edge.id, person, part)}
              onChangeLabel={label => onChangeLabel(edge.id, label)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
