"""
app/pages/05_network_graph.py

Transmission network graph — visualizes directed links between
the original patient (OP) and their contact partners.

Uses streamlit-agraph to render an interactive node-link diagram.
Each ArrowLink row in the database becomes a directed edge.
Users can add and remove links from this page.

Node colors:
  - OP:       coral  (#D85A30)
  - Partners: teal   (#1D9E75)
  - Untreated partners: amber (#EF9F27)
"""

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from app.db.database import SessionLocal
from app.db.queries import (
    get_case_by_id,
    get_partners_for_case,
)
from app.db.models import ArrowLink
from app.utils.session_state import (
    init_session_state,
    get_active_case_id,
    set_active_partner_id,
    require_password
)
from app.utils.validators import validate_arrow_link

st.set_page_config(page_title="Network Graph — VCA Monitor", layout="wide")
init_session_state()
require_password()


# ---------------------------------------------------------------------------
# DB helpers (arrow-specific — not in queries.py yet)
# ---------------------------------------------------------------------------

def get_arrow_links(db, case_id: int) -> list[ArrowLink]:
    return (
        db.query(ArrowLink)
        .filter(ArrowLink.case_id == case_id)
        .all()
    )


def create_arrow_link(db, case_id: int, from_ref: str, to_ref: str) -> ArrowLink:
    link = ArrowLink(case_id=case_id, from_ref=from_ref, to_ref=to_ref)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def delete_arrow_link(db, link_id: int) -> bool:
    link = db.query(ArrowLink).filter(ArrowLink.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


def link_exists(db, case_id: int, from_ref: str, to_ref: str) -> bool:
    return (
        db.query(ArrowLink)
        .filter(
            ArrowLink.case_id == case_id,
            ArrowLink.from_ref == from_ref,
            ArrowLink.to_ref == to_ref,
        )
        .first()
    ) is not None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Active case")

    case_id = get_active_case_id()

    if not case_id:
        st.warning("No case selected.")
        if st.button("← Dashboard", use_container_width=True):
            st.switch_page("pages/01_dashboard.py")
        st.stop()

    with SessionLocal() as db:
        case = get_case_by_id(db, case_id)
        partners = get_partners_for_case(db, case_id)
        links = get_arrow_links(db, case_id)

    if not case:
        st.error("Case not found.")
        st.stop()

    st.write(f"**#{case.id} — {case.patient_name}**")
    st.caption(f"Lot: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")
    st.divider()

    if st.button("← MAP sheet", use_container_width=True):
        st.switch_page("pages/04_map_sheet.py")
    if st.button("Timeline →", use_container_width=True):
        st.switch_page("pages/06_timeline.py")
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")


# ---------------------------------------------------------------------------
# Build node/edge references
# ---------------------------------------------------------------------------

# ref_map: display label → internal ref string used in ArrowLink
# e.g. "OP — Doe, Jane" → "OP"
#      "Partner 1 — Smith, John" → "1"

ref_to_label: dict[str, str] = {"OP": f"OP — {case.patient_name}"}
label_to_ref: dict[str, str] = {f"OP — {case.patient_name}": "OP"}

for p in partners:
    ref = str(p.partner_number)
    label = f"Partner {p.partner_number} — {p.name or 'Unnamed'}"
    ref_to_label[ref] = label
    label_to_ref[label] = ref

all_labels = list(label_to_ref.keys())


# ---------------------------------------------------------------------------
# Build agraph nodes and edges
# ---------------------------------------------------------------------------

def build_graph(case, partners, links):
    nodes = []
    edges = []

    # OP node
    nodes.append(Node(
        id="OP",
        label=case.patient_name or "OP",
        size=28,
        color="#D85A30",
        font={"color": "#FFFFFF", "size": 14},
        title=f"OP: {case.patient_name}\nLot: {case.lot or '—'}",
    ))

    # Partner nodes
    for p in partners:
        ref = str(p.partner_number)
        treated = p.treatment_date is not None
        color = "#1D9E75" if treated else "#EF9F27"
        nodes.append(Node(
            id=ref,
            label=f"P{p.partner_number}\n{p.name or 'Unnamed'}",
            size=22,
            color=color,
            font={"color": "#FFFFFF", "size": 12},
            title=(
                f"Partner {p.partner_number}: {p.name or 'Unnamed'}\n"
                f"Treatment: {p.treatment_date or 'Pending'}\n"
                f"Lab 1: {p.lab_1 or '—'}"
            ),
        ))

    # Edges from ArrowLink rows
    for link in links:
        edges.append(Edge(
            source=link.from_ref,
            target=link.to_ref,
            id=str(link.id),
            color="#534AB7",
            width=2,
        ))

    return nodes, edges


nodes, edges = build_graph(case, partners, links)

# ---------------------------------------------------------------------------
# Page header + legend
# ---------------------------------------------------------------------------

st.title("Transmission Network")
st.caption(
    f"Case #{case.id} — {case.patient_name}  |  "
    f"{len(partners)} partner{'s' if len(partners) != 1 else ''}  |  "
    f"{len(links)} link{'s' if len(links) != 1 else ''}"
)

# Legend
leg1, leg2, leg3, leg4 = st.columns(4)
leg1.markdown(
    '<span style="background:#D85A30;color:#fff;padding:2px 10px;'
    'border-radius:4px;font-size:12px">OP</span>',
    unsafe_allow_html=True,
)
leg2.markdown(
    '<span style="background:#1D9E75;color:#fff;padding:2px 10px;'
    'border-radius:4px;font-size:12px">Partner — treated</span>',
    unsafe_allow_html=True,
)
leg3.markdown(
    '<span style="background:#EF9F27;color:#fff;padding:2px 10px;'
    'border-radius:4px;font-size:12px">Partner — untreated</span>',
    unsafe_allow_html=True,
)
leg4.markdown(
    '<span style="background:#534AB7;color:#fff;padding:2px 10px;'
    'border-radius:4px;font-size:12px">Transmission link</span>',
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Graph + add/remove links side by side
# ---------------------------------------------------------------------------

col_graph, col_controls = st.columns([3, 1])

with col_graph:
    if not nodes:
        st.info("No partners added yet. Add partners on the Partner Form first.")
    else:
        config = Config(
            width="100%",
            height=520,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F5A623",
            collapsible=False,
            node={"labelProperty": "label"},
            link={"labelProperty": "label", "renderLabel": False},
        )
        agraph(nodes=nodes, edges=edges, config=config)

with col_controls:
    st.subheader("Add link")

    if len(all_labels) < 2:
        st.info("Add at least two parties (OP + one partner) to draw links.")
    else:
        with st.form("add_link_form"):
            from_label = st.selectbox("From", options=all_labels, key="from_sel")
            to_label   = st.selectbox("To",   options=all_labels, key="to_sel")
            add_btn    = st.form_submit_button(
                "➕  Add link", type="primary", use_container_width=True
            )

        if add_btn:
            from_ref = label_to_ref[from_label]
            to_ref   = label_to_ref[to_label]

            errors = validate_arrow_link(from_ref, to_ref)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                with SessionLocal() as db:
                    if link_exists(db, case_id, from_ref, to_ref):
                        st.warning("That link already exists.")
                    else:
                        create_arrow_link(db, case_id, from_ref, to_ref)
                        st.success(
                            f"Link added: "
                            f"{ref_to_label[from_ref]} → {ref_to_label[to_ref]}"
                        )
                        st.rerun()

    # Remove links
    if links:
        st.divider()
        st.subheader("Remove link")

        link_labels = {
            lnk.id: (
                f"{ref_to_label.get(lnk.from_ref, lnk.from_ref)} → "
                f"{ref_to_label.get(lnk.to_ref, lnk.to_ref)}"
            )
            for lnk in links
        }

        with st.form("remove_link_form"):
            remove_id = st.selectbox(
                "Select link to remove",
                options=list(link_labels.keys()),
                format_func=lambda k: link_labels[k],
            )
            remove_btn = st.form_submit_button(
                "✕  Remove", use_container_width=True
            )

        if remove_btn:
            with SessionLocal() as db:
                if delete_arrow_link(db, remove_id):
                    st.success("Link removed.")
                    st.rerun()

# ---------------------------------------------------------------------------
# Link table — full list below graph
# ---------------------------------------------------------------------------

if links:
    st.divider()
    st.subheader("All transmission links")

    import pandas as pd

    rows = [
        {
            "From": ref_to_label.get(lnk.from_ref, lnk.from_ref),
            "To":   ref_to_label.get(lnk.to_ref,   lnk.to_ref),
        }
        for lnk in links
    ]
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# Ghosting section
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Ghosting tracker")
st.caption(
    "Record ghosted lesion exposure paths. "
    "Corresponds to the GhostingSource and GhostingSpread sheets."
)

from app.db.models import Ghosting, GhostingType

def get_ghostings(db, case_id):
    return db.query(Ghosting).filter(Ghosting.case_id == case_id).all()

def create_ghosting(db, case_id, ghosting_type, from_ref, to_ref, notes):
    g = Ghosting(
        case_id=case_id,
        ghosting_type=ghosting_type,
        from_ref=from_ref,
        to_ref=to_ref,
        notes=notes,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return g

def delete_ghosting(db, ghosting_id):
    g = db.query(Ghosting).filter(Ghosting.id == ghosting_id).first()
    if not g:
        return False
    db.delete(g)
    db.commit()
    return True

with SessionLocal() as db:
    ghostings = get_ghostings(db, case_id)

gcol1, gcol2 = st.columns([2, 1])

with gcol1:
    if ghostings:
        ghost_rows = [
            {
                "Type":  g.ghosting_type,
                "From":  ref_to_label.get(g.from_ref, g.from_ref or "—"),
                "To":    ref_to_label.get(g.to_ref,   g.to_ref or "—"),
                "Notes": g.notes or "",
            }
            for g in ghostings
        ]
        st.dataframe(
            pd.DataFrame(ghost_rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No ghosting records yet.")

with gcol2:
    with st.form("add_ghosting_form"):
        ghost_type = st.selectbox(
            "Type",
            options=[t.value for t in GhostingType],
        )
        ghost_from = st.selectbox("From", options=[""] + all_labels)
        ghost_to   = st.selectbox("To",   options=[""] + all_labels)
        ghost_note = st.text_input("Notes", placeholder="Optional...")
        ghost_btn  = st.form_submit_button(
            "➕  Add ghosting", use_container_width=True
        )

    if ghost_btn:
        with SessionLocal() as db:
            create_ghosting(
                db,
                case_id=case_id,
                ghosting_type=ghost_type,
                from_ref=label_to_ref.get(ghost_from, "") or None,
                to_ref=label_to_ref.get(ghost_to, "") or None,
                notes=ghost_note or None,
            )
        st.success("Ghosting record added.")
        st.rerun()

    if ghostings:
        with st.form("remove_ghosting_form"):
            ghost_options = {
                g.id: f"{g.ghosting_type} | "
                      f"{ref_to_label.get(g.from_ref, g.from_ref or '—')} → "
                      f"{ref_to_label.get(g.to_ref, g.to_ref or '—')}"
                for g in ghostings
            }
            remove_ghost_id = st.selectbox(
                "Remove ghosting",
                options=list(ghost_options.keys()),
                format_func=lambda k: ghost_options[k],
            )
            remove_ghost_btn = st.form_submit_button(
                "✕  Remove", use_container_width=True
            )

        if remove_ghost_btn:
            with SessionLocal() as db:
                delete_ghosting(db, remove_ghost_id)
            st.success("Ghosting record removed.")
            st.rerun()
