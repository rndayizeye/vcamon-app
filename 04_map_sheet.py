"""
app/pages/04_map_sheet.py

Major Analytical Points (MAP) assessment sheet.
Renders the 46-item P/C checklist grouped by section.
Supports both the OP MAP sheet (partner_id=None) and
partner-specific MAP sheets (MAP1, MAP2, etc.).

The 46 items and their section groupings come from MAP_ITEMS
in models.py — no item labels are stored in the database.
"""

import streamlit as st
import pandas as pd

from app.db.database import SessionLocal
from app.db.queries import (
    get_case_by_id,
    get_partners_for_case,
    get_partner_by_id,
    get_map_entries,
    upsert_map_entry,
)
from app.db.models import MAP_ITEMS
from app.utils.session_state import (
    init_session_state,
    get_active_case_id,
    set_active_case_id,
    get_active_partner_id,
    set_active_partner_id,
)

st.set_page_config(page_title="MAP Sheet — VCA Monitor", layout="wide")
init_session_state()

# ---------------------------------------------------------------------------
# Sidebar — case + subject selector
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

    if not case:
        st.error("Case not found.")
        st.stop()

    st.write(f"**#{case.id} — {case.patient_name}**")
    st.caption(f"Lot: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")

    st.divider()
    st.subheader("MAP subject")
    st.caption("Choose whose MAP sheet to view.")

    # Subject = OP or a specific partner
    subject_options = {0: f"OP — {case.patient_name}"}
    subject_options.update({
        p.id: f"Partner {p.partner_number} — {p.name or 'Unnamed'}"
        for p in partners
    })

    # Default to OP (0) unless a partner is active
    current_partner_id = get_active_partner_id() or 0
    if current_partner_id not in subject_options:
        current_partner_id = 0

    selected_subject = st.selectbox(
        "Subject",
        options=list(subject_options.keys()),
        format_func=lambda k: subject_options[k],
        index=list(subject_options.keys()).index(current_partner_id),
    )

    # Sync partner session state to match subject selection
    set_active_partner_id(selected_subject if selected_subject != 0 else None)
    map_partner_id = selected_subject if selected_subject != 0 else None

    st.divider()

    if st.button("← Partner form", use_container_width=True):
        st.switch_page("pages/03_partner_form.py")
    if st.button("Network graph →", use_container_width=True):
        st.switch_page("pages/05_network_graph.py")
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")

# ---------------------------------------------------------------------------
# Load existing MAP entries for this subject
# ---------------------------------------------------------------------------

with SessionLocal() as db:
    existing = get_map_entries(db, case_id, partner_id=map_partner_id)

# Subject label for headings
subject_label = (
    subject_options.get(selected_subject, "OP")
)

# ---------------------------------------------------------------------------
# Page header + completion summary
# ---------------------------------------------------------------------------

st.title("MAP Assessment Sheet")
st.caption(f"Subject: {subject_label}  |  Case #{case.id} — {case.patient_name}")

# Completion metrics
total_items    = len([i for i, v in MAP_ITEMS.items() if v["label"]])
checked_p      = sum(1 for e in existing.values() if e.p_value)
checked_c      = sum(1 for e in existing.values() if e.c_value)
high_pri_count = sum(1 for e in existing.values() if e.high_priority)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Items with P checked", f"{checked_p} / {total_items}")
m2.metric("Items with C checked", f"{checked_c} / {total_items}")
m3.metric("High priority flags",  high_pri_count,
          delta=str(high_pri_count) if high_pri_count else None,
          delta_color="inverse")
m4.metric("Subject",              subject_label.split(" — ")[0])

st.divider()

# ---------------------------------------------------------------------------
# Build form state from existing entries + defaults
# ---------------------------------------------------------------------------
# We collect all widget values into dicts keyed by item_number,
# then batch-save on submit. This avoids 46 individual DB calls
# mid-render and keeps the form fast.

# Pre-populate state dicts
p_vals:    dict[int, bool] = {}
c_vals:    dict[int, bool] = {}
notes_vals: dict[int, str] = {}
hp_vals:   dict[int, bool] = {}

for item_num in MAP_ITEMS:
    entry = existing.get(item_num)
    p_vals[item_num]     = entry.p_value     if entry else False
    c_vals[item_num]     = entry.c_value     if entry else False
    notes_vals[item_num] = entry.notes       if entry and entry.notes else ""
    hp_vals[item_num]    = entry.high_priority if entry else False

# ---------------------------------------------------------------------------
# Section rendering helper
# ---------------------------------------------------------------------------

SECTION_ORDER = [
    "Social History",
    "Medical History",
    "Partners",
    "Clusters",
    "Risk Reduction",
    "Other",
]

SECTION_COLORS = {
    "Social History":  "#e3f2fd",
    "Medical History": "#fce4ec",
    "Partners":        "#e8f5e9",
    "Clusters":        "#fff8e1",
    "Risk Reduction":  "#f3e5f5",
    "Other":           "#f5f5f5",
}

def render_section(
    section_name: str,
    items: dict,
    p_vals: dict,
    c_vals: dict,
    notes_vals: dict,
    hp_vals: dict,
) -> tuple[dict, dict, dict, dict]:
    """
    Render one MAP section as an expander with a grid of rows.
    Returns updated (p_vals, c_vals, notes_vals, hp_vals) dicts.
    """
    color = SECTION_COLORS.get(section_name, "#f5f5f5")
    section_items = {
        num: meta for num, meta in items.items()
        if meta["section"] == section_name and meta["label"]
    }

    if not section_items:
        return p_vals, c_vals, notes_vals, hp_vals

    checked_in_section = sum(
        1 for num in section_items
        if p_vals.get(num) or c_vals.get(num)
    )
    total_in_section = len(section_items)

    label = (
        f"**{section_name}** — "
        f"{checked_in_section}/{total_in_section} items active"
    )

    with st.expander(label, expanded=True):

        # Column headers
        hdr = st.columns([0.5, 3.5, 0.6, 0.6, 0.6, 2.5])
        hdr[0].caption("#")
        hdr[1].caption("Assessment item")
        hdr[2].caption("P")
        hdr[3].caption("C")
        hdr[4].caption("Hi-pri")
        hdr[5].caption("Notes")

        st.markdown(
            f'<hr style="margin:4px 0; border-color:{color}; border-width:2px;">',
            unsafe_allow_html=True,
        )

        for item_num, meta in section_items.items():
            cols = st.columns([0.5, 3.5, 0.6, 0.6, 0.6, 2.5])

            with cols[0]:
                st.caption(str(item_num))
            with cols[1]:
                st.write(meta["label"])
            with cols[2]:
                p_vals[item_num] = st.checkbox(
                    "P",
                    value=p_vals.get(item_num, False),
                    key=f"p_{item_num}",
                    label_visibility="collapsed",
                )
            with cols[3]:
                c_vals[item_num] = st.checkbox(
                    "C",
                    value=c_vals.get(item_num, False),
                    key=f"c_{item_num}",
                    label_visibility="collapsed",
                )
            with cols[4]:
                hp_vals[item_num] = st.checkbox(
                    "!",
                    value=hp_vals.get(item_num, False),
                    key=f"hp_{item_num}",
                    label_visibility="collapsed",
                    help="Mark as high priority",
                )
            with cols[5]:
                notes_vals[item_num] = st.text_input(
                    "Notes",
                    value=notes_vals.get(item_num, ""),
                    key=f"notes_{item_num}",
                    label_visibility="collapsed",
                    placeholder="Notes...",
                )

    return p_vals, c_vals, notes_vals, hp_vals


# ---------------------------------------------------------------------------
# Render all sections (outside a form — checkboxes update live)
# ---------------------------------------------------------------------------

st.subheader("Assessment items")
st.caption(
    "Check **P** for items discussed in the previous interview, "
    "**C** for the current interview. Flag high-priority items with **Hi-pri**."
)

for section in SECTION_ORDER:
    p_vals, c_vals, notes_vals, hp_vals = render_section(
        section, MAP_ITEMS, p_vals, c_vals, notes_vals, hp_vals
    )

# ---------------------------------------------------------------------------
# High-priority comments block
# ---------------------------------------------------------------------------

st.divider()
st.subheader("High priority comments")

hp_comment = st.text_area(
    "Notes on high-priority items",
    value=existing.get(-1, None) and existing[-1].notes or "",
    height=120,
    placeholder="Summarise high-priority findings and recommended follow-up actions...",
    key="hp_comment",
)

# ---------------------------------------------------------------------------
# Save button
# ---------------------------------------------------------------------------

st.divider()
col_save, col_clear, _ = st.columns([1, 1, 5])

with col_save:
    save_clicked = st.button("💾  Save MAP sheet", type="primary", use_container_width=True)

with col_clear:
    clear_clicked = st.button("✕  Clear all", use_container_width=True,
                               help="Uncheck all items for this subject")

if save_clicked:
    saved_count = 0
    with SessionLocal() as db:
        for item_num, meta in MAP_ITEMS.items():
            if not meta["label"]:
                continue
            upsert_map_entry(
                db=db,
                case_id=case_id,
                item_number=item_num,
                p_value=p_vals.get(item_num, False),
                c_value=c_vals.get(item_num, False),
                notes=notes_vals.get(item_num, ""),
                high_priority=hp_vals.get(item_num, False),
                partner_id=map_partner_id,
            )
            saved_count += 1

        # Save high-priority comment block as item -1 convention
        if hp_comment.strip():
            upsert_map_entry(
                db=db,
                case_id=case_id,
                item_number=-1,
                p_value=False,
                c_value=False,
                notes=hp_comment.strip(),
                high_priority=True,
                partner_id=map_partner_id,
            )

    st.success(f"MAP sheet saved — {saved_count} items recorded for {subject_label}.")
    st.rerun()

if clear_clicked:
    with SessionLocal() as db:
        for item_num in MAP_ITEMS:
            upsert_map_entry(
                db=db,
                case_id=case_id,
                item_number=item_num,
                p_value=False,
                c_value=False,
                notes="",
                high_priority=False,
                partner_id=map_partner_id,
            )
    st.info("All items cleared.")
    st.rerun()

# ---------------------------------------------------------------------------
# Summary table — checked items only (shown after save)
# ---------------------------------------------------------------------------

active_items = {
    num: e for num, e in existing.items()
    if (e.p_value or e.c_value or e.high_priority) and num > 0
}

if active_items:
    st.divider()
    st.subheader("Active items summary")

    rows = []
    for num, entry in sorted(active_items.items()):
        meta = MAP_ITEMS.get(num, {})
        rows.append({
            "#":           num,
            "Section":     meta.get("section", "—"),
            "Item":        meta.get("label", "—"),
            "P":           "✓" if entry.p_value else "",
            "C":           "✓" if entry.c_value else "",
            "Hi-pri":      "!" if entry.high_priority else "",
            "Notes":       entry.notes or "",
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "#":      st.column_config.NumberColumn("#", width="small"),
            "P":      st.column_config.TextColumn("P", width="small"),
            "C":      st.column_config.TextColumn("C", width="small"),
            "Hi-pri": st.column_config.TextColumn("Hi-pri", width="small"),
        },
    )

    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("Network graph →", use_container_width=True):
            st.switch_page("pages/05_network_graph.py")
    with col_nav2:
        if st.button("← Partner form", use_container_width=True):
            st.switch_page("pages/03_partner_form.py")
