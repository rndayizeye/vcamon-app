"""
quickvca/presets.py

Known-answer scenarios for the standalone Quick VCA tool. Each preset seeds the
two-person input form so testers can poke at cases with an expected outcome.

Symptom rows use the same columns as the editor:
  Type, Onset Date, Duration, Location
Sex types use display labels: Anal, Oral, Vaginal, Penile, Rectal.

The "expected" note is what the (current) engine returns and why — useful for
spotting when a code change shifts a known answer.

Multi-partner presets use mode="multi" and have an "op" key plus a "contacts"
list (up to 5). Each contact carries its own exposure/sex fields plus the OP's
side of that specific pair (op_exp_first, op_exp_last, op_sex).
"""

from __future__ import annotations

from datetime import date

# label -> scenario dict (or None for the blank form)
PRESETS: dict[str, dict | None] = {
    "— Blank form —": None,

    # ------------------------------------------------------------------
    # Single-pair presets
    # ------------------------------------------------------------------

    "Transcript: Carmela & Johannes (decisive)": {
        "expected": (
            "Johannes is the SOURCE, Carmela is a SPREAD. Carmela has an existing "
            "primary chancre (the anchor); Johannes presents with secondary "
            "symptoms, so he was infected first and gave it to Carmela. Matches the "
            "NCSD training worked example."
        ),
        "a": {
            "name": "Carmela",
            "symptoms": [
                {
                    "Type": "Primary Chancre",
                    "Onset Date": date(2022, 3, 16),
                    "Duration": 12,
                    "Location": "Vaginal LX",
                }
            ],
            "exp_first": date(2021, 9, 1),
            "exp_last": date(2022, 3, 14),
            "sex": ["Vaginal", "Oral"],
            "treat": date(2022, 3, 28),
        },
        "b": {
            "name": "Johannes",
            "symptoms": [
                {
                    "Type": "Secondary Rash/Lesions",
                    "Onset Date": date(2022, 3, 12),
                    "Duration": 25,
                    "Location": None,
                }
            ],
            "exp_first": date(2021, 9, 1),
            "exp_last": date(2022, 3, 14),
            "sex": ["Vaginal", "Oral"],
            "treat": date(2022, 4, 6),
        },
    },

    "Asymptomatic partner (ambiguous)": {
        "expected": (
            "AMBIGUOUS (Possible 3/5 each). Alex has a primary chancre with unknown "
            "duration (duration=0), so the entered date is treated as the observation "
            "date and the onset is back-calculated. Both source and spread scenarios "
            "get 3 clean passes (inoculation date within the Jan–Feb window for the "
            "aggressive, expected, and fast-infection tiers). Manual review required."
        ),
        "a": {
            "name": "Alex",
            "symptoms": [
                {
                    "Type": "Primary Chancre",
                    "Onset Date": date(2024, 3, 5),
                    "Duration": 0,
                    "Location": "Penile LX",
                }
            ],
            "exp_first": date(2024, 1, 1),
            "exp_last": date(2024, 2, 28),
            "sex": ["Penile", "Oral"],
            "treat": date(2024, 3, 10),
        },
        "b": {
            "name": "Blake",
            "symptoms": [],
            "exp_first": date(2024, 1, 1),
            "exp_last": date(2024, 2, 28),
            "sex": ["Vaginal", "Oral"],
            "treat": None,
        },
    },

    "Incompatible exposure (unrelated)": {
        "expected": (
            "UNRELATED. The only reported contact is long after both infections, so "
            "neither direction of transmission is plausible."
        ),
        "a": {
            "name": "Person A",
            "symptoms": [
                {
                    "Type": "Primary Chancre",
                    "Onset Date": date(2020, 3, 1),
                    "Duration": 0,
                    "Location": "Penile LX",
                }
            ],
            "exp_first": date(2021, 1, 1),
            "exp_last": date(2021, 6, 1),
            "sex": ["Penile"],
            "treat": date(2020, 3, 5),
        },
        "b": {
            "name": "Person B",
            "symptoms": [
                {
                    "Type": "Secondary Rash/Lesions",
                    "Onset Date": date(2020, 10, 1),
                    "Duration": 0,
                    "Location": None,
                }
            ],
            "exp_first": date(2021, 1, 1),
            "exp_last": date(2021, 6, 1),
            "sex": ["Vaginal"],
            "treat": None,
        },
    },

    # ------------------------------------------------------------------
    # Multi-partner preset
    # ------------------------------------------------------------------

    "Carmela — Multi-Partner Source Investigation": {
        "mode": "multi",
        "expected": (
            "Carmela (OP) is the index patient with a primary chancre (2022-03-16). "
            "Four contacts are evaluated; Contact 5 is blank and skipped.\n\n"
            "Comprehensive mode ranking (verdict direction first, then confidence):\n"
            "  1. Johannes — SOURCE, Likely (4/5). Secondary predates Carmela's primary by "
            "     4 days; long shared window; timing is decisive per the NCSD worked example.\n"
            "  2. Marcus — SOURCE, Possible (3/5). Spread passes 3/5 tiers; inoculation "
            "     date (Date2=Mar 22) falls within the shared exposure window for the 3 "
            "     faster tiers; conservative and slow-infection tiers fail natural order.\n"
            "  3. Nadia — AMBIGUOUS (Possible 3/5 each). Source and spread both score 3/5: "
            "     the conservative and slow-infection tiers fall outside the Jan–Mar window "
            "     for source (d1=Dec), and reverse the timeline for spread (ghosted chancre "
            "     starts after Nadia's June secondary). Manual review required.\n"
            "  4. Derek — UNRELATED (0/5). Exposure began after Carmela's treatment; "
            "     neither direction is supported in any tier.\n\n"
            "Teaching point: Nadia's demotion from Likely to AMBIGUOUS demonstrates the "
            "clean-pass exposure rule — the inoculation date must fall *within* the "
            "exposure window, not just the infectious period. Overlap-only counts as a "
            "warn and does not increment the confidence score."
        ),
        "op": {
            "name": "Carmela",
            "symptoms": [
                {
                    "Type": "Primary Chancre",
                    "Onset Date": date(2022, 3, 16),
                    "Duration": 12,
                    "Location": "Vaginal LX",
                }
            ],
            "treat": date(2022, 3, 28),
        },
        "contacts": [
            {
                # Johannes — decisive source
                "name": "Johannes",
                "symptoms": [
                    {
                        "Type": "Secondary Rash/Lesions",
                        "Onset Date": date(2022, 3, 12),
                        "Duration": 25,
                        "Location": None,
                    }
                ],
                "exp_first": date(2021, 9, 1),
                "exp_last": date(2022, 3, 14),
                "sex": ["Vaginal", "Oral"],
                "treat": date(2022, 4, 6),
                "op_exp_first": date(2021, 9, 1),
                "op_exp_last": date(2022, 3, 14),
                "op_sex": ["Vaginal", "Oral"],
            },
            {
                # Marcus — plausible source, earlier primary
                "name": "Marcus",
                "symptoms": [
                    {
                        "Type": "Primary Chancre",
                        "Onset Date": date(2022, 1, 28),
                        "Duration": 21,
                        "Location": "Penile LX",
                    }
                ],
                "exp_first": date(2021, 12, 1),
                "exp_last": date(2022, 3, 10),
                "sex": ["Penile", "Vaginal"],
                "treat": date(2022, 2, 25),
                "op_exp_first": date(2021, 12, 1),
                "op_exp_last": date(2022, 3, 10),
                "op_sex": ["Vaginal", "Penile"],
            },
            {
                # Nadia — Carmela spread to her. Her June secondary is consistent
                # with being infected by Carmela in March (primary ~April, secondary
                # ~June). Under wide natural-history ranges both directions have some
                # support, but the verdict is Carmela→Nadia because that direction
                # scores higher — demonstrating why verdict direction matters more
                # than raw source-scenario confidence alone.
                "name": "Nadia",
                "symptoms": [
                    {
                        "Type": "Secondary Rash/Lesions",
                        "Onset Date": date(2022, 6, 15),
                        "Duration": 0,
                        "Location": None,
                    }
                ],
                "exp_first": date(2022, 1, 1),
                "exp_last": date(2022, 3, 25),
                "sex": ["Vaginal", "Oral"],
                "treat": date(2022, 7, 1),
                "op_exp_first": date(2022, 1, 1),
                "op_exp_last": date(2022, 3, 25),
                "op_sex": ["Vaginal", "Oral"],
            },
            {
                # Derek — unrelated; exposure began after Carmela's treatment
                "name": "Derek",
                "symptoms": [
                    {
                        "Type": "Primary Chancre",
                        "Onset Date": date(2022, 9, 1),
                        "Duration": 14,
                        "Location": "Penile LX",
                    }
                ],
                "exp_first": date(2022, 7, 1),
                "exp_last": date(2022, 8, 30),
                "sex": ["Penile", "Vaginal"],
                "treat": date(2022, 9, 10),
                "op_exp_first": date(2022, 7, 1),
                "op_exp_last": date(2022, 8, 30),
                "op_sex": ["Vaginal"],
            },
            # Contact 5 intentionally left absent — engine will skip it
        ],
    },
}
