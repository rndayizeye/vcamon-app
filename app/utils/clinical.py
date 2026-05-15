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

Naming conventions:
  Case1  — the person whose symptom anchors the analysis (highest rank)
  Case2  — the other person
  Date1  — likely inoculation date for Case1 (working back from Case1 symptom)
  Date2  — midpoint of Case1's infectious period (most likely transmission date)

Exposure criterion (scenario-specific):
  Source scenario  — Date1 must fall within the reported exposure window
                     (Case2 → Case1 transmission happened around Date1)
  Spread scenario  — Date2 must fall within the reported exposure window
                     (Case1 → Case2 transmission happened around Date2)
  Warn threshold   — if the relevant date misses the window by ≤ half the
                     average incubation period (10 days), warn instead of fail
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Syphilis natural history constants (days)
# Source: VCA Training slide 10, Marion County Public Health / NCSDDC 2022
# ---------------------------------------------------------------------------

INCUBATION = {"min": 10, "avg": 21, "max": 90}
PRIMARY    = {"min":  7, "avg": 21, "max": 35}
LATENCY    = {"min":  0, "avg": 28, "max": 70}
SECONDARY  = {"min": 14, "avg": 28, "max": 42}

INTERVIEW_PERIOD_PRIMARY_DAYS   = INCUBATION["max"] + PRIMARY["max"]           # 125
INTERVIEW_PERIOD_SECONDARY_DAYS = (
    INCUBATION["max"] + PRIMARY["max"] + LATENCY["max"] + SECONDARY["max"]    # 237
)

# Warn threshold for exposure check — half average incubation (10 days)
EXPOSURE_WARN_MARGIN_DAYS = INCUBATION["avg"] // 2   # 10

# Minimum latency between ghosted lesion end and secondary symptom onset
MIN_LATENCY_TO_SECONDARY_DAYS = 35   # 5 weeks

# ---------------------------------------------------------------------------
# Interview period — calculate earliest relevant date for case investigation based on symptoms and previous negative tests
# ---------------------------------------------------------------------------

def calc_interview_period_start(
    symptom_onset: date,
    symptom_type: str,
    last_negative_date: Optional[date] = None,
) -> date:
    """
    Calculate interview period start date.
    
    Standard: 125 days (primary) or 237 days (secondary) from onset
    With previous negative: Cannot go before (negative_date - 90 days)
    """
    if symptom_type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        standard_start = symptom_onset - timedelta(days=INTERVIEW_PERIOD_PRIMARY_DAYS)
    else:
        standard_start = symptom_onset - timedelta(days=INTERVIEW_PERIOD_SECONDARY_DAYS)
    
    if last_negative_date:
        floor = last_negative_date - timedelta(days=INCUBATION["max"])
        return max(standard_start, floor)
    
    return standard_start
# ---------------------------------------------------------------------------
# Symptom ranking — ghosting hierarchy
# ---------------------------------------------------------------------------

SYMPTOM_RANK: dict[str, int] = {
    "Primary Chancre":        1,
    "Historical Primary":     2,
    "Ghosted Primary":        3,
    "Secondary Rash/Lesions": 4,
}


def symptom_rank(symptom_type: str) -> int:
    return SYMPTOM_RANK.get(symptom_type, 99)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Symptom:
    type: str
    onset: date
    duration_days: int
    location: str | None = None  # "Anal LX", "Penile LX", etc.


@dataclass
class Exposure:
    first: date
    last: date
    sex_types: list[str] = field(default_factory=list)


@dataclass
class GhostedLesion:
    lesion_type: str        # "ghosted_source" | "ghosted_spread"
    onset: date
    end: date
    derived_from_symptom: str
    assigned_to: str        # "OP" | "partner"


@dataclass
class GhostingResult:
    case1_name: str
    case2_name: str
    case1_symptom: Symptom
    ghosted_source: GhostedLesion
    ghosted_spread: GhostedLesion
    criteria: dict
    verdict: str
    log: list[str]

    # Keep legacy aliases so existing page code doesn't break immediately
    @property
    def p1_name(self): return self.case1_name
    @property
    def p2_name(self): return self.case2_name
    @property
    def p1_symptom(self): return self.case1_symptom


# ---------------------------------------------------------------------------
# Step 1 — Select Case1
# ---------------------------------------------------------------------------

def select_case1(
    op_symptoms: list[Symptom],
    partner_symptoms: list[Symptom],
) -> tuple[str, Symptom, str, list[Symptom]]:
    """
    Compare OP and partner symptoms using the ghosting hierarchy.
    If ranks are equal, earlier onset becomes Case1.
    Returns (case1_role, case1_symptom, case2_role, case2_symptoms).
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

    op_rank = symptom_rank(op_best.type)
    partner_rank = symptom_rank(partner_best.type)

    # If ranks are equal, use onset date as tiebreaker
    if op_rank == partner_rank:
        # Earlier onset wins (higher priority)
        if partner_best.onset < op_best.onset:
            return "partner", partner_best, "OP", op_symptoms
        else:
            return "OP", op_best, "partner", partner_symptoms
    
    # Different ranks - lower rank number wins
    if op_rank < partner_rank:
        return "OP", op_best, "partner", partner_symptoms
    else:
        return "partner", partner_best, "OP", op_symptoms


# Legacy alias so existing call sites don't break
select_p1 = select_case1


# ---------------------------------------------------------------------------
# Step 2 — Calculate Date1 (likely inoculation date for Case1)
# ---------------------------------------------------------------------------

def calc_date1(symptom: Symptom) -> date:
    """
    Work backwards from Case1's symptom onset to estimate when Case1
    was inoculated (Date1).

    Primary / Historical / Ghosted:
        Date1 = onset − avg incubation (21 days)

    Secondary:
        Date1 = onset − avg latency − avg primary − avg incubation
    """
    if symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        return symptom.onset - timedelta(days=INCUBATION["avg"])
    elif symptom.type == "Secondary Rash/Lesions":
        days_back = INCUBATION["avg"] + PRIMARY["avg"] + LATENCY["avg"]
        return symptom.onset - timedelta(days=days_back)
    else:
        raise ValueError(f"Cannot calculate Date1 for symptom type: {symptom.type}")


# Legacy alias
avg_inoculation_date = calc_date1


# ---------------------------------------------------------------------------
# Step 3 — Ghosted source lesion for Case2
# Date1 is the midpoint of the ghosted source window
# ---------------------------------------------------------------------------

def calc_ghosted_source(date1: date, assigned_to: str, derived_from: str) -> GhostedLesion:
    """
    Date1 is the likely inoculation date of Case1.
    The ghosted source chancre for Case2 is centred on Date1:

        onset = Date1 − half avg primary duration  (10 days)
        end   = Date1 + half avg primary duration  (10 days)
    """
    half_primary = PRIMARY["avg"] // 2
    return GhostedLesion(
        lesion_type="ghosted_source",
        onset=date1 - timedelta(days=half_primary),
        end=date1   + timedelta(days=half_primary),
        derived_from_symptom=derived_from,
        assigned_to=assigned_to,
    )


# ---------------------------------------------------------------------------
# Step 4 — Date2 and ghosted spread lesion for Case2
# ---------------------------------------------------------------------------

def calc_date2(symptom: Symptom) -> date:
    """
    Date2 = midpoint of Case1's primary chancre — the point of peak
    infectiousness for Case1.

    Primary / Historical / Ghosted:
        Date2 = onset + (duration ÷ 2)

    Secondary only:
        Date2 = secondary onset − avg latency − half avg primary
    """
    if symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        dur = symptom.duration_days if symptom.duration_days > 0 else PRIMARY["avg"]
        return symptom.onset + timedelta(days=dur // 2)
    elif symptom.type == "Secondary Rash/Lesions":
        half_primary = PRIMARY["avg"] / 2
        return symptom.onset - timedelta(days=round(LATENCY["avg"] + half_primary))
    else:
        raise ValueError(f"Cannot calculate Date2 for symptom type: {symptom.type}")


# Legacy alias
calc_d2 = calc_date2


def calc_ghosted_spread(date2: date, assigned_to: str, derived_from: str) -> GhostedLesion:
    """
    Ghosted spread lesion for Case2, starting one avg incubation duration
    after Date2 (Case1's infectious midpoint):

        onset = Date2 + avg incubation (21 days)
        end   = onset + avg primary duration (21 days)
    """
    onset = date2 + timedelta(days=INCUBATION["avg"])
    end   = onset + timedelta(days=PRIMARY["avg"])
    return GhostedLesion(
        lesion_type="ghosted_spread",
        onset=onset,
        end=end,
        derived_from_symptom=derived_from,
        assigned_to=assigned_to,
    )


# ---------------------------------------------------------------------------
# Criteria evaluation
# ---------------------------------------------------------------------------

def _check_exposure(
    infectious_start: date,
    infectious_end: date,
    exposure: Optional[Exposure],
    scenario: str,
) -> tuple[str, str]:
    """
    Check if infectious period overlaps with exposure window.
    Any intersection = transmission possible.
    """
    if exposure is None or exposure.first is None or exposure.last is None:
        return "warn", "Exposure dates not recorded — cannot verify overlap."
    
    # Check period intersection
    overlaps = (infectious_start <= exposure.last and 
                exposure.first <= infectious_end)
    
    if overlaps:
        overlap_days = (min(infectious_end, exposure.last) - 
                       max(infectious_start, exposure.first)).days + 1
        return "pass", (
            f"Infectious period ({infectious_start} → {infectious_end}) "
            f"overlaps exposure ({exposure.first} → {exposure.last}) "
            f"by {overlap_days} day(s)."
        )
        # Calculate gap
    if infectious_end < exposure.first:
        gap = (exposure.first - infectious_end).days
        direction = "before"
    else:
        gap = (infectious_start - exposure.last).days
        direction = "after"
    
    if gap <= EXPOSURE_WARN_MARGIN_DAYS:
        return "warn", (
            f"Infectious period ends {gap} day(s) {direction} exposure window "
            f"(within {EXPOSURE_WARN_MARGIN_DAYS}-day warn margin)."
        )
    
    return "fail", (
        f"No overlap: infectious period is {gap} day(s) {direction} "
        f"exposure window (exceeds warn margin)."
    )

    # Outside window — check warn margin
    days_before = (exposure.first - check_date).days   # positive if before window
    days_after  = (check_date - exposure.last).days    # positive if after window
    margin = EXPOSURE_WARN_MARGIN_DAYS

    if days_before > 0 and days_before <= margin:
        return "warn", (
            f"{date_label} ({check_date}) is {days_before} day(s) before the exposure "
            f"window ({exposure.first} to {exposure.last}) — within {margin}-day warn margin."
        )
    if days_after > 0 and days_after <= margin:
        return "warn", (
            f"{date_label} ({check_date}) is {days_after} day(s) after the exposure "
            f"window ({exposure.first} to {exposure.last}) — within {margin}-day warn margin."
        )

    # Beyond warn margin
    miss = max(days_before, days_after)
    return "fail", (
        f"{date_label} ({check_date}) is {miss} day(s) outside the exposure window "
        f"({exposure.first} to {exposure.last}) — exceeds {margin}-day warn margin."
    )


def _sex_type_compatible(
    symptom: Symptom,
    sex_types: list[str],
) -> tuple[str, str]:
    if not sex_types:
        return "warn", "Sex types not recorded — cannot check anatomical compatibility."
    
    # Use location if available, fall back to type
    check_string = (symptom.location or symptom.type).lower()
    sex_lower = [s.lower() for s in sex_types]
    
    compatible = False
    if "anal" in check_string or "rectal" in check_string:
        compatible = any("anal" in s for s in sex_lower)
    elif "penile" in check_string or "vaginal" in check_string:
        compatible = any(k in s for s in sex_lower for k in ("vaginal", "anal"))
    elif "oral" in check_string:
        compatible = any("oral" in s for s in sex_lower)
    else:
        # No location data or unknown type
        if symptom.location is None:
            return "warn", "Lesion location not recorded — cannot verify compatibility."
        compatible = True  # Lab LX or other non-specific
    
    if compatible:
        return "pass", (
            f"Lesion location ({symptom.location or symptom.type}) is consistent "
            f"with reported sex types ({', '.join(sex_types)})."
        )
    return "fail", (
        f"Lesion location ({symptom.location or symptom.type}) may NOT be consistent "
        f"with reported sex types ({', '.join(sex_types)}). Manual verification needed."
    )


def _latency_to_secondary(
    lesion_end: date,
    case2_symptoms: list[Symptom],
) -> tuple[str, str]:
    secondary = [s for s in case2_symptoms if s.type == "Secondary Rash/Lesions"]
    if not secondary:
        return "na", "Case2 has no secondary symptoms — latency check not applicable."

    earliest_sec = min(s.onset for s in secondary)
    gap = (earliest_sec - lesion_end).days

    if gap >= MIN_LATENCY_TO_SECONDARY_DAYS:
        return "pass", (
            f"{gap} days between ghosted lesion end ({lesion_end}) and "
            f"Case2 secondary onset ({earliest_sec}) — meets ≥5-week requirement."
        )
    return "fail", (
        f"Only {gap} days between ghosted lesion end ({lesion_end}) and "
        f"Case2 secondary onset ({earliest_sec}) — less than required "
        f"{MIN_LATENCY_TO_SECONDARY_DAYS} days."
    )


def _natural_order(
    lesion: GhostedLesion,
    case2_symptoms: list[Symptom],
    case2_treatment_date: Optional[date],
) -> tuple[str, str]:
    issues = []

    secondary = [s for s in case2_symptoms if s.type == "Secondary Rash/Lesions"]
    if secondary:
        earliest_sec = min(s.onset for s in secondary)
        if lesion.onset >= earliest_sec:
            issues.append(
                f"Ghosted lesion onset ({lesion.onset}) is on/after Case2 secondary "
                f"onset ({earliest_sec}) — violates primary-before-secondary order."
            )

    if case2_treatment_date and lesion.onset >= case2_treatment_date:
        issues.append(
            f"Ghosted lesion onset ({lesion.onset}) is on/after Case2 treatment "
            f"({case2_treatment_date}) — symptoms should not appear after treatment."
        )

    if issues:
        return "fail", " | ".join(issues)
    return "pass", "Ghosted lesion follows natural syphilis progression order."


def evaluate_criteria(
    scenario: str,                          # "source" or "spread"
    lesion: GhostedLesion,
    case1_symptom: Symptom,
    case2_symptoms: list[Symptom],
    case2_exposure: Optional[Exposure],
    op_exposure: Optional[Exposure],
    case2_treatment_date: Optional[date],
    date1: Optional[date] = None,
    date2: Optional[date] = None,
) -> dict:
    """
    Run all four criteria checks for one scenario.

    Exposure check is scenario-specific:
      source scenario → Date1 must be within exposure window
      spread scenario → Date2 must be within exposure window
    """
    exposure = case2_exposure or op_exposure

    # Exposure overlap check - use period intersection
    if scenario == "source":
        # Case2 must be infectious during Case1's exposure
        infectious_start = lesion.onset
        infectious_end = lesion.end
    else:  # spread
        # Case1 must be infectious during Case2's exposure
        dur = case1_symptom.duration_days if case1_symptom.duration_days > 0 else PRIMARY["avg"]
        infectious_start = case1_symptom.onset
        infectious_end = case1_symptom.onset + timedelta(days=dur)
    
    exp_status, exp_detail = _check_exposure(
        infectious_start, infectious_end, exposure, scenario
    )

    sex_status, sex_detail = _sex_type_compatible(
        case1_symptom, exposure.sex_types if exposure else []
    )
    lat_status, lat_detail = _latency_to_secondary(lesion.end, case2_symptoms)
    ord_status, ord_detail = _natural_order(lesion, case2_symptoms, case2_treatment_date)

    return {
        "exposure":      {"status": exp_status, "detail": exp_detail},
        "sex_type":      {"status": sex_status, "detail": sex_detail},
        "latency":       {"status": lat_status, "detail": lat_detail},
        "natural_order": {"status": ord_status, "detail": ord_detail},
    }


def _scenario_passes(criteria: dict) -> bool:
    return all(v["status"] != "fail" for v in criteria.values())


# ---------------------------------------------------------------------------
# Step 6 — Verdict
# ---------------------------------------------------------------------------

def determine_verdict(
    source_passes: bool,
    spread_passes: bool,
    case1_role: str,
    case1_name: str,
    case2_name: str,
) -> str:
    if source_passes and not spread_passes:
        if case1_role == "OP":
            return f"OP ({case1_name}) is the SOURCE of infection for partner ({case2_name})."
        else:
            return f"Partner ({case1_name}) is the SOURCE of infection for OP ({case2_name})."
    elif spread_passes and not source_passes:
        if case1_role == "OP":
            return f"Partner ({case2_name}) is the SOURCE — OP ({case1_name}) is a SPREAD."
        else:
            return f"OP ({case2_name}) is the SOURCE — partner ({case1_name}) is a SPREAD."
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
    op_exposure: Optional[Exposure],
    op_treatment_date: Optional[date],

    partner_name: str,
    partner_symptoms: list[Symptom],
    partner_exposure: Optional[Exposure],
    partner_treatment_date: Optional[date],
) -> GhostingResult:
    """
    Full ghosting analysis pipeline following VCA methodology.

    Steps:
      1. Identify Case1 (highest-ranking symptom)
      2. Calculate Date1 (likely inoculation date for Case1)
      3. Calculate ghosted SOURCE lesion for Case2 (centred on Date1)
      4. Calculate Date2 (Case1's infectious midpoint)
      5. Calculate ghosted SPREAD lesion for Case2
      6. Evaluate source scenario — Date1 vs exposure window
      7. Evaluate spread scenario — Date2 vs exposure window
      8. Determine verdict
    """
    log: list[str] = ["=== VCA Ghosting Analysis ===", ""]

    # --- Step 1 ---
    case1_role, case1_symptom, case2_role, case2_symptoms = select_case1(
        op_symptoms, partner_symptoms
    )
    case1_name = op_name      if case1_role == "OP" else partner_name
    case2_name = partner_name if case1_role == "OP" else op_name
    case2_treatment = partner_treatment_date if case1_role == "OP" else op_treatment_date
    case2_exposure  = partner_exposure       if case1_role == "OP" else op_exposure

    log.append(
        f"Step 1: Case1 = {case1_name} ({case1_role}) with '{case1_symptom.type}' "
        f"(rank {symptom_rank(case1_symptom.type)}) on {case1_symptom.onset}."
    )
    log.append(f"        Case2 = {case2_name} ({case2_role}).")

    # --- Step 2 ---
    date1 = calc_date1(case1_symptom)
    log.append(f"Step 2: Date1 (likely inoculation date for Case1) = {date1}.")

    # --- Step 3 ---
    ghosted_source = calc_ghosted_source(date1, assigned_to=case2_role,
                                         derived_from=case1_symptom.type)
    log.append(
        f"Step 3: Ghosted SOURCE lesion for {case2_name}: "
        f"{ghosted_source.onset} → {ghosted_source.end}."
    )

    # --- Step 4 ---
    date2 = calc_date2(case1_symptom)
    ghosted_spread = calc_ghosted_spread(date2, assigned_to=case2_role,
                                         derived_from=case1_symptom.type)
    log.append(f"Step 4: Date2 (Case1 infectious midpoint) = {date2}.")
    log.append(
        f"        Ghosted SPREAD lesion for {case2_name}: "
        f"{ghosted_spread.onset} → {ghosted_spread.end}."
    )

    # --- Steps 5 & 6 — evaluate criteria ---
    log.append("")
    log.append("--- Evaluating SOURCE scenario (Date1 vs exposure window) ---")
    source_criteria = evaluate_criteria(
        scenario="source",
        lesion=ghosted_source,
        case1_symptom=case1_symptom,
        case2_symptoms=case2_symptoms,
        case2_exposure=case2_exposure,
        op_exposure=op_exposure,
        case2_treatment_date=case2_treatment,
        date1=date1,
        date2=date2,
    )
    for k, v in source_criteria.items():
        icon = {"pass": "[PASS]", "fail": "[FAIL]",
                "warn": "[WARN]", "na":   "[N/A ]"}.get(v["status"], "[?]")
        log.append(f"  {icon} {k.upper()}: {v['detail']}")

    log.append("")
    log.append("--- Evaluating SPREAD scenario (Date2 vs exposure window) ---")
    spread_criteria = evaluate_criteria(
        scenario="spread",
        lesion=ghosted_spread,
        case1_symptom=case1_symptom,
        case2_symptoms=case2_symptoms,
        case2_exposure=case2_exposure,
        op_exposure=op_exposure,
        case2_treatment_date=case2_treatment,
        date1=date1,
        date2=date2,
    )
    for k, v in spread_criteria.items():
        icon = {"pass": "[PASS]", "fail": "[FAIL]",
                "warn": "[WARN]", "na":   "[N/A ]"}.get(v["status"], "[?]")
        log.append(f"  {icon} {k.upper()}: {v['detail']}")

    # --- Step 7 — verdict ---
    source_passes = _scenario_passes(source_criteria)
    spread_passes = _scenario_passes(spread_criteria)
    verdict = determine_verdict(source_passes, spread_passes,
                                case1_role, case1_name, case2_name)

    log.append("")
    log.append("--- Conclusion ---")
    log.append(verdict)

    return GhostingResult(
        case1_name=case1_name,
        case2_name=case2_name,
        case1_symptom=case1_symptom,
        ghosted_source=ghosted_source,
        ghosted_spread=ghosted_spread,
        criteria={"source": source_criteria, "spread": spread_criteria},
        verdict=verdict,
        log=log,
    )
