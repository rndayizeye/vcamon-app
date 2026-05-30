"""
app/utils/quick_inputs.py

Shared input vocabulary and conversion helpers for the two "quick" ghosting
front-ends — the in-app page (`app/pages/09_quick_ghost.py`) and the standalone
sandbox (`quickvca/quick_vca.py`). Both render a symptom data-editor and a
sex-type multiselect, then feed the shared clinical engine; keeping the maps and
the row→Symptom conversion here prevents the two surfaces from drifting apart.

This module may import pandas — it is NOT part of the framework-free engine
(`app/utils/clinical.py`), which must stay dependency-light.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.utils.clinical import Symptom

# Sex-type vocabulary -------------------------------------------------------
# Display labels are shown without the "LX" suffix; the engine wants the full
# value, and the body-part map drives the anatomical-compatibility check.
SEX_DISPLAY = ["Anal", "Oral", "Vaginal", "Penile", "Rectal"]

SEX_DISPLAY_TO_VALUE = {
    "Anal": "Anal LX",
    "Oral": "Oral LX",
    "Vaginal": "Vaginal LX",
    "Penile": "Penile LX",
    "Rectal": "Rectal LX",
}

MODALITY_TO_BODY_PART = {
    "Anal LX": "anus",
    "Rectal LX": "anus",
    "Oral LX": "mouth",
    "Vaginal LX": "vagina",
    "Penile LX": "penis",
}

# Symptom data-editor vocabulary -------------------------------------------
SYMPTOM_TYPES = [
    "Primary Chancre",
    "Historical Primary",
    "Ghosted Primary",
    "Secondary Rash/Lesions",
]

LOCATION_OPTIONS = [
    "Anal LX",
    "Oral LX",
    "Vaginal LX",
    "Penile LX",
    "Rectal LX",
    "Non-genital LX",
    "LX",
]

SYM_COLUMNS = ["Type", "Onset Date", "Duration", "Location"]


def sex_display_to_values(display_labels: list[str]) -> list[str]:
    """Convert display labels (no "LX") back to full engine sex-type values."""
    return [
        SEX_DISPLAY_TO_VALUE[s] for s in display_labels if s in SEX_DISPLAY_TO_VALUE
    ]


def body_parts_from_modalities(sex_values: list[str]) -> list[str]:
    """Map full sex-type values to the deduplicated body parts they imply."""
    return list(
        {MODALITY_TO_BODY_PART[m] for m in sex_values if m in MODALITY_TO_BODY_PART}
    )


def rows_to_symptoms(df: pd.DataFrame) -> list[Symptom]:
    """Convert a symptom data-editor DataFrame into engine ``Symptom`` objects.

    Rows missing a type or onset date are skipped. Duration of 0 (or blank)
    signals "use the natural-history average" downstream; location is optional.
    """
    syms: list[Symptom] = []
    for row in df.to_dict("records"):
        sym_type = row.get("Type")
        onset = row.get("Onset Date")
        if not sym_type or (isinstance(sym_type, float) and pd.isna(sym_type)):
            continue
        if onset is None or (not isinstance(onset, date) and pd.isna(onset)):
            continue
        onset_d = onset if isinstance(onset, date) else pd.to_datetime(onset).date()
        dur = row.get("Duration")
        duration_days = int(dur) if pd.notna(dur) else 0
        loc = row.get("Location")
        loc_is_nan = isinstance(loc, float) and pd.isna(loc)
        anatomical_site = loc if loc and not loc_is_nan else None
        syms.append(
            Symptom(
                type=sym_type,
                onset=onset_d,
                duration_days=duration_days,
                anatomical_site=anatomical_site,
            )
        )
    return syms
