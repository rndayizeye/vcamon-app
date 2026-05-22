from datetime import date
from typing import Any, Dict, List, Optional

import networkx as nx


def get_first_date(entity: Any, default_date: Optional[date]) -> Optional[date]:
    """Find the earliest known date for a case or partner to determine when they 'appear'."""
    dts = []
    if getattr(entity, "initial_contact_date", None):
        dts.append(entity.initial_contact_date)
    if getattr(entity, "treatment_date", None):
        dts.append(entity.treatment_date)
    if getattr(entity, "symptom_onset_date", None):
        dts.append(entity.symptom_onset_date)
    if getattr(entity, "historical_primary_date", None):
        dts.append(entity.historical_primary_date)
    return min(dts) if dts else default_date


def build_nx_graph(
    case: Any,
    partners: List[Any],
    links: List[Any],
    ref_to_label: Dict[str, str],
    selected_date: Optional[date] = None,
) -> nx.DiGraph:
    """Build a NetworkX directed graph from case, partners, and links."""
    G = nx.DiGraph()

    # Add OP
    G.add_node("OP", label=ref_to_label.get("OP", "OP"))

    # Add Partners
    for p in partners:
        ref = str(p.partner_number)
        if selected_date is not None:
            first_d = get_first_date(p, None)
            if first_d and first_d > selected_date:
                continue
        G.add_node(ref, label=ref_to_label.get(ref, ref))

    # Add Edges
    valid_nodes = set(G.nodes)
    for link in links:
        if link.from_ref in valid_nodes and link.to_ref in valid_nodes:
            G.add_edge(link.from_ref, link.to_ref)

    return G


def calculate_centralities(G: nx.DiGraph) -> List[Dict[str, Any]]:
    """Calculate centrality measures for the network."""
    if len(G.nodes) == 0:
        return []

    in_degree = nx.in_degree_centrality(G)
    out_degree = nx.out_degree_centrality(G)
    betweenness = nx.betweenness_centrality(G)

    cent_data = []
    for n in G.nodes:
        cent_data.append(
            {
                "Node": G.nodes[n].get("label", n),
                "In-Degree": round(in_degree.get(n, 0), 3),
                "Out-Degree": round(out_degree.get(n, 0), 3),
                "Betweenness": round(betweenness.get(n, 0), 3),
            }
        )
    return cent_data


def detect_clusters(G: nx.DiGraph) -> Dict[str, Any]:
    """Detect clusters and cliques in the network."""
    if len(G.nodes) == 0:
        return {"components": [], "cliques": []}

    # Weakly connected components (clusters)
    wcc = list(nx.weakly_connected_components(G))
    components = []
    for comp in wcc:
        components.append([G.nodes[n].get("label", n) for n in comp])

    # Cliques (Requires undirected graph)
    G_undirected = G.to_undirected()
    cliques = list(nx.find_cliques(G_undirected))
    # Filter out trivial cliques of size 1 or 2
    meaningful_cliques = [
        [G.nodes[n].get("label", n) for n in clq] for clq in cliques if len(clq) > 2
    ]

    return {"components": components, "cliques": meaningful_cliques}
