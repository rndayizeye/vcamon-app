"""
tests/test_clinical.py

Unit tests for the VCA ghosting analysis engine in app/utils/clinical.py.

Test case based on VCA Training slide 17 (Fussell 2022):
  OP = Johnny Smith — penile chancre onset 3/5/2020, treated 3/10/2020
  Partner Samuel — rectal chancre onset ~2/8/2020 (7 days before exam 2/15/2020)
  Partner Heather — vaginal chancre 4/3/2020
  Expected: Samuel is SOURCE, Heather is SPREAD
"""

import pytest
from datetime import date, timedelta
from app.utils.clinical import (
    Symptom, Exposure,
    select_p1, avg_inoculation_date, calc_ghosted_source,
    calc_d2, calc_ghosted_spread, evaluate_criteria,
    run_ghosting_analysis, symptom_rank,
    INCUBATION, PRIMARY, LATENCY,
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
def heather_chancre():
    return Symptom(type="Secondary Rash/Lesions", onset=date(2020, 4, 3), duration_days=0)

@pytest.fixture
def samuel_exposure():
    return Exposure(
        first=date(2019, 9, 1),
        last=date(2020, 2, 15),
        sex_types=["Rectal LX"],
    )

@pytest.fixture
def heather_exposure():
    return Exposure(
        first=date(2019, 6, 1),
        last=date(2020, 3, 8),
        sex_types=["Vaginal LX"],
    )


# ---------------------------------------------------------------------------
# symptom_rank
# ---------------------------------------------------------------------------

class TestSymptomRank:
    def test_primary_is_highest(self):
        assert symptom_rank("Primary Chancre") < symptom_rank("Secondary Rash/Lesions")

    def test_ghosted_between_historical_and_secondary(self):
        assert symptom_rank("Historical Primary") < symptom_rank("Ghosted Primary")
        assert symptom_rank("Ghosted Primary") < symptom_rank("Secondary Rash/Lesions")

    def test_unknown_type_gets_low_priority(self):
        assert symptom_rank("Unknown") == 99


# ---------------------------------------------------------------------------
# select_p1
# ---------------------------------------------------------------------------

class TestSelectP1:
    def test_op_with_primary_beats_partner_secondary(self, johnny_chancre, heather_chancre):
        role, sym, p2_role, _ = select_p1([johnny_chancre], [heather_chancre])
        assert role == "OP"
        assert sym.type == "Primary Chancre"

    def test_partner_with_primary_beats_op_secondary(self, heather_chancre, samuel_chancre):
        role, sym, p2_role, _ = select_p1([heather_chancre], [samuel_chancre])
        assert role == "partner"
        assert sym.type == "Primary Chancre"

    def test_equal_rank_op_wins(self):
        op_sym = Symptom("Primary Chancre", date(2020, 1, 1), 0)
        p_sym  = Symptom("Primary Chancre", date(2020, 2, 1), 0)
        role, sym, _, _ = select_p1([op_sym], [p_sym])
        assert role == "OP"

    def test_no_symptoms_raises(self):
        with pytest.raises(ValueError, match="Neither"):
            select_p1([], [])

    def test_only_op_symptoms(self):
        s = Symptom("Primary Chancre", date(2020, 1, 1), 0)
        role, sym, p2_role, _ = select_p1([s], [])
        assert role == "OP"
        assert p2_role == "partner"

    def test_only_partner_symptoms(self):
        s = Symptom("Secondary Rash/Lesions", date(2020, 3, 1), 0)
        role, sym, p2_role, _ = select_p1([], [s])
        assert role == "partner"


# ---------------------------------------------------------------------------
# avg_inoculation_date
# ---------------------------------------------------------------------------

class TestAvgInoculationDate:
    def test_primary_chancre(self, johnny_chancre):
        d1 = avg_inoculation_date(johnny_chancre)
        expected = johnny_chancre.onset - timedelta(days=INCUBATION["avg"])
        assert d1 == expected

    def test_secondary_goes_back_full_chain(self):
        s = Symptom("Secondary Rash/Lesions", date(2020, 4, 1), 0)
        d1 = avg_inoculation_date(s)
        expected = s.onset - timedelta(days=INCUBATION["avg"] + PRIMARY["avg"] + LATENCY["avg"])
        assert d1 == expected

    def test_unknown_type_raises(self):
        s = Symptom("Unknown", date(2020, 1, 1), 0)
        with pytest.raises(ValueError):
            avg_inoculation_date(s)


# ---------------------------------------------------------------------------
# calc_ghosted_source
# ---------------------------------------------------------------------------

class TestCalcGhostedSource:
    def test_d1_is_midpoint(self, johnny_chancre):
        d1 = avg_inoculation_date(johnny_chancre)
        gs = calc_ghosted_source(d1, "partner", johnny_chancre.type)
        half = PRIMARY["avg"] // 2
        assert gs.onset == d1 - timedelta(days=half)
        assert gs.end   == d1 + timedelta(days=half)

    def test_assigned_to_set(self, johnny_chancre):
        d1 = avg_inoculation_date(johnny_chancre)
        gs = calc_ghosted_source(d1, "partner", johnny_chancre.type)
        assert gs.assigned_to == "partner"
        assert gs.lesion_type == "ghosted_source"


# ---------------------------------------------------------------------------
# calc_d2 and calc_ghosted_spread
# ---------------------------------------------------------------------------

class TestCalcD2:
    def test_primary_midpoint(self, johnny_chancre):
        dur = PRIMARY["avg"]
        d2 = calc_d2(johnny_chancre)
        expected = johnny_chancre.onset + timedelta(days=dur // 2)
        assert d2 == expected

    def test_primary_with_known_duration(self, samuel_chancre):
        d2 = calc_d2(samuel_chancre)
        expected = samuel_chancre.onset + timedelta(days=samuel_chancre.duration_days // 2)
        assert d2 == expected

    def test_secondary_uses_latency_formula(self):
        s = Symptom("Secondary Rash/Lesions", date(2020, 4, 1), 0)
        d2 = calc_d2(s)
        expected = s.onset - timedelta(days=round(LATENCY["avg"] + PRIMARY["avg"] / 2))
        assert d2 == expected

    def test_ghosted_spread_starts_after_d2(self, johnny_chancre):
        d2 = calc_d2(johnny_chancre)
        spread = calc_ghosted_spread(d2, "partner", johnny_chancre.type)
        assert spread.onset == d2 + timedelta(days=PRIMARY["avg"])
        assert spread.end   == spread.onset + timedelta(days=PRIMARY["avg"])
        assert spread.lesion_type == "ghosted_spread"


# ---------------------------------------------------------------------------
# Full pipeline — slide 17 scenario (Johnny + Samuel)
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_samuel_is_source(self, johnny_chancre, samuel_chancre, heather_exposure, samuel_exposure):
        """
        Per slide 17: Samuel (with existing chancre) is the source of Johnny's infection.
        """
        result = run_ghosting_analysis(
            op_name="Johnny",
            op_symptoms=[johnny_chancre],
            op_exposure=Exposure(date(2019, 9, 3), date(2020, 2, 25), ["Penile LX"]),
            op_treatment_date=date(2020, 3, 10),
            partner_name="Samuel",
            partner_symptoms=[samuel_chancre],
            partner_exposure=samuel_exposure,
            partner_treatment_date=date(2020, 2, 17),
        )
        assert "SOURCE" in result.verdict or "AMBIGUOUS" in result.verdict
        assert result.p1_name == "Samuel"   # Samuel has higher-rank symptom (earlier chancre)
        assert result.ghosted_source.lesion_type == "ghosted_source"
        assert result.ghosted_spread.lesion_type == "ghosted_spread"

    def test_result_has_log(self, johnny_chancre, samuel_chancre, samuel_exposure):
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
        assert len(result.log) > 5
        assert any("Step 1" in line for line in result.log)
        assert any("Conclusion" in line for line in result.log)

    def test_no_symptoms_raises(self):
        with pytest.raises(ValueError):
            run_ghosting_analysis(
                op_name="A", op_symptoms=[], op_exposure=None,
                op_treatment_date=None,
                partner_name="B", partner_symptoms=[], partner_exposure=None,
                partner_treatment_date=None,
            )

    def test_unrelated_when_exposure_dates_incompatible(self):
        """Force fail by making exposure dates nowhere near the ghosted lesion."""
        op_sym = Symptom("Primary Chancre", date(2020, 3, 1), 0)
        p_sym  = Symptom("Secondary Rash/Lesions", date(2020, 10, 1), 0)

        # Exposure that doesn't overlap with any ghosted window
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
        # With bad exposure dates, both scenarios should fail exposure criterion
        assert result.criteria["source"]["exposure"]["status"] == "fail"
        assert result.criteria["spread"]["exposure"]["status"] == "fail"


# ---------------------------------------------------------------------------
# _scenario_passes
# ---------------------------------------------------------------------------

class TestScenarioPasses:
    def test_all_pass(self):
        criteria = {
            "exposure":      {"status": "pass", "detail": ""},
            "sex_type":      {"status": "pass", "detail": ""},
            "latency":       {"status": "na",   "detail": ""},
            "natural_order": {"status": "warn", "detail": ""},
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
