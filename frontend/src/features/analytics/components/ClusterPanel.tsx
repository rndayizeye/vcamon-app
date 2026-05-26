import type { AnalyticsClusterRead } from '../types'

function GroupList({
  title,
  technicalTerm,
  description,
  groups,
}: {
  title: string
  technicalTerm: string
  description: string
  groups: string[][]
}) {
  return (
    <section className="stack-sm">
      <div>
        <p className="eyebrow">{title} <span className="muted">({technicalTerm})</span></p>
        <h3>{groups.length}</h3>
        <p className="muted text-sm">{description}</p>
      </div>

      {groups.length === 0 ? <p className="muted">None identified</p> : null}

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
    <div className="panel stack-sm">
      <div>
        <p className="eyebrow">Groupings</p>
        <h2>How people cluster together</h2>
      </div>
      <div className="two-column-grid">
        <GroupList
          title="Transmission clusters"
          technicalTerm="connected components"
          description="Groups of people who are linked to each other through any chain of reported contacts — directly or indirectly. People in separate clusters have no known connection to each other."
          groups={clusters.components}
        />
        <GroupList
          title="Fully connected groups"
          technicalTerm="cliques"
          description="Sub-groups where every person reported contact with every other person in the group. These tight clusters represent the highest-density transmission risk within the network."
          groups={clusters.cliques}
        />
      </div>
    </div>
  )
}
