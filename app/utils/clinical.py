"""
app/utils/clinical.py

Pure Python clinical logic for Visual Case Analysis (VCA).
No Streamlit, no SQLAlchemy — only date math and syphilis natural history.

Clinical reference:
  Fussell, E. (2022). Visual Case Analysis.
  National Coalition of STD Directors / Marion County Public Health Dept.
  https://www.ncsddc.org/wp-content/uploads/2022/07/VCA-Training-7.2022.pdf

Ghosting hierarchy (highest to lowest rank):
  1. Existing primary chancre     (rank 1)
  2. Historical primary chancre   (rank 2)
  3. Ghosted primary chancre      (rank 3)
  4. Secondary symptom            (rank 4)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Syphilis natural history constants (days)
# Source: VCA Training slide 10, Marion County Public Health / NCSDDC 2022
# ---------------------------------------------------------------------------

INCUBATION = {"min": 10, "avg": 21, "max": 90}   # days from exposure to primary chancre
PRIMARY    = {"min":  7, "avg": 21, "max": 35}    # duration of primary chancre
LATENCY    = {"min":  0, "avg": 28, "max": 70}    # days from primary end to secondary onset
SECONDARY  = {"min": 14, "avg": 28, "max": 42}    # duration of secondary symptoms

# Interview periods (per slide 11):
#   Primary:   max incubation + max primary = 90 + 35 = 125 days before chancre onset
#   Secondary: max incubation + max primary + max latency + max secondary
#              = 90 + 35 + 70 + 42 = 237 days before secondary onset
INTERVIEW_PERIOD_PRIMARY_DAYS   = INCUBATION["max"] + PRIMARY["max"]           # 125
INTERVIEW_PERIOD_SECONDARY_DAYS = (
    INCUBATION["max"] + PRIMARY["max"] + LATENCY["max"] + SECONDARY["max"]    # 237
)

# Minimum latency between ANY lesion end and a following secondary symptom onset
MIN_LATENCY_TO_SECONDARY_DAYS = 35  # "at least five weeks" per user spec


# ---------------------------------------------------------------------------
# Symptom ranking — ghosting hierarchy (slide 13)
# ---------------------------------------------------------------------------

SYMPTOM_RANK: dict[str, int] = {
    "Primary Chancre":          1,   # existing primary (highest)
    "Historical Primary":       2,   # past primary, healed without treatment
    "Ghosted Primary":          3,   # calculated ghosted chancre
    "Secondary Rash/Lesions":   4,   # secondary (lowest usable)
}

def symptom_rank(symptom_type: str) -> int:
    """Return rank for a symptom type. Lower = higher priority in hierarchy."""
    return SYMPTOM_RANK.get(symptom_type, 99)


# ---------------------------------------------------------------------------
# Data classes (lightweight, decoupled from ORM)
# ---------------------------------------------------------------------------

@dataclass
class Symptom:
    type: str               # maps to SYMPTOM_RANK keys
    onset: date
    duration_days: int      # 0 = unknown; will use avg for that type


@dataclass
class Exposure:
    first: date
    last: date
    sex_types: list[str] = field(default_factory=list)  # e.g. ["Anal LX", "Oral LX"]


@dataclass
class GhostedLesion:
    lesion_type: str        # "ghosted_source" | "ghosted_spread"
    onset: date
    end: date
    derived_from_symptom: str
    assigned_to: str        # "OP" | "partner"


@dataclass
class GhostingResult:
    p1_name: str
    p2_name: str
    p1_symptom: Symptom
    ghosted_source: GhostedLesion     # assigned to P2
    ghosted_spread: GhostedLesion     # assigned to P2
    criteria: dict                    # per-criterion pass/fail/warn
    verdict: str                      # "source" | "spread" | "unrelated" | "ambiguous"
    log: list[str]                    # human-readable step-by-step log


# ---------------------------------------------------------------------------
# Step 1 — Select P1 (person with highest-ranking symptom)
# ---------------------------------------------------------------------------

def select_p1(
    op_symptoms: list[Symptom],
    partner_symptoms: list[Symptom],
) -> tuple[str, Symptom, str, list[Symptom]]:
    """
    Compare OP and partner symptoms using the ghosting hierarchy.
    Returns (p1_role, p1_symptom, p2_role, p2_symptoms).
    p1_role is 'OP' or 'partner'.
    Raises ValueError if neither party has usable symptoms.
    """
    def best(symptoms: list[Symptom]) -> Optional[Symptom]:
        usable = [s for s in symptoms if s.type in SYMPTOM_RANK]
        return min(usable, key=lambda s: symptom_rank(s.type)) if usable else None

    op_best      = best(op_symptoms)
    partner_best = best(partner_symptoms)

    if op_best is None and partner_best is None:
        raise ValueError("Neither the OP nor the partner has usable symptoms for ghosting.")

    if op_best is None:
        return "partner", partner_best, "OP", op_symptoms
    if partner_best is None:
        return "OP", op_best, "partner", partner_symptoms

    # Both have symptoms — pick highest rank (lower number wins)
    if symptom_rank(op_best.type) <= symptom_rank(partner_best.type):
        return "OP", op_best, "partner", partner_symptoms
    else:
        return "partner", partner_best, "OP", op_symptoms


# ---------------------------------------------------------------------------
# Step 2 — Calculate average inoculation date (D1)
# ---------------------------------------------------------------------------

def avg_inoculation_date(symptom: Symptom) -> date:
    """
    Work backwards from symptom onset to find when P1 was likely infected.

    For Primary Chancre / Historical Primary / Ghosted Primary:
        D1 = onset - avg_incubation_days

    For Secondary Rash/Lesions:
        D1 = onset - (avg_latency + avg_primary_duration + avg_incubation)
        We go back through the full natural history chain.
    """
    if symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        return symptom.onset - timedelta(days=INCUBATION["avg"])
    elif symptom.type == "Secondary Rash/Lesions":
        days_back = INCUBATION["avg"] + PRIMARY["avg"] + LATENCY["avg"]
        return symptom.onset - timedelta(days=days_back)
    else:
        raise ValueError(f"Cannot calculate inoculation date for symptom type: {symptom.type}")


# ---------------------------------------------------------------------------
# Step 3 — Ghosted source lesion for P2
# D1 is the midpoint of the ghosted source lesion window.
# onset = D1 - half_primary_avg ; end = D1 + half_primary_avg
# ---------------------------------------------------------------------------

def calc_ghosted_source(d1: date, assigned_to: str, derived_from: str) -> GhostedLesion:
    """
    D1 is the avg inoculation date of P1.
    Per the training: D1 = midpoint of the ghosted source lesion.
    So the ghosted source chancre started avg_incubation_days before D1
    and lasted avg_primary_duration days after that start.

    onset = D1 - half of primary avg duration
    end   = D1 + half of primary avg duration
    """
    half_primary = PRIMARY["avg"] // 2          # 10 days (21//2)
    onset = d1 - timedelta(days=half_primary)
    end   = d1 + timedelta(days=half_primary)
    return GhostedLesion(
        lesion_type="ghosted_source",
        onset=onset,
        end=end,
        derived_from_symptom=derived_from,
        assigned_to=assigned_to,
    )


# ---------------------------------------------------------------------------
# Step 4 — D2 and ghosted spread lesion for P2
# ---------------------------------------------------------------------------

def calc_d2(symptom: Symptom) -> date:
    """
    D2 = midpoint of P1's primary chancre window.

    If P1 has a primary chancre (existing, historical, or ghosted):
        duration = symptom.duration_days if known, else avg
        midpoint = onset + (duration / 2)

    If P1 has secondary symptoms only:
        D2 = secondary_onset - avg_latency - half_primary_avg
        (per slide: d2 = onset - avg_latency - 10.5 days)
    """
    if symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        dur = symptom.duration_days if symptom.duration_days > 0 else PRIMARY["avg"]
        return symptom.onset + timedelta(days=dur // 2)
    elif symptom.type == "Secondary Rash/Lesions":
        # D2 = onset of secondary - average latency - half primary duration
        half_primary = PRIMARY["avg"] / 2        # 10.5 days
        days_back = LATENCY["avg"] + half_primary
        return symptom.onset - timedelta(days=round(days_back))
    else:
        raise ValueError(f"Cannot calculate D2 for symptom type: {symptom.type}")


def calc_ghosted_spread(d2: date, assigned_to: str, derived_from: str) -> GhostedLesion:
    """
    Ghosted spread lesion for P2:
        onset = d2 + avg_primary_duration   (starts after P1's chancre midpoint)
        end   = onset + avg_primary_duration (lasts one avg primary duration)
    Per user spec: "start on d2 + average primary duration and end three weeks later"
    Three weeks = 21 days = PRIMARY["avg"]
    """
    onset = d2 + timedelta(days=PRIMARY["avg"])
    end   = onset + timedelta(days=PRIMARY["avg"])
    return GhostedLesion(
        lesion_type="ghosted_spread",
        onset=onset,
        end=end,
        derived_from_symptom=derived_from,
        assigned_to=assigned_to,
    )


# ---------------------------------------------------------------------------
# Criteria evaluation (slide 12 + user spec)
# ---------------------------------------------------------------------------

def _within_exposure(lesion_onset: date, exposure: Optional[Exposure]) -> tuple[str, str]:
    """Check if lesion onset falls within the reported sexual exposure window."""
    if exposure is None or exposure.first is None or exposure.last is None:
        return "warn", "Cannot check — exposure dates not recorded."
    if exposure.first <= lesion_onset <= exposure.last:
        return "pass", (
            f"Lesion onset {lesion_onset} falls within exposure period "
            f"({exposure.first} to {exposure.last})."
        )
    return "fail", (
        f"Lesion onset {lesion_onset} is OUTSIDE exposure period "
        f"({exposure.first} to {exposure.last})."
    )


def _sex_type_compatible(
    lesion_type_symptom: str,
    sex_types: list[str],
) -> tuple[str, str]:
    """
    Check whether the location of the primary symptom is consistent with
    the reported sex types. This is a best-effort check — the worker
    confirms anatomical plausibility.

    Lesion location keywords vs sex type keywords:
      Anal LX     → Anal
      Penile LX   → Vaginal / Anal (receptive)
      Vaginal LX  → Vaginal
      Oral LX     → Oral
      Lab LX      → any (lab-confirmed, location ambiguous)
    """
    if not sex_types:
        return "warn", "Sex types not recorded — cannot check anatomical compatibility."

    loc_lower = lesion_type_symptom.lower()
    sex_lower = [s.lower() for s in sex_types]

    compatible = False
    if "anal" in loc_lower:
        compatible = any("anal" in s for s in sex_lower)
    elif "penile" in loc_lower or "vaginal" in loc_lower:
        compatible = any(k in s for s in sex_lower for k in ("vaginal", "anal"))
    elif "oral" in loc_lower:
        compatible = any("oral" in s for s in sex_lower)
    else:
        compatible = True   # Lab LX or unknown location — give benefit of doubt

    if compatible:
        return "pass", (
            f"Symptom location ({lesion_type_symptom}) is consistent with "
            f"reported sex types ({', '.join(sex_types)})."
        )
    return "fail", (
        f"Symptom location ({lesion_type_symptom}) may NOT be consistent with "
        f"reported sex types ({', '.join(sex_types)}). Manual verification needed."
    )


def _latency_to_secondary(
    lesion_end: date,
    p2_symptoms: list[Symptom],
) -> tuple[str, str]:
    """
    At least MIN_LATENCY_TO_SECONDARY_DAYS (35 days / 5 weeks) must elapse
    between the end of ANY ghosted lesion and the onset of secondary symptoms.
    """
    secondary = [s for s in p2_symptoms if s.type == "Secondary Rash/Lesions"]
    if not secondary:
        return "na", "P2 has no secondary symptoms — latency check not applicable."

    earliest_sec = min(s.onset for s in secondary)
    gap = (earliest_sec - lesion_end).days

    if gap >= MIN_LATENCY_TO_SECONDARY_DAYS:
        return "pass", (
            f"{gap} days between ghosted lesion end ({lesion_end}) and "
            f"P2 secondary onset ({earliest_sec}) — meets ≥5-week requirement."
        )
    return "fail", (
        f"Only {gap} days between ghosted lesion end ({lesion_end}) and "
        f"P2 secondary onset ({earliest_sec}) — less than required 5 weeks ({MIN_LATENCY_TO_SECONDARY_DAYS} days)."
    )


def _natural_order(
    lesion: GhostedLesion,
    p2_symptoms: list[Symptom],
    p2_treatment_date: Optional[date],
) -> tuple[str, str]:
    """
    Syphilis natural order check:
      - Primary symptoms must precede secondary symptoms.
      - No symptoms should appear after treatment date.
      - Ghosted lesion onset must precede any secondary onset of P2.
    """
    issues = []

    secondary = [s for s in p2_symptoms if s.type == "Secondary Rash/Lesions"]
    if secondary:
        earliest_sec = min(s.onset for s in secondary)
        if lesion.onset >= earliest_sec:
            issues.append(
                f"Ghosted lesion onset ({lesion.onset}) is on/after P2 secondary onset "
                f"({earliest_sec}) — violates primary-before-secondary order."
            )

    if p2_treatment_date:
        if lesion.onset >= p2_treatment_date:
            issues.append(
                f"Ghosted lesion onset ({lesion.onset}) is on/after P2 treatment "
                f"({p2_treatment_date}) — symptoms should not appear after treatment."
            )

    if issues:
        return "fail", " | ".join(issues)
    return "pass", "Ghosted lesion follows natural syphilis progression order."


def evaluate_criteria(
    lesion: GhostedLesion,
    p1_symptom: Symptom,
    p2_symptoms: list[Symptom],
    p2_exposure: Optional[Exposure],        # from P2's perspective (partner exposure to OP)
    op_exposure: Optional[Exposure],        # from OP's perspective (OP exposure to partner)
    p2_treatment_date: Optional[date],
) -> dict:
    """
    Run all four criteria checks and return results dict.
    Keys: exposure, sex_type, latency, natural_order
    Each value: {"status": "pass"|"fail"|"warn"|"na", "detail": str}
    """
    # Use whichever exposure record is available (partner's report preferred)
    exposure = p2_exposure or op_exposure

    exp_status, exp_detail       = _within_exposure(lesion.onset, exposure)
    sex_status, sex_detail       = _sex_type_compatible(
        p1_symptom.type, exposure.sex_types if exposure else []
    )
    lat_status, lat_detail       = _latency_to_secondary(lesion.end, p2_symptoms)
    ord_status, ord_detail       = _natural_order(lesion, p2_symptoms, p2_treatment_date)

    return {
        "exposure":      {"status": exp_status, "detail": exp_detail},
        "sex_type":      {"status": sex_status, "detail": sex_detail},
        "latency":       {"status": lat_status, "detail": lat_detail},
        "natural_order": {"status": ord_status, "detail": ord_detail},
    }


def _scenario_passes(criteria: dict) -> bool:
    """A scenario passes if no criterion is a hard fail (warn and na are acceptable)."""
    return all(v["status"] != "fail" for v in criteria.values())


# ---------------------------------------------------------------------------
# Verdict — source, spread, or unrelated?
# ---------------------------------------------------------------------------

def determine_verdict(
    source_passes: bool,
    spread_passes: bool,
    p1_role: str,
    p1_name: str,
    p2_name: str,
) -> str:
    """
    Per VCA training slide 16:
      - If ghosted SOURCE criteria met → partner in that scenario is the source.
      - If ghosted SPREAD criteria met → partner in that scenario is the spread.
      - If both pass → ambiguous.
      - If neither → unrelated infections.

    p1 is the person whose symptom drives the analysis.
    """
    if source_passes and not spread_passes:
        if p1_role == "OP":
            return f"OP ({p1_name}) is the SOURCE of infection for partner ({p2_name})."
        else:
            return f"Partner ({p1_name}) is the SOURCE of infection for OP ({p2_name})."
    elif spread_passes and not source_passes:
        if p1_role == "OP":
            return f"Partner ({p2_name}) is the SOURCE — OP ({p1_name}) is a SPREAD."
        else:
            return f"OP ({p2_name}) is the SOURCE — partner ({p1_name}) is a SPREAD."
    elif source_passes and spread_passes:
        return "AMBIGUOUS — both source and spread scenarios meet criteria. Manual review required."
    else:
        return "UNRELATED INFECTIONS — neither source nor spread scenario meets criteria."


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_ghosting_analysis(
    op_name: str,
    op_symptoms: list[Symptom],
    op_exposure: Optional[Exposure],          # OP's account of exposure with partner
    op_treatment_date: Optional[date],

    partner_name: str,
    partner_symptoms: list[Symptom],
    partner_exposure: Optional[Exposure],     # Partner's account of exposure with OP
    partner_treatment_date: Optional[date],
) -> GhostingResult:
    """
    Full ghosting analysis pipeline following VCA training methodology.

    Steps:
      1. Identify P1 (highest-ranking symptom in hierarchy)
      2. Calculate D1 (avg inoculation date for P1)
      3. Calculate ghosted SOURCE lesion for P2 (D1 is its midpoint)
      4. Calculate D2 (midpoint of P1's primary window)
      5. Calculate ghosted SPREAD lesion for P2
      6. Evaluate source scenario criteria
      7. Evaluate spread scenario criteria
      8. Determine verdict
    """
    log: list[str] = ["=== VCA Ghosting Analysis ===", ""]

    # --- Step 1 ---
    p1_role, p1_symptom, p2_role, p2_symptoms = select_p1(op_symptoms, partner_symptoms)
    p1_name = op_name if p1_role == "OP" else partner_name
    p2_name = partner_name if p1_role == "OP" else op_name
    p2_treatment = partner_treatment_date if p1_role == "OP" else op_treatment_date
    p1_exposure = op_exposure if p1_role == "OP" else partner_exposure
    p2_exposure_rec = partner_exposure if p1_role == "OP" else op_exposure

    log.append(
        f"Step 1: P1 = {p1_name} ({p1_role}) with '{p1_symptom.type}' "
        f"(rank {symptom_rank(p1_symptom.type)}) on {p1_symptom.onset}."
    )
    log.append(f"        P2 = {p2_name} ({p2_role}).")

    # --- Step 2 ---
    d1 = avg_inoculation_date(p1_symptom)
    log.append(f"Step 2: D1 (avg inoculation date for P1) = {d1}.")

    # --- Step 3 ---
    ghosted_source = calc_ghosted_source(d1, assigned_to=p2_role, derived_from=p1_symptom.type)
    log.append(
        f"Step 3: Ghosted SOURCE lesion for {p2_name}: "
        f"{ghosted_source.onset} → {ghosted_source.end}."
    )

    # --- Step 4 ---
    d2 = calc_d2(p1_symptom)
    ghosted_spread = calc_ghosted_spread(d2, assigned_to=p2_role, derived_from=p1_symptom.type)
    log.append(f"Step 4: D2 (midpoint of P1 primary window) = {d2}.")
    log.append(
        f"        Ghosted SPREAD lesion for {p2_name}: "
        f"{ghosted_spread.onset} → {ghosted_spread.end}."
    )

    # --- Steps 5 & 6 — Evaluate criteria ---
    log.append("")
    log.append("--- Evaluating SOURCE scenario (ghosted source for P2) ---")
    source_criteria = evaluate_criteria(
        lesion=ghosted_source,
        p1_symptom=p1_symptom,
        p2_symptoms=p2_symptoms,
        p2_exposure=p2_exposure_rec,
        op_exposure=op_exposure,
        p2_treatment_date=p2_treatment,
    )
    for k, v in source_criteria.items():
        icon = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]", "na": "[N/A ]"}.get(v["status"], "[?]")
        log.append(f"  {icon} {k.upper()}: {v['detail']}")

    log.append("")
    log.append("--- Evaluating SPREAD scenario (ghosted spread for P2) ---")
    spread_criteria = evaluate_criteria(
        lesion=ghosted_spread,
        p1_symptom=p1_symptom,
        p2_symptoms=p2_symptoms,
        p2_exposure=p2_exposure_rec,
        op_exposure=op_exposure,
        p2_treatment_date=p2_treatment,
    )
    for k, v in spread_criteria.items():
        icon = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]", "na": "[N/A ]"}.get(v["status"], "[?]")
        log.append(f"  {icon} {k.upper()}: {v['detail']}")

    # --- Step 7 — Verdict ---
    source_passes = _scenario_passes(source_criteria)
    spread_passes = _scenario_passes(spread_criteria)
    verdict = determine_verdict(source_passes, spread_passes, p1_role, p1_name, p2_name)

    log.append("")
    log.append("--- Conclusion ---")
    log.append(verdict)

    return GhostingResult(
        p1_name=p1_name,
        p2_name=p2_name,
        p1_symptom=p1_symptom,
        ghosted_source=ghosted_source,
        ghosted_spread=ghosted_spread,
        criteria={"source": source_criteria, "spread": spread_criteria},
        verdict=verdict,
        log=log,
    )
