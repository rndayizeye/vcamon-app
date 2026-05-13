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

import pytest
from datetime import date, timedelta
from app.utils.clinical import (
    Symptom, Exposure,
    select_case1, select_p1,          # both aliases should work
    calc_date1, avg_inoculation_date,  # both aliases
    calc_date2, calc_d2,               # both aliases
    calc_ghosted_source,
    calc_ghosted_spread,
    evaluate_criteria,
    run_ghosting_analysis,
    symptom_rank,
    INCUBATION, PRIMARY, LATENCY,
    EXPOSURE_WARN_MARGIN_DAYS,
    _scenario_passes,
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
    return Symptom(type="Secondary Rash/Lesions", onset=date(2020, 4, 3), duration_days=0)

@pytest.fixture
def samuel_exposure():
    return Exposure(
        first=date(2019, 9, 1),
        last=date(2020, 2, 15),
        sex_types=["Rectal LX"],
    )

@pytest.fixture
def johnny_exposure():
    return Exposure(
        first=date(2019, 9, 3),
        last=date(2020, 2, 25),
        sex_types=["Penile LX"],
    )


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
    def test_op_with_primary_beats_partner_secondary(self, johnny_chancre, heather_secondary):
        role, sym, case2_role, _ = select_case1([johnny_chancre], [heather_secondary])
        assert role == "OP"
        assert sym.type == "Primary Chancre"

    def test_partner_with_primary_beats_op_secondary(self, heather_secondary, samuel_chancre):
        role, sym, _, _ = select_case1([heather_secondary], [samuel_chancre])
        assert role == "partner"
        assert sym.type == "Primary Chancre"

    def test_equal_rank_op_wins(self):
        op_sym = Symptom("Primary Chancre", date(2020, 1, 1), 0)
        p_sym  = Symptom("Primary Chancre", date(2020, 2, 1), 0)
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
        assert gs.end   == date1 + timedelta(days=half)
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
        assert spread.end   == spread.onset + timedelta(days=PRIMARY["avg"])
        assert spread.lesion_type == "ghosted_spread"


# ---------------------------------------------------------------------------
# Exposure criterion — scenario-specific Date1 / Date2 checks
# ---------------------------------------------------------------------------

class TestExposureCriterion:

    def _run_source_exposure(self, check_date, exposure):
        """Helper: run just the exposure criterion for source scenario."""
        symptom = Symptom("Primary Chancre", check_date + timedelta(days=21), 0)
        result = evaluate_criteria(
            scenario="source",
            lesion=calc_ghosted_source(check_date, "partner", symptom.type),
            case1_symptom=symptom,
            case2_symptoms=[],
            case2_exposure=exposure,
            op_exposure=None,
            case2_treatment_date=None,
            date1=check_date,
            date2=None,
        )
        return result["exposure"]

    def _run_spread_exposure(self, check_date, exposure):
        """Helper: run just the exposure criterion for spread scenario."""
        symptom = Symptom("Primary Chancre", check_date - timedelta(days=10), 0)
        gs = calc_ghosted_source(check_date, "partner", symptom.type)
        result = evaluate_criteria(
            scenario="spread",
            lesion=gs,
            case1_symptom=symptom,
            case2_symptoms=[],
            case2_exposure=exposure,
            op_exposure=None,
            case2_treatment_date=None,
            date1=None,
            date2=check_date,
        )
        return result["exposure"]

    # Source scenario — Date1 tests
    def test_source_pass_date1_inside_window(self):
        window = Exposure(date(2020, 1, 1), date(2020, 3, 1), [])
        result = self._run_source_exposure(date(2020, 2, 1), window)
        assert result["status"] == "pass"

    def test_source_fail_date1_far_outside_window(self):
        window = Exposure(date(2020, 1, 1), date(2020, 2, 1), [])
        # date1 is 30 days after window ends — beyond warn margin
        result = self._run_source_exposure(date(2020, 3, 2), window)
        assert result["status"] == "fail"

    def test_source_warn_date1_just_outside_window(self):
        window = Exposure(date(2020, 1, 1), date(2020, 2, 1), [])
        # date1 is 5 days after window — within 10-day warn margin
        result = self._run_source_exposure(date(2020, 2, 6), window)
        assert result["status"] == "warn"

    def test_source_warn_exactly_at_margin(self):
        window = Exposure(date(2020, 1, 1), date(2020, 2, 1), [])
        # date1 is exactly EXPOSURE_WARN_MARGIN_DAYS after window
        result = self._run_source_exposure(
            date(2020, 2, 1) + timedelta(days=EXPOSURE_WARN_MARGIN_DAYS), window
        )
        assert result["status"] == "warn"

    def test_source_fail_one_day_beyond_margin(self):
        window = Exposure(date(2020, 1, 1), date(2020, 2, 1), [])
        result = self._run_source_exposure(
            date(2020, 2, 1) + timedelta(days=EXPOSURE_WARN_MARGIN_DAYS + 1), window
        )
        assert result["status"] == "fail"

    def test_source_warn_when_no_exposure_dates(self):
        result = self._run_source_exposure(date(2020, 2, 1), None)
        assert result["status"] == "warn"

    # Spread scenario — Date2 tests
    def test_spread_pass_date2_inside_window(self):
        window = Exposure(date(2020, 1, 1), date(2020, 3, 1), [])
        result = self._run_spread_exposure(date(2020, 2, 1), window)
        assert result["status"] == "pass"

    def test_spread_fail_date2_far_outside_window(self):
        window = Exposure(date(2020, 1, 1), date(2020, 2, 1), [])
        result = self._run_spread_exposure(date(2020, 3, 15), window)
        assert result["status"] == "fail"

    def test_spread_warn_date2_just_outside_window(self):
        window = Exposure(date(2020, 1, 1), date(2020, 2, 1), [])
        result = self._run_spread_exposure(date(2020, 2, 5), window)
        assert result["status"] == "warn"

    def test_source_and_spread_use_different_dates(self, johnny_chancre, samuel_chancre):
        """
        Source checks Date1, spread checks Date2 — they should produce
        different exposure results when the window is narrow.
        """
        date1 = calc_date1(samuel_chancre)   # Samuel is Case1
        date2 = calc_date2(samuel_chancre)

        # Window tight around date1 only
        window = Exposure(
            date1 - timedelta(days=3),
            date1 + timedelta(days=3),
            ["Rectal LX"],
        )

        source_result = self._run_source_exposure(date1, window)
        spread_result = self._run_spread_exposure(date2, window)

        assert source_result["status"] == "pass"
        # date2 is weeks after date1 so it should be outside this narrow window
        assert spread_result["status"] in ("warn", "fail")


# ---------------------------------------------------------------------------
# Full pipeline — slide 17 scenario
# ---------------------------------------------------------------------------

class TestFullPipeline:

    def test_result_uses_case1_case2_naming(self, johnny_chancre, samuel_chancre,
                                             samuel_exposure, johnny_exposure):
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

    def test_samuel_is_case1_source(self, johnny_chancre, samuel_chancre,
                                     samuel_exposure, johnny_exposure):
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

    def test_log_uses_case1_case2_language(self, johnny_chancre, samuel_chancre,
                                            samuel_exposure):
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
        assert "Case1" in full_log
        assert "Case2" in full_log
        assert "Date1" in full_log
        assert "Date2" in full_log

    def test_source_criteria_checks_date1(self, johnny_chancre, samuel_chancre,
                                           samuel_exposure):
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
        assert "Date1" in source_exp_detail

    def test_spread_criteria_checks_date2(self, johnny_chancre, samuel_chancre,
                                           samuel_exposure):
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
        assert "Date2" in spread_exp_detail

    def test_no_symptoms_raises(self):
        with pytest.raises(ValueError):
            run_ghosting_analysis(
                op_name="A", op_symptoms=[], op_exposure=None,
                op_treatment_date=None,
                partner_name="B", partner_symptoms=[], partner_exposure=None,
                partner_treatment_date=None,
            )

    def test_unrelated_when_exposure_dates_incompatible(self):
        op_sym = Symptom("Primary Chancre", date(2020, 3, 1), 0)
        p_sym  = Symptom("Secondary Rash/Lesions", date(2020, 10, 1), 0)
        bad_exposure = Exposure(date(2021, 1, 1), date(2021, 6, 1), [])

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

class TestScenarioPasses:
    def test_all_pass_or_warn_passes(self):
        criteria = {
            "exposure":      {"status": "pass", "detail": ""},
            "sex_type":      {"status": "warn", "detail": ""},
            "latency":       {"status": "na",   "detail": ""},
            "natural_order": {"status": "pass", "detail": ""},
        }
        assert _scenario_passes(criteria) is True

    def test_one_fail_fails_scenario(self):
        criteria = {
            "exposure":      {"status": "pass", "detail": ""},
            "sex_type":      {"status": "fail", "detail": ""},
            "latency":       {"status": "pass", "detail": ""},
            "natural_order": {"status": "pass", "detail": ""},
        }
        assert _scenario_passes(criteria) is False
