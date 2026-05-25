import type { MAPSheetItem } from '../types'

export function MapSection({
  section,
  items,
  onToggle,
  onNotesChange,
}: {
  section: string
  items: MAPSheetItem[]
  onToggle: (
    itemNumber: number,
    field: 'p_value' | 'c_value' | 'high_priority',
  ) => void
  onNotesChange: (itemNumber: number, notes: string) => void
}) {
  return (
    <section className="panel table-panel stack-sm">
      <div>
        <p className="eyebrow">MAP section</p>
        <h2>{section}</h2>
      </div>

      <table className="data-table map-table">
        <thead>
          <tr>
            <th className="map-item-column">Item</th>
            <th className="map-checkbox-column">P</th>
            <th className="map-checkbox-column">C</th>
            <th className="map-checkbox-column">High</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.item_number}>
              <td>
                <div className="stack-xs">
                  <strong>{item.item_number}</strong>
                  <span>{item.label}</span>
                </div>
              </td>
              <td>
                <label className="checkbox-cell">
                  <input
                    type="checkbox"
                    checked={item.p_value}
                    onChange={() => onToggle(item.item_number, 'p_value')}
                  />
                </label>
              </td>
              <td>
                <label className="checkbox-cell">
                  <input
                    type="checkbox"
                    checked={item.c_value}
                    onChange={() => onToggle(item.item_number, 'c_value')}
                  />
                </label>
              </td>
              <td>
                <label className="checkbox-cell">
                  <input
                    type="checkbox"
                    checked={item.high_priority}
                    onChange={() => onToggle(item.item_number, 'high_priority')}
                  />
                </label>
              </td>
              <td>
                <textarea
                  rows={2}
                  value={item.notes}
                  onChange={(event) =>
                    onNotesChange(item.item_number, event.target.value)
                  }
                  placeholder="Add context or evidence…"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
