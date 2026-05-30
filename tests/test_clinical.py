"""
tests/test_clinical.py

Unit tests for the VCA ghosting analysis engine in app/utils/clinical.py.

Naming conventions match the engine:
  Case1  — person with highest-ranking symptom
  Case2  — the other person
  Date1  — likely inoculation date (Case1 symptom onset − avg incubation)
  Date2  — Case1's infectious midpoint

Test scenario based on VCA Training slide 17 (Fussell 2022):
  OP = Johnny Smith — penile chancre onset 3/5/2020, treated 3/10/2020
  Partner Samuel — rectal chancre onset ~2/8/2020 (7 days before exam 2/15/2020)
  Expected: Samuel is SOURCE (Case1), Johnny is Case2

Exposure criterion rules:
  Source scenario → Date1 must be within exposure window
  Spread scenario → Date2 must be within exposure window
  Warn threshold  → miss by ≤ 10 days (EXPOSURE_WARN_MARGIN_DAYS) → warn not fail
"""

from datetime import date, timedelta

import pytest

from app.db.models import SymptomDateKind, SymptomDurationSource
from app.utils.clinical import (
    EXPOSURE_WARN_MARGIN_DAYS,
    INCUBATION,
    LATENCY,
    PRIMARY,
    Exposure,
    GhostedLesion,
    Symptom,
    _anatomical_compatibility,
    _best_primary_symptom,
    _latency_to_secondary,
    _scenario_passes,
    avg_inoculation_date,  # both aliases
    calc_d2,  # both aliases
    calc_date1,
    calc_date2,
    calc_ghosted_source,
    calc_ghosted_spread,
    derive_symptom_capture_metadata,
    evaluate_criteria,
    resolve_symptom_timing_for_analysis,
    run_ghosting_analysis,
    select_case1,
    select_p1,  # both aliases should work
    symptom_rank,
)

# ---------------------------------------------------------------------------
# Fixtures — slide 17 scenario
# ---------------------------------------------------------------------------


@pytest.fixture
def johnny_chancre():
    return Symptom(type="Primary Chancre", onset=date(2020, 3, 5), duration_days=0)


@pytest.fixture
def samuel_chancre():
    """Samuel's rectal chancre: 7 days before exam on 2/15 → onset ~2/8/2020."""
    return Symptom(type="Primary Chancre", onset=date(2020, 2, 8), duration_days=7)


@pytest.fixture
def heather_secondary():
    return Symptom(
        type="Secondary Rash/Lesions", onset=date(2020, 4, 3), duration_days=0
    )


@pytest.fixture
def samuel_exposure():
    return Exposure(
        first=date(2019, 9, 1),
        last=date(2020, 2, 15),
    )


@pytest.fixture
def johnny_exposure():
    return Exposure(
        first=date(2019, 9, 3),
        last=date(2020, 2, 25),
    )


# ---------------------------------------------------------------------------
# symptom capture derivation helpers
# ---------------------------------------------------------------------------


class TestSymptomCaptureDerivation:
    def test_observed_primary_without_duration_assumes_max_duration(self):
        date_kind, duration_source, derived_ongoing = derive_symptom_capture_metadata(
            symptom_type="Penile LX",
            anchor_date=date(2024, 2, 15),
            duration_days=None,
            date_kind=SymptomDateKind.OBSERVED_DURING_EXAM,
            classification="Primary",
        )
        onset, duration = resolve_symptom_timing_for_analysis(
            symptom_type="Penile LX",
            anchor_date=date(2024, 2, 15),
            duration_days=None,
            date_kind=date_kind,
            classification="Primary",
        )

        assert date_kind == SymptomDateKind.OBSERVED_DURING_EXAM
        assert duration_source == SymptomDurationSource.ASSUMED_MAX
        assert derived_ongoing is True
        assert duration == PRIMARY["max"]
        assert onset == date(2024, 2, 15) - timedelta(days=PRIMARY["max"])

    def test_reported_onset_keeps_reported_timing(self):
        date_kind, duration_source, derived_ongoing = derive_symptom_capture_metadata(
            symptom_type="Rash",
            anchor_date=date(2024, 3, 1),
            duration_days=14,
            date_kind=SymptomDateKind.ONSET_REPORTED,
            classification="Secondary",
        )
        onset, duration = resolve_symptom_timing_for_analysis(
            symptom_type="Rash",
            anchor_date=date(2024, 3, 1),
            duration_days=14,
            date_kind=date_kind,
            classification="Secondary",
        )

        assert date_kind == SymptomDateKind.ONSET_REPORTED
        assert duration_source == SymptomDurationSource.REPORTED
        assert derived_ongoing is False
        assert onset == date(2024, 3, 1)
        assert duration == 14


# ---------------------------------------------------------------------------
# symptom_rank
# ---------------------------------------------------------------------------


class TestSymptomRank:
    def test_primary_is_highest(self):
        assert symptom_rank("Primary Chancre") < symptom_rank("Secondary Rash/Lesions")

    def test_hierarchy_order(self):
        assert symptom_rank("Primary Chancre") < symptom_rank("Historical Primary")
        assert symptom_rank("Historical Primary") < symptom_rank("Ghosted Primary")
        assert symptom_rank("Ghosted Primary") < symptom_rank("Secondary Rash/Lesions")

    def test_unknown_type_gets_low_priority(self):
        assert symptom_rank("Unknown") == 99


# ---------------------------------------------------------------------------
# select_case1 (and legacy select_p1 alias)
# ---------------------------------------------------------------------------


class TestSelectCase1:
    def test_op_with_primary_beats_partner_secondary(
        self, johnny_chancre, heather_secondary
    ):
        role, sym, case2_role, _ = select_case1([johnny_chancre], [heather_secondary])
        assert role == "OP"
        assert sym.type == "Primary Chancre"

    def test_partner_with_primary_beats_op_secondary(
        self, heather_secondary, samuel_chancre
    ):
        role, sym, _, _ = select_case1([heather_secondary], [samuel_chancre])
        assert role == "partner"
        assert sym.type == "Primary Chancre"

    def test_equal_rank_op_wins(self):
        op_sym = Symptom("Primary Chancre", date(2020, 1, 1), 0)
        p_sym = Symptom("Primary Chancre", date(2020, 2, 1), 0)
        role, _, _, _ = select_case1([op_sym], [p_sym])
        assert role == "OP"

    def test_no_symptoms_raises(self):
        with pytest.raises(ValueError, match="Neither"):
            select_case1([], [])

    def test_legacy_alias_works(self, johnny_chancre):
        role, sym, _, _ = select_p1([johnny_chancre], [])
        assert role == "OP"


# ---------------------------------------------------------------------------
# calc_date1 (and legacy avg_inoculation_date alias)
# ---------------------------------------------------------------------------


class TestCalcDate1:
    def test_primary_chancre(self, johnny_chancre):
        date1 = calc_date1(johnny_chancre)
        assert date1 == johnny_chancre.onset - timedelta(days=INCUBATION["avg"])

    def test_secondary_goes_back_full_chain(self):
        s = Symptom("Secondary Rash/Lesions", date(2020, 4, 1), 0)
        date1 = calc_date1(s)
        expected = s.onset - timedelta(
            days=INCUBATION["avg"] + PRIMARY["avg"] + LATENCY["avg"]
        )
        assert date1 == expected

    def test_unknown_type_raises(self):
        s = Symptom("Unknown", date(2020, 1, 1), 0)
        with pytest.raises(ValueError):
            calc_date1(s)

    def test_legacy_alias_works(self, johnny_chancre):
        assert avg_inoculation_date(johnny_chancre) == calc_date1(johnny_chancre)


# ---------------------------------------------------------------------------
# calc_date2 (and legacy calc_d2 alias)
# ---------------------------------------------------------------------------


class TestCalcDate2:
    def test_primary_midpoint(self, johnny_chancre):
        date2 = calc_date2(johnny_chancre)
        assert date2 == johnny_chancre.onset + timedelta(days=PRIMARY["avg"] // 2)

    def test_known_duration_used(self, samuel_chancre):
        date2 = calc_date2(samuel_chancre)
        assert date2 == samuel_chancre.onset + timedelta(
            days=samuel_chancre.duration_days // 2
        )

    def test_secondary_formula(self):
        s = Symptom("Secondary Rash/Lesions", date(2020, 4, 1), 0)
        date2 = calc_date2(s)
        expected = s.onset - timedelta(days=round(LATENCY["avg"] + PRIMARY["avg"] / 2))
        assert date2 == expected

    def test_legacy_alias_works(self, johnny_chancre):
        assert calc_d2(johnny_chancre) == calc_date2(johnny_chancre)


# ---------------------------------------------------------------------------
# calc_ghosted_source
# ---------------------------------------------------------------------------


class TestCalcGhostedSource:
    def test_date1_is_midpoint(self, johnny_chancre):
        date1 = calc_date1(johnny_chancre)
        gs = calc_ghosted_source(date1, "partner", johnny_chancre.type)
        half = PRIMARY["avg"] // 2
        assert gs.onset == date1 - timedelta(days=half)
        assert gs.end == date1 + timedelta(days=half)
        assert gs.assigned_to == "partner"
        assert gs.lesion_type == "ghosted_source"


# ---------------------------------------------------------------------------
# calc_ghosted_spread — uses avg incubation not primary duration
# ---------------------------------------------------------------------------


class TestCalcGhostedSpread:
    def test_spread_starts_after_avg_incubation(self, johnny_chancre):
        date2 = calc_date2(johnny_chancre)
        spread = calc_ghosted_spread(date2, "partner", johnny_chancre.type)
        assert spread.onset == date2 + timedelta(days=INCUBATION["avg"])
        assert spread.end == spread.onset + timedelta(days=PRIMARY["avg"])
        assert spread.lesion_type == "ghosted_spread"


# ---------------------------------------------------------------------------
# Exposure criterion — scenario-specific Date1 / Date2 checks
# ---------------------------------------------------------------------------
class TestExposureCriterion:
    def _run_source_exposure(self, infectious_start, infectious_end, exposure):
        """Helper: run exposure criterion for source scenario with exact period."""

        symptom = Symptom("Primary Chancre", date(2020, 5, 1), 0)
        # Create lesion directly with exact dates we want to test
        lesion = GhostedLesion(
            lesion_type="ghosted_source",
            onset=infectious_start,
            end=infectious_end,
            derived_from_symptom=symptom.type,
            assigned_to="partner",
        )
        result = evaluate_criteria(
            scenario="source",
            lesion=lesion,
            case1_symptom=symptom,
            case2_symptoms=[],
            case2_exposure=exposure,
            op_exposure=None,
            case2_treatment_date=None,
            date2=None,
        )
        return result["exposure"]

    def _run_spread_exposure(self, infectious_start, infectious_end, exposure):
        """Helper: run exposure criterion for spread scenario with exact period."""

        # Create symptom with exact infectious period
        duration = (infectious_end - infectious_start).days
        symptom = Symptom("Primary Chancre", infectious_start, duration)

        # Dummy lesion for spread scenario (not used in exposure check)
        lesion = GhostedLesion(
            lesion_type="ghosted_spread",
            onset=date(2020, 1, 1),
            end=date(2020, 1, 10),
            derived_from_symptom=symptom.type,
            assigned_to="partner",
        )

        result = evaluate_criteria(
            scenario="spread",
            lesion=lesion,
            case1_symptom=symptom,
            case2_symptoms=[],
            case2_exposure=exposure,
            op_exposure=None,
            case2_treatment_date=None,
            date2=None,
        )
        return result["exposure"]

    # Source scenario tests
    def test_source_pass_date1_inside_window(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 3, 1))
        # Infectious period completely within window
        result = self._run_source_exposure(date(2020, 2, 1), date(2020, 2, 10), window)
        assert result["status"] == "pass"

    def test_source_fail_date1_far_outside_window(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 2, 1))
        # Infectious period completely after window (gap > 10 days)
        result = self._run_source_exposure(date(2020, 3, 1), date(2020, 3, 20), window)
        assert result["status"] == "fail"

    def test_source_warn_date1_just_outside_window(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 2, 1))
        # Infectious period starts 5 days after window ends
        result = self._run_source_exposure(date(2020, 2, 6), date(2020, 2, 15), window)
        assert result["status"] == "warn"

    def test_source_warn_exactly_at_margin(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 2, 1))
        # Infectious period starts exactly at warn margin (10 days after window)
        margin_date = date(2020, 2, 1) + timedelta(days=EXPOSURE_WARN_MARGIN_DAYS)
        result = self._run_source_exposure(
            margin_date, margin_date + timedelta(days=5), window
        )
        assert result["status"] == "warn"

    def test_source_fail_one_day_beyond_margin(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 2, 1))
        # Infectious period starts 11 days after window (beyond 10-day margin)
        beyond_date = date(2020, 2, 1) + timedelta(days=EXPOSURE_WARN_MARGIN_DAYS + 1)
        result = self._run_source_exposure(
            beyond_date, beyond_date + timedelta(days=5), window
        )
        assert result["status"] == "fail"

    def test_source_warn_when_no_exposure_dates(self):
        result = self._run_source_exposure(date(2020, 2, 1), date(2020, 2, 10), None)
        assert result["status"] == "warn"

    # Spread scenario tests
    def test_spread_pass_date2_inside_window(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 3, 1))
        result = self._run_spread_exposure(date(2020, 2, 1), date(2020, 2, 10), window)
        assert result["status"] == "pass"

    def test_spread_fail_date2_far_outside_window(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 2, 1))
        result = self._run_spread_exposure(date(2020, 3, 15), date(2020, 3, 25), window)
        assert result["status"] == "fail"

    def test_spread_warn_date2_just_outside_window(self):
        window = Exposure(first=date(2020, 1, 1), last=date(2020, 2, 1))
        result = self._run_spread_exposure(date(2020, 2, 5), date(2020, 2, 15), window)
        assert result["status"] == "warn"

    def test_source_and_spread_use_different_periods(
        self, johnny_chancre, samuel_chancre
    ):
        """Verify source and spread check different infectious periods."""
        date1 = calc_date1(samuel_chancre)
        source_period = calc_ghosted_source(date1, "partner", samuel_chancre.type)

        # Window around source period only
        window = Exposure(
            first=source_period.onset - timedelta(days=3),
            last=source_period.end + timedelta(days=3),
        )

        source_result = self._run_source_exposure(
            source_period.onset, source_period.end, window
        )

        # Spread uses samuel's actual chancre period (much later)
        spread_result = self._run_spread_exposure(
            samuel_chancre.onset,
            samuel_chancre.onset + timedelta(days=samuel_chancre.duration_days or 21),
            window,
        )

        assert source_result["status"] == "pass"
        assert spread_result["status"] in ("warn", "fail")


# ---------------------------------------------------------------------------
# Full pipeline — slide 17 scenario
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_result_uses_case1_case2_naming(
        self, johnny_chancre, samuel_chancre, samuel_exposure, johnny_exposure
    ):
        result = run_ghosting_analysis(
            op_name="Johnny",
            op_symptoms=[johnny_chancre],
            op_exposure=johnny_exposure,
            op_treatment_date=date(2020, 3, 10),
            partner_name="Samuel",
            partner_symptoms=[samuel_chancre],
            partner_exposure=samuel_exposure,
            partner_treatment_date=date(2020, 2, 17),
        )
        # New attribute names
        assert hasattr(result, "case1_name")
        assert hasattr(result, "case2_name")
        assert hasattr(result, "case1_symptom")
        # Legacy aliases still work
        assert result.p1_name == result.case1_name
        assert result.p2_name == result.case2_name

    def test_samuel_is_case1_source(
        self, johnny_chancre, samuel_chancre, samuel_exposure, johnny_exposure
    ):
        """Samuel has earlier/higher-rank chancre so becomes Case1."""
        result = run_ghosting_analysis(
            op_name="Johnny",
            op_symptoms=[johnny_chancre],
            op_exposure=johnny_exposure,
            op_treatment_date=date(2020, 3, 10),
            partner_name="Samuel",
            partner_symptoms=[samuel_chancre],
            partner_exposure=samuel_exposure,
            partner_treatment_date=date(2020, 2, 17),
        )
        assert result.case1_name == "Samuel"
        assert "SOURCE" in result.verdict or "AMBIGUOUS" in result.verdict

    def test_log_uses_case1_case2_language(
        self, johnny_chancre, samuel_chancre, samuel_exposure
    ):
        result = run_ghosting_analysis(
            op_name="Johnny",
            op_symptoms=[johnny_chancre],
            op_exposure=None,
            op_treatment_date=date(2020, 3, 10),
            partner_name="Samuel",
            partner_symptoms=[samuel_chancre],
            partner_exposure=samuel_exposure,
            partner_treatment_date=date(2020, 2, 17),
        )
        full_log = "\n".join(result.log)
        assert "Anchor patient" in full_log
        assert "Comparison patient" in full_log
        assert "range" in full_log.lower()

    def test_source_criteria_checks_date1(
        self, johnny_chancre, samuel_chancre, samuel_exposure
    ):
        result = run_ghosting_analysis(
            op_name="Johnny",
            op_symptoms=[johnny_chancre],
            op_exposure=None,
            op_treatment_date=date(2020, 3, 10),
            partner_name="Samuel",
            partner_symptoms=[samuel_chancre],
            partner_exposure=samuel_exposure,
            partner_treatment_date=date(2020, 2, 17),
        )
        source_exp_detail = result.criteria["source"]["exposure"]["detail"]
        # Check for new message format
        assert (
            "Infectious period" in source_exp_detail
            or "overlap" in source_exp_detail.lower()
        )

    def test_spread_criteria_checks_date2(
        self, johnny_chancre, samuel_chancre, samuel_exposure
    ):
        result = run_ghosting_analysis(
            op_name="Johnny",
            op_symptoms=[johnny_chancre],
            op_exposure=None,
            op_treatment_date=date(2020, 3, 10),
            partner_name="Samuel",
            partner_symptoms=[samuel_chancre],
            partner_exposure=samuel_exposure,
            partner_treatment_date=date(2020, 2, 17),
        )
        spread_exp_detail = result.criteria["spread"]["exposure"]["detail"]
        # Check for new message format
        assert (
            "Infectious period" in spread_exp_detail
            or "overlap" in spread_exp_detail.lower()
        )

    def test_no_symptoms_raises(self):
        with pytest.raises(ValueError):
            run_ghosting_analysis(
                op_name="A",
                op_symptoms=[],
                op_exposure=None,
                op_treatment_date=None,
                partner_name="B",
                partner_symptoms=[],
                partner_exposure=None,
                partner_treatment_date=None,
            )

    def test_unrelated_when_exposure_dates_incompatible(self):
        op_sym = Symptom("Primary Chancre", date(2020, 3, 1), 0)
        p_sym = Symptom("Secondary Rash/Lesions", date(2020, 10, 1), 0)
        bad_exposure = Exposure(first=date(2021, 1, 1), last=date(2021, 6, 1))

        result = run_ghosting_analysis(
            op_name="A",
            op_symptoms=[op_sym],
            op_exposure=bad_exposure,
            op_treatment_date=date(2020, 3, 5),
            partner_name="B",
            partner_symptoms=[p_sym],
            partner_exposure=bad_exposure,
            partner_treatment_date=None,
        )
        assert result.criteria["source"]["exposure"]["status"] == "fail"
        assert result.criteria["spread"]["exposure"]["status"] == "fail"


# ---------------------------------------------------------------------------
# _scenario_passes
# ---------------------------------------------------------------------------


class TestSpreadInfectiousWindowTreatmentClip:
    """Spread infectious window must end at Case1's treatment date (VCA: infectious
    only while the chancre is present, until adequately treated)."""

    def _spread_exposure(self, case1_symptom, exposure, treatment, key="avg", date2=None):
        lesion = GhostedLesion(
            lesion_type="ghosted_spread",
            onset=date(2020, 1, 1),
            end=date(2020, 1, 10),
            derived_from_symptom=case1_symptom.type,
            assigned_to="partner",
        )
        return evaluate_criteria(
            scenario="spread",
            lesion=lesion,
            case1_symptom=case1_symptom,
            case2_symptoms=[],
            case2_exposure=exposure,
            op_exposure=None,
            case2_treatment_date=None,
            date2=date2,
            case1_treatment_date=treatment,
            constant_key=key,
        )["exposure"]

    def test_treatment_truncates_infectious_window_to_fail(self):
        # Primary chancre 2/1–2/22 (21d). Exposure 2/20–2/28 overlaps the
        # untreated window, but treatment on 2/5 cuts infectiousness to 2/1–2/5.
        sym = Symptom("Primary Chancre", date(2020, 2, 1), 21)
        window = Exposure(first=date(2020, 2, 20), last=date(2020, 2, 28))

        untreated = self._spread_exposure(sym, window, treatment=None)
        treated = self._spread_exposure(sym, window, treatment=date(2020, 2, 5))

        assert untreated["status"] == "pass"
        assert treated["status"] == "fail"


class TestSecondaryAnchorSpreadWindow:
    """When Case1's anchor is a secondary symptom, the spread infectious window is
    Case1's GHOSTED primary chancre (centred on Date2), not the secondary onset."""

    def _spread_exposure(self, sym, exposure, date2):
        lesion = GhostedLesion(
            lesion_type="ghosted_spread",
            onset=date(2019, 1, 1),
            end=date(2019, 1, 10),
            derived_from_symptom=sym.type,
            assigned_to="partner",
        )
        return evaluate_criteria(
            scenario="spread",
            lesion=lesion,
            case1_symptom=sym,
            case2_symptoms=[],
            case2_exposure=exposure,
            op_exposure=None,
            case2_treatment_date=None,
            date2=date2,
            constant_key="avg",
        )["exposure"]

    def test_window_centres_on_date2_not_secondary_onset(self):
        sym = Symptom("Secondary Rash/Lesions", date(2020, 6, 1), 0)
        date2 = calc_date2(sym)  # midpoint of Case1's ghosted primary chancre

        near_primary = Exposure(
            first=date2 - timedelta(days=3), last=date2 + timedelta(days=3)
        )
        near_secondary = Exposure(
            first=sym.onset - timedelta(days=3), last=sym.onset + timedelta(days=3)
        )

        assert self._spread_exposure(sym, near_primary, date2)["status"] == "pass"
        # Exposure sitting at the secondary rash must NOT register as the
        # infectious window (that was the old bug).
        assert self._spread_exposure(sym, near_secondary, date2)["status"] == "fail"


class TestLatencyBand:
    """Latency-to-secondary uses the natural-history band (0..LATENCY['max']);
    there is no fixed 5-week floor."""

    def _lesion(self, end):
        return GhostedLesion(
            lesion_type="ghosted_source",
            onset=end - timedelta(days=PRIMARY["avg"]),
            end=end,
            derived_from_symptom="Primary Chancre",
            assigned_to="partner",
        )

    def _sec(self, onset):
        return [Symptom("Secondary Rash/Lesions", onset, 0)]

    def test_no_secondary_is_na(self):
        status, _ = _latency_to_secondary(self._lesion(date(2020, 3, 1)), [])
        assert status == "na"

    def test_gap_within_band_passes(self):
        lesion = self._lesion(date(2020, 3, 1))
        status, _ = _latency_to_secondary(lesion, self._sec(date(2020, 3, 29)))  # 28d
        assert status == "pass"

    def test_short_gap_no_longer_fails(self):
        # 20-day gap < old 35-day floor — must now PASS (it is within latency band).
        lesion = self._lesion(date(2020, 3, 1))
        status, _ = _latency_to_secondary(lesion, self._sec(date(2020, 3, 21)))  # 20d
        assert status == "pass"

    def test_gap_exceeding_max_latency_warns(self):
        lesion = self._lesion(date(2020, 3, 1))
        far = date(2020, 3, 1) + timedelta(days=LATENCY["max"] + 5)
        status, _ = _latency_to_secondary(lesion, self._sec(far))
        assert status == "warn"

    def test_overlap_still_fails(self):
        lesion = self._lesion(date(2020, 3, 20))  # onset ~2/28, end 3/20
        # secondary onset inside the lesion window → overlap → fail
        status, detail = _latency_to_secondary(lesion, self._sec(date(2020, 3, 10)))
        assert status == "fail"
        assert "overlap" in detail.lower()


class TestAnatomicalCompatibility:
    """VCA criterion 2 is two-sided and direction-aware: both the source's and the
    recipient's known chancre sites must match the body parts each used."""

    def _criteria(self, scenario, case1_symptom, case2_symptoms, c1_parts, c2_parts):
        lesion = GhostedLesion(
            lesion_type=f"ghosted_{scenario}",
            onset=date(2020, 2, 1),
            end=date(2020, 2, 20),
            derived_from_symptom=case1_symptom.type,
            assigned_to="partner",
        )
        return evaluate_criteria(
            scenario=scenario,
            lesion=lesion,
            case1_symptom=case1_symptom,
            case2_symptoms=case2_symptoms,
            case2_exposure=None,
            op_exposure=None,
            case2_treatment_date=None,
            case1_body_parts=c1_parts,
            case2_body_parts=c2_parts,
        )["exposure_modality"]

    def test_spread_source_site_mismatch_fails(self):
        # Case1 is the source in spread; penile chancre but only oral sex reported.
        case1 = Symptom("Primary Chancre", date(2020, 3, 5), 0, anatomical_site="Penile LX")
        result = self._criteria("spread", case1, [], ["mouth"], [])
        assert result["status"] == "fail"

    def test_source_scenario_validates_case2_as_source(self):
        # Direction-awareness: in the source scenario Case2 is the source, so a
        # Case2 site/parts mismatch must FAIL even when Case1 is fully compatible.
        # (The old one-sided check looked only at Case1 and would have passed.)
        case1 = Symptom("Primary Chancre", date(2020, 3, 5), 0, anatomical_site="Penile LX")
        case2 = [Symptom("Primary Chancre", date(2020, 2, 8), 7, anatomical_site="Penile LX")]
        result = self._criteria(
            "source", case1, case2, c1_parts=["penis"], c2_parts=["mouth"]
        )
        assert result["status"] == "fail"

    def test_both_sides_compatible_passes(self):
        case1 = Symptom("Primary Chancre", date(2020, 3, 5), 0, anatomical_site="Penile LX")
        case2 = [Symptom("Primary Chancre", date(2020, 4, 1), 0, anatomical_site="Vaginal LX")]
        result = self._criteria(
            "spread", case1, case2, c1_parts=["penis"], c2_parts=["vagina"]
        )
        assert result["status"] == "pass"

    def test_aggregator_fail_dominates(self):
        src = Symptom("Primary Chancre", date(2020, 1, 1), 0, anatomical_site="Penile LX")
        rcp = Symptom("Primary Chancre", date(2020, 2, 1), 0, anatomical_site="Penile LX")
        status, _ = _anatomical_compatibility(src, ["penis"], rcp, ["mouth"])
        assert status == "fail"

    def test_aggregator_warns_when_no_data(self):
        status, _ = _anatomical_compatibility(None, [], None, [])
        assert status == "warn"

    def test_best_primary_prefers_sited_and_skips_secondary(self):
        sited = Symptom("Primary Chancre", date(2020, 2, 1), 0, anatomical_site="Penile LX")
        unsited = Symptom("Primary Chancre", date(2020, 1, 1), 0)
        assert _best_primary_symptom([unsited, sited]) is sited
        secondary = Symptom("Secondary Rash/Lesions", date(2020, 3, 1), 0)
        assert _best_primary_symptom([secondary]) is None


class TestScenarioPasses:
    def test_all_pass_or_warn_passes(self):
        criteria = {
            "exposure": {"status": "pass", "detail": ""},
            "sex_type": {"status": "warn", "detail": ""},
            "latency": {"status": "na", "detail": ""},
            "natural_order": {"status": "pass", "detail": ""},
        }
        assert _scenario_passes(criteria) is True

    def test_one_fail_fails_scenario(self):
        criteria = {
            "exposure": {"status": "pass", "detail": ""},
            "sex_type": {"status": "fail", "detail": ""},
            "latency": {"status": "pass", "detail": ""},
            "natural_order": {"status": "pass", "detail": ""},
        }
        assert _scenario_passes(criteria) is False
