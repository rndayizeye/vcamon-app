import type { AnalyticsClusterRead } from '../types'

function GroupList({ title, groups }: { title: string; groups: string[][] }) {
  return (
    <section className="stack-sm">
      <div>
        <p className="eyebrow">{title}</p>
        <h3>{groups.length}</h3>
      </div>

      {groups.length === 0 ? <p className="muted">None</p> : null}

      <div className="stack-sm">
        {groups.map((group, index) => (
          <div className="badge-group" key={`${title}-${index}`}>
            {group.map((member) => (
              <span className="badge" key={member}>
                {member}
              </span>
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}

export function ClusterPanel({
  clusters,
}: {
  clusters: AnalyticsClusterRead
}) {
  return (
    <div className="panel two-column-grid">
      <GroupList title="Connected components" groups={clusters.components} />
      <GroupList title="Cliques" groups={clusters.cliques} />
    </div>
  )
}
