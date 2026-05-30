"""
quickvca/presets.py

Known-answer scenarios for the standalone Quick VCA tool. Each preset seeds the
two-person input form so testers can poke at cases with an expected outcome.

Symptom rows use the same columns as the editor:
  Type, Onset Date, Duration, Location
Sex types use display labels: Anal, Oral, Vaginal, Penile, Rectal.

The "expected" note is what the (current) engine returns and why — useful for
spotting when a code change shifts a known answer.
"""

from __future__ import annotations

from datetime import date

# label -> scenario dict (or None for the blank form)
PRESETS: dict[str, dict | None] = {
    "— Blank form —": None,
    "Transcript: Carmela & Johannes (decisive)": {
        "expected": (
            "Johannes is the SOURCE, Carmela is a SPREAD. Carmela has an existing "
            "primary chancre (the anchor); Johannes presents with secondary "
            "symptoms, so he was infected first and gave it to Carmela. Matches the "
            "NCSDDC training worked example."
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
            "AMBIGUOUS. Alex has a primary chancre; Blake is positive but has no "
            "symptoms, and the exposure window is symmetric — so dates alone cannot "
            "say who infected whom. A realistic 'needs more evidence' case."
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
}
