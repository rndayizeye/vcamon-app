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

Exposure criterion (scenario-specific) — an infectious window must OVERLAP the
reported sexual-exposure window (any intersection ⇒ transmission possible):
  Source scenario  — Case2's ghosted source chancre window (centred on Date1)
                     (Case2 → Case1 transmission happened around Date1)
  Spread scenario  — Case1's primary chancre window; when Case1's anchor is a
                     secondary symptom that chancre is ghosted (centred on Date2),
                     and the window is clipped at Case1's treatment date
                     (Case1 → Case2 transmission happened around Date2)
  Warn threshold   — if the windows miss each other by ≤ half the average
                     incubation period (10 days), warn instead of fail
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from app.db.models import SymptomClassification, SymptomDateKind, SymptomDurationSource

# ---------------------------------------------------------------------------
# Syphilis natural history constants (days)
# Source: VCA Training slide 10, Marion County Public Health / NCSDDC 2022
# ---------------------------------------------------------------------------

INCUBATION = {"min": 10, "avg": 21, "max": 90}
PRIMARY = {"min": 7, "avg": 21, "max": 35}
LATENCY = {"min": 0, "avg": 28, "max": 70}
SECONDARY = {"min": 14, "avg": 28, "max": 42}

# Ordered confidence labels → integer rank (higher = stronger evidence).
# Shared by determine_verdict, run_ghosting_analysis, and all callers.
CONFIDENCE_RANK: dict[str, int] = {
    "Robust": 5, "Likely": 4, "Possible": 3, "Weak": 2, "Unlikely": 1, "Unrelated": 0,
}
_CONFIDENCE_LEVELS: dict[int, str] = {v: k for k, v in CONFIDENCE_RANK.items()}

_ZERO_DUR_PRIMARY_TYPES = frozenset(
    {"Primary Chancre", "Historical Primary", "Ghosted Primary"}
)
_ZERO_DUR_SECONDARY_TYPES = frozenset(
    {"Secondary Rash/Lesions", "Historical Secondary", "Ghosted Secondary"}
)

INTERVIEW_PERIOD_PRIMARY_DAYS = INCUBATION["max"] + PRIMARY["max"]  # 125
INTERVIEW_PERIOD_SECONDARY_DAYS = (
    INCUBATION["max"] + PRIMARY["max"] + LATENCY["max"] + SECONDARY["max"]  # 237
)

# Warn threshold for exposure check — half average incubation (10 days)
EXPOSURE_WARN_MARGIN_DAYS = INCUBATION["avg"] // 2  # 10

# Max gap (days) allowed between a ghosted chancre and the comparison patient's
# OWN confirmed primary chancre before that transmission direction is ruled out.
PRIMARY_CONSISTENCY_TOLERANCE_DAYS = INCUBATION["avg"]  # 21

# Plausible latency between a (ghosted) primary chancre healing and the onset of
# secondary symptoms is the natural-history latency band itself: LATENCY min..max
# (0–70 days per the VCA training). There is no fixed 5-week floor in the method.

# ---------------------------------------------------------------------------
# Interview period — calculate earliest relevant date for case investigation based on symptoms and previous negative tests
# ---------------------------------------------------------------------------


def resolve_zero_duration_symptom(symptom: "Symptom") -> "Symptom":
    """
    When duration_days==0, the entered date is the observation date (last day
    of the longest possible duration). Back-calculate onset using the max
    duration for the symptom's stage. Returns symptom unchanged if duration
    is known or the type is unrecognised.
    """
    if symptom.duration_days != 0:
        return symptom
    if symptom.type in _ZERO_DUR_PRIMARY_TYPES:
        dur = PRIMARY["max"]
    elif symptom.type in _ZERO_DUR_SECONDARY_TYPES:
        dur = SECONDARY["max"]
    else:
        return symptom
    return Symptom(
        type=symptom.type,
        onset=symptom.onset - timedelta(days=dur),
        duration_days=dur,
        anatomical_site=symptom.anatomical_site,
    )


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
    "Primary Chancre": 1,
    "Historical Primary": 2,
    "Ghosted Primary": 3,
    "Secondary Rash/Lesions": 4,
}


def symptom_rank(symptom_type: str) -> int:
    return SYMPTOM_RANK.get(symptom_type, 99)


# ---------------------------------------------------------------------------
# Symptom classification — shared UI/save helper (Primary vs Secondary)
# ---------------------------------------------------------------------------

# Values mirror LesionType enum  →  Primary syphilis
_PRIMARY_LESION_VALUES: frozenset[str] = frozenset(
    {
        "Anal LX",
        "Non-genital LX",
        "LX",
        "Oral LX",
        "Penile LX",
        "Rectal LX",
        "Vaginal LX",
    }
)

# Values mirror Symptom enum  →  Secondary syphilis
_SECONDARY_SYMPTOM_VALUES: frozenset[str] = frozenset(
    {
        "Rash",
        "PP Rash",
        "GB Rash",
        "C-lata",
        "Alopecia",
    }
)


def get_symptom_classification(symptom_type: str | None) -> str | None:
    """
    Derive Primary / Secondary classification from a symptom or lesion type
    string as stored in SymptomEntry.symptom_type.

    Returns "Primary", "Secondary", or None if the type is unrecognised.
    Called on every save so the DB value always reflects the current type;
    the user never needs to set it manually.
    """
    if not symptom_type:
        return None
    if symptom_type in _PRIMARY_LESION_VALUES:
        return SymptomClassification.PRIMARY.value
    if symptom_type in _SECONDARY_SYMPTOM_VALUES:
        return SymptomClassification.SECONDARY.value
    return None


def normalize_symptom_date_kind(
    date_kind: SymptomDateKind | str | None,
) -> SymptomDateKind:
    if isinstance(date_kind, SymptomDateKind):
        return date_kind
    if not date_kind:
        return SymptomDateKind.ONSET_REPORTED

    for option in SymptomDateKind:
        if date_kind in {option.value, option.name}:
            return option

    return SymptomDateKind.ONSET_REPORTED


def get_symptom_max_duration_days(
    symptom_type: str | None = None,
    classification: str | None = None,
) -> int | None:
    resolved_classification = classification or get_symptom_classification(symptom_type)

    if resolved_classification == SymptomClassification.PRIMARY.value:
        return PRIMARY["max"]
    if resolved_classification == SymptomClassification.SECONDARY.value:
        return SECONDARY["max"]
    return None


def derive_symptom_capture_metadata(
    symptom_type: str | None,
    anchor_date: date | None,
    duration_days: int | None,
    date_kind: SymptomDateKind | str | None,
    classification: str | None = None,
) -> tuple[SymptomDateKind, SymptomDurationSource, bool]:
    normalized_date_kind = normalize_symptom_date_kind(date_kind)
    derived_ongoing = (
        normalized_date_kind == SymptomDateKind.OBSERVED_DURING_EXAM
        and anchor_date is not None
    )

    if duration_days is not None:
        duration_source = SymptomDurationSource.REPORTED
    elif (
        normalized_date_kind == SymptomDateKind.OBSERVED_DURING_EXAM
        and get_symptom_max_duration_days(symptom_type, classification) is not None
    ):
        duration_source = SymptomDurationSource.ASSUMED_MAX
    else:
        duration_source = SymptomDurationSource.UNKNOWN

    return normalized_date_kind, duration_source, derived_ongoing


def resolve_symptom_timing_for_analysis(
    symptom_type: str | None,
    anchor_date: date | None,
    duration_days: int | None,
    date_kind: SymptomDateKind | str | None,
    classification: str | None = None,
) -> tuple[date | None, int]:
    if not anchor_date:
        return None, duration_days or 0

    normalized_date_kind, _, _ = derive_symptom_capture_metadata(
        symptom_type=symptom_type,
        anchor_date=anchor_date,
        duration_days=duration_days,
        date_kind=date_kind,
        classification=classification,
    )

    if normalized_date_kind == SymptomDateKind.OBSERVED_DURING_EXAM:
        effective_duration = duration_days
        if effective_duration is None:
            effective_duration = get_symptom_max_duration_days(
                symptom_type=symptom_type,
                classification=classification,
            )
        if effective_duration is None:
            return anchor_date, 0
        return anchor_date - timedelta(days=effective_duration), effective_duration

    return anchor_date, duration_days or 0


def derive_symptom_end_date(
    anchor_date: date | None,
    duration_days: int | None,
    date_kind: SymptomDateKind | str | None,
) -> date | None:
    if not anchor_date:
        return None

    if normalize_symptom_date_kind(date_kind) == SymptomDateKind.OBSERVED_DURING_EXAM:
        return anchor_date

    if duration_days is None:
        return None

    return anchor_date + timedelta(days=duration_days)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Symptom:
    type: str
    onset: date
    duration_days: int
    anatomical_site: str | None = None  # "Anal LX", "Penile LX", etc.


@dataclass
class Exposure:
    first: date
    last: date


@dataclass
class GhostedLesion:
    lesion_type: str  # "ghosted_source" | "ghosted_spread"
    onset: date
    end: date
    derived_from_symptom: str
    assigned_to: str  # "OP" | "partner"


@dataclass
class ScenarioResult:
    """Results for a specific transmission direction across all constant ranges."""

    range_data: dict[
        str, dict
    ]  # Maps 'aggressive'|'expected'|'conservative' -> criteria_dict
    range_lesions: dict[
        str, GhostedLesion
    ]  # Maps 'aggressive'|'expected'|'conservative' -> GhostedLesion
    confidence: str  # "Robust", "Likely", "Possible", "Weak", "Unlikely", "Unrelated"
    pass_count: int  # Number of tiers that passed (0-5)


@dataclass
class GhostingResult:
    case1_name: str
    case2_name: str
    case1_symptom: Symptom
    source_scenarios: ScenarioResult
    spread_scenarios: ScenarioResult
    verdict: str
    log: list[str]

    # Keep legacy aliases so existing page code doesn't break immediately
    @property
    def p1_name(self):
        return self.case1_name

    @property
    def p2_name(self):
        return self.case2_name

    @property
    def p1_symptom(self):
        return self.case1_symptom

    @property
    def ghosted_source(self):
        return self.source_scenarios.range_lesions["expected"]

    @property
    def ghosted_spread(self):
        return self.spread_scenarios.range_lesions["expected"]

    @property
    def criteria(self):
        return {
            "source": self.source_scenarios.range_data["expected"],
            "spread": self.spread_scenarios.range_data["expected"],
        }


# ---------------------------------------------------------------------------
# Step 1 — Select Case1
# ---------------------------------------------------------------------------


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

    op_best = best(op_symptoms)
    partner_best = best(partner_symptoms)

    if op_best is None and partner_best is None:
        raise ValueError(
            "Neither the OP nor the partner has usable symptoms for ghosting."
        )

    if op_best is None:
        return "partner", partner_best, "OP", op_symptoms
    if partner_best is None:
        return "OP", op_best, "partner", partner_symptoms

    op_rank = symptom_rank(op_best.type)
    partner_rank = symptom_rank(partner_best.type)

    # If ranks are equal, OP always anchors — the investigation is OP-centered
    if op_rank == partner_rank:
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


def _stage_key(stage_keys: dict | None, stage: str, fallback: str) -> str:
    """Return the constant tier key ('min'/'avg'/'max') for a specific stage.

    When stage_keys is provided (cross-scenario analysis), each natural-history
    stage may use a different tier. Falls back to the global constant_key for
    callers that still use the single-key API.
    """
    return stage_keys.get(stage, fallback) if stage_keys else fallback


def calc_date1(symptom: Symptom, constant_key: str = "avg", stage_keys: dict | None = None) -> date:
    """
    Work backwards from Case1's symptom onset to estimate when Case1
    was inoculated (Date1).
    """
    inc_k = _stage_key(stage_keys, "incubation", constant_key)
    pri_k = _stage_key(stage_keys, "primary", constant_key)
    lat_k = _stage_key(stage_keys, "latency", constant_key)
    if symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        return symptom.onset - timedelta(days=INCUBATION[inc_k])
    elif symptom.type == "Secondary Rash/Lesions":
        days_back = INCUBATION[inc_k] + PRIMARY[pri_k] + LATENCY[lat_k]
        return symptom.onset - timedelta(days=days_back)
    else:
        raise ValueError(f"Cannot calculate Date1 for symptom type: {symptom.type}")


# Legacy alias
def avg_inoculation_date(symptom: Symptom) -> date:
    return calc_date1(symptom, constant_key="avg")


# ---------------------------------------------------------------------------
# Step 3 — Ghosted source lesion for Case2
# Date1 is the midpoint of the ghosted source window
# ---------------------------------------------------------------------------


def calc_ghosted_source(
    date1: date, assigned_to: str, derived_from: str, constant_key: str = "avg",
    stage_keys: dict | None = None,
) -> GhostedLesion:
    """
    Date1 is the likely inoculation date of Case1.
    The ghosted source chancre for Case2 is centred on Date1.
    """
    half_primary = PRIMARY[_stage_key(stage_keys, "primary", constant_key)] // 2
    return GhostedLesion(
        lesion_type="ghosted_source",
        onset=date1 - timedelta(days=half_primary),
        end=date1 + timedelta(days=half_primary),
        derived_from_symptom=derived_from,
        assigned_to=assigned_to,
    )


# ---------------------------------------------------------------------------
# Step 4 — Date2 and ghosted spread lesion for Case2
# ---------------------------------------------------------------------------


def calc_date2(symptom: Symptom, constant_key: str = "avg", stage_keys: dict | None = None) -> date:
    """
    Date2 = midpoint of Case1's primary chancre — the point of peak
    infectiousness for Case1.
    """
    pri_k = _stage_key(stage_keys, "primary", constant_key)
    lat_k = _stage_key(stage_keys, "latency", constant_key)
    if symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        dur = symptom.duration_days if symptom.duration_days > 0 else PRIMARY[pri_k]
        return symptom.onset + timedelta(days=dur // 2)
    elif symptom.type == "Secondary Rash/Lesions":
        half_primary = PRIMARY[pri_k] / 2
        return symptom.onset - timedelta(days=round(LATENCY[lat_k] + half_primary))
    else:
        raise ValueError(f"Cannot calculate Date2 for symptom type: {symptom.type}")


# Legacy alias
calc_d2 = calc_date2


def calc_ghosted_spread(
    date2: date, assigned_to: str, derived_from: str, constant_key: str = "avg",
    stage_keys: dict | None = None,
) -> GhostedLesion:
    """
    Ghosted spread lesion for Case2, starting one incubation duration
    after Date2 (Case1's infectious midpoint).
    """
    onset = date2 + timedelta(days=INCUBATION[_stage_key(stage_keys, "incubation", constant_key)])
    end = onset + timedelta(days=PRIMARY[_stage_key(stage_keys, "primary", constant_key)])
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
    inoculation_date: Optional[date] = None,
) -> tuple[str, str]:
    """
    Check exposure window against the infectious period.

    Clean pass (VCA rule): the inoculation date falls *within* the reported
    exposure window (and the infectious period overlaps it).
    Overlap-only warn: the infectious period overlaps but the inoculation date
    is outside the window — transmission is possible but timing is borderline.
    Fail: no overlap at all (subject to the near-miss warn margin).
    """
    if exposure is None or exposure.first is None or exposure.last is None:
        return "warn", "Exposure dates not recorded — cannot verify overlap."

    overlaps = infectious_start <= exposure.last and exposure.first <= infectious_end

    if overlaps:
        overlap_days = (
            min(infectious_end, exposure.last) - max(infectious_start, exposure.first)
        ).days + 1
        if inoculation_date is None:
            raise ValueError(
                "_check_exposure: inoculation_date must be provided when the infectious "
                "period overlaps the exposure window — pass date1 (source scenario) or "
                "date2 (spread scenario) via evaluate_criteria"
            )
        # Clean pass: inoculation date is within the exposure window
        if exposure.first <= inoculation_date <= exposure.last:
            return "pass", (
                f"Inoculation date ({inoculation_date}) is within exposure window "
                f"({exposure.first} → {exposure.last}); infectious period overlaps "
                f"by {overlap_days} day(s)."
            )
        # Overlap-only warn: inoculation date outside the exposure window
        return "warn", (
            f"Infectious period ({infectious_start} → {infectious_end}) "
            f"overlaps exposure ({exposure.first} → {exposure.last}) "
            f"by {overlap_days} day(s), but inoculation date "
            f"({inoculation_date}) falls outside the window — borderline timing."
        )

    # No overlap — calculate gap
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


def _confirmed_primaries(symptoms: list[Symptom]) -> list[Symptom]:
    """Primaries that were actually OBSERVED on this patient — used to rule out a
    transmission direction in ``_natural_order``.

    Deliberately excludes "Ghosted Primary": a ghosted primary is itself a
    derived/inferred lesion, so it cannot be used as independent evidence to
    contradict a scenario's ghosted window. Contrast ``_best_primary_symptom``,
    which DOES include ghosted primaries — there it only needs a representative
    lesion for the anatomical-site check, where an inferred site is acceptable.
    """
    return [
        s
        for s in symptoms
        if s.type in ("Primary Chancre", "Historical Primary")
    ]


def _sex_type_compatible(
    symptom: Symptom,
    body_parts: list[str],
) -> tuple[str, str]:
    """
    Check if the lesion's anatomical site is consistent with the body parts
    this person reported using during sexual contact.
    """
    if not body_parts:
        return "warn", "Body parts not recorded — cannot check anatomical compatibility."

    site = (symptom.anatomical_site or symptom.type).lower()
    parts_lower = [p.lower() for p in body_parts]
    parts_display = ", ".join(body_parts)

    if "penile" in site or "penis" in site:
        site_label, compatible = "Penile", "penis" in parts_lower
    elif "vaginal" in site or "vagina" in site:
        site_label, compatible = "Vaginal", "vagina" in parts_lower
    elif "anal" in site or "rectal" in site or "anus" in site or "rectum" in site:
        site_label, compatible = "Anal/rectal", "anus" in parts_lower
    elif "oral" in site or "mouth" in site or "lip" in site:
        site_label, compatible = "Oral", "mouth" in parts_lower
    else:
        if symptom.anatomical_site is None:
            return "warn", "Lesion location not recorded — cannot verify compatibility."
        return "pass", "Non-specific lesion site — anatomical compatibility not applicable."

    if compatible:
        return "pass", (
            f"{site_label} lesion is consistent with reported body parts used ({parts_display})."
        )
    return "fail", (
        f"{site_label} lesion is NOT consistent with reported body parts used ({parts_display}). "
        f"The lesion site was not used during sexual contact with this partner."
    )


def _best_primary_symptom(symptoms: list[Symptom]) -> Optional[Symptom]:
    """Pick the comparison patient's representative primary chancre for the
    anatomical check, preferring one with a known anatomical site.

    Includes "Ghosted Primary" on purpose (unlike ``_confirmed_primaries``): this
    only needs a representative lesion site for the anatomical-compatibility
    check, not independent evidence to rule out a direction.
    """
    primaries = [
        s
        for s in symptoms
        if s.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary")
    ]
    if not primaries:
        return None
    with_site = [s for s in primaries if s.anatomical_site]
    pool = with_site or primaries
    return min(pool, key=lambda s: symptom_rank(s.type))


def _anatomical_compatibility(
    source_symptom: Optional[Symptom],
    source_body_parts: list[str],
    recipient_symptom: Optional[Symptom],
    recipient_body_parts: list[str],
) -> tuple[str, str]:
    """
    Two-sided anatomical-compatibility check (VCA criterion 2).

    A chancre appears at the site of inoculation, so each party's known primary
    chancre site must be consistent with a body part they reported using with the
    partner: the source must have had an infectious lesion at a site used during
    contact, and the recipient's chancre marks where they were inoculated. We
    check whichever sides have data; ghosted lesions carry no site, so an unknown
    side degrades to a warn rather than a hard pass/fail.
    """
    sides: list[tuple[str, str, str]] = []
    if source_symptom is not None:
        s_status, s_detail = _sex_type_compatible(source_symptom, source_body_parts)
        sides.append(("Source", s_status, s_detail))
    if recipient_symptom is not None:
        r_status, r_detail = _sex_type_compatible(
            recipient_symptom, recipient_body_parts
        )
        sides.append(("Recipient", r_status, r_detail))

    if not sides:
        return "warn", "No lesion sites recorded — cannot check anatomical compatibility."

    detail = " | ".join(f"{label}: {d}" for label, _, d in sides)
    statuses = {st for _, st, _ in sides}
    if "fail" in statuses:
        return "fail", detail
    if "warn" in statuses:
        return "warn", detail
    if "pass" in statuses:
        return "pass", detail
    return "na", detail


def _latency_to_secondary(
    lesion: GhostedLesion,
    case2_symptoms: list[Symptom],
    case2_name: str = "the comparison patient",
) -> tuple[str, str]:
    """
    Check that sufficient latency exists between the ghosted lesion end and
    the comparison patient's earliest secondary symptom.

    Accepts the full GhostedLesion (not just lesion_end) so it can distinguish
    two clinically distinct negative-gap situations:

      overlap        lesion.onset < sec.onset ≤ lesion.end
                     Primary was started before secondary and was still active
                     when secondary appeared.  Latency min = 0 permits this
                     but it is suspicious and warrants review.

      reversed       lesion.onset ≥ sec.onset
                     Secondary appeared before the ghosted primary even started.
                     Impossible under natural progression; _natural_order also
                     returns a hard FAIL for this case.
    """
    secondary = [s for s in case2_symptoms if s.type == "Secondary Rash/Lesions"]
    if not secondary:
        return "na", f"{case2_name} has no secondary symptoms — latency check not applicable."

    earliest_sec = min(s.onset for s in secondary)
    gap = (earliest_sec - lesion.end).days

    if gap < 0:
        if lesion.onset < earliest_sec:
            # True overlap: primary started before secondary but was still active
            # when secondary appeared (lesion.onset < sec <= lesion.end).
            return "fail", (
                f"Primary-secondary overlap: ghosted lesion end ({lesion.end}) is "
                f"{abs(gap)} day(s) after {case2_name}'s secondary symptom onset ({earliest_sec}) - "
                f"the chancre was still present when secondary symptoms appeared."
            )
        else:
            # Reversed timeline: secondary appeared before the ghosted primary even
            # started (lesion.onset >= sec.onset). _natural_order reports a hard FAIL
            # for the same reason; this message adds the latency dimension.
            days_before = (lesion.onset - earliest_sec).days
            return "fail", (
                f"Reversed timeline: {case2_name}'s secondary symptoms began ({earliest_sec}) "
                f"{days_before} day(s) before ghosted lesion onset ({lesion.onset}) - "
                f"secondary preceded primary, which is impossible under natural progression."
            )

    # Gap >= 0: the gap is the implied latency between primary healing and secondary
    # onset. Plausible values fall within the natural-history latency band (0..max).
    if gap > LATENCY["max"]:
        return "warn", (
            f"{gap} days between ghosted lesion end ({lesion.end}) and {case2_name}'s "
            f"secondary symptom onset ({earliest_sec}) exceeds the maximum latency "
            f"({LATENCY['max']} days) - the secondary may belong to a separate episode; "
            f"manual review recommended."
        )

    return "pass", (
        f"{gap} days between ghosted lesion end ({lesion.end}) and {case2_name}'s "
        f"secondary symptom onset ({earliest_sec}) falls within the "
        f"{LATENCY['min']}-{LATENCY['max']}-day latency range."
    )

def _natural_order(
    lesion: GhostedLesion,
    case2_symptoms: list[Symptom],
    case2_treatment_date: Optional[date],
    case2_name: str = "the comparison patient",
) -> tuple[str, str]:
    """Check the ghosted lesion against the comparison patient's own timeline.

    Three checks fold into this one criterion (rather than adding new keys to the
    criteria dict, which would ripple into the API schema and the React UI):
      1. primary-before-secondary ordering,
      2. lesion must predate the patient's treatment,
      3. two-confirmed-primaries viability — when the comparison patient has an
         OBSERVED primary chancre (see ``_confirmed_primaries``), the ghosted
         window must coincide with it within ``PRIMARY_CONSISTENCY_TOLERANCE_DAYS``;
         a far-off real chancre makes this transmission direction impossible.
    """
    fail_issues: list[str] = []
    warn_issues: list[str] = []

    secondary = [s for s in case2_symptoms if s.type == "Secondary Rash/Lesions"]
    if secondary:
        earliest_sec = min(s.onset for s in secondary)
        if lesion.onset >= earliest_sec:
            # Hard fail: primary started on or after secondary — impossible biology
            fail_issues.append(
                f"Ghosted lesion onset ({lesion.onset}) is on/after {case2_name}'s secondary "
                f"symptom onset ({earliest_sec}) — violates primary-before-secondary order."
            )
        elif lesion.end > earliest_sec:
            # Soft warn: primary started before secondary but was still active when
            # secondary appeared. LATENCY min = 0 permits this, but it is clinically
            # suspicious and must be reviewed. The latency criterion will also fail.
            overlap_days = (lesion.end - earliest_sec).days
            warn_issues.append(
                f"Primary-secondary overlap: ghosted lesion ({lesion.onset} → "
                f"{lesion.end}) was still active {overlap_days} day(s) into "
                f"{case2_name}'s secondary symptom onset ({earliest_sec}). Latency minimum is 0 days "
                f"so this is technically possible, but warrants manual review."
            )

    if case2_treatment_date and lesion.onset >= case2_treatment_date:
        fail_issues.append(
            f"Ghosted lesion onset ({lesion.onset}) is on/after {case2_name}'s treatment date "
            f"({case2_treatment_date}) — symptoms should not appear after treatment."
        )

    # Consistency with the comparison patient's OWN confirmed primary chancre.
    # The ghosted lesion is Case2's chancre for this scenario, so if Case2 has a
    # confirmed primary chancre the two should coincide. A real chancre far from
    # the ghosted window means this direction is biologically impossible (e.g.
    # Case2 had not yet been infected when they supposedly transmitted, or had
    # already had their chancre before the supposed exposure).
    confirmed_primaries = _confirmed_primaries(case2_symptoms)
    if confirmed_primaries:
        known = min(confirmed_primaries, key=lambda s: s.onset)
        known_end = known.onset + timedelta(
            days=known.duration_days if known.duration_days > 0 else PRIMARY["avg"]
        )
        if lesion.end < known.onset:
            gap = (known.onset - lesion.end).days
        elif known_end < lesion.onset:
            gap = (lesion.onset - known_end).days
        else:
            gap = 0  # windows overlap

        if gap > PRIMARY_CONSISTENCY_TOLERANCE_DAYS:
            fail_issues.append(
                f"Ghosted chancre ({lesion.onset} -> {lesion.end}) is {gap} day(s) from "
                f"{case2_name}'s confirmed primary chancre ({known.onset} -> {known_end}) - "
                f"inconsistent with their actual disease timeline, so this transmission "
                f"direction is not possible."
            )
        elif gap > 0:
            warn_issues.append(
                f"Ghosted chancre ({lesion.onset} -> {lesion.end}) is {gap} day(s) from "
                f"{case2_name}'s confirmed primary chancre ({known.onset} -> {known_end}) - "
                f"close but not coinciding; manual review."
            )

    if fail_issues:
        return "fail", " | ".join(fail_issues + warn_issues)
    if warn_issues:
        return "warn", " | ".join(warn_issues)
    return "pass", "Ghosted lesion follows natural syphilis progression order."


def evaluate_criteria(
    scenario: str,  # "source" or "spread"
    lesion: GhostedLesion,
    case1_symptom: Symptom,
    case2_symptoms: list[Symptom],
    case2_exposure: Optional[Exposure],
    op_exposure: Optional[Exposure],
    case2_treatment_date: Optional[date],
    date2: Optional[date] = None,
    case1_body_parts: Optional[list[str]] = None,
    case2_name: str = "the comparison patient",
    case1_treatment_date: Optional[date] = None,
    constant_key: str = "avg",
    case2_body_parts: Optional[list[str]] = None,
    stage_keys: dict | None = None,
    date1: Optional[date] = None,
) -> dict:
    """
    Run all four criteria checks for one scenario.

    Exposure check is scenario-specific and uses period intersection (the
    infectious window must OVERLAP the reported sexual-exposure window):
      source scenario → Case2's ghosted source chancre window
      spread scenario → Case1's (possibly ghosted) primary chancre window

    Infectiousness ends once the source is adequately treated, so the spread
    infectious window is clipped at Case1's treatment date.
    """
    exposure = case2_exposure or op_exposure

    # Exposure overlap check - use period intersection
    if scenario == "source":
        # Case2 must be infectious during Case1's exposure: use the ghosted
        # source chancre window assigned to Case2.
        infectious_start = lesion.onset
        infectious_end = lesion.end
    else:  # spread
        # Case1 must be infectious during Case2's exposure. Transmission happens
        # from Case1's PRIMARY chancre. When Case1's anchor is a secondary
        # symptom that chancre is ghosted (centred on Date2); otherwise it is the
        # reported primary chancre window.
        pri_k = _stage_key(stage_keys, "primary", constant_key)
        if case1_symptom.type == "Secondary Rash/Lesions" and date2 is not None:
            half_primary = PRIMARY[pri_k] // 2
            infectious_start = date2 - timedelta(days=half_primary)
            infectious_end = date2 + timedelta(days=half_primary)
        else:
            dur = (
                case1_symptom.duration_days
                if case1_symptom.duration_days > 0
                else PRIMARY[pri_k]
            )
            infectious_start = case1_symptom.onset
            infectious_end = case1_symptom.onset + timedelta(days=dur)

        # Infectiousness ends at adequate treatment (VCA: infectious while the
        # chancre is present, until penicillin).
        if case1_treatment_date and case1_treatment_date < infectious_end:
            infectious_end = max(infectious_start, case1_treatment_date)

    # Source: inoculation_date = date1 (when Case2 infected Case1).
    # Spread: inoculation_date = date2 (when Case1 infected Case2).
    inoculation_date = date1 if scenario == "source" else date2
    exp_status, exp_detail = _check_exposure(
        infectious_start, infectious_end, exposure,
        inoculation_date=inoculation_date,
    )

    # Anatomical compatibility (VCA criterion 2) is direction-aware: validate the
    # source's lesion site and the recipient's lesion site against the body parts
    # each used. Case1 is the anchor; Case2's representative primary comes from
    # its symptom list (its ghosted chancre carries no site).
    case2_primary = _best_primary_symptom(case2_symptoms)
    if scenario == "source":
        # Case2 is the hypothesised source, Case1 the recipient.
        modality_status, modality_detail = _anatomical_compatibility(
            source_symptom=case2_primary,
            source_body_parts=case2_body_parts or [],
            recipient_symptom=case1_symptom,
            recipient_body_parts=case1_body_parts or [],
        )
    else:  # spread — Case1 is the source, Case2 the recipient.
        modality_status, modality_detail = _anatomical_compatibility(
            source_symptom=case1_symptom,
            source_body_parts=case1_body_parts or [],
            recipient_symptom=case2_primary,
            recipient_body_parts=case2_body_parts or [],
        )
    lat_status, lat_detail = _latency_to_secondary(lesion, case2_symptoms, case2_name)
    ord_status, ord_detail = _natural_order(
        lesion, case2_symptoms, case2_treatment_date, case2_name
    )

    return {
        "exposure": {"status": exp_status, "detail": exp_detail},
        "exposure_modality": {"status": modality_status, "detail": modality_detail},
        "latency": {"status": lat_status, "detail": lat_detail},
        "natural_order": {"status": ord_status, "detail": ord_detail},
    }


def _scenario_passes(criteria: dict) -> bool:
    return all(v["status"] != "fail" for v in criteria.values())


# ---------------------------------------------------------------------------
# Step 6 — Verdict
# ---------------------------------------------------------------------------


def determine_verdict(
    source_confidence: str,
    spread_confidence: str,
    case1_role: str,
    case1_name: str,
    case2_name: str,
    source_results: ScenarioResult,
    spread_results: ScenarioResult,
) -> str:
    """
    Build the final verdict string based on confidence levels.

    Confidence levels: Robust > Likely > Possible > Weak > Unlikely > Unrelated
    """
    s_rank = CONFIDENCE_RANK.get(source_confidence, 0)
    sp_rank = CONFIDENCE_RANK.get(spread_confidence, 0)

    # Display labels with role prefix. Case2's role is the complement of Case1's.
    case2_role = "partner" if case1_role == "OP" else "OP"

    def _label(name: str, role: str) -> str:
        return f"{'OP' if role == 'OP' else 'Partner'} ({name})"

    case1_label = _label(case1_name, case1_role)
    case2_label = _label(case2_name, case2_role)

    # --- Base directional conclusion ---
    # source scenario = "Did Case2 infect Case1?" → Case2 is the SOURCE.
    # spread scenario = "Did Case1 infect Case2?" → Case1 is the SOURCE.
    if s_rank > sp_rank and s_rank >= 2:
        verdict = f"{case2_label} is the SOURCE — {case1_label} is a SPREAD."
    elif sp_rank > s_rank and sp_rank >= 2:
        verdict = f"{case1_label} is the SOURCE — {case2_label} is a SPREAD."
    elif s_rank >= 2 and s_rank == sp_rank:
        verdict = "AMBIGUOUS — both source and spread scenarios show similar confidence. Manual review required."
    else:
        verdict = "UNRELATED INFECTIONS — neither source nor spread scenario shows a likely transmission link."

    # --- Overlap annotation ---
    # Scan ALL ranges for primary-secondary overlap signals
    overlap_flagged = False
    for res in [source_results, spread_results]:
        for range_name, criteria in res.range_data.items():
            nat = criteria.get("natural_order", {})
            lat = criteria.get("latency", {})
            if (
                nat.get("status") == "warn"
                and "primary-secondary overlap" in (nat.get("detail") or "").lower()
            ) or (
                lat.get("status") == "fail"
                and "overlap" in (lat.get("detail") or "").lower()
            ):
                overlap_flagged = True
                break
        if overlap_flagged:
            break

    if overlap_flagged:
        verdict += (
            " ⚠ Primary-secondary overlap detected in at least one range — "
            "manual clinical review recommended."
        )

    return verdict


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
    op_body_parts: Optional[list[str]] = None,
    partner_body_parts: Optional[list[str]] = None,
    op_last_neg_test: Optional[date] = None,
    partner_last_neg_test: Optional[date] = None,
) -> GhostingResult:
    """
    Full ghosting analysis pipeline following VCA methodology, executing
    across three ranges: Aggressive, Expected, and Conservative.
    """
    log: list[str] = ["=== VCA Range-Based Ghosting Analysis ===", ""]

    # Range mapping
    SCENARIOS: dict[str, dict[str, str]] = {
        "aggressive":                {"incubation": "min", "primary": "min", "latency": "min", "secondary": "min"},
        "expected":                  {"incubation": "avg", "primary": "avg", "latency": "avg", "secondary": "avg"},
        "conservative":              {"incubation": "max", "primary": "max", "latency": "max", "secondary": "max"},
        "fast_infection_slow_disease": {"incubation": "min", "primary": "max", "latency": "max", "secondary": "max"},
        "slow_infection_fast_disease": {"incubation": "max", "primary": "min", "latency": "min", "secondary": "min"},
    }
    # Hoisted out of the loop — these are constant across all 5 scenario iterations.
    _RANGE_LABELS: dict[str, str] = {
        "aggressive":                "Optimistic range — minimum constants (fastest possible progression)",
        "expected":                  "Expected range — average constants",
        "conservative":              "Conservative range — maximum constants (slowest possible progression)",
        "fast_infection_slow_disease": "Fast-infection range — min incubation, max primary/latency/secondary",
        "slow_infection_fast_disease": "Slow-infection range — max incubation, min primary/latency/secondary",
    }
    _LOG_ICON: dict[str, str] = {
        "pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]", "na": "[N/A ]",
    }
    _CRIT_LABEL: dict[str, str] = {
        "exposure": "Exposure overlap",
        "exposure_modality": "Anatomical compatibility",
        "latency": "Latency to secondary",
        "natural_order": "Natural progression order",
    }

    # --- Step 1: Identify Case1 ---
    case1_role, case1_symptom, case2_role, case2_symptoms = select_case1(
        op_symptoms, partner_symptoms
    )
    case1_name = op_name if case1_role == "OP" else partner_name
    case2_name = partner_name if case1_role == "OP" else op_name
    case2_treatment = (
        partner_treatment_date if case1_role == "OP" else op_treatment_date
    )
    case1_treatment = (
        op_treatment_date if case1_role == "OP" else partner_treatment_date
    )
    case2_exposure = partner_exposure if case1_role == "OP" else op_exposure
    case1_body_parts = (op_body_parts or []) if case1_role == "OP" else (partner_body_parts or [])
    case2_body_parts = (partner_body_parts or []) if case1_role == "OP" else (op_body_parts or [])
    case1_last_neg_test = op_last_neg_test if case1_role == "OP" else partner_last_neg_test

    log.append(
        f"Step 1: Anchor patient — {case1_name} ({case1_role}) has the highest-ranked "
        f"symptom: {case1_symptom.type} (onset {case1_symptom.onset})."
    )
    log.append(f"        Comparison patient — {case2_name} ({case2_role}).")

    # Containers for range results
    source_range_data = {}
    source_range_lesions = {}
    spread_range_data = {}
    spread_range_lesions = {}

    # --- Steps 2-6: Range Loop ---
    for scenario_name, stage_keys in SCENARIOS.items():
        log.append(f"\n--- {_RANGE_LABELS.get(scenario_name, scenario_name)} ---")

        effective_symptom = resolve_zero_duration_symptom(case1_symptom)

        # Date calculations
        d1 = calc_date1(effective_symptom, stage_keys=stage_keys)
        if case1_last_neg_test:
            floor = case1_last_neg_test - timedelta(days=INCUBATION["max"])
            if d1 < floor:
                log.append(
                    f"  [FLOOR] Date1 ({d1}) precedes the infectious floor derived from "
                    f"{case1_name}'s last negative test ({case1_last_neg_test} − 90 d = {floor}). "
                    f"Flooring Date1 to {floor}."
                )
                d1 = floor
        d2 = calc_date2(effective_symptom, stage_keys=stage_keys)

        # Lesion generation
        source_lesion = calc_ghosted_source(
            d1,
            assigned_to=case2_role,
            derived_from=effective_symptom.type,
            stage_keys=stage_keys,
        )
        spread_lesion = calc_ghosted_spread(
            d2,
            assigned_to=case2_role,
            derived_from=effective_symptom.type,
            stage_keys=stage_keys,
        )

        # Evaluate
        source_crit = evaluate_criteria(
            scenario="source",
            lesion=source_lesion,
            case1_symptom=effective_symptom,
            case2_symptoms=case2_symptoms,
            case2_exposure=case2_exposure,
            op_exposure=op_exposure,
            case2_treatment_date=case2_treatment,
            date2=d2,
            date1=d1,
            case1_body_parts=case1_body_parts,
            case2_name=case2_name,
            case1_treatment_date=case1_treatment,
            stage_keys=stage_keys,
            case2_body_parts=case2_body_parts,
        )
        spread_crit = evaluate_criteria(
            scenario="spread",
            lesion=spread_lesion,
            case1_symptom=effective_symptom,
            case2_symptoms=case2_symptoms,
            case2_exposure=case2_exposure,
            op_exposure=op_exposure,
            case2_treatment_date=case2_treatment,
            date2=d2,
            date1=d1,
            case1_body_parts=case1_body_parts,
            case2_name=case2_name,
            case1_treatment_date=case1_treatment,
            stage_keys=stage_keys,
            case2_body_parts=case2_body_parts,
        )

        source_range_data[scenario_name] = source_crit
        source_range_lesions[scenario_name] = source_lesion
        spread_range_data[scenario_name] = spread_crit
        spread_range_lesions[scenario_name] = spread_lesion

        # Log results for this range
        for sname, crit in [("SOURCE", source_crit), ("SPREAD", spread_crit)]:
            log.append(f"  {sname} scenario:")
            for k, v in crit.items():
                log.append(
                    f"    {_LOG_ICON.get(v['status'], '[?]')} "
                    f"{_CRIT_LABEL.get(k, k)}: {v['detail']}"
                )

    # --- Step 7: Confidence and Verdict ---
    def derive_confidence(data: dict[str, dict]) -> tuple[str, int]:
        # A tier counts only when all criteria pass-or-warn AND the exposure
        # criterion is a clean pass (inoculation date inside the window).
        passes = sum(
            1 for crit in data.values()
            if _scenario_passes(crit) and crit["exposure"]["status"] == "pass"
        )
        assert passes in _CONFIDENCE_LEVELS, f"Unexpected pass_count {passes}"
        return _CONFIDENCE_LEVELS[passes], passes

    source_conf, source_pass_count = derive_confidence(source_range_data)
    spread_conf, spread_pass_count = derive_confidence(spread_range_data)

    log.append("\nConfidence summary:")
    _n_tiers = len(SCENARIOS)
    log.append(f"  Did {case2_name} infect {case1_name}? {source_conf} ({source_pass_count}/{_n_tiers} tiers pass)")
    log.append(f"  Did {case1_name} infect {case2_name}? {spread_conf} ({spread_pass_count}/{_n_tiers} tiers pass)")

    source_scenarios = ScenarioResult(
        range_data=source_range_data,
        range_lesions=source_range_lesions,
        confidence=source_conf,
        pass_count=source_pass_count,
    )
    spread_scenarios = ScenarioResult(
        range_data=spread_range_data,
        range_lesions=spread_range_lesions,
        confidence=spread_conf,
        pass_count=spread_pass_count,
    )

    verdict = determine_verdict(
        source_confidence=source_conf,
        spread_confidence=spread_conf,
        case1_role=case1_role,
        case1_name=case1_name,
        case2_name=case2_name,
        source_results=source_scenarios,
        spread_results=spread_scenarios,
    )

    log.append(f"\nConclusion: {verdict}")

    return GhostingResult(
        case1_name=case1_name,
        case2_name=case2_name,
        case1_symptom=case1_symptom,
        source_scenarios=source_scenarios,
        spread_scenarios=spread_scenarios,
        verdict=verdict,
        log=log,
    )
